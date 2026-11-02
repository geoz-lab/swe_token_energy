"""Sensitivity to the assumed concentration of grid-source share draws."""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

from grid_mix import factor, sample_shares, shares_for_year

OUT = Path(__file__).resolve().parent / "model_outputs/grid_mix_kappa_sensitivity.csv"
N_DRAWS = 10_000


def quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    x = (len(ordered)-1) * p
    a, b = math.floor(x), math.ceil(x)
    return ordered[a] + (ordered[b]-ordered[a]) * (x-a)


rows = []
for renewable_year in (2024, 2025):
    for kappa in (20., 100., 500.):
        # Same coarse-source draws in both years isolate the renewable-proxy change.
        rng = random.Random(20261102 + int(kappa))
        factors = [[], [], []]
        for _ in range(N_DRAWS):
            shares = sample_shares(rng, kappa, renewable_year)
            for j in (0, 1, 2):
                factors[j].append(factor(shares, j))
        for j, name in enumerate(("IPCC_low", "IPCC_median", "IPCC_high")):
            values = factors[j]
            rows.append(dict(renewable_proxy_year=renewable_year, kappa=kappa,
                             factor_scenario=name, n_draws=N_DRAWS,
                             central_share_factor_kgco2e_per_kwh=f"{factor(shares_for_year(renewable_year), j):.9g}",
                             p10_kgco2e_per_kwh=f"{quantile(values,.1):.9g}",
                             p50_kgco2e_per_kwh=f"{quantile(values,.5):.9g}",
                             p90_kgco2e_per_kwh=f"{quantile(values,.9):.9g}",
                             interpretation="2024 is main; 2025 is temporal proxy sensitivity; Dirichlet kappa is analyst assumption; IPCC factor bounds are not probabilistic"))
with OUT.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} grid-factor sensitivity rows to {OUT}")
