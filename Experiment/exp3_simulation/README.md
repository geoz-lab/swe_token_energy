# Experiment 3 — Five-layer stochastic infrastructure model

Monte-Carlo framework linking software-engineering labor substitution → token demand → GPU fleet →
electricity → cost, propagating uncertainty across all layers. The two pivotal inputs are **fitted
from our measurements**: token demand from Experiment 1, throughput/power from Experiment 2.

## Run

```bash
python simulate.py        # reads ../exp1_results, ../final_results/exp2_supply_saturated.csv
                          # writes ../exp3_results/ (CSVs + figures)
```

## Files

```
params.py     prior distributions (triangular low/central/high) with literature citations
simulate.py   fit T_FTE (Exp-1) + theta/power (Exp-2); 5-layer Monte-Carlo; scenarios + sensitivity
```

## Layers (per substitution rate s)

```
L1  N_sub = N_eng * s
L2  D     = N_sub * T_FTE                     [T_FTE fitted from Exp-1, tokens/FTE-day]
L3  R     = D / 86400 ;  G = R / (theta * U)  [theta fitted from Exp-2 total-token throughput]
L4  P_fac = G * P_GPU * PUE ; E = P_fac*8760 ; C_energy = E * C_MWh   [P_GPU measured in Exp-2]
    C_API = 365 * D * C_token                 [retail-pricing comparison]
```

## Outputs (`../exp3_results/`)

| file | content |
|---|---|
| `exp3_fitted_inputs.json` | fitted T_FTE (P10/P50/P90) and the Exp-2 throughput/power ranges used |
| `exp3_scenarios.csv` | P10/P50/P90 of D, G, facility power, annual electricity, energy cost, API cost — per scenario |
| `exp3_sensitivity.csv` | one-at-a-time sensitivity of GPU count + energy cost (30 % scenario) |
| `fig_gpu`, `fig_energy`, `fig_cost` | median + P10–P90 band vs substitution rate |
| `fig_tfte` | the fitted per-FTE-day token-demand distribution |

See `../exp3_summary.md` for the full writeup, parameter sources, results, and findings.

## Editing assumptions

All priors live in `params.py` (developer count, tasks/day, utilization, PUE, electricity, API price,
GPU mix, deployed model set). The empirical inputs are re-fitted on every run, so re-running Exp-1 or
Exp-2 automatically flows through.
