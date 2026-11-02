#!/usr/bin/env bash
# download_models.sh — pre-fetch Exp-2 weights on a Sherlock LOGIN node (which has internet).
# GPU/compute nodes are offline, so we cache to $GROUP_HOME (persistent, seen by compute nodes)
# and the SLURM job then runs with HF_HUB_OFFLINE=1.
#
#   conda activate token-energy-exp2
#   export HF_HOME=$GROUP_HOME/hf          # or wherever you want the cache
#   # export HF_TOKEN=hf_xxx               # only if you add a gated model (none by default)
#   ./download_models.sh                   # all models in models.conf
#   ./download_models.sh kimi-dev-72b      # just one key
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$HERE/models.conf"

export HF_HOME="${HF_HOME:-$GROUP_HOME/hf}"
# Disable Xet: its in-memory buffering OOM-kills large downloads on Sherlock login nodes
# (per-user memory cgroup). Plain HTTP is low-memory and resumable. Critical for the 72-80B models.
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
mkdir -p "$HF_HOME"
echo "[download] HF_HOME=$HF_HOME (Xet disabled for low-memory login-node downloads)"

want=("$@")  # optional list of keys; empty = all

in_want() {  # $1 = key
  [ ${#want[@]} -eq 0 ] && return 0
  for k in "${want[@]}"; do [ "$k" = "$1" ] && return 0; done
  return 1
}

while IFS='|' read -r key hf_id prec maxlen tiers; do
  key="$(echo "$key" | xargs)"; [ -z "$key" ] && continue
  [ "${key:0:1}" = "#" ] && continue
  hf_id="$(echo "$hf_id" | xargs)"
  in_want "$key" || continue
  echo "[download] $key -> $hf_id"
  # `huggingface-cli` was removed in huggingface_hub>=1.0; the CLI is now `hf`. Our model repos are
  # safetensors-only (no original/ or gguf duplicates), so we fetch the whole snapshot.
  hf download "$hf_id"
done < "$CONF"

echo "[download] done. Cache at $HF_HOME"
