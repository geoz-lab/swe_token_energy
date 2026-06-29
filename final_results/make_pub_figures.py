#!/usr/bin/env python3
"""
make_pub_figures.py — regenerate the key Experiment-1 / Experiment-2 figures in a scientific-journal
style (no titles, serif fonts, thin spines, 300 dpi, PDF+PNG) into final_results/.

Figures:
  fig1_token_demand   Exp-1: per-task token demand by model, SWE-bench vs SWE-Lancer (log box)
  fig2_daily_demand   Exp-1: per-engineer daily/annual token demand (T_FTE), log-normal
  fig3_throughput     Exp-2: saturated θ_GPU by model and GPU
  fig4_energy         Exp-2: energy per 1M generated tokens by model and GPU
  fig5_active_scaling Exp-2: θ_GPU vs active parameters (the headline)
  fig6_cost_sim       Exp-2: Monte-Carlo distribution of θ_GPU and serving cost
"""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import pubstyle
pubstyle.apply()

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP1 = ROOT / "exp1_results" / "exp1_raw.csv"
EXP2 = ROOT / "exp2_results" / "exp2_raw.csv"

MODELS1 = ["gpt-5.4", "claude-opus-4-8", "gemini-3.1-pro-preview"]
LAB1 = {"gpt-5.4": "GPT-5.4", "claude-opus-4-8": "Opus 4.8", "gemini-3.1-pro-preview": "Gemini 3.1 Pro"}
C1 = pubstyle.COMMERCIAL_COLOR
ACTIVE_B = {"gpt-oss-20b": 3.6, "Qwen3-Coder-30B-A3B-Instruct": 3.0, "Qwen3-Coder-Next": 3.0,
            "Qwen3-32B": 32.0, "Kimi-Dev-72B": 72.0}
LAB2 = {"Qwen3-Coder-30B-A3B-Instruct": "Qwen3-Coder-30B-A3B"}


def bench(i):
    return "SWE-bench" if "__" in i else "SWE-Lancer"


# ---------------- Exp-1 ----------------
def load_exp1():
    cell = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(EXP1)):
        cell[(bench(r["instance_id"]), r["model"])]["total"].append(int(r["total_tokens"]))
    return cell


def fig1_token_demand(cell):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    for ax, b in zip(axes, ("SWE-bench", "SWE-Lancer")):
        data = [np.log10(cell[(b, m)]["total"]) for m in MODELS1]
        bp = ax.boxplot(data, vert=True, widths=0.6, patch_artist=True,
                        medianprops=dict(color="black", lw=1.1),
                        flierprops=dict(marker="o", ms=2.5, alpha=0.5))
        for patch, m in zip(bp["boxes"], MODELS1):
            patch.set_facecolor(C1[LAB1[m]]); patch.set_alpha(0.75); patch.set_edgecolor("black")
            patch.set_linewidth(0.6)
        ax.set_xticks([1, 2, 3]); ax.set_xticklabels([LAB1[m] for m in MODELS1], rotation=12)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(1))   # integer decades in log10 space
        ax.yaxis.set_minor_locator(mticker.NullLocator())
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"$10^{{{v:.0f}}}$"))
        ax.set_ylabel("tokens per task" if b == "SWE-bench" else "")
        ax.text(0.5, 0.97, b, transform=ax.transAxes, ha="center", va="top", fontsize=9)
        ax.grid(axis="y", alpha=0.25, lw=0.5)
    fig.tight_layout()
    pubstyle.save(fig, str(HERE / "fig1_token_demand"))


def fig2_daily_demand(cell):
    # daily demand per engineer: 3 SWE-bench + 1 SWE-Lancer task/day, log-normal MC
    N, NS, NL, WD = 200_000, 3, 1, 250
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    for m in MODELS1:
        sb = np.array(cell[("SWE-bench", m)]["total"], float)
        sl = np.array(cell[("SWE-Lancer", m)]["total"], float)
        rng = np.random.default_rng(0)
        sbs, sls = np.log(sb), np.log(sl)
        small = np.exp(rng.normal(sbs.mean(), sbs.std(), (N, NS))).sum(1)
        lanc = np.exp(rng.normal(sls.mean(), sls.std(), (N, NL))).sum(1)
        d = (small + lanc) / 1e6
        xs = np.logspace(np.log10(d.min()), np.log10(d.max()), 200)
        f = stats.lognorm.fit(d, floc=0)
        ax.plot(xs, stats.lognorm.pdf(xs, *f), color=C1[LAB1[m]], lw=1.4,
                label=f"{LAB1[m]} ({np.median(d):.2f}M/day)")
    ax.set_xscale("log")
    ax.set_xlabel("tokens per engineer-day (millions)")
    ax.set_ylabel("probability density")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    pubstyle.save(fig, str(HERE / "fig2_daily_demand"))


# ---------------- Exp-2 ----------------
def load_exp2():
    df = pd.read_csv(EXP2)
    df = df[df["input_len"] == 8192].copy()
    base = df["model"].str.split("/").str[-1]
    df["mlabel"] = base.map(lambda b: LAB2.get(b, b))
    df["active_B"] = base.map(ACTIVE_B)
    sat = df[df["max_concurrency"] == 64].copy()
    return sat


def _grouped_bar(sat, value, ylabel, outname, logy=False, fmt="{:.0f}"):
    order = sat.sort_values("active_B")["mlabel"].unique().tolist()
    tiers = ["A100", "H100", "H200"]
    x = np.arange(len(order)); w = 0.26
    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    for i, t in enumerate(tiers):
        sub = sat[sat["gpu_type"] == t].set_index("mlabel")
        vals = [sub.loc[m, value] if m in sub.index else np.nan for m in order]
        bars = ax.bar(x + (i - 1) * w, vals, w, label=t, color=pubstyle.GPU_COLOR[t],
                      edgecolor="black", linewidth=0.4)
        for b, v in zip(bars, vals):
            if not np.isnan(v):
                ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, v),
                            ha="center", va="bottom", fontsize=6.5,
                            xytext=(0, 1), textcoords="offset points")
    if logy:
        ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=12, ha="right")
    ax.set_ylabel(ylabel); ax.legend(title="GPU", ncol=3, columnspacing=1.0)
    ax.grid(axis="y", alpha=0.25, lw=0.5)
    fig.tight_layout()
    pubstyle.save(fig, str(HERE / outname))


def fig5_active_scaling(sat):
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    for t in ["A100", "H100", "H200"]:
        sub = sat[sat["gpu_type"] == t].sort_values("active_B")
        ax.plot(sub["active_B"], sub["theta_gpu_tok_s"], "o-", color=pubstyle.GPU_COLOR[t],
                label=t, lw=1.3)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("active parameters (billions)")
    ax.set_ylabel(r"$\theta_{\mathrm{GPU}}$ (generated tokens s$^{-1}$ GPU$^{-1}$)")
    ax.legend(title="GPU")
    ax.grid(which="both", alpha=0.25, lw=0.5)
    fig.tight_layout()
    pubstyle.save(fig, str(HERE / "fig5_active_scaling"))


def fig6_cost_sim(sat):
    # Monte-Carlo over model/GPU/price (total-token cost basis), convolved with T_FTE
    rng = np.random.default_rng(0); N = 200_000
    cells = sat[["gpu_type", "theta_gpu_tok_s", "total_token_throughput", "mean_power_w"]].values
    RENT = {"A100": (1.0, 2.5), "H100": (2.0, 4.5), "H200": (3.0, 6.0)}
    MIX = {"A100": 0.35, "H100": 0.45, "H200": 0.20}
    w = np.array([MIX[c[0]] for c in cells]); w /= w.sum()
    idx = rng.choice(len(cells), N, p=w)
    gpu = np.array([cells[i][0] for i in idx])
    th = np.array([cells[i][1] for i in idx], float)
    tt = np.array([cells[i][2] for i in idx], float)
    rlo = np.array([RENT[g][0] for g in gpu]); rhi = np.array([RENT[g][1] for g in gpu])
    rental = rng.uniform(rlo, rhi)
    usd_per_1M = rental / 3600.0 / tt * 1e6
    tfte = rng.lognormal(np.log(159e6), np.log(2.5), N)
    usd_fte = tfte / 1e6 * usd_per_1M

    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6))
    panels = [(th, r"$\theta_{\mathrm{GPU}}$ (tok s$^{-1}$ GPU$^{-1}$)"),
              (usd_per_1M, r"USD per $10^6$ tokens"),
              (usd_fte, "USD per engineer-year")]
    for a, (data, xl) in zip(ax, panels):
        a.hist(data, bins=np.logspace(np.log10(data.min()), np.log10(data.max()), 50),
               color="#4C72B0", alpha=0.85, edgecolor="white", linewidth=0.2)
        a.set_xscale("log"); a.set_xlabel(xl)
        a.axvline(np.median(data), color="black", lw=1.0)
        a.grid(alpha=0.2, lw=0.5)
        a.set_yticks([])
    ax[0].set_ylabel("density")
    fig.tight_layout()
    pubstyle.save(fig, str(HERE / "fig6_cost_sim"))


def main():
    c1 = load_exp1()
    fig1_token_demand(c1)
    fig2_daily_demand(c1)
    sat = load_exp2()
    _grouped_bar(sat, "theta_gpu_tok_s", r"$\theta_{\mathrm{GPU}}$ (generated tok s$^{-1}$ GPU$^{-1}$)",
                 "fig3_throughput", logy=True)
    _grouped_bar(sat, "kwh_per_1M_tok", r"kWh per $10^6$ generated tokens", "fig4_energy",
                 fmt="{:.3f}")
    fig5_active_scaling(sat)
    fig6_cost_sim(sat)
    print("wrote fig1..fig6 (.pdf/.png) to", HERE)


if __name__ == "__main__":
    main()
