#!/usr/bin/env python3
"""
fit_distributions.py — fit token-demand distributions to Experiment-1 data and build a
daily-workload (T_FTE) model: a developer-day = n_small SWE-bench-like tasks + n_lancer
SWE-Lancer tasks. Reads exp1_results/exp1_raw.csv; writes figures + prints a stats report.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "exp1_results" / "exp1_raw.csv"
OUT = ROOT / "exp1_results"
MODELS = ["gpt-5.4", "claude-opus-4-8", "gemini-3.1-pro-preview"]
LABEL = {"gpt-5.4": "GPT-5.4", "claude-opus-4-8": "Opus 4.8", "gemini-3.1-pro-preview": "Gemini 3.1 Pro"}
MCOLOR = {"gpt-5.4": "#55A868", "claude-opus-4-8": "#4C72B0", "gemini-3.1-pro-preview": "#C44E52"}
N_SMALL, N_LANCER, WORKDAYS, NDAYS = 3, 1, 250, 200_000


def bench(i):
    return "swe-bench" if "__" in i else "swe-lancer"


def load():
    cell = defaultdict(list)
    for r in csv.DictReader(open(CSV)):
        cell[(bench(r["instance_id"]), r["model"])].append(int(r["total_tokens"]))
    return cell


def fit_lognorm(x):
    x = np.asarray(x, float)
    s, loc, scale = stats.lognorm.fit(x, floc=0)        # s = sigma(log), scale = exp(mu) = median
    ks_ln = stats.kstest(x, "lognorm", args=(s, loc, scale)).pvalue
    a, gloc, gscale = stats.gamma.fit(x, floc=0)
    ks_g = stats.kstest(x, "gamma", args=(a, gloc, gscale)).pvalue
    (_osm, _osr), (_sl, _ic, r) = stats.probplot(np.log(x), dist="norm")  # QQ-line correlation
    return dict(median=scale, mu=np.log(scale), sigma=s, gsd=np.exp(s),
                mean=np.exp(np.log(scale) + s * s / 2), ks_lognorm=ks_ln, ks_gamma=ks_g, r2=r * r)


def main():
    cell = load()
    fits = {k: fit_lognorm(v) for k, v in cell.items()}

    print("\n=== Log-normal fits (token demand per task) ===")
    print(f"{'benchmark':<11}{'model':<22}{'n':>4}{'median':>11}{'sigma_log':>10}{'GSD':>7}"
          f"{'mean':>11}{'KS-p(LN)':>10}{'KS-p(Γ)':>9}{'QQ-R2':>8}")
    for k in sorted(fits):
        b, m = k
        f = fits[k]
        print(f"{b:<11}{m:<22}{len(cell[k]):>4}{f['median']:>11,.0f}{f['sigma']:>10.2f}{f['gsd']:>7.1f}"
              f"{f['mean']:>11,.0f}{f['ks_lognorm']:>10.2f}{f['ks_gamma']:>9.2f}{f['r2']:>8.3f}")

    # ---- daily-workload model (per model): n_small SWE-bench + n_lancer SWE-Lancer ----
    print(f"\n=== Daily-workload model: {N_SMALL} SWE-bench + {N_LANCER} SWE-Lancer task/day, "
          f"{WORKDAYS} workdays/yr ===")
    print(f"{'model':<22}{'daily median':>14}{'daily P10':>12}{'daily P90':>12}{'annual median (T_FTE)':>22}")
    daily = {}
    for m in MODELS:
        fb, fl = fits[("swe-bench", m)], fits[("swe-lancer", m)]
        rng = np.random.default_rng(0)
        small = stats.lognorm(fb["sigma"], 0, fb["median"]).rvs((NDAYS, N_SMALL), random_state=rng).sum(1)
        lanc = stats.lognorm(fl["sigma"], 0, fl["median"]).rvs((NDAYS, N_LANCER), random_state=rng).sum(1)
        d = small + lanc
        daily[m] = d
        med, p10, p90 = np.percentile(d, [50, 10, 90])
        print(f"{m:<22}{med:>14,.0f}{p10:>12,.0f}{p90:>12,.0f}{med * WORKDAYS:>22,.0f}")

    # sensitivity over n_small
    print(f"\n=== Sensitivity: annual median T_FTE (tokens/yr) vs n_small (n_lancer={N_LANCER}) ===")
    print(f"{'model':<22}" + "".join(f"{'n=' + str(n):>16}" for n in (1, 3, 5)))
    for m in MODELS:
        fb, fl = fits[("swe-bench", m)], fits[("swe-lancer", m)]
        row = f"{m:<22}"
        for n in (1, 3, 5):
            rng = np.random.default_rng(0)
            s = stats.lognorm(fb["sigma"], 0, fb["median"]).rvs((NDAYS, n), random_state=rng).sum(1)
            l = stats.lognorm(fl["sigma"], 0, fl["median"]).rvs((NDAYS, N_LANCER), random_state=rng).sum(1)
            row += f"{np.median(s + l) * WORKDAYS:>16,.0f}"
        print(row)

    # ---------------- Figure 2: fitted per-task distributions (in log10-token space) ----------------
    ln10 = np.log(10)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    xs = np.linspace(3.7, 6.7, 400)                      # log10(tokens)
    for ax, b in zip(axes, ("swe-bench", "swe-lancer")):
        for m in MODELS:
            x = np.log10(np.asarray(cell[(b, m)], float))
            f = fits[(b, m)]
            mu10, sig10 = np.log10(f["median"]), f["sigma"] / ln10   # log-normal is normal in log space
            ax.plot(xs, stats.norm(mu10, sig10).pdf(xs), color=MCOLOR[m], lw=2,
                    label=f"{LABEL[m]} (med {f['median']/1e3:.0f}k, σ={f['sigma']:.2f})")
            ax.plot(x, np.zeros_like(x), "|", color=MCOLOR[m], alpha=0.5, ms=10)   # data rug
        ax.set_xticks([4, 5, 6]); ax.set_xticklabels(["10k", "100k", "1M"])
        ax.set_xlabel("Tokens per task (log scale)")
        ax.set_title(f"{b}  (log-normal fit)"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    axes[0].set_ylabel("Density (in log-token space)")
    fig.suptitle("Per-task token-demand distributions, fitted log-normal by model")
    fig.tight_layout()
    fig.savefig(OUT / "fig_distfit.png", dpi=300); fig.savefig(OUT / "fig_distfit.pdf")

    # ---------------- Figure 3: daily-workload demand ----------------
    fig2, ax = plt.subplots(figsize=(8, 4.6))
    for m in MODELS:
        d = daily[m] / 1e6
        ax.hist(d, bins=np.logspace(np.log10(d.min()), np.log10(d.max()), 60),
                density=True, histtype="stepfilled", alpha=0.35, color=MCOLOR[m])
        f = fit_lognorm(daily[m])
        xs = np.logspace(np.log10(daily[m].min()), np.log10(daily[m].max()), 400)
        ax.plot(xs / 1e6, stats.lognorm(f["sigma"], 0, f["median"]).pdf(xs) * 1e6, color=MCOLOR[m], lw=2,
                label=f"{LABEL[m]}: median {np.median(daily[m])/1e6:.2f}M/day → {np.median(daily[m])*WORKDAYS/1e6:.0f}M/yr")
    ax.set_xscale("log"); ax.set_xlabel("Tokens per developer-day (log, millions)")
    ax.set_ylabel("Probability density")
    ax.set_title(f"Daily agentic token demand per engineer\n({N_SMALL} SWE-bench + {N_LANCER} SWE-Lancer task/day)")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(OUT / "fig_daily_demand.png", dpi=300); fig2.savefig(OUT / "fig_daily_demand.pdf")

    # ---------------- Figure 4: normal QQ-plots of log(tokens) (goodness-of-fit) ----------------
    fig3, axes = plt.subplots(2, 3, figsize=(11, 6.6))
    for i, b in enumerate(("swe-bench", "swe-lancer")):
        for j, m in enumerate(MODELS):
            ax = axes[i, j]
            x = np.log(np.asarray(cell[(b, m)], float))
            (osm, osr), (sl, ic, r) = stats.probplot(x, dist="norm")
            ax.scatter(osm, osr, s=16, color=MCOLOR[m], alpha=0.85, edgecolor="white", linewidth=0.3, zorder=3)
            ax.plot(osm, sl * osm + ic, "k--", lw=1.2, zorder=2)
            ax.set_title(f"{b} · {LABEL[m]}   (R²={r*r:.3f})", fontsize=9)
            ax.grid(alpha=0.3)
            if j == 0:
                ax.set_ylabel("ordered ln(tokens)")
            if i == 1:
                ax.set_xlabel("normal theoretical quantiles")
    fig3.suptitle("Normal QQ-plots of log(token demand) — log-normal goodness-of-fit\n"
                  "(points on the dashed line ⇒ log-normal)")
    fig3.tight_layout()
    fig3.savefig(OUT / "fig_qqplot.png", dpi=300); fig3.savefig(OUT / "fig_qqplot.pdf")

    print(f"\nwrote {OUT}/fig_distfit, fig_daily_demand, fig_qqplot (.png/.pdf)")


if __name__ == "__main__":
    main()
