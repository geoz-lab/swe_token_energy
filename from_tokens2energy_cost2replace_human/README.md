# From Tokens to Energy: The Cost of Replacing Human Engineering with AI

> **Archived exploration.** This earlier economics draft uses substitution assumptions and token calibrations that do not drive the current AGU 2026 poster. For the current seven-stage method and limitations, start at the [project README](../README.md) and [numerical study](../AGU_Token/numerical/README.md).

**Paper draft:** `paper_arxiv_draft.tex` → compiled to `paper_arxiv_draft.pdf`  
**Bibliography:** `paper.bib`  
**Figures:** `figures/`  
**Scripts:** `scripts/`

---

## Project overview

This paper quantifies the energy and economic consequences of replacing software engineering labor with AI. The core analytical chain is:

```
Engineering labor (FTE-hours)
    → Token demand (per task × tasks/day × FTEs substituted)
        → Compute infrastructure (GPUs, racks, data centers)
            → Energy consumption (MW, TWh/year)
                → Economic cost ($/FTE-year, vs. human salary)
```

The central scenario (30% substitution, 7.2M FTEs, agentic mode) requires approximately **110 MW** of continuous inference power — 0.10% of IEA's projected 2030 global data center load — at an API cost of **$9,020/FTE-year** (6.8% of US median software developer salary of $133,080).

---

## Repository structure

```
paper_arxiv_draft.tex       Main LaTeX source
paper_arxiv_draft.pdf       Compiled output (tectonic)
paper.bib                   BibTeX bibliography
.env                        API keys (not committed — see .gitignore)
.gitignore                  Excludes .env, build artifacts

figures/
  fig_token_calibration.pdf      Figure 1: empirical token calibration (LaTeX)
  fig_token_calibration.png      Figure 1: preview
  empirical_token_calibration.csv  Raw per-run API measurements
  empirical_token_summary.csv      Summary statistics by model × task
  empirical_token_summary.json     Machine-readable summary
  scenario_token_demand.csv        Token demand by substitution scenario
  gpu_infrastructure_requirements.csv
  fte_cost_breakdown_central.csv
  geographic_cost_comparison.csv
  carbon_emissions.csv
  sensitivity_analysis.csv
  scenario_matrix_full.csv
  power_global_context.csv
  api_cost_per_fte_by_pricing_tier.csv
  model_tier_comparison.csv
  hardware_inference_comparison.csv
  power_source_profile.csv
  engineering_task_taxonomy_extended.csv

scripts/
  token_calibration.py     Empirical API token measurement (multi-provider)
  generate_figures.py      Publication figure generation (matplotlib)
```

---

## Compiling the paper

```bash
tectonic paper_arxiv_draft.tex
```

Requires [tectonic](https://tectonic-typesetting.github.io/) (installed via Homebrew). No separate BibTeX pass needed — tectonic handles the full LaTeX+BibTeX pipeline automatically.

---

## Running the token calibration

### Setup

Fill in `.env` with your API keys:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

Only providers with a real key are tested. Placeholder values are skipped automatically.

### Install dependencies

```bash
pip install anthropic openai google-genai matplotlib numpy
```

### Run

```bash
python scripts/token_calibration.py
```

This makes **54 API calls** (6 models × 3 tasks × 3 runs) and writes:
- `figures/empirical_token_calibration.csv` — raw results
- `figures/empirical_token_summary.csv` — mean/min/max per (task, model)
- `figures/empirical_token_summary.json` — machine-readable summary

### Regenerate figure

```bash
python scripts/generate_figures.py
```

Reads the CSV and writes `figures/fig_token_calibration.pdf` and `.png`. The figure is automatically included in the paper at the next compile.

---

## Empirical calibration results (single-turn)

Measured May 2026 across 3 representative engineering task tiers:

| Task tier | Claude Opus 4.7 | Claude Sonnet 4.6 | GPT-4o | GPT-4.1 | Gemini 2.5 Flash | Gemini 2.5 Pro |
|-----------|---------------|-----------------|--------|---------|-----------------|---------------|
| Simple bug fix | 0.9K | 0.8K | 0.6K | 0.6K | — | — |
| Feature implementation | 5.6K | 8.5K | 2.4K | 2.7K | — | — |
| Architectural refactor | 10.5K | 9.9K | 3.8K | 4.4K | — | — |

*(Gemini results pending — see note below)*

**Key finding:** These single-turn baselines are **100–300× smaller** than the agentic range of 1–3.5M tokens/task reported by Bai et al. (2026). The gap arises from tool calls, multi-turn context accumulation, and iterative refinement in agentic workflows. This multiplier is the principal driver of AI infrastructure energy demand.

**Anthropic vs. OpenAI:** GPT-4o and GPT-4.1 used 2–3× fewer tokens per task than Claude models at similar capability tiers. This likely reflects different output verbosity defaults, not task quality differences.

**Output cap saturation:** Feature implementation and architectural refactor tasks frequently hit the 8,192-token output cap, confirming that single-turn prompts cannot fully resolve complex tasks — multi-turn agentic operation is necessary in practice.

### Gemini model note

The original model IDs (`gemini-2.0-flash`, `gemini-1.5-pro`) were deprecated. Updated in `scripts/token_calibration.py` to:
- `gemini-2.5-flash-preview-05-20`
- `gemini-2.5-pro-preview-05-06`

Rerun `python scripts/token_calibration.py` to collect Gemini results. The figure will update automatically.

---

## Peer review summary

A multi-agent peer review was conducted on the draft (May 2026). Key findings:

### Top 3 strengths

1. **Excellent uncertainty transparency.** The paper explicitly tags all data quality (`[PRIMARY]`, `[SECONDARY]`, `[ESTIMATE]`, `[VERIFY]`) and quantifies a 14× uncertainty band on aggregate token demand. Rare in this literature.

2. **The 0.10% finding is striking and well-quantified.** The central scenario's 110 MW load represents 0.10% of IEA's projected 2030 global data center baseline — directly refuting the assumption that engineering AI substitution would impose major new infrastructure demand.

3. **The cost-structure analysis is sharp.** Infrastructure capex + energy = $19.52/FTE-year vs. $9,000 in API token cost. This makes the conclusion clear: at current API pricing, the token price is the only cost that matters, and it is still only 6.8% of US engineer salary.

### Top 5 weaknesses (pre-submission priorities)

1. **Tasks-per-day assumption (2 tasks/day) is unsupported.** A substituted FTE completing 2 SWE-bench-class tasks per day (every ~4 hours) is likely optimistic by an order of magnitude. If the correct figure is 0.2–0.5 tasks/day, all token demand and GPU estimates drop proportionally.

2. **API cost and owned-infrastructure cost are additive in Table 10 but are mutually exclusive.** An enterprise either pays API prices (no capex) or owns hardware (no API cost). The fully-loaded number conflates two different deployment models and should be split into two scenarios.

3. **Taxonomy substitutability percentages (Table 2) are entirely asserted.** The 90%/95%/85%/40%/45%/5% figures driving the 71% FTE ceiling have no empirical citation — they are expert judgment presented as data. Meyer et al. (2019) provides time-shares but not substitutability rates.

4. **Appendix B (sensitivity analysis) is marked as a placeholder.** The tornado charts and sensitivity tables are not yet written. This is a submission-blocking gap for any journal.

5. **No quantitative treatment of the Jevons/rebound effect.** If lower software cost expands software output proportionally (historically well-supported), the paper's central premise (labor reduction) may not hold. This is acknowledged as a limitation but not modeled.

### Citation issues to resolve before submission

- `mckinsey2023genai` (57% automatable figure): marked `[VERIFY]` — cited via secondary summary, original report not retrieved.
- `goldmansachs2024capex` ($1.15T capex figure): marked `[VERIFY]` — cited via third-party aggregators.
- `Recommendation 3` in Conclusion contains an internal editorial note about legal challenge status — remove before submission.
- Abstract has two typos: "serval priorities" → "several priorities"; "use approximately" → "uses approximately".
- Acknowledgments and funding sections contain `[TBD]` placeholders.

---

## Citation quality tagging system

The paper uses inline quality flags on all empirical claims:

| Tag | Meaning |
|-----|---------|
| `[PRIMARY]` | Directly citable government/official source |
| `[SECONDARY]` | Citable with caveat (preprint, analyst estimate, secondary summary) |
| `[ESTIMATE]` | Derived or illustrative; not independently verifiable |
| `[VERIFY]` | Requires primary source before submission — **do not submit with these** |

---

## Key scenario parameters (central case)

| Parameter | Value | Source |
|-----------|-------|--------|
| Global software developers | 24M | Evans Data / BLS |
| Substitution rate | 30% | Central scenario |
| FTEs substituted | 7.2M | Derived |
| Token mode | Agentic | Bai et al. 2026 |
| Tokens/task | 2.25M (mid) | Bai et al. 2026 |
| Tasks/FTE/day | 2 | Assumed |
| Daily token demand | 28.8T | Derived |
| H100 SXM5 throughput | 3,311 tok/s | Hyperstack benchmark |
| GPUs required | 2.52M | Derived |
| Data center power | 110 MW | Derived (PUE 1.56) |
| API cost/FTE-year | $9,020 | $4.35/MTok blended |
| Capex + energy/FTE-year | $19.52 | Self-hosted estimate |
| As % of US engineer salary | 6.8% | $133,080 BLS OES 2024 |
