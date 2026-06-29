#!/usr/bin/env python3
"""
build_sanity.py — consolidate the open-vs-commercial token-parity sanity check into a clean CSV and a
publication figure for final_results/.

Premise: Experiment 1 measures token DEMAND with commercial models; Experiment 2 measures token SUPPLY
with open models. The sanity check runs an OPEN model (Qwen3-Coder-30B-A3B) through the IDENTICAL
mini-swe-agent scaffold on the SAME 10 SWE-bench Lite tasks, to verify the per-task token budget is the
same order of magnitude (i.e. demand is a property of the task+scaffold, not the specific model).

Reads:  exp2_sanity_check_results/sanity_raw.csv  (open model, this run, 256k context)
        exp1_results/exp1_raw.csv                  (commercial models, Experiment 1)
Writes: final_results/exp3_sanity_token_parity.csv  + fig7_sanity_tokens.{pdf,png}
"""
from pathlib import Path

import numpy as np
import pandas as pd

import pubstyle
pubstyle.apply()
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SANITY = ROOT / "exp2_sanity_check_results" / "sanity_raw.csv"
EXP1 = ROOT / "exp1_results" / "exp1_raw.csv"

COMM = ["gpt-5.4", "claude-opus-4-8", "gemini-3.1-pro-preview"]
CLABEL = {"gpt-5.4": "GPT-5.4", "claude-opus-4-8": "Opus 4.8", "gemini-3.1-pro-preview": "Gemini 3.1 Pro"}
OPEN_LABEL = "Qwen3-Coder-30B-A3B (open)"
COLORS = ["#55A868", "#4C72B0", "#C44E52", "#DD8452"]   # GPT, Opus, Gemini, open


def main():
    opn = pd.read_csv(SANITY)
    com = pd.read_csv(EXP1)
    tasks = list(opn["instance_id"])
    com = com[com["instance_id"].isin(tasks)]

    piv_c = com.pivot_table(index="instance_id", columns="model", values="total_tokens", aggfunc="median")
    piv_o = opn.set_index("instance_id")["total_tokens"]
    retry = opn.set_index("instance_id")["retry_frac"]
    calls = opn.set_index("instance_id")["api_calls"]

    # ---- per-task table ----
    rows = []
    for t in tasks:
        rows.append({
            "instance_id": t,
            "GPT-5.4": int(piv_c.loc[t, "gpt-5.4"]),
            "Opus 4.8": int(piv_c.loc[t, "claude-opus-4-8"]),
            "Gemini 3.1 Pro": int(piv_c.loc[t, "gemini-3.1-pro-preview"]),
            "Qwen3-Coder-30B-A3B (open)": int(piv_o[t]),
            "open_api_calls": int(calls[t]),
            "open_retry_frac": round(float(retry[t]), 2),
        })
    df = pd.DataFrame(rows)
    med = {c: int(np.median(df[c])) for c in
           ["GPT-5.4", "Opus 4.8", "Gemini 3.1 Pro", "Qwen3-Coder-30B-A3B (open)"]}
    med_row = {"instance_id": "MEDIAN", **med,
               "open_api_calls": int(np.median(df["open_api_calls"])),
               "open_retry_frac": round(float(np.median(df["open_retry_frac"])), 2)}
    out = pd.concat([df, pd.DataFrame([med_row])], ignore_index=True)
    out.to_csv(HERE / "exp3_sanity_token_parity.csv", index=False)

    c_lo, c_hi = med["GPT-5.4"], med["Gemini 3.1 Pro"]
    om = med["Qwen3-Coder-30B-A3B (open)"]
    print(out.to_string(index=False))
    print(f"\ncommercial median range: {c_lo:,} - {c_hi:,} tokens/task")
    print(f"open model median:       {om:,} tokens/task "
          f"({om/c_hi:.2f}x the heaviest commercial, {om/med['Opus 4.8']:.1f}x the lightest)")

    # ---- figure: per-task grouped bars (log y), commercial band shaded ----
    cols = ["gpt-5.4", "claude-opus-4-8", "gemini-3.1-pro-preview", "open"]
    labels = ["GPT-5.4", "Opus 4.8", "Gemini 3.1 Pro", OPEN_LABEL]
    x = np.arange(len(tasks)); w = 0.2
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    series = [piv_c["gpt-5.4"], piv_c["claude-opus-4-8"], piv_c["gemini-3.1-pro-preview"], piv_o]
    for i, (s, lab) in enumerate(zip(series, labels)):
        vals = [s.get(t, np.nan) for t in tasks]
        ax.bar(x + (i - 1.5) * w, vals, w, label=lab, color=COLORS[i], edgecolor="white", linewidth=0.2)
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(mticker.LogLocator(base=10))
    ax.set_xticks(x)
    ax.set_xticklabels([t.split("__")[-1] for t in tasks], rotation=40, ha="right", fontsize=7)
    ax.set_ylabel("total tokens per task")
    ax.legend(ncol=2, loc="upper left", fontsize=7.5)
    ax.grid(axis="y", which="major", alpha=0.25, lw=0.5)
    fig.tight_layout()
    pubstyle.save(fig, str(HERE / "fig7_sanity_tokens"))
    print(f"\nwrote exp3_sanity_token_parity.csv and fig7_sanity_tokens.(pdf/png)")


if __name__ == "__main__":
    main()
