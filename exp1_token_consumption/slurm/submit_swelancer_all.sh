#!/bin/bash
# submit_swelancer_all.sh — SWE-Lancer (full 20 IC tasks) for all 3 models, one job each.
# Run ONLY after the single-task pilot validates the path.
#
#   ./submit_swelancer_all.sh            # all 3 models, full 20 each
#   ./submit_swelancer_all.sh opus       # just one model
#   DRYRUN=1 ./submit_swelancer_all.sh   # preview
set -euo pipefail

unset ONLY   # critical: a leftover exported ONLY would otherwise run just 1 task via --export=ALL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="${PROJ:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
SCRATCH="${SCRATCH:-/scratch/users/$USER}"

MODELS=(
  "opus:anthropic/claude-opus-4-8"
  "gpt54:openai/gpt-5.4"
  "gemini:gemini/gemini-3.1-pro-preview"
)
WANT="${1:-all}"

for entry in "${MODELS[@]}"; do
  IFS=":" read -r tag model <<<"$entry"
  [[ "$WANT" != "all" && "$WANT" != "$tag" ]] && continue
  out="$SCRATCH/exp1/swelancer_${tag}"
  exports="ALL,PROJ=$PROJ,MODEL=$model,OUT=$out"     # no ONLY → full sampled set
  cmd=(sbatch --job-name="exp1-swelancer-${tag}" --export="$exports" "$SCRIPT_DIR/run_swelancer.sbatch")
  if [[ "${DRYRUN:-0}" == "1" ]]; then printf '%q ' "${cmd[@]}"; echo; else "${cmd[@]}"; fi
done
echo "submitted SWE-Lancer (WANT=$WANT). Monitor: squeue -u $USER"
