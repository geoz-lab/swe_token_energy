# Project History & Summary — *From Tokens to Energy*

> A durable, human-readable record of everything built in this project (code, experiments, results,
> and the hard-won technical lessons), written so the work survives even if the Claude Code chat
> history is lost. Committed to GitHub (`geoz-lab/swe_token_energy`) so it is preserved online.
> Last updated: 2026-06-29.

---

## 0. What this project is

An empirical study of the **token → energy → cost economics of AI software-engineering agents**: how
many tokens an autonomous coding agent consumes per task, how fast and cheaply GPUs can generate those
tokens, and what that implies for the infrastructure, electricity, and cost of substituting software
engineering labor. Three experiments plus a unifying stochastic model:

| | Experiment | Question | Writeup |
|---|---|---|---|
| **Exp-1** | Token **demand** | Tokens per agentic SWE task, across frontier commercial models | `exp1_summary.md` |
| **Exp-2** | Inference **supply** | θ_GPU (tokens/s/GPU) + energy of open-weight coders on A100/H100/H200 | `exp2_summary.md` |
| — | Sanity check | Do open models consume a comparable per-task token budget to commercial? | `exp2_summary.md` §10 |
| **Exp-3** | **Cost model** | Cost/energy/GPUs per substituted software engineer (5-layer Monte-Carlo) | `exp3_summary.md` |

**Headline results**
- **Exp-1:** agentic tasks cost 10⁴–10⁶ tokens; model choice → ~11× spread; ≤1% of tokens are
  *generated* (the rest is re-sent, cacheable context → prefill-bound, caching-amenable).
  `T_FTE` ≈ 77–631 M tokens/FTE-yr.
- **Exp-2:** **active** parameters (not total size) drive throughput/energy. A 3B-active MoE coder
  (`Qwen3-Coder-30B-A3B`) delivers **~6× the θ_GPU and energy efficiency** of a same-size 32B-active
  dense model (`Qwen3-32B`). gpt-oss-20b (3.6B active, MXFP4) is the efficiency leader.
- **Sanity check:** open model median 445k tokens/task vs commercial 32k–363k — same 10⁵–10⁶ regime
  (≈Gemini-heavy), confirming demand is set by task+scaffold, not the specific model.
- **Exp-3 (per substituted engineer, fully-agentic volume):** **1 GPU serves ~175 engineers**;
  **~36 kWh and ~$2.35 electricity / engineer-year** — **~1,300× below** the API-priced equivalent
  (~$3,095). Energy is negligible; price is set by capital + margin.
- **Per-GPU reference:** one H100/H200 at 700 W TDP ≈ **6,100 kWh/yr** (9,566 facility @PUE 1.56,
  ~$574/yr); at our measured coding load ~4,400–5,100 kWh/yr.

---

## 1. Repository layout

```
README.md                  repo landing page (experiment index + headline results)
PLAN.md                    overall research plan
claude_summary.md          THIS FILE — full project history
exp1_summary.md / exp2_summary.md / exp3_summary.md   scientific writeups
.env.example               API-key template (.env itself is git-ignored — never committed)

exp1_token_consumption/    Exp-1 code (29 files)
exp1_results/              Exp-1 outputs (raw CSV + figures)
exp2_token_gen/            Exp-2 code (19 files)
exp2_results/              Exp-2 outputs (per-cell JSON, power CSVs, exp2_raw.csv, figures)
exp2_sanity_check/         open-vs-commercial token-parity check (5 files)
exp2_sanity_check_results/ sanity outputs (trajectories, sanity_raw.csv)
exp3_simulation/           Exp-3 five-layer Monte-Carlo (params.py, simulate.py, README)
exp3_results/              Exp-3 outputs (per-engineer CSVs, sensitivity, GPU reference, figures)
final_results/             consolidated clean CSVs + publication figures (36 files)
setup_sherlock.sh / sync_to_sherlock.sh   cluster helpers
```

---

## 2. Experiment 1 — agentic token demand (commercial models)

**Goal.** Measure tokens consumed per software-engineering task by frontier commercial models, via APIs,
on real benchmarks; derive `T_FTE` (tokens per FTE-year).

**Setup.** Scaffold = **mini-swe-agent v2.4.2** (bash-tool ReAct agent via LiteLLM). Benchmarks:
SWE-bench Lite/Verified (`princeton-nlp/SWE-bench_*`) and SWE-Lancer (`DCAgent2/swe-lancer`, Expensify
freelance IC tasks). Models: **GPT-5.4, Claude Opus 4.8, Gemini 3.1 Pro**. Ran on Stanford **Sherlock**
CPU nodes via SLURM + Apptainer. 270 task-runs total (210 SWE-bench + 60 SWE-Lancer), ~$216.

**Key code (`exp1_token_consumption/`).**
- `sample_tasks.py` / `sample_swelancer.py` — stratified task sampling → `task_manifest.json`,
  `swelancer_manifest.json`.
- `swebench.yaml` — agent config (system/instance/observation templates, step_limit 250, cost guards).
- `run_swelancer.py` — custom SWE-Lancer driver (`SingularityEnvironment`, `get_model` + `DefaultAgent`).
- `parse_trajectory.py` — reconstructs tokens from `.traj.json`: partitions `total = T_input + T_output
  + T_tool`; cost-anchors to billed cost where available (SWE-bench), else tiktoken-derived (SWE-Lancer).
- `fit_distributions.py` — fits **log-normal** per (model × benchmark), KS test, QQ-plots; daily-workload
  Monte-Carlo for `T_FTE`.
- `summarize.py`, `make_figure.py`, `estimate_cost.py`, `slurm/*.sbatch`.

**Results.** SWE-bench median tokens: GPT-5.4 28k / Opus 34k / Gemini 306k. SWE-Lancer: 190k / 524k /
1.49M. `T_FTE` = 77M (GPT) / 159M (Opus) / 631M (Gemini) tokens/FTE-yr. Log-normal fits validated
(KS p up to 0.99, QQ R² 0.957–0.986). Findings: model choice ~11× spread; real freelance tasks 5–16×
heavier than benchmarks; ≤1% of tokens are generation (58–86% are re-sent tool observations).

---

## 3. Experiment 2 — inference throughput & energy (open-weight models)

**Goal.** Measure θ_GPU = T_generated/(t·G) and energy intensity (tokens/J) for open coding models on
H100/A100/H200, to convert token demand into GPU fleet / power / electricity.

**Models (active-parameter ladder, all open):** `gpt-oss-20b` (MoE 3.6B active, MXFP4),
`Qwen3-Coder-30B-A3B` (MoE 3B), `Qwen3-32B` (dense 32B), `Kimi-Dev-72B` (dense 72B, FP8),
`Qwen3-Coder-Next` (MoE 80B/3B, FP8). Controlled contrast: 30B-A3B vs Qwen3-32B (same ~30B total, 3B
vs 32B active).

**Hardware.** Sherlock `owners` partition, single GPU: A100-80GB / H100-80GB / H200-141GB.
Matrix = 3 BF16 models × 3 GPUs + 2 FP8 models × 2 GPUs = **26 cells**.

**Method.** vLLM 0.23 OpenAI server + `vllm bench serve --dataset-name random`; input 8192 / output 1024
/ prefix 5440 (66.5% cacheable, from Exp-1); concurrency 1 (single-stream) and 64 (saturated).
`power_logger.py` samples board power via nvidia-smi at 5 Hz → tokens/J.

**Key code (`exp2_token_gen/`).** `models.conf`, `build_workload.py` (Exp-1 → workload stats),
`launch_vllm.sh`, `bench_sweep.py`, `power_logger.py`, `parse_results.py`, `make_figures.py`,
`simulate_cost.py` (supply-side Monte-Carlo), `slurm/{run_exp2.sbatch,submit_all.sh,smoke.sbatch}`,
plus the container helpers in §6.

**Results (saturated θ_GPU, tok/s/GPU):** gpt-oss 1828/4150/4528 (A100/H100/H200); 30B-A3B
794/1484/2653; Qwen3-32B 140/249/951; Kimi-72B —/OOM/608; Coder-Next —/OOM/2416. The two FP8 models
**OOM'd on 80 GB H100** (72–80 GB weights leave no KV room) → H200-only. Energy: 0.04–0.07 kWh/M tok
(MoE) vs 0.19–0.70 (dense). **Active params, not total size, drive everything.**

---

## 4. Sanity check — open vs commercial token demand

**Question.** Exp-1 measures demand with *commercial* models, Exp-2 supply with *open* models — are they
comparable? Ran `Qwen3-Coder-30B-A3B` (open, served by the Exp-2 vLLM stack at 256k context) through the
**identical Exp-1 scaffold** on the **same 10 SWE-bench Lite tasks**.

**Result.** Open median **445k tokens/task** vs commercial 32k (GPT) / 36k (Opus) / 363k (Gemini) — same
10⁵–10⁶ order of magnitude, ~1.2× Gemini, within the existing commercial spread. Solved 8/10 tasks.
Higher token use driven by format-retry friction (retry_frac ≈ 0.93). Confirms demand is a property of
task + scaffold. Code: `exp2_sanity_check/{slurm/run_sanity.sbatch, compare.py, tasks_10.txt}`.

---

## 5. Experiment 3 — five-layer Monte-Carlo cost model

**Framework (per substituted engineer, N=200k draws).**
```
L1 Labor   : 1 substituted FTE
L2 Demand  : D = T_FTE                          [fitted from Exp-1 log-normals: 3.47M tok/eng-day P50]
L3 Compute : R = D/86400 ; g = R/(theta·U)      [theta from Exp-2 total-token throughput]
L4 Energy  : p = g·P_GPU·PUE ; e = p·8760 ;  c_e = e·C_MWh   [P_GPU = measured board power]
   Cost    : c_api = 365·D·C_token              [retail-pricing comparison]
```

**Fitted inputs:** `T_FTE` composed as Q_small (20) SWE-bench + Q_lancer (4) SWE-Lancer tasks/day
(fully-agentic volume), task sizes from Exp-1 log-normals, model sampled uniformly. `theta`/`P_GPU`
sampled from Exp-2 saturated cells (deploy models gpt-oss/30B-A3B/Coder-Next/Kimi; GPU mix
A100:H100:H200 = .35:.45:.20).

**Literature priors (verified):** N_eng 19.6/24/28.7 M (JetBrains/Evans Data); PUE 1.30/1.56/1.70
(Uptime Institute 2024 avg = 1.56); U 0.3/0.5/0.7; C_MWh $40/60/100; C_token $0.5/2/5 per 1M.

**Results (P50):** 175 engineers/GPU, 36 kWh/engineer-yr, $2.35 energy, $3,095 API-equivalent. Biggest
uncertainty levers: utilization U (+65/−29%), task counts (±21–30%). Code: `exp3_simulation/params.py`,
`simulate.py`; outputs in `exp3_results/`; consolidated in `final_results/` (exp4_*.csv, fig8–11).

---

## 6. Hard-won technical lessons (Sherlock / infrastructure)

These cost real debugging time — recorded so they are never re-learned:

- **Sherlock is glibc 2.17 (CentOS 7):** modern torch/vLLM wheels can't be pip-installed. **Run vLLM
  from the official Apptainer image** (`vllm/vllm-openai`); a host conda env holds only glue
  (hf_hub, pynvml, pandas).
- **CUDA forward compatibility:** the vLLM image is CUDA 13 (torch cu13/R580) but the cluster driver is
  R550/CUDA 12.4 → engine init fails ("driver too old"). Fix: prepend the image's
  `/usr/local/cuda/compat` libcuda to `LD_LIBRARY_PATH` inside the container (`vllm_apptainer.sh`).
  `module load cuda` does NOT help (driver, not toolkit, is the issue).
- **Build the image as a `--sandbox` dir, not a `.sif`:** `apptainer pull`/mksquashfs gets SIGKILL'd
  (exit 137) by the login-node memory watchdog. Sandbox skips compression.
- **`owners` partition forbids interactive jobs** (`salloc` blocked) → use `sbatch` for everything.
- **Storage:** GROUP_HOME is only 1 TB; put `HF_HOME=$SCRATCH/hf` (100 TB) for the ~470 GB model set.
- **HF downloads:** `huggingface-cli` removed in huggingface_hub≥1.0 → use `hf download`; set
  `HF_HUB_DISABLE_XET=1` or Xet OOM-kills big downloads on login nodes.
- **Env vars lost on login-node hops** → put HF_HOME / HF_HUB_DISABLE_XET / VLLM_SIF in `~/.bashrc`.
- **vLLM 0.23 CLI:** `--disable-log-requests` removed; prefix caching on by default; `bench serve`
  ADDS `--random-prefix-len` ON TOP of `--random-input-len`.
- **Agent → local vLLM (litellm):** use the `openai/<model>` provider + `OPENAI_API_BASE`; serve with
  `--enable-auto-tool-choice --tool-call-parser qwen3_coder` (tools 400 otherwise); set
  `MSWEA_COST_TRACKING=ignore_errors` (no price entry for local models). Pre-cache the SWE-bench
  dataset on a login node; compute nodes have internet for the per-task images.

---

## 7. Git / reproducing / resuming

- **Repo:** `git@github.com:geoz-lab/swe_token_energy.git` (private). `.env` is git-ignored;
  copy `.env.example` → `.env` and add keys to reproduce Exp-1.
- **Run locally:** `python exp3_simulation/simulate.py`; `python final_results/build_tables.py`;
  `python final_results/make_pub_figures.py`; `python final_results/build_sanity.py`.
- **Run on Sherlock:** see each folder's README and §6 above.
- **Claude Code history:** transcripts are stored locally at
  `~/.claude/projects/<this-project>/*.jsonl` and persist across VSCode restarts — resume with
  `claude --continue` (last session) or `claude --resume` (pick a session). This `claude_summary.md`
  + the committed code are the durable, online record if that local history is ever lost.

---

## 8. Status

All three experiments complete, analyzed, written up, and packaged in `final_results/` (5 demand/supply
CSVs + sanity + exp4 cost CSVs + fig1–11, journal style via `pubstyle.py`). Pushed to GitHub. Outstanding
optional items: tornado/sensitivity figure for Exp-3; a `LICENSE`; surfacing the per-GPU reference in
`exp2_summary.md`.
