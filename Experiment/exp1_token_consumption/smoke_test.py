#!/usr/bin/env python3
"""
smoke_test.py — verify we can RECORD per-call token usage (and cost) for all three providers.

Sends one tiny single-turn request to each model and captures input / cached / output tokens,
then prices it via estimate_cost.cost_from_usage. This is NOT the agentic experiment — it only
proves the token-recording plumbing + key access work before we build the full runner.

    python smoke_test.py            # frontier trio (Opus 4.8 / GPT-5.3-Codex / Gemini 3.1 Pro)
    python smoke_test.py --cheap    # cheap models (Haiku / GPT-4.1 / Gemini 2.5 Flash) — pennies
    python smoke_test.py --anthropic-model claude-sonnet-4-6   # override any provider

Uses the native SDKs (anthropic / openai / google-generativeai). Each provider is independent:
one failing (no access, wrong id) does not stop the others.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from estimate_cost import cost_from_usage, PRICING  # noqa: E402

PROMPT = ("You are a coding assistant. Write a Python function `is_palindrome(s)` that returns "
          "True if the string is a palindrome ignoring case and non-alphanumerics. Code only.")

FRONTIER = {"anthropic": "claude-opus-4-8", "openai": "gpt-5.4", "google": "gemini-3.1-pro-preview"}
CHEAP = {"anthropic": "claude-haiku-4-5", "openai": "gpt-4o", "google": "gemini-2.5-flash"}


def load_env():
    env = HERE.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ── Per-provider calls → return (input_uncached, cached, output) ──────────────
def call_anthropic(model, max_tokens):
    import anthropic
    r = anthropic.Anthropic().messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": PROMPT}],
    )
    u = r.usage
    cached = getattr(u, "cache_read_input_tokens", 0) or 0
    return u.input_tokens, cached, u.output_tokens  # input_tokens already excludes cached


def call_openai(model, max_tokens):
    from openai import OpenAI
    client = OpenAI()
    try:  # chat API (gpt-5.4 / gpt-5.5 / gpt-4o all accept max_completion_tokens)
        r = client.chat.completions.create(model=model, max_completion_tokens=max_tokens,
                                           messages=[{"role": "user", "content": PROMPT}])
        u = r.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        return u.prompt_tokens - cached, cached, u.completion_tokens  # prompt_tokens includes cached
    except Exception as e:
        if "not a chat model" not in str(e):
            raise
        # codex models (gpt-5.1-codex-max/mini) are Responses-API only
        r = client.responses.create(model=model, input=PROMPT, max_output_tokens=max_tokens)
        u = r.usage
        cached = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        return u.input_tokens - cached, cached, u.output_tokens


def call_google(model, max_tokens):
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    r = genai.GenerativeModel(model).generate_content(
        PROMPT, generation_config={"max_output_tokens": max_tokens})
    u = r.usage_metadata
    cached = getattr(u, "cached_content_token_count", 0) or 0
    return u.prompt_token_count - cached, cached, u.candidates_token_count


CALLERS = {"anthropic": call_anthropic, "openai": call_openai, "google": call_google}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cheap", action="store_true", help="use cheap models instead of frontier")
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--anthropic-model")
    ap.add_argument("--openai-model")
    ap.add_argument("--google-model")
    args = ap.parse_args(argv)

    load_env()
    models = dict(CHEAP if args.cheap else FRONTIER)
    for prov, ov in (("anthropic", args.anthropic_model), ("openai", args.openai_model),
                     ("google", args.google_model)):
        if ov:
            models[prov] = ov

    print(f"\nToken-recording smoke test (max_tokens={args.max_tokens})\n")
    print(f"  {'provider':<10} {'model':<22} {'in':>7} {'cache':>6} {'out':>6} {'cost $':>9}  status")
    print("  " + "-" * 74)

    rows = []
    for prov, model in models.items():
        keyvar = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
                  "google": "GOOGLE_API_KEY"}[prov]
        if not os.environ.get(keyvar):
            print(f"  {prov:<10} {model:<22} {'—':>7} {'—':>6} {'—':>6} {'—':>9}  NO KEY ({keyvar})")
            continue
        t0 = time.time()
        try:
            inp, cached, out = CALLERS[prov](model, args.max_tokens)
            cost = cost_from_usage(model, inp, out, cached) if model in PRICING else float("nan")
            dt = time.time() - t0
            print(f"  {prov:<10} {model:<22} {inp:>7} {cached:>6} {out:>6} {cost:>9.5f}  OK ({dt:.1f}s)")
            rows.append({"provider": prov, "model": model, "input_uncached": inp,
                         "cached_input": cached, "output": out, "cost_usd": cost,
                         "seconds": round(dt, 2)})
        except Exception as e:
            msg = str(e).splitlines()[0][:60]
            print(f"  {prov:<10} {model:<22} {'—':>7} {'—':>6} {'—':>6} {'—':>9}  ERROR: {msg}")
            rows.append({"provider": prov, "model": model, "error": str(e)[:300]})

    out_dir = HERE.parent / "exp1_results"
    out_dir.mkdir(exist_ok=True)
    out_csv = out_dir / "smoke_test.csv"
    if rows:
        fields = sorted({k for r in rows for k in r})
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    ok = sum(1 for r in rows if "error" not in r and "cost_usd" in r)
    print(f"\n  {ok}/{len(models)} providers recorded tokens → {out_csv}\n")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
