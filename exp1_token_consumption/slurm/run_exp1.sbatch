#!/bin/bash
# Experiment 1 — agentic token consumption on Sherlock (CPU-only; NO GPU).
# Runs mini-swe-agent over our sampled tasks for ONE (model, subset) via Apptainer.
#
# Submit (one per model × subset), passing config through --export:
#   sbatch --export=ALL,PROJ=$PWD,MODEL=anthropic/claude-opus-4-8,SUBSET=lite,\
#FILTERFILE=$PWD/data/filter_swe_bench_lite.txt,OUTDIR=$SCRATCH/exp1/opus_lite,\
#COSTLIMIT=350,WORKERS=4 slurm/run_exp1.sbatch
#
#SBATCH --partition=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --job-name=exp1
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail

: "${PROJ:?set PROJ to the Experiment dir}"
: "${MODEL:?set MODEL (litellm id, e.g. anthropic/claude-opus-4-8)}"
: "${SUBSET:?set SUBSET (lite|verified)}"
: "${FILTERFILE:?set FILTERFILE}"
: "${OUTDIR:?set OUTDIR}"
WORKERS="${WORKERS:-4}"
COSTLIMIT="${COSTLIMIT:-50}"
ENVCLASS="${ENVCLASS:-singularity}"        # singularity (Sherlock) | modal (cloud fallback) | docker
CONFIG="${CONFIG:-$PROJ/exp1_token_consumption/swebench.yaml}"

# Apptainer (no Docker on Sherlock). Cache images on scratch.
module load system apptainer 2>/dev/null || module load singularity 2>/dev/null || true
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-$SCRATCH/apptainer_cache}"
mkdir -p "$APPTAINER_CACHEDIR" "$OUTDIR"

# Conda env + API keys. A batch shell needs the conda hook sourced before activate, or `python`
# silently resolves to base (env shows active but PATH isn't updated).
CONDA_BASE="${CONDA_BASE:-/home/groups/kovscek/$USER/miniconda3}"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV:-token-energy-exp1}"
python -c "import sys; assert 'envs/' in sys.executable, sys.executable" || { echo "conda env not active: $(which python)"; exit 1; }
set -a; source "$PROJ/.env"; set +a        # ANTHROPIC/OPENAI/GOOGLE keys

# Per-run cost ceiling = the account cap (hard stop).
export MSWEA_GLOBAL_COST_LIMIT="$COSTLIMIT"

echo "model=$MODEL subset=$SUBSET workers=$WORKERS cost_limit=$COSTLIMIT out=$OUTDIR"
mini-extra swebench \
  -c "$CONFIG" \
  --model "$MODEL" \
  --subset "$SUBSET" --split test \
  --environment-class "$ENVCLASS" \
  --filter "$(cat "$FILTERFILE")" \
  --workers "$WORKERS" \
  -o "$OUTDIR"

echo "done. predictions: $OUTDIR/preds.json ; trajectories: $OUTDIR/*/*.traj.json"
