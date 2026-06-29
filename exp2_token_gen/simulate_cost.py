#!/usr/bin/env python3
"""
simulate_cost.py — Monte-Carlo distribution of θ_GPU and serving cost under deployment uncertainty.

The Exp-2 matrix gives θ_GPU and board power for each (model × GPU) at saturation. A real deployment,
though, is a *random* choice: which open model, which GPU generation, how many GPUs, and at what market
prices. This script samples those choices and propagates them into distributions of:

  • θ_GPU          per-GPU saturated throughput  (tokens/s/GPU)
  • fleet θ        = G · θ_GPU                    (tokens/s, for a sampled fleet size G)
  • $ / 10⁶ tok    cloud-rental cost of generation (rental bundles power/facility)
  • kWh / 10⁶ tok  physical energy intensity      (measured board power × PUE)

and — convolving with the Exp-1 token-demand T_FTE (itself log-normal) — the per-engineer-year:

  • $ / engineer-yr   and   kWh / engineer-yr

This is the supply-side companion to Exp-1's demand Monte-Carlo; together they give the full
demand×supply distribution of the cost of an "AI software engineer".

Priors below are deliberately wide (2026 market). Edit them or pass --flags. Reads exp2_results/exp2_raw.csv.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# ---- priors (uniform lo,hi unless noted) ----
RENTAL_USD_HR = {"A100": (1.0, 2.5), "H100": (2.0, 4.5), "H200": (3.0, 6.0)}  # cloud $/GPU-hr (bundles power)
KWH_USD = (0.08, 0.16)        # $/kWh datacenter electricity
PUE = (1.10, 1.40)            # facility power overhead
GPU_MIX = {"A100": 0.35, "H100": 0.45, "H200": 0.20}   # deployment availability mix
MODEL_WEIGHTS = None          # None = uniform over measured models; or {basename: weight}


def load_saturated(csv_path):
    """model -> {gpu: (theta_gen, total_throughput, power_w)} at the saturated 8k/c64 point.
    theta_gen = generated (decode) tok/s = the paper's θ_GPU; total_throughput = prefill+decode tok/s,
    the basis that matches T_FTE (total tokens) and commercial $/token pricing."""
    cells = defaultdict(dict)
    for r in csv.DictReader(open(csv_path)):
        try:
            if int(r["max_concurrency"]) != 64 or int(r["input_len"]) != 8192:
                continue
            th = float(r["theta_gpu_tok_s"]); tt = float(r["total_token_throughput"]); pw = float(r["mean_power_w"])
        except (ValueError, KeyError):
            continue
        if th > 0 and tt > 0:
            cells[r["model"].split("/")[-1]][r["gpu_type"]] = (th, tt, pw)
    return cells


def build_catalog(cells):
    """Flat arrays over (model,gpu) cells + a sampling weight = P(model)·P(gpu|valid)."""
    models = sorted(cells)
    mw = {m: (MODEL_WEIGHTS.get(m, 0.0) if MODEL_WEIGHTS else 1.0) for m in models}
    tot = sum(mw.values()) or 1.0
    rows = []
    for m in models:
        valid = list(cells[m])
        gsum = sum(GPU_MIX.get(g, 0) for g in valid) or 1.0
        for g in valid:
            th, tt, pw = cells[m][g]
            w = (mw[m] / tot) * (GPU_MIX.get(g, 0) / gsum)
            rows.append((m, g, th, tt, pw, w))
    models_, gpus_, theta, total, power, w = zip(*rows)
    w = np.array(w); w = w / w.sum()
    return list(models_), list(gpus_), np.array(theta), np.array(total), np.array(power), w


def pct(a):
    p = np.percentile(a, [10, 50, 90])
    return f"P10={p[0]:,.4g}  P50={p[1]:,.4g}  P90={p[2]:,.4g}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "exp2_results" / "exp2_raw.csv"))
    ap.add_argument("--n", type=int, default=300_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tfte-median", type=float, default=159e6, help="Exp-1 T_FTE median (tokens/eng-yr)")
    ap.add_argument("--tfte-gsd", type=float, default=2.5, help="geometric SD of T_FTE (demand spread)")
    ap.add_argument("--gpu-range", type=int, nargs=2, default=[1, 16], help="log-uniform fleet size G")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    cells = load_saturated(args.csv)
    if not cells:
        print(f"no saturated (8k/c64) cells in {args.csv}"); return
    models, gpus, theta, total, power, w = build_catalog(cells)
    N = args.n

    print("=== measured saturated cells (deterministic) ===")
    for m, g, th, tt, pw in sorted(zip(models, gpus, theta, total, power)):
        print(f"  {g:5s} {m:34s} θ_GPU={th:8,.0f}  total={tt:9,.0f} tok/s  P={pw:6.1f} W")

    idx = rng.choice(len(theta), size=N, p=w)
    th = theta[idx]; tt = total[idx]; pw = power[idx]
    gpu_of = np.array(gpus)[idx]

    # prices
    rlo = np.array([RENTAL_USD_HR[g][0] for g in gpu_of]); rhi = np.array([RENTAL_USD_HR[g][1] for g in gpu_of])
    rental = rng.uniform(rlo, rhi)                      # $/GPU-hr
    kwh_price = rng.uniform(*KWH_USD, N)
    pue = rng.uniform(*PUE, N)
    G = np.exp(rng.uniform(np.log(args.gpu_range[0]), np.log(args.gpu_range[1]), N)).round().astype(int)

    # Cost/energy per 10⁶ TOTAL tokens (prefill+decode) — the basis that matches T_FTE and
    # commercial $/token pricing. (θ_GPU stays the headline *throughput* metric, on generated tokens.)
    usd_per_1M = rental / 3600.0 / tt * 1e6                          # cloud rental $/10⁶ total tok
    kwh_per_1M = pw / 1000.0 * (1e6 / tt) / 3600.0 * pue             # energy/10⁶ total tok (×PUE)
    energy_usd_per_1M = kwh_per_1M * kwh_price
    fleet_theta = G * th                                            # generated tok/s for the sampled fleet

    # convolve with demand T_FTE ~ log-normal(median, gsd)  [T_FTE = total tokens/eng-yr]
    sigma = np.log(args.tfte_gsd)
    tfte = rng.lognormal(np.log(args.tfte_median), sigma, N)
    usd_per_fte = tfte / 1e6 * usd_per_1M
    kwh_per_fte = tfte / 1e6 * kwh_per_1M

    print(f"\n=== Monte-Carlo (N={N:,}; random model/GPU/fleet/prices) ===")
    print(f"θ_GPU   (generated tok/s/GPU) : {pct(th)}")
    print(f"fleet θ (generated tok/s, G∈{args.gpu_range}): {pct(fleet_theta)}")
    print(f"$  / 10⁶ total tokens (rental): {pct(usd_per_1M)}")
    print(f"kWh / 10⁶ total tokens        : {pct(kwh_per_1M)}")
    print(f"energy $ / 10⁶ total tokens   : {pct(energy_usd_per_1M)}")
    print(f"\n=== × demand  (T_FTE median {args.tfte_median:,.0f} total tokens, GSD {args.tfte_gsd}) ===")
    print(f"$ / engineer-yr  (rental): {pct(usd_per_fte)}")
    print(f"kWh / engineer-yr        : {pct(kwh_per_fte)}")

    # figures
    out = ROOT / "exp2_results"
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    for a, data, title, xl in [
        (ax[0], th, "θ_GPU distribution", "tokens/s/GPU (saturated)"),
        (ax[1], usd_per_1M, "Serving cost (rental)", "$ per 10⁶ generated tokens"),
        (ax[2], usd_per_fte, "Cost per engineer-year", "$ / engineer-yr (rental × T_FTE)")]:
        a.hist(data, bins=np.logspace(np.log10(max(data.min(), 1e-6)), np.log10(data.max()), 60),
               color="#4C72B0", alpha=0.8)
        a.set_xscale("log"); a.set_title(title); a.set_xlabel(xl); a.grid(alpha=0.3)
        for q, ls in [(50, "-"), (10, ":"), (90, ":")]:
            a.axvline(np.percentile(data, q), color="k", ls=ls, lw=1)
    ax[0].set_ylabel("draws")
    fig.suptitle("Exp-2 supply-side Monte-Carlo: θ_GPU and serving cost under deployment uncertainty")
    fig.tight_layout()
    fig.savefig(out / "fig_cost_sim.png", dpi=300); fig.savefig(out / "fig_cost_sim.pdf")
    print(f"\nwrote {out}/fig_cost_sim.(png/pdf)")


if __name__ == "__main__":
    main()
