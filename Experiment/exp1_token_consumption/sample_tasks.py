#!/usr/bin/env python3
"""
sample_tasks.py — deterministic stratified sampler for Experiment 1.

Locks a fixed task manifest sampled from three SWE benchmarks, reused across ALL models so
every model is graded on the *same* tasks (paired comparison). Sampling is seeded and
reproducible: re-running with the same --seed yields the identical manifest.

Default plan (PLAN.md §1.4):
    SWE-bench Lite      30   stratified by repository
    SWE-bench Verified  40   stratified by annotated difficulty (falls back to repo)
    SWE-Lancer          20   stratified by task type × price band
    ───────────────────────
    ≈ 90 tasks

Usage:
    python sample_tasks.py                              # full 90-task manifest
    python sample_tasks.py --lite-n 20 --verified-n 25 --lancer-n 15   # 60-task trim
    python sample_tasks.py --lancer-source ./swelancer_tasks.jsonl     # local SWE-Lancer
    python sample_tasks.py --self-test                 # offline: validate allocation math
    python sample_tasks.py --dry-run                   # print config, don't download

Output:
    task_manifest.json   full manifest (seed, per-benchmark allocation, task list)
    task_manifest.csv    flat rows: benchmark, instance_id, stratum

SWE-Lancer note: its HF availability/schema is unstable. Pass --lancer-source pointing at a
HuggingFace dataset id OR a local .jsonl/.json/.csv exported from the SWE-Lancer repo. If it
can't be loaded, the other two benchmarks still produce a (partial) manifest with a warning.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "task_manifest.json"


# ── Allocation: split n across strata proportionally, capped at stratum size ──
def allocate(sizes: dict[str, int], n: int) -> dict[str, int]:
    """Largest-remainder apportionment of n across strata, never exceeding a stratum's size."""
    total = sum(sizes.values())
    if total == 0:
        return {k: 0 for k in sizes}
    n = min(n, total)
    raw = {k: n * sz / total for k, sz in sizes.items()}
    alloc = {k: min(int(math.floor(v)), sizes[k]) for k, v in raw.items()}
    remaining = n - sum(alloc.values())
    # hand out the remainder by largest fractional part, then key (deterministic), respecting capacity
    order = sorted(sizes, key=lambda k: (-(raw[k] - math.floor(raw[k])), k))
    while remaining > 0:
        progressed = False
        for k in order:
            if remaining <= 0:
                break
            if alloc[k] < sizes[k]:
                alloc[k] += 1
                remaining -= 1
                progressed = True
        if not progressed:  # all strata capped
            break
    return alloc


def stratified_sample(rows, id_field, key_fn, n, seed, benchmark):
    """Return (sampled[list of (stratum, id)], allocation, stratum_sizes)."""
    strata: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        strata[key_fn(r)].append(str(r[id_field]))
    strata = {k: sorted(set(v)) for k, v in strata.items()}
    sizes = {k: len(v) for k, v in strata.items()}
    alloc = allocate(sizes, n)
    sampled: list[tuple[str, str]] = []
    for k in sorted(strata):
        take = alloc.get(k, 0)
        if take <= 0:
            continue
        ids = strata[k][:]
        random.Random(f"{seed}:{benchmark}:{k}").shuffle(ids)
        sampled.extend((k, i) for i in ids[:take])
    return sampled, alloc, sizes


# ── Dataset loaders (datasets imported lazily so --self-test/--dry-run need no install) ──
def load_hf(hf_id: str, split: str) -> list[dict]:
    from datasets import load_dataset  # lazy
    print(f"  loading {hf_id} [{split}] …")
    return list(load_dataset(hf_id, split=split))


def load_parquet(path: Path) -> list[dict]:
    import pyarrow.parquet as pq  # lazy
    print(f"  loading local {path.name} …")
    return pq.read_table(path).to_pylist()


def _first_field(row: dict, candidates: list[str]):
    for c in candidates:
        if c in row and row[c] not in (None, ""):
            return c
    return None


def load_lancer_rows(source: str) -> list[dict]:
    """Load SWE-Lancer rows from a local file (.jsonl/.json/.csv) or a HuggingFace id."""
    p = Path(source)
    if p.exists():
        if p.suffix == ".jsonl":
            return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        if p.suffix == ".json":
            data = json.loads(p.read_text())
            return data if isinstance(data, list) else data.get("tasks", data.get("data", []))
        if p.suffix == ".csv":
            with open(p) as f:
                return list(csv.DictReader(f))
        raise ValueError(f"Unsupported SWE-Lancer file type: {p.suffix}")
    return load_hf(source, "test")  # treat as HF id


def build_swe_bench(name, hf_id, split, n, seed, stratify, local_dir=None):
    if local_dir:
        rows = load_parquet(Path(local_dir) / f"{name}.parquet")
    else:
        rows = load_hf(hf_id, split)
    id_field = "instance_id"
    if stratify == "difficulty":
        key_fn = lambda r: (r.get("difficulty") or r.get("repo") or "?")
    else:
        key_fn = lambda r: (r.get("repo") or "?")
    sampled, alloc, sizes = stratified_sample(rows, id_field, key_fn, n, seed, name)
    meta = {str(r[id_field]): {"repo": r.get("repo"), "difficulty": r.get("difficulty")} for r in rows}
    return _pack(name, hf_id, split, stratify, n, sampled, alloc, sizes, meta)


def build_swe_lancer(name, source, n, seed):
    rows = load_lancer_rows(source)
    id_field = _first_field(rows[0], ["instance_id", "id", "task_id", "question_id"]) or "instance_id"
    var_field = _first_field(rows[0], ["variant", "task_type", "type", "category"])
    price_field = _first_field(rows[0], ["price", "amount", "payout", "reward", "value"])

    # price → low/mid/high terciles (global), combined with task type
    band_of = lambda _p: ""
    if price_field:
        prices = []
        for r in rows:
            try:
                prices.append(float(r[price_field]))
            except (TypeError, ValueError):
                pass
        if len(set(prices)) >= 3:
            q1, q2 = statistics.quantiles(prices, n=3)[:2]
            def band_of(p):
                try:
                    p = float(p)
                except (TypeError, ValueError):
                    return "na"
                return "low" if p <= q1 else ("mid" if p <= q2 else "high")

    def key_fn(r):
        parts = []
        if var_field:
            parts.append(str(r.get(var_field, "?")))
        if price_field:
            parts.append(band_of(r.get(price_field)))
        return "|".join(parts) if parts else "all"

    sampled, alloc, sizes = stratified_sample(rows, id_field, key_fn, n, seed, name)
    meta = {str(r[id_field]): {"variant": r.get(var_field) if var_field else None,
                               "price": r.get(price_field) if price_field else None} for r in rows}
    strat_desc = " × ".join(x for x in [var_field, (price_field and "price-band")] if x) or "all"
    return _pack(name, source, "test", strat_desc, n, sampled, alloc, sizes, meta)


def _pack(name, src, split, stratify, n_req, sampled, alloc, sizes, meta):
    return {
        "benchmark": name,
        "source": src,
        "split": split,
        "stratify_by": stratify,
        "n_requested": n_req,
        "n_sampled": len(sampled),
        "strata_sizes": sizes,
        "allocation": alloc,
        "tasks": [{"benchmark": name, "instance_id": i, "stratum": k, "meta": meta.get(i, {})}
                  for (k, i) in sampled],
    }


# ── Output ───────────────────────────────────────────────────────────────────
def write_manifest(out_path: Path, seed: int, blocks: list[dict]):
    manifest = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "benchmarks": {b["benchmark"]: {k: b[k] for k in
                       ("source", "split", "stratify_by", "n_requested", "n_sampled",
                        "strata_sizes", "allocation")} for b in blocks},
        "tasks": [t for b in blocks for t in b["tasks"]],
    }
    out_path.write_text(json.dumps(manifest, indent=2))
    csv_path = out_path.with_suffix(".csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["benchmark", "instance_id", "stratum"])
        for t in manifest["tasks"]:
            w.writerow([t["benchmark"], t["instance_id"], t["stratum"]])
    return manifest, csv_path


def print_summary(manifest, csv_path, out_path):
    print("\n── Manifest summary ──")
    for name, b in manifest["benchmarks"].items():
        print(f"\n  {name}: {b['n_sampled']}/{b['n_requested']} sampled "
              f"(stratify: {b['stratify_by']})")
        for k in sorted(b["allocation"]):
            if b["allocation"][k] > 0:
                print(f"      {k:<40} {b['allocation'][k]:>3} / {b['strata_sizes'][k]}")
    print(f"\n  TOTAL tasks: {len(manifest['tasks'])}")
    print(f"  → {out_path}")
    print(f"  → {csv_path}\n")


def _self_test():
    a = allocate({"a": 100, "b": 5, "c": 1}, 30)
    assert sum(a.values()) == 30 and all(a[k] <= s for k, s in {"a": 100, "b": 5, "c": 1}.items()), a
    b = allocate({"x": 2, "y": 2}, 10)  # n > total → take all
    assert b == {"x": 2, "y": 2}, b
    c = allocate({"x": 3, "y": 3, "z": 3}, 5)
    assert sum(c.values()) == 5 and max(c.values()) <= 3, c
    s, al, sz = stratified_sample([{"id": i, "g": i % 3} for i in range(30)],
                                  "id", lambda r: f"g{r['g']}", 9, 42, "t")
    assert len(s) == 9 and len({i for _, i in s}) == 9, s
    print("self-test OK")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--lite-n", type=int, default=30)
    ap.add_argument("--verified-n", type=int, default=40)
    ap.add_argument("--lancer-n", type=int, default=20)
    ap.add_argument("--lite-id", default="princeton-nlp/SWE-bench_Lite")
    ap.add_argument("--verified-id", default="princeton-nlp/SWE-bench_Verified")
    ap.add_argument("--lancer-source", default=None,
                    help="HF id OR local .jsonl/.json/.csv for SWE-Lancer (schema auto-detected)")
    ap.add_argument("--local-dir", default=None,
                    help="sample SWE-bench from local parquet (from download_datasets.py) instead of HF")
    ap.add_argument("--self-test", action="store_true", help="offline: validate sampling math")
    ap.add_argument("--dry-run", action="store_true", help="print config, download nothing")
    args = ap.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0

    if args.dry_run:
        print("DRY RUN — planned manifest:")
        print(f"  seed={args.seed}")
        print(f"  SWE-bench Lite     {args.lite_n:>3}  ({args.lite_id}, stratify: repo)")
        print(f"  SWE-bench Verified {args.verified_n:>3}  ({args.verified_id}, stratify: difficulty)")
        print(f"  SWE-Lancer         {args.lancer_n:>3}  ({args.lancer_source or 'NO SOURCE — pass --lancer-source'})")
        print(f"  → {args.out}")
        return 0

    random.seed(args.seed)
    blocks = []

    print("Sampling SWE-bench Lite …")
    blocks.append(build_swe_bench("swe_bench_lite", args.lite_id, "test", args.lite_n, args.seed, "repo", args.local_dir))
    print("Sampling SWE-bench Verified …")
    blocks.append(build_swe_bench("swe_bench_verified", args.verified_id, "test", args.verified_n, args.seed, "difficulty", args.local_dir))

    if args.lancer_source:
        try:
            print("Sampling SWE-Lancer …")
            blocks.append(build_swe_lancer("swe_lancer", args.lancer_source, args.lancer_n, args.seed))
        except Exception as e:  # non-fatal: keep the partial manifest
            print(f"  ⚠️  SWE-Lancer skipped: {e}", file=sys.stderr)
    else:
        print("  ⚠️  SWE-Lancer skipped: no --lancer-source given (partial manifest).", file=sys.stderr)

    manifest, csv_path = write_manifest(args.out, args.seed, blocks)
    print_summary(manifest, csv_path, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
