#!/usr/bin/env python3
"""
simulate.py — Experiment 3: five-layer stochastic model expressed PER SUBSTITUTED SOFTWARE ENGINEER.

Instead of a global headcount, we report the inference infrastructure, electricity, and cost required
to substitute ONE software-engineering FTE. (Any deployment total is then just per-engineer × the
number of substituted engineers — an exact linear scale-up, shown in the scaling table.)

The two pivotal inputs are FITTED from our own measurements:
  T_FTE   (tokens / FTE-day)            <- Experiment 1 per-task log-normals, composed into a day
  theta   (total-token tok/s/GPU)       <- Experiment 2 saturated cells (sizing basis = TOTAL tokens)
  P_GPU   (board power, W)              <- Experiment 2 measured power (not assumed TDP)

Per-engineer layers (N_sub = 1):
  L2  D    = T_FTE                                    [total tokens / engineer-day]
  L3  R    = D / 86400 ;  g = R / (theta * U)         [tokens/s ; GPUs per engineer]
  L4  p    = g * P_GPU * PUE ; e = p * 8760 ;  c_e = e * C_MWh   [W ; Wh/yr ; $/yr per engineer]
      c_api = 365 * D * C_token                       [API-pricing comparison, $/yr per engineer]

Outputs (-> exp3_results/):
  exp3_fitted_inputs.json     fitted T_FTE and theta/power summaries
  exp3_per_engineer.csv       P10/P50/P90 per substituted engineer (demand, GPU, energy, cost)
  exp3_scaling.csv            illustrative scale-up to global substitution scenarios
  exp3_sensitivity.csv        one-at-a-time sensitivity (per-engineer GPU + energy cost)
  fig_engineers_per_gpu / fig_energy_per_eng / fig_cost_per_eng / fig_tfte  (.pdf/.png)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "final_results"))
import params as P
import pubstyle
pubstyle.apply()
import matplotlib.pyplot as plt

EXP1 = ROOT / "exp1_results" / "exp1_raw.csv"
EXP2 = ROOT / "final_results" / "exp2_supply_saturated.csv"
OUT = ROOT / "exp3_results"
OUT.mkdir(exist_ok=True)
N = 200_000


def tri(rng, lch, n):
    lo, c, hi = lch
    return np.full(n, c, float) if lo == hi else rng.triangular(lo, c, hi, n)


# ---------------- fit Layer-2 input: T_FTE from Exp-1 ----------------
def fit_tfte():
    df = pd.read_csv(EXP1)
    df["benchmark"] = np.where(df["instance_id"].str.contains("__"), "swe-bench", "swe-lancer")
    fits = {}
    for (b, m), g in df.groupby(["benchmark", "model"]):
        lx = np.log(g["total_tokens"].values.astype(float))
        fits[(b, m)] = (float(lx.mean()), float(lx.std(ddof=1)))
    return fits, sorted(df["model"].unique())


def sample_tfte(rng, fits, models, n, q_small, q_lancer, rho):
    out = np.zeros(n)
    midx = rng.integers(0, len(models), n)
    for j, m in enumerate(models):
        sel = midx == j
        k = int(sel.sum())
        if k == 0:
            continue
        mu_s, sg_s = fits[("swe-bench", m)]
        mu_l, sg_l = fits[("swe-lancer", m)]
        tot = np.zeros(k)
        for _ in range(int(round(q_small))):
            tot += rng.lognormal(mu_s, sg_s, k)
        for _ in range(int(round(q_lancer))):
            tot += rng.lognormal(mu_l, sg_l, k)
        out[sel] = tot
    return out * rho


# ---------------- fit Layer-3 input: theta + power from Exp-2 ----------------
def fit_supply():
    df = pd.read_csv(EXP2)
    df = df[df["model_name"].isin(P.DEPLOY_MODELS)]
    return [(r["gpu"], r["model_name"], float(r["total_throughput_tok_s"]), float(r["power_w"]))
            for _, r in df.iterrows()]


def sample_supply(rng, cells, n):
    w = np.array([P.GPU_MIX.get(c[0], 0) for c in cells], float); w /= w.sum()
    idx = rng.choice(len(cells), n, p=w)
    return np.array([cells[i][2] for i in idx]), np.array([cells[i][3] for i in idx])


# ---------------- per-engineer Monte-Carlo ----------------
def run(rng, n, fits, models, cells, overrides=None):
    o = overrides or {}
    q_small = o.get("Q_small", P.Q_SMALL[1])
    q_lancer = o.get("Q_lancer", P.Q_LANCER[1])
    rho = o.get("rho", P.RHO[1])
    tfte = o.get("T_FTE", sample_tfte(rng, fits, models, n, q_small, q_lancer, rho))
    if "theta" in o or "P_GPU" in o:
        theta = o.get("theta", np.full(n, np.median([c[2] for c in cells])))
        power = o.get("P_GPU", np.full(n, np.median([c[3] for c in cells])))
    else:
        theta, power = sample_supply(rng, cells, n)
    U = o.get("U", tri(rng, P.U_UTIL, n))
    pue = o.get("PUE", tri(rng, P.PUE, n))
    cmwh = o.get("C_MWh", tri(rng, P.C_MWH, n))
    ctok = o.get("C_token", tri(rng, P.C_TOKEN_PER_1M, n))

    D = tfte                                            # tokens/engineer-day
    R = D / P.SEC_PER_DAY                                # tokens/s per engineer
    g = R / (theta * U)                                 # GPUs per engineer (fractional)
    p_w = g * power * pue                                # W per engineer
    e_kwh = p_w * P.HOURS_PER_YEAR / 1000.0             # kWh / engineer-year
    c_energy = e_kwh / 1000.0 * cmwh                     # $/engineer-year (C_MWh is $/MWh)
    c_api = P.DAYS_PER_YEAR * D * ctok / 1e6            # $/engineer-year (ctok $/1M tok)
    return dict(D_day=D, D_year=D * P.DAYS_PER_YEAR, g_per_eng=g, eng_per_gpu=1.0 / g,
                W_per_eng=p_w, kWh_per_eng_yr=e_kwh, C_energy_per_eng_yr=c_energy,
                C_API_per_eng_yr=c_api)


def pcts(a):
    return [float(x) for x in np.percentile(a, [10, 50, 90])]


def main():
    fits, models = fit_tfte()
    cells = fit_supply()
    r = run(np.random.default_rng(0), N, fits, models, cells)

    # ---- fitted-inputs summary ----
    tf = r["D_day"]
    thetas = np.array([c[2] for c in cells]); powers = np.array([c[3] for c in cells])
    fitted = {
        "T_FTE_tokens_per_FTE_day": dict(zip(["p10", "p50", "p90"], pcts(tf))),
        "supply_total_throughput_tok_s": {"min": float(thetas.min()), "median": float(np.median(thetas)),
                                          "max": float(thetas.max())},
        "supply_power_w": {"min": float(powers.min()), "median": float(np.median(powers)),
                           "max": float(powers.max())},
        "deploy_models": P.DEPLOY_MODELS, "gpu_mix": P.GPU_MIX,
    }
    (OUT / "exp3_fitted_inputs.json").write_text(json.dumps(fitted, indent=2))

    # ---- per-engineer P10/P50/P90 ----
    metrics = [
        ("D_day", "tokens / engineer-day"),
        ("D_year", "tokens / engineer-year"),
        ("g_per_eng", "GPUs / engineer"),
        ("eng_per_gpu", "engineers / GPU"),
        ("W_per_eng", "W / engineer"),
        ("kWh_per_eng_yr", "kWh / engineer-year"),
        ("C_energy_per_eng_yr", "USD energy / engineer-year"),
        ("C_API_per_eng_yr", "USD API-equiv / engineer-year"),
    ]
    rows = []
    for key, unit in metrics:
        p10, p50, p90 = pcts(r[key])
        rows.append({"metric": key, "unit": unit, "p10": p10, "p50": p50, "p90": p90})
    pe = pd.DataFrame(rows)
    pe.to_csv(OUT / "exp3_per_engineer.csv", index=False)

    # ---- illustrative scale-up (per-engineer × substituted headcount) ----
    g50 = np.median(r["g_per_eng"]); kwh50 = np.median(r["kWh_per_eng_yr"])
    ce50 = np.median(r["C_energy_per_eng_yr"]); n_eng = P.N_ENG[1]
    srows = []
    for s in P.SUBSTITUTION_RATES:
        nsub = n_eng * s
        srows.append({"substitution_rate": s, "substituted_FTEs": int(nsub),
                      "GPUs_median": nsub * g50, "GWh_per_yr_median": nsub * kwh50 / 1e6,
                      "energy_cost_Musd_per_yr_median": nsub * ce50 / 1e6})
    pd.DataFrame(srows).to_csv(OUT / "exp3_scaling.csv", index=False)

    # ---- sensitivity (per-engineer GPUs/energy, one-at-a-time) ----
    base_g = np.median(r["g_per_eng"]); base_ce = np.median(r["C_energy_per_eng_yr"])
    knobs = {"tasks_small_per_day": ("Q_small", P.Q_SMALL),
             "tasks_lancer_per_day": ("Q_lancer", P.Q_LANCER),
             "utilization_U": ("U", P.U_UTIL), "PUE": ("PUE", P.PUE),
             "electricity_USD_MWh": ("C_MWh", P.C_MWH)}
    sens = []
    for label, (ov, (lo, c, hi)) in knobs.items():
        glo = np.median(run(np.random.default_rng(7), N, fits, models, cells, {ov: lo})["g_per_eng"])
        ghi = np.median(run(np.random.default_rng(7), N, fits, models, cells, {ov: hi})["g_per_eng"])
        elo = np.median(run(np.random.default_rng(7), N, fits, models, cells, {ov: lo})["C_energy_per_eng_yr"])
        ehi = np.median(run(np.random.default_rng(7), N, fits, models, cells, {ov: hi})["C_energy_per_eng_yr"])
        sens.append({"parameter": label, "low": lo, "high": hi,
                     "G_pct_low": 100 * (glo / base_g - 1), "G_pct_high": 100 * (ghi / base_g - 1),
                     "energycost_pct_low": 100 * (elo / base_ce - 1),
                     "energycost_pct_high": 100 * (ehi / base_ce - 1)})
    pd.DataFrame(sens).to_csv(OUT / "exp3_sensitivity.csv", index=False)

    _figures(r)
    _workflow(r, fitted)
    _report(pe)


def _figures(r):
    specs = [("eng_per_gpu", "engineers served per GPU", "fig_engineers_per_gpu", "#4C72B0"),
             ("kWh_per_eng_yr", "kWh per engineer-year", "fig_energy_per_eng", "#55A868"),
             ("C_API_per_eng_yr", "USD per engineer-year (API-equivalent)", "fig_cost_per_eng", "#DD8452"),
             ("D_day", "tokens per engineer-day (millions)", "fig_tfte", "#C44E52")]
    for key, xl, name, col in specs:
        d = r[key] / (1e6 if key == "D_day" else 1.0)
        fig, ax = plt.subplots(figsize=(4.4, 3.2))
        ax.hist(d, bins=np.logspace(np.log10(d.min()), np.log10(d.max()), 60), color=col,
                alpha=0.85, edgecolor="white", linewidth=0.2)
        ax.set_xscale("log"); ax.set_xlabel(xl); ax.set_ylabel("draws")
        for q, ls in [(50, "-"), (10, ":"), (90, ":")]:
            ax.axvline(np.percentile(d, q), color="black", ls=ls, lw=1.0)
        ax.grid(alpha=0.2, lw=0.5)
        fig.tight_layout()
        pubstyle.save(fig, str(OUT / name))


def _workflow(r, fitted):
    m = lambda k: np.median(r[k])
    print("=" * 66)
    print("  PER-SUBSTITUTED-ENGINEER WORKFLOW  (median draw)")
    print("=" * 66)
    print(f"  L1  Labor    : 1 substituted software-engineering FTE")
    print(f"  L2  Demand   : T_FTE = {m('D_day'):>12,.0f} tokens/engineer-day")
    print(f"                       = {m('D_year'):>12,.0f} tokens/engineer-year   [fitted from Exp-1]")
    print(f"  L3  Compute  : R     = {m('D_day')/P.SEC_PER_DAY:>12,.1f} tokens/s")
    print(f"                 theta, U (Exp-2 supply) -> g = {m('g_per_eng'):.5f} GPU/engineer")
    print(f"                 => 1 GPU serves ~{m('eng_per_gpu'):,.0f} engineers")
    print(f"  L4  Energy   : {m('W_per_eng'):>6.2f} W/engineer -> {m('kWh_per_eng_yr'):>6.1f} kWh/engineer-year")
    print(f"                 energy cost = ${m('C_energy_per_eng_yr'):>6.2f} / engineer-year")
    print(f"      API cost : ${m('C_API_per_eng_yr'):>8.0f} / engineer-year   [retail-token pricing]")
    print("=" * 66)


def _report(pe):
    print("\n=== Per substituted engineer (P10 / P50 / P90) ===")
    for _, r in pe.iterrows():
        if r["metric"] in ("D_year",):
            continue
        print(f"  {r['unit']:<34} {r['p10']:>12,.2f} {r['p50']:>12,.2f} {r['p90']:>12,.2f}")
    print(f"\nwrote exp3_per_engineer.csv, exp3_scaling.csv, exp3_sensitivity.csv, "
          f"exp3_fitted_inputs.json + 4 figures to {OUT}")


if __name__ == "__main__":
    main()
