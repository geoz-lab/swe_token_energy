#!/usr/bin/env python3
"""
parse_trajectory.py — turn mini-swe-agent .traj.json files into Experiment-1 token records.

mini-swe-agent (v2) stores only `info.model_stats.instance_cost` + `api_calls` — NOT token counts.
But it stores the full message list (roles: system/user/assistant/tool/exit). So we RECONSTRUCT the
agentic token demand from the messages and ANCHOR it to the exact recorded cost:

  • Replay turn-by-turn: each `assistant` message is one API call whose INPUT is every prior message
    (system + task + the growing assistant/tool history re-sent each turn = the real agentic demand),
    and whose OUTPUT is that assistant message.
  • Tokenize with tiktoken (falls back to ~chars/4 if unavailable).
  • §1.3 partition (mutually exclusive): split the timeline at the FIRST failed verification (first
    `tool` message with a non-zero <returncode>). Before it → T_input (system+task+assistant history
    re-sent), T_output (assistant gens), T_tool (tool/observation re-sent). After it → T_retry (all
    input+output of post-failure turns).
  • COST-ANCHOR: scale all four so reconstructed cost == recorded instance_cost. The tiktoken split is
    approximate (esp. for Claude/Gemini), but the totals are pinned to the real billed cost, and the
    printed cost-check shows how close the raw reconstruction was.

    python parse_trajectory.py --inspect one.traj.json                 # schema dump
    python parse_trajectory.py --runs-dir runs/opus --model claude-opus-4-8 [--results resolved.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from estimate_cost import PRICING  # noqa: E402

_RETURNCODE = re.compile(r"<returncode>\s*(-?\d+)\s*</returncode>")


def _encoder():
    # Cache the vocab in-repo so it works on compute nodes too: run the parser ONCE on the login
    # node (internet) to populate it, then offline reads succeed everywhere (shared filesystem).
    import os
    os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(HERE / ".tiktoken_cache"))
    try:
        import tiktoken
        return tiktoken.get_encoding("o200k_base")  # GPT-4o/5 vocab; approx for Claude/Gemini
    except Exception:
        return None


def _ntok(text: str, enc) -> int:
    if not text:
        return 0
    return len(enc.encode(text)) if enc else max(1, len(text) // 4)


def _text(m: dict) -> str:
    c = m.get("content")
    return c if isinstance(c, str) else json.dumps(c)


def _failed(text: str) -> bool:
    codes = _RETURNCODE.findall(text)
    if codes:
        return any(int(c) != 0 for c in codes)
    return any(k in text for k in ("Traceback (most recent call last)", "FAILED", "AssertionError"))


def inspect(path: Path):
    t = json.loads(path.read_text())
    print(f"top-level keys: {list(t)}")
    msgs = t.get("messages") or t.get("trajectory") or []
    print(f"#messages: {len(msgs)} | roles: {sorted({m.get('role') for m in msgs})}")
    print(f"model_stats: {t.get('info', {}).get('model_stats')}")


def parse_one(path: Path, model: str, enc) -> dict:
    t = json.loads(path.read_text())
    instance = path.stem.replace(".traj", "")
    msgs = t.get("messages") or t.get("trajectory") or []
    stats = t.get("info", {}).get("model_stats", {})
    cost = stats.get("instance_cost")
    api_calls = stats.get("api_calls", sum(1 for m in msgs if m.get("role") == "assistant"))

    roles = [m.get("role") for m in msgs]
    sizes = [_ntok(_text(m), enc) for m in msgs]

    # Additive partition (T_input + T_output + T_tool = total): at each assistant turn the WHOLE prior
    # context is re-sent as input; tool/observation messages are the T_tool share of that input, the
    # rest (system + task + assistant history) is T_input, and the assistant message itself is T_output.
    Ti = To = Ttool = 0
    est_in = est_out = 0
    for i, role in enumerate(roles):
        if role != "assistant":
            continue
        out_toks = sizes[i]
        in_tool = sum(sz for j, sz in enumerate(sizes[:i]) if roles[j] == "tool")
        in_ctx = sum(sz for j, sz in enumerate(sizes[:i]) if roles[j] != "tool")
        To += out_toks
        Ttool += in_tool
        Ti += in_ctx
        est_out += out_toks
        est_in += in_tool + in_ctx

    # Retry DIAGNOSTIC (not part of the additive total — retries overlap input/output). A SWE-bench
    # task's first failing test is normal bug-reproduction; a genuine retry is re-testing after a fix
    # still fails. Proxy: count failed test cycles; retry_frac = token share in turns after the 2nd
    # failure (i.e. excluding the initial reproduction).
    fail_idxs = [i for i, m in enumerate(msgs) if roles[i] == "tool" and _failed(_text(m))]
    n_failed = len(fail_idxs)
    retry_after = fail_idxs[1] if len(fail_idxs) >= 2 else None
    retry_tok = 0
    if retry_after is not None:
        for i, role in enumerate(roles):
            if role == "assistant" and i > retry_after:
                retry_tok += sum(sizes[:i]) + sizes[i]
    retry_frac = round(retry_tok / (est_in + est_out), 3) if (est_in + est_out) else 0.0

    # cost-anchor: scale so reconstructed cost == recorded instance_cost
    factor, est_cost = 1.0, None
    if model in PRICING and (est_in or est_out):
        p = PRICING[model]
        est_cost = (est_in * p["input"] + est_out * p["output"]) / 1_000_000
        if cost and est_cost > 0:
            factor = cost / est_cost          # billed cost known (SWE-bench) → anchor tokens to it
        elif not cost:
            cost = est_cost                    # no billed cost (SWE-Lancer driver) → tiktoken-derived estimate
    scale = lambda x: int(round(x * factor))

    return {
        "model": model, "instance_id": instance, "api_calls": api_calls,
        "T_input": scale(Ti), "T_output": scale(To), "T_tool": scale(Ttool),
        "total_tokens": scale(Ti + To + Ttool),
        "cost_usd": round(cost, 6) if cost is not None else "",
        "n_failed_tests": n_failed, "retry_frac": retry_frac,   # diagnostics (not additive)
        "raw_input_est": est_in, "raw_output_est": est_out,
        "raw_cost_est": round(est_cost, 6) if est_cost else "", "anchor_factor": round(factor, 3),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inspect", type=Path)
    ap.add_argument("--runs-dir", type=Path)
    ap.add_argument("--model")
    ap.add_argument("--results", type=Path, help="optional grading json (instance_id -> resolved)")
    ap.add_argument("--out", type=Path, default=HERE.parent / "exp1_results" / "exp1_raw.csv")
    args = ap.parse_args(argv)

    if args.inspect:
        inspect(args.inspect)
        return 0
    if not args.runs_dir or not args.model:
        ap.error("--runs-dir and --model are required (unless --inspect)")

    resolved = {}
    if args.results and args.results.exists():
        data = json.loads(args.results.read_text())
        resolved = data if isinstance(data, dict) else {d["instance_id"]: d.get("resolved") for d in data}

    enc = _encoder()
    if enc is None:
        print("NOTE: tiktoken unavailable — using ~chars/4 fallback (less accurate).", file=sys.stderr)

    rows = []
    for traj in sorted(args.runs_dir.rglob("*.traj.json")):
        r = parse_one(traj, args.model, enc)
        r["resolved"] = resolved.get(r["instance_id"], "")
        rows.append(r)
    if not rows:
        print(f"no .traj.json under {args.runs_dir}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(exist_ok=True)
    write_header = not args.out.exists()
    with open(args.out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        if write_header:
            w.writeheader()
        w.writerows(rows)

    tot = sum(r["total_tokens"] for r in rows)
    cst = sum(r["cost_usd"] for r in rows if isinstance(r["cost_usd"], (int, float)))
    print(f"  parsed {len(rows)} task(s) · {tot:,} tokens · ${cst:.4f} · appended to {args.out}")
    for r in rows:
        print(f"    {r['instance_id']:<28} calls={r['api_calls']:>3} "
              f"in={r['T_input']:>8} out={r['T_output']:>7} tool={r['T_tool']:>8} "
              f"total={r['total_tokens']:>8} ${r['cost_usd']} "
              f"(fails={r['n_failed_tests']} retry={r['retry_frac']} anchor×{r['anchor_factor']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
