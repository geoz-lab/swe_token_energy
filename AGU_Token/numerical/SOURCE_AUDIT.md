# Source and calculation audit of superseded assumptions

Reviewed 31 October 2026; archival status updated 1 November 2026. This document records why the original first-pass assumptions were superseded. The old scenario summary was a code demonstration, not an empirical estimate of the carbon footprint of replacing a software engineer. Its duplicate scripts, inputs, draw table and figures have been removed. The current seven-stage model is documented in [README](README.md), with source links consolidated in [REFERENCES](REFERENCES.md).

The old four-hour task bundle, facility multiplier table, and generic EIA national mix were retired. The current model reads the Microsoft workday evidence, duration scenarios, facility parameter table, data-center supply evidence, and EPA factors from the main numerical directory.

For later literature and vendor-specification additions, see [the 1 November evidence expansion](EVIDENCE_EXPANSION_2026-11-01.md). Request, session, and account-day token measures remain separate from local task traces because they cannot be merged without matched observations.

## Historical audit verdict

| Stage | Assumption audited at the time | Verification | Scientific status |
|---|---|---|---|
| FTE share | 30%, 50%, 70% | No cited study estimates these as SWE work replacement fractions | Scenario values only |
| Daily task volume | Four productive hours; 2/8/20 hours per task; 30/50/20% mix | No source supplies these values | Illustrative assumptions |
| Agent tokens | 270 local trajectories; raw reconstructed input plus output | Recomputed medians and group counts from raw CSV | Measured trace with tokenizer reconstruction; outcomes ungraded |
| Hardware | Six Qwen3-Coder A100/H100/H200 cells | Matched rounded values to raw benchmark CSV | Board power and benchmark throughput measured; workload transfer unvalidated |
| Facility energy | 1.2 server multiplier, 1.4 PUE central | DOE defines PUE and cites about 1.6 average, but does not support the central multipliers | Illustrative assumptions |
| Electricity mix | EIA 2023 U.S. utility-scale source shares | Shares transcribed; rounded shares sum to 100% | Historical U.S. generation context, not data-center procurement |
| Operational CO2e | EPA eGRID2023 U.S., CAMX, ERCT | Matched CO2e lb/MWh and unit conversions | Valid regional annual-average generation factors; location and year unresolved |
| Source life cycle | IPCC AR5 Annex III Table A.III.2 | Matched low/median/high for eight technologies | Historical cross-technology comparison, different boundary from EPA |

## 1. FTE share and work performed

[Cui et al.](https://www.microsoft.com/en-us/research/publication/the-effects-of-generative-ai-on-high-skilled-work-evidence-from-three-field-experiments-with-software-developers/) report a 26.08% increase (standard error 10.3%) in completed tasks across three randomized field experiments with 4,867 developers who received AI coding assistance. The treatment was access to a completion assistant. That number is neither an AI-autonomous work share nor a headcount displacement estimate. The larger gain for less experienced developers also does not imply a fixed junior-to-senior task ratio.

[Choudhuri et al.](https://www.microsoft.com/en-us/research/publication/you-shall-not-pass-where-and-why-developers-draw-the-line-on-ai-autonomy/) surveyed 448 professional developers about acceptable AI autonomy. Acceptance was lower for design, identity-defining, and human-facing work. This supports a task-specific delegation policy. It does not quantify the share of an engineer's day that an agent can replace.

[METR's time horizon series](https://metr.org/time-horizons/) predicts agent success as a function of human task duration on clean, self-contained benchmark tasks. METR explicitly says that its time horizon does not represent the ability to automate the same number of hours of a high-context professional's day. Therefore a benchmark horizon cannot calibrate 30–70% FTE share.

**Decision:** retain 30/50/70% as labeled scenarios. Estimate realized work substitution only after task-level success, human review, and company time-use data are measured.

## 2. Task-day formula and assumptions

The model assumes four productive task hours in one eight-hour paid day. The 30/50/20% split and 2/8/20 human hours per debug/development/system task have no supporting sample. The formula itself is dimensionally correct:

`tasks_k/day = productive_hours/day × time_share_k ÷ human_hours_per_task_k`.

The delegated task count is this baseline multiplied by the portion of family `k` included at a chosen work share. This is an expected daily rate; fractional tasks are appropriate for multi-day work. The **easy-first allocation is an independent assumption**, and it excludes system work until more than 80% of productive time is delegated. It must not be presented as observed agent capability.

[SWE-Lancer](https://openai.com/index/swe-lancer/) includes more than 1,400 freelance engineering tasks with monetary payouts and grading tests. Posted payout is not a measurement of hours. The local 20-task sample is not a representative time-use survey.

**Required replacement:** a role-stratified time diary or issue sample, explicit task boundaries, elapsed human effort, review effort, and overlapping work/meeting time. The developer-day denominator should then be estimated from data rather than fixed at four hours.

## 3. Token accounting

The local `Experiment/exp1_results/exp1_raw.csv` has 270 rows: 70 SWE-bench and 20 SWE-Lancer attempts for each of three models. All 270 `resolved` fields are blank. The local [experiment methods](../../Experiment/exp1_summary.md) explain that `raw_input_est` and `raw_output_est` are reconstructed with one tokenizer. The `total_tokens` field for SWE-bench is additionally scaled to match billed cost. For GPT-5.4 SWE-bench, the median `anchor_factor` is 0.556. Thus the billed/cost-adjusted total is not an observed physical token count.

Medians independently recomputed from `raw_input_est + raw_output_est`:

| Model | SWE-bench, n=70 | SWE-Lancer, n=20 |
|---|---:|---:|
| GPT-5.4 | 44,407 | 189,944 |
| Claude Opus 4.8 | 51,090 | 524,152 |
| Gemini 3.1 Pro | 428,426 | 1,490,306 |

These results are specific to mini-SWE-agent, not a measured Codex, Claude Code, or Gemini CLI workflow. The script uses GPT-5.4 only. The median raw input/output ratios for those GPT-5.4 trajectories are about 116:1 on SWE-bench and 343:1 on SWE-Lancer. Hidden reasoning, provider tokenizer differences, and actual prompt-cache treatment are not fully recovered from this local CSV. The paper by [Bai et al.](https://arxiv.org/abs/2604.22750) supports a stochastic, input-heavy model; its across-agent statistics should not be copied into a different scaffold as if they were local measurements.

**Required replacement:** provider-reported token categories, per-request input and output, cache creation/read, reasoning where exposed, repeated runs, success grading, and accepted work units for each product/harness.

## 4. GPU throughput and board power

The six rows in `stage4_hardware_measured.csv` match rounded Qwen3-Coder-30B-A3B values in `Experiment/exp2_results/exp2_raw.csv`. The local [protocol](../../Experiment/exp2_token_gen/README.md) states that its benchmark uses an 8,192-token prompt and 1,024-token output at concurrency 1 or 64, with prefix caching. The CSV's `total_token_throughput` includes input plus output. The GPT-5.4 agent traces have much larger input/output ratios. Total tokens per second under one mix cannot be transferred to the other by dividing total tokens. Cache hit rate, prefill, decode, queueing, and power must be matched to the agent trace.

Concurrency 64 is a saturated reference. On H100 for this model, the local table gives median first-token latency of about 22.7 seconds at concurrency 64, versus 0.105 seconds at concurrency 1. Treating c64 as an interactive deployment is unjustified. The energy calculation also uses a closed model's reconstructed demand with an open model's measured serving efficiency. This is a proxy scenario, not the footprint of GPT-5.4 itself.

A production trace study from [Microsoft Research](https://www.microsoft.com/en-us/research/publication/agentic-coding-in-the-wild-characterizing-github-copilot-at-production-scale/) reports about 90% KV-cache hits within a turn and 55% across turns, with model switches disrupting cache reuse. That corroborates the need to measure cache behavior and model routing together. It does not provide the GPU joules per request needed here.

**Required replacement:** replay the empirical agent prompt/output length sequence on each open model and accelerator; measure prefill, decode, cache hits, request latency, board and server watts in the same interval. Benchmark a common quality threshold.

## 5. Facility electricity and utilization

The local board-power readings are genuine for the tested cells. The [DOE/FEMP design guide](https://www.energy.gov/sites/default/files/2024-07/best-practice-guide-data-center-design.pdf) defines PUE as total facility energy divided by total IT energy and says an average data center PUE is about 1.6, citing a 2022 large-data-center average of 1.55. It gives no value for GPU-to-server overhead applicable to these Sherlock nodes. The model's triangular 1.0–1.4 server overhead and 1.2–1.6 PUE are uncalibrated.

GPU board joules during a benchmark are not the same as marginal facility electricity. Shared server idle draw, GPU idle time, and utilization allocation need a defined accounting policy. A company fleet estimate must size the fleet for demand peaks and latency, then account for energy during idle and active periods. Multiplying per-request busy-time energy by request count omits that standing energy.

For clarity, facility power is `IT power × PUE`; dividing board power by PUE would be dimensionally and conceptually wrong. The numerical script multiplies by PUE. This remains a scenario assumption until host and facility power are measured for the same serving workload.

**Decision:** call the present energy figure a throughput-and-board-power demonstration. Do not use it as a lower confidence bound; the serving workload and overhead are mismatched.

## 6. U.S. electricity mix

[EIA's detailed 2023 utility-scale table](https://www.eia.gov/tools/faqs/faq.php?id=427) supports the listed rounded shares. Utility-scale generation excludes 73.62 billion kWh of estimated small-scale solar in that year. The table includes negative net generation for pumped storage, so its -0.1% row cannot be interpreted as a probability of power source. The petroleum/other-gas value of 0.7% is an aggregation of two rounded categories. Although the stage CSV sums to 100%, it is not a categorical probability distribution suitable for Monte Carlo source draws.

The [EIA 2025 overview](https://www.eia.gov/energyexplained/electricity/electricity-in-the-us-generation-capacity-and-sales.php) gives a more recent broad U.S. utility-scale mix. Neither national mix identifies a data center's purchase mix or which generator responds to its incremental load. The [DOE data-center update](https://www.energy.gov/documents/united-states-data-center-energy-usage-report-2025-update) estimates 192 TWh of U.S. data-center electricity in 2024. That total is context, not a multiplier in this task-level model.

**Required replacement:** select U.S. data-center locations and load profiles. Use the matching eGRID subregion for annual location-based accounting. For a consequential scenario, select a specific scenario/year and time-varying long-run marginal factor from [NREL Cambium](https://www.nrel.gov/analysis/cambium.html) or another documented grid model. The existing marginal-emissions workbooks require a separate provenance and scenario audit before use.

## 7. Emission factors and boundaries

[EPA eGRID2023](https://www.epa.gov/egrid/summary-data) reports CO2e total output rates of 770.884 lb/MWh for the U.S., 429.983 for CAMX, and 736.629 for ERCT. Conversion is `lb/MWh × 0.45359237 / 1000 = kg/kWh`, yielding 0.349667, 0.195037, and 0.334129 kg/kWh. A 0.000002 kg/kWh rounding error in the initial U.S. ledger entry was corrected. [EPA guidance](https://www.epa.gov/system/files/documents/2025-01/using-egrid-to-determine-emissions.pdf) supports multiplying purchased electricity by a regional total output rate for a location-based estimate. This is operational generation emissions, not a life-cycle or marginal factor.

[IPCC AR5 Annex III, Table A.III.2](https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_wg3_ar5_annex-iii.pdf) supports the separate technology life-cycle factor rows. The source is older and spans technology/site differences, particularly hydropower; its low and high values are literature ranges, **not P10/P90 probabilities**. The solar and wind rows use utility-PV and onshore-wind proxies for broad EIA categories. There is no defensible factor currently assigned to the petroleum/other/negative-storage portion.

**Decision:** use EPA eGRID for the current operational calculation. Use IPCC only for a labeled life-cycle source comparison. Do not multiply EIA source shares by IPCC factors and call the result a verified U.S. data-center factor.

## 8. Monte Carlo and company extrapolation

The script samples empirical token rows, six measured hardware cells, and two assumed triangular multipliers. It does **not** sample FTE share, task durations, task allocation, success, cache behavior, grid factors, or model efficacy. Therefore the conditional 10th/90th percentiles in `scenario_summary.csv` are not a comprehensive uncertainty interval.

The initial company output multiplied a single engineer-day draw by all employees, effectively making every person's task and hardware random variation perfectly correlated. That was incorrect for company uncertainty. The script now reports only a median scenario extrapolation for company sizes, with interval columns blank. A company model must distinguish shared systematic uncertainty (task mix, PUE, grid region) from individual random variation, model utilization, and peak capacity.

The three named cases also change work share, grid, and concurrency at once. They cannot isolate any one driver's effect. The final design should cross these axes factorially and show sensitivity with other factors held fixed. The “fan” should use separate units at each stage, with conditional bands and uncertainty source labels.

## Correction queue, in order

1. Obtain graded success and human review data on matched tasks. Without this, the numerator “work performed” is undefined.
2. Replace the assumed task-day schedule with role-stratified time-use observations and match benchmark tasks to those families.
3. Obtain actual per-call token telemetry for Codex, Claude Code, Gemini, and the chosen open model, including cache and reasoning categories.
4. Replay agent-shaped workloads on GPUs at a stated latency service level; measure GPU/server power, prefill, decode, and cache.
5. Choose U.S. data-center location(s) and audit the marginal-emissions workbook's scenario/year/geography before consequential results.
6. Rebuild Monte Carlo with separate between-company, between-engineer, between-task, and measurement uncertainties; then produce the quantitative fan and company intervals.
