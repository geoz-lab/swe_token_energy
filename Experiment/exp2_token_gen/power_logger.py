#!/usr/bin/env python3
"""
power_logger.py — sample GPU board power + utilization during a benchmark window.

Runs as a sidecar alongside bench_sweep.py / bench_empirical.py. Samples every --interval
seconds via NVML (pynvml) and writes a CSV time series. parse_results.py integrates power over
the benchmark window to get energy (J) and combines with generated tokens -> tokens/joule.

We log board power (nvmlDeviceGetPowerUsage = full-board draw incl. memory + losses), SM/memory
utilization, memory used, SM clock, and temperature. Energy = integral(power dt) over the window
the client reports as steady-state (parse_results.py trims warmup/cooldown by timestamp).

Usage
  python power_logger.py --gpu 0 --interval 0.2 --out exp2_results/power_<tag>.csv
  # stop with SIGINT/SIGTERM (the sbatch / driver sends it when the bench finishes)
"""
import argparse
import csv
import signal
import sys
import time

try:
    import pynvml
    HAVE_NVML = True
except Exception:
    HAVE_NVML = False
    import subprocess


_RUN = True


def _stop(signum, frame):
    global _RUN
    _RUN = False


def sample_nvml(h):
    u = pynvml.nvmlDeviceGetUtilizationRates(h)
    mem = pynvml.nvmlDeviceGetMemoryInfo(h)
    try:
        clk = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_SM)
    except Exception:
        clk = -1
    try:
        temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
    except Exception:
        temp = -1
    return {
        "power_w": pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0,  # mW -> W
        "util_gpu": u.gpu,
        "util_mem": u.memory,
        "mem_used_mb": mem.used / 1024 / 1024,
        "sm_clock_mhz": clk,
        "temp_c": temp,
    }


def sample_smi(gpu):
    q = ("power.draw,utilization.gpu,utilization.memory,memory.used,clocks.sm,temperature.gpu")
    out = subprocess.check_output(
        ["nvidia-smi", f"--id={gpu}", f"--query-gpu={q}",
         "--format=csv,noheader,nounits"], text=True).strip()
    p, ug, um, mu, clk, temp = [v.strip() for v in out.split(",")]
    return {"power_w": float(p), "util_gpu": float(ug), "util_mem": float(um),
            "mem_used_mb": float(mu), "sm_clock_mhz": float(clk), "temp_c": float(temp)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--interval", type=float, default=0.2)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    h = None
    if HAVE_NVML:
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(args.gpu)
        name = pynvml.nvmlDeviceGetName(h)
        name = name.decode() if isinstance(name, bytes) else name
    else:
        name = "nvidia-smi"
    sys.stderr.write(f"[power_logger] backend={'nvml' if HAVE_NVML else 'smi'} gpu={args.gpu} "
                     f"dev={name} interval={args.interval}s -> {args.out}\n")

    fields = ["t_unix", "power_w", "util_gpu", "util_mem", "mem_used_mb", "sm_clock_mhz", "temp_c"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        next_t = time.time()
        while _RUN:
            try:
                row = sample_nvml(h) if HAVE_NVML else sample_smi(args.gpu)
            except Exception as e:  # keep logging through transient query errors
                sys.stderr.write(f"[power_logger] sample error: {e}\n")
                row = {k: -1 for k in fields if k != "t_unix"}
            row["t_unix"] = time.time()
            w.writerow(row)
            f.flush()
            next_t += args.interval
            sleep = next_t - time.time()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_t = time.time()  # fell behind; resync

    if HAVE_NVML:
        pynvml.nvmlShutdown()
    sys.stderr.write("[power_logger] stopped\n")


if __name__ == "__main__":
    main()
