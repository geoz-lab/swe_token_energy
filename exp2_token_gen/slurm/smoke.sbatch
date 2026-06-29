#!/bin/bash
# smoke.sbatch — run smoke_test.sh on a GPU node (owners forbids interactive salloc).
# Pass partition/constraint on the command line; pick the model/tier via --export.
#
#   cd exp2_token_gen
#   sbatch -p owners --gres=gpu:1 -C "GPU_SKU:H100_SXM5" \
#          --export=ALL,SMOKE_KEY=gpt-oss-20b,SMOKE_TIER=H100 slurm/smoke.sbatch
#   tail -f exp2_smoke_*.out
#
#SBATCH --job-name=exp2_smoke
#SBATCH --output=exp2_smoke_%j.out
#SBATCH --time=00:40:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export SMOKE_KEY="${SMOKE_KEY:-gpt-oss-20b}"
export SMOKE_TIER="${SMOKE_TIER:-H100}"
exec bash "$SLURM_SUBMIT_DIR/smoke_test.sh" "$SMOKE_KEY" "$SMOKE_TIER"
