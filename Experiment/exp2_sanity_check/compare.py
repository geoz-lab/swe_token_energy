#!/usr/bin/env python3
"""
compare.py — does an OPEN-weight model consume a SWE-bench-task token budget of the same scale as the
COMMERCIAL models (Exp-1)? Joins per-task total tokens on the same 10 Lite tasks and reports the ratio.

Reads:  exp2_sanity_check_results/sanity_raw.csv  (open model(s), this experiment)
        exp1_results/exp1_raw.csv                  (commercial models, Experiment 1)
        exp2_sanity_check/tasks_10.txt             (the paired task ids)
Writes: exp2_sanity_check_results/fig_sanity_tokens.{png,pdf} + a console table.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COMMERCIAL = ["gpt-5.4", "claude-opus-4-8", "gemini-3.1-pro-preview"]
CLABEL = {"gpt-5.4": "GPT-5.4", "claude-opus-4-8": "Opus 4.8", "gemini-3.1-pro-preview": "Gemini 3.1 Pro"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sanity", default=str(ROOT / "exp2_sanity_check_results" / "sanity_raw.csv"))
    ap.add_argument("--exp1", default=str(ROOT / "exp1_results" / "exp1_raw.csv"))
    ap.add_argument("--tasks", default=str(HERE / "tasks_10.txt"))
    args = ap.parse_args()

    tasks = [t.strip() for t in open(args.tasks) if t.strip()]
    if not Path(args.sanity).exists():
        print(f"no sanity results yet at {args.sanity} (run slurm/run_sanity.sbatch first)")
        return
    com = pd.read_csv(args.exp1)
    opn = pd.read_csv(args.sanity)
    com = com[com["instance_id"].isin(tasks)]
    opn = opn[opn["instance_id"].isin(tasks)]
    open_models = list(opn["model"].unique())

    # ---- per-task table ----
    print(f"\n=== Per-task total tokens on {len(tasks)} SWE-bench Lite tasks ===")
    piv_c = com.pivot_table(index="instance_id", columns="model", values="total_tokens", aggfunc="median")
    piv_o = opn.pivot_table(index="instance_id", columns="model", values="total_tokens", aggfunc="median")
    table = piv_c.reindex(columns=[m for m in COMMERCIAL if m in piv_c.columns]).join(piv_o, how="outer")
    table = table.reindex(tasks)
    with pd.option_context("display.float_format", lambda v: f"{v:,.0f}" if pd.notna(v) else "—",
                           "display.max_columns", None, "display.width", 200):
        print(table.to_string())

    # ---- medians + verdict ----
    print("\n=== Median total tokens/task ===")
    med = {}
    for m in COMMERCIAL:
        if m in piv_c.columns:
            med[CLABEL[m]] = np.nanmedian(piv_c[m].values)
    for m in open_models:
        med[m] = np.nanmedian(piv_o[m].values)
    for k, v in med.items():
        print(f"  {k:24s} {v:>12,.0f}")
    c_lo = min(med[CLABEL[m]] for m in COMMERCIAL if CLABEL[m] in med)
    c_hi = max(med[CLABEL[m]] for m in COMMERCIAL if CLABEL[m] in med)
    print(f"\ncommercial median range: {c_lo:,.0f} – {c_hi:,.0f} tokens/task")
    for m in open_models:
        om = med[m]
        verdict = "WITHIN commercial range" if c_lo <= om <= c_hi else \
                  ("below" if om < c_lo else "above") + " commercial range"
        ratio = om / np.median([med[CLABEL[x]] for x in COMMERCIAL if CLABEL[x] in med])
        print(f"  {m}: {om:,.0f} tokens/task  →  {ratio:.2f}× the commercial median  ({verdict})")

    # ---- figure: per-task grouped bars (log y) ----
    cols = [m for m in COMMERCIAL if m in piv_c.columns] + open_models
    labels = [CLABEL.get(m, m) for m in cols]
    colors = ["#55A868", "#4C72B0", "#C44E52", "#8172B2", "#CCB974"]
    x = np.arange(len(tasks)); w = 0.8 / len(cols)
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, (m, lab) in enumerate(zip(cols, labels)):
        src = piv_c if m in piv_c.columns else piv_o
        vals = [src[m].get(t, np.nan) if m in src.columns else np.nan for t in tasks]
        ax.bar(x + i * w - 0.4 + w / 2, vals, w, label=lab, color=colors[i % len(colors)])
    ax.set_yscale("log"); ax.set_ylabel("total tokens / task (log)")
    ax.set_xticks(x); ax.set_xticklabels([t.split("__")[-1] for t in tasks], rotation=40, ha="right", fontsize=8)
    ax.set_title("Token consumption per SWE-bench Lite task: open-weight vs commercial")
    ax.legend(fontsize=9); ax.grid(axis="y", which="both", alpha=0.3)
    fig.tight_layout()
    out = ROOT / "exp2_sanity_check_results"
    fig.savefig(out / "fig_sanity_tokens.png", dpi=300); fig.savefig(out / "fig_sanity_tokens.pdf")
    print(f"\nwrote {out}/fig_sanity_tokens.(png/pdf)")


if __name__ == "__main__":
    main()
