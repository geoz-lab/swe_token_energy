#!/bin/bash
# submit_all.sh — submit the full Experiment-1 matrix: 3 models × {lite, verified} = 6 CPU jobs.
#
#   ./submit_all.sh                 # submit all 6
#   ./submit_all.sh opus            # only the opus jobs (lite+verified)
#   DRYRUN=1 ./submit_all.sh        # print the sbatch commands without submitting
#   WORKERS=8 ./submit_all.sh       # override worker threads
#
# Requires: make_filter.py already run (data/filter_swe_bench_{lite,verified}.txt present),
#           .venv + .env set up per RUNBOOK_exp1.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="${PROJ:-$(cd "$SCRIPT_DIR/../.." && pwd)}"      # Experiment/
EXP1="$PROJ/exp1_token_consumption"
SCRATCH="${SCRATCH:-/scratch/users/$USER}"
WORKERS="${WORKERS:-4}"

# tag : litellm-model-id : per-account-cost-cap (USD)
MODELS=(
  "opus:anthropic/claude-opus-4-8:350"
  "gpt54:openai/gpt-5.4:200"
  "gemini:gemini/gemini-3.1-pro-preview:200"
)
SUBSETS=(lite verified)
WANT="${1:-all}"

for entry in "${MODELS[@]}"; do
  IFS=":" read -r tag model cap <<<"$entry"
  [[ "$WANT" != "all" && "$WANT" != "$tag" ]] && continue
  for subset in "${SUBSETS[@]}"; do
    filter="$EXP1/data/filter_swe_bench_${subset}.txt"
    outdir="$SCRATCH/exp1/${tag}_${subset}"
    if [[ ! -f "$filter" ]]; then
      echo "MISSING filter $filter — run: (cd $EXP1 && python make_filter.py)" >&2
      exit 1
    fi
    exports="ALL,PROJ=$PROJ,MODEL=$model,SUBSET=$subset,FILTERFILE=$filter,OUTDIR=$outdir,COSTLIMIT=$cap,WORKERS=$WORKERS"
    cmd=(sbatch --job-name="exp1-${tag}-${subset}" --export="$exports" "$SCRIPT_DIR/run_exp1.sbatch")
    if [[ "${DRYRUN:-0}" == "1" ]]; then
      printf '%q ' "${cmd[@]}"; echo
    else
      "${cmd[@]}"
    fi
  done
done
echo "submitted (WANT=$WANT, workers=$WORKERS). Monitor: squeue -u $USER"
