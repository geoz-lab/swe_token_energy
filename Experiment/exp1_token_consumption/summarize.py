#!/usr/bin/env python3
"""summarize.py — per-model summary of exp1_results/exp1_raw.csv (run with no args; avoids long one-liners)."""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else \
      Path(__file__).resolve().parent.parent / "exp1_results" / "exp1_raw.csv"


def main():
    if not CSV.exists():
        print(f"no CSV at {CSV}", file=sys.stderr)
        return 1
    # benchmark inferred from instance-id shape: SWE-bench ids contain "__" (repo__repo-N),
    # SWE-Lancer ids are numeric (e.g. 13066_1). Keep them separate — different scale + methodology.
    def bench(iid: str) -> str:
        return "swe-bench" if "__" in iid else "swe-lancer"

    by = defaultdict(list)
    for r in csv.DictReader(open(CSV)):
        by[(bench(r["instance_id"]), r["model"])].append(r)

    print(f"\n{CSV}  ({sum(len(v) for v in by.values())} task-runs)\n")
    hdr = f"{'benchmark':<12}{'model':<26}{'n':>4}{'tok/task(mean)':>16}{'tok/task(med)':>15}{'$/task':>9}{'$tot':>9}{'calls':>7}{'retry':>7}"
    print(hdr); print("-" * len(hdr))
    for key in sorted(by):
        b, m = key
        rows = by[key]
        tok = [int(r["total_tokens"]) for r in rows]
        cost = [float(r["cost_usd"]) for r in rows if r["cost_usd"] not in ("", None)]
        calls = [int(r["api_calls"]) for r in rows if r["api_calls"] not in ("", None)]
        retry = [float(r["retry_frac"]) for r in rows if r.get("retry_frac") not in ("", None)]
        resolved = [r.get("resolved") for r in rows if r.get("resolved") not in ("", None)]
        rr = ""
        if resolved:
            n_res = sum(1 for x in resolved if str(x).lower() in ("true", "1", "resolved"))
            rr = f"  resolved {n_res}/{len(resolved)}"
        print(f"{b:<12}{m:<26}{len(rows):>4}{statistics.mean(tok):>16,.0f}{statistics.median(tok):>15,.0f}"
              f"{(statistics.mean(cost) if cost else 0):>9.3f}{sum(cost):>9.2f}"
              f"{(statistics.mean(calls) if calls else 0):>7.0f}{(statistics.mean(retry) if retry else 0):>7.2f}{rr}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
