#!/usr/bin/env python3
"""
run_swelancer.py — run mini-swe-agent on sampled SWE-Lancer IC tasks via Apptainer.

SWE-Lancer tasks aren't SWE-bench instances, so `mini-extra swebench` can't load them. Each is a
self-contained single-container image (`docker://swelancer/swelancer_x86_<id>:releasev1`). We drive
mini-swe-agent's library directly: build a writable Apptainer sandbox from the image, run the agent
inside it (cwd `/app/expensify`) on the task's `instruction.md`, and save a `.traj.json` in the SAME
format as the SWE-bench runs so `parse_trajectory.py` works unchanged.

    # pilot ONE task first (validate the whole path on Sherlock):
    python run_swelancer.py --only 13066_1 --model anthropic/claude-opus-4-8 --out $SCRATCH/exp1/swelancer_pilot
    # then the full sampled set:
    python run_swelancer.py --model anthropic/claude-opus-4-8 --out $SCRATCH/exp1/swelancer_opus

Notes / validate-on-pilot:
  * Images are LARGE (multi-GB each); `apptainer build --sandbox` per task needs scratch space + time.
  * Set MSWEA_SINGULARITY_EXECUTABLE=apptainer (done below) and APPTAINER_CACHEDIR on $SCRATCH.
  * Token demand only — grading (in-container end-to-end tests) is a separate, heavier step (--grade stub).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = "https://huggingface.co/datasets/DCAgent2/swe-lancer/resolve/main"


def _fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def run_task(task: str, image: str, model_name: str, out_dir: Path,
             step_limit: int, cost_limit: float) -> tuple[float, int]:
    import yaml
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments.singularity import SingularityEnvironment
    from minisweagent.models import get_model

    # Use OUR swebench.yaml (agent + model sections) — its templates are built for a containerized
    # env and don't reference {{system}} (default.yaml does, which SingularityEnvironment can't supply).
    config = yaml.safe_load((HERE / "swebench.yaml").read_text())
    instruction = _fetch(f"{RAW}/{task}/instruction.md")
    env = SingularityEnvironment(image=image, cwd="/app/expensify")     # builds writable sandbox
    model = get_model(input_model_name=model_name, config=dict(config.get("model", {})))
    agent_cfg = dict(config.get("agent", {}))
    agent_cfg["step_limit"] = step_limit
    agent_cfg["cost_limit"] = cost_limit
    agent = DefaultAgent(model, env, **agent_cfg)

    try:
        agent.run(instruction)
    finally:
        msgs = agent.messages
        # cost: sum the per-call litellm cost carried on each assistant message; fall back to model.cost
        cost = sum(float(m.get("cost") or 0) for m in msgs)
        if not cost:
            cost = float(getattr(model, "cost", 0) or 0)
        calls = getattr(model, "n_calls", None) or sum(1 for m in msgs if m.get("role") == "assistant")
        traj = {
            "info": {"model_stats": {"instance_cost": cost, "api_calls": calls}},
            # keep per-message cost so the cost is inspectable / recomputable
            "messages": [{k: m.get(k) for k in ("role", "content", "cost") if k in m} for m in msgs],
            "instance_id": task,
        }
        d = out_dir / task
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{task}.traj.json").write_text(json.dumps(traj, indent=2))
        try:
            env.cleanup()
        except Exception:
            pass
    return cost, calls


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=HERE / "swelancer_manifest.json")
    ap.add_argument("--model", default=os.getenv("MSWEA_MODEL_NAME", "anthropic/claude-opus-4-8"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", help="run a single instance id (pilot)")
    ap.add_argument("--step-limit", type=int, default=250)
    ap.add_argument("--cost-limit", type=float, default=8.0)
    args = ap.parse_args(argv)

    os.environ.setdefault("MSWEA_SINGULARITY_EXECUTABLE", "apptainer")
    tasks = json.loads(args.manifest.read_text())["tasks"]
    if args.only:
        tasks = [t for t in tasks if t["instance_id"] == args.only]
        if not tasks:
            print(f"instance {args.only} not in manifest", file=sys.stderr)
            return 1

    print(f"Running {len(tasks)} SWE-Lancer task(s) with {args.model} → {args.out}")
    ok = 0
    for t in tasks:
        print(f"== {t['instance_id']} ({t['variant']} ${t['price']}) ==", flush=True)
        try:
            cost, calls = run_task(t["instance_id"], t["image"], args.model, args.out,
                                   args.step_limit, args.cost_limit)
            print(f"   done: {calls} calls, ${cost:.4f}", flush=True)
            ok += 1
        except Exception as e:
            print(f"   ERROR: {str(e).splitlines()[0][:160]}", file=sys.stderr, flush=True)
    print(f"\n{ok}/{len(tasks)} tasks completed → parse with: "
          f"parse_trajectory.py --runs-dir {args.out} --model {args.model.split('/')[-1]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
