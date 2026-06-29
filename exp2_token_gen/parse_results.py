#!/usr/bin/env python3
"""
parse_results.py — aggregate Exp-2 raw outputs into one tidy CSV.

For each vllm-bench result JSON (bench_<tag>.json) it:
  * reads throughput / latency metrics,
  * loads the co-measured power series (power_<tag>.csv), trims warmup/cooldown to the steady
    window stamped in the JSON (_window), integrates power -> energy (J),
  * derives the headline quantities:
        theta_GPU            = output_throughput            (tokens/s/GPU, since G=1)
        tokens_per_joule     = total_output_tokens / energy_J
        gpu_seconds_per_1M   = 1e6 / theta_GPU
        kWh_per_1M_tokens    = (1e6 / tokens_per_joule) / 3.6e6

Writes exp2_results/exp2_raw.csv and prints a summary table.

Usage:  python parse_results.py [--dir ../exp2_results]
"""
import argparse
import csv
import glob
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def g(d, *keys, default=""):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def load_power_window(power_csv, t_start, t_end, warmup_frac=0.10, cooldown_frac=0.05):
    """Return (mean_power_w, energy_J, gpu_util_mean, mem_used_mb_mean, n) over the steady part
    of [t_start, t_end]. Energy via trapezoidal integration on the trimmed window."""
    if not power_csv or not os.path.exists(power_csv):
        return None
    ts, pw, ug, mem = [], [], [], []
    with open(power_csv) as f:
        for r in csv.DictReader(f):
            try:
                t = float(r["t_unix"])
            except (KeyError, ValueError):
                continue
            if t_start <= t <= t_end:
                ts.append(t); pw.append(float(r["power_w"]))
                ug.append(float(r["util_gpu"])); mem.append(float(r["mem_used_mb"]))
    if len(ts) < 3:
        return None
    span = ts[-1] - ts[0]
    lo, hi = ts[0] + warmup_frac * span, ts[-1] - cooldown_frac * span
    idx = [i for i, t in enumerate(ts) if lo <= t <= hi] or list(range(len(ts)))
    energy = 0.0
    for a, b in zip(idx[:-1], idx[1:]):
        energy += 0.5 * (pw[a] + pw[b]) * (ts[b] - ts[a])
    mean_p = sum(pw[i] for i in idx) / len(idx)
    return dict(mean_power_w=mean_p, energy_J=energy,
                gpu_util_mean=sum(ug[i] for i in idx) / len(idx),
                mem_used_mb_mean=sum(mem[i] for i in idx) / len(idx), n=len(idx))


def from_tag(tag):
    """tag = <gpu>__<model-slug>__in<input>__c<conc>  ->  (gpu, input_len, max_concurrency)."""
    parts = str(tag).split("__")
    gpu = parts[0] if parts else ""
    il = mc = ""
    for p in parts:
        if p.startswith("in") and p[2:].isdigit():
            il = p[2:]
        elif p.startswith("c") and p[1:].isdigit():
            mc = p[1:]
    return gpu, il, mc


def parse_one(path):
    d = json.loads(Path(path).read_text())
    # vLLM may serialize --metadata as a dict OR a list of "k=v" strings; handle both.
    md = d.get("metadata")
    if isinstance(md, dict):
        meta = {k: str(v) for k, v in md.items()}
    elif isinstance(md, list):
        meta = {kv.split("=", 1)[0]: kv.split("=", 1)[1] for kv in md if "=" in kv}
    else:
        meta = {}
    win = d.get("_window", {})
    tag = meta.get("tag") or win.get("tag") or Path(path).stem
    if tag.startswith("bench_"):
        tag = tag[len("bench_"):]
    tgpu, til, tmc = from_tag(tag)          # robust fallback straight from the tag
    out_tok = float(g(d, "total_output_tokens", default=0) or 0)
    theta = float(g(d, "output_throughput", default=0) or 0)
    row = {
        "tag": tag,
        "gpu_type": meta.get("gpu_type") or tgpu,
        "model": g(d, "model_id", "model", default=""),
        "input_len": meta.get("input_len") or til,
        "max_concurrency": g(d, "max_concurrency", default=meta.get("max_concurrency") or tmc),
        "prefix_len": meta.get("prefix_len", ""),
        "completed": g(d, "completed", default=""),
        "duration_s": g(d, "duration", default=win.get("wall_s", "")),
        "total_input_tokens": g(d, "total_input_tokens", default=""),
        "total_output_tokens": out_tok,
        "request_throughput": g(d, "request_throughput", default=""),
        "theta_gpu_tok_s": theta,                      # output throughput = theta_GPU (G=1)
        "total_token_throughput": g(d, "total_token_throughput", default=""),
        "mean_ttft_ms": g(d, "mean_ttft_ms", default=""),
        "p50_ttft_ms": g(d, "p50_ttft_ms", "median_ttft_ms", default=""),
        "p99_ttft_ms": g(d, "p99_ttft_ms", default=""),
        "mean_tpot_ms": g(d, "mean_tpot_ms", default=""),
        "p50_tpot_ms": g(d, "p50_tpot_ms", "median_tpot_ms", default=""),
        "p99_tpot_ms": g(d, "p99_tpot_ms", default=""),
    }
    p = load_power_window(
        str(Path(path).parent / win.get("power_csv", "")) if win.get("power_csv") else "",
        float(win.get("t_start", 0)), float(win.get("t_end", 0)))
    if p:
        row.update(mean_power_w=round(p["mean_power_w"], 1),
                   energy_J=round(p["energy_J"], 1),
                   gpu_util_mean=round(p["gpu_util_mean"], 1),
                   mem_used_mb_mean=round(p["mem_used_mb_mean"], 0))
        if p["energy_J"] > 0 and out_tok > 0:
            tpj = out_tok / p["energy_J"]
            row["tokens_per_joule"] = round(tpj, 2)
            row["kwh_per_1M_tok"] = round((1e6 / tpj) / 3.6e6, 4)
    else:
        row.update(mean_power_w="", energy_J="", gpu_util_mean="", mem_used_mb_mean="",
                   tokens_per_joule="", kwh_per_1M_tok="")
    row["gpu_seconds_per_1M_tok"] = round(1e6 / theta, 1) if theta > 0 else ""
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HERE.parent / "exp2_results"))
    args = ap.parse_args()
    d = Path(args.dir)
    files = sorted(glob.glob(str(d / "bench_*.json")))
    if not files:
        print(f"no bench_*.json in {d}")
        return
    rows = [parse_one(f) for f in files]
    cols = ["tag", "gpu_type", "model", "input_len", "max_concurrency", "prefix_len",
            "completed", "duration_s", "total_input_tokens", "total_output_tokens",
            "request_throughput", "theta_gpu_tok_s", "total_token_throughput",
            "mean_ttft_ms", "p50_ttft_ms", "p99_ttft_ms", "mean_tpot_ms", "p50_tpot_ms",
            "p99_tpot_ms", "mean_power_w", "energy_J", "tokens_per_joule",
            "gpu_util_mean", "mem_used_mb_mean", "gpu_seconds_per_1M_tok", "kwh_per_1M_tok"]
    out = d / "exp2_raw.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

    print(f"\n=== Exp-2 results ({len(rows)} cells) ===")
    print(f"{'gpu':<6}{'model':<34}{'conc':>5}{'theta tok/s':>13}{'power W':>9}"
          f"{'tok/J':>9}{'GPU-s/1M':>10}{'kWh/1M':>9}")
    for r in sorted(rows, key=lambda x: (x["gpu_type"], str(x["model"]), int(x["max_concurrency"] or 0))):
        m = str(r["model"]).split("/")[-1][:33]
        print(f"{r['gpu_type']:<6}{m:<34}{str(r['max_concurrency']):>5}"
              f"{r['theta_gpu_tok_s']:>13,.0f}{str(r['mean_power_w']):>9}"
              f"{str(r['tokens_per_joule']):>9}{str(r['gpu_seconds_per_1M_tok']):>10}"
              f"{str(r['kwh_per_1M_tok']):>9}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
