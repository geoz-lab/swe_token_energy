#!/usr/bin/env bash
# pull_vllm_image.sh — fetch the official vLLM image as an Apptainer .sif on a LOGIN node.
# Sherlock is glibc-2.17, so we run vLLM containerized instead of pip-installing it.
#
#   ./pull_vllm_image.sh                 # -> $GROUP_HOME/vllm.sif from vllm/vllm-openai:latest
#   IMAGE=docker://vllm/vllm-openai:v0.11.0 SIF=$GROUP_HOME/vllm_0_11.sif ./pull_vllm_image.sh
set -euo pipefail

IMAGE="${IMAGE:-docker://vllm/vllm-openai:latest}"
SIF="${SIF:-$GROUP_HOME/vllm.sif}"

# Build/cache on scratch. FORCE these (don't inherit a pre-set /tmp from the shell): mksquashfs
# stages the multi-GB image here, and login-node /tmp is too small/slow (and may get the build
# killed). Override deliberately with PULL_CACHEDIR / PULL_TMPDIR if needed.
export APPTAINER_CACHEDIR="${PULL_CACHEDIR:-$SCRATCH/.apptainer_cache}"
export APPTAINER_TMPDIR="${PULL_TMPDIR:-$SCRATCH/.apptainer_tmp}"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR" "$(dirname "$SIF")"

echo "[pull] image=$IMAGE"
echo "[pull] sif  =$SIF"
echo "[pull] cache=$APPTAINER_CACHEDIR tmp=$APPTAINER_TMPDIR"
apptainer pull --force "$SIF" "$IMAGE"
echo "[pull] done. Set VLLM_SIF=$SIF (run_exp2.sbatch/smoke_test default to \$GROUP_HOME/vllm.sif)."
echo "[pull] sanity: apptainer exec $SIF vllm --version"
apptainer exec "$SIF" vllm --version || true
