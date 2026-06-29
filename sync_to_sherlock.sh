#!/usr/bin/env bash
# sync_to_sherlock.sh — mirror this local Experiment/ folder to the matching path on Sherlock.
#   local : /Users/geozhang/.../token_energy_paper/Experiment/
#   remote: /home/groups/kovscek/gmzhang/Token_experiment/Experiment/
#
# Usage:
#   ./sync_to_sherlock.sh              # do the sync
#   ./sync_to_sherlock.sh -n           # dry run (preview, change nothing)   [-n == --dry-run]
#   ./sync_to_sherlock.sh --delete     # also delete remote files not present locally (careful!)
# Any extra args are passed straight through to rsync.
set -euo pipefail

LOCAL="/Users/geozhang/Library/CloudStorage/OneDrive-Stanford/2024-Autumn/Research/Projects/token_energy_paper/Experiment/"
HOST="gmzhang@login.sherlock.stanford.edu"
REMOTE_DIR="/home/groups/kovscek/gmzhang/Token_experiment/Experiment"
REMOTE="${HOST}:${REMOTE_DIR}/"

# Excludes: caches, the (un-uploadable) venv, secrets, and remote-generated outputs.
# Note: exp1_results/ IS synced (build_workload.py reads it); exp2_results/ is NOT (it's produced
# on Sherlock — we don't want to clobber the runs). .env is NOT synced (manage keys on Sherlock).
EXCLUDES=(
  --exclude '.git/'
  --exclude '.DS_Store'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.venv/'
  --exclude '.env'
  --exclude '*.key'
  --exclude '.tiktoken_cache/'
  --exclude 'exp2_results/'
  --exclude 'exp2_sanity_check_results/'
  --exclude '*.log'
)

echo "[sync] local : $LOCAL"
echo "[sync] remote: $REMOTE"
echo "[sync] (exp1_results synced; exp2_results, .env, .venv excluded)"

# Multiplex SSH so the mkdir + rsync share ONE connection -> a single Duo/2FA prompt.
CM_OPTS=(-o ControlMaster=auto -o ControlPath="$HOME/.ssh/cm-%r@%h:%p" -o ControlPersist=180)

# Ensure the remote directory tree exists (opens/authenticates the master connection).
ssh "${CM_OPTS[@]}" "$HOST" "mkdir -p '${REMOTE_DIR}'"

rsync -avz --human-readable --partial --progress \
  -e "ssh ${CM_OPTS[*]}" \
  "${EXCLUDES[@]}" \
  "$@" \
  "$LOCAL" "$REMOTE"

echo "[sync] done."
