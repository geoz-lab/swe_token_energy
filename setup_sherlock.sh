#!/bin/bash
# setup_sherlock.sh — one-shot Experiment-1 setup on Sherlock (run from the Experiment/ dir,
# on a LOGIN node, which has internet for pip + dataset download). Idempotent.
#   bash setup_sherlock.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "[1/5] python module"
module load python/3.12 2>/dev/null || module load python/3.12.1 2>/dev/null || module load python 2>/dev/null || true
python3 --version

echo "[2/5] venv + install (rebuilt on Linux; a Mac-built .venv won't work)"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -U pip >/dev/null
pip install -r exp1_token_consumption/requirements-sherlock.txt

echo "[3/5] datasets + task filters"
cd exp1_token_consumption
[ -f data/swe_bench_lite.parquet ] || python download_datasets.py
python make_filter.py
cd ..

echo "[4/5] apptainer cache + availability"
export APPTAINER_CACHEDIR="${SCRATCH:-/scratch/users/$USER}/apptainer_cache"
mkdir -p "$APPTAINER_CACHEDIR"
echo "  APPTAINER_CACHEDIR=$APPTAINER_CACHEDIR"
module load system apptainer 2>/dev/null || module load singularity 2>/dev/null || true
if command -v apptainer >/dev/null; then apptainer --version
else echo "  WARN: apptainer not on PATH here — the module name may differ; check on a compute node"; fi

echo "[5/5] keys"
if [ -f .env ]; then chmod 600 .env; echo "  .env present (chmod 600)"; else echo "  WARN: .env missing — copy your API keys into Experiment/.env"; fi

cat <<'EOF'

Setup done. Next:
  1) salloc -p normal -c 2 --mem=4G -t 0:20:00      # then RUNBOOK Step 0:
       curl -sI https://api.anthropic.com | head -1 # must return an HTTP status
  2) source .venv/bin/activate && set -a; source .env; set +a
  3) Step 5 pilot (single task) — see RUNBOOK_exp1.md
EOF
