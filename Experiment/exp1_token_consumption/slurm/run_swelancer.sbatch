#!/bin/bash
# Experiment 1 — SWE-Lancer (20 IC tasks) via Apptainer on Sherlock (CPU; NO GPU).
# Heavier than SWE-bench: each task is a multi-GB single-container image built into a writable
# Apptainer sandbox, so we give more memory/scratch and run sequentially.
#
# PILOT one task first (validate the whole path before the full set):
#   sbatch --export=ALL,PROJ=$PWD,MODEL=anthropic/claude-opus-4-8,\
#OUT=$SCRATCH/exp1/swelancer_pilot,ONLY=13066_1 slurm/run_swelancer.sbatch
#
# Full sampled set for one model:
#   sbatch --export=ALL,PROJ=$PWD,MODEL=anthropic/claude-opus-4-8,OUT=$SCRATCH/exp1/swelancer_opus \
#     slurm/run_swelancer.sbatch
#
#SBATCH --partition=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --job-name=exp1-swelancer
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail

: "${PROJ:?set PROJ to the Experiment dir}"
: "${MODEL:?set MODEL (litellm id)}"
: "${OUT:?set OUT (output dir)}"
ONLY="${ONLY:-}"

# Apptainer + big scratch tmp (sandboxes are multi-GB; /tmp is too small).
module load system apptainer 2>/dev/null || module load singularity 2>/dev/null || true
export MSWEA_SINGULARITY_EXECUTABLE=apptainer
# Build the writable sandbox on NODE-LOCAL SSD ($L_SCRATCH), NOT Lustre ($SCRATCH): `build --sandbox`
# creates a dir with millions of small files, and Lustre metadata ops make that ~40 min/image. Local
# SSD does it in minutes. $L_SCRATCH is per-node + wiped at job end (fine — we save the .traj to $OUT).
LOCAL_TMP="${L_SCRATCH:-$SCRATCH/swelancer_tmp}"
export TMPDIR="$LOCAL_TMP/swelancer"                       # SingularityEnvironment builds sandboxes here
export APPTAINER_TMPDIR="$TMPDIR"
export APPTAINER_CACHEDIR="$SCRATCH/apptainer_cache"       # layer cache can stay on Lustre (few large files)
mkdir -p "$APPTAINER_CACHEDIR" "$TMPDIR" "$OUT"

# Conda env (same robust activation as run_exp1.sbatch).
CONDA_BASE="${CONDA_BASE:-/home/groups/kovscek/$USER/miniconda3}"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV:-token-energy-exp1}"
python -c "import sys; assert 'envs/' in sys.executable, sys.executable" || { echo "env not active"; exit 1; }
set -a; source "$PROJ/.env"; set +a

cd "$PROJ/exp1_token_consumption"
echo "model=$MODEL out=$OUT only=${ONLY:-<all>} tmpdir=$TMPDIR"
python run_swelancer.py --model "$MODEL" --out "$OUT" ${ONLY:+--only "$ONLY"}

echo "done. parse with: python parse_trajectory.py --runs-dir $OUT --model ${MODEL##*/}"
