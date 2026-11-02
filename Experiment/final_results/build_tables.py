#!/usr/bin/env python3
"""
build_tables.py — consolidate Experiment-1 (demand) and Experiment-2 (supply) raw outputs into
clean, human-readable summary CSVs in final_results/.

Outputs:
  exp1_demand_per_task.csv     per (benchmark, model): token demand stats per agentic task
  exp2_supply_all_cells.csv    every measured (model × GPU × concurrency) cell, tidy columns
  exp2_supply_saturated.csv    saturated (concurrency 64) headline: θ_GPU, energy, cost basis
  headline_summary.csv         a few cross-experiment numbers used in the paper
"""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP1 = ROOT / "exp1_results" / "exp1_raw.csv"
EXP2 = ROOT / "exp2_results" / "exp2_raw.csv"

ACTIVE_B = {  # active parameters (billions) per model basename
    "gpt-oss-20b": 3.6, "Qwen3-Coder-30B-A3B-Instruct": 3.0, "Qwen3-Coder-Next": 3.0,
    "Qwen3-32B": 32.0, "Kimi-Dev-72B": 72.0,
}
TOTAL_B = {
    "gpt-oss-20b": 21, "Qwen3-Coder-30B-A3B-Instruct": 30, "Qwen3-Coder-Next": 80,
    "Qwen3-32B": 32, "Kimi-Dev-72B": 72,
}
ARCH = {
    "gpt-oss-20b": "MoE", "Qwen3-Coder-30B-A3B-Instruct": "MoE", "Qwen3-Coder-Next": "MoE",
    "Qwen3-32B": "dense", "Kimi-Dev-72B": "dense",
}
LABEL = {"Qwen3-Coder-30B-A3B-Instruct": "Qwen3-Coder-30B-A3B"}
MODEL_LABEL = {"gpt-5.4": "GPT-5.4", "claude-opus-4-8": "Opus 4.8",
               "gemini-3.1-pro-preview": "Gemini 3.1 Pro"}


def bench(iid):
    return "SWE-bench" if "__" in iid else "SWE-Lancer"


# ---------------- Experiment 1: demand ----------------
def exp1_demand():
    cell = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(EXP1)):
        b, m = bench(r["instance_id"]), r["model"]
        calls = max(int(r["api_calls"]), 1)
        cell[(b, m)]["total"].append(int(r["total_tokens"]))
        cell[(b, m)]["in"].append(int(r["T_input"]))
        cell[(b, m)]["out"].append(int(r["T_output"]))
        cell[(b, m)]["tool"].append(int(r["T_tool"]))
        cell[(b, m)]["calls"].append(calls)
    rows = []
    for (b, m), d in sorted(cell.items()):
        t = np.array(d["total"], float)
        rows.append({
            "benchmark": b,
            "model": MODEL_LABEL.get(m, m),
            "n_tasks": len(t),
            "median_total_tokens": int(np.median(t)),
            "mean_total_tokens": int(t.mean()),
            "p10_total_tokens": int(np.percentile(t, 10)),
            "p90_total_tokens": int(np.percentile(t, 90)),
            "median_input_tokens": int(np.median(d["in"])),
            "median_output_tokens": int(np.median(d["out"])),
            "median_tool_tokens": int(np.median(d["tool"])),
            "median_api_calls": int(np.median(d["calls"])),
        })
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "exp1_demand_per_task.csv", index=False)
    return df


# ---------------- Experiment 2: supply ----------------
def exp2_supply():
    df = pd.read_csv(EXP2)
    df = df[df["input_len"] == 8192].copy()              # drop any smoke cells
    base = df["model"].str.split("/").str[-1]
    df["model_name"] = base.map(lambda b: LABEL.get(b, b))
    df["arch"] = base.map(ARCH)
    df["active_params_B"] = base.map(ACTIVE_B)
    df["total_params_B"] = base.map(TOTAL_B)
    out = df.rename(columns={
        "gpu_type": "gpu", "max_concurrency": "concurrency",
        "theta_gpu_tok_s": "theta_gpu_generated_tok_s",
        "total_token_throughput": "total_throughput_tok_s",
        "p50_ttft_ms": "ttft_p50_ms", "p99_ttft_ms": "ttft_p99_ms",
        "p50_tpot_ms": "tpot_p50_ms", "p99_tpot_ms": "tpot_p99_ms",
        "mean_power_w": "power_w", "tokens_per_joule": "tokens_per_joule",
        "gpu_seconds_per_1M_tok": "gpu_seconds_per_1M_generated",
        "kwh_per_1M_tok": "kwh_per_1M_generated", "gpu_util_mean": "gpu_util_pct",
    })
    cols = ["gpu", "model_name", "arch", "active_params_B", "total_params_B", "concurrency",
            "theta_gpu_generated_tok_s", "total_throughput_tok_s", "ttft_p50_ms", "ttft_p99_ms",
            "tpot_p50_ms", "tpot_p99_ms", "power_w", "tokens_per_joule",
            "gpu_seconds_per_1M_generated", "kwh_per_1M_generated", "gpu_util_pct"]
    out = out[cols].round({"theta_gpu_generated_tok_s": 0, "total_throughput_tok_s": 0,
                           "ttft_p50_ms": 0, "ttft_p99_ms": 0, "tpot_p50_ms": 1, "tpot_p99_ms": 1,
                           "power_w": 0, "tokens_per_joule": 2, "gpu_seconds_per_1M_generated": 0,
                           "kwh_per_1M_generated": 4, "gpu_util_pct": 0})
    gpu_order = {"A100": 0, "H100": 1, "H200": 2}
    out = out.sort_values(by=["active_params_B", "model_name", "concurrency", "gpu"],
                          key=lambda s: s.map(gpu_order) if s.name == "gpu" else s)
    out.to_csv(HERE / "exp2_supply_all_cells.csv", index=False)

    sat = out[out["concurrency"] == 64].drop(columns=["concurrency"]).copy()
    sat.to_csv(HERE / "exp2_supply_saturated.csv", index=False)
    return out, sat


def headline(d1, sat):
    rows = []
    # Exp-1 demand medians
    for _, r in d1.iterrows():
        rows.append({"experiment": "Exp-1 demand", "metric": f"median tokens/task · {r['benchmark']} · {r['model']}",
                     "value": r["median_total_tokens"], "unit": "tokens"})
    # Exp-2 saturated headline (H100 + H200)
    for _, r in sat.iterrows():
        rows.append({"experiment": "Exp-2 supply",
                     "metric": f"θ_GPU saturated · {r['model_name']} · {r['gpu']}",
                     "value": int(r["theta_gpu_generated_tok_s"]), "unit": "tok/s/GPU"})
        rows.append({"experiment": "Exp-2 supply",
                     "metric": f"energy · {r['model_name']} · {r['gpu']}",
                     "value": r["kwh_per_1M_generated"], "unit": "kWh/1M gen-tok"})
    pd.DataFrame(rows).to_csv(HERE / "headline_summary.csv", index=False)


def main():
    d1 = exp1_demand()
    allc, sat = exp2_supply()
    headline(d1, sat)
    print("=== Exp-1 demand per task ===")
    print(d1.to_string(index=False))
    print("\n=== Exp-2 saturated supply (concurrency 64) ===")
    print(sat.to_string(index=False))
    print(f"\nwrote 4 CSVs to {HERE}")


if __name__ == "__main__":
    main()
