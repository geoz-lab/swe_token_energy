#!/bin/bash
# run_exp2.sbatch — one GPU job for a single tier; loops its models, benchmarks each, logs power.
# Partition / constraint / gres are passed on the command line by submit_all.sh (so this one file
# serves A100 / H100 / H200). Required env (via --export): TIER, MODELS.
#
#   sbatch -p owners --gres=gpu:1 -C "GPU_SKU:H100_SXM5" \
#          --export=ALL,TIER=H100,MODELS="gpt-oss-20b qwen3-coder-30b qwen3-32b kimi-dev-72b qwen3-coder-next" \
#          slurm/run_exp2.sbatch
#
#SBATCH --job-name=exp2
#SBATCH --output=exp2_%x_%j.out
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=256G
set -euo pipefail

TIER="${TIER:?set TIER (A100|H100|H200)}"
MODELS="${MODELS:?set MODELS (space-separated keys from models.conf)}"
PORT="${PORT:-8000}"

HERE="$SLURM_SUBMIT_DIR"                 # submit from exp2_token_gen/
cd "$HERE"
CONF="$HERE/models.conf"
OUT="${OUT:-$HERE/../exp2_results}"
mkdir -p "$OUT"

# ---- conda (must source before activate on Sherlock) ----
CONDA_BASE="${CONDA_BASE:-/home/groups/kovscek/$USER/miniconda3}"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV:-token-energy-exp2}"

# ---- offline model cache (pre-fetched by download_models.sh on a login node) ----
export HF_HOME="${HF_HOME:-$GROUP_HOME/hf}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-WARNING}"

# ---- vLLM runs in the Apptainer container (Sherlock is glibc 2.17) ----
export VLLM_SIF="${VLLM_SIF:-$GROUP_HOME/vllm.sif}"
export VLLM_BIN="${VLLM_BIN:-$HERE/vllm_apptainer.sh}"
# -e not -f: VLLM_SIF may be a .sif file OR an Apptainer sandbox directory.
if [ ! -e "$VLLM_SIF" ]; then
  echo "[run_exp2] ERROR: VLLM_SIF not found at $VLLM_SIF (run pull_vllm_image.sh / build_vllm_sandbox.sh first)"; exit 1
fi

echo "[run_exp2] TIER=$TIER MODELS='$MODELS' HF_HOME=$HF_HOME VLLM_SIF=$VLLM_SIF"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true

lookup() {  # $1=key -> echoes "hf_id|precision|maxlen|tiers"
  awk -F'|' -v k="$1" '
    /^[[:space:]]*#/ {next} NF<5 {next}
    { gsub(/^[ \t]+|[ \t]+$/,"",$1) }
    $1==k { gsub(/^[ \t]+|[ \t]+$/,"",$2); gsub(/^[ \t]+|[ \t]+$/,"",$3);
            gsub(/^[ \t]+|[ \t]+$/,"",$4); gsub(/^[ \t]+|[ \t]+$/,"",$5);
            print $2"|"$3"|"$4"|"$5; exit }' "$CONF"
}

for key in $MODELS; do
  row="$(lookup "$key")"
  if [ -z "$row" ]; then echo "[run_exp2] SKIP unknown key: $key" >&2; continue; fi
  IFS='|' read -r HF_ID PREC MAXLEN TIERS <<< "$row"
  case " $TIERS " in *" $TIER "*) : ;; *)
      echo "[run_exp2] SKIP $key: not configured for $TIER (tiers: $TIERS)"; continue ;; esac

  echo "=================================================================="
  echo "[run_exp2] $key  ($HF_ID)  precision=$PREC  tier=$TIER"
  SERVER_LOG="$OUT/vllm_${TIER}_${key}.log"

  # start server, wait until healthy, capture pid (last stdout line)
  set +e
  PID="$(MODEL="$HF_ID" PRECISION="$PREC" MAXLEN="$MAXLEN" PORT="$PORT" \
         SERVER_LOG="$SERVER_LOG" bash "$HERE/launch_vllm.sh")"
  rc=$?
  set -e
  if [ $rc -ne 0 ] || [ -z "$PID" ]; then
    echo "[run_exp2] launch failed for $key (rc=$rc); skipping"; continue
  fi

  python "$HERE/bench_sweep.py" --model "$HF_ID" --gpu-type "$TIER" \
         --port "$PORT" --gpu 0 --out-dir "$OUT" || echo "[run_exp2] bench had failures for $key"

  echo "[run_exp2] stopping server pid=$PID"
  kill "$PID" 2>/dev/null || true
  for i in $(seq 1 12); do kill -0 "$PID" 2>/dev/null || break; sleep 2; done
  kill -9 "$PID" 2>/dev/null || true
  sleep 3
done

echo "[run_exp2] aggregating..."
python "$HERE/parse_results.py" --dir "$OUT" || true
echo "[run_exp2] done for tier $TIER"
