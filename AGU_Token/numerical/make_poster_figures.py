"""Render seven compact high-load stage cards and a seven-stage poster fan.

SVG is the editable original. PNG is rasterized by PyMuPDF when available.
Run after run_high_load_sensitivity.py.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from xml.sax.saxutils import escape

from grid_mix import SHARES, factor as grid_factor, shares_for_year

BASE = Path(__file__).resolve().parent
OUT = BASE / "poster_figures"
OUT.mkdir(exist_ok=True)

INK = "#172f3b"
SUB = "#536b77"
GRID = "#d7e3e7"
PALE = "#f3f8f8"
TEAL = "#087d83"
TEAL2 = "#68b6b4"
AMBER = "#d18433"
RED = "#b65955"
BLUE = "#3873a3"
VIOLET = "#765a9e"
WHITE = "#ffffff"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


SUMMARY = {(r["case"], r["metric"]): r for r in read(BASE / "model_outputs/case_summary.csv")}
HIGH_SUMMARY = {(r["case"], r["metric"]): r for r in read(BASE / "model_outputs/high_load_summary.csv")}


def q(case: str, metric: str, p: str = "p50") -> float:
    return float(SUMMARY[(case, metric)][p])


def hq(case: str, metric: str, p: str = "p50") -> float:
    return float(HIGH_SUMMARY[(case, metric)][p])


class Figure:
    def __init__(self, width: int, height: int, title: str):
        self.w, self.h = width, height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
                      f'<title>{escape(title)}</title>',
                      f'<rect width="{width}" height="{height}" fill="{WHITE}"/>']

    def rect(self, x, y, w, h, fill=WHITE, rx=0, stroke="none", sw=1):
        self.parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color=GRID, sw=1, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{sw}"{d}/>')

    def circle(self, x, y, r, fill):
        self.parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}"/>')

    def text(self, x, y, value, size=22, weight=400, color=INK, anchor="start"):
        self.parts.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}" dominant-baseline="middle">{escape(str(value))}</text>')

    def save(self, name: str, png_scale: float = 1.5):
        self.parts.append("</svg>")
        p = OUT / name
        p.write_text("\n".join(self.parts), encoding="utf-8")
        try:
            import fitz
            doc = fitz.open(p)
            doc[0].get_pixmap(matrix=fitz.Matrix(png_scale, png_scale), alpha=False).save(p.with_suffix(".png"))
        except ImportError:
            pass


def base(step: int, title: str, subtitle: str, source: str) -> Figure:
    f = Figure(1600, 900, title)
    f.rect(0, 0, 1600, 13, TEAL)
    f.circle(82, 74, 34, TEAL)
    f.text(82, 75, step, 27, 700, WHITE, "middle")
    f.text(135, 68, title, 37, 700)
    f.text(136, 116, subtitle, 19, 400, SUB)
    f.line(70, 158, 1530, 158, GRID, 2)
    f.line(70, 774, 1530, 774, GRID, 2)
    f.text(72, 822, source, 17, 400, SUB)
    return f


def bar(f: Figure, x: float, y: float, w: float, value: float, maximum: float,
        color=TEAL, h=22):
    f.rect(x, y, w, h, PALE, rx=h/2)
    f.rect(x, y, max(2, w * value / maximum), h, color, rx=h/2)


def stage1():
    f = base(1, "Work assigned to an agent", "Attempted work share is a scenario, not an observed FTE replacement rate", "Source: Kumar et al., Time Warp (n=484); 30/50/70% allocation scenarios. See REFERENCES.md.")
    f.text(72, 214, "Share of tracked task time", 24, 700)
    f.text(720, 214, "Agent-attempted hours / day", 21, 700)
    f.text(1235, 214, "Attempted paid-day share", 21, 700)
    for i, (label, case, share) in enumerate([
        ("Conservative", "survey30_gpt_h100", .3),
        ("Central", "survey50_gpt_h100", .5),
        ("Ambitious", "survey70_gpt_h100", .7),
    ]):
        y = 288 + 130*i
        f.text(75, y, label, 27, 700)
        bar(f, 330, y-13, 310, share, 1, AMBER, 26)
        f.text(662, y, f"{share:.0%}", 27, 700)
        f.text(762, y, f"{q(case,'delegated_hours'):.3f} h", 30, 700, TEAL)
        f.text(1300, y, f"{q(case,'paid_fte_equivalent_attempted'):.1%}", 30, 700)
    f.text(76, 618, "Observed activity shares of the reported workweek", 19, 700)
    x, y, total = 77, 646, 1435
    for share, color in ((.11, BLUE), (.09, TEAL), (.06, VIOLET), (.05, AMBER), (.69, PALE)):
        f.rect(x, y, total*share, 27, color)
        x += total*share
    f.text(78, 699, "11% feature coding   9% debugging   6% design   5% review   69% other activities", 18, color=SUB)
    f.text(78, 736, "Four tracked activities = 2.48 h of an assumed 8 h paid day; success and human review remain unmeasured.", 18, color=SUB)
    f.save("step_01_work_share.svg")


def stage2():
    f = base(2, "Work hours to attempted tasks", "Issue-scale task rates depend on both time allocation and human task duration", "Sources: Kumar et al., Time Warp; METR 2025 issue study. Duration ranges are analyst assumptions.")
    data = read(BASE / "stage2_duration_sensitivity.csv")
    f.text(74, 219, "Activity", 23, 700)
    f.text(566, 219, "Hours/day", 23, 700)
    f.text(883, 219, "Task duration (short / central / long)", 21, 700)
    f.text(1470, 219, "Baseline tasks/day", 20, 700, anchor="end")
    names = {"debugging":"Debugging", "coding_new_features":"Feature coding",
             "architecting_and_design":"Architecture/design", "PR_and_code_review":"PR/code review"}
    for i, r in enumerate(data):
        y = 296 + 103*i
        f.line(76, y+46, 1519, y+46, GRID)
        f.text(74, y, names[r["activity"]], 25, 700)
        v = float(r["assumed_hours_per_day"])
        bar(f, 432, y-10, 175, v, .9, TEAL, 20)
        f.text(635, y, f"{v:.2f}", 25, 700)
        f.text(881, y, f'{r["short_task_hours"]} / {r["central_task_hours"]} / {r["long_task_hours"]} h', 23)
        f.text(1470, y, f'{float(r["tasks_per_day_if_central"]):.3f}', 26, 700, anchor="end")
    baseline_rate = sum(float(r["tasks_per_day_if_central"]) for r in data)
    central_rate = baseline_rate * .5
    f.text(76, 701, f"At 50% delegated time: {baseline_rate:.3f} baseline × 0.5 = {central_rate:.3f} issue-scale tasks/day", 20, 700, TEAL)
    f.text(76, 740, "Monte Carlo with duration variation: "+
           f"{q('survey50_gpt_h100','attempted_tasks'):.3f} median " +
           f"[{q('survey50_gpt_h100','attempted_tasks','p10'):.3f}, {q('survey50_gpt_h100','attempted_tasks','p90'):.3f}] P10–P90; fractional rates include multiday work.", 18, color=SUB)
    f.save("step_02_tasks.svg")


def stage3():
    f = base(3, "Attempted tasks to model tokens", "Local task attempts and production telemetry have different denominators", "Sources: local mini-SWE-agent traces; Standard Compute 2026 telemetry; Bai et al. 2026.")
    data = read(BASE / "stage3_token_observations.csv")
    f.text(75, 209, "Median reconstructed total tokens per attempted task", 24, 700)
    x0, x1 = 540, 1200
    lo, hi = math.log10(10000), math.log10(2000000)
    xmap = lambda v: x0 + (math.log10(v)-lo)/(hi-lo)*(x1-x0)
    for tick in (10000, 100000, 1000000):
        x = xmap(tick)
        f.line(x, 256, x, 659, GRID)
        f.text(x, 681, f"{tick/1000:g}k" if tick<1e6 else "1M", 17, color=SUB, anchor="middle")
    models = [("gpt-5.4","GPT-5.4",BLUE),("claude-opus-4-8","Claude Opus 4.8",VIOLET),("gemini-3.1-pro-preview","Gemini 3.1 Pro",TEAL)]
    for i, bench in enumerate(("SWE-bench", "SWE-Lancer")):
        for j, (id_, label, color) in enumerate(models):
            r = next(z for z in data if z["benchmark"]==bench and z["model"]==id_)
            y = 283 + i*203 + j*64
            f.text(78, y, bench, 19, 700 if j==0 else 400, SUB)
            f.text(260, y, label, 20)
            v = float(r["median_raw_total_tokens"])
            f.rect(x0, y-11, xmap(v)-x0, 22, color, rx=5)
            f.text(min(xmap(v)+15, 1470), y, f"{v:,.0f}", 19, 700)
    f.rect(77, 704, 1445, 64, PALE, rx=5)
    f.text(92, 726, "External telemetry: 1.4M / median session · 8.6M / median active account-day · 87M / P90 account-day", 17, 700, TEAL)
    f.text(92, 750, "Local totals are reconstructed and ungraded; session and account-day totals are not tokens per accepted task.", 17, color=SUB)
    f.save("step_03_tokens.svg")


def stage4():
    f = base(4, "Tokens to measured GPU service", "Qwen3-Coder-30B-A3B, 8:1 input:output benchmark; model and workload matching matter", "Source: Experiment 2 A100/H100/H200 throughput, board power and latency; see experimental protocol.")
    data = read(BASE / "stage4_hardware_measured.csv")
    detail = read(BASE.parents[1] / "Experiment/final_results/exp2_supply_all_cells.csv")
    f.text(76, 213, "Board Wh per 1M benchmark tokens", 24, 700)
    f.text(76, 252, "(board W / total tokens per second) × 1M / 3600", 19, color=SUB)
    for i, gpu in enumerate(("A100", "H100", "H200")):
        y = 335 + i*120
        f.text(77, y+19, gpu, 27, 700)
        for j, (con, color, label) in enumerate(((1,BLUE,"single c1"),(64,TEAL,"saturated c64"))):
            r = next(z for z in data if z["gpu"]==gpu and int(z["concurrency"])==con)
            v = float(r["mean_board_w"])/float(r["total_tokens_per_second"])*1e6/3600
            yy = y+j*41
            f.text(240, yy, label, 18, color=SUB)
            bar(f, 460, yy-10, 690, v, 70, color, 20)
            f.text(1200, yy, f"{v:.1f} Wh", 22, 700)
    latencies = {int(r["concurrency"]): float(r["ttft_p50_ms"])/1000 for r in detail
                 if r["gpu"] == "H100" and r["model_name"] == "Qwen3-Coder-30B-A3B"
                 and int(r["concurrency"]) in (1, 64)}
    f.rect(73, 697, 1450, 66, PALE, rx=5)
    f.text(89, 719, f"H100 median first-token latency: c1 {latencies[1]:.3f} s; c64 {latencies[64]:.1f} s — service quality differs.", 18, 700, TEAL)
    f.text(89, 746, "30B total / 3B active MoE; B200, AMD and TPU specifications are not measured joules per token.", 18, color=SUB)
    f.save("step_04_gpu.svg")


def range_bar(f, case, metric, y, x0, x1, lo, hi, color=TEAL, scale=1):
    v10, v50, v90 = (q(case,metric,p)*scale for p in ("p10","p50","p90"))
    xp = lambda v: x0+(v-lo)/(hi-lo)*(x1-x0)
    f.line(xp(v10),y,xp(v90),y,color,12)
    f.circle(xp(v50),y,10,INK)
    f.text(1490,y,f"{v50:.2f}  [{v10:.2f}, {v90:.2f}]",21,700,anchor="end")


def stage5():
    f = base(5, "GPU electricity to facility electricity", "Board energy multiplied by server overhead and facility PUE", "Sources: local GPU benchmark; DOE/FEMP PUE; LBNL 2025 update estimates 2024 U.S. average PUE 1.45.")
    f.text(75, 210, "Local task-trace proxy: facility Wh per engineer-day", 24, 700)
    f.text(78, 261, "Scenario", 20, color=SUB)
    f.text(1340, 261, "Median [P10, P90] Wh", 20, color=SUB)
    for i,(label,case) in enumerate((('30%','survey30_gpt_h100'),('50%','survey50_gpt_h100'),('70%','survey70_gpt_h100'))):
        y = 346 + i*121
        f.text(82,y,label,29,700)
        range_bar(f,case,'facility_kwh',y,250,1010,0,6,TEAL,1000)
    f.rect(77, 670, 706, 86, PALE, rx=7)
    f.text(94, 695, "Efacility = (tokens / benchmark tok·s⁻¹)", 19, 700, TEAL)
    f.text(94, 728, "× board W / 3.6×10⁶ × host factor × PUE", 19, 700, TEAL)
    f.rect(808, 670, 710, 86, PALE, rx=7)
    f.text(825, 695, "Separate 40-microinteraction stress case:", 18, 700, BLUE)
    f.text(825, 728, f"{hq('micro40_q50_session','benchmark_facility_kwh'):.2f} kWh/day median (different task boundary)", 20, 700, BLUE)
    f.text(81, 637, "Host factor Tri(1.0, 1.2, 1.4); PUE Tri(1.2, 1.4, 1.6): assumptions, not site measurements.", 17, color=SUB)
    f.save("step_05_electricity.svg")


def stage6():
    f = base(6, "Electricity-source shares to grid factor", "One correlated source mix per scenario; source emission ranges remain separate sensitivity bounds", "Sources: Guidi et al. 2026 (403 HDCs); EIA 2024 main/2025 sensitivity; IPCC AR5 Table A.III.2.")
    rows = read(BASE / "stage6_grid_source_probabilities.csv")
    f.text(76, 212, "Source", 21,700)
    f.text(285, 212, "Share", 21,700)
    f.text(415, 203, "IPCC life-cycle (kg CO₂e/kWh)", 19,700)
    f.text(415, 230, "low / median / high", 17, color=SUB)
    names={"natural_gas":"Natural gas", "coal":"Coal", "nuclear":"Nuclear",
           "other_fossil":"Other fossil*", "wind":"Wind*", "solar":"Solar*",
           "hydropower":"Hydro*", "biomass":"Biomass*", "geothermal":"Geothermal*"}
    for i,r in enumerate(rows):
        y=265+i*48
        f.line(76,y+22,845,y+22,GRID)
        f.text(77,y,names[r["source"]],18,700 if i<4 else 400)
        f.text(285,y,f'{float(r["share_percent"]):.2f}%',18)
        lo=float(r["factor_low_kgco2e_per_kwh"])
        mid=float(r["factor_median_kgco2e_per_kwh"])
        hi=float(r["factor_high_kgco2e_per_kwh"])
        f.text(422,y,f"{lo:.3f} / {mid:.3f} / {hi:.3f}",18)
    f.line(875,197,875,708,GRID,2)
    f.text(908,215,"Weighted grid factor",25,700)
    center=grid_factor(SHARES, 1)
    p10=q('survey50_gpt_h100','mix_lifecycle_factor_median','p10')
    p90=q('survey50_gpt_h100','mix_lifecycle_factor_median','p90')
    f.text(910,277,f"{center:.3f} kg CO₂e/kWh",31,700,TEAL)
    f.text(910,319,f"Mix-only P10–P90 (κ=100): {p10:.3f}–{p90:.3f}",20)
    f.text(910,389,"IPCC source-factor envelope",21,700)
    f.text(910,433,f"Low factors: {grid_factor(SHARES, 0):.3f}",22)
    f.text(910,475,f"Median factors: {center:.3f}",22)
    f.text(910,517,f"High factors: {grid_factor(SHARES, 2):.3f}",22)
    f.line(907,557,1514,557,GRID)
    f.text(910,603,"EPA eGRID operational U.S.: 0.350",21,700,BLUE)
    f.text(910,644,"Guidi reported CO₂: 0.545 (unreconciled)",18,700,RED)
    f.text(910,687,"Different boundaries; do not combine.",18,color=SUB)
    alternative=grid_factor(shares_for_year(2025), 1)
    f.text(910,727,f"EIA 2025 proxy: median {alternative:.6f} ({alternative-center:+.6f})",16,color=SUB)
    f.text(78,735,"*Renewables: EIA proxy; other fossil: gas proxy; hydro high: reservoir extreme.",16,color=SUB)
    f.save("step_06_grid.svg")


def stage7():
    f = base(7, "Facility electricity to CO₂e", "Report life-cycle electricity supply and operational generation as separate outcomes", "Sources: Guidi/EIA/IPCC source-mix scenario; EPA eGRID2023 Revision 2 total-output factors.")
    erates={r["source"]:float(r["median_kgco2e_per_kwh"])
            for r in read(BASE / "stage7_carbon_factors.csv")
            if r["boundary"]=="operational generation"}
    f.text(78, 223, "Conditional daily scenario", 21, 700)
    f.text(597, 223, "Facility electricity", 20, 700)
    f.text(924, 223, "Supply life cycle", 20, 700, TEAL)
    f.text(1275, 223, "EPA operational", 20, 700, BLUE)
    f.text(924, 251, "IPCC median source factors", 16, color=SUB)
    f.text(1275, 251, "U.S. annual total output", 16, color=SUB)

    cases = [
        ("Local task trace, 50%", f"{q('survey50_gpt_h100','facility_kwh')*1000:.2f} Wh",
         f"{q('survey50_gpt_h100','mix_lifecycle_kgco2e_median')*1000:.3f} g",
         f"{q('survey50_gpt_h100','operational_kgco2e')*1000:.3f} g"),
        ("One session per task", f"{q('survey50_session_h100','facility_kwh')*1000:.1f} Wh",
         f"{q('survey50_session_h100','mix_lifecycle_kgco2e_median')*1000:.2f} g",
         f"{q('survey50_session_h100','operational_kgco2e')*1000:.2f} g"),
        ("20 sessions/day stress", f"{hq('micro40_q50_session','benchmark_facility_kwh'):.2f} kWh",
         f"{hq('micro40_q50_session','mix_lifecycle_kgco2e_median'):.2f} kg",
         f"{hq('micro40_q50_session','benchmark_kgco2e'):.2f} kg"),
    ]
    for i,(label,energy,lifecycle,operational) in enumerate(cases):
        y=327+i*105
        f.line(77,y+51,1517,y+51,GRID)
        f.text(79,y,label,23,700 if i==2 else 400)
        f.text(597,y,energy,25,700)
        f.text(924,y,lifecycle,26,700,TEAL)
        f.text(1275,y,operational,26,700,BLUE)
    f.text(80, 615, "Local 50% case, life-cycle P10–P90: "+
           f"{q('survey50_gpt_h100','mix_lifecycle_kgco2e_median','p10')*1000:.3f}–"+
           f"{q('survey50_gpt_h100','mix_lifecycle_kgco2e_median','p90')*1000:.3f} g/day; stress rows use different task boundaries.", 17, color=SUB)

    f.rect(77, 656, 705, 99, PALE, rx=7)
    f.text(94, 681, "Grid factors (kg CO₂e/kWh)", 18, 700)
    f.text(94, 711, f"Life cycle {grid_factor(SHARES,1):.3f}   ·   EPA U.S. {erates['US_eGRID']:.3f}", 20, 700)
    f.text(94, 738, "Different accounting boundaries; do not add.", 16, color=SUB)
    f.rect(807, 656, 710, 99, PALE, rx=7)
    f.text(824, 681, "Location-based operational factors", 18, 700)
    f.text(824, 711, f"CAMX {erates['CAMX_eGRID']:.3f}   ·   ERCT {erates['ERCT_eGRID']:.3f}", 20, 700)
    f.text(824, 738, "Use the facility's EPA subregion when known.", 16, color=SUB)
    f.save("step_07_emissions.svg")


def fan():
    f = Figure(2400, 1510, "Seven-stage high-load FTE-to-carbon scenario fan")
    f.rect(0, 0, 2400, 12, TEAL)
    f.text(70, 65, "Seven-stage fan · high-load scenarios", 43, 700)
    f.text(72, 112, "One engineer-day · 40 equal-effort candidate work units · three attempted FTE allocations carried through the same seven-stage model", 21, color=SUB)
    f.text(72, 155, "Within each stage:", 18, 700, INK)
    for x, label, color in [(286, "light · 0.30 FTE/day", "#92b5c6"), (634, "medium · 0.50 FTE/day", "#447f91"), (1037, "dark · 0.70 FTE/day", "#245065")]:
        f.line(x, 155, x+42, 155, color, 7)
        f.text(x+54, 155, label, 18, 700, INK)
    f.text(1700, 155, "Thin paths: sampled Monte Carlo days", 17, color=SUB)

    names = ["1  Work", "2  Agent sessions", "3  Tokens", "4  GPU time", "5  Facility energy", "6  Grid factor", "7  Emissions"]
    units = ["attempted FTE/day", "sessions/day", "M tokens/day", "GPU-h/day", "kWh/day", "kg CO₂e/kWh", "kg CO₂e/day"]
    metrics = ["attempted_fte_day", "modeled_agent_units", "total_tokens", "benchmark_gpu_seconds", "benchmark_facility_kwh", "mix_lifecycle_factor_median", "mix_lifecycle_kgco2e_median"]
    scales = [1, 1, 1e-6, 1/3600, 1, 1, 1]
    formats = [".2f", ".0f", ".1f", ".2f", ".2f", ".3f", ".2f"]
    xs = [170 + i*345 for i in range(7)]
    stage_colors = ["#3979ad", "#248c99", "#638e48", "#8065a5", "#c48335", "#5b7484", "#c05b58"]
    cases = ["micro40_q30_session", "micro40_q50_session", "micro40_q70_session"]

    def shade(hex_color: str, fraction: float) -> str:
        rgb = [int(hex_color[j:j+2], 16) for j in (1, 3, 5)]
        endpoint = 255 if fraction >= 0 else 0
        return "#" + "".join(f"{round(value*(1-abs(fraction))+endpoint*abs(fraction)):02x}" for value in rgb)

    tone = [.37, 0, -.18]
    fills = [.70, .82, .91]
    bounds = [xs[0]] + [(xs[i]+xs[i+1])/2 for i in range(6)] + [xs[-1]]
    for i, (x, name, unit, color) in enumerate(zip(xs, names, units, stage_colors)):
        f.rect(bounds[i], 301, bounds[i+1]-bounds[i], 540, shade(color, .955))
        f.rect(x-151, 193, 302, 86, WHITE, rx=9, stroke=GRID, sw=2)
        f.rect(x-151, 193, 302, 9, color, rx=5)
        f.text(x, 223, name, 23, 700, INK, "middle")
        f.text(x, 258, unit, 17, color=SUB, anchor="middle")
        f.line(x, 301, x, 841, shade(color, .72), 1, "5,7")

    # Median placement is schematic because stage units differ. Within each
    # stage, quantile offsets and thin sample paths come from actual draws.
    offsets = [38, 63, 94, 113, 142, 110, 188]
    gains = [70 + 80*i/6 for i in range(7)]
    medians = [[hq(case, metric) for metric in metrics] for case in cases]
    centers = [[565 + sign*offset for offset in offsets] for sign in (1, 0, -1)]
    upper = [[centers[j][i] - gains[i]*math.log(hq(case, metric, "p90")/medians[j][i])
              for i, metric in enumerate(metrics)] for j, case in enumerate(cases)]
    lower = [[centers[j][i] + gains[i]*math.log(medians[j][i]/hq(case, metric, "p10"))
              for i, metric in enumerate(metrics)] for j, case in enumerate(cases)]

    def at(values: list[float], i: int, side: str) -> float:
        if side == "left":
            return values[i] if i == 0 else (values[i-1]+values[i])/2
        return values[i] if i == 6 else (values[i]+values[i+1])/2

    for i, color in enumerate(stage_colors):
        left, right = bounds[i], bounds[i+1]
        for j in range(3):
            top, bottom = upper[j], lower[j]
            polygon = f"{left:.1f},{at(top,i,'left'):.1f} {xs[i]:.1f},{top[i]:.1f} {right:.1f},{at(top,i,'right'):.1f} "
            polygon += f"{right:.1f},{at(bottom,i,'right'):.1f} {xs[i]:.1f},{bottom[i]:.1f} {left:.1f},{at(bottom,i,'left'):.1f}"
            f.parts.append(f'<polygon points="{polygon}" fill="{shade(color,fills[j])}" opacity="0.86" stroke="none"/>')

    selected = {113 + 433*k for k in range(20)}
    sample_rows = {case: [] for case in cases}
    with (BASE / "model_outputs/high_load_draws.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["case"] in sample_rows and int(row["draw"]) in selected:
                sample_rows[row["case"]].append(row)
    assert all(len(rows) == len(selected) for rows in sample_rows.values())
    f.parts.append('<defs><clipPath id="fan-area"><rect x="19" y="301" width="2355" height="540"/></clipPath></defs>')
    f.parts.append('<g clip-path="url(#fan-area)">')
    for j, case in enumerate(cases):
        for row in sample_rows[case]:
            ys = [centers[j][i] - gains[i]*math.log(max(float(row[metric]), 1e-12)/medians[j][i])
                  for i, metric in enumerate(metrics)]
            for i, color in enumerate(stage_colors):
                left, right = bounds[i], bounds[i+1]
                coords = f"M {left:.1f} {at(ys,i,'left'):.1f} L {xs[i]:.1f} {ys[i]:.1f} L {right:.1f} {at(ys,i,'right'):.1f}"
                f.parts.append(f'<path d="{coords}" fill="none" stroke="{shade(color,tone[j])}" stroke-width="1.7" opacity="0.18"/>')
    f.parts.append('</g>')
    for j in range(3):
        for i, color in enumerate(stage_colors):
            left, right = bounds[i], bounds[i+1]
            ys = centers[j]
            coords = f"M {left:.1f} {at(ys,i,'left'):.1f} L {xs[i]:.1f} {ys[i]:.1f} L {right:.1f} {at(ys,i,'right'):.1f}"
            f.parts.append(f'<path d="{coords}" fill="none" stroke="{shade(color,tone[j])}" stroke-width="5" stroke-linejoin="round"/>')
            f.circle(xs[i], ys[i], 8, shade(color,tone[j]))

    for stage, (x, name, metric, unit, scale, fmt) in enumerate(zip(xs, names, metrics, units, scales, formats)):
        color = stage_colors[stage]
        f.rect(x-148, 859, 296, 279, WHITE, rx=9, stroke=GRID, sw=2)
        f.rect(x-148, 859, 296, 9, color, rx=5)
        f.text(x, 888, "MEDIAN BY SCENARIO", 16, 700, SUB, "middle")
        for y, case, label, case_tone in [
            (935, "micro40_q30_session", "0.30", tone[0]),
            (976, "micro40_q50_session", "0.50", tone[1]),
            (1017, "micro40_q70_session", "0.70", tone[2]),
        ]:
            row_color = shade(color, case_tone)
            f.circle(x-114, y, 6, row_color)
            f.text(x-100, y, label, 17, 700, row_color)
            f.text(x+120, y, format(hq(case, metric)*scale, fmt), 21, 700, row_color, "end")
        f.line(x-123, 1047, x+123, 1047, GRID, 1)
        lo = format(hq("micro40_q50_session", metric, "p10")*scale, fmt)
        hi = format(hq("micro40_q50_session", metric, "p90")*scale, fmt)
        f.text(x, 1075, "0.50 P10–P90", 15, 700, SUB, "middle")
        f.text(x, 1107, f"{lo}–{hi}", 18, 700, INK, "middle")

    f.rect(27, 1157, 2346, 105, PALE, rx=10)
    f.text(52, 1185, "WORK-DENSITY SENSITIVITY · target 0.50 attempted FTE/day", 18, 700, TEAL)
    for i, density in enumerate((20, 40, 60)):
        case = f"micro{density}_q50_session"
        x = 75 + i*772
        f.text(x, 1229, f"{density} units/day → {hq(case,'modeled_agent_units'):.0f} sessions → {hq(case,'total_tokens')/1e6:.1f}M tokens → {hq(case,'benchmark_facility_kwh'):.2f} kWh → {hq(case,'mix_lifecycle_kgco2e_median'):.2f} kg", 18, 700)

    f.text(53, 1292, "Model: N ~ Binomial(A,q); attempted FTE/day = N/A; total tokens = sum of N sessions (median 1.4M/session).", 18, color=INK)
    f.text(53, 1324, "H100 benchmark: 1,642 tokens/s, 326 W; facility kWh = GPU-s × W × host factor × PUE / 3.6M; CO₂e = kWh × U.S. source-mix factor.", 18, color=INK)
    f.text(53, 1358, "Stage ribbons follow marginal P10–P90; thin paths are sampled days. Their vertical placement is schematic because stage units differ.", 18, 700, RED)
    f.text(53, 1391, "Equal human effort and one session per delegated unit are assumptions. Attempted FTE is not verified net labor replacement.", 18, color=SUB)
    f.text(53, 1424, "Energy is a Qwen3-Coder-30B-A3B H100 proxy, not measured commercial-agent serving energy. IPCC median source factors; sampled U.S. mix.", 18, color=SUB)
    f.text(53, 1468, "Sources: Meyer et al. 2014; Standard Compute Agent Burn Index; local GPU tests; Guidi et al. 2026; EIA 2024; IPCC AR5. See REFERENCES.md.", 17, color=SUB)
    f.save("seven_stage_fan.svg")


def poster_stage_cards():
    """Seven narrow cards sized to sit below the fan in the AGU poster."""
    palette = ["#3979ad", "#248c99", "#638e48", "#8065a5", "#c48335", "#5b7484", "#c05b58"]
    specs = [
        ("Work", "attempted FTE/day", "attempted_fte_day", 1, ".2f", "N / 40; allocation assumption", "step_01_work_share.svg"),
        ("Agent sessions", "sessions/day", "modeled_agent_units", 1, ".0f", "N ~ Binomial(40, q)", "step_02_tasks.svg"),
        ("Tokens", "million tokens/day", "total_tokens", 1e-6, ".1f", "1.4M median per session", "step_03_tokens.svg"),
        ("GPU time", "H100 GPU-hours/day", "benchmark_gpu_seconds", 1/3600, ".2f", "tokens / 1,642 per second", "step_04_gpu.svg"),
        ("Electricity", "facility kWh/day", "benchmark_facility_kwh", 1, ".2f", "326 W board × host × PUE", "step_05_electricity.svg"),
        ("Grid factor", "kg CO2e/kWh (LCA)", "mix_lifecycle_factor_median", 1, ".3f", "U.S. mix × IPCC factors", "step_06_grid.svg"),
        ("Emissions", "kg CO2e/day (LCA)", "mix_lifecycle_kgco2e_median", 1, ".2f", "electricity × grid factor", "step_07_emissions.svg"),
    ]
    cases = ["micro40_q30_session", "micro40_q50_session", "micro40_q70_session"]

    def shade(hex_color: str, fraction: float) -> str:
        rgb = [int(hex_color[j:j+2], 16) for j in (1, 3, 5)]
        endpoint = 255 if fraction >= 0 else 0
        return "#" + "".join(f"{round(v*(1-abs(fraction))+endpoint*abs(fraction)):02x}" for v in rgb)

    cards = []
    for step, (title, unit, metric, scale, fmt, method, filename) in enumerate(specs, start=1):
        color = palette[step-1]
        f = Figure(440, 560, f"Stage {step}: {title}, high-load poster card")
        f.rect(1, 1, 438, 558, WHITE, rx=12, stroke=GRID, sw=2)
        f.rect(1, 1, 438, 13, color, rx=7)
        f.circle(48, 58, 27, color)
        f.text(48, 59, step, 29, 700, WHITE, "middle")
        f.text(91, 58, title, 33, 700)
        f.text(30, 113, "40 UNITS/DAY · q = 0.50", 25, 700, SUB)
        value = hq(cases[1], metric) * scale
        f.text(30, 199, format(value, fmt), 90, 700, color)
        f.text(33, 256, unit, 28, 700)
        f.line(29, 286, 411, 286, GRID, 2)
        f.text(30, 319, "P10–P90 AT q = 0.50", 23, 700, SUB)
        lo = format(hq(cases[1], metric, "p10")*scale, fmt)
        hi = format(hq(cases[1], metric, "p90")*scale, fmt)
        f.text(30, 366, f"{lo}–{hi}", 42, 700)
        f.line(29, 401, 411, 401, GRID, 2)
        for j, (x, case, label, tint) in enumerate(zip((79,220,361), cases, ("q = 0.30","q = 0.50","q = 0.70"), (.30,0,-.18))):
            row_color = shade(color, tint)
            f.text(x, 434, label, 21, 700, row_color, "middle")
            f.text(x, 479, format(hq(case, metric)*scale,fmt), 33, 700, row_color, "middle")
        f.rect(17, 514, 406, 36, shade(color, .93), rx=6)
        f.text(220, 533, method, 21, 700, SUB, "middle")
        f.save(filename, png_scale=3)
        cards.append(f)

    row = Figure(7*440, 560, "Seven high-load stage cards for the AGU poster")
    for index, card in enumerate(cards):
        row.parts.append(f'<g transform="translate({index*440},0)">')
        row.parts.extend(card.parts[2:-1])
        row.parts.append('</g>')
    row.save("seven_stage_cards_row.svg", png_scale=1.5)


fan()
poster_stage_cards()
print(f"Wrote fan, seven compact stage figures, and a seven-card row to {OUT}")
