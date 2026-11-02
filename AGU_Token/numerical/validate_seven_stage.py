"""Check arithmetic, units and source-table agreement in the saved MC output."""

import csv
import math
from collections import Counter
from pathlib import Path

from grid_mix import SHARES, factor as mix_factor, renewable_mwh_by_year, shares_for_year

BASE = Path(__file__).resolve().parent
OUT = BASE / "model_outputs"


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


design = {r["case"]: r for r in rows(OUT / "case_design.csv")}
draws = rows(OUT / "monte_carlo_draws.csv")
summary = rows(OUT / "case_summary.csv")
hardware = {(r["gpu"],int(r["concurrency"])):r for r in rows(BASE / "stage4_hardware_measured.csv")}
hdc = next(float(r["value"]) for r in rows(BASE / "stage6_datacenter_supply_evidence.csv")
           if r["source_id"] == "Guidi_2026" and r["metric"] == "electricity_weighted_carbon_intensity")
assert len(design) == 9 and len(draws) == 90_000
assert set(Counter(r["case"] for r in draws).values()) == {10_000}
assert all(float(r["p10"]) <= float(r["p50"]) <= float(r["p90"]) for r in summary)

for r in draws:
    d = design[r["case"]]
    get = lambda key: float(r[key])
    assert math.isclose(get("delegated_hours"), float(d["tracked_hours_per_day"]) * float(d["delegated_share"]), rel_tol=1e-12)
    assert math.isclose(get("paid_fte_equivalent_attempted"), get("delegated_hours")/8, rel_tol=1e-12)
    assert math.isclose(get("total_tokens"), get("input_tokens") + get("output_tokens"), rel_tol=1e-12)
    h=hardware[(d["gpu"],int(d["concurrency"]))]
    assert math.isclose(get("gpu_seconds"),get("total_tokens")/float(h["total_tokens_per_second"]),rel_tol=1e-12)
    assert math.isclose(get("board_kwh"), get("gpu_seconds")*float(h["mean_board_w"])/3_600_000, rel_tol=1e-12)
    assert math.isclose(get("facility_kwh"), get("board_kwh")*get("server_multiplier")*get("pue"), rel_tol=1e-12)
    assert math.isclose(get("operational_kgco2e"), get("facility_kwh")*get("grid_kgco2e_per_kwh"), rel_tol=1e-12)
    assert math.isclose(get("hdc_sensitivity_kgco2"), get("facility_kwh")*hdc, rel_tol=1e-12)
    shares = {s: get(f"grid_share_{s}") for s in SHARES}
    assert math.isclose(sum(shares.values()), 1., abs_tol=1e-12)
    for name, j in (("low",0),("median",1),("high",2)):
        assert math.isclose(get(f"mix_lifecycle_factor_{name}"), mix_factor(shares,j), rel_tol=1e-12)
        assert math.isclose(get(f"mix_lifecycle_kgco2e_{name}"),get("facility_kwh")*get(f"mix_lifecycle_factor_{name}"),rel_tol=1e-12)
    assert get("attempted_tasks") > 0 and get("total_tokens") > 0

print(f"Validated {len(draws):,} draws, {len(design)} cases, {len(summary)} summary rows")

high_draws = rows(OUT / "high_load_draws.csv")
high_summary = rows(OUT / "high_load_summary.csv")
assert len(high_draws) == 130_000
assert set(Counter(r["case"] for r in high_draws).values()) == {10_000}
assert all(float(r["p10"]) <= float(r["p50"]) <= float(r["p90"]) for r in high_summary)
for r in high_draws:
    get = lambda key: float(r[key])
    if r["unit"] == "session_per_delegated_microaction":
        assert math.isclose(get("attempted_fte_day"), get("modeled_agent_units") / get("candidate_interactions"), rel_tol=1e-12)
        assert math.isclose(get("assumed_human_hours_per_unit") * get("candidate_interactions"), 8, rel_tol=1e-12)
    h = hardware[(r["gpu"], 1)]
    assert math.isclose(get("benchmark_gpu_seconds"), get("total_tokens") / float(h["total_tokens_per_second"]), rel_tol=1e-12)
    assert math.isclose(get("benchmark_board_kwh"), get("benchmark_gpu_seconds") * float(h["mean_board_w"]) / 3_600_000, rel_tol=1e-12)
    assert math.isclose(get("benchmark_facility_kwh"), get("benchmark_board_kwh") * get("host_to_board_factor") * get("pue"), rel_tol=1e-12)
    assert math.isclose(get("benchmark_kgco2e"), get("benchmark_facility_kwh") * get("us_grid_kgco2e_per_kwh"), rel_tol=1e-12)
    shares = {s: get(f"grid_share_{s}") for s in SHARES}
    assert math.isclose(sum(shares.values()), 1., abs_tol=1e-12)
    for name, j in (("low",0),("median",1),("high",2)):
        assert math.isclose(get(f"mix_lifecycle_factor_{name}"), mix_factor(shares,j), rel_tol=1e-12)
        assert math.isclose(get(f"mix_lifecycle_kgco2e_{name}"),get("benchmark_facility_kwh")*get(f"mix_lifecycle_factor_{name}"),rel_tol=1e-12)
    assert get("modeled_agent_units") >= 0 and get("total_tokens") >= 0
print(f"Validated {len(high_draws):,} high-load draws, {len(high_summary)} summary rows")

source_rows = rows(BASE / "stage6_grid_source_probabilities.csv")
assert len(source_rows) == len(SHARES)
assert math.isclose(sum(float(r["central_share"]) for r in source_rows), 1., abs_tol=1e-10)
for r in source_rows:
    assert math.isclose(float(r["central_share"]), SHARES[r["source"]], rel_tol=1e-10)
assert math.isclose(sum(renewable_mwh_by_year[2024].values()), 976_462)
assert math.isclose(sum(renewable_mwh_by_year[2025].values()), 1_064_103)
grid_sensitivity = rows(OUT / "grid_mix_kappa_sensitivity.csv")
assert len(grid_sensitivity) == 18
for r in grid_sensitivity:
    year = int(r["renewable_proxy_year"])
    j = {"IPCC_low": 0, "IPCC_median": 1, "IPCC_high": 2}[r["factor_scenario"]]
    assert math.isclose(float(r["central_share_factor_kgco2e_per_kwh"]),
                        mix_factor(shares_for_year(year), j), rel_tol=1e-8)
    assert float(r["p10_kgco2e_per_kwh"]) <= float(r["p50_kgco2e_per_kwh"]) <= float(r["p90_kgco2e_per_kwh"])
epa_rows = rows(BASE / "stage6_egrid_reconciliation.csv")
for r in epa_rows:
    assert math.isclose(float(r["source_value_lb_per_mwh"]) * .45359237 / 1000,
                        float(r["converted_kgco2e_per_kwh"]), rel_tol=1e-8)
print(f"Validated {len(source_rows)} grid-source weights, {len(grid_sensitivity)} grid sensitivities, and {len(epa_rows)} EPA unit conversions")
