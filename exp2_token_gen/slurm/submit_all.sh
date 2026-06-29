#!/usr/bin/env bash
# submit_all.sh — submit one Exp-2 GPU job per tier (A100, H100, H200) on the owners partition.
# Each job loops the models configured for that tier in models.conf.
# Run from exp2_token_gen/ AFTER download_models.sh has populated $HF_HOME on a login node.
#
#   cd exp2_token_gen && ./slurm/submit_all.sh           # all three tiers
#   ./slurm/submit_all.sh H100                            # just one tier
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # exp2_token_gen/
PART="${PART:-owners}"
# Container image/sandbox (a .sif file OR a sandbox dir). Override by exporting VLLM_SIF.
VLLM_SIF="${VLLM_SIF:-$GROUP_HOME/vllm.sif}"

# BF16 models run on every tier; FP8 (72-80B) only on Hopper (H100/H200). run_exp2.sbatch also
# self-skips any model whose 'tiers' column excludes the tier, so these lists can be permissive.
BF16="gpt-oss-20b qwen3-coder-30b qwen3-32b"
HOPPER="$BF16 kimi-dev-72b qwen3-coder-next"

declare -A CONSTRAINT=(
  [A100]="GPU_SKU:A100_SXM4&GPU_MEM:80GB"
  [H100]="GPU_SKU:H100_SXM5"
  [H200]="GPU_SKU:H200_SXM5"
)
declare -A MODELS=(
  [A100]="$BF16"
  [H100]="$HOPPER"
  [H200]="$HOPPER"
)

tiers=("$@"); [ ${#tiers[@]} -eq 0 ] && tiers=(A100 H100 H200)

for TIER in "${tiers[@]}"; do
  C="${CONSTRAINT[$TIER]:-}"; M="${MODELS[$TIER]:-}"
  if [ -z "$C" ]; then echo "unknown tier: $TIER (use A100|H100|H200)"; continue; fi
  echo "[submit] tier=$TIER  constraint='$C'  models='$M'"
  sbatch -p "$PART" --gres=gpu:1 -C "$C" \
         --job-name="exp2_${TIER}" \
         --export=ALL,TIER="$TIER",MODELS="$M",VLLM_SIF="$VLLM_SIF" \
         "$HERE/slurm/run_exp2.sbatch"
done
echo "[submit] submitted. Track with: squeue -u \$USER ; tail -f exp2_token_gen/exp2_exp2_*.out"
