"""High-load token and benchmark-equivalent energy sensitivity.

This is intentionally separate from the accepted-task/FTE model. Gateway sessions,
Copilot turns, and micro-actions have different denominators. The 10x energy row is
an analyst stress multiplier, not a calibrated frontier-model estimate.
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

from grid_mix import SHARES, factor as mix_factor, sample_shares, write_source_table

BASE = Path(__file__).resolve().parent
OUT = BASE / "model_outputs"
OUT.mkdir(exist_ok=True)
write_source_table(BASE / "stage6_grid_source_probabilities.csv")
RNG = random.Random(20261102)
N_DRAWS = 10_000


def read_csv(name: str) -> list[dict[str, str]]:
    with (BASE / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)


def qtile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    i = math.floor(position)
    j = math.ceil(position)
    return ordered[i] + (ordered[j] - ordered[i]) * (position - i)


hw = {(r["gpu"], int(r["concurrency"])): r for r in read_csv("stage4_hardware_measured.csv")}
grid = next(float(r["median_kgco2e_per_kwh"]) for r in read_csv("stage7_carbon_factors.csv")
            if r["source"] == "US_eGRID")
assert abs(grid - .349667) < 1e-8

# A session is a gateway-defined request burst, not a verified SWE work item.
# Its lognormal spread is an analyst assumption: only its median is published.
SESSION_MEDIAN = 1_400_000
SESSION_SIGMA = .7

# The Copilot Table 4 marginal prompt quantiles define a two-quantile scenario
# curve. This is not a fitted empirical distribution; cached prompts are included.
TURN_PROMPT_MEDIAN = 227_600
TURN_PROMPT_P90 = 1_500_000
TURN_SIGMA = math.log(TURN_PROMPT_P90 / TURN_PROMPT_MEDIAN) / 1.2815515655446004
TURN_OUTPUT_RATIO = 1_900 / TURN_PROMPT_MEDIAN  # ratio of marginal medians, illustrative

# For microaction cases, A equal-human-time work units partition one paid
# engineer-day (8/A human hours each). q is the *targeted attempted FTE/day*;
# realized attempted FTE/day in a draw is N_agent/A. Equal effort and one
# gateway session per delegated unit are analyst stress assumptions. Neither
# quantity is verified net FTE replacement or a completed-task count.
CASES = [
    ("micro20_q30_session", "session_per_delegated_microaction", 20, .30, "H100", 1),
    ("micro40_q50_session", "session_per_delegated_microaction", 40, .50, "H100", 1),
    ("micro60_q70_session", "session_per_delegated_microaction", 60, .70, "H100", 1),
    ("micro40_q50_h200", "session_per_delegated_microaction", 40, .50, "H200", 1),
    ("turn20_copilot", "copilot_user_turn", 20, 1., "H100", 1),
    ("gateway_active_day_median", "observed_account_day_p50", 1, 1., "H100", 1),
    ("gateway_active_day_p90", "observed_account_day_p90", 1, 1., "H100", 1),
    # Crossed work-density × FTE scenarios for the seven-stage fan. Keep the
    # original cases above in place so their seeded draws remain reproducible.
    ("micro40_q30_session", "session_per_delegated_microaction", 40, .30, "H100", 1),
    ("micro40_q70_session", "session_per_delegated_microaction", 40, .70, "H100", 1),
    ("micro20_q50_session", "session_per_delegated_microaction", 20, .50, "H100", 1),
    ("micro20_q70_session", "session_per_delegated_microaction", 20, .70, "H100", 1),
    ("micro60_q30_session", "session_per_delegated_microaction", 60, .30, "H100", 1),
    ("micro60_q50_session", "session_per_delegated_microaction", 60, .50, "H100", 1),
]

fields = ["case", "draw", "unit", "candidate_interactions", "delegation_share",
          "attempted_fte_day", "assumed_human_hours_per_unit",
          "modeled_agent_units", "total_tokens", "gpu", "benchmark_gpu_seconds",
          "benchmark_board_kwh", "host_to_board_factor", "pue",
          "benchmark_facility_kwh", "us_grid_kgco2e_per_kwh", "benchmark_kgco2e",
          "mix_lifecycle_factor_low", "mix_lifecycle_factor_median", "mix_lifecycle_factor_high",
          "mix_lifecycle_kgco2e_low", "mix_lifecycle_kgco2e_median",
          "mix_lifecycle_kgco2e_high"] + [f"grid_share_{s}" for s in SHARES]
draws: list[dict] = []
for case, unit, opportunities, share, gpu, concurrency in CASES:
    power = float(hw[(gpu, concurrency)]["mean_board_w"])
    rate = float(hw[(gpu, concurrency)]["total_tokens_per_second"])
    for draw_id in range(N_DRAWS):
        if unit == "session_per_delegated_microaction":
            count = sum(RNG.random() < share for _ in range(opportunities))
            tokens = sum(RNG.lognormvariate(math.log(SESSION_MEDIAN), SESSION_SIGMA)
                         for _ in range(count))
        elif unit == "copilot_user_turn":
            count = opportunities
            prompt = sum(RNG.lognormvariate(math.log(TURN_PROMPT_MEDIAN), TURN_SIGMA)
                         for _ in range(count))
            tokens = prompt * (1 + TURN_OUTPUT_RATIO)
        elif unit == "observed_account_day_p50":
            count, tokens = 1, 8_600_000
        else:
            count, tokens = 1, 87_000_000
        gpu_s = tokens / rate
        board_kwh = gpu_s * power / 3_600_000
        host_factor = RNG.triangular(1, 1.4, 1.2)
        pue = RNG.triangular(1.2, 1.6, 1.4)
        facility_kwh = board_kwh * host_factor * pue
        shares = sample_shares(RNG)
        low_factor, median_factor, high_factor = (mix_factor(shares, j) for j in (0, 1, 2))
        draws.append(dict(case=case, draw=draw_id, unit=unit,
                          candidate_interactions=opportunities, delegation_share=share,
                          attempted_fte_day=count/opportunities if unit == "session_per_delegated_microaction" else "",
                          assumed_human_hours_per_unit=8/opportunities if unit == "session_per_delegated_microaction" else "",
                          modeled_agent_units=count, total_tokens=tokens, gpu=gpu,
                          benchmark_gpu_seconds=gpu_s, benchmark_board_kwh=board_kwh,
                          host_to_board_factor=host_factor, pue=pue,
                          benchmark_facility_kwh=facility_kwh,
                          us_grid_kgco2e_per_kwh=grid,
                          benchmark_kgco2e=facility_kwh * grid,
                          mix_lifecycle_factor_low=low_factor,
                          mix_lifecycle_factor_median=median_factor,
                          mix_lifecycle_factor_high=high_factor,
                          mix_lifecycle_kgco2e_low=facility_kwh * low_factor,
                          mix_lifecycle_kgco2e_median=facility_kwh * median_factor,
                          mix_lifecycle_kgco2e_high=facility_kwh * high_factor,
                          **{f"grid_share_{s}": shares[s] for s in SHARES}))
write_csv("high_load_draws.csv", draws, fields)

summary = []
for case, unit, opportunities, share, gpu, _ in CASES:
    subset = [d for d in draws if d["case"] == case]
    summary_metrics = [("modeled_agent_units", "agent_units/day"),
                          ("total_tokens", "raw_tokens/day"),
                          ("benchmark_gpu_seconds", "GPU_seconds/day"),
                          ("benchmark_facility_kwh", "kWh/day"),
                          ("benchmark_kgco2e", "kgCO2e/day"),
                          ("mix_lifecycle_factor_low", "kgCO2e/kWh"),
                          ("mix_lifecycle_factor_median", "kgCO2e/kWh"),
                          ("mix_lifecycle_factor_high", "kgCO2e/kWh"),
                          ("mix_lifecycle_kgco2e_low", "kgCO2e/day"),
                          ("mix_lifecycle_kgco2e_median", "kgCO2e/day"),
                          ("mix_lifecycle_kgco2e_high", "kgCO2e/day")]
    if unit == "session_per_delegated_microaction":
        summary_metrics.insert(0, ("attempted_fte_day", "attempted_FTE/day"))
    for metric, units in summary_metrics:
        values = [float(d[metric]) for d in subset]
        summary.append(dict(case=case, unit=unit, candidate_interactions=opportunities,
                            delegation_share=share, gpu=gpu, metric=metric, measure_unit=units,
                            p10=f"{qtile(values,.1):.9g}", p50=f"{qtile(values,.5):.9g}",
                            p90=f"{qtile(values,.9):.9g}",
                            interpretation="conditional benchmark-equivalent proxy"))
write_csv("high_load_summary.csv", summary, list(summary[0]))

print(f"Wrote {len(draws):,} high-load sensitivity draws across {len(CASES)} cases")
