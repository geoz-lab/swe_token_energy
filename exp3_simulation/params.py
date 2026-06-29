"""
params.py — prior distributions and constants for the Experiment-3 five-layer Monte-Carlo.

Each uncertain parameter is a (low, central, high) triangular prior. Sources are cited inline.
Two inputs are NOT here because they are *fitted from our own measurements*:
  - T_FTE  (tokens per FTE-day)        <- Experiment 1   (fit in simulate.py)
  - theta, P_GPU (throughput, power)   <- Experiment 2   (fit in simulate.py)
"""

# ---- Layer 1: labor ----
# Global professional software-developer population. JetBrains 2024 ≈ 19.6M (professional);
# Evans Data / Statista ≈ 27–28.7M. We span both methodologies.
#   https://blog.jetbrains.com/research/2025/01/global-developer-population-2024/
#   https://www.statista.com/statistics/627312/worldwide-developer-population/
N_ENG = (19.6e6, 24.0e6, 28.7e6)

# Effective FTE substitution-rate scenarios (Layer-1 scenario parameter, not a forecast).
SUBSTITUTION_RATES = [0.10, 0.30, 0.50, 0.70, 1.00]

# ---- Layer 2: token demand (workload composition; sizes fitted from Exp-1) ----
# A developer-day = Q_SMALL SWE-bench-like tasks + Q_LANCER SWE-Lancer-like tasks.
# Under a FULLY-AGENTIC production mode, one FTE-equivalent of output is far above a human's
# traditional pace: tens of small issue/bug-fix-scale tasks and several substantial
# (freelance-job-scale) tasks per day. (Tasks/day is a modeling choice — Exp-1 measured per-task
# tokens, not task volume — so this raises T_FTE above Exp-1's conservative 3+1/day placeholder.)
Q_SMALL = (10, 20, 30)     # small (SWE-bench) tasks per FTE-day
Q_LANCER = (2, 4, 6)       # large (SWE-Lancer) tasks per FTE-day
# Retry/iteration multiplier rho: retries are ALREADY included in the Exp-1 measured token counts,
# so the empirical T_FTE needs no extra rho (kept at 1; exposed for sensitivity only).
RHO = (1.0, 1.0, 1.5)

# ---- Layer 3: compute ----
# Average realized GPU utilization for production inference serving (queueing, batch composition,
# demand variation). Literature on LLM serving puts sustained utilization well below 1.
U_UTIL = (0.30, 0.50, 0.70)
# theta (total-token throughput) and P_GPU are sampled from the Exp-2 saturated cells (measured).

# ---- Layer 4: energy & cost ----
# Power usage effectiveness. Uptime Institute 2024 global average = 1.56; new builds ≈ 1.3;
# legacy/high ≈ 1.7.   https://datacenter.uptimeinstitute.com (2024 Global Data Center Survey)
PUE = (1.30, 1.56, 1.70)
# Industrial electricity price ($/MWh). US industrial ≈ $70–80/MWh; spans cheap-grid to high-cost.
C_MWH = (40.0, 60.0, 100.0)
# Commercial API token price for the API-cost comparison ($ per 1M total tokens, blended).
C_TOKEN_PER_1M = (0.5, 2.0, 5.0)

# ---- constants ----
SEC_PER_DAY = 86_400
HOURS_PER_YEAR = 8_760
DAYS_PER_YEAR = 365

# ---- supply (Exp-2) sampling weights ----
# Deployment GPU-availability mix and which open models are "good enough" to deploy. We exclude the
# dense Qwen3-32B from the default deployment set (dominated on throughput by the MoE coders at equal
# capability) but keep it available for sensitivity. Edit to taste.
GPU_MIX = {"A100": 0.35, "H100": 0.45, "H200": 0.20}
DEPLOY_MODELS = ["gpt-oss-20b", "Qwen3-Coder-30B-A3B", "Qwen3-Coder-Next", "Kimi-Dev-72B"]
