#!/usr/bin/env python3
"""make_figure.py — token-demand distribution figure for Experiment 1 (reads exp1_results/exp1_raw.csv)."""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "exp1_results" / "exp1_raw.csv"

# model display order (ascending token demand) + labels
MODELS = ["gpt-5.4", "claude-opus-4-8", "gemini-3.1-pro-preview"]
LABEL = {"gpt-5.4": "GPT-5.4", "claude-opus-4-8": "Opus 4.8", "gemini-3.1-pro-preview": "Gemini 3.1 Pro"}
BENCHES = ["swe-bench", "swe-lancer"]
COLOR = {"swe-bench": "#4C72B0", "swe-lancer": "#C44E52"}


def bench(iid):
    return "swe-bench" if "__" in iid else "swe-lancer"


def main():
    data = defaultdict(list)
    for r in csv.DictReader(open(CSV)):
        data[(r["model"], bench(r["instance_id"]))].append(int(r["total_tokens"]))

    fig, ax = plt.subplots(figsize=(8, 5))
    import random
    rng = random.Random(0)
    xticks, xlabels = [], []
    for i, m in enumerate(MODELS):
        for j, b in enumerate(BENCHES):
            vals = data.get((m, b), [])
            if not vals:
                continue
            pos = i * 3 + j
            ax.boxplot(vals, positions=[pos], widths=0.6, showfliers=False,
                       patch_artist=True, medianprops=dict(color="black", linewidth=1.5),
                       boxprops=dict(facecolor=COLOR[b], alpha=0.55, edgecolor="black"),
                       whiskerprops=dict(color="black"), capprops=dict(color="black"))
            ax.scatter([pos + rng.uniform(-0.18, 0.18) for _ in vals], vals,
                       s=14, color=COLOR[b], edgecolor="white", linewidth=0.4, alpha=0.8, zorder=3)
        xticks.append(i * 3 + 0.5)
        xlabels.append(LABEL[m])

    ax.set_yscale("log")
    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)
    ax.set_ylabel("Tokens per task (log scale)")
    ax.set_title("Agentic token demand per software-engineering task\n(90 tasks × 3 models; boxes = IQR, line = median)")
    ax.grid(axis="y", which="both", linestyle=":", alpha=0.4)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=COLOR[b], alpha=0.55, edgecolor="black") for b in BENCHES]
    ax.legend(handles, ["SWE-bench (Lite+Verified)", "SWE-Lancer (IC freelance)"], loc="upper left", frameon=True)
    fig.tight_layout()

    out_png = ROOT / "exp1_results" / "fig_token_demand.png"
    out_pdf = ROOT / "exp1_results" / "fig_token_demand.pdf"
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    print(f"wrote {out_png}\nwrote {out_pdf}")


if __name__ == "__main__":
    main()
