#!/usr/bin/env python3
"""
download_datasets.py — fetch the Experiment-1 benchmark datasets and cache them locally.

Saves each as parquet (compact, full fields) + a lightweight CSV index (instance_id, repo,
difficulty) for quick inspection, under exp1_token_consumption/data/. Idempotent: skips files
that exist unless --force. After this, sample_tasks.py --local-dir data can sample offline.

    python download_datasets.py
    python download_datasets.py --force

SWE-Lancer is not fetched here — pass its source to sample_tasks.py directly (unstable schema).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

DATASETS = {
    "swe_bench_lite":     ("princeton-nlp/SWE-bench_Lite", "test"),
    "swe_bench_verified": ("princeton-nlp/SWE-bench_Verified", "test"),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    args = ap.parse_args(argv)

    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: `datasets` not installed. Run:  pip install datasets", file=sys.stderr)
        return 1
    import csv

    DATA.mkdir(exist_ok=True)
    for name, (hf_id, split) in DATASETS.items():
        pq = DATA / f"{name}.parquet"
        idx = DATA / f"{name}.index.csv"
        if pq.exists() and not args.force:
            print(f"  {name}: cached ({pq.name}) — skip (use --force to refresh)")
            continue
        print(f"  {name}: downloading {hf_id} [{split}] …")
        ds = load_dataset(hf_id, split=split)
        ds.to_parquet(pq)
        with open(idx, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["instance_id", "repo", "difficulty"])
            for r in ds:
                w.writerow([r.get("instance_id"), r.get("repo"), r.get("difficulty", "")])
        # quick distribution print
        repos = {}
        diffs = {}
        for r in ds:
            repos[r.get("repo")] = repos.get(r.get("repo"), 0) + 1
            d = r.get("difficulty") or "(none)"
            diffs[d] = diffs.get(d, 0) + 1
        print(f"      {len(ds)} instances · {len(repos)} repos · {pq.stat().st_size//1024} KB")
        if any(k != "(none)" for k in diffs):
            print(f"      difficulty: {dict(sorted(diffs.items()))}")
    print(f"\n  → saved under {DATA}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
