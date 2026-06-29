#!/usr/bin/env python3
"""
build_workload.py — turn the Experiment-1 token measurements into a representative
request workload for the Experiment-2 inference benchmark.

Why this exists
---------------
Exp-2 measures GPU token-generation throughput (theta_GPU) and energy intensity. To make
those numbers representative of *real agentic software engineering* (rather than an arbitrary
synthetic shape), we drive the benchmark with the request-size distribution actually observed
in Exp-1.

The serving unit is a single inference request (one API call inside the agent loop), so we
work in *per-request* tokens:

    per_req_input  = T_input  / api_calls     (prompt: instructions + re-sent tool output)
    per_req_output = T_output / api_calls     (newly generated assistant tokens)

Across the 270 Exp-1 task-runs these per-request sizes are heavy-tailed and well described by
a log-normal (same family as the per-task fits in exp1). vLLM's built-in `random` dataset can
only spread input length *uniformly* (--random-range-ratio in [0,1]), which cannot reproduce a
log-normal with GSD ~2-3 — hence we export the empirical distribution explicitly.

Two design choices, both grounded in Exp-1:
  * INPUT length follows the empirical per-request log-normal (the prefill-bound, tail-heavy
    cost driver).
  * OUTPUT length: Exp-1 generation is tiny (<=1% of tokens), so empirical per-request output
    is only tens of tokens — too short to measure a stable *decode* rate. We therefore record
    the empirical output stats but let the client pin a fixed decode length (--fixed-output)
    for the theta_GPU measurement, and also emit the empirical value for a faithful-mix variant.
  * PREFIX REUSE: T_tool / T_input is the share of each prompt that is re-sent tool
    observations — i.e. a growing, cacheable prefix. We report it so the benchmark can model
    vLLM automatic prefix caching (--prefix-frac in the client / --random-prefix-len in grid).

Outputs (-> exp2_results/ by default)
  workload_stats.json       per task-type + overall: input/output log-normal params,
                            prefix-reuse fraction, api_calls distribution, grid suggestions.
  workload_empirical.jsonl  N sampled requests {task_type, input_len, output_len} for the
                            self-driven client (bench_empirical.py).

Usage
  python build_workload.py                       # reads ../exp1_results/exp1_raw.csv
  python build_workload.py --csv PATH --n 512 --seed 0 --out ../exp2_results
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def task_type(instance_id: str) -> str:
    # SWE-bench instance ids look like "repo__owner-1234"; SWE-Lancer ids do not contain "__".
    return "swe-bench" if "__" in instance_id else "swe-lancer"


def lognorm_params(x):
    """MLE log-normal params from positive samples (mu, sigma in log space)."""
    x = np.asarray(x, float)
    x = x[x > 0]
    lx = np.log(x)
    mu = float(lx.mean())
    sigma = float(lx.std(ddof=1)) if len(lx) > 1 else 0.0
    return dict(
        n=int(len(x)),
        median=float(np.exp(mu)),
        mu=mu,
        sigma=sigma,
        gsd=float(np.exp(sigma)),
        mean=float(np.exp(mu + sigma * sigma / 2)),
        p10=float(np.percentile(x, 10)),
        p50=float(np.percentile(x, 50)),
        p90=float(np.percentile(x, 90)),
        p99=float(np.percentile(x, 99)),
    )


def load(csv_path):
    rows = list(csv.DictReader(open(csv_path)))
    per = defaultdict(lambda: defaultdict(list))  # task_type -> field -> list
    for r in rows:
        calls = max(int(r["api_calls"]), 1)
        t_in, t_out, t_tool = int(r["T_input"]), int(r["T_output"]), int(r["T_tool"])
        tt = task_type(r["instance_id"])
        # Exp-1 partitions total = T_input + T_output + T_tool (disjoint). The model PROMPT for a
        # request is everything that is not generated output = instructions/history (T_input) plus
        # re-sent tool observations (T_tool). The cacheable growing prefix is the tool share.
        prompt = t_in + t_tool
        prefix_frac = (t_tool / prompt) if prompt > 0 else 0.0
        for key, val in (
            ("input", prompt / calls),
            ("output", max(t_out / calls, 1.0)),
            ("api_calls", calls),
            ("prefix_frac", prefix_frac),
        ):
            per[tt][key].append(val)
            per["overall"][key].append(val)
    return per


def summarize(per):
    out = {}
    for tt, d in per.items():
        out[tt] = {
            "input_tokens_per_request": lognorm_params(d["input"]),
            "output_tokens_per_request": lognorm_params(d["output"]),
            "api_calls_per_task": {
                "median": float(np.median(d["api_calls"])),
                "mean": float(np.mean(d["api_calls"])),
                "p90": float(np.percentile(d["api_calls"], 90)),
            },
            "prefix_reuse_fraction": {
                "mean": float(np.mean(d["prefix_frac"])),
                "median": float(np.median(d["prefix_frac"])),
            },
        }
    return out


def grid_suggestions(stats):
    """Round the overall input median to nearby powers-of-two-ish buckets for the controlled
    grid, and anchor a representative cell on the empirical medians."""
    ov = stats["overall"]["input_tokens_per_request"]
    return {
        "controlled_grid": {
            "input_len": [4096, 16384, 32768],
            "output_len": 1024,
            "max_concurrency": [1, 4, 16],
            "note": "vllm bench serve --dataset-name random; prefix via --random-prefix-len",
        },
        "representative_cell": {
            "input_len_median": round(ov["median"]),
            "input_gsd": round(ov["gsd"], 2),
            "prefix_frac": round(stats["overall"]["prefix_reuse_fraction"]["mean"], 3),
            "fixed_output_len": 1024,
            "note": "input drawn from empirical log-normal (bench_empirical.py)",
        },
    }


def sample_requests(per, n, seed, fixed_output):
    rng = np.random.default_rng(seed)
    reqs = []
    for tt in ("swe-bench", "swe-lancer"):
        d = per[tt]
        pin = lognorm_params(d["input"])
        pout = lognorm_params(d["output"])
        ins = rng.lognormal(pin["mu"], pin["sigma"], n)
        outs = rng.lognormal(pout["mu"], pout["sigma"], n)
        for i in range(n):
            reqs.append({
                "task_type": tt,
                "input_len": int(np.clip(round(ins[i]), 16, 1_000_000)),
                "output_len_empirical": int(np.clip(round(outs[i]), 1, 100_000)),
                "output_len": int(fixed_output),  # used for the theta_GPU decode measurement
            })
    rng.shuffle(reqs)
    return reqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "exp1_results" / "exp1_raw.csv"))
    ap.add_argument("--out", default=str(ROOT / "exp2_results"))
    ap.add_argument("--n", type=int, default=512, help="requests sampled per task type")
    ap.add_argument("--fixed-output", type=int, default=1024,
                    help="decode length pinned for the theta_GPU measurement")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    per = load(args.csv)
    stats = summarize(per)
    stats["_grid"] = grid_suggestions(stats)
    stats["_meta"] = {"csv": args.csv, "n_per_type": args.n, "seed": args.seed,
                      "fixed_output": args.fixed_output}

    (out / "workload_stats.json").write_text(json.dumps(stats, indent=2))

    reqs = sample_requests(per, args.n, args.seed, args.fixed_output)
    with open(out / "workload_empirical.jsonl", "w") as f:
        for r in reqs:
            f.write(json.dumps(r) + "\n")

    # ---- console report ----
    print("\n=== Per-request token shape from Experiment 1 (T/api_calls) ===")
    hdr = f"{'task_type':<11}{'n':>5}{'in median':>11}{'in GSD':>8}{'in p90':>10}" \
          f"{'out median':>12}{'prefix%':>9}{'calls med':>10}"
    print(hdr)
    for tt in ("swe-bench", "swe-lancer", "overall"):
        s = stats[tt]
        pin, pout = s["input_tokens_per_request"], s["output_tokens_per_request"]
        print(f"{tt:<11}{pin['n']:>5}{pin['median']:>11,.0f}{pin['gsd']:>8.2f}{pin['p90']:>10,.0f}"
              f"{pout['median']:>12,.0f}{s['prefix_reuse_fraction']['mean']*100:>8.0f}%"
              f"{s['api_calls_per_task']['median']:>10,.0f}")
    g = stats["_grid"]["representative_cell"]
    print(f"\nrepresentative cell: input~LogN(median={g['input_len_median']:,}, GSD={g['input_gsd']}), "
          f"prefix_frac={g['prefix_frac']}, fixed_output={g['fixed_output_len']}")
    print(f"controlled grid: input {stats['_grid']['controlled_grid']['input_len']} x "
          f"concurrency {stats['_grid']['controlled_grid']['max_concurrency']}")
    print(f"\nwrote {out}/workload_stats.json and workload_empirical.jsonl "
          f"({len(reqs)} requests)")


if __name__ == "__main__":
    main()
