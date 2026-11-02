# Domain 2: Token & Compute Benchmarks
*Processed: 2026-05-06*

> See [SUMMARY.md](./SUMMARY.md) for the full scenario model, locked assumptions, and top 10 key numbers.

---

## Raw Data Table

| Metric | Value | Source | Quality |
|--------|-------|---------|---------|
| Avg tokens per SWE-bench agentic coding task | 1–3.5 million tokens/task (incl. retries, self-correction) | arXiv:2604.22750 | [SECONDARY] |
| Token variability across SWE-bench runs (same task) | Up to 30× variation between runs on identical tasks | arXiv:2604.22750 | [PRIMARY] |
| Input vs. output token ratio in agentic coding | Input tokens dominate; input drives cost even with caching | arXiv:2604.22750 | [PRIMARY] |
| Agentic token consumption vs. single-turn code chat | ~1,000× more tokens | arXiv:2604.22750 / Stanford Digital Economy Lab | [PRIMARY] |
| Agentic vs. single-turn multiplier (enterprise practical) | 50–500× multiplier; 50K–500K tokens per agentic task | NavyaAI AI Cost Report / Stevens Online | [SECONDARY] |
| Reflexion loop (10 cycles) vs. single linear pass | Up to 50× the tokens of a single pass | DEV Community / AI Agent Context Window article | [SECONDARY] |
| Unconstrained AI agent cost per SW engineering task | $5–$8 per task | NavyaAI AI Cost Report | [SECONDARY] |
| SWE-bench full evaluation run cost (some agents) | $300+ per full evaluation run | arXiv:2604.22750 / OpenReview | [PRIMARY] |
| Devin AI cost model | 1 ACU ≈ 15 min; Core plan $2.25/ACU → ~$9/hr; ~$2.40/bug fix | Devin.ai pricing page / Pensero blog | [PRIMARY] |
| Devin SWE-bench score (Devin 2.0) | 13.86% resolution rate | Cognition / OpenAIToolsHub | [SECONDARY] |
| FLOPs per token — 70B model (2N rule, FP16) | ~140 billion FLOPs/token | Epoch AI / HuggingFace scaling law derivation | [SECONDARY] |
| FLOPs per token — 7B model (2N rule) | ~14 billion FLOPs/token | Scaling law approximation (2N rule) | [ESTIMATE] |
| FLOPs per token — GPT-4 class (~400B+ dense equiv.) | ~275B dense arithmetic equivalent; ~1.8T dense memory equiv. | Epoch AI MoE vs. dense analysis | [SECONDARY] |
| H100 SXM5 inference throughput — 70B model, batch 64, FP16 | ~3,311 tokens/sec aggregate (vs A100: 1,148 tok/s) — Llama 3.1 70B | Hyperstack.cloud benchmark | [SECONDARY] |
| H100 SXM5 — 7B model, batch 64, FP8 (TensorRT-LLM) | >10,000 tokens/sec aggregate | NVIDIA TensorRT-LLM blog | [PRIMARY] |
| H100 SXM5 — single-user batch-1, 7B model, FP8 | ~350–500 tokens/sec | NVIDIA TensorRT-LLM / Jarvislabs FAQ | [SECONDARY] |
| B200 GPU inference throughput (GPT-class model) | 60,000 tokens/sec per GPU; 1,000 tokens/sec per user | NVIDIA Blackwell InferenceMAX benchmarks | [PRIMARY] |
| GB200 NVL72 — DeepSeek R1, SGLang | 26K input + 13K output tokens/sec/GPU | NVIDIA Developer Blog | [PRIMARY] |
| Blackwell vs. Hopper throughput/MW (agentic low-latency) | Up to 50× higher throughput/MW; 35× lower cost per token | NVIDIA Blackwell Ultra (GB300 NVL72) announcement | [PRIMARY] |
| Claude Sonnet 4.6 API pricing | $3.00/M input tokens; $15.00/M output tokens | Anthropic Claude API Docs | [PRIMARY] |
| Claude Opus 4.7 API pricing | $5.00/M input tokens; $25.00/M output tokens | Anthropic API Docs | [PRIMARY] |
| Claude Haiku 4.5 API pricing | $1.00/M input tokens; $5.00/M output tokens | Anthropic API Docs | [PRIMARY] |
| Anthropic Batch API discount | 50% off both input and output | Anthropic API Docs | [PRIMARY] |
| OpenAI GPT-4o API pricing (2025) | ~$5.00/M input; ~$20.00/M output | OpenAI API pricing page | [PRIMARY] |
| OpenAI GPT-4.1 API pricing (2025) | ~$3.00/M input; ~$12.00/M output | OpenAI API pricing page / LLM Stats | [PRIMARY] |
| OpenAI GPT-4 (original) pricing | $30.00/M input; $60.00/M output | OpenAI API pricing page | [PRIMARY] |
| Claude Opus 4.7: new tokenizer effect | ~35% more tokens for same input text — effective cost increase despite unchanged rate card | Finout blog | [SECONDARY] |
| GitHub Copilot chat-heavy developer daily token est. | ~100K input + 20K output tokens/day | GitHub Copilot billing docs (illustrative) | [ESTIMATE] |

> ⚠️ **Note — Agentic multiplier (1,000× vs. 50–500×):** These figures use different baselines — see reconciliation below. **Working value: 50–500× practical multiplier.** See [Locked Assumptions](./SUMMARY.md#locked-assumptions).

> ⚠️ **Note — Devin SWE-bench 13.86%:** This means ~86% of benchmark tasks still require human intervention. Critical context for the capability-gap argument; verify this figure is current at swebench.com before publication.

> ⚠️ **Note — GPT-4 class FLOPs:** MoE architecture makes direct FLOPs comparisons unreliable. The 275B dense equivalent is Epoch AI's analytical construct, not a measured figure.

> ⚠️ **Note — Blackwell throughput/MW claim:** NVIDIA self-reported benchmark; awaits independent verification. Use with attribution to NVIDIA.

> ⚠️ **Note — Tokenizer change (Claude Opus 4.7):** Cost models using token count must account for tokenizer version. Lock pricing to a specific date in the paper.

> ⚠️ **Note — GitHub Copilot 100K tokens/day:** Illustrative billing example, not an empirical benchmark. Actual usage varies widely.

---

## Derived Calculations

### 1. Tokens per Engineering-FTE per Day — Two Scenarios

#### Scenario A: Copilot-Augmented Mode

```plaintext
10 chat queries × 10,000 tokens context each = 100,000 input tokens
10 responses × 2,000 tokens each             =  20,000 output tokens
Total: 120,000 tokens/day per FTE
```

Human-in-the-loop; AI assists but does not execute autonomously.

#### Scenario B: Fully Agentic Mode

```plaintext
From SWE-bench: 1–3.5M tokens/task (midpoint: 2.25M)
2 tasks/day × 2,250,000 tokens/task = 4,500,000 tokens/day per FTE
Working figure: ~4 million tokens/day per FTE (agentic)
Range: 2M (low) to 7M (high) tokens/day
```

| Mode | Input Tokens/Day | Output Tokens/Day | Total Tokens/Day |
|------|-----------------|-------------------|-----------------|
| Copilot-augmented | 100,000 | 20,000 | **120,000** |
| Agentic (low) | ~1.7M | ~300K | ~2,000,000 |
| Agentic (mid) | ~3.4M | ~600K | **~4,000,000** |
| Agentic (high) | ~6.0M | ~1.0M | ~7,000,000 |

---

### 2. Resolving the Agentic Multiplier Conflict

| Source | Multiplier | Baseline Used |
|--------|-----------|---------------|
| arXiv:2604.22750 / Stanford | ~1,000× | Single-turn code chat (one prompt → one response, ~3K tokens) |
| NavyaAI / enterprise estimate | 50–500× | Multi-turn interactive coding session (~10K–60K tokens/session) |

> **RESOLUTION:** These figures are not contradictory — they measure against different baselines. 1,000× vs. a single chat prompt (~3K tokens) gives 3M tokens/task, which is consistent with SWE-bench data. 50–500× vs. a multi-turn session is also internally consistent.
>
> **Working estimate: 50–500× practical multiplier** (enterprise deployment). Reserve 1,000× for contrasting with simple single-turn interactions in the paper introduction. The midpoint of 50–500× implies ~225×, a reasonable anchor for scenario sensitivity analysis.

---

### 3. Blended API Cost per Token

Assume 85% input / 15% output token ratio (arXiv:2604.22750 confirms input dominates in agentic coding).

| Model | Input $/MTok | Output $/MTok | Blended $/MTok (85:15) |
|-------|-------------|--------------|------------------------|
| Claude Sonnet 4.6 | $3.00 | $15.00 | $4.80 |
| Claude Opus 4.7 | $5.00 | $25.00 | $8.00 |
| GPT-4.1 | $3.00 | $12.00 | $4.35 |
| GPT-4o | $5.00 | $20.00 | $7.25 |

**Working blended price: ~$9/MTok** (conservative, Opus-class for complex engineering). For cost-optimized deployments (Sonnet/GPT-4.1): ~$5/MTok.

---

### 4. Cost per Engineering-FTE-Year at API Prices

#### Copilot Mode (120K tokens/day)

```plaintext
120,000 tokens/day × 250 workdays = 30,000,000 tokens/year = 30 MTok/year
30 MTok × $5/MTok  = $150/FTE-year (optimized)
30 MTok × $9/MTok  = $270/FTE-year (frontier)
```

| Price Tier | Annual Token Cost per FTE |
|-----------|--------------------------|
| $5/MTok (Sonnet/optimized) | **$150/year** |
| $9/MTok (Opus/frontier) | **$270/year** |

#### Agentic Mode (4M tokens/day)

```plaintext
4,000,000 tokens/day × 250 workdays = 1,000 MTok/year
1,000 MTok × $5/MTok  = $5,000/FTE-year (optimized)
1,000 MTok × $9/MTok  = $9,000/FTE-year (frontier)
1,000 MTok × $9/MTok × 50% batch discount = $4,500/FTE-year
```

| Price Tier | Annual Token Cost per FTE (Agentic) |
|-----------|-------------------------------------|
| $5/MTok (optimized) | **$5,000/year** |
| $9/MTok (frontier) | **$9,000/year** |
| Frontier + 50% batch discount | **$4,500/year** |

---

### 5. Break-Even vs. Human Engineer

| Metric | Value |
|--------|-------|
| US SW developer median salary | $133,080/year ([PRIMARY] BLS) |
| Total US employment cost (~1.3× for benefits) | ~$173,000/year |
| AI agentic cost/FTE-year (frontier pricing) | $9,000/year |
| AI agentic cost/FTE-year (optimized pricing) | $5,000/year |
| **AI cost as % of human salary (frontier)** | **~6.8%** |
| **AI cost as % of human salary (optimized)** | **~3.8%** |
| **Labor cost savings per FTE replaced (frontier)** | **~$124,000/year** |

**Interpretation for paper:** Even at frontier API pricing, the pure token cost of an agentic AI replacing one engineering FTE is roughly 1/15th the salary cost. The binding constraint is not cost — it is capability (Devin 2.0 at 13.86% SWE-bench is far from production-ready for full substitution).

---

### 6. GPU Count Needed to Serve 1M Engineering FTEs in Agentic Mode

```plaintext
Token demand: 1,000,000 FTEs × 4,000,000 tokens/day = 4T tokens/day

Per-second: 4T ÷ 86,400 sec/day = 46.3M tokens/sec needed

H100 throughput (70B model, batch 64, FP16): 3,311 tok/s per GPU

GPUs needed: 46,296,296 ÷ 3,311 = ~13,983 ≈ 14,000 H100s
```

| Scale | FTEs Served | Tokens/Day | H100s Needed |
|-------|------------|-----------|-------------|
| Pilot | 1,000 | 4B | ~14 |
| Mid-size | 100,000 | 400B | ~1,400 |
| **1M FTEs** | **1,000,000** | **4T** | **~14,000** |
| 7.2M FTEs (30% of 24M SW devs) | 7,200,000 | 28.8T | ~101,000 |
| Full SW workforce (24M) | 24,000,000 | 96T | ~337,000 |

**Working figure for paper: ~14,000 H100s per 1 million agentic engineering FTEs.**

With Blackwell B200 (60,000 tok/s/GPU), the same 1M FTE workload requires only ~772 B200 GPUs — an 18× GPU-count reduction. Power efficiency improves ~50×/MW per NVIDIA (self-reported [PRIMARY]; awaits independent verification).

> For the full scenario matrix (power, capex, energy cost by substitution level), see [SUMMARY.md — Scenario Model](./SUMMARY.md#the-core-quantitative-chain).
