#!/usr/bin/env bash
# smoke_test.sh — fast end-to-end validation of the Exp-2 pipeline on ONE model / ONE GPU.
# Runs a deliberately tiny benchmark (short input/output, few prompts) so it finishes in ~2-3 min,
# then asserts a θ_GPU row landed in exp2_results/exp2_raw.csv. Use it before submit_all.sh.
#
# owners forbids interactive jobs, so submit this via sbatch (see slurm/smoke.sbatch):
#   sbatch -p owners --gres=gpu:1 -C "GPU_SKU:H100_SXM5" -t 0:30:00 \
#          --export=ALL,SMOKE_KEY=gpt-oss-20b,SMOKE_TIER=H100 slurm/smoke.sbatch
# (Or run directly if you already hold a GPU node: ./smoke_test.sh <model-key> <tier>.)
#
# Prereqs: conda env built, vllm.sif pulled, and the model downloaded (./download_models.sh <key>).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

KEY="${1:-${SMOKE_KEY:-gpt-oss-20b}}"
TIER="${2:-${SMOKE_TIER:-SMOKE}}"
PORT="${PORT:-8765}"
OUT="${OUT:-$HERE/../exp2_results}"
mkdir -p "$OUT"

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
grn()  { printf '\033[32m%s\033[0m\n' "$*"; }

# ---- conda ----
CONDA_BASE="${CONDA_BASE:-/home/groups/kovscek/$USER/miniconda3}"
# shellcheck disable=SC1091
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV:-token-energy-exp2}"

export HF_HOME="${HF_HOME:-$GROUP_HOME/hf}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-WARNING}"
export VLLM_SIF="${VLLM_SIF:-$GROUP_HOME/vllm.sif}"
export VLLM_BIN="${VLLM_BIN:-$HERE/vllm_apptainer.sh}"

echo "[smoke] key=$KEY tier=$TIER port=$PORT HF_HOME=$HF_HOME VLLM_SIF=$VLLM_SIF"
# -e not -f: VLLM_SIF may be a .sif file OR an Apptainer sandbox directory.
[ -e "$VLLM_SIF" ] || { red "[smoke] VLLM_SIF not found: $VLLM_SIF (build_vllm_sandbox.sh / pull_vllm_image.sh)"; exit 2; }
if ! command -v nvidia-smi >/dev/null || ! nvidia-smi >/dev/null 2>&1; then
  red "[smoke] no visible GPU — run this inside a GPU allocation (salloc ... --gres=gpu:1)"; exit 2
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# ---- resolve model from models.conf ----
row="$(awk -F'|' -v k="$KEY" '
  /^[[:space:]]*#/ {next} NF<5 {next} { gsub(/^[ \t]+|[ \t]+$/,"",$1) }
  $1==k { for(i=2;i<=5;i++) gsub(/^[ \t]+|[ \t]+$/,"",$i); print $2"|"$3"|"$4; exit }' models.conf)"
if [ -z "$row" ]; then red "[smoke] unknown model key: $KEY (see models.conf)"; exit 2; fi
IFS='|' read -r HF_ID PREC MAXLEN <<< "$row"
echo "[smoke] model=$HF_ID precision=$PREC"

SERVER_LOG="$OUT/vllm_smoke_${KEY}.log"
PID=""
cleanup() { [ -n "$PID" ] && kill "$PID" 2>/dev/null; [ -n "$PID" ] && { sleep 2; kill -9 "$PID" 2>/dev/null; }; }
trap cleanup EXIT

# ---- 1) launch server ----
echo "[smoke] launching vLLM (first load can take a few min)..."
PID="$(MODEL="$HF_ID" PRECISION="$PREC" MAXLEN="${MAXLEN}" PORT="$PORT" \
       SERVER_LOG="$SERVER_LOG" bash "$HERE/launch_vllm.sh")"
if [ -z "$PID" ]; then red "[smoke] server failed to come up; see $SERVER_LOG"; exit 1; fi
grn "[smoke] server healthy (pid=$PID)"

# ---- 2) tiny benchmark: small input/output, 2 quick cells ----
python "$HERE/bench_sweep.py" --model "$HF_ID" --gpu-type "$TIER" --port "$PORT" --gpu 0 \
  --out-dir "$OUT" --input-lens 2048 --concurrencies 1 4 --output-len 128 \
  --min-prompts 8 --prompts-per-conc 2
bench_rc=$?

# ---- 3) aggregate ----
python "$HERE/parse_results.py" --dir "$OUT" >/dev/null

# ---- 4) assert a θ_GPU row exists for this model with theta>0 ----
base="${HF_ID##*/}"
ok="$(awk -F',' -v m="$base" 'NR>1 && index($3,m)>0 && ($12+0)>0 {c++} END{print c+0}' "$OUT/exp2_raw.csv")"
echo
if [ "$bench_rc" -eq 0 ] && [ "${ok:-0}" -ge 1 ]; then
  grn "[smoke] PASS — $ok cell(s) with θ_GPU>0 for $base in exp2_raw.csv"
  awk -F',' -v m="$base" 'NR==1 || index($3,m)>0' "$OUT/exp2_raw.csv" | column -t -s,
  exit 0
else
  red "[smoke] FAIL — bench_rc=$bench_rc, valid θ_GPU rows=$ok. Check $SERVER_LOG and the bench output above."
  exit 1
fi
