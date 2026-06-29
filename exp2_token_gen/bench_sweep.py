#!/usr/bin/env python3
"""
bench_sweep.py — controlled-grid throughput/latency sweep against a running vLLM server,
with a co-measured GPU power time series per cell.

For each (input_len x max_concurrency) cell it:
  1. starts power_logger.py as a sidecar (writes power_<tag>.csv),
  2. runs `vllm bench serve --dataset-name random` (rate = inf -> saturate at the chosen
     concurrency), saving the JSON result (ttft/tpot/itl/throughput/percentiles),
  3. stops the sidecar.
parse_results.py later joins each result JSON with its power CSV by <tag> to compute theta_GPU
and tokens/joule.

The shared agentic prefix (cacheable re-sent tool output, ~67% of the prompt in Exp-1) is
modeled with --random-prefix-len so vLLM automatic prefix caching is exercised as in production.

Usage (after launch_vllm.sh is healthy on $PORT):
  python bench_sweep.py --model Qwen/Qwen3.5-9B --gpu-type H100 --port 8000 \
      --out-dir ../exp2_results --gpu 0
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")


def prefix_len_for(input_len, prefix_frac):
    # round the cacheable prefix to a multiple of vLLM's block size (16) and keep < input_len
    p = int(round(input_len * prefix_frac / 16) * 16)
    return max(0, min(p, input_len - 16))


def run_cell(args, input_len, conc, prefix_frac):
    tag = f"{args.gpu_type}__{slug(args.model)}__in{input_len}__c{conc}"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    power_csv = out_dir / f"power_{tag}.csv"
    result_json = f"bench_{tag}.json"
    prefix_len = prefix_len_for(input_len, prefix_frac)

    # 1) start power sidecar
    plog = subprocess.Popen(
        [sys.executable, str(HERE / "power_logger.py"), "--gpu", str(args.gpu),
         "--interval", str(args.power_interval), "--out", str(power_csv)])
    time.sleep(1.0)  # capture a little idle baseline before load

    # 2) run vllm bench serve (saturating: request-rate inf, bounded by --max-concurrency)
    t0 = time.time()
    cmd = [
        *args.vllm_bin.split(), "bench", "serve",
        "--model", args.model,
        "--base-url", f"http://127.0.0.1:{args.port}",
        "--endpoint", "/v1/completions",
        "--dataset-name", "random",
        # vLLM ADDS random-prefix-len on top of random-input-len, so to make the TOTAL prompt equal
        # input_len (with prefix_len of it cacheable), the variable part is input_len - prefix_len.
        "--random-input-len", str(max(input_len - prefix_len, 16)),
        "--random-output-len", str(args.output_len),
        "--random-prefix-len", str(prefix_len),
        "--random-range-ratio", "0.0",
        "--ignore-eos",
        "--temperature", "0",   # greedy: deterministic, and vllm no longer defaults to it
        "--num-prompts", str(max(conc * args.prompts_per_conc, args.min_prompts)),
        "--max-concurrency", str(conc),
        "--request-rate", "inf",
        "--percentile-metrics", "ttft,tpot,itl,e2el",
        "--metric-percentiles", "50,90,99",
        "--save-result", "--result-dir", str(out_dir), "--result-filename", result_json,
        "--metadata", f"tag={tag}", f"gpu_type={args.gpu_type}", f"input_len={input_len}",
        f"max_concurrency={conc}", f"prefix_len={prefix_len}",
    ]
    print(f"\n[bench_sweep] CELL {tag}  (prefix_len={prefix_len})", flush=True)
    rc = subprocess.call(cmd)
    dt = time.time() - t0

    # 3) stop power sidecar
    plog.send_signal(signal.SIGTERM)
    try:
        plog.wait(timeout=15)
    except subprocess.TimeoutExpired:
        plog.kill()

    if rc != 0:
        print(f"[bench_sweep] WARNING: cell {tag} exited rc={rc}", file=sys.stderr)
    else:
        # stamp the wallclock window into the result so parse_results can trim power by time
        rp = out_dir / result_json
        try:
            d = json.loads(rp.read_text())
            d["_window"] = {"t_start": t0, "t_end": time.time(), "wall_s": dt, "tag": tag,
                            "power_csv": power_csv.name}
            rp.write_text(json.dumps(d))
        except Exception as e:
            print(f"[bench_sweep] could not stamp window into {rp}: {e}", file=sys.stderr)
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--gpu-type", required=True, help="label only, e.g. H100 / A100 / H200")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--gpu", type=int, default=0, help="GPU index for power_logger")
    ap.add_argument("--out-dir", default=str(HERE.parent / "exp2_results"))
    ap.add_argument("--input-lens", type=int, nargs="+", default=[8192],
                    help="representative input size(s); 8192 ~ between SWE-bench/SWE-Lancer medians")
    ap.add_argument("--concurrencies", type=int, nargs="+", default=[1, 64],
                    help="operating points: 1 = single-stream latency, 64 = saturated (max theta)")
    ap.add_argument("--output-len", type=int, default=1024)
    ap.add_argument("--prompts-per-conc", type=int, default=4,
                    help="num_prompts = max(concurrency * this, --min-prompts)")
    ap.add_argument("--min-prompts", type=int, default=32,
                    help="floor on prompts/cell so single-stream still generates enough tokens")
    ap.add_argument("--prefix-frac", type=float, default=0.665,
                    help="cacheable prefix share (Exp-1 overall mean); see workload_stats.json")
    ap.add_argument("--vllm-bin", default=os.environ.get("VLLM_BIN", "vllm"),
                    help="vLLM launcher; on Sherlock set to ./vllm_apptainer.sh (or env VLLM_BIN)")
    ap.add_argument("--power-interval", type=float, default=0.2)
    args = ap.parse_args()

    print(f"[bench_sweep] model={args.model} gpu_type={args.gpu_type} "
          f"grid input={args.input_lens} x conc={args.concurrencies} "
          f"output_len={args.output_len} prefix_frac={args.prefix_frac}")
    fails = 0
    for input_len in args.input_lens:
        for conc in args.concurrencies:
            fails += 1 if run_cell(args, input_len, conc, args.prefix_frac) else 0
    print(f"\n[bench_sweep] done; {fails} cell(s) failed. results in {args.out_dir}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
