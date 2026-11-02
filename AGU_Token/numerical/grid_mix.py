"""U.S. hyperscale data-center electricity mix and IPCC lifecycle sensitivity.

Shares are attributional electricity weights, not physically sampled generators
for individual requests. Source-factor low/median/high are literature envelopes,
not probability quantiles. Dirichlet concentration is a transparent analyst
sensitivity for *mix* uncertainty; no empirical share-error distribution exists.
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path


BASE = Path(__file__).resolve().parent
GRID_SHARE_CONCENTRATION = 100.0  # analyst sensitivity, not a fitted posterior
GUIDI_URL = "https://arxiv.org/html/2606.05420v1"
EIA_URL = "https://www.eia.gov/electricity/annual/table.php?t=epa_03_01_b.html"


def read(name: str) -> list[dict[str, str]]:
    with (BASE / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


guidi = {r["source_category"]: float(r["value"]) / 100
         for r in read("stage6_datacenter_supply_evidence.csv")
         if r["source_id"] == "Guidi_2026" and r["metric"] == "attributed_electricity_share"
         and r["source_category"] in ("natural_gas", "coal", "nuclear", "renewables")}
assert set(guidi) == {"natural_gas", "coal", "nuclear", "renewables"}
residual = 1 - sum(guidi.values())
assert math.isclose(residual, .004, abs_tol=1e-10)

renewable_mwh_by_year: dict[int, dict[str, float]] = {}
for row in read("stage6_renewable_split_eia_2024_2025.csv"):
    renewable_mwh_by_year.setdefault(int(row["year"]), {})[row["source"]] = float(row["utility_scale_thousand_mwh"])
assert set(renewable_mwh_by_year) == {2024, 2025}
for year, values in renewable_mwh_by_year.items():
    assert set(values) == {"wind", "solar", "hydropower", "biomass", "geothermal"}
    assert math.isclose(sum(values.values()), {2024: 976_463, 2025: 1_064_102}[year], abs_tol=1)


def shares_for_year(renewable_year: int = 2024) -> dict[str, float]:
    """Use a national utility-scale year only to split Guidi's renewable share."""
    renewable_mwh = renewable_mwh_by_year[renewable_year]
    renewable_total = sum(renewable_mwh.values())
    shares = {"natural_gas": guidi["natural_gas"],
              "coal": guidi["coal"],
              "nuclear": guidi["nuclear"],
              "other_fossil": residual}
    shares.update({source: guidi["renewables"] * generation / renewable_total
                   for source, generation in renewable_mwh.items()})
    return shares


SHARES = shares_for_year(2024)
assert math.isclose(sum(SHARES.values()), 1., abs_tol=1e-12)

factor_rows = {r["source"]: r for r in read("stage7_carbon_factors.csv")}
FACTORS = {}
for source in SHARES:
    proxy = "natural_gas" if source == "other_fossil" else source
    r = factor_rows[proxy]
    assert r["boundary"] == "lifecycle"
    FACTORS[source] = tuple(float(r[f"{k}_kgco2e_per_kwh"])
                            for k in ("low", "median", "high"))


def factor(shares: dict[str, float], column: int = 1) -> float:
    return sum(shares[source] * FACTORS[source][column] for source in SHARES)


def sample_shares(rng: random.Random, concentration: float = GRID_SHARE_CONCENTRATION,
                  renewable_year: int = 2024) -> dict[str, float]:
    """One correlated 9-component vector; renewable internal split stays fixed."""
    assert concentration > 0
    coarse = {"natural_gas": guidi["natural_gas"], "coal": guidi["coal"],
              "nuclear": guidi["nuclear"], "renewables": guidi["renewables"],
              "other_fossil": residual}
    draws = {source: rng.gammavariate(concentration * share, 1.)
             for source, share in coarse.items()}
    normalizer = sum(draws.values())
    weights = {source: value / normalizer for source, value in draws.items()}
    shares = {source: weights[source] for source in
              ("natural_gas", "coal", "nuclear", "other_fossil")}
    renewable_mwh = renewable_mwh_by_year[renewable_year]
    renewable_total = sum(renewable_mwh.values())
    shares.update({source: weights["renewables"] * generation / renewable_total
                   for source, generation in renewable_mwh.items()})
    return shares


def write_source_table(path: Path) -> None:
    fields = ["source", "central_share", "share_percent", "factor_low_kgco2e_per_kwh",
              "factor_median_kgco2e_per_kwh", "factor_high_kgco2e_per_kwh",
              "factor_boundary", "share_evidence", "factor_reference_url", "qualification"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for source, share in SHARES.items():
            low, median, high = FACTORS[source]
            qualification = ("Rounded Guidi residual; natural-gas factor is a proxy"
                             if source == "other_fossil" else
                             "EIA 2024 national utility-scale renewable split is a proxy for unknown HDC split"
                             if source in renewable_mwh_by_year[2024] else
                             "Guidi 403-HDC attributed generation share")
            writer.writerow(dict(source=source, central_share=f"{share:.12g}",
                                 share_percent=f"{share*100:.9g}",
                                 factor_low_kgco2e_per_kwh=low,
                                 factor_median_kgco2e_per_kwh=median,
                                 factor_high_kgco2e_per_kwh=high,
                                 factor_boundary="IPCC_AR5_lifecycle",
                                 share_evidence=f"{GUIDI_URL} | {EIA_URL}" if source in renewable_mwh_by_year[2024] else GUIDI_URL,
                                 factor_reference_url=factor_rows["natural_gas" if source == "other_fossil" else source]["reference_url"],
                                 qualification=qualification))
