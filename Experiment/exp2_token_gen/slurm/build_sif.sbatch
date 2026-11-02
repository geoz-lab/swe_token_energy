#!/bin/bash
# build_sif.sbatch — (optional) convert the vLLM sandbox to a single .sif on a COMPUTE node,
# where there's plenty of RAM and no login watchdog, so mksquashfs won't be killed. No internet
# needed: the source is the local sandbox directory. A single .sif loads faster from Lustre than a
# many-file sandbox, which is nicer for the per-model job loads.
#
#   sbatch --export=ALL,SB=$SCRATCH/vllm_sandbox,SIF=$GROUP_HOME/vllm.sif slurm/build_sif.sbatch
#   # then use VLLM_SIF=$GROUP_HOME/vllm.sif (the scripts' default) — no --export needed afterwards
#
#SBATCH --job-name=build_sif
#SBATCH --output=build_sif_%j.out
#SBATCH --partition=owners
#SBATCH --time=00:40:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
set -euo pipefail
SB="${SB:?set SB to the sandbox dir (e.g. \$SCRATCH/vllm_sandbox)}"
SIF="${SIF:-$GROUP_HOME/vllm.sif}"
export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-$L_SCRATCH/apptainer_tmp}"   # node-local SSD = fast
mkdir -p "$APPTAINER_TMPDIR" "$(dirname "$SIF")"
echo "[build_sif] $SB -> $SIF  (tmp=$APPTAINER_TMPDIR)"
apptainer build --force "$SIF" "$SB"
echo "[build_sif] done: $SIF"
apptainer exec "$SIF" vllm --version || true
