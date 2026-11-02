#!/usr/bin/env python3
"""
make_figures.py — turn exp2_results/exp2_raw.csv into the Experiment-2 figures.

At the saturated operating point (highest max_concurrency per model x GPU) it plots:
  fig_throughput  : theta_GPU (tokens/s/GPU) per model, grouped by GPU tier
  fig_energy      : kWh per 1M generated tokens per model, grouped by GPU tier
  fig_active_scaling : theta_GPU vs active parameters (the headline: active params drive throughput)

Reads the model->active-params map below (CSV only stores the HF id). Saturated cell = the row with
the largest max_concurrency for each (gpu_type, model); the smoke `in2048` cells are ignored because
we key on the representative input_len (default 8192).

Usage:  python make_figures.py [--csv ../exp2_results/exp2_raw.csv] [--input-len 8192]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent

# model basename -> (short label, active params [B], architecture tag)
MODELS = {
    "gpt-oss-20b":                  ("gpt-oss-20b",         3.6, "MoE/mxfp4"),
    "Qwen3-Coder-30B-A3B-Instruct": ("Qwen3-Coder-30B-A3B", 3.0, "MoE"),
    "Qwen3-Coder-Next":             ("Qwen3-Coder-Next",    3.0, "MoE/FP8"),
    "Qwen3-32B":                    ("Qwen3-32B",          32.0, "dense"),
    "Kimi-Dev-72B":                 ("Kimi-Dev-72B",       72.0, "dense/FP8"),
}
TIER_COLOR = {"A100": "#C44E52", "H100": "#4C72B0", "H200": "#55A868"}


def model_key(hf_id):
    base = str(hf_id).split("/")[-1]
    for k in MODELS:
        if k.lower() in base.lower():
            return k
    return base


def load(csv, input_len):
    df = pd.read_csv(csv)
    for c in ("theta_gpu_tok_s", "max_concurrency", "input_len", "tokens_per_joule",
              "kwh_per_1M_tok", "gpu_seconds_per_1M_tok", "mean_power_w"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["input_len"] == input_len].copy()          # drop smoke / other operating points
    df["mkey"] = df["model"].map(model_key)
    df["label"] = df["mkey"].map(lambda k: MODELS.get(k, (k, np.nan, "?"))[0])
    df["active_B"] = df["mkey"].map(lambda k: MODELS.get(k, (k, np.nan, "?"))[1])
    # saturated cell = max concurrency per (gpu_type, model)
    idx = df.groupby(["gpu_type", "mkey"])["max_concurrency"].idxmax()
    return df.loc[idx].sort_values("active_B")


def grouped_bar(sat, value, ylabel, title, outname, logy=False, fmt="{:.0f}"):
    models = sat.sort_values("active_B")["label"].unique().tolist()
    tiers = sorted(sat["gpu_type"].unique())
    x = np.arange(len(models))
    w = 0.8 / max(len(tiers), 1)
    fig, ax = plt.subplots(figsize=(max(7, 1.6 * len(models)), 4.8))
    for i, t in enumerate(tiers):
        sub = sat[sat["gpu_type"] == t].set_index("label")
        vals = [sub.loc[m, value] if m in sub.index else np.nan for m in models]
        bars = ax.bar(x + i * w - 0.4 + w / 2, vals, w, label=t,
                      color=TIER_COLOR.get(t, None), edgecolor="white")
        for b, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(b.get_x() + b.get_width() / 2, v, fmt.format(v),
                        ha="center", va="bottom", fontsize=8)
    if logy:
        ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=15, ha="right", fontsize=9)
    ax.set_ylabel(ylabel); ax.set_title(title)
    ax.legend(title="GPU"); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE.parent / "exp2_results" / f"{outname}.png", dpi=300)
    fig.savefig(HERE.parent / "exp2_results" / f"{outname}.pdf")


def fig_scaling(sat):
    fig, ax = plt.subplots(figsize=(6.4, 5))
    for t in sorted(sat["gpu_type"].unique()):
        sub = sat[sat["gpu_type"] == t].sort_values("active_B")
        ax.plot(sub["active_B"], sub["theta_gpu_tok_s"], "o-", color=TIER_COLOR.get(t),
                label=t, ms=8)
        for _, r in sub.iterrows():
            ax.annotate(r["label"], (r["active_B"], r["theta_gpu_tok_s"]),
                        fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Active parameters (billions, log)")
    ax.set_ylabel(r"$\theta_{GPU}$  (tokens/s/GPU, saturated, log)")
    ax.set_title("Inference throughput vs active parameters\n(active params, not total size, drive θ_GPU)")
    ax.legend(title="GPU"); ax.grid(which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE.parent / "exp2_results" / "fig_active_scaling.png", dpi=300)
    fig.savefig(HERE.parent / "exp2_results" / "fig_active_scaling.pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(HERE.parent / "exp2_results" / "exp2_raw.csv"))
    ap.add_argument("--input-len", type=int, default=8192)
    args = ap.parse_args()
    sat = load(args.csv, args.input_len)
    if sat.empty:
        print(f"no rows with input_len={args.input_len} in {args.csv}"); return

    print("\n=== Saturated operating point (per GPU x model) ===")
    cols = ["gpu_type", "label", "active_B", "max_concurrency", "theta_gpu_tok_s",
            "tokens_per_joule", "gpu_seconds_per_1M_tok", "kwh_per_1M_tok", "mean_power_w"]
    print(sat[cols].to_string(index=False))

    grouped_bar(sat, "theta_gpu_tok_s", r"$\theta_{GPU}$ (tokens/s/GPU)",
                "Saturated inference throughput", "fig_throughput", logy=True)
    grouped_bar(sat, "kwh_per_1M_tok", "kWh per 1M generated tokens",
                "Energy intensity of token generation", "fig_energy", fmt="{:.3f}")
    fig_scaling(sat)
    print(f"\nwrote fig_throughput, fig_energy, fig_active_scaling (.png/.pdf) to exp2_results/")


if __name__ == "__main__":
    main()
