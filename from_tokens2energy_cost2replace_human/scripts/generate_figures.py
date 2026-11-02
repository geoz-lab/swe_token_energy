"""
generate_figures.py
Generate publication-quality figures from calibration CSV data.

Outputs:
    figures/fig_token_calibration.pdf   -- main paper figure (LaTeX-ready)
    figures/fig_token_calibration.png   -- PNG preview

Run:
    python scripts/generate_figures.py
"""

import csv
import os
import sys
from pathlib import Path
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
except ImportError:
    sys.exit("matplotlib/numpy not installed. Run: pip install matplotlib numpy")

PROJECT = Path(__file__).resolve().parent.parent
RAW_CSV = PROJECT / "figures" / "empirical_token_calibration.csv"
OUT_PDF = PROJECT / "figures" / "fig_token_calibration.pdf"
OUT_PNG = PROJECT / "figures" / "fig_token_calibration.png"


# ── Load data ────────────────────────────────────────────────────────────────

def load_raw(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def compute_means(rows: list[dict]) -> dict:
    """Return {(task_tier, provider, model_label): mean_total_tokens}"""
    groups = defaultdict(list)
    for r in rows:
        if r["total_tokens"]:
            key = (r["task_tier"], r["provider"], r["model_label"])
            groups[key].append(int(r["total_tokens"]))
    return {k: sum(v) / len(v) for k, v in groups.items()}


# ── Color / style maps ───────────────────────────────────────────────────────

PROVIDER_COLORS = {
    "anthropic": "#E17A00",   # Anthropic orange
    "openai":    "#10A37F",   # OpenAI green
    "google":    "#4285F4",   # Google blue
}

TASK_LABELS = {
    "simple_bug_fix":       "Simple\nBug Fix",
    "feature_implementation": "Feature\nImplementation",
    "architectural_refactor": "Architectural\nRefactor",
}
TASK_ORDER = ["simple_bug_fix", "feature_implementation", "architectural_refactor"]

# ── Build figure ─────────────────────────────────────────────────────────────

def make_figure(means: dict):
    model_keys = sorted(
        {(p, m) for (_, p, m) in means.keys()},
        key=lambda x: (x[0], x[1])
    )

    n_tasks  = len(TASK_ORDER)
    n_models = len(model_keys)
    bar_w    = 0.72 / n_models
    x_base   = np.arange(n_tasks, dtype=float)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    fig.subplots_adjust(left=0.11, right=0.97, top=0.84, bottom=0.13)

    # Build per-model color: vary brightness within provider
    provider_model_counts = {}
    for (p, m) in model_keys:
        provider_model_counts[p] = provider_model_counts.get(p, 0) + 1
    provider_model_idx = {}

    MODEL_COLORS = []
    for p, m in model_keys:
        base = PROVIDER_COLORS.get(p, "#888888")
        idx  = provider_model_idx.get(p, 0)
        provider_model_idx[p] = idx + 1
        total = provider_model_counts[p]
        # lighten later models within the same provider
        alphas = [1.0, 0.55, 0.35]
        MODEL_COLORS.append((base, alphas[idx % len(alphas)]))

    for i, ((provider, model_label), (color, alpha)) in enumerate(zip(model_keys, MODEL_COLORS)):
        offset = (i - (n_models - 1) / 2) * bar_w
        heights = [means.get((task, provider, model_label), 0) for task in TASK_ORDER]

        bars = ax.bar(
            x_base + offset, heights,
            width=bar_w * 0.88, color=color, alpha=alpha,
            edgecolor="white", linewidth=0.5, label=model_label,
        )
        for bar, h in zip(bars, heights):
            if h > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2, h + 130,
                    f"{h/1000:.1f}K",
                    ha="center", va="bottom", fontsize=6.5, color="#333333",
                )

    # 8K output cap dashed line
    cap = 8192
    ax.axhline(cap, color="#999999", linestyle="--", linewidth=0.9, zorder=0)
    ax.text(n_tasks - 0.52, cap + 180, "8,192 token output cap",
            fontsize=7, color="#777777", va="bottom", ha="right")

    # Inline agentic note — two lines to avoid clipping
    fig.text(
        0.13, 0.875,
        "Note: Agentic agents (Bai et al. 2026) consume 1–3.5 M tokens/task\n"
        "— 100–300× more than these single-turn measurements.",
        fontsize=7.5, color="#AA2200", style="italic",
        ha="left", va="bottom",
    )

    # Axes
    ax.set_xticks(x_base)
    ax.set_xticklabels([TASK_LABELS[t] for t in TASK_ORDER], fontsize=9.5)
    ax.set_ylabel("Tokens per task (single-turn)", fontsize=9)
    ax.set_ylim(0, 13_000)
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x/1000)}K")
    )
    ax.set_xlim(-0.55, n_tasks - 0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8.5)

    ax.legend(fontsize=7.5, loc="upper left", frameon=True,
              framealpha=0.9, edgecolor="#cccccc", ncol=min(n_models, 3))

    ax.set_title("Empirical Single-Turn Token Consumption by Task Complexity",
                 fontsize=10, pad=4)

    return fig


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not RAW_CSV.exists():
        sys.exit(f"ERROR: {RAW_CSV} not found. Run scripts/token_calibration.py first.")

    rows  = load_raw(RAW_CSV)
    means = compute_means(rows)

    if not means:
        sys.exit("ERROR: No valid rows in CSV (all total_tokens empty).")

    print(f"Loaded {len(rows)} rows from {RAW_CSV.name}")
    print(f"Models found: {sorted({m for (_, _, m) in means.keys()})}")

    fig = make_figure(means)
    fig.savefig(OUT_PDF, dpi=150)
    fig.savefig(OUT_PNG, dpi=120)
    print(f"Saved: {OUT_PDF}")
    print(f"Saved: {OUT_PNG}")


if __name__ == "__main__":
    main()
