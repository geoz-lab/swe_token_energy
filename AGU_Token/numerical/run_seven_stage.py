"""Seven-stage conditional Monte Carlo examples for the AGU poster.

All outputs are proxy scenarios. Closed-model / gateway token traces are mapped to
an open-model benchmark only to show the arithmetic, not to estimate their actual
provider electricity. See README.md for the measurement boundary and limitations.
"""

from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from pathlib import Path

from grid_mix import GRID_SHARE_CONCENTRATION, SHARES, factor as mix_factor, sample_shares, write_source_table


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "model_outputs"
OUT.mkdir(exist_ok=True)
write_source_table(BASE / "stage6_grid_source_probabilities.csv")
RNG = random.Random(20261101)
DRAWS_PER_CASE = 10_000
PAID_HOURS = 8.0  # normalizing assumption, not a measured Microsoft daily total


def read(name: str, root: Path = BASE) -> list[dict[str, str]]:
    with (root / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write(name: str, fields: list[str], data: list[dict]) -> None:
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


# Shares of the 8-hour example from the Microsoft 484-developer survey.
# Only these four activities are modeled; the other 69% of paid time is outside
# the agent-task numerator. Review and architecture token mappings are weak proxies.
families = ("debugging", "coding_new_features", "architecting_and_design", "PR_and_code_review")
evidence_shares = {r["activity"]: float(r["value"]) / 100
                   for r in read("stage2_workday_evidence.csv")
                   if r["source_id"] == "MS_TimeWarp_2025" and r["activity"] in families}
WORK_SHARE = {family: evidence_shares[family] for family in families}
assert set(WORK_SHARE) == set(families)
TRACKED_SHARE = sum(WORK_SHARE.values())
assert abs(TRACKED_SHARE - .31) < 1e-12
WEIGHTS = {k: v / TRACKED_SHARE for k, v in WORK_SHARE.items()}
TRACKED_HOURS = PAID_HOURS * TRACKED_SHARE
assert {float(r["ai_work_share"]) for r in read("stage1_fte_scenarios.csv")} == {.3,.5,.7}

factor_rows = read("stage7_carbon_factors.csv")
US_KGCO2E_KWH = float(next(r["median_kgco2e_per_kwh"] for r in factor_rows
                           if r["source"] == "US_eGRID"))
HDC_KGCO2_KWH = float(next(r["value"] for r in read("stage6_datacenter_supply_evidence.csv")
                            if r["source_id"] == "Guidi_2026" and
                            r["metric"] == "electricity_weighted_carbon_intensity"))
facility_rows = {r["parameter"]: r for r in read("stage5_model_parameters.csv")}


def triangular_parameter(name: str) -> float:
    row = facility_rows[name]
    return RNG.triangular(float(row["low"]), float(row["high"]), float(row["mode"]))

duration_rows = read("stage2_duration_sensitivity.csv")
DURATION = {r["activity"]: tuple(float(r[k]) for k in
            ("short_task_hours", "central_task_hours", "long_task_hours"))
            for r in duration_rows}
assert set(DURATION) == set(WORK_SHARE)

raw = read("Experiment/exp1_results/exp1_raw.csv", ROOT)
assert len(raw) == 270 and all(not r["resolved"] for r in raw)
TRACE: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
for r in raw:
    benchmark = "SWE-bench" if "__" in r["instance_id"] else "SWE-Lancer"
    TRACE[(r["model"], benchmark)].append(
        (float(r["raw_input_est"]), float(r["raw_output_est"])))
for model in ("gpt-5.4", "claude-opus-4-8", "gemini-3.1-pro-preview"):
    assert len(TRACE[(model, "SWE-bench")]) == 70
    assert len(TRACE[(model, "SWE-Lancer")]) == 20

BENCHMARK_FOR = {"debugging": "SWE-bench", "coding_new_features": "SWE-Lancer",
                 "architecting_and_design": "SWE-Lancer", "PR_and_code_review": "SWE-bench"}
HARDWARE = {(r["gpu"], int(r["concurrency"])): r
            for r in read("stage4_hardware_measured.csv")}

# Cases are controlled contrasts: work share, token source, task-day denominator,
# hardware, and serving load are varied one at a time around survey50_gpt_h100.
CASES = [
    ("survey30_gpt_h100", .30, TRACKED_HOURS, "gpt-5.4", "H100", 1),
    ("survey50_gpt_h100", .50, TRACKED_HOURS, "gpt-5.4", "H100", 1),
    ("survey70_gpt_h100", .70, TRACKED_HOURS, "gpt-5.4", "H100", 1),
    ("survey50_claude_h100", .50, TRACKED_HOURS, "claude-opus-4-8", "H100", 1),
    ("survey50_gemini_h100", .50, TRACKED_HOURS, "gemini-3.1-pro-preview", "H100", 1),
    ("survey50_session_h100", .50, TRACKED_HOURS, "session_proxy", "H100", 1),
    ("fourhour50_gpt_h100", .50, 4.00, "gpt-5.4", "H100", 1),
    ("survey50_gpt_h200", .50, TRACKED_HOURS, "gpt-5.4", "H200", 1),
    ("survey50_gpt_h100_c64", .50, TRACKED_HOURS, "gpt-5.4", "H100", 64),
]


def token_pair(source: str, family: str) -> tuple[float, float]:
    if source == "session_proxy":
        # Assumption: one gateway session corresponds to one task; Standard
        # Compute reports only a 1.4M median, not a task-level distribution.
        # sigma=0.7 is analyst-selected and is NOT an empirical estimate.
        total = RNG.lognormvariate(math.log(1_400_000), .7)
        return total * 192 / 193, total / 193
    return RNG.choice(TRACE[(source, BENCHMARK_FOR[family])])


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    x = (len(values) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] + (values[hi] - values[lo]) * (x - lo)


draw_fields = ["case", "draw", "delegated_hours", "paid_fte_equivalent_attempted",
               "attempted_tasks", "input_tokens", "output_tokens", "total_tokens",
               "gpu_seconds", "board_kwh", "server_multiplier", "pue",
               "facility_kwh", "grid_kgco2e_per_kwh", "operational_kgco2e",
               "hdc_sensitivity_kgco2", "mix_lifecycle_factor_low", "mix_lifecycle_factor_median",
               "mix_lifecycle_factor_high", "mix_lifecycle_kgco2e_low",
               "mix_lifecycle_kgco2e_median", "mix_lifecycle_kgco2e_high"] + [f"grid_share_{s}" for s in SHARES]
draws = []
for case, delegated_share, tracked_hours, source, gpu, concurrency in CASES:
    hw = HARDWARE[(gpu, concurrency)]
    throughput = float(hw["total_tokens_per_second"])
    board_watts = float(hw["mean_board_w"])
    for draw_number in range(DRAWS_PER_CASE):
        attempted = input_tokens = output_tokens = 0.0
        for family in WORK_SHARE:
            low, mode, high = DURATION[family]
            human_hours_per_task = RNG.triangular(low, high, mode)
            count = tracked_hours * WEIGHTS[family] * delegated_share / human_hours_per_task
            tin, tout = token_pair(source, family)
            attempted += count
            input_tokens += count * tin
            output_tokens += count * tout
        total = input_tokens + output_tokens
        gpu_seconds = total / throughput  # benchmark-equivalent proxy only
        board_kwh = board_watts * gpu_seconds / 3_600_000
        server = triangular_parameter("host_to_board_energy_factor")
        pue = triangular_parameter("pue")
        facility_kwh = board_kwh * server * pue
        shares = sample_shares(RNG)
        low_factor, median_factor, high_factor = (mix_factor(shares, j) for j in (0, 1, 2))
        draws.append(dict(case=case, draw=draw_number,
                          delegated_hours=tracked_hours * delegated_share,
                          paid_fte_equivalent_attempted=tracked_hours * delegated_share / PAID_HOURS,
                          attempted_tasks=attempted, input_tokens=input_tokens,
                          output_tokens=output_tokens, total_tokens=total,
                          gpu_seconds=gpu_seconds, board_kwh=board_kwh,
                          server_multiplier=server, pue=pue, facility_kwh=facility_kwh,
                          grid_kgco2e_per_kwh=US_KGCO2E_KWH,
                          operational_kgco2e=facility_kwh * US_KGCO2E_KWH,
                          hdc_sensitivity_kgco2=facility_kwh * HDC_KGCO2_KWH,
                          mix_lifecycle_factor_low=low_factor,
                          mix_lifecycle_factor_median=median_factor,
                          mix_lifecycle_factor_high=high_factor,
                          mix_lifecycle_kgco2e_low=facility_kwh * low_factor,
                          mix_lifecycle_kgco2e_median=facility_kwh * median_factor,
                          mix_lifecycle_kgco2e_high=facility_kwh * high_factor,
                          **{f"grid_share_{s}": shares[s] for s in SHARES}))
write("monte_carlo_draws.csv", draw_fields, draws)

METRICS = [
    ("delegated_hours", "h/engineer-day"),
    ("paid_fte_equivalent_attempted", "fraction_of_8h_paid_day"),
    ("attempted_tasks", "tasks/engineer-day"),
    ("input_tokens", "tokens/engineer-day"),
    ("output_tokens", "tokens/engineer-day"),
    ("total_tokens", "tokens/engineer-day"),
    ("gpu_seconds", "GPU-s/engineer-day"),
    ("board_kwh", "kWh/engineer-day"),
    ("facility_kwh", "kWh/engineer-day"),
    ("grid_kgco2e_per_kwh", "kgCO2e/kWh"),
    ("operational_kgco2e", "kgCO2e/engineer-day"),
    ("hdc_sensitivity_kgco2", "kgCO2/engineer-day"),
    ("mix_lifecycle_factor_low", "kgCO2e/kWh"),
    ("mix_lifecycle_factor_median", "kgCO2e/kWh"),
    ("mix_lifecycle_factor_high", "kgCO2e/kWh"),
    ("mix_lifecycle_kgco2e_low", "kgCO2e/engineer-day"),
    ("mix_lifecycle_kgco2e_median", "kgCO2e/engineer-day"),
    ("mix_lifecycle_kgco2e_high", "kgCO2e/engineer-day"),
]
summary = []
by_case: dict[str, list[dict]] = defaultdict(list)
for d in draws:
    by_case[d["case"]].append(d)
for case, *_ in CASES:
    for metric, unit in METRICS:
        values = [d[metric] for d in by_case[case]]
        summary.append(dict(case=case, metric=metric, unit=unit,
                            p10=f"{quantile(values,.1):.9g}",
                            p50=f"{quantile(values,.5):.9g}",
                            p90=f"{quantile(values,.9):.9g}",
                            status="conditional_proxy"))
write("case_summary.csv", ["case", "metric", "unit", "p10", "p50", "p90", "status"], summary)

case_meta = [dict(case=c, delegated_share=q, tracked_hours_per_day=h,
                  token_source=t, gpu=g, concurrency=n, grid="US_eGRID2023",
                  mix_model=f"Guidi403_EIArenew_IPCC_LCA_Dirichlet_kappa{GRID_SHARE_CONCENTRATION:g}",
                  token_energy_match="unvalidated_open_model_proxy")
             for c, q, h, t, g, n in CASES]
write("case_design.csv", ["case", "delegated_share", "tracked_hours_per_day",
                          "token_source", "gpu", "concurrency", "grid", "mix_model",
                          "token_energy_match"], case_meta)

print(f"Wrote {len(draws):,} draws across {len(CASES)} cases to {OUT}")
