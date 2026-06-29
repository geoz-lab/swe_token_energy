# Experiment 3 — Five-Layer Monte-Carlo Model: Cost and Energy per Substituted Software Engineer

A stochastic framework that propagates uncertainty from a single substituted software-engineering FTE
through token demand, GPU fleet, electricity, and cost. We report everything **per substituted
engineer** — any deployment total is then per-engineer × the number of substituted engineers (an exact
linear scale-up, §7). The two pivotal inputs are **fitted from our own measurements**: token demand
from Experiment 1, inference throughput and power from Experiment 2. Every other parameter is an
explicit probability distribution drawn from the literature, listed in full below.

## 1. The five layers (per substituted engineer)

```
  L1  Labor    :  one substituted SWE-engineering FTE                         (basis)
  L2  Demand   :  D      = T_FTE                          [total tokens / engineer-day]
  L3  Compute  :  R      = D / 86,400                     [tokens / s]
                  g      = R / (theta · U)                [GPUs / engineer]
  L4  Energy   :  p      = g · P_GPU · PUE                [W / engineer]
                  e      = p · 8,760 / 1000               [kWh / engineer-year]
                  c_e    = e / 1000 · C_MWh               [USD energy / engineer-year]
      Cost(API):  c_api  = 365 · D · C_token              [USD / engineer-year, retail comparison]
```

The uncertain vector is
`X = (T_FTE, theta, U, P_GPU, PUE, C_MWh, C_token)` plus the workload-composition counts
`(Q_small, Q_lancer)`. We draw **N = 200,000** Monte-Carlo samples.

## 2. All input distributions and parameters

### 2.1 Fitted from Experiment 1 — token demand `T_FTE` (empirical log-normal mixture)

Each task's token count is **log-normal**, `ln(tokens) ~ Normal(μ, σ)`, with parameters fitted by MLE
to the Exp-1 measurements (270 task-runs). A developer-day is composed as `Q_small` SWE-bench tasks +
`Q_lancer` SWE-Lancer tasks, with the **model drawn uniformly** per sample (capturing model-choice
uncertainty). Retries/iterations are already contained in the measured token counts, so the retry
multiplier `ρ = 1`.

Fitted per-task log-normal parameters (μ, σ in natural-log space; median = e^μ):

| benchmark | model | μ | σ | median tokens | n |
|---|---|---:|---:|---:|---:|
| SWE-bench | GPT-5.4 | 10.250 | 0.428 | 28,279 | 70 |
| SWE-bench | Opus 4.8 | 10.664 | 0.980 | 42,799 | 70 |
| SWE-bench | Gemini 3.1 Pro | 12.583 | 0.521 | 291,526 | 70 |
| SWE-Lancer | GPT-5.4 | 12.272 | 0.562 | 213,693 | 20 |
| SWE-Lancer | Opus 4.8 | 12.953 | 0.768 | 422,156 | 20 |
| SWE-Lancer | Gemini 3.1 Pro | 14.224 | 0.520 | 1,504,714 | 20 |

Resulting **`T_FTE` (total tokens per engineer-day)** distribution, under the fully-agentic daily
volume of §2.3:

| | P10 | P50 | P90 |
|---|---:|---:|---:|
| tokens/engineer-day | 1,437,340 | 3,468,466 | 14,433,131 |

(P50 ≈ 3.5 M/day → ~1.27 B tokens/engineer-yr. This is ~6× Exp-1's conservative 3+1-task/day annual
figure: under a fully-agentic production mode an FTE-equivalent of output is far above a human's
traditional task pace — §2.3. Per-task tokens are measured; tasks/day is the modeled volume.)

### 2.2 Fitted from Experiment 2 — supply `theta` and `P_GPU` (empirical, sampled)

Each draw samples a deployed open model and a GPU; the pair's measured saturated values are used.
Because `T_FTE` counts **total** tokens, sizing uses the measured **total-token throughput**, and power
uses the measured **board power** (not assumed TDP). Deployed set and the empirical cells:

- **Models** (uniform over those that ran): `gpt-oss-20b`, `Qwen3-Coder-30B-A3B`, `Qwen3-Coder-Next`,
  `Kimi-Dev-72B`.
- **GPU mix** (categorical): A100 0.35, H100 0.45, H200 0.20.
- **`theta` (total tok/s/GPU)**: empirical range **5,474 – 40,749** (min Kimi-72B/H200, max gpt-oss/H200).
- **`P_GPU` (board W)**: empirical range **338 – 697 W**.

### 2.3 Literature priors — triangular(low, central, high)

| Parameter | Symbol | Low | Central | High | Distribution | Source |
|---|---|---:|---:|---:|---|---|
| Tasks/day (small, SWE-bench) | `Q_small` | 10 | 20 | 30 | triangular | fully-agentic daily volume (tens of issue/bug-fix tasks) |
| Tasks/day (large, SWE-Lancer) | `Q_lancer` | 2 | 4 | 6 | triangular | fully-agentic daily volume (several freelance-job-scale tasks) |
| Retry multiplier | `ρ` | 1.0 | 1.0 | 1.5 | triangular (fixed 1 by default) | retries already in measured tokens |
| GPU utilization | `U` | 0.30 | 0.50 | 0.70 | triangular | production LLM-serving utilization |
| Power usage effectiveness | `PUE` | 1.30 | 1.56 | 1.70 | triangular | Uptime Institute 2024 (global avg 1.56; new builds ≈1.3) |
| Electricity price | `C_MWh` | $40 | $60 | $100 | triangular | US industrial electricity range |
| API token price | `C_token` | $0.5 | $2 | $5 / 1M tok | triangular | commercial blended pricing |

Context-only (used for the §7 scale-up, not the per-engineer headline):

| Parameter | Symbol | Low | Central | High | Source |
|---|---|---:|---:|---:|---|
| Global developer count | `N_eng` | 19.6 M | 24 M | 28.7 M | JetBrains 2024 (19.6 M prof.); Evans Data / Statista (27–28.7 M) |
| Substitution rate | `s` | — | {10,30,50,70,100}% | — | scenario sweep |

All priors live in `exp3_simulation/params.py`; the two empirical inputs are re-fitted on every run.

## 3. Workflow (median draw)

```
  L1  Labor    : 1 substituted software-engineering FTE
  L2  Demand   : T_FTE =    3,468,466 tokens/engineer-day
                       = 1,265,990,090 tokens/engineer-year    [fitted from Exp-1]
  L3  Compute  : R     =         40.1 tokens/s
                 theta, U (Exp-2) -> g = 0.00571 GPU/engineer
                 => 1 GPU serves ~175 engineers
  L4  Energy   :  4.14 W/engineer -> 36.3 kWh/engineer-year
                 energy cost = $2.35 / engineer-year
      API cost : $3,095 / engineer-year                        [retail-token pricing]
```

## 4. Results — per substituted software engineer

Full distribution (P10 / P50 / P90), N = 200,000 (`exp3_results/exp3_per_engineer.csv`):

| Quantity | P10 | P50 | P90 |
|---|---:|---:|---:|
| tokens / engineer-day | 1,437,340 | 3,468,466 | 14,433,131 |
| **engineers served per GPU** | 38 | **175** | 744 |
| GPUs / engineer | 0.0013 | 0.0057 | 0.026 |
| W / engineer | 0.94 | 4.14 | 20.9 |
| **kWh / engineer-year** | 8.3 | **36.3** | 183 |
| **USD energy / engineer-year** | 0.53 | **2.35** | 12.1 |
| **USD API-equivalent / engineer-year** | 1,048 | **3,095** | 14,707 |

## 5. Findings

1. **One GPU serves ~175 engineers** (median; P10–P90 38–744) under a fully-agentic daily volume (tens
   of small + several large tasks/engineer-day). Even at this heavy workload, agentic
   software-engineering inference is light per engineer because generated tokens are a small fraction of
   the work and modern accelerators are fast.
2. **Energy per engineer is small: ~36 kWh/year** (P10–P90 8–183) — about the annual electricity of a
   single LED bulb left on, and orders of magnitude below a developer's personal/office energy
   footprint. The **electricity cost is ~$2.35/engineer-year**.
3. **Electricity is a negligible fraction of the service price.** The API-priced equivalent is
   **~$3,095/engineer-year** — about **1,300× the raw electricity cost** ($2.35). The gap is GPU
   depreciation, facilities, networking, operations, and provider margin: the *energy* of automating an
   engineer is negligible; the *price* is set by capital and margin, not physics.
4. **Uncertainty is workload- and utilization-driven, not hardware-driven** (§6).

## 6. Sensitivity (one-at-a-time, per-engineer)

Median GPU-per-engineer and energy-cost response to each parameter's low/high
(`exp3_results/exp3_sensitivity.csv`):

| Parameter | low → high | GPU/engineer | energy cost/engineer |
|---|---|---:|---:|
| utilization `U` | 0.30 → 0.70 | +65% / −29% | +65% / −29% |
| SWE-Lancer tasks/day | 2 → 6 | −31% / +30% | −30% / +30% |
| SWE-bench tasks/day | 10 → 30 | −21% / +20% | −21% / +21% |
| electricity price | $40 → $100 | 0% / 0% | −38% / +54% |
| `PUE` | 1.30 → 1.70 | 0% / 0% | −14% / +12% |

The infrastructure footprint is dominated by **serving utilization** and **how much agentic work a
developer-day contains** (both task counts) — operational/empirical quantities, not hardware specs.
`PUE` and electricity price move *cost* but not *GPU count* (by construction).

## 7. Illustrative scale-up (per-engineer × substituted headcount)

Per-engineer medians scale linearly. For context, applying them to global developer substitution
(`N_eng` central 24 M, `exp3_results/exp3_scaling.csv`):

| Substitution `s` | Substituted FTEs | GPUs (median) | GWh/yr (median) | Energy cost (median) |
|---:|---:|---:|---:|---:|
| 10 % | 2.4 M | 13,700 | 87 | $5.6 M |
| 30 % | 7.2 M | 41,100 | 261 | $16.9 M |
| 50 % | 12.0 M | 68,500 | 435 | $28.2 M |
| 70 % | 16.8 M | 95,900 | 609 | $39.5 M |
| 100 % | 24.0 M | 137,000 | 870 | $56.4 M |

Even substituting *all* global SWE labor implies a median ~137,000 GPUs and ~0.87 TWh/yr — still
negligible against global data-center electricity (~400+ TWh/yr). (This table is illustrative context;
the per-engineer figures in §4 are the primary result.)

## 8. Figures (`exp3_results/`, journal style)

| file | content |
|---|---|
| `fig_engineers_per_gpu` | distribution of engineers served per GPU (P10/P50/P90 marked) |
| `fig_energy_per_eng` | distribution of kWh per engineer-year |
| `fig_cost_per_eng` | distribution of USD per engineer-year (API-equivalent) |
| `fig_tfte` | fitted per-engineer-day token-demand distribution |

## 9. Limitations

- **Steady-state serving.** `T_FTE` is a per-working-day demand served continuously (provisioned GPUs
  drawing power 8,760 h/yr); bursty or business-hours load changes the GPU count for a fixed SLO.
- **Total-token sizing.** Throughput is the saturated total-token rate; a latency-bounded deployment
  operates below saturation (Exp-2 §6.4), raising `g`.
- **Demand from commercial models.** `T_FTE` is fitted from Exp-1 commercial trajectories; deployed open
  models consume a comparable but somewhat higher per-task budget (Exp-2 §10) — conservative for *price*,
  a mild under-count for *energy*.
- **Inference only.** Excludes training, off-node data movement, embodied energy, and non-SWE workloads.

## 10. Reproducibility

`exp3_simulation/`: `params.py` (all priors, cited), `simulate.py` (fit Exp-1/Exp-2 inputs + per-engineer
Monte-Carlo + sensitivity + scaling). Outputs to `exp3_results/`: `exp3_fitted_inputs.json`,
`exp3_per_engineer.csv`, `exp3_scaling.csv`, `exp3_sensitivity.csv`, and the four figures (shared
`final_results/pubstyle.py` style). Run: `python exp3_simulation/simulate.py`.
