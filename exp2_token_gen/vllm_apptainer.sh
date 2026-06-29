#!/usr/bin/env bash
# vllm_apptainer.sh — run the vLLM CLI inside the official vLLM Apptainer image.
# Sherlock is glibc-2.17, so vLLM/torch can't be pip-installed; we run it containerized instead.
# This wrapper makes `vllm_apptainer.sh <args...>` behave like `vllm <args...>` on the host:
#   ./vllm_apptainer.sh serve MODEL --port 8000 ...
#   ./vllm_apptainer.sh bench serve --model MODEL --base-url http://127.0.0.1:8000 ...
#
# Required env:
#   VLLM_SIF   path to the pulled image (e.g. $GROUP_HOME/vllm.sif)
# Optional env:
#   HF_HOME (default $GROUP_HOME/hf), HF_HUB_OFFLINE (default 1), VLLM_EXTRA_BINDS (colon list)
set -euo pipefail

SIF="${VLLM_SIF:?set VLLM_SIF to the vllm .sif path (apptainer pull ... docker://vllm/vllm-openai)}"
HF_HOME="${HF_HOME:-$GROUP_HOME/hf}"

# Bind the storage the job touches into the container. $GROUP_HOME covers the project tree and the
# HF cache (default under it); also bind scratch spaces when present. Apptainer shares the host
# network namespace by default, so a server on 127.0.0.1:PORT inside is reachable on the host.
BINDS=("$GROUP_HOME")
[ -n "${SCRATCH:-}" ] && BINDS+=("$SCRATCH")
[ -n "${L_SCRATCH:-}" ] && [ -d "${L_SCRATCH:-}" ] && BINDS+=("$L_SCRATCH")
case ":${HF_HOME}:" in *":$GROUP_HOME"*) : ;; *) BINDS+=("$HF_HOME") ;; esac
if [ -n "${VLLM_EXTRA_BINDS:-}" ]; then
  IFS=':' read -ra extra <<< "$VLLM_EXTRA_BINDS"; BINDS+=("${extra[@]}")
fi
bind_args=(); for b in "${BINDS[@]}"; do bind_args+=(--bind "$b"); done

# CUDA forward compatibility: the image is built for a newer CUDA (torch cu13/R580) than Sherlock's
# GPU driver (R550 / CUDA 12.4). Prepend the image's compat libcuda (newer userspace driver) ahead
# of the host libcuda that --nv injects, so torch runs against the older host *kernel* driver --
# supported on datacenter GPUs (H100/H200/A100). Set inside the container so we extend ITS
# LD_LIBRARY_PATH, not the host's. Override the compat dir via VLLM_CUDA_COMPAT if it moves.
COMPAT_DIR="${VLLM_CUDA_COMPAT:-/usr/local/cuda/compat}"
exec apptainer exec --nv \
  "${bind_args[@]}" \
  --env HF_HOME="$HF_HOME" \
  --env HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}" \
  --env HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-0}" \
  --env VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-WARNING}" \
  --env CUDA_COMPAT_DIR="$COMPAT_DIR" \
  "$SIF" bash -c 'export LD_LIBRARY_PATH="$CUDA_COMPAT_DIR:${LD_LIBRARY_PATH:-}"; exec vllm "$@"' vllm-compat "$@"
