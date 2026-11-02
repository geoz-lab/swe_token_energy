# Final results — consolidated tables and publication figures

Clean, human-readable summaries of Experiment 1 (token **demand**) and Experiment 2 (inference
**supply**: throughput, energy, cost), plus journal-styled figures (no titles; captions belong in the
manuscript). Regenerate everything with:

```bash
python build_tables.py        # -> the 4 CSVs below (from ../exp1_results, ../exp2_results)
python make_pub_figures.py    # -> fig1..fig6 (.pdf + .png, 300 dpi)
python build_sanity.py        # -> exp3_sanity_token_parity.csv + fig7 (open-vs-commercial parity)
```

## Summary tables (CSV)

| file | what it contains |
|---|---|
| `exp1_demand_per_task.csv` | Per (benchmark × commercial model): n tasks, median/mean/p10/p90 total tokens per agentic task, and the median input / output / tool-observation split and API-call count. The token **demand** side. |
| `exp2_supply_all_cells.csv` | Every measured (open model × GPU × concurrency) cell: θ_GPU (generated tok/s/GPU), total throughput, TTFT/TPOT p50/p99, board power, tokens/J, GPU-seconds and kWh per 1M generated tokens, GPU utilisation. |
| `exp2_supply_saturated.csv` | The saturated (concurrency 64) headline rows — the numbers used for fleet/energy sizing. |
| `headline_summary.csv` | A flat list of the key cross-experiment numbers (demand medians + saturated θ_GPU and energy). |
| `exp3_sanity_token_parity.csv` | Open-vs-commercial token-parity check: per-task total tokens for the open model (Qwen3-Coder-30B-A3B) vs the 3 commercial models on the same 10 SWE-bench Lite tasks, plus the open model's API-call count and retry fraction, and a MEDIAN row. |
| `exp4_cost_per_engineer.csv` | Exp-3 five-layer model **per substituted software engineer**: P10/P50/P90 of token demand, engineers-per-GPU, W, kWh/yr, energy cost, and API-equivalent cost. |
| `exp4_scaling.csv` | Exp-3 illustrative linear scale-up of the per-engineer medians to global substitution scenarios (10/30/50/70/100 %). |
| `exp4_sensitivity.csv` | Exp-3 one-at-a-time sensitivity of per-engineer GPU count and energy cost. |
| `exp4_gpu_annual_energy_reference.csv` | Reference: energy + cost of running ONE GPU continuously for a year — at H100/H200 nameplate TDP (700 W) and at Exp-2 measured mean power per tier. |

Model metadata (architecture, active vs total parameters) is included in the Exp-2 tables so the
"active parameters drive throughput" finding is readable directly from the CSV.

## Figures (PDF for the manuscript, PNG for preview)

| file | content |
|---|---|
| `fig1_token_demand` | Exp-1: per-task token demand by model, SWE-bench vs SWE-Lancer (log box plots). |
| `fig2_daily_demand` | Exp-1: per-engineer daily token demand (T_FTE), log-normal, by model. |
| `fig3_throughput` | Exp-2: saturated θ_GPU by model, grouped by GPU (A100/H100/H200). |
| `fig4_energy` | Exp-2: energy (kWh) per 10⁶ generated tokens by model and GPU. |
| `fig5_active_scaling` | Exp-2: θ_GPU vs active parameters — the headline (small-active models dominate). |
| `fig6_cost_sim` | Exp-2: Monte-Carlo distribution of θ_GPU and serving cost under deployment uncertainty. |
| `fig7_sanity_tokens` | Sanity check: per-task token demand, open model vs the 3 commercial models (same 10 SWE-bench Lite tasks). |
| `fig8_engineers_per_gpu` | Exp-3: distribution of engineers served per GPU (P10/P50/P90). |
| `fig9_energy_per_engineer` | Exp-3: distribution of kWh per engineer-year. |
| `fig10_cost_per_engineer` | Exp-3: distribution of USD per engineer-year (API-equivalent). |
| `fig11_tfte` | Exp-3: fitted per-engineer-day token-demand distribution (from Exp-1). |

Style is defined once in `pubstyle.py` (serif, 8–9 pt, no top/right spines, embedded TrueType fonts,
tight bounding box). Source data: `../exp1_results/exp1_raw.csv`, `../exp2_results/exp2_raw.csv`,
`../exp2_sanity_check_results/sanity_raw.csv`.

**Sanity-check takeaway:** the open model (Qwen3-Coder-30B-A3B) used a median **445k tokens/task** vs the
commercial **32k–363k** range — same 10⁵–10⁶ order of magnitude, ~1.2× the heaviest commercial model
(Gemini), confirming token demand is set by the task + scaffold, not the specific model. See
`../exp2_summary.md` §10.
