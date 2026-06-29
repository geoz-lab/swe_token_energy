#!/usr/bin/env python3
"""
estimate_cost.py — dry-run budget projector + post-hoc cost accounting for Experiment 1.

Two jobs:

  1. A-priori projection (CLI): given per-task token assumptions and a task count, project
     the API cost per model and per provider account, and flag anything over its budget cap.
     Run this BEFORE spending real money.

         python estimate_cost.py                      # default 90-task matrix, "mid" scenario
         python estimate_cost.py --tasks 90 --scenario high
         python estimate_cost.py --models claude-sonnet-4-6 gpt-4.1 gemini-2.5-pro

  2. Post-hoc exact cost (importable): the agent runner calls `cost_from_usage(...)` with the
     real token counts the API reports, to track spend against the per-account kill-switch.

Pricing notes:
  * Anthropic rates verified via the claude-api skill (cached 2026-05-26): per 1M tokens.
  * OpenAI / Google rates are APPROXIMATE (from project notes + public rate cards) — confirm
    against the live pricing pages before the real run; update PRICING below.
  * Agentic loops re-send the growing transcript every turn, so most INPUT tokens are served
    from cache at ~0.1x. The projector models this via `cache_read_fraction`; OUTPUT tokens
    are never cached.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

# ── Pricing: USD per 1,000,000 tokens ────────────────────────────────────────
# cached_input = price for prompt tokens served from cache (prefix re-reads).
PRICING: dict[str, dict[str, float]] = {
    # ── Frontier coding models (default matrix), June 2026 ────────────────────
    # Anthropic — Opus 4.8 is the coding flagship (Fable 5 exists at $10/$50 but is
    # temporarily export-control suspended). Rates per claude-api skill (2026-05-26).
    "claude-opus-4-8":   {"input": 5.00,  "output": 25.00, "cached_input": 0.50},
    # OpenAI — accessible & confirmed working 2026-06-23 (gpt-5.3-codex / gpt-5-codex NOT on this account).
    "gpt-5.4":             {"input": 2.50, "output": 15.00, "cached_input": 0.25},   # balanced, chat API (default)
    "gpt-5.1-codex-max":   {"input": 1.25, "output": 10.00, "cached_input": 0.125},  # dedicated agentic coder (Responses API)
    "gpt-5.5-2026-04-23":  {"input": 5.00, "output": 30.00, "cached_input": 0.50},   # general flagship (priciest)
    # Google — Gemini 3.1 Pro. NOTE: prompts >200K tokens jump to $4 in / $18 out.
    # cached_input approximate; confirm before real run.
    "gemini-3.1-pro-preview":    {"input": 2.00,  "output": 12.00, "cached_input": 0.20},
    # ── Cheaper fallbacks / older models (for pilot or budget trims) ──────────
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00, "cached_input": 0.30},
    "claude-haiku-4-5":  {"input": 1.00,  "output": 5.00,  "cached_input": 0.10},
    "gpt-4.1":           {"input": 2.00,  "output": 8.00,  "cached_input": 0.50},
    "gpt-4o":            {"input": 2.50,  "output": 10.00, "cached_input": 1.25},  # fallback if no gpt-5 access
    "gemini-2.5-flash":  {"input": 0.30,  "output": 2.50,  "cached_input": 0.075},
    "gemini-2.5-pro":    {"input": 1.25,  "output": 10.00, "cached_input": 0.31},
}

# ── Which provider account pays for each model ───────────────────────────────
MODEL_PROVIDER: dict[str, str] = {
    "claude-opus-4-8": "anthropic", "claude-sonnet-4-6": "anthropic",
    "claude-haiku-4-5": "anthropic",
    "gpt-5.4": "openai", "gpt-5.1-codex-max": "openai", "gpt-5.5-2026-04-23": "openai",
    "gpt-4.1": "openai", "gpt-4o": "openai",
    "gemini-3.1-pro-preview": "google", "gemini-2.5-pro": "google", "gemini-2.5-flash": "google",
}

# ── Per-account budget caps (also the runner's --max-budget-usd kill-switch) ──
ACCOUNT_BUDGET_USD: dict[str, float] = {
    "anthropic": 350.0,   # Opus 4.8 — most expensive per task
    "openai":    200.0,   # GPT-5.3-Codex
    "google":    200.0,   # Gemini 3.1 Pro
}  # ~$750 total: full 90-task frontier matrix at the mid scenario, with headroom

# ── Runner safety defaults (single source of truth, imported by the agent runner) ─
STEP_CAP = 50                       # max agent turns per task
PER_TASK_TOKEN_CEILING = 3_000_000  # abort a task if cumulative tokens exceed this

# Default "most-advanced coding model per provider" matrix (June 2026).
DEFAULT_MODELS = ["claude-opus-4-8", "gpt-5.4", "gemini-3.1-pro-preview"]
DEFAULT_TASKS = 90  # SWE-bench Lite 30 + Verified 40 + SWE-Lancer 20

# ── Per-task token scenarios (input-dominated agentic runs) ──────────────────
@dataclass(frozen=True)
class Scenario:
    raw_input: int   # cumulative prompt tokens summed across all turns
    output: int      # cumulative completion tokens

SCENARIOS: dict[str, Scenario] = {
    "low":  Scenario(raw_input=300_000,   output=40_000),
    "mid":  Scenario(raw_input=800_000,   output=100_000),
    "high": Scenario(raw_input=2_000_000, output=200_000),
}


def task_cost(model: str, raw_input: int, output: int, cache_read_fraction: float) -> float:
    """Projected USD for one task under the given token assumptions.

    Uncached input is charged at the full input rate (a slight under-estimate vs the ~1.25x
    cache-WRITE premium on genuinely new content — treat projections as a floor, not a ceiling).
    """
    p = PRICING[model]
    cached_in = raw_input * cache_read_fraction
    fresh_in = raw_input * (1.0 - cache_read_fraction)
    cost = (
        cached_in * p["cached_input"]
        + fresh_in * p["input"]
        + output * p["output"]
    ) / 1_000_000.0
    return cost


def cost_from_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Exact USD from REAL usage the API reported. Used post-hoc by the runner.

    `input_tokens` is the uncached (full-price) remainder; `cached_input_tokens` is what was
    served from cache. This matches Anthropic's usage fields
    (input_tokens vs cache_read_input_tokens) and OpenAI/Gemini cached-token reporting.
    """
    if model not in PRICING:
        raise KeyError(f"No pricing for {model!r}; add it to PRICING.")
    p = PRICING[model]
    return (
        input_tokens * p["input"]
        + cached_input_tokens * p["cached_input"]
        + output_tokens * p["output"]
    ) / 1_000_000.0


def _project(models: list[str], tasks: int, scenario: Scenario, cache_read_fraction: float):
    print(f"\nProjection — {tasks} tasks/model, scenario "
          f"(input={scenario.raw_input:,}  output={scenario.output:,} per task), "
          f"cache_read_fraction={cache_read_fraction:.0%}\n")
    print(f"  {'model':<20} {'provider':<10} {'$/task':>8} {'$/'+str(tasks)+' tasks':>14}")
    print("  " + "-" * 56)

    per_account: dict[str, float] = {}
    for model in models:
        if model not in PRICING:
            print(f"  {model:<20} {'?':<10} {'(no pricing — add to PRICING)':>24}")
            continue
        per_task = task_cost(model, scenario.raw_input, scenario.output, cache_read_fraction)
        total = per_task * tasks
        provider = MODEL_PROVIDER.get(model, "?")
        per_account[provider] = per_account.get(provider, 0.0) + total
        print(f"  {model:<20} {provider:<10} {per_task:>8.2f} {total:>14.2f}")

    print("\n  Per-account total vs budget cap:")
    print(f"  {'account':<12} {'projected':>10} {'cap':>8} {'status':>10}")
    print("  " + "-" * 44)
    over = False
    for account, cap in ACCOUNT_BUDGET_USD.items():
        spent = per_account.get(account, 0.0)
        status = "OK" if spent <= cap else "OVER"
        if spent > cap:
            over = True
        print(f"  {account:<12} {spent:>10.2f} {cap:>8.0f} {status:>10}")
    print()
    return over


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                    help=f"models to project (default: {DEFAULT_MODELS})")
    ap.add_argument("--tasks", type=int, default=DEFAULT_TASKS,
                    help=f"tasks per model (default: {DEFAULT_TASKS})")
    ap.add_argument("--scenario", choices=list(SCENARIOS), default="mid",
                    help="per-task token scenario (default: mid)")
    ap.add_argument("--cache-fraction", type=float, default=0.80,
                    help="fraction of input tokens served from cache (default: 0.80)")
    ap.add_argument("--input-per-task", type=int, default=None,
                    help="override scenario raw input tokens/task")
    ap.add_argument("--output-per-task", type=int, default=None,
                    help="override scenario output tokens/task")
    args = ap.parse_args(argv)

    base = SCENARIOS[args.scenario]
    scenario = Scenario(
        raw_input=args.input_per_task if args.input_per_task is not None else base.raw_input,
        output=args.output_per_task if args.output_per_task is not None else base.output,
    )
    over = _project(args.models, args.tasks, scenario, args.cache_fraction)
    if over:
        print("  ⚠️  At least one account exceeds its cap — trim sample size, switch to a "
              "cheaper model, or raise the cap before the real run.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
