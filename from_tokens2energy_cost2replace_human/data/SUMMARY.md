# Research Data Summary — From Tokens to Energy
*Processed: 2026-05-06 | Sources: 42 [PRIMARY], 46 [SECONDARY], 4 [ESTIMATE]*

---

## Table of Contents

1. [Overall Data Quality Assessment](#overall-data-quality-assessment)
2. [Locked Assumptions](#locked-assumptions)
3. [Top 10 Key Numbers for the Paper](#top-10-key-numbers-for-the-paper)
4. [The Core Quantitative Chain](#the-core-quantitative-chain)
5. [Critical Gaps](#critical-gaps)
6. [Data Points to Verify Before Publication](#data-points-to-verify-before-publication)
7. [Recommended Next Steps](#recommended-next-steps)

---

## Overall Data Quality Assessment

The macro-level figures — IEA energy data, BLS workforce data, hyperscaler capex from company filings, and NVIDIA revenue — are strong [PRIMARY] sources that can be cited directly. The weakest links are the global developer headcount (two credible [SECONDARY] estimates disagree by 46%, requiring the paper to use a midpoint with acknowledged uncertainty), the average global software engineer salary (self-reported [SECONDARY] data from Glassdoor/EZtek, likely biased upward), and the per-task agentic token consumption (arXiv:2604.22750 is a pre-print with solid methodology but not yet peer-reviewed). The McKinsey automation percentage figures are widely cited [SECONDARY] trade reports — robust for directional argument but should not be the sole basis for quantitative claims. The Goldman Sachs $1.1T capex forecast is cited via third-party aggregators and requires retrieval of the original research before publication.

---

## Locked Assumptions

The following conflicting data points have been resolved. **Use these values in all models and calculations; do not re-open unless new primary data is available.**

| Assumption | Locked Value | Alternatives Considered | Rationale |
|-----------|-------------|------------------------|-----------|
| H100 power (inference) | **700 W/GPU** | 1,275 W (DGX full-load spec) | 700 W is the per-GPU TDP under inference; 1,275 W is max system power under training load. Use 700 W for inference scenarios. |
| H100 power (peak/ceiling) | **1,275 W/GPU** | — | Use only for worst-case energy calculations. |
| Data center construction cost | **$15 M/MW** | $6 M (older efficiency builds), $10–12 M (Cushman & Wakefield standard), $20 M+ (liquid-cooled AI) | Mid-estimate for AI-optimized facility (2024–2026). |
| Global SW developers | **24 million** | 19.6 M (JetBrains narrow), 28.7 M (Evans Data broad), 47.2 M (upper bound) | Midpoint of two credible professional-developer estimates. Do not use 47.2 M in the model. |
| Agentic token multiplier | **50–500× (practical)** | 1,000× (arXiv:2604.22750 vs. single-turn code Q&A) | 50–500× is the enterprise deployment range. 1,000× is valid only when contrasting with a single chat prompt; useful in the introduction, not in the scenario model. |
| Copper demand (data centers, 2030) | **375 K tonnes/year** | 1.1 M tonnes (Sprott) | Macquarie figure covers data centers only; Sprott includes the broader AI/EV supply chain. Use Macquarie for the data-center-specific claim. |

---

## Top 10 Key Numbers for the Paper

| Rank | Number | What It Means | Source Quality |
|------|--------|--------------|----------------|
| 1 | **$133,080/year** | US SW developer median salary — break-even benchmark | [PRIMARY] — BLS OES May 2024 |
| 2 | **~24 million** | Global professional software developers (working estimate) | [SECONDARY] — midpoint of JetBrains and Evans Data |
| 3 | **4 million tokens/day** | Per-FTE token demand, fully agentic mode | [SECONDARY] — derived from arXiv:2604.22750 |
| 4 | **$9,000/FTE-year** | AI token cost to run one agentic engineering FTE at frontier API pricing | [ESTIMATE] — ~6.8% of human salary |
| 5 | **30%** | Engineering work hours automatable by 2030 (McKinsey accelerated scenario) | [SECONDARY] — McKinsey MGI May 2024 |
| 6 | **7.2 million FTEs** | SW engineering FTE-equivalents effectively replaced at 30% automation | [ESTIMATE] — derived |
| 7 | **47.4 GW** | Current global data center average power demand (from IEA 415 TWh, 2024) | [PRIMARY] — IEA "Energy and AI" |
| 8 | **107.9 GW** | Projected global data center avg power demand by 2030 (IEA Base Case) | [PRIMARY] — IEA "Energy and AI" |
| 9 | **$448 billion** | 2025 combined hyperscaler capex guidance (4 companies) | [PRIMARY] — earnings reports |
| 10 | **~14,000 H100s** | GPUs required to serve 1 million agentic engineering FTEs | [ESTIMATE] — derived from [SECONDARY] benchmark |

---

## The Core Quantitative Chain

### Locked Model Inputs

| Parameter | Value | Source Quality |
|-----------|-------|----------------|
| Global SW developers | 24 million | [SECONDARY] |
| Tokens/FTE/day (agentic) | 4 million | [SECONDARY] derived |
| API cost (blended frontier) | $9/MTok | [PRIMARY] |
| H100 throughput (70B, batch 64, FP16) | 3,311 tok/s | [SECONDARY] |
| H100 power (inference) | 700 W/GPU | [PRIMARY] derived |
| PUE (global avg 2024) | 1.56 | [SECONDARY] |
| Construction cost | $15 M/MW | [SECONDARY] derived |
| Energy cost | $60/MWh | [ESTIMATE] blended |
| Avg global SW salary | $70,877/year | [SECONDARY] |

### Scenario Model: LOW / MID / HIGH

| Step in Chain | LOW (10%) | MID (30%) | HIGH (80%) |
|--------------|-----------|-----------|-----------|
| Engineering FTEs replaced | 2.4 million | **7.2 million** | 19.2 million |
| Tokens/day (total) | 9.6 trillion | **28.8 trillion** | 76.8 trillion |
| H100 GPUs needed | ~33,700 | **~101,000** | ~269,000 |
| GPU power demand | 23.6 MW | **70.7 MW** | 188 MW |
| Total facility power (PUE 1.56) | 36.8 MW | **110 MW** | 293 MW |
| Data center capex | $552 M | **$1.65 B** | $4.40 B |
| Annual energy cost | $19 M/yr | **$58 M/yr** | $154 M/yr |
| AI token cost/FTE-year | $9,000 | **$9,000** | $9,000 |
| Annual labor cost savings | $170 B/yr | **$511 B/yr** | $1.36 T/yr |
| AI cost as % of human salary | 6.8% | **6.8%** | 6.8% |

> ⚠️ **Critical Framing Note:** The 110 MW of additional power demand in the MID scenario is approximately **0.10% of the IEA's projected 2030 global data center power demand (107.9 GW)**. Engineering automation alone is not a primary driver of the data center energy story. The correct narrative: the same AI infrastructure buildout consuming 108 GW globally by 2030 makes engineering substitution economically trivial once AI capability reaches production grade. The paper should anchor the energy story to the macro AI buildout, not to engineering substitution power demand specifically.

---

## Critical Gaps

1. **Global engineering total compensation pool** — No authoritative aggregate exists. The ~$1.7T figure is derived from two [SECONDARY] sources. Uncertainty range: $1.2T–$3T depending on definition of "engineering."

2. **Per-FTE daily token consumption (Copilot mode)** — The 120K tokens/day figure is an illustrative billing example, not empirical data. Actual usage likely varies 10–100× across developers.

3. **Devin/SWE-agent token count per task (in tokens)** — Only ACU-based dollar pricing is published. Token-level detail is back-calculated from cost, not directly measured.

4. **arXiv:2604.22750 peer review status** — This pre-print is the load-bearing anchor for all agentic token calculations. The 1–3.5M tokens/task range is across models; per-model medians are needed for a tighter estimate.

5. **H100 power draw under inference (independent benchmark)** — DGX spec implies 1,275 W/GPU (system max); 700 W is NVIDIA's inference TDP. The 2× gap changes energy estimates materially. MLPerf Inference power data needed.

6. **McKinsey Nov 2025 "57% automatable"** — Currently cited via a Medium summary of a McKinsey report. Must retrieve the original MGI publication before use.

7. **IEA country-level breakdown of 415 TWh** — Full country table not extracted; available in the full IEA "Energy and AI" report (April 2025).

---

## Data Points to Verify Before Publication

| Priority | Data Point | Current Source | Required Action |
|----------|-----------|----------------|-----------------|
| HIGH | 1–3.5M tokens/task (agentic) | arXiv:2604.22750 pre-print | Retrieve full paper + GitHub supplementary data at github.com/LongjuBai/agent_token_consumption_analysis |
| HIGH | McKinsey 57% automatable | Medium summary (2nd-order citation) | Retrieve original McKinsey MGI Nov 2025 report |
| HIGH | Goldman Sachs $1.15T cumulative capex | Third-party financial aggregator | Retrieve original GS Equity Research note "Tracking Trillions" |
| HIGH | Nuclear PPA price ~$100–$112/MWh | Bloomberg/Jefferies analyst estimate | Note as analyst estimate in paper; actual contract is confidential |
| MEDIUM | H100 700W inference power draw | Inferred/spec-derived | Cross-check against MLPerf Inference v4.1 power results at mlcommons.org |
| MEDIUM | Global SW salary $70,877 | Glassdoor/EZtek self-reported | Replace with OECD/Eurostat data where available |
| MEDIUM | GitHub Copilot 55% speed improvement | GitHub Blog | Retrieve original CACM study for methodology validation |
| LOW | Uranium spot prices 2020 monthly | Investing News Network | Access FRED series PURANUSDM (free monthly data) |

---

## Recommended Next Steps

1. **Retrieve arXiv:2604.22750 and its GitHub data repository** — this is the single most important action before finalizing the model. The 1–3.5M tokens/task figure anchors the entire agentic scenario.

2. **Access FRED series PURANUSDM** for precise monthly uranium spot price history 2019–2024.

3. **Retrieve McKinsey MGI "A New Future of Work" (May 2024) and the November 2025 update** directly — the 30% and 57% figures are the second most important empirical anchors.

4. **Obtain Goldman Sachs "Tracking Trillions" (2024) and Briggs/Kodnani March 2023** via institutional access for occupation-level automation exposure percentages for software/engineering roles.

5. **Check MLPerf Inference v4.1 power benchmarks** (mlcommons.org) for independent H100 power consumption per token under inference workloads.

6. **Construct a defensible global engineering compensation pool** from BLS OES (US), Eurostat (EU), and OECD regional data. The current ~$1.7T is too rough for a Table 1 anchor.

7. **Update EIA Short-Term Energy Outlook** (monthly) for latest ERCOT and PJM load growth revisions — these have moved upward multiple times in 2025–2026.

8. **Check SWE-bench leaderboard** (swebench.com) for current state-of-the-art scores — the Devin 2.0 13.86% figure may be outdated and is critical context for the capability-gap argument.

---

*For domain-level detail, see:*
- *[Domain 1 — Workforce & Compensation](./workforce_compensation.md)*
- *[Domain 2 — Token & Compute Benchmarks](./token_compute_benchmarks.md)*
- *[Domain 3 — Data Center Energy & Infrastructure](./datacenter_energy.md)*
- *[Domain 4 — Energy Markets & Capital Markets](./markets_capital.md)*
