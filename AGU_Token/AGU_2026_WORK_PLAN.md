# AGU 2026 Token to Carbon Poster Work Plan

> **Historical planning document.** The current poster and numerical README supersede several early targets below. In particular, the implemented high-load branch models *attempted* work allocation and electricity-supply life-cycle emissions; it does not estimate achieved FTE replacement. See [the current model](numerical/README.md).

## 1. Poster Objective

Build a bottom-up, uncertainty-aware accounting framework for estimating the operational carbon footprint of replacing a specified share of software-engineering work with AI agents.

The main visual will be a left-to-right uncertainty fan:

```text
Software work -> Task bundle -> Token demand -> Model serving -> Hardware -> Facility energy -> Carbon footprint
     FTE-day          a              b                c             d              e                  f
```

For a compact poster, `Software work` and `Task bundle` can share the first panel, and `Model serving` and `Hardware` can remain adjacent panels. The calculation must retain all seven stages even if the graphic shows only six labels.

The final result should answer:

> For a defined mix of software-engineering work, what operational electricity use and carbon emissions result when AI agents perform 0–100% of that work under alternative agent, model, hardware, and electricity-supply scenarios?

This is a scenario-accounting result, not a prediction that a given percentage of engineers will be replaced.

## 2. Core Design Principles

1. Use one `FTE-day` as the base functional unit before scaling to annual or workforce scenarios.
2. Translate FTE share into a task bundle before assigning tokens.
3. Treat task difficulty, agent mode, model choice, serving configuration, hardware, and electricity supply as separate variables.
4. Separate measured values, fitted distributions, literature inputs, and illustrative assumptions.
5. Propagate joint uncertainty through the complete chain. Do not multiply unrelated high-end values to create an artificial worst case.
6. Report central estimates and uncertainty intervals at every stage so the widening fan has quantitative meaning.
7. Keep operational emissions separate from embodied hardware and data-center emissions. Add embodied emissions only as a clearly labeled extension.
8. Report attributional and consequential grid emissions separately because they answer different questions.

## 3. System Boundary and Units

### Primary boundary

- Software-engineering work performed during one working day.
- Agent inference, including prefill, decode, repeated context, reasoning tokens where observable, and tool-result context.
- Accelerator electricity and facility overhead through PUE.
- Operational grid emissions associated with data-center electricity.

### Initially excluded or reported separately

- Model training and fine-tuning.
- Embodied emissions of GPUs, servers, and buildings.
- Developer laptop energy.
- Network and storage energy unless a defensible source is available.
- Productivity changes caused by altered software quality or downstream maintenance.
- Economy-wide rebound or Jevons effects; these belong in a separate demand-growth scenario.

### Standard units

| Stage | Primary unit | Secondary unit |
|---|---|---|
| Software work | FTE-day and percent of FTE-day | FTE-year |
| Tasks | completed tasks per FTE-day | task-hours and success-adjusted tasks |
| Tokens | total processed tokens per task and FTE-day | input, cached input, output, reasoning, and tool-context tokens |
| Serving | tokens per second per accelerator | GPU-seconds or TPU-seconds per task |
| Hardware | watt-hours per task | joules per token |
| Facility energy | kWh per FTE-day | kWh per FTE-year |
| Carbon | kg CO2e per FTE-day | t CO2e per FTE-year or workforce scenario |

## 4. Calculation Framework

### Stage A: Software work to task bundle

Define a role-and-task matrix instead of one universal FTE.

Recommended role levels:

- Junior engineer.
- Mid-level engineer.
- Senior or staff engineer.

Recommended task families:

- Debugging and maintenance.
- Feature development.
- System design, architecture, and integration.
- Testing, review, documentation, and operational work if included in the boundary.

For role `r`, task family `k`, and difficulty band `h`:

```text
tasks(r,k,h) = FTE_share(r) x work_minutes_per_day x task_time_share(r,k,h)
               / median_human_minutes_per_task(r,k,h)
```

The AI-addressable task bundle is:

```text
AI_tasks(r,k,h) = tasks(r,k,h) x substitution_fraction(r,k,h)
```

The `substitution_fraction` varies from 0 to 100% but should be constrained by task suitability and agent success, not assumed to be identical across all work.

Required data:

- Working minutes per FTE-day.
- Task-family time allocation by seniority.
- Human time per task or tasks per day.
- Task-difficulty distribution.
- Fraction technically addressable by AI.
- Quality or success threshold defining a completed task.

Outputs:

- Task bundles for junior, mid-level, and senior roles.
- Easy, medium, and hard variants within each task family.
- A normalized `1 FTE-day` bundle and 0–100% substitution slider or scenario grid.

Validation gate:

- The task bundle must sum to the defined workday.
- Human task rates must be plausible when reconstructed from the matrix.
- The definition of “solved” must be consistent between human and agent work.

### Stage B: Task bundle to token demand

Token demand must vary by task and operating mode.

Recommended operating modes:

- Single-turn dialogue or code generation.
- Multi-turn assistant with human interaction.
- Autonomous agent with tools and repeated context.
- Long-context agent with repository-scale input.
- Router-assisted agent in which a decision model selects the model, tool, subagent, or reasoning policy at defined cache-safe boundaries.

For task type `i`, mode `m`, and model or agent system `s`:

```text
T_task(i,m,s) = T_uncached_input + T_cached_input + T_output
                + T_reasoning_if_reported
```

Tool output is not a separate model-generated category when it re-enters the prompt; record it as a component of subsequent input tokens to avoid double counting.

Daily demand is:

```text
T_FTE_day = sum over tasks [AI_tasks(i) x T_task(i,m,s) / agent_success_rate(i,m,s)]
```

The success adjustment must be handled carefully. If failed attempts already appear in measured trajectories, do not divide by success again. Instead, model retries and terminal failures explicitly.

Required data:

- Existing Experiment 1 trajectories and token summaries.
- The open-versus-commercial sanity check.
- Single-turn calibration data from the earlier exploration.
- New targeted runs only where the current task taxonomy lacks coverage.
- Context length, number of turns, tool calls, retry intensity, success, and task difficulty.
- Router calls, routing decisions, confidence, fallback behavior, cache events, and correction chains for routed runs.

Outputs:

- Token distributions by task family, difficulty, model, and operating mode.
- Nonlinear task-difficulty curve rather than one average token-per-task value.
- Input/output/cache composition.
- Daily token demand by role and substitution percentage.
- Net token change from routing and context optimization, including decision-model overhead and rework after misrouting.

Validation gate:

- Confirm additive token accounting.
- Check that agentic versus single-turn comparisons use the same task boundary.
- Separate observed token counts from token estimates reconstructed from cost or text.

### Stage C: Tokens to model-serving workload

This stage defines what computation the tokens require. The same number of tokens can have very different compute and energy implications depending on model architecture and serving configuration.

Scenario dimensions:

- Closed frontier systems accessed through APIs, used for token-demand and capability observations when hardware is undisclosed.
- Open-weight proxy models with known architecture and measured hardware behavior.
- Dense versus mixture-of-experts models.
- Total parameters and active parameters per token.
- Precision or quantization: BF16, FP8, INT8, INT4, or hardware-specific formats.
- Context length and prefill-to-decode ratio.
- Batch size, concurrency, latency target, and prefix caching.
- Agent scaffold, reasoning setting, tool policy, and retry policy.
- Runtime optimization policy: model routing, tool routing, subagent routing, reasoning-effort routing, context pruning, retrieval, summarization, and cache management.

Do not claim that a closed model runs on a specific GPU. Use open models to measure the serving relationship, then present proxy or bracketed scenarios for closed frontier systems.

#### Jev and agent-runtime routing

Jev is TypeSafe AI's decision-only System One model. It receives supplied state and bounded, typed questions, then returns choices, scores, or probabilities. It does not generate the code or prose that completes a software-engineering task. In this framework, Jev belongs beside the agent as a control-plane component that can select among allowed models, tools, subagents, or policies.

The study should compare at least four harness configurations on the same task set:

1. `Fixed baseline`: one generative model and one policy for the complete session.
2. `Jev session router`: choose a capability tier at session start, then keep the main conversation on that model.
3. `Jev cache-safe router`: route at session start, subagent launch, or bounded side-lane tasks without migrating the warm main conversation.
4. `Naive per-turn router`: switch models at arbitrary turns. Use this as a negative control because cache reconstruction may eliminate apparent savings.

Optional Jev decisions include:

- Select the cheapest model tier predicted to satisfy the task and quality threshold.
- Decide whether to launch a specialized subagent.
- Select a tool from an allowed set.
- Choose low, medium, or high reasoning effort.
- Decide whether a small bounded request should run in a compact side lane.
- Trigger escalation or human review when confidence is below a threshold.

Measure the complete system rather than only the router call:

```text
net_tokens = generative_input + generative_output + router_input + router_output
             + cache_rebuild_tokens + correction_or_retry_tokens

net_latency = router_latency + generative_latency + tool_latency + rework_latency

net_energy = generative_serving_energy + router_energy_or_reported_proxy
             + rework_energy
```

Because Jev is a hosted proprietary service, its accelerator energy may not be disclosed. Report its token, request, latency, and cost overhead directly, and treat router energy as `not observed` or a bounded proxy rather than silently assigning the generative model's energy intensity.

Routing success criteria must include task quality. A configuration is not more efficient if it reduces tokens by selecting a model that fails, requires escalation, or causes a longer correction chain.

#### Broader optimization scenarios

Jev is one example of a larger optimization layer. Test or model the following levers separately so their effects are not attributed to routing alone:

- Prompt and system-instruction compression.
- Selective retrieval instead of sending the full repository or transcript.
- Context pruning and structured project ledgers.
- Prefix caching and model-affine session persistence.
- Model and subagent capability routing.
- Reasoning-effort routing.
- Tool-result filtering and summarization.
- Early termination and loop detection.
- Continuous batching, speculative decoding, and scheduler optimization.
- Quantization and accelerator-specific kernels.

The first seven levers primarily affect token volume, cache behavior, or task success. Early termination affects both token demand and agent control. Batching, speculative decoding, quantization, and specialized kernels primarily affect serving throughput and energy per processed token. All combined configurations must be measured end to end.

Required outputs:

- A serving-profile table for each modeled system.
- Total processed tokens split into prefill and generated tokens.
- Representative saturated and latency-constrained operating points.
- A declared mapping between closed-agent demand measurements and open-model hardware measurements.
- An optimization matrix showing baseline, routed, cache-aware, context-reduced, and combined configurations.

Validation gate:

- Explain why each open model is an appropriate proxy or scenario.
- Ensure throughput and power come from the same workload window.
- Evaluate router accuracy, fallbacks, cache effects, and quality on held-out tasks before using routed results in the headline scenario.
- Keep Jev, the TypeSafe AI decision model, distinct from the unrelated Jevons-effect demand-growth extension.

### Stage D: Model serving to accelerator fleet

For hardware `g` and serving profile `q`:

```text
accelerator_seconds = prefill_tokens / prefill_throughput(g,q)
                      + output_tokens / decode_throughput(g,q)
```

If only total-token throughput is available, label that simplification and provide a sensitivity range.

Hardware scenarios should initially include measured systems:

- NVIDIA A100.
- NVIDIA H100.
- NVIDIA H200.

Possible extensions, subject to defensible measurements:

- NVIDIA B200 or B300.
- Google TPU.
- Other accelerators with comparable workload-level throughput and power data.

Required data:

- Accelerator compatibility and count per model.
- Tensor or expert parallelism.
- Measured throughput by workload and concurrency.
- Board power measured over the same interval.
- Utilization and idle allocation policy.
- Server-level overhead where available.

Outputs:

- Accelerator-seconds per task and per FTE-day.
- Concurrent accelerator count for a defined service demand and latency target.
- Hardware comparison table.

Validation gate:

- Normalize multi-accelerator runs correctly.
- Distinguish nameplate TDP from measured power.
- Avoid comparing throughput measured under incompatible context lengths or latency constraints.

### Stage E: Accelerator use to facility electricity

```text
accelerator_energy_kWh = sum [accelerator_seconds x measured_board_power_W] / 3,600,000

IT_energy_kWh = accelerator_energy_kWh + allocated_CPU_memory_network_energy

facility_energy_kWh = IT_energy_kWh x PUE
```

Use at least three accounting cases:

- Lower bound: measured accelerator board energy only.
- Central case: accelerator energy plus defensible server overhead and representative PUE.
- Upper case: conservative server overhead, PUE, and utilization allocation.

Outputs:

- Wh per task.
- kWh per FTE-day and FTE-year.
- Energy breakdown by accelerator, server overhead, and facility overhead.
- Sensitivity to utilization, latency target, caching, and PUE.

Validation gate:

- Confirm all power values are average watts over an identified measurement window.
- Do not multiply GPU TDP by wall-clock time when measured power is available.
- Ensure PUE is applied once and only once.

### Stage F: Facility electricity to carbon footprint

For location `l` and time interval `t`:

```text
CO2e = sum over l,t [facility_energy_kWh(l,t) x emission_factor_kgCO2e_per_kWh(l,t)]
```

Electricity scenarios:

- Location-based average grid mix.
- Market-based contractual supply where credible instruments exist.
- Consequential or marginal emissions for changes in load.
- Clean-energy-constrained scheduling and geographic shifting.

Power-source detail should include consistent life-cycle emission factors for coal, gas, nuclear, hydro, wind, solar, geothermal, biomass, and storage losses where relevant. The poster must not multiply a regional grid factor by a separate source mix if the grid factor already represents that mix.

Required data:

- Data-center location scenarios.
- Hourly or annual grid mix, depending on the resolution selected.
- Average and marginal emission factors.
- Life-cycle generation factors for the explanatory power-source comparison.
- Temporal matching assumptions for contracted clean power.

Outputs:

- kg CO2e per task, FTE-day, and FTE-year.
- Carbon comparison by location and electricity scenario.
- Attributional and consequential results displayed separately.
- Contribution analysis identifying which stage dominates uncertainty.

Validation gate:

- Keep combustion-only and life-cycle emission factors distinct.
- Match the geographic and temporal resolution of electricity and emissions data.
- Avoid claiming zero emissions for renewable or nuclear electricity when using life-cycle accounting.

## 5. Integrated Uncertainty Fan

Use Monte Carlo simulation or structured scenario sampling. Each draw should preserve dependencies:

1. Draw role and task mix.
2. Draw task difficulty and AI-addressable share.
3. Draw agent mode, token demand, retries, and success.
4. Draw model-serving profile and caching behavior.
5. Draw hardware, throughput, measured power, utilization, and PUE.
6. Draw location, time, and the appropriate grid-emission factor.
7. Calculate the complete chain for the same draw.

At each node, save P10, P50, and P90 values. These quantiles form the fan boundaries. Also save rank correlations or Sobol-style sensitivity measures so the poster can identify the dominant drivers.

The fan should not imply that uncertainty must widen monotonically. A stage can narrow uncertainty when new information constrains the scenario. Its geometry should follow calculated intervals rather than decorative expansion.

Recommended primary fan normalization:

```text
1 FTE-day at a selected role mix -> tasks/day -> million tokens/day
-> accelerator-hours/day -> kWh/day -> kg CO2e/day
```

A 0–100% replacement scenario can then scale the normalized unit while allowing the task mix to change with substitution level.

## 6. Data Architecture

Create one tidy table per transformation and preserve provenance.

### Table A: task taxonomy

Minimum fields:

```text
role_level, task_family, difficulty, human_minutes, daily_time_share,
addressable_fraction, completion_definition, source, evidence_type
```

### Table B: token observations

```text
task_id, task_family, difficulty, agent_system, model, operating_mode,
input_tokens, cached_input_tokens, output_tokens, reasoning_tokens,
turns, tool_calls, retries, success, wall_time, router_system,
router_calls, route_decision, route_confidence, fallback, cache_rebuild_tokens,
correction_tokens, source_run
```

### Table C: serving and hardware measurements

```text
model, architecture, total_params, active_params, precision, hardware,
accelerator_count, input_length, output_length, concurrency, cache_mode,
prefill_tok_s, decode_tok_s, total_tok_s, mean_power_W, utilization,
runtime_optimization, measurement_source
```

### Table D: electricity and carbon

```text
location, timestamp_or_period, accounting_method, power_source,
grid_share, emission_factor_kgCO2e_kWh, factor_boundary,
PUE, source, source_year
```

### Table E: scenario outputs

```text
scenario_id, FTE_share, role_mix, task_mix, agent_mode, model_profile,
hardware_profile, location, grid_method, tasks, tokens,
accelerator_hours, facility_kWh, kgCO2e
```

Every source value should have a source, year, geography, system boundary, and evidence label: `measured`, `fitted`, `literature`, or `assumed`.

## 7. Work Packages

### WP0: Lock the research question and boundary

Tasks:

- Confirm the primary functional unit.
- Decide whether the headline is per FTE-day, per completed task, or a workforce scenario. Recommendation: calculate all three but headline `per FTE-day`.
- Decide whether the main story is replacement, augmentation, or an addressable-work scenario. Recommendation: use `AI-performed share of work` in scientific text and reserve `replacement` for clearly labeled scenarios.
- Confirm operational-only versus operational-plus-embodied emissions.
- Resolve the meaning of `JEV`.

Deliverable: one-page scope memo and locked variable dictionary.

### WP1: Build the role-task-FTE model

Tasks:

- Create the task taxonomy and difficulty bands.
- Assemble human productivity evidence by seniority.
- Construct normalized junior, mid-level, and senior FTE-days.
- Define substitution curves from 0 to 100% by task type.

Deliverable: task taxonomy table, FTE calculator, and first-stage plot.

### WP2: Build the task-token model

Tasks:

- Map existing benchmark tasks to the poster taxonomy.
- Reanalyze existing Experiment 1 data by task family and difficulty.
- Integrate single-turn and agentic modes without conflating task boundaries.
- Identify missing cells and run only targeted additional experiments.
- Fit token-demand distributions and retry/success relationships.

Deliverable: token model, nonlinear difficulty plot, and mode comparison.

### WP3: Build the model-serving bridge

Tasks:

- Define serving profiles for dense and mixture-of-experts models.
- Separate prefill and decode where data permit.
- Quantify caching, context, concurrency, and latency effects.
- Document how open-model measurements bracket undisclosed closed-model serving.
- Implement a controlled Jev routing experiment with fixed, session-routed, cache-safe, and naive per-turn configurations.
- Measure router overhead, cache reconstruction, misroutes, correction chains, task quality, and end-to-end latency.
- Compare routing with context reduction, cache management, and reasoning-effort controls so savings are assigned to the correct mechanism.

Deliverable: serving-profile matrix, model-to-hardware mapping rules, and router/optimization ablation table.

### WP4: Complete hardware-energy comparisons

Tasks:

- Reuse and quality-check A100, H100, and H200 measurements.
- Add B200, B300, TPU, or other hardware only if workload-comparable data can be obtained.
- Calculate accelerator-seconds, Wh per task, and kWh per FTE-day.
- Add utilization, server overhead, and PUE scenarios.

Deliverable: hardware-energy table and accelerator comparison plot.

### WP5: Complete electricity-carbon accounting

Tasks:

- Inspect and reconcile the three existing externality spreadsheets.
- Choose data-center location scenarios.
- Select grid-mix and marginal-emissions datasets.
- Harmonize life-cycle power-source emission factors.
- Calculate attributional and consequential footprints separately.

Deliverable: carbon-factor table, power-source comparison, and location/time carbon scenarios.

### WP6: Integrate and quantify uncertainty

Tasks:

- Implement the full transformation chain.
- Preserve correlations and avoid independent extreme stacking.
- Generate P10/P50/P90 values at every stage.
- Run sensitivity and contribution-to-variance analysis.
- Create traceable scenario output tables.

Deliverable: reproducible scenario model and final fan dataset.

### WP7: Design the poster

Tasks:

- Convert the sketch into a vector fan graphic driven by model outputs.
- Build one evidence module below each stage.
- Use the older poster only as a size or layout reference, not as scientific content.
- Keep detailed methods in a QR-linked supplement if space is limited.

Deliverable: poster source, print PDF, screen PDF, and figure package.

### WP8: Scientific and visual QA

Tasks:

- Recalculate headline numbers independently.
- Verify units and system boundaries end to end.
- Trace every poster number to a source table.
- Review claims with collaborators.
- Print a reduced-size proof and inspect readability.
- Test the explanation with a two-minute and a five-minute walkthrough.

Deliverable: signed-off calculation audit and final poster.

## 8. Proposed Poster Structure

### Top band: research question and headline result

- One-sentence question.
- One central quantitative conclusion with uncertainty.
- One boundary statement: operational inference and grid emissions.

### Middle band: the uncertainty fan

Recommended labeled nodes:

```text
FTE-day and tasks | Tokens | Model serving | Hardware | Facility energy | Carbon
```

Each connection should show its conversion unit:

```text
tasks/day | tokens/task | accelerator-seconds/token | watts | PUE | kg CO2e/kWh
```

Show P10–P90 as the fan and P50 as the centerline. Use color to distinguish evidence categories or scenarios, not merely to decorate stages.

### Bottom band: six evidence modules

1. `FTE and tasks`: stacked task mix by seniority and substitution share.
2. `Tokens`: nonlinear token demand by difficulty and operating mode.
3. `Model serving`: Jev routing and other runtime optimizations, context, caching, dense/MoE, and prefill/decode effects.
4. `Hardware`: throughput, measured board power, and energy per token by accelerator.
5. `Facility energy`: accelerator, server, and PUE decomposition.
6. `Carbon`: grid mix, power-source factors, location/time cases, and attributional versus consequential results.

### Footer

- Methods summary.
- Limitations.
- Data and code QR link.
- Authors and affiliations.
- References limited to the most load-bearing sources.

## 9. Minimum Viable Poster and Extensions

### Minimum viable poster

- Junior/mid/senior role scenarios.
- Debugging, development, and system-design task families.
- Easy/medium/hard task bands.
- Single-turn versus agentic token modes.
- Fixed-agent versus Jev-routed and cache-aware agent modes.
- Existing A100/H100/H200 empirical measurements.
- Board-only, central PUE, and conservative facility-energy cases.
- Three contrasting grid-location scenarios.
- Average and marginal emissions shown separately.
- P10/P50/P90 fan and top sensitivity drivers.

### Extensions after the core model is stable

- B200/B300 and TPU measurements.
- Embodied hardware emissions.
- Hourly workload shifting.
- Rebound or Jevons-effect scenarios.
- Other occupations or agentic task domains.
- Quality-adjusted or success-adjusted functional units.

## 10. Six-Sprint Execution Sequence

### Sprint 1: Scope and inventory

- Lock the functional unit, task taxonomy, system boundary, and evidence labels.
- Map all existing files to the transformation stages.
- Inspect the externality spreadsheets and identify missing inputs.

### Sprint 2: FTE-task and token models

- Build task bundles by seniority.
- Reclassify existing token observations.
- Produce initial Stage A and B figures.

### Sprint 3: Serving and hardware

- Reconcile total-token versus generated-token throughput.
- Finalize measured A100/H100/H200 profiles.
- Run or specify the Jev routing and optimization ablations.
- Quantify cache-safe routing, decision overhead, misroutes, and correction chains.
- Decide whether newer accelerators can be included defensibly.

### Sprint 4: Energy and carbon

- Finalize overhead and PUE cases.
- Build average and marginal grid-emissions scenarios.
- Produce energy and carbon tables.

### Sprint 5: Integration and sensitivity

- Run the full uncertainty model.
- Generate the fan dataset, contribution analysis, and headline results.
- Complete an independent unit audit.

### Sprint 6: Poster production

- Build the vector fan and supporting modules.
- Review scientific language and citations.
- Render, print-test, revise, and freeze the final poster.

## 11. Immediate Next Decisions

Before calculation begins, confirm these choices:

1. Is the primary unit one FTE-day, one completed task, or a global workforce scenario?
2. Does `0–100%` mean share of work performed by AI, share of headcount replaced, or both as separate scenarios?
3. Which task families must be included beyond debugging, development, and system design?
4. Should agent failure and human review time be included in the functional unit?
5. Which Jev decisions should be in the first controlled experiment: model tier, tool, subagent, reasoning effort, or a limited subset?
6. Is the poster limited to operational carbon, or should embodied emissions be added?
7. Which geographic grid scenarios are most relevant to the intended AGU audience?

The recommended default is: `one FTE-day`, `share of work performed by AI`, three role levels, three core task families, explicit success and review adjustments, operational emissions as the primary boundary, embodied/rebound effects as extensions, and a Jev experiment limited initially to session-start model-tier routing plus cache-safe subagent routing.

