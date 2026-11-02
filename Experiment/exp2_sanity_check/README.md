# Experiment 2 — Sanity Check: open-weight token consumption on SWE-bench

## Why this exists

Experiment 1 measures **token demand** (`T_FTE`) using **commercial** frontier models (Claude / GPT /
Gemini). Experiment 2 measures **token supply** (θ_GPU, energy) using **open-weight** models. A natural
objection: *are these two populations comparable?* If an open model needed, say, 10× more tokens to
solve the same task, splicing commercial-demand with open-supply would be inconsistent.

This sanity check answers it directly: run an **open-weight** coding model (served by the same vLLM
stack as Exp-2) through the **identical mini-swe-agent scaffold** Exp-1 used, on the **same 10
SWE-bench Lite tasks** Exp-1 already ran on the commercial models, and compare per-task token
consumption. If the open model lands in the **same order of magnitude**, the cross-experiment splice is
justified.

Commercial reference on these tasks (Exp-1, SWE-bench Lite median total tokens/task):
**gpt-5.4 ≈ 28k · Opus 4.8 ≈ 37k · Gemini 3.1 Pro ≈ 318k.**

## Design

- **Tasks:** `tasks_10.txt` — 10 SWE-bench Lite instances, stratified across 8 repos, all of which have
  commercial token data in `exp1_results/exp1_raw.csv` (→ paired comparison on identical tasks).
- **Model:** an open coder served locally by vLLM (default `qwen3-coder-30b`; a strong single-GPU
  agentic coder). Optionally `gpt-oss-20b` as a second point.
- **Scaffold:** **reused verbatim** from Exp-1 — `exp1_token_consumption/swebench.yaml` (same system /
  instance / observation templates, step_limit 250) and `mini-extra swebench --environment-class
  singularity`. Only `--model` changes (to the local vLLM endpoint via litellm `hosted_vllm/…`).
- **Token reconstruction:** **reused verbatim** — `exp1_token_consumption/parse_trajectory.py`
  (tiktoken-derived, the same estimator Exp-1 used where billed cost was unavailable).
- **Comparison:** `compare.py` joins the open-model tokens with the commercial tokens on the same 10
  tasks and reports the ratio + a figure.

## Run (Sherlock, GPU node)

vLLM serves the open model on the GPU; the agent (in the Exp-1 conda env) drives SWE-bench tasks in
Apptainer and calls the local endpoint. Prereqs: Exp-2 `vllm.sif`/sandbox built, the model downloaded
(`$HF_HOME`), and the **SWE-bench task images cached** from Exp-1 (`$APPTAINER_CACHEDIR`).

```bash
# from Mac: sync, then on Sherlock submit the GPU job
sbatch -p owners --gres=gpu:1 -C "GPU_SKU:H100_SXM5|GPU_SKU:H200_SXM5" \
  --export=ALL,MODELS="qwen3-coder-30b",VLLM_SIF=$SCRATCH/vllm_sandbox,HF_HOME=$SCRATCH/hf \
  slurm/run_sanity.sbatch
tail -f exp2_sanity_*.out

# when done (results in ../exp2_sanity_check_results/sanity_raw.csv):
python compare.py
```

## Files

```
tasks_10.txt              the 10 SWE-bench Lite instance ids (paired with Exp-1)
slurm/run_sanity.sbatch   GPU job: serve open model (vLLM container) + run mini-swe-agent + parse
compare.py                open vs commercial token comparison → table + fig_sanity_tokens
```
(Serving reuses `../exp2_token_gen/{launch_vllm.sh,vllm_apptainer.sh,models.conf}`; the agent +
parser reuse `../exp1_token_consumption/{swebench.yaml,parse_trajectory.py}`.)

## Interpreting the result

Expected outcome: the open model's median total-tokens/task falls **within the commercial spread**
(≈28k–318k), i.e. the same order of magnitude — confirming that token *demand* is a property of the
**task + agent scaffold**, not of the specific frontier model, so Exp-1 (commercial demand) and Exp-2
(open supply) compose consistently. A large deviation (e.g. the open model looping to the step limit on
many tasks) would instead flag a caveat to state in the paper.
