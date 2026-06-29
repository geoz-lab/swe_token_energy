# Experiment 2 — Inference Throughput & Energy (token generation per GPU)

**Objective.** Measure the effective inference capacity of modern accelerators for open-weight coding
models, to parameterise the compute-throughput layer of the labor-to-infrastructure model. Primary
metric:

    θ_GPU = T_generated / (t · G)         (tokens / second / GPU)

plus the energy intensity **tokens/joule** (θ_GPU · G ÷ board power), which converts the Exp-1 token
demand into GPU-fleet size, facility power, and electricity.

Runs on **Sherlock GPU nodes** (Exp-1 used CPU; Exp-2 needs GPU), via the **`owners`** partition
(single GPU, G=1; lightweight models → no tensor parallelism). Confirmed hardware (2026-06-24):

| Tier | SKU | Mem | `sbatch` |
|---|---|---|---|
| A100 | `A100_SXM4` | 80 GB | `-p owners --gres=gpu:1 -C "GPU_SKU:A100_SXM4&GPU_MEM:80GB"` |
| H100 | `H100_SXM5` | 80 GB | `-p owners --gres=gpu:1 -C "GPU_SKU:H100_SXM5"` |
| H200 *(bonus)* | `H200_SXM5` | 141 GB | `-p owners --gres=gpu:1 -C "GPU_SKU:H200_SXM5"` |

The H100-vs-A100(-vs-H200) comparison runs on every model. Results → `exp2_results/`.

---

## 1. Models — coding-specialized active-param ladder (final, ungated/open)

| key | HF id | arch · total / **active** | precision · tiers |
|---|---|---|---|
| `gpt-oss-20b` | `openai/gpt-oss-20b` | MoE · 21B / **3.6B** | BF16 · A100·H100·H200 |
| `qwen3-coder-30b` | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | MoE · 30B / **3B** | BF16 · A100·H100·H200 |
| `qwen3-32b` | `Qwen/Qwen3-32B` | **dense** · 32B / **32B** | BF16 · A100·H100·H200 |
| `kimi-dev-72b` | `moonshotai/Kimi-Dev-72B` | **dense** · 72B | FP8 · H100·H200 |
| `qwen3-coder-next` | `Qwen/Qwen3-Coder-Next` | MoE · 80B / **3B** | FP8 · H100·H200 |

All Apache-2.0 (Kimi: Modified MIT) — ungated, no HF token. Chosen to span the variable that
drives θ_GPU: **active params 3B → 3.6B → 32B → 72B**, dense vs MoE. The key contrast is
`qwen3-coder-30b` vs `qwen3-32b` — ~30B total either way, but 3B-active MoE vs 32B-active dense.
FP8 (dynamic W8A8) is Hopper-only, so the 72-80B models are H100/H200; the BF16 trio gives the
clean A100-vs-H100-vs-H200 comparison. Model set lives in `models.conf`.

## 2. Serving + benchmark

**vLLM** OpenAI server + `vllm bench serve --dataset-name random` (online, rate-controlled →
TTFT/TPOT/percentiles + throughput). Single GPU, `--tensor-parallel-size 1` (G=1), automatic
prefix caching ON. Conda env `environment-sherlock-gpu.yml` (vLLM bundles its own CUDA).

## 3. Workload — representative, derived from Exp-1

Driven by the per-request token shape measured in Exp-1 (`build_workload.py` → `workload_stats.json`):
agentic SE is input-heavy with a large cacheable prefix.

- **input_len = 8192** (between the SWE-bench ~3.9k and SWE-Lancer ~14.5k per-request medians)
- **output_len = 1024** (fixed: Exp-1 generation is tiny, so we pin a decode length long enough to
  measure a stable θ_GPU)
- **prefix_frac ≈ 0.665** → `--random-prefix-len` ≈ 5440 (Exp-1 mean re-sent-tool-output share),
  so vLLM prefix caching is exercised as in production
- **2 operating points**: `max_concurrency = 1` (single-stream latency reference) and `= 64`
  (saturated → the max-θ_GPU fleet-sizing number)

## 4. Metrics (per cell) and the headline quantities

θ_GPU = output-token throughput (G=1); also total throughput, TTFT, TPOT/ITL p50/p99, GPU/mem util,
and **board power** co-measured by `power_logger.py`. `parse_results.py` derives:

```
theta_GPU          = output_throughput                 (tokens/s/GPU)
tokens_per_joule   = total_output_tokens / energy_J     (energy intensity)
gpu_seconds_per_1M = 1e6 / theta_GPU                    } the "X tokens -> compute & energy"
kWh_per_1M_tokens  = (1e6 / tokens_per_joule) / 3.6e6   } lookup the paper needs
```

## 5. Files (`exp2_token_gen/`)

vLLM runs from its **official Apptainer image** (Sherlock is glibc-2.17 → modern torch/vLLM wheels
can't be pip-installed). The conda env holds only host-side glue (download, power, parsing).

```
environment-sherlock-gpu.yml   conda env: host glue only (hf_hub, pynvml, pandas) — NO vllm
pull_vllm_image.sh             LOGIN node: apptainer pull -> $GROUP_HOME/vllm.sif
vllm_apptainer.sh              wrapper: run `vllm ...` inside the container (--nv, HF binds)
models.conf                    model set: key | hf_id | precision | max_len | tiers
build_workload.py              Exp-1 per-request token stats -> workload_stats.json (+jsonl)
download_models.sh             pre-fetch weights on a LOGIN node (-> $HF_HOME, offline-ready)
launch_vllm.sh                 start vLLM server (via $VLLM_BIN), wait for /health, print PID
bench_sweep.py                 2 operating points via vllm bench serve, + power sidecar/cell
power_logger.py                NVML/nvidia-smi power+util sampler on the HOST (per-cell series)
parse_results.py               aggregate -> exp2_results/exp2_raw.csv (θ_GPU, tokens/J, $/energy)
smoke_test.sh                  fast 1-model/1-GPU pipeline check; asserts a θ_GPU row appears
slurm/smoke.sbatch             submit the smoke test (owners has no interactive jobs)
slurm/run_exp2.sbatch          one GPU job per tier; loops its models
slurm/submit_all.sh            submit A100 + H100 + H200 jobs with the right -C constraints
```

## 6. How to run (Sherlock)

```bash
# 0) one-time on a LOGIN node (has internet): env + container image + weights
conda env create -f environment-sherlock-gpu.yml
conda activate token-energy-exp2
pip install "huggingface_hub[hf_transfer]>=0.34" "aiohttp>=3.10" "pynvml>=11.5"   # if env predates this
cd exp2_token_gen
./pull_vllm_image.sh                                   # -> $GROUP_HOME/vllm.sif (~6-9 GB)
export HF_HOME=$GROUP_HOME/hf
./download_models.sh gpt-oss-20b                       # small one first for the smoke test

# 1) smoke-test ONE model via sbatch (owners forbids interactive salloc)
sbatch -p owners --gres=gpu:1 -C "GPU_SKU:H100_SXM5" \
       --export=ALL,SMOKE_KEY=gpt-oss-20b,SMOKE_TIER=H100 slurm/smoke.sbatch
tail -f exp2_smoke_*.out                               # look for green [smoke] PASS
# (optional) refresh Exp-1-derived workload stats:  python build_workload.py

# 2) download the rest, then submit one GPU job per tier (~20-45 min each)
./download_models.sh                                   # remaining 4 models
./slurm/submit_all.sh                                  # or: ./slurm/submit_all.sh H100
squeue -u $USER ;  tail -f exp2_exp2_*.out

# 3) results -> ../exp2_results/exp2_raw.csv (parse_results runs at end of each job;
#    re-aggregate any time:  python parse_results.py)
```

Estimated cost: ~1.7 GPU-hr active compute (~3-4 hr wall incl. warmup/queue). See PLAN.md.

## 7. Notes / caveats
- **Why a container.** Sherlock login + compute nodes are glibc-2.17 (CentOS 7); torch ≥2.7 ships
  only glibc-2.28 wheels, so `pip install vllm` fails (`No matching distribution for torch==2.8.0`).
  We run vLLM from `vllm/vllm-openai` via Apptainer (`--nv`), which bundles its own OS/CUDA/torch.
  `VLLM_BIN` selects native `vllm` vs the wrapper, so the scripts are dual-mode.
- **No interactive jobs on `owners`.** Use `sbatch` for everything (the smoke test too — `slurm/smoke.sbatch`).
- **FP8 download.** Dynamic FP8 loads the **BF16** repo then quantizes at load (job needs the big
  download + `--mem`; we request 256G). If an official `*-FP8` checkpoint exists, set its id in
  `models.conf` with `precision=bf16` (vLLM reads the quant from the checkpoint) to halve both.
- **Saturated concurrency.** 64 is a target; for the 72-80B FP8 models on an 80 GB card, KV space
  caps the running batch below 64 — that *is* the real saturated θ_GPU for that GPU, and is exactly
  why H200's 141 GB should show a higher number (more KV → larger batch).
