#!/usr/bin/env python3
"""
make_filter.py — turn the sampled task manifest into mini-swe-agent --filter regexes.

mini-swe-agent's swebench runner selects instances with --subset + --filter (regex on instance
id). This writes one anchored regex per benchmark so the run covers EXACTLY our sampled tasks.

    python make_filter.py
    -> data/filter_swe_bench_lite.txt      (regex for the 30 sampled Lite ids)
    -> data/filter_swe_bench_verified.txt  (regex for the 40 sampled Verified ids)
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    manifest = json.loads((HERE / "task_manifest.json").read_text())
    by_bench: dict[str, list[str]] = {}
    for t in manifest["tasks"]:
        by_bench.setdefault(t["benchmark"], []).append(t["instance_id"])
    (HERE / "data").mkdir(exist_ok=True)
    for bench, ids in by_bench.items():
        rgx = "^(" + "|".join(re.escape(i) for i in sorted(ids)) + ")$"
        out = HERE / "data" / f"filter_{bench}.txt"
        out.write_text(rgx)
        print(f"  {bench}: {len(ids)} ids -> {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
