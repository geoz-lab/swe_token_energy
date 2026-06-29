#!/bin/bash
# run_sanity.sbatch — open-weight token-consumption sanity check on 10 SWE-bench Lite tasks.
# Serves an open model with the Exp-2 vLLM container (GPU), drives it through the EXACT Exp-1
# mini-swe-agent scaffold, and reconstructs per-task tokens with the EXACT Exp-1 parser.
#
#   cd exp2_sanity_check
#   sbatch -p owners --gres=gpu:1 -C "GPU_SKU:H100_SXM5|GPU_SKU:H200_SXM5" \
#          --export=ALL,MODELS="qwen3-coder-30b",VLLM_SIF=$SCRATCH/vllm_sandbox,HF_HOME=$SCRATCH/hf \
#          slurm/run_sanity.sbatch
#
#SBATCH --job-name=exp2_sanity
#SBATCH --output=exp2_sanity_%j.out
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=08:00:00
set -euo pipefail

MODELS="${MODELS:-qwen3-coder-30b}"          # space-separated keys from exp2_token_gen/models.conf
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-2}"
# Context window for the served model. Qwen3-Coder natively supports 256k; the first run capped this
# at 32768 which artificially failed long tasks. 262144 needs the KV headroom of an H200 (141 GB).
SANITY_MAXLEN="${SANITY_MAXLEN:-262144}"

SAN="$SLURM_SUBMIT_DIR"                       # exp2_sanity_check/
EXP1="$SAN/../exp1_token_consumption"
EXP2="$SAN/../exp2_token_gen"
OUT="${OUT:-$SAN/../exp2_sanity_check_results}"
CONF="$EXP2/models.conf"
SWEYAML="$EXP1/swebench.yaml"
mkdir -p "$OUT"

# ---- conda: use the Exp-1 AGENT env (mini-swe-agent + swebench + litellm). vLLM is containerized. ----
CONDA_BASE="${CONDA_BASE:-/home/groups/kovscek/$USER/miniconda3}"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "${SANITY_CONDA_ENV:-token-energy-exp1}"
python -c "import minisweagent" 2>/dev/null || { echo "[sanity] mini-swe-agent not in env; need token-energy-exp1"; exit 1; }

# ---- storage / container ----
export HF_HOME="${HF_HOME:-$GROUP_HOME/hf}"
# Host stays ONLINE: the swebench harness loads the dataset (pre-cached anyway) and pulls the per-task
# Apptainer images via the Sherlock compute-node proxy, exactly as Exp-1 did. vLLM serves the CACHED
# model offline inside the container (vllm_apptainer.sh sets HF_HUB_OFFLINE=1 for the container itself).
unset HF_HUB_OFFLINE
export VLLM_SIF="${VLLM_SIF:-$GROUP_HOME/vllm.sif}"
export VLLM_BIN="${VLLM_BIN:-$EXP2/vllm_apptainer.sh}"
# SWE-bench task images (Apptainer): reuse the Exp-1 cache (compute nodes have no internet).
module load system apptainer 2>/dev/null || module load singularity 2>/dev/null || true
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-$SCRATCH/apptainer_cache}"
[ -e "$VLLM_SIF" ] || { echo "[sanity] VLLM_SIF not found: $VLLM_SIF"; exit 1; }

TASKS_FILE="${TASKS_FILE:-$SAN/tasks_10.txt}"   # override with a 1-task file for a wiring smoke
FILTER="$(paste -sd'|' "$TASKS_FILE")"
rm -f "$OUT/sanity_raw.csv"                       # fresh per job (parse appends)
echo "[sanity] MODELS='$MODELS' workers=$WORKERS tasks=$TASKS_FILE filter=$FILTER"

lookup() { awk -F'|' -v k="$1" '
  /^[[:space:]]*#/{next} NF<5{next} {gsub(/^[ \t]+|[ \t]+$/,"",$1)}
  $1==k{gsub(/^[ \t]+|[ \t]+$/,"",$2); gsub(/^[ \t]+|[ \t]+$/,"",$3); print $2"|"$3; exit}' "$CONF"; }

for key in $MODELS; do
  row="$(lookup "$key")"; [ -z "$row" ] && { echo "[sanity] unknown key $key"; continue; }
  IFS='|' read -r HF_ID PREC <<< "$row"
  echo "=================================================================="
  echo "[sanity] $key  ($HF_ID)  precision=$PREC"

  # 1) serve the open model (reuse Exp-2 launcher + container) WITH tool calling enabled — the agent
  #    uses native function calls, which vLLM 400s unless a tool-call parser is set. Pick per model.
  case "$key" in
    qwen3-coder-*|qwen3-32b) PARSER="${TOOL_CALL_PARSER:-qwen3_coder}" ;;
    gpt-oss-*)               PARSER="${TOOL_CALL_PARSER:-openai}" ;;
    *)                       PARSER="${TOOL_CALL_PARSER:-hermes}" ;;
  esac
  set +e
  PID="$(MODEL="$HF_ID" PRECISION="$PREC" PORT="$PORT" MAXLEN="$SANITY_MAXLEN" TOOL_CALL_PARSER="$PARSER" \
         SERVER_LOG="$OUT/vllm_sanity_${key}.log" bash "$EXP2/launch_vllm.sh")"
  rc=$?; set -e
  [ $rc -ne 0 ] && { echo "[sanity] vLLM launch failed for $key"; continue; }

  # 2) point litellm at the local vLLM via the plain OpenAI-compatible provider (most robust route).
  #    vLLM serves an OpenAI /v1 API; litellm's `openai/<model>` + OPENAI_API_BASE talks to it directly.
  BASE_URL="http://127.0.0.1:${PORT}/v1"
  export OPENAI_API_KEY="EMPTY"
  export OPENAI_API_BASE="$BASE_URL"
  export OPENAI_BASE_URL="$BASE_URL"
  # also set the hosted_vllm vars in case the config path uses them
  export HOSTED_VLLM_API_BASE="$BASE_URL"
  export HOSTED_VLLM_API_KEY="EMPTY"
  # Local model has no litellm price entry → cost calc raises. We measure tokens from the trajectory
  # (parse_trajectory.py), not billed cost, so disable cost tracking.
  export MSWEA_COST_TRACKING='ignore_errors'
  # sanity: confirm the server advertises the model under this exact id
  echo "[sanity] models advertised by vLLM:"; curl -sS "$BASE_URL/models" | head -c 400; echo

  # 3) run the SAME Exp-1 scaffold on the 10 tasks (fresh run dir + --redo-existing so nothing skips)
  RUNDIR="$OUT/runs_${key}"; rm -rf "$RUNDIR"; mkdir -p "$RUNDIR"
  mini-extra swebench \
    -c "$SWEYAML" \
    --model "openai/${HF_ID}" \
    --subset lite --split test \
    --environment-class singularity \
    --filter "$FILTER" \
    --redo-existing \
    --workers "$WORKERS" \
    -o "$RUNDIR" || echo "[sanity] swebench run had errors for $key"

  # 4) reconstruct tokens with the SAME Exp-1 parser
  python "$EXP1/parse_trajectory.py" --runs-dir "$RUNDIR" --model "$key" \
    --out "$OUT/sanity_raw.csv" || echo "[sanity] parse had errors for $key"

  # 5) stop the server
  echo "[sanity] stopping vLLM pid=$PID"
  kill "$PID" 2>/dev/null || true
  for i in $(seq 1 12); do kill -0 "$PID" 2>/dev/null || break; sleep 2; done
  kill -9 "$PID" 2>/dev/null || true
  sleep 3
done

echo "[sanity] done. tokens -> $OUT/sanity_raw.csv ; compare with: python compare.py"
