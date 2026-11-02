# Current poster figure set

These are AGU 2026 review figures. SVG is editable; PNG is a preview. Generate them after the Monte Carlo runs with `python3 AGU_Token/numerical/make_poster_figures.py` and `python3 AGU_Token/numerical/make_high_load_figure.py`. Read the [model equations and boundaries](../README.md) and [high-load reassessment](../HIGH_LOAD_REASSESSMENT_2026-11-01.md) before using numbers on a poster.

| Stage | Figure | Quantitative content |
|---|---|---|
| 1 | [Work](step_01_work_share.png) | Attempted FTE/day: 0.50 median; 0.40–0.60 conditional P10–P90 |
| 2 | [Agent sessions](step_02_tasks.png) | 20 sessions/day; 16–24 P10–P90; **sessions are not completed tasks** |
| 3 | [Tokens](step_03_tokens.png) | 35.1 million tokens/day; 25.3–46.9 million P10–P90 |
| 4 | [GPU time](step_04_gpu.png) | 5.94 H100 benchmark GPU-hours/day; 4.28–7.93 P10–P90 |
| 5 | [Electricity](step_05_electricity.png) | 3.25 facility kWh/day; 2.29–4.44 P10–P90 |
| 6 | [U.S. grid factor](step_06_grid.png) | 0.325 kg CO2e/kWh life-cycle factor; 0.286–0.363 P10–P90 |
| 7 | [Emissions](step_07_emissions.png) | 1.05 kg CO2e/day electricity life-cycle emissions; 0.72–1.46 P10–P90 |
| All seven | [Combined card strip](seven_stage_cards_row.png) | Compact preview sized to sit below the fan on the poster; the seven individual SVG/PNG cards remain separate assets |
| 1–7 | [Seven-stage fan](seven_stage_fan.png), [editable PowerPoint](seven_stage_fan_editable.pptx) | High-load branch: attempted FTE/day → agent sessions → tokens → H100 benchmark GPU time → facility electricity → U.S. source-mix factor → life-cycle electricity CO₂e/day; three FTE targets at 40 work units/day and separate work-density sensitivity |
| 1–7 schematic | [Preview](stage_schematic_numeric_preview.png), [editable PowerPoint](stage_schematic_numeric_editable.pptx) | Reference-style system boundary → four numeric stages → final outputs, reconstructed as native PowerPoint text and shapes |
| 1–7, high-load sensitivity | [Production-denominator comparison](high_load_reassessment.png) | Human tasks versus agent turns, sessions, and account-days; high-load case with the new life-cycle mix and separate EPA comparison |

The fan's three overlaid ribbons use the **high-load reassessment**. Each stage has its own hue; light, medium, and dark shades mark 0.30/0.50/0.70 attempted FTE/day. At each stage, ribbon boundaries use that scenario's **marginal P10/P90 log deviations from its median**. Twenty thin paths per scenario show selected, internally correlated Monte Carlo draws. The paths are normalized within each stage and placed on a widening **schematic** layout; vertical distances are **not comparable across stages**, because units and display gains differ, and the outline is not a joint probability band. The compact stage cards use the same `A=40` high-load cases, with `q=0.50` as the large headline, `q=0.30/0.50/0.70` scenario medians below, and a conditional P10–P90 for the central case. Equal-human-effort candidate work units partition a normalized eight-hour engineer-day. One delegated unit is assumed to start one full agent session; that is a deliberately high-load mapping, not an observed task-to-session rate. Stage 6 samples a **correlated source-share vector** with IPCC median life-cycle factors. All figures describe agent **attempts** and benchmark-equivalent energy; accepted task success, actual provider serving energy, idle fleet energy, and marginal grid effects remain unmeasured. Detailed evidence is in the stage CSV ledgers and the [numerical README](../README.md).

The seven narrow 440 × 560 SVG cards also have high-resolution PNG versions for inserting separately. The [current AGU poster](../../AGU26_Token_GeoZhang.pptx) and its [PNG preview](../../AGU26_Token_GeoZhang.png) are the primary presentation files.

The [numeric schematic PowerPoint](stage_schematic_numeric_editable.pptx) is a one-slide reconstruction with editable native text, shapes, lines, and custom paths. It contains no embedded raster image. It uses a custom 25 × 15.73 inch page. The full AGU poster includes embedded figure assets as well as native editable text and shapes.
