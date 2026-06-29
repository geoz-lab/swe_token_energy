#!/usr/bin/env bash
# build_vllm_sandbox.sh — build the vLLM image as an Apptainer SANDBOX (directory) on a LOGIN node.
#
# Why a sandbox instead of `apptainer pull` (a .sif): pulling a .sif runs mksquashfs to compress
# the ~9 GB image, which is memory-heavy and gets SIGKILL'd (exit 137) by the login-node watchdog.
# A sandbox is the uncompressed, extracted layers — no mksquashfs — so it builds without being
# killed, and `apptainer exec <sandbox-dir> ...` works exactly like a .sif.
#
#   ./build_vllm_sandbox.sh                 # -> $SCRATCH/vllm_sandbox  (set VLLM_SIF to this)
#   IMAGE=docker://vllm/vllm-openai:v0.11.0 DEST=$SCRATCH/vllm_sb ./build_vllm_sandbox.sh
#
# Then:  export VLLM_SIF=$SCRATCH/vllm_sandbox   (pass via --export to the sbatch jobs)
set -euo pipefail

IMAGE="${IMAGE:-docker://vllm/vllm-openai:latest}"
DEST="${DEST:-$SCRATCH/vllm_sandbox}"

# Reuse the already-downloaded blobs; keep any scratch work off login /tmp.
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-$SCRATCH/.apptainer}"
export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-$SCRATCH/.apptainer_tmp}"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR" "$(dirname "$DEST")"

echo "[sandbox] image=$IMAGE"
echo "[sandbox] dest =$DEST"
echo "[sandbox] cache=$APPTAINER_CACHEDIR tmp=$APPTAINER_TMPDIR"
apptainer build --force --sandbox "$DEST" "$IMAGE"

echo "[sandbox] done. Set VLLM_SIF=$DEST"
echo "[sandbox] sanity: apptainer exec $DEST vllm --version"
apptainer exec "$DEST" vllm --version || true
