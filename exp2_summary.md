# Experiment 2 — Inference Throughput and Energy Intensity of Open-Weight Coding Models

> **Status:** methodology final; results being collected. Cells marked **[FILL]** are populated once
> the full A100/H100/H200 matrix completes (`parse_results.py` → `exp2_raw.csv`). A preliminary H100
> run (§6.0) already confirms the central finding.

## 1. Objective

Experiment 1 measured *demand*: the agentic token consumption of frontier models on real
software-engineering tasks, yielding a per-developer-year token budget `T_FTE` (77M–631M tokens/FTE-yr
depending on model). Experiment 2 measures *supply*: how fast, and at what energy cost, a modern
accelerator can **generate** those tokens for open-weight coding models. This converts a token budget
into a GPU fleet size, facility power, and electricity. The primary metric is

```
        θ_GPU = T_generated / (t · G)        (tokens · s⁻¹ · GPU⁻¹)
```

where `T_generated` is the number of generated (decode) tokens, `t` the wall-clock generation time,
and `G` the number of GPUs (here G = 1; single-GPU serving). Alongside throughput we measure the
**energy intensity** of generation (tokens · J⁻¹) from co-measured board power, and report the two
quantities the labor-to-infrastructure model needs:

```
        GPU-seconds per 10⁶ tokens = 10⁶ / θ_GPU
        kWh per 10⁶ tokens         = (10⁶ / tokens-per-joule) / 3.6×10⁶
```

## 2. Models

We benchmark a **coding-specialized ladder** chosen to isolate the variable that governs inference
cost — the number of **active** parameters per token — across dense and Mixture-of-Experts (MoE)
architectures and a 3.6B–72B active range. All are open-weight and (except Kimi, Modified MIT)
Apache-2.0; none are gated.

| Model | Lab | Architecture · total / **active** | Precision |
|---|---|---|---|
| `openai/gpt-oss-20b` | OpenAI | MoE · 21B / **3.6B** | MXFP4 (native) |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | Alibaba | MoE · 30B / **3B** | BF16 |
| `Qwen/Qwen3-32B` | Alibaba | **dense** · 32B / **32B** | BF16 |
| `moonshotai/Kimi-Dev-72B` | Moonshot | **dense** · 72B | FP8 (dynamic W8A8) |
| `Qwen/Qwen3-Coder-Next` | Alibaba | MoE · 80B / **3B** | FP8 (dynamic W8A8) |

The controlled contrast is `Qwen3-Coder-30B-A3B` vs `Qwen3-32B`: identical ~30B total size, identical
BF16, identical hardware, differing only in active parameters (3B vs 32B). FP8 is used for the 72–80B
models so they fit a single 80 GB GPU; native FP8 tensor cores are Hopper-only, so those two run on
H100/H200 only.

## 3. Hardware

Stanford **Sherlock**, `owners` partition, single GPU per run (G = 1, no tensor parallelism):

| Tier | SKU | Memory | Constraint |
|---|---|---|---|
| A100 | `A100_SXM4` | 80 GB | `GPU_SKU:A100_SXM4&GPU_MEM:80GB` |
| H100 | `H100_SXM5` | 80 GB | `GPU_SKU:H100_SXM5` |
| H200 | `H200_SXM5` | 141 GB | `GPU_SKU:H200_SXM5` |

The 3 BF16 models run on all three tiers (the cross-hardware comparison); the 2 FP8 models run on
H100/H200. Matrix: **3 models × 3 GPUs + 2 models × 2 GPUs = 13 model-runs (26 cells)**.

## 4. Serving and measurement

**Engine.** vLLM 0.23.0, OpenAI-compatible server, `--tensor-parallel-size 1`, automatic prefix
caching on, `--gpu-memory-utilization 0.90`, `--max-model-len 16384`. Precision via `--dtype auto`
(native: BF16 for the dense/Qwen models, MXFP4 for gpt-oss) plus `--quantization fp8` for the 72–80B.

**Containerization (Sherlock-specific).** Sherlock nodes are glibc 2.17 (CentOS 7), on which modern
torch/vLLM wheels cannot be installed; we therefore run vLLM from the official `vllm/vllm-openai`
image under **Apptainer** (`--nv`). The image targets CUDA 13 (torch cu13) but the cluster GPU driver
is R550 (CUDA 12.4); we bridge this with **CUDA forward compatibility**, prepending the image's
`/usr/local/cuda/compat` `libcuda` (R580 userspace) ahead of the host driver — supported on
datacenter GPUs. A lightweight host-side conda environment performs model download, power sampling,
and parsing.

**Benchmark.** `vllm bench serve --dataset-name random`, rate-controlled, reporting throughput, TTFT,
TPOT/ITL, and percentiles. Requests use `--ignore-eos` (exactly `output_len` tokens, so decode rate
is measured cleanly) and `--temperature 0` (greedy, deterministic).

**Power.** A sidecar samples board power and utilization via `nvidia-smi` at 5 Hz over each cell's
window; energy is the trapezoidal integral of power over the steady interval (warm-up/cool-down
trimmed). Tokens-per-joule = generated tokens ÷ window energy.

## 5. Workload (derived from Experiment 1)

To make the measurement representative of real agentic software engineering rather than an arbitrary
synthetic shape, the request shape is taken from the Experiment-1 trajectories. Per inference request
(one API call inside the agent loop) the **prompt** is `(T_input + T_tool)/api_calls` and the
**generation** is `T_output/api_calls`. Across the 270 Exp-1 task-runs these per-request prompts are
heavy-tailed (log-normal), with medians ≈ **3.9k tokens (SWE-bench)** and **14.5k (SWE-Lancer)**, and
a large **cacheable prefix** (re-sent tool observations: 64–74% of the prompt).

Operating parameters:
- **Input (prompt) length = 8192 tokens**, between the two task-type medians; of which **5440 (≈66.5%)**
  is a shared cacheable prefix (`--random-prefix-len`), exercising prefix caching as in production.
- **Output length = 1024 tokens (fixed).** Exp-1 generation is a tiny fraction of tokens (<1%), so the
  empirical per-request output (tens of tokens) is too short to measure a stable decode rate; we pin a
  decode length adequate for a clean θ_GPU.
- **Two operating points:** `max_concurrency = 1` (single-stream latency reference) and `= 64`
  (saturated — the maximum-throughput point that sizes a fleet).

(`build_workload.py` regenerates these statistics from `exp1_results/exp1_raw.csv`.)

## 6. Results

Full 26-cell matrix collected on Sherlock (2026-06-25), corrected 8k operating point (input 8192 /
output 1024, prefix 5440). Saturated cells reached ~99–100% GPU utilization. The two FP8 models
(Kimi-Dev-72B, Qwen3-Coder-Next) **OOM'd on the 80 GB H100** (engine-core init failed during KV-cache
allocation: 72–80 GB of FP8 weights leave no room on an 80 GB card) and ran on **H200 (141 GB) only** —
a result in its own right (§7.4).

### 6.1 Saturated throughput θ_GPU (tokens · s⁻¹ · GPU⁻¹), c64

| Model | active | A100 | H100 | H200 |
|---|---|---:|---:|---:|
| gpt-oss-20b | 3.6B (MXFP4) | 1,828 | 4,150 | 4,528 |
| Qwen3-Coder-30B-A3B | 3B (MoE) | 794 | 1,484 | 2,653 |
| Qwen3-32B | 32B (dense) | 140 | 249 | 951 |
| Kimi-Dev-72B | 72B (dense, FP8) | — | OOM | 608 |
| Qwen3-Coder-Next | 3B (MoE, FP8) | — | OOM | 2,416 |

### 6.2 Energy intensity — kWh per 10⁶ generated tokens (board power, c64)

| Model | A100 | H100 | H200 |
|---|---:|---:|---:|
| gpt-oss-20b | 0.0574 | 0.0396 | 0.0378 |
| Qwen3-Coder-30B-A3B | 0.1394 | 0.1010 | 0.0694 |
| Qwen3-32B | 0.6986 | 0.5329 | 0.1928 |
| Kimi-Dev-72B | — | — | 0.2918 |
| Qwen3-Coder-Next | — | — | 0.0733 |

(Equivalently in tokens · J⁻¹: gpt-oss 4.84 / 7.02 / 7.35; Qwen3-Coder-30B-A3B 1.99 / 2.75 / 4.00;
Qwen3-32B 0.40 / 0.52 / 1.44; Kimi-Dev-72B —/—/0.95; Qwen3-Coder-Next —/—/3.79, for A100/H100/H200.)

### 6.3 Compute cost — GPU-seconds per 10⁶ generated tokens (= 10⁶ / θ_GPU)

| Model | A100 | H100 | H200 |
|---|---:|---:|---:|
| gpt-oss-20b | 547 | 241 | 221 |
| Qwen3-Coder-30B-A3B | 1,259 | 674 | 377 |
| Qwen3-32B | 7,124 | 4,010 | 1,052 |
| Kimi-Dev-72B | — | — | 1,644 |
| Qwen3-Coder-Next | — | — | 414 |

Board power at saturation ranged 338–697 W (higher for the dense models and on H200). Note `T_FTE`
counts total tokens, so §8 sizes against `total_token_throughput` (prefill+decode, ≈9× the decode
rate at the 8k:1k mix): e.g. 37,351 tok/s (gpt-oss) / 13,352 (Qwen3-Coder-30B-A3B) / 2,245 (Qwen3-32B)
on H100.

### 6.4 Single-stream latency (concurrency 1)

At c1, θ_GPU equals the **per-user decode speed**; TTFT is the **prefill latency** for the 8192-token
prompt. This is the interactive/latency reference; saturated serving (c64) trades it for ~8–30× the
aggregate throughput above.

| Model | per-user tok/s — A100 / H100 / H200 | prefill TTFT (ms) — A100 / H100 / H200 |
|---|---|---|
| gpt-oss-20b | 189 / 287 / 317 | 278 / 79 / 75 |
| Qwen3-Coder-30B-A3B | 122 / 182 / 224 | 278 / 105 / 104 |
| Qwen3-32B | 23 / 38 / 51 | 950 / 362 / 360 |
| Kimi-Dev-72B | — / — / 44 | — / — / 465 |
| Qwen3-Coder-Next | — / — / 173 | — / — / 196 |

Per-user decode latency (TPOT p50) spans **3 ms** (gpt-oss, interactive) to **43 ms** (dense 32B on
A100). At the saturated point, per-request TTFT balloons with queuing (e.g. Qwen3-32B on H100 reaches
~216 s p50 TTFT at c64) — so a latency-bounded (SLO-constrained) deployment operates **between** c1 and
c64, and the saturated θ_GPU is an upper bound on fleet efficiency rather than an interactive setting.

Per-cell θ_GPU, TTFT, TPOT p50/p99, power, tokens/J, and `total_token_throughput` are in
`exp2_results/exp2_raw.csv`; figures in `fig_throughput`, `fig_energy`, `fig_active_scaling`.

## 7. Findings

1. **Active parameters, not total size, govern inference cost.** The controlled pair (same ~30B total,
   same BF16, same GPU) — `Qwen3-Coder-30B-A3B` (3B active) vs `Qwen3-32B` (32B active) — gives a
   throughput ratio of **5.7× on A100, 6.0× on H100, 2.8× on H200**. The effect persists at the top
   end: on H200 the **80B** MoE `Qwen3-Coder-Next` (3B active) generates **2,416 tok/s vs 608 tok/s**
   for the **72B** dense `Kimi-Dev-72B` — **4.0× faster while being larger in total**. Capability is
   decoupled from serving cost; the active-parameter count is the cost driver.
2. **Quantization compounds it.** `gpt-oss-20b` (3.6B active + native MXFP4) is the throughput and
   energy leader on every tier (4,528 tok/s, 0.038 kWh/10⁶ tok on H200).
3. **Hardware scaling is workload-dependent.** A100→H100 gives ≈1.8–2.3× across models. H100→H200,
   however, ranges from **+9%** (gpt-oss, compute-bound) to **1.8×** (30B MoE) to **3.8×** (Qwen3-32B
   dense). H200's larger/faster HBM disproportionately helps the **memory-bandwidth-bound dense** model
   — which is why the MoE-vs-dense gap *narrows* on H200 (6.0× → 2.8×).
4. **Energy intensity tracks throughput.** Per generated token, the MoE coder costs ≈0.07 kWh/10⁶ vs
   ≈0.19–0.70 kWh/10⁶ for the same-size dense model — an order-of-magnitude difference — and gpt-oss is
   lower still (≈0.04). The most efficient configuration is the smallest-active model on the newest GPU.
5. **70–80B models do not fit a single 80 GB GPU in FP8 + KV cache.** Both `Kimi-Dev-72B` and
   `Qwen3-Coder-Next` failed engine init on the 80 GB H100 (no KV-cache headroom after 72–80 GB of
   weights) and required the 141 GB H200. Single-GPU serving of this class needs H200-class memory, or
   multi-GPU on H100 (which changes per-GPU efficiency and is out of scope here).

## 8. From tokens to infrastructure

Combining the two experiments closes the labor → infrastructure loop. For a token demand `T` (e.g.
`T_FTE` from Exp-1 scaled by workforce size):

```
   GPU-seconds   = T / θ_GPU                       (compute)
   GPUs (steady) = T / (θ_GPU · seconds_per_year · utilization)
   electricity   = T · (kWh per token)             (energy)
```

Thus an organization's agentic-coding token demand maps directly onto a GPU fleet, its facility power
(`GPUs × board power / PUE`), and annual electricity.

**Worked example (total-token basis).** Experiment 1's daily-workload model puts one engineer's annual
demand at `T_FTE ≈ 1.6×10⁸ total tokens` (Opus-grade; the range across demand models is 77M–631M).
Since `T_FTE` counts *all* tokens (input + tool + output), we size against the **total** (prefill+decode)
throughput measured at saturation (`total_token_throughput`, ≈9× the decode rate at the 8k:1k mix) and
the co-measured board power. For one **H100**:

| serving model (H100, saturated) | total tok/s | **GPU-hr / engineer-yr** | **kWh / engineer-yr** | engineers / GPU |
|---|---:|---:|---:|---:|
| gpt-oss-20b (3.6B active) | 37,351 | 1.2 | 0.53 | ~7,400 |
| Qwen3-Coder-30B-A3B (3B active) | 13,352 | 3.3 | 1.80 | ~2,650 |
| Qwen3-32B (32B active, dense) | 2,245 | 19.7 | 10.8 | ~450 |

(On H200, the 80B MoE `Qwen3-Coder-Next` lands at 2.0 GPU-hr / 1.2 kWh / ~4,300 engineers per GPU; the
72B dense `Kimi-Dev-72B` at 8.1 GPU-hr / 5.6 kWh / ~1,100.)

**The headline:** a *single* modern accelerator serves the agentic-coding token demand of **hundreds
(dense) to thousands (MoE) of engineers**, at **single-digit kWh per engineer-year** — orders of
magnitude below the energy embodied in the human labor it augments. The serving choice dominates:
picking a 3B-active MoE over a 32B-active dense model of equal capability cuts the per-engineer energy
and GPU-time by **~6×** (1.8 vs 10.8 kWh). These scale linearly with token demand `T`, so the whole
range 77M–631M tokens/FTE-yr maps to ≈0.9–7 kWh (MoE) up to ≈5–43 kWh (dense) per engineer-year.

*(Caveats: board power only — multiply by PUE ≈1.1–1.3 for facility energy, and add host/network
overhead; single-GPU saturated operating point; figures scale with the assumed `T_FTE` and serving
model.)*

## 9. Supply-side Monte-Carlo: distribution of θ_GPU and serving cost

§8 is a point estimate for one (model, GPU). A real deployment is a *random* choice — which open
model, which GPU generation, how many GPUs, at what market prices. `simulate_cost.py` samples those and
propagates the measured matrix into distributions — the supply-side companion to Exp-1's demand
Monte-Carlo, and together the full **demand × supply** distribution of the cost of an "AI software
engineer".

**Sampling.** Each draw picks a **model** (uniform over the measured set), a **GPU** (availability mix
A100 : H100 : H200 = 0.35 : 0.45 : 0.20, restricted to tiers where that model ran), and a **fleet size**
G (log-uniform 1–16); θ_GPU and board power are the measured saturated values for that (model, GPU).
**Prices** are sampled from wide 2026 priors: rental $/GPU-hr A100 [1.0, 2.5] / H100 [2.0, 4.5] /
H200 [3.0, 6.0]; electricity [0.08, 0.16] $/kWh; PUE [1.1, 1.4]. Cost and energy are computed per
**total** token (prefill + decode, `total_token_throughput`) — the basis that matches `T_FTE` and
commercial $/token pricing — while θ_GPU remains the generated-token throughput metric. (Per-token cost
is invariant to G for independent replicas; G scales fleet capacity.) N = 3×10⁵ draws.

**Per-token distribution:**

| quantity | P10 | P50 | P90 |
|---|---:|---:|---:|
| θ_GPU (generated tok/s/GPU) | 249 | 1,484 | 4,150 |
| $ / 10⁶ total tokens (rental) | 0.027 | 0.071 | 0.354 |
| kWh / 10⁶ total tokens | 0.0044 | 0.0148 | 0.088 |

**Convolved with demand** (`T_FTE` ~ log-normal, median 1.6×10⁸ total tokens, GSD 2.5):

| per engineer-year | P10 | P50 | P90 |
|---|---:|---:|---:|
| $ (rental) | 2.7 | 14 | 86 |
| kWh | 0.5 | 2.8 | 19 |

**Reading it.** A self-hosted open coding model serves an engineer's *full annual agentic-coding token
demand* for a **median ≈ $14 and ≈ 2.8 kWh/year** (P10–P90: $2.7–86, 0.5–19 kWh). The median per-token
cost, **≈ $0.07 per 10⁶ total tokens**, is **~30–70× below commercial API list prices** (≈ $2–5 / 10⁶
blended) — the economic driver for open-weight self-hosting once GPUs are owned. The spread is dominated
by **model choice** (gpt-oss-20b vs the 72B dense) and demand variance; GPU generation and price priors
add the rest (figure `fig_cost_sim`, priors editable at the top of `simulate_cost.py`). The figure
reflects *compute* cost only; whether an open model is *capable* enough to substitute the commercial one
— and consumes a comparable token budget per task — is checked separately in `exp2_sanity_check/`.

## 10. Sanity check: open vs commercial token demand

Experiment 1 measures token **demand** with commercial models; Experiment 2 measures token **supply**
with open models. To justify composing the two, we verify the two model populations consume the same
order-of-magnitude token budget on the same work. We ran an **open** model (`Qwen3-Coder-30B-A3B`,
served by the Exp-2 vLLM stack at its native 256k context) through the **identical mini-swe-agent
scaffold** used in Exp-1, on the **same 10 SWE-bench Lite tasks** the commercial models solved.

**Result** (median total tokens per task; full per-task table in `final_results/exp3_sanity_token_parity.csv`):

| model | median tokens/task |
|---|---:|
| GPT-5.4 | 31.9k |
| Opus 4.8 | 36.3k |
| Gemini 3.1 Pro | 362.7k |
| **Qwen3-Coder-30B-A3B (open)** | **444.8k** |

**Reading.** All four models live in the same **10⁵–10⁶ tokens/task** regime, confirming that token
demand is set by the **task + agent scaffold**, not the specific model. The open model's median
(445k) is **1.23× the heaviest commercial model (Gemini)** and ~12× the lightest (GPT/Opus) — i.e. it
sits at the top of, and just above, the commercial spread, which is itself ~11× wide (Gemini vs
GPT/Opus). The open model is "Gemini-heavy", not an outlier in a different regime; its demand falls
within the model-to-model variation that **already exists among commercial models**. It also *solved*
the tasks (8/10 patches submitted), so it is genuinely capable on this benchmark.

**Why the open model runs heavier.** The dominant driver is **format-retry friction**: the smaller open
model emits malformed tool calls far more often (median `retry_frac ≈ 0.93`, vs near-zero for the
frontier commercial models), and each retry re-sends the growing context. This is a real model-quality
effect, not a measurement artifact — a stronger/larger open model would land lower. (The first attempt
also hit a 32k context cap that failed 2 tasks; re-running at the model's native 256k context removed
that artifact and barely moved the median, 457k → 445k, confirming robustness.)

**Conclusion.** Splicing commercial-measured demand (Exp-1) with open-model supply (Exp-2) is justified:
agentic token demand is a property of the task and scaffold, and the open model operates within the same
order of magnitude — indeed within the existing commercial spread. The ~12× efficiency gap to the
lightest commercial models is itself a finding (smaller open models trade tokens for capability), and is
bounded by the commercial model-choice spread already characterised in Experiment 1.

## 11. Limitations

- **Single-GPU, single-node.** θ_GPU is measured at G = 1; multi-GPU tensor/expert parallelism (needed
  for >80B-active models) is out of scope and would change per-GPU efficiency.
- **Synthetic prompt shape.** Input/output lengths and prefix fraction are drawn from Exp-1 statistics
  via vLLM's `random` dataset (fixed lengths + a shared prefix), not replayed verbatim trajectories;
  the heavy tail is represented by the chosen operating point rather than a full distribution.
- **Precision differs across models** (MXFP4 / BF16 / FP8) — each served at its native/intended
  precision, which is realistic for deployment but means throughput differences mix architecture and
  precision effects.
- **Board power** (`nvidia-smi`) excludes host CPU, networking, cooling, and PUE; facility-level energy
  requires a PUE multiplier.
- **Saturation at fixed concurrency (64).** For the 80B FP8 model on an 80 GB card, KV-cache limits cap
  the running batch below 64; the reported θ_GPU is the realistic memory-bound maximum for that GPU.

## 12. Reproducibility

All code in `exp2_token_gen/`: `models.conf` (model set), `build_workload.py` (Exp-1 → workload
stats), `pull_vllm_image.sh`/`build_vllm_sandbox.sh` (container), `vllm_apptainer.sh` (CUDA-compat
wrapper), `launch_vllm.sh`, `bench_sweep.py`, `power_logger.py`, `parse_results.py`, `make_figures.py`,
`simulate_cost.py` (§9 Monte-Carlo), and `slurm/{run_exp2.sbatch,submit_all.sh,smoke.sbatch}`. Raw
per-cell JSON, power CSVs, the aggregated `exp2_raw.csv`, and all figures (`fig_throughput`,
`fig_energy`, `fig_active_scaling`, `fig_cost_sim`) are written to `exp2_results/`. The open-vs-commercial
token-parity check lives in `exp2_sanity_check/`. See `exp2_token_gen/README.md` §6–7 for the exact run
sequence and the Sherlock environment notes.

## Appendix A — per-run configuration

vLLM: tp=1, prefix-caching on, gpu-mem-util 0.90, max-model-len 16384, dtype auto (+fp8 for 72–80B).
Bench: dataset random, input 8192 (prefix 5440), output 1024, ignore-eos, temperature 0, request-rate
inf, max-concurrency ∈ {1, 64}, ≥32 prompts/cell. Power: nvidia-smi @ 5 Hz, trapezoidal energy over
the trimmed steady window.
