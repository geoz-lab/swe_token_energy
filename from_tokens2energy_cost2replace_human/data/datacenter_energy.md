# Domain 3: Data Center Energy & Infrastructure
*Processed: 2026-05-06*

> See [SUMMARY.md](./SUMMARY.md) for the full scenario model, locked assumptions, and top 10 key numbers.

> ⚠️ **CRITICAL CORRECTION — Do not conflate engineering substitution demand with total AI data center demand:**
> Replacing 30% of global SW engineers (7.2M FTEs) adds approximately **110 MW (0.11 GW)** of incremental data center power demand. This is ~0.10% of the IEA's projected 2030 global data center load of 107.9 GW. The 107.9 GW figure is **total projected global data center power demand from all AI and non-AI workloads combined**, not a consequence of engineering substitution alone. The paper must not conflate these two figures.

> **ASSUMPTION — H100 power:** All scenario calculations in this file use **700 W per H100 GPU** (NVIDIA inference TDP). Peak system power is 1,275 W/GPU (derived from DGX spec: 10,200 W ÷ 8 GPUs). The 1,275 W ceiling applies only to full training load; 700 W is the appropriate figure for inference workloads. Using 1,275 W yields ~28 MW facility power per 1M FTEs vs. ~15 MW at 700 W — a 2× difference. See [Locked Assumptions](./SUMMARY.md#locked-assumptions).

> **ASSUMPTION — Construction cost:** All capex calculations use **$15 M/MW** as the mid-estimate for AI-optimized, liquid-cooled facilities (2024–2026). Sources span $10–12 M/MW (Cushman & Wakefield standard) to $20 M+/MW (DCD AI-optimized). The $6 M/MW figure from older DCD coverage reflects a prior cost era and should not be used. See [Locked Assumptions](./SUMMARY.md#locked-assumptions).

---

## Raw Data Table

### Global and US Electricity Consumption

| Metric | Value | Source | Quality |
|--------|-------|---------|---------|
| Global data center electricity consumption (2024) | ~415 TWh (~1.5% of global electricity) | IEA "Energy and AI" | [PRIMARY] |
| Global data center electricity consumption (2030 Base Case) | ~945 TWh (~3% of global electricity) | IEA "Energy and AI" | [PRIMARY] |
| Global data center electricity growth rate (~2019–2024) | ~12%/year | IEA "Energy and AI" | [PRIMARY] |
| AI server electricity consumption growth rate (IEA) | 30%/year (Base Case, through 2030) | IEA "Energy and AI" | [PRIMARY] |
| US data center electricity consumption (2024) | ~183 TWh (>4% of total US electricity) | IEA "Energy and AI" / Pew Research | [PRIMARY] |
| US data center electricity consumption (2023) | 176 TWh (~4.4% of total US electricity) | LBNL 2024 US Data Center Energy Usage Report | [PRIMARY] |
| US data center electricity (2014 baseline) | 58 TWh | LBNL 2024 Report | [PRIMARY] |
| US data center electricity forecast (2028) | 325–580 TWh (6.7–12% of total US electricity) | LBNL 2024 Report | [PRIMARY] |
| US data center energy source — natural gas (2024) | >40% | IEA | [PRIMARY] |
| US data center energy source — renewables (2024) | ~24% | IEA | [PRIMARY] |
| US data center energy source — nuclear (2024) | ~20% | IEA | [PRIMARY] |

### Efficiency Benchmarks

| Metric | Value | Source | Quality |
|--------|-------|---------|---------|
| Global average PUE (Uptime Institute 2024 survey) | 1.56 (5th consecutive year of flat trend) | Uptime Institute 2024 | [SECONDARY] |
| Global average PUE (Uptime Institute 2023 survey) | 1.58 per-site; 1.47 capacity-weighted | Uptime Institute 2023 | [SECONDARY] |
| PUE by region | Middle East/Africa/LatAm: >1.7; North America/Europe: ~1.5 | Uptime Institute 2024 | [SECONDARY] |
| Industry average WUE | 1.80–1.90 L/kWh (industry avg); hyperscalers: 0.19–0.21 L/kWh | Multiple sources | [SECONDARY] |
| AWS WUE (global avg, 2024) | 0.19 L/kWh (24% improvement YoY from 0.25) | AWS Sustainability reporting | [SECONDARY] |

### GPU and Rack Specifications

| Metric | Value | Source | Quality |
|--------|-------|---------|---------|
| H100 DGX server power (max) | 10.2 kW per DGX system (8× H100 GPUs) | NVIDIA DGX SuperPOD Design Guide | [PRIMARY] |
| H100 power per GPU (full load, derived) | 1,275 W/GPU (10,200 ÷ 8) | Derived from NVIDIA DGX specs | [PRIMARY] |
| H100 power per GPU (inference TDP — locked working value) | **700 W/GPU** | NVIDIA TDP spec / inference benchmarks | [PRIMARY] |
| H100 cluster rack density (air-cooled) | ~40–48 kW/rack (4 DGX systems recommended max) | NVIDIA DGX SuperPOD design guide / Sunbird DCIM | [PRIMARY] |
| H100 cluster rack density (liquid-cooled, CoreWeave) | Up to 130 kW/rack | SemiAnalysis newsletter | [SECONDARY] |
| GB200 NVL72 / AI-ready racks | 120+ kW/rack pre-configured | Digital Realty / Equinix specs | [SECONDARY] |

### Infrastructure Cost and Hyperscaler Capex

| Metric | Value | Source | Quality |
|--------|-------|---------|---------|
| Hyperscale data center construction cost/MW (standard 2024) | $10–$12M/MW (benchmark: $10.7M/MW in 2025) | Cushman & Wakefield 2024 | [SECONDARY] |
| AI-optimized data center construction cost (liquid cooling) | $20M+/MW | Data Center Dynamics / TrueLook | [SECONDARY] |
| **Working construction cost (locked)** | **$15M/MW** | Mid-estimate (this analysis) | [ESTIMATE] |
| Hyperscale data center build time | 12–24 months (edge sites: 6–9 months) | mastt.com / aveva.com | [SECONDARY] |
| Microsoft 2023 capex | $31.9 billion | Company filings via DCPulse | [PRIMARY] |
| Microsoft 2024 capex | $55.7 billion | Company filings via DCPulse | [PRIMARY] |
| Google/Alphabet 2023 capex | $32.3 billion | Company filings via DCPulse | [PRIMARY] |
| Google/Alphabet 2024 capex | $52.5 billion | Company filings via DCPulse | [PRIMARY] |
| Amazon 2023 capex | $48.4 billion | Company filings via DCPulse | [PRIMARY] |
| Amazon 2024 capex | $77.0 billion | Company filings via DCPulse | [PRIMARY] |
| Meta 2023 capex | $28.1 billion | Company filings via DCPulse | [PRIMARY] |
| Meta 2024 capex | $39.2 billion | Company filings via DCPulse | [PRIMARY] |
| Combined 4-hyperscaler capex 2025 guidance | ~$448 billion | Multiple earnings reports | [PRIMARY] |
| NVIDIA total revenue FY2024 (ending Jan 2024) | $60.9 billion (+126% YoY) | NVIDIA Q4 FY2024 earnings | [PRIMARY] |
| NVIDIA data center segment revenue FY2024 | $47.5 billion (~78% of total) | NVIDIA FY2024 earnings | [PRIMARY] |
| NVIDIA total revenue FY2025 (ending Jan 2025) | $130.5 billion (+114% YoY) | NVIDIA Q4 FY2025 earnings | [PRIMARY] |
| NVIDIA data center segment revenue FY2025 | $116.2 billion (~89% of total) | NVIDIA FY2025 earnings | [PRIMARY] |

> ⚠️ **Note — Combined 2024 hyperscaler capex:** Some sources cite ~$200B for combined 2024 capex. The arithmetic from company filings gives $55.7B + $52.5B + $77.0B + $39.2B = **$224.4B**. The $200B figure likely reflects earlier guidance estimates. Use $224.4B (sum of PRIMARY filings) in the paper.

---

## Derived Calculations

### 1. TWh to Average GW Conversion

```plaintext
Global data center average power (2024):
415 TWh ÷ 8,760 hr/yr = 47.4 GW average load

Global data center average power (2030 Base Case):
945 TWh ÷ 8,760 hr/yr = 107.9 GW average load

US data center average power (2024):
183 TWh ÷ 8,760 hr/yr = 20.9 GW average load

US data center average power (2028, LBNL midpoint 452 TWh):
452 TWh ÷ 8,760 hr/yr = 51.6 GW average load
```

| Year | Global Avg Power | US Avg Power |
|------|-----------------|--------------|
| 2024 | **47.4 GW** | 20.9 GW |
| 2028 (LBNL midpoint) | — | 51.6 GW |
| 2030 (IEA Base Case) | **107.9 GW** | — |

---

### 2. Power to Serve 1 Million Engineering FTEs in Agentic Mode

From Domain 2: **~14,000 H100 GPUs** needed for 1M agentic FTEs.

```plaintext
Using locked inference TDP: 700 W/GPU

GPU power:        14,000 × 700 W = 9,800,000 W = 9.8 MW
Facility (PUE 1.56): 9.8 MW × 1.56 = 15.3 MW ≈ 15 MW
Facility (PUE 1.47): 9.8 MW × 1.47 = 14.4 MW ≈ 14 MW

Ceiling (1,275 W/GPU):
GPU power:        14,000 × 1,275 W = 17.85 MW
Facility (PUE 1.56): 17.85 × 1.56 = 27.8 MW
```

**Working figure: ~15 MW total facility power per 1 million agentic engineering FTEs** (at 700 W/GPU, PUE 1.56).

---

### 3. Power, Capex, and Energy Cost by Substitution Scenario

```plaintext
30% substitution scenario:
7.2M FTEs × 4M tokens/day = 28.8T tokens/day
28.8T ÷ 86,400 = 333M tok/s needed
333M ÷ 3,311 tok/s per H100 = ~101,000 H100s
GPU power: 101,000 × 700W = 70.7 MW
Facility (PUE 1.56): 70.7 × 1.56 = 110 MW = 0.11 GW
```

| Substitution | FTEs Replaced | H100s Needed | GPU Power | Facility Power |
|-------------|--------------|-------------|-----------|---------------|
| 10% | 2.4M | ~33,700 | 23.6 MW | **36.8 MW (0.037 GW)** |
| **30%** | **7.2M** | **~101,000** | **70.7 MW** | **110 MW (0.11 GW)** |
| 80% | 19.2M | ~269,000 | 188 MW | **293 MW (0.29 GW)** |
| 100% | 24.0M | ~337,000 | 236 MW | **368 MW (0.37 GW)** |

**Construction capex** (at $15M/MW):

| Substitution | Facility Power | Construction Capex |
|-------------|---------------|-------------------|
| 10% | 36.8 MW | **$552 million** |
| 30% | 110 MW | **$1.65 billion** |
| 80% | 293 MW | **$4.40 billion** |

**Annual energy cost** (at $60/MWh blended):

| Substitution | Facility Power | Annual Energy (TWh) | Annual Energy Cost |
|-------------|---------------|--------------------|--------------------|
| 10% | 36.8 MW | 0.32 TWh | **$19 million/year** |
| 30% | 110 MW | 0.96 TWh | **$58 million/year** |
| 80% | 293 MW | 2.57 TWh | **$154 million/year** |

---

### 4. Combined AI Cost per FTE-Year (Infrastructure + API)

```plaintext
Token API cost:                         $9,000/FTE-year (frontier pricing)
Amortized capex (20-year life, 30% case):
  $1.65B ÷ 20 yr ÷ 7,200,000 FTEs  =  $11.46/FTE-year
Annual energy cost share:
  $58M ÷ 7,200,000 FTEs             =  $8.06/FTE-year

Total (API + infra + energy):         ~$9,020/FTE-year
Human salary benchmark:                $133,080/year

AI total cost ≈ 6.8% of human salary — infrastructure adds negligible overhead.
```

The economic case is overwhelmingly positive at all scenarios. Energy cost is a rounding error relative to labor displacement value; the binding constraint is AI capability, not cost.
