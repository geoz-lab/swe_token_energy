# Experiment data used by the poster model

This directory contains the empirical inputs and acquisition methods used by the seven-stage poster model. It is a curated subset of the larger exploratory project.

| Input | Contents | Poster use |
|---|---|---|
| [Agent-task records](exp1_results/exp1_raw.csv) | 270 task attempts across three commercial models and two benchmark families | Local token-demand evidence; `resolved` was not measured |
| [Experiment 1 methods](exp1_summary.md) and [code](exp1_token_consumption/) | Task sampling, agent scaffold, and reconstructed-token methodology | Interpretation of task-token records |
| [GPU cell summary](exp2_results/exp2_raw.csv) | Open-model throughput, board power, and benchmark settings | Hardware evidence |
| [Per-cell GPU measurements](exp2_results/) and [measurement code](exp2_token_gen/) | Benchmark JSON and power time series for A100, H100, and H200 | Audit and reproduction of measured cells |
| [Poster hardware input](final_results/exp2_supply_all_cells.csv) | Consolidated table consumed by the figure generator | Stage 4 figure data |

The numerical model reads `exp1_results/exp1_raw.csv` and `final_results/exp2_supply_all_cells.csv` directly. The benchmark uses an 8,192-token prompt and 1,024-token output at concurrency 1 or 64 with prefix caching. The poster's main scenario uses one measured H100/Qwen3-Coder-30B-A3B cell as a **benchmark-equivalent conversion**, not a measurement of commercial-agent serving hardware. Aggregate task records do not include the original full trajectories; rerunning acquisition needs the documented cluster, model access, and external benchmark datasets.

Historical cost simulations, unrelated drafts, duplicate graphics, and cluster logs are omitted from this public release. See the [numerical methods](../AGU_Token/numerical/README.md) and [source audit](../AGU_Token/numerical/SOURCE_AUDIT.md) for the model assumptions and limitations.
