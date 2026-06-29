#!/usr/bin/env python3
"""
sample_swelancer.py — stratified sample of SWE-Lancer IC SWE tasks (Terminal-Bench packaging).

SWE-Lancer (DCAgent2/swe-lancer on HF) ships each task as a self-contained single-container env:
  <id>_1 / <id>        = IC SWE  (write code in /app/expensify — the agentic coding tasks)
  <id>-manager-0       = Manager (choose between proposals — single-turn, low-token; excluded by default)
Price is in the issue title (e.g. "[$4000]"), not task.toml. We sample IC tasks stratified by price band.

    python sample_swelancer.py                 # 20 IC tasks, stratified by price tercile
    python sample_swelancer.py --n 20 --include-manager

Output:
    swelancer_manifest.json   per-task: instance_id, variant, price, band, image (docker://...)
    data/filter_swe_lancer.txt        regex of sampled ids (parity with make_filter)
    data/swelancer_images.txt         one `docker://swelancer/swelancer_x86_<id>:releasev1` per line (for apptainer pull)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sample_tasks import allocate, stratified_sample  # reuse the SWE-bench sampler logic

REPO = "DCAgent2/swe-lancer"
TREE = f"https://huggingface.co/api/datasets/{REPO}/tree/main?recursive=true"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main"
PRICE_RE = re.compile(r"\[\s*\$([0-9][0-9,]*)\s*\]")


def _fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def list_tasks():
    tree = json.loads(_fetch(TREE))
    dirs = sorted({p.split("/")[0] for p in (e.get("path", "") for e in tree) if "/" in p})
    ic = [d for d in dirs if "manager" not in d]
    mgr = [d for d in dirs if "manager" in d]
    return ic, mgr


def price_of(task: str):
    try:
        m = PRICE_RE.findall(_fetch(f"{RAW}/{task}/instruction.md"))
    except Exception:
        return None
    return max((int(x.replace(",", "")) for x in m), default=None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--include-manager", action="store_true", help="also allow Manager tasks (not agentic)")
    ap.add_argument("--out", type=Path, default=HERE / "swelancer_manifest.json")
    args = ap.parse_args(argv)

    print("Listing SWE-Lancer tasks …")
    ic, mgr = list_tasks()
    cand = ic + (mgr if args.include_manager else [])
    print(f"  IC SWE: {len(ic)} | Manager: {len(mgr)} | sampling from: {len(cand)}")

    print(f"Fetching prices for {len(cand)} tasks (from issue titles) …")
    rows = []
    for i, t in enumerate(cand, 1):
        p = price_of(t)
        rows.append({"id": t, "price": p, "variant": "manager" if "manager" in t else "ic_swe"})
        if i % 20 == 0:
            print(f"    {i}/{len(cand)}")

    priced = [r["price"] for r in rows if r["price"]]
    if len(set(priced)) >= 3:
        import statistics
        q1, q2 = statistics.quantiles(priced, n=3)[:2]
        band = lambda p: "na" if not p else ("low" if p <= q1 else ("mid" if p <= q2 else "high"))
    else:
        band = lambda p: "all"
    for r in rows:
        r["band"] = (r["variant"] + ":" + band(r["price"]))

    sampled, alloc, sizes = stratified_sample(rows, "id", lambda r: r["band"], args.n, args.seed, "swe_lancer")
    meta = {r["id"]: r for r in rows}
    tasks = [{"benchmark": "swe_lancer", "instance_id": i, "stratum": k,
              "variant": meta[i]["variant"], "price": meta[i]["price"],
              "image": f"docker://swelancer/swelancer_x86_{i}:releasev1"} for (k, i) in sampled]

    args.out.write_text(json.dumps({"seed": args.seed, "n_sampled": len(tasks),
                                    "allocation": alloc, "strata_sizes": sizes, "tasks": tasks}, indent=2))
    (HERE / "data").mkdir(exist_ok=True)
    ids = sorted(t["instance_id"] for t in tasks)
    (HERE / "data" / "filter_swe_lancer.txt").write_text("^(" + "|".join(re.escape(i) for i in ids) + ")$")
    (HERE / "data" / "swelancer_images.txt").write_text("\n".join(t["image"] for t in tasks) + "\n")

    print(f"\n  sampled {len(tasks)} tasks  (allocation: {alloc})")
    for t in tasks:
        print(f"    {t['instance_id']:<14} {t['variant']:<8} ${t['price']}  {t['image']}")
    print(f"\n  → {args.out}\n  → data/filter_swe_lancer.txt  → data/swelancer_images.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
