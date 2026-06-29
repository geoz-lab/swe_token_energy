#!/usr/bin/env bash
# launch_vllm.sh — start a single-GPU vLLM OpenAI server and wait until it is healthy.
# Sourced/called by slurm/run_exp2.sbatch. Prints the server PID on stdout (last line).
#
#   MODEL=Qwen/Qwen3.5-9B PORT=8000 DTYPE=bfloat16 MAXLEN=40960 ./launch_vllm.sh
#
# Env knobs (with defaults):
#   MODEL        HF id to serve                         (required)
#   PORT         OpenAI server port                     (8000)
#   PRECISION    bf16 | fp8   (fp8 = dynamic W8A8, Hopper-only)   (bf16)
#   MAXLEN       --max-model-len                         (16384; covers 8k input + 1k output)
#   GPU_MEM_UTIL --gpu-memory-utilization                (0.90)
#   PREFIX_CACHE enable automatic prefix caching         (1 -> on; agentic prefix reuse)
#   SERVER_LOG   server log file                         ($PWD/vllm_server.log)
set -euo pipefail

MODEL="${MODEL:?set MODEL to an HF id}"
PORT="${PORT:-8000}"
PRECISION="${PRECISION:-bf16}"
# How to invoke vLLM. Native install -> "vllm". On Sherlock (glibc 2.17) point this at the
# Apptainer wrapper:  VLLM_BIN=./vllm_apptainer.sh
VLLM_BIN="${VLLM_BIN:-vllm}"
MAXLEN="${MAXLEN:-16384}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
PREFIX_CACHE="${PREFIX_CACHE:-1}"
SERVER_LOG="${SERVER_LOG:-$PWD/vllm_server.log}"

# Precision -> vLLM flags. fp8 = dynamic per-tensor W8A8 quantization of BF16 weights at load
# time (needs Hopper FP8 tensor cores: H100/H200, NOT A100). Lets a 72-80B model fit one 80GB
# GPU. If an official *-FP8 checkpoint is used as MODEL instead, set PRECISION=bf16 (vLLM detects
# the quant from the checkpoint config) to avoid double-quantizing.
# Use the checkpoint's native dtype ("auto"): bf16 for the dense/Qwen models, mxfp4 for gpt-oss.
# fp8 adds dynamic W8A8 quantization (Hopper).
case "$PRECISION" in
  bf16) DTYPE_FLAGS=(--dtype auto) ;;
  fp8)  DTYPE_FLAGS=(--dtype auto --quantization fp8) ;;
  *) echo "[launch_vllm] unknown PRECISION=$PRECISION (use bf16|fp8)" >&2; exit 2 ;;
esac

# Keep HF model cache on fast storage; hf_transfer for quick first download.
export HF_HOME="${HF_HOME:-${L_SCRATCH:-/tmp}/hf}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"
mkdir -p "$HF_HOME"

# Prefix caching is ON by default in the vLLM V1 engine, so only pass a flag to DISABLE it
# (avoids depending on a possibly-renamed --enable flag).
pc_flag=""
[ "$PREFIX_CACHE" = "0" ] && pc_flag="--no-enable-prefix-caching"

# Tool calling: the Exp-2 throughput benchmark sends plain completions (no tools), but the sanity
# check drives an AGENT that uses native function/tool calls. vLLM rejects tool requests with a 400
# unless the server is launched with auto tool choice + a model-specific parser. Set TOOL_CALL_PARSER
# (e.g. qwen3_coder / hermes) to enable it.
tool_flags=()
if [ -n "${TOOL_CALL_PARSER:-}" ]; then
  tool_flags=(--enable-auto-tool-choice --tool-call-parser "$TOOL_CALL_PARSER")
fi

echo "[launch_vllm] MODEL=$MODEL PORT=$PORT PRECISION=$PRECISION MAXLEN=$MAXLEN HF_HOME=$HF_HOME TOOLS=${TOOL_CALL_PARSER:-none}" >&2
echo "[launch_vllm] log -> $SERVER_LOG" >&2

# Single GPU (G=1): tensor-parallel-size 1. (Request logging is off by default in vLLM V1.)
$VLLM_BIN serve "$MODEL" \
  --host 127.0.0.1 --port "$PORT" \
  "${DTYPE_FLAGS[@]}" \
  --tensor-parallel-size 1 \
  --max-model-len "$MAXLEN" \
  --gpu-memory-utilization "$GPU_MEM_UTIL" \
  $pc_flag \
  "${tool_flags[@]}" \
  > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
echo "[launch_vllm] server pid=$SERVER_PID; waiting for /health ..." >&2

# Wait up to 20 min for weights download + load.
for i in $(seq 1 240); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "[launch_vllm] server died during startup; tail of log:" >&2
    tail -n 40 "$SERVER_LOG" >&2
    exit 1
  fi
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "[launch_vllm] healthy after ~$((i*5))s" >&2
    echo "$SERVER_PID"
    exit 0
  fi
  sleep 5
done

echo "[launch_vllm] timed out waiting for /health; tail of log:" >&2
tail -n 40 "$SERVER_LOG" >&2
kill "$SERVER_PID" 2>/dev/null || true
exit 1
