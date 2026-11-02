"""Source-aware high-load sensitivity figure for the AGU poster draft."""
from __future__ import annotations

import csv
import html
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "poster_figures"
OUT.mkdir(exist_ok=True)
with (BASE / "model_outputs/high_load_summary.csv").open(newline="", encoding="utf-8") as stream:
    ROWS = {(r["case"], r["metric"]): r for r in csv.DictReader(stream)}


def e(text: str) -> str:
    return html.escape(str(text))


def text(x: float, y: float, value: str, size=19, color="#17324d", weight=400,
         anchor="start") -> str:
    return (f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}">{e(value)}</text>')


def box(x, y, w, h, fill, radius=13, stroke="none") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="900" viewBox="0 0 1500 900">',
       box(0, 0, 1500, 900, "#f7fafc", 0),
       text(70, 72, "High-load reassessment | coding agents", 36, "#0b2d46", 700),
       text(70, 108, "Different denominators must stay separate", 20, "#426178")]

cards = [
    ("Human distinct tasks", "4.8 / 4 h", "11-person field observation", "#e4eef8"),
    ("Task switches", "13.3 / h", "Repeated visits included", "#e4eef8"),
    ("Copilot user turn", "227.6K", "Median prompt; P90 1.50M", "#e7f2ef"),
    ("Gateway session", "1.4M", "Median total tokens", "#e7f2ef"),
    ("Gateway active day", "8.6M", "Median; P90 87M", "#fff1df"),
]
for i, (label, value, note, fill) in enumerate(cards):
    x = 70 + i * 277
    svg += [box(x, 140, 261, 140, fill), text(x + 15, 174, label, 17, "#33546a", 700),
            text(x + 15, 221, value, 36, "#0b2d46", 700),
            text(x + 15, 253, note, 14, "#426178")]

svg += [text(70, 325, "Seven-stage stress case: 40 candidate micro-interactions × 50% delegated", 25, "#0b2d46", 700),
        text(70, 353, "Assumption: each delegated interaction triggers one full gateway session; not an observed task-to-session mapping", 16, "#6b4d20")]

mix_case = "micro40_q50_session"
mix_factor = float(ROWS[(mix_case, "mix_lifecycle_factor_median")]["p50"])
mix_carbon = float(ROWS[(mix_case, "mix_lifecycle_kgco2e_median")]["p50"])
epa_carbon = float(ROWS[(mix_case, "benchmark_kgco2e")]["p50"])
mix_tokens = float(ROWS[(mix_case, "total_tokens")]["p50"])
mix_electricity = float(ROWS[(mix_case, "benchmark_facility_kwh")]["p50"])
stages = [
    ("1  Work", "40 candidate", "micro-interactions/day"),
    ("2  Delegation", "20 median", "agent sessions/day"),
    ("3  Tokens", f"{mix_tokens/1e6:.1f}M", "median raw tokens/day"),
    ("4  GPU", "H100 c1", "30B MoE benchmark"),
    ("5  Electricity", f"{mix_electricity:.2f} kWh", "facility-equivalent/day"),
    ("6  DC mix", f"{mix_factor:.3f}", "LCA kg CO₂e/kWh"),
    ("7  Carbon", f"{mix_carbon:.2f} kg", "LCA CO₂e/day"),
]
for i, (label, value, note) in enumerate(stages):
    x = 70 + i * 199
    fill = ["#e1edfa", "#e1edfa", "#dcf0e6", "#eee7fb", "#fff0d7", "#fff0d7", "#fbe4dd"][i]
    svg += [box(x, 390, 185, 145, fill), text(x + 12, 420, label, 17, "#35566a", 700),
            text(x + 12, 466, value, 26, "#0b2d46", 700),
            text(x + 12, 500, note, 12.7, "#426178")]
    if i < 6:
        svg.append(text(x + 190, 467, "›", 28, "#7c96a8", 700, "middle"))

svg += [text(70, 584, "Daily raw-token ranges", 24, "#0b2d46", 700),
        text(1370, 584, "P10 ━ P50 ━ P90", 17, "#426178", 400, "end")]
bar_cases = [
    ("20 Copilot user turns (assumed/day)", "turn20_copilot", "#449883"),
    ("Gateway active account-day median (observed)", "gateway_active_day_median", "#ba8c40"),
    ("20 micro-interactions × 30% → sessions", "micro20_q30_session", "#427eae"),
    ("40 micro-interactions × 50% → sessions", "micro40_q50_session", "#427eae"),
    ("60 micro-interactions × 70% → sessions", "micro60_q70_session", "#427eae"),
    ("Gateway active account-day P90 (observed)", "gateway_active_day_p90", "#ba8c40"),
]
plot_x0, plot_x1 = 540, 1270
def xpos(tokens):
    return plot_x0 + (math.log10(max(tokens, 1_000_000)) - 6) / 2 * (plot_x1 - plot_x0)

for j, (label, case, color) in enumerate(bar_cases):
    y = 615 + j * 34
    r = ROWS[(case, "total_tokens")]
    lo, mid, hi = (float(r[k]) for k in ("p10", "p50", "p90"))
    svg += [text(70, y + 6, label, 15, "#29485c"),
            f'<line x1="{xpos(lo):.1f}" y1="{y}" x2="{xpos(hi):.1f}" y2="{y}" stroke="{color}" stroke-width="8" stroke-linecap="round"/>',
            f'<circle cx="{xpos(mid):.1f}" cy="{y}" r="7" fill="#ffffff" stroke="{color}" stroke-width="4"/>',
            text(1380, y + 6, f"{mid/1e6:.1f}M", 16, "#29485c", 700, "end")]
for tick in [1, 3, 10, 30, 100]:
    x = xpos(tick * 1_000_000)
    svg += [f'<line x1="{x:.1f}" y1="807" x2="{x:.1f}" y2="816" stroke="#829aaa"/>',
            text(x, 836, f"{tick}M", 14, "#557082", anchor="middle")]
svg += [text(70, 874, f"Life-cycle mix uses Guidi/EIA/IPCC proxies; EPA operational comparison = {epa_carbon:.2f} kg CO₂e/day. H100/30B energy remains a proxy.", 15, "#6b4d20"),
        '</svg>']
path = OUT / "high_load_reassessment.svg"
path.write_text("\n".join(svg), encoding="utf-8")
try:
    import fitz
    document = fitz.open(path)
    document[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(path.with_suffix(".png"))
    print("Wrote SVG and PNG")
except ImportError:
    print("Wrote SVG; install PyMuPDF for PNG")
