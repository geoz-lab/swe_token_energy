# Experiment Plan — Token Demand & Inference Throughput

Supports §Experimental Evaluation of *From Tokens to Energy*. Two experiments:

1. **Token Consumption** (agentic) — local API orchestration, Linux/Sherlock grading.
2. **Inference Throughput** — Sherlock SLURM, H100 + A100, vLLM.

Locked decisions (2026-06-22): existing scaffolds (not custom agent); Docker grading on Sherlock/Linux;
API budget **$300–500**; both H100 + A100 available on Sherlock.
Refinements (2026-06-23): Exp-1 uses **3 benchmarks** (SWE-bench Lite + Verified + SWE-Lancer; **Aider Polyglot
dropped**); **most-advanced coding model per provider** — **Claude Opus 4.8**, **GPT-5.3-Codex**,
**Gemini 3.1 Pro**; keys stored in `Experiment/.env`. **Funding raised to ~$750** ($350 Anthropic /
$200 OpenAI / $200 Google) to run the **full 90-task matrix** on frontier models at the mid scenario.

---

## Environment facts (verified)

- Local machine: macOS **arm64** (Apple Silicon), **Docker not installed**. → arm64 cannot natively run the
  amd64 Docker images SWE-bench/SWE-Lancer ship; grading must move off the Mac.
- **Sherlock has no Docker** (rootless HPC; uses **Apptainer/Singularity**). This affects Exp-1 grading.
- Python 3.13 locally; `anthropic`, `openai`, `google-generativeai` installed. `.env` has key slots.
- 70B model ≈ 140 GB in BF16 → cannot fit one 80 GB GPU; needs tensor-parallel ≥2 GPUs (θ_GPU normalizes by G).
- User OK to create a fresh conda env.

---

## Experiment 1 — Agentic Token Consumption

### 1.1 Goal
Measure, per real benchmark task, the agentic token budget decomposed as
`T_task = T_input + T_output + T_tool + T_retry`, plus success rate, wall time, iteration count, API cost.
Output feeds the FTE-equivalent token demand `T_FTE`.

### 1.2 Scaffolds (existing, per benchmark)
All route models through **litellm** so Claude / GPT / Gemini share one token-accounting path.

| Benchmark | Scaffold | Why | Grading |
|---|---|---|---|
| SWE-bench Lite | **mini-swe-agent** (SWE-bench authors) | ~100-line, token-transparent, batch mode, litellm | SWE-bench eval harness |
| SWE-bench Verified | mini-swe-agent (SWE-agent as fallback) | same; Verified has difficulty labels for stratification | SWE-bench eval harness |
| SWE-Lancer | **OpenAI SWE-Lancer harness** | only faithful option; Docker-based, heavy | SWE-Lancer graders |

> **Aider Polyglot dropped** (2026-06-23, user decision). Three benchmarks: SWE-bench Lite, SWE-bench Verified, SWE-Lancer.

### 1.3 Token decomposition — as implemented (`parse_trajectory.py`)
**Finding (2026-06-23 pilot):** mini-swe-agent v2.4.2 persists only `info.model_stats.{instance_cost, api_calls}`
in each `.traj.json` — **no token counts**, and messages are `{role, content}` only. So we **reconstruct** the
agentic token demand from the saved conversation and **cost-anchor** it to the exact billed cost:

- Replay turn-by-turn: each `assistant` message is one API call whose **input = all prior messages** (system +
  task + the growing assistant/tool history re-sent every turn = the real agentic demand), **output = that
  message**. Tokenize with tiktoken (`o200k_base`; run the parser on the login node so it can fetch the vocab).
- **Additive partition** `T_task = T_input + T_output + T_tool`:
  - `T_output` = all generated (assistant) tokens, cumulative.
  - `T_tool`   = the tool/observation share of cumulative input (bash output, file reads, test logs).
  - `T_input`  = the rest of cumulative input (system + task + assistant history).
- **Cost-anchor:** scale the three so reconstructed cost == recorded `instance_cost` (cost is ground-truth;
  tiktoken gives the split). `anchor_factor` (printed) shows raw-reconstruction vs real; near 1 = good.
- **Retry is a DIAGNOSTIC, not a 4th additive term** (it overlaps input/output). A SWE-bench task's *first*
  failing test is normal bug-reproduction, not a retry — so we report `n_failed_tests` and `retry_frac` (token
  share in turns after the *2nd* failure) separately, instead of the original `T_retry` bucket.

> Note vs. the paper's `T_input+T_output+T_tool+T_retry`: retries can't be cleanly partitioned from input/output,
> so we use the 3-way additive identity above + retry as a separate intensity metric. Reconcile in the writeup.

### 1.4 Stratified sampling (within budget)
| Benchmark | n | Stratify by |
|---|---|---|
| SWE-bench Lite | 30 | repository |
| SWE-bench Verified | 40 | annotated difficulty (<15m / 15m–1h / 1–4h / >4h) |
| SWE-Lancer | 20 | task type (IC SWE vs Manager) × price band |

≈ **90 tasks**. Same sampled task IDs are reused across all models (paired comparison).

### 1.5 Models — most-advanced coding model per provider, full 90-task matrix each
Frontier coding flagships (June 2026). Output rates dominate agentic cost (caching doesn't help output).

Exact API ids verified accessible 2026-06-23 (smoke_test.py / live probe).

| Provider | Model (full matrix) | $/1M in · out · cached-in | $/task (mid) | ×90 |
|---|---|---|---|---|
| Anthropic | **`claude-opus-4-8`** | 5.00 · 25.00 · 0.50 | ~$3.62 | ~$326 |
| OpenAI | **`gpt-5.4`** (balanced GPT-5, chat API) | 2.50 · 15.00 · 0.25 | ~$2.06 | ~$185 |
| Google | **`gemini-3.1-pro-preview`** (>200K ctx → 4.00·18.00) | 2.00 · 12.00 · 0.20 | ~$1.65 | ~$148 |

- **Total ≈ $660 at mid scenario**; funded at **$350 / $200 / $200 = $750** (caps = `--max-budget-usd`).
  Add a ~$25–40 pilot (5 tasks × 3 models) first to calibrate real $/task before the full run.
- **OpenAI model access (2026-06-23):** this account has the **GPT-5 chat line** (`gpt-5.5`, `gpt-5.4`,
  `gpt-5.2`, `gpt-5`, `gpt-4o`) but **no codex / gpt-4.1 / o3 / gpt-5-pro** (403). So `gpt-5.3-codex` is
  *not* usable here — `gpt-5.4` is the balanced accessible coder (gpt-5.5 = max ability at $5/$30 if wanted).
- Anthropic **Fable 5** ($10/$50) is export-control suspended → Opus 4.8 is the Anthropic flagship.
- All routed via **litellm**. OpenAI/Google cached rates in `estimate_cost.py` are approximate — verify vs
  live rate cards.
- Build everything **cost-instrumented**; the dry-run estimator prints projected $ and the runner enforces the
  per-account `--max-budget-usd` kill-switch, `STEP_CAP=50`, and `PER_TASK_TOKEN_CEILING=3M`.

### 1.6 Where grading runs (resolve the Docker constraint)
Sub-decision — pick one (recommendation first):
- **(A) Separate Docker-capable Linux box / cloud VM** for SWE-bench + SWE-Lancer grading; orchestrate from Mac.
  Cleanest, matches the upstream harnesses exactly. *Recommended.*
- **(B) Apptainer/Singularity on Sherlock** — convert SWE-bench images; more setup, but no extra machine.
- **(C) SWE-bench hosted grading (`sb-cli` / Modal)** — offload eval to the cloud; least infra, small cost.
- Aider Polyglot needs no Docker either way (can run on Mac or Linux).

### 1.7 Deliverables
- `exp1_token_consumption/` — runner, sampler, token-tagger, cost estimator.
- `exp1_results/exp1_raw.csv` (per task: 4 token components, success, time, iterations, $) and
  `exp1_results/exp1_summary.csv` (per benchmark×model). Figure: token-demand distribution → `T_FTE`.

---

## Experiment 2 — Inference Throughput (Sherlock)

### 2.1 Goal
Measure `θ_GPU = T_generated / (t · G)` and supporting metrics across model size, context length,
and concurrency, to convert token demand into GPU-fleet / power / energy estimates.

### 2.2 Stack
- **vLLM** OpenAI-compatible server + **`vllm bench serve`** (built-in serving benchmark).
- Fresh **conda env** on Sherlock; `module load` CUDA matching the H100/A100 driver.
- No Apptainer needed (vLLM via pip).

### 2.3 Models — hardware-feasible set (June 2026), exact HF IDs
**Hardware reality (2026-06-23): only 1× H100 (80 GB) or a few A100 (80 GB) available.** This rules out the
entire current open *frontier* — GLM-5.2 (744B), DeepSeek-V4 (284B–1.6T), MiniMax M3 (428B), Llama-4-Scout
(109B) all need 4–16 GPUs/multi-node. So we use current-gen models that fit one H100 or a few A100, spanning
~8B→120B, and report throughput vs **both total and active params** (MoE decouples memory from compute).
Note `A100 = Ampere → no FP8/MXFP4 tensor cores → BF16 only` (large models need more A100s).

Scope (2026-06-23): **strong-coding, lightweight (single-GPU) models only.** All Apache-2.0/ungated →
**no HF token**. Every model fits **1× H100 and 1× A100**, so the H100-vs-A100 comparison runs on all of them
and no tensor parallelism is needed. Verify exact id suffixes on HF before running (Qwen3.5 is multimodal —
serve text-only).

| HF id | Type · total / active | Why |
|---|---|---|
| `Qwen/Qwen3.5-9B` | dense · 9B / 9B | small strong coder (lower bound of the size axis) |
| `Qwen/Qwen3.5-27B` | dense · 27B / 27B | flagship-level coding in a single-GPU dense model |
| `Qwen/Qwen3.5-35B-A3B` | MoE · 35B / 3B | strong + fast (only 3B active); MoE arm of the control |
| `openai/gpt-oss-20b` | MoE · 21B / 3.6B | cross-family lightweight coder/reasoner (Apache) |

- **MoE-vs-dense control:** Qwen3.5-27B (dense, 27B active) vs Qwen3.5-35B-A3B (MoE, 3B active) at ~equal
  footprint; active-param sweep 3B / 3.6B (MoE) vs 9B / 27B (dense).
- Heavy frontier models (gpt-oss-120b, Qwen3.5-122B, DeepSeek-V4, GLM-5.2, Llama-70B) **dropped** — not
  lightweight / need >1 GPU.
- Swap-in option if you want the very newest coder: `Qwen3.6-27B` (dense, flagship coding).

### 2.4 GPU mapping — θ_GPU = T/(t·G) normalizes by G
Weights ≈ total_params × bytes/param (BF16 2 B, FP8/MXFP4 ≈ 0.5–1 B) + KV cache + activations. 80 GB/GPU.

| Model | total / active | 1× H100 (precision) | 1× A100 80 GB (BF16) |
|---|---|---|---|
| Qwen3.5-9B | 9B / 9B | ✓ BF16 (18 GB) | ✓ |
| Qwen3.5-27B | 27B / 27B | ✓ BF16 (54 GB) | ✓ |
| Qwen3.5-35B-A3B | 35B / 3B | ✓ BF16 (70 GB, tight; FP8 35 GB) | ✓ |
| gpt-oss-20b | 21B / 3.6B | ✓ MXFP4 (~12 GB) / BF16 42 GB | ✓ |

**Every model is single-GPU**, so no tensor parallelism (G=1) and the **H100-vs-A100 comparison is direct**
on all four. KV cache has ample room at 4k–32k context. (A100 = BF16; H100 = BF16, or FP8 for the 35B MoE.)

### 2.5 Config matrix (9 / model / GPU type)
- Context length (input_len): **4k / 16k / 32k**; output_len fixed (propose **1024**).
- Concurrency (`--max-concurrency`): **1 / 4 / 16**.
- Per config record: sustained throughput (tok/s total & per-GPU θ_GPU), TTFT, TPOT/ITL, p50/p99 latency,
  GPU util, memory util, **power draw**.
- Power/util sampled by a background `nvidia-smi --query-gpu=...,power.draw,utilization.gpu,memory.used
  --format=csv -lms 200` (or `dcgmi dmon`) logger spanning each run.

### 2.5a Making θ_GPU **representative** (not just a synthetic peak)
The headline risk is measuring generic throughput instead of throughput *for the workload that replaces
engineers*. Seven rules:
1. **Workload from Exp-1, not arbitrary lengths.** Drive the load with the empirical input/output token
   distribution measured in Exp-1 (input-heavy, prefix-reuse-heavy agentic SE) — `vllm bench serve
   --dataset-name custom --dataset-path agent_prompts.jsonl`, or sample lengths from the measured
   distribution. Keep 4k/16k/32k as a *controlled axis*, but the representative number uses the real mix.
2. **Online serving with a request-rate sweep**, not the offline max-batch tool. Use `vllm bench serve` with
   Poisson arrivals (`--request-rate`) to trace the latency–throughput curve; `bench throughput` (offline)
   only gives the saturated ceiling.
3. **Report two operating points:** (a) **saturated** max sustained tok/s (batch/offline fleets) and
   (b) **throughput at an interactive SLO** (e.g. TPOT ≤ ~50 ms, TTFT ≤ ~1 s). Agentic serving is
   latency-bounded → the SLO-constrained number is the representative θ_GPU; peak is the upper bound.
4. **Steady state + warmup:** discard the first ~30 s / N requests, measure over ≥ a few minutes or
   ≥200–500 completed requests; repeat each config **≥3×**, report mean ± CI.
5. **Prefix caching ON** (vLLM automatic) — agentic loops re-send a growing shared prefix, so cache hits
   dominate real throughput; report ON (realistic) and optionally OFF (baseline). Mirrors Exp-1's input cache.
6. **Power at the *same* window as throughput** → tokens/joule = θ_GPU·G / mean_power. Never measure
   throughput and power in separate runs. (Apply a PUE multiplier later for facility energy.)
7. **Headline decode (output) throughput** for θ_GPU = T_generated/(t·G), but also report **total
   (prefill+decode)** throughput — input-heavy agentic load is prefill-heavy and prefill burns real energy.

### 2.6 SLURM
- One `sbatch` per (model × gpu-type × tp): request `--gres=gpu:h100:N` / `:a100:N`, correct partition.
- Job: launch vLLM server (background) → poll `/health` → run the 9-config sweep → teardown. Power logger runs
  alongside the client.
- **Open item:** confirm Sherlock partitions/QOS for H100 vs A100 and the A100 memory variant (40 vs 80 GB).

### 2.7 Deliverables
- `exp2_throughput/` — sbatch templates, server-launch + sweep driver, power logger, parser.
- `exp1_results/exp2_raw.csv` (per config) + `exp1_results/exp2_summary.csv` (θ_GPU table). Figures: θ_GPU vs
  size / context / concurrency; power & efficiency (tok/s/W).

---

## Proposed directory layout
```
Experiment/
  PLAN.md                      (this file)
  environment.yml              (conda env for both experiments)
  exp1_token_consumption/
    sample_tasks.py            stratified sampler per benchmark
    run_agent.py               scaffold driver (litellm) + token tagger
    estimate_cost.py           dry-run budget projector
    scaffolds/                 mini-swe-agent / aider / swe-lancer configs
  exp2_throughput/
    slurm/                     sbatch templates (h100, a100-tp2, a100-tp4)
    launch_vllm.sh             server up + health wait
    bench_sweep.py             9-config driver
    power_logger.py            nvidia-smi/dcgm sampler
    parse_results.py
  exp1_results/                     all CSVs + figures
```

## Open items to confirm before building
1. **Exp-1 grading host** — A (separate Docker box, recommended) / B (Apptainer on Sherlock) / C (hosted sb-cli).
2. **Token-decomposition semantics** — confirm the §1.3 partition matches the paper's 4 terms.
3. **Sherlock specifics** — H100/A100 partition names, QOS, and A100 memory (must be **80 GB**; 40 GB breaks
   the GPU map). Confirm you can get **1× H100** and **2–4× A100** in a single job.
4. **Exp-2 large models** — keep gpt-oss-120b (and optional Llama-3.3-70B), or trim to the three ≤32B models
   if even single-H100 time is scarce? gpt-oss-120b on H100 uses *emulated* MXFP4 (slower than Blackwell).

**Resolved:** Exp-1 models = `claude-opus-4-8` / `gpt-5.4` / `gemini-3.1-pro-preview` (verified accessible
2026-06-23; account has no codex/gpt-4.1), $750 funded (§1.5).
Exp-2 re-scoped to **hardware-feasible** set — 1× H100 / few A100, frontier MoE dropped (§2.3): `Qwen/Qwen3-8B`,
`Qwen/Qwen3-Coder-30B-A3B-Instruct`, `Qwen/Qwen3-32B`, `openai/gpt-oss-120b` (all Apache, **no HF token**);
optional `meta-llama/Llama-3.3-70B-Instruct` (gated).
```
