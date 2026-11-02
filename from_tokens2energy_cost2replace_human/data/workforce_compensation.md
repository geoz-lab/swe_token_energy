# Domain 1: Engineering Workforce & Compensation
*Processed: 2026-05-06*

> See [SUMMARY.md](./SUMMARY.md) for the full scenario model, locked assumptions, and top 10 key numbers.

---

## Raw Data Table

| Metric | Value | Source | Quality |
|--------|-------|---------|---------|
| US SW developer median annual wage (May 2024) | $133,080/yr | BLS OES May 2024 | [PRIMARY] |
| US SW developer employment count (May 2024) | ~1,847,900 (SOC 15-1252) | BLS OES May 2024 | [PRIMARY] |
| US total architecture & engineering employment (May 2024) | 2,567,210 | BLS OES May 2024 | [PRIMARY] |
| US median wage, all architecture & engineering (May 2024) | $97,310/yr | BLS OES May 2024 | [PRIMARY] |
| Global SW developer headcount (2024) — Evans Data / Statista | ~28.7 million | Evans Data / Statista | [SECONDARY] |
| Global SW developer headcount (2024) — JetBrains revised | ~19.6 million professional developers | JetBrains Developer Ecosystem Survey 2025 | [SECONDARY] |
| Global developer count incl. citizen developers (early 2025) | ~47.2 million | ShiftMag / Springs Apps | [SECONDARY] |
| Average global SW engineer salary (self-reported, 2024) | $70,877/yr | Glassdoor / EZtek | [SECONDARY] |
| % of STEM/engineering work automatable by AI (McKinsey 2024) | 30% of work hours (by 2030, accelerated scenario) | McKinsey Global Institute, May 2024 | [SECONDARY] |
| % of US work hours automatable w/ GenAI (by 2030) | 29.5% (vs 21.5% without GenAI) | McKinsey Global Institute, 2024 | [SECONDARY] |
| Jobs potentially affected globally (Goldman Sachs, 2023) | ~300 million (US + Europe, affected or degraded) | Goldman Sachs Research, March 2023 | [SECONDARY] |
| % of computer programmer tasks exposed to automation (GS) | High-risk category (alongside legal at 44%, office/admin at 46%) | Goldman Sachs Research, 2023 | [SECONDARY] |
| GitHub Copilot: task completion speed improvement | 55% faster (JS HTTP server; n=4,800 developers) | GitHub Blog / CACM study | [SECONDARY] |
| GitHub Copilot: suggestion acceptance rate | ~30% average | GitHub Blog / Harness case study | [SECONDARY] |
| GitHub Copilot: estimated daily token consumption (chat-heavy) | ~100K input + 20K output tokens/day | GitHub Copilot billing docs (illustrative) | [ESTIMATE] |
| GitHub Copilot: total cumulative users (July 2025) | 20 million | Second Talent / GetPanto | [SECONDARY] |
| McKinsey Nov 2025 update: % of work hours automatable | 57% of work hours | McKinsey Global Institute, November 2025 | [SECONDARY] |

> ⚠️ **Note — Global developer headcount conflict:** Evans Data (28.7M) uses a broad "developer" definition including citizen developers; JetBrains (19.6M) counts professional developers only. The 47.2M ShiftMag figure is an upper bound with unclear methodology — do not use in the quantitative model. **Working estimate: 24 million** (midpoint of 19.6M–28.7M). See [Locked Assumptions](./SUMMARY.md#locked-assumptions).

> ⚠️ **Note — Global salary:** The $70,877/yr Glassdoor/EZtek figure is self-reported and skewed toward English-speaking respondents. Use with explicit caveat; replace with OECD/Eurostat data where available.

> ⚠️ **Note — Goldman Sachs 300M jobs:** "Affected or degraded" ≠ displaced. This headline is frequently misquoted. Cite the original GS research note and use precise language.

> ⚠️ **Note — GitHub Copilot 55% speed improvement:** Based on a controlled experiment on a narrow task type (JavaScript HTTP server). May not generalize to full engineering workflows.

> ⚠️ **Note — McKinsey 57% figure:** Currently cited via a Medium summary. Must retrieve the original MGI November 2025 report before using this figure in the paper.

> ⚠️ **Note — GitHub Copilot 100K tokens/day:** Illustrative billing example, not an empirically benchmarked figure. Actual usage varies widely across developers.

---

## Derived Calculations

### 1. Working Estimate: Global Software Developer Count

| Scenario | Count | Basis |
|----------|-------|-------|
| Narrow (professional developers only) | 19.6 million | JetBrains 2025 |
| **Mid-point working estimate** | **~24 million** | Average of 19.6M and 28.7M |
| Broad (all "developers") | 28.7 million | Evans Data / Statista |
| Upper bound (incl. citizen devs) | 47.2 million | ShiftMag (ceiling only — not for model use) |

**Working estimate for paper: 24 million software developers globally.**
Rationale: The 19.6M–28.7M range brackets professional developers. Using the midpoint (~24M) is appropriately conservative and defensible. The 47.2M figure must not be used in the quantitative model.

---

### 2. Global Software Engineering Compensation Pool

```plaintext
24,000,000 developers × $70,877 avg global salary = $1.701 trillion/year
```

| Component | Calculation | Result |
|-----------|-------------|--------|
| SW engineering pool (24M mid estimate) | 24M × $70,877 | **~$1.70 trillion/year** |
| SW engineering pool (28.7M broad) | 28.7M × $70,877 | ~$2.03 trillion/year |
| Full engineering pool (+50% for non-SW disciplines) | $1.70T × 1.50 | **~$2.55 trillion/year** |
| Full engineering pool (broad base, +50%) | $2.03T × 1.50 | ~$3.05 trillion/year |

**Working estimate: $1.7T (SW only) to $2.6T (all engineering disciplines).**

> ⚠️ **Note:** The +50% uplift for non-SW disciplines (civil, mechanical, electrical, chemical, aerospace) is a rough proxy. BLS reports 2.57M US architecture & engineering workers vs 1.85M SW developers — a ratio of ~1.39×. Using 1.4× instead of 1.5× yields ~$2.38T, consistent with the $2–$3T range.

---

### 3. FTEs Effectively Replaced Under Automation Scenarios

Base: **24 million software engineers** + 40% uplift = **~33.6 million total engineering FTEs** globally.

| Scenario | Automation % | Source | SW Engineers Replaced | Total Eng. FTEs Replaced |
|----------|-------------|--------|-----------------------|--------------------------|
| Conservative | 10% | Illustrative low | 2.4 million | 3.4 million |
| McKinsey 2024 base | **30%** | McKinsey MGI, May 2024 | **7.2 million** | **10.1 million** |
| McKinsey 2025 aggressive | 57% | McKinsey MGI, Nov 2025 | 13.7 million | 19.2 million |
| Near-full substitution | 80% | Illustrative high | 19.2 million | 26.9 million |

**Primary working scenario for paper: 30% substitution → 7.2M SW engineering FTE-equivalents replaced.**

```plaintext
30% scenario arithmetic check:
24,000,000 × 0.30 = 7,200,000 SW engineering FTE-equivalents replaced

Labor value displaced (30% scenario):
7,200,000 FTEs × $70,877/yr = ~$510 billion/year
```

---

### 4. Reconciling McKinsey Automation Estimates

| Report | Figure | Interpretation |
|--------|--------|----------------|
| McKinsey MGI, May 2024 | 30% of hours (2030 accelerated scenario) | Forward-looking deployment projection; GenAI adoption required |
| McKinsey MGI, Nov 2025 | 57% of hours "already automatable" | Current technical capability; actual adoption rate is lower |

These figures are **not contradictory**: 30% is a deployment/adoption projection; 57% is the technical ceiling if all existing tools were fully adopted today. **For the paper's model, 30% is the appropriate scenario anchor** (reflects likely real-world deployment), with 57% as the aggressive/upper-bound case.
