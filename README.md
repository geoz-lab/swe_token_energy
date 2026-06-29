# From Tokens to Energy — the token/energy/cost economics of AI software-engineering agents

Empirical study linking software-engineering **labor** → **token demand** → **GPU compute** →
**energy and cost**, in three experiments plus a unifying stochastic model.

| | Experiment | Question | Writeup |
|---|---|---|---|
| **Exp-1** | Agentic token **demand** | How many tokens does an agent consume per SWE task, across frontier commercial models? | [`exp1_summary.md`](exp1_summary.md) |
| **Exp-2** | Inference **supply** | What throughput (θ_GPU) and energy intensity do open-weight coders achieve on A100/H100/H200? | [`exp2_summary.md`](exp2_summary.md) |
| — | Sanity check | Do open models consume a comparable per-task token budget to commercial ones? | [`exp2_summary.md`](exp2_summary.md) §10 |
| **Exp-3** | **Cost model** | Cost/energy/GPUs per substituted software engineer (5-layer Monte-Carlo fitting Exp-1 + Exp-2) | [`exp3_summary.md`](exp3_summary.md) |

## Headline results

- **Demand (Exp-1):** agentic SWE tasks cost 10⁴–10⁶ tokens; model choice drives an ~11× spread; ≤1% of tokens are generated (the rest is re-sent, cacheable context).
- **Supply (Exp-2):** **active** parameters (not total size) drive throughput — a 3B-active MoE coder delivers ~6× the θ_GPU and energy efficiency of a same-size 32B-active dense model.
- **Cost (Exp-3):** under fully-agentic production, **one GPU serves ~175 engineers**; **~36 kWh and ~$2.35 electricity per engineer-year** — roughly **1,300× below** the API-priced equivalent (~$3,095). Energy is negligible; price is set by capital and margin.

## Layout

```
exp1_token_consumption/   Exp-1 code (mini-swe-agent on SWE-bench / SWE-Lancer)
exp1_results/             Exp-1 outputs (raw CSV + figures)
exp2_token_gen/           Exp-2 code (vLLM throughput/energy on Sherlock GPUs)
exp2_results/             Exp-2 outputs (per-cell JSON, power CSVs, exp2_raw.csv, figures)
exp2_sanity_check/        open-vs-commercial token-parity check
exp3_simulation/          Exp-3 five-layer Monte-Carlo (params.py, simulate.py)
exp3_results/             Exp-3 outputs (per-engineer CSVs, sensitivity, figures)
final_results/            consolidated clean CSVs + publication figures (pubstyle.py)
exp{1,2,3}_summary.md      scientific writeups
PLAN.md                   overall plan
```

## Reproducing

Each experiment folder has its own README and environment file. Exp-1/Exp-2 run on the Stanford
**Sherlock** cluster (SLURM + Apptainer); Exp-3 and all figures run locally:

```bash
python exp3_simulation/simulate.py     # five-layer model
python final_results/build_tables.py   # consolidated CSVs
python final_results/make_pub_figures.py
```

## Configuration

Copy `.env.example` → `.env` and add API keys for the Exp-1 commercial-model runs. **`.env` is
git-ignored** — never commit live credentials.
