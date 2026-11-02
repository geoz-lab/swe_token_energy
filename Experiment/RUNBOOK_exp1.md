# RUNBOOK — Experiment 1 (agentic token consumption) on Sherlock

End-to-end steps to measure per-task agentic token demand for `claude-opus-4-8`, `gpt-5.4`,
`gemini-3.1-pro-preview` over the sampled SWE-bench tasks, on Sherlock **CPU** nodes.

**Where things run:** model inference = provider clouds (APIs); agent loop + repo/test execution
= Sherlock CPU node inside **Apptainer** (no Docker on Sherlock); grading = **sb-cli cloud**
(avoids Docker entirely). **No GPU is requested anywhere in Exp-1.**

Key paths used below — set once:
```bash
export PROJ=$HOME/token_energy/Experiment        # where this repo lives on Sherlock
export SCRATCH=${SCRATCH:-/scratch/users/$USER}  # large scratch for container images
```

---

## Step 0 — Confirm the two prerequisites (do this FIRST)
Grab a short interactive CPU allocation and verify outbound internet + Apptainer:
```bash
salloc -p normal -c 2 --mem=4G -t 0:20:00
module load system apptainer 2>/dev/null || module load singularity 2>/dev/null
apptainer --version                              # must print a version
curl -sI https://api.anthropic.com | head -1     # must return an HTTP status line
exit
```
- If `curl` hangs/fails → compute nodes are walled off; Exp-1 can't call the APIs from there.
  Stop and switch to a Docker/Modal box (tell me and I'll adjust the plan).
- If both succeed → proceed.

---

## Step 1 — Get the project onto Sherlock
From your **Mac** (the repo is in OneDrive). Do **not** copy `.env` over an untrusted channel; rsync over SSH is fine.
```bash
# on the Mac:
rsync -av --exclude .venv --exclude data/'*.parquet' \
  "/Users/geozhang/Library/CloudStorage/OneDrive-Stanford/2024-Autumn/Research/Projects/token_energy_paper/Experiment/" \
  sherlock:token_energy/Experiment/
```
`.env` (your keys) transfers via rsync/SSH encrypted — fine. On Sherlock, lock it down:
```bash
chmod 600 $PROJ/.env
```

---

## Step 2 — Python env + install
```bash
cd $PROJ
module load python/3.12 2>/dev/null || true
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r exp1_token_consumption/requirements-sherlock.txt
```

---

## Step 3 — Datasets + task filters
Datasets may already be in `exp1_token_consumption/data/` (rsynced). If not, re-download (no token needed):
```bash
cd $PROJ/exp1_token_consumption
python download_datasets.py
python make_filter.py        # -> data/filter_swe_bench_{lite,verified}.txt (our exact sampled ids)
```
(The 70-task manifest `task_manifest.json` is already committed; re-run `sample_tasks.py --local-dir data`
only if you want to re-sample.)

---

## Step 4 — Point Apptainer at scratch
SWE-bench task images are large; keep them off `$HOME`:
```bash
export APPTAINER_CACHEDIR=$SCRATCH/apptainer_cache
mkdir -p $APPTAINER_CACHEDIR
```

---

## Will this actually run on Sherlock? (read before Step 5)
Two parts, different confidence levels:
- **Definitely runs:** the agent loop, the API calls, and token recording. Proven on the Mac
  (`smoke_test.py`, all 3 models green) — identical on a Sherlock CPU node once Step 0 passes.
- **The real risk = Apptainer running SWE-bench's Docker images.** Those images assume **root + a
  writable filesystem + `conda activate testbed` via `/root/.bashrc`**. Apptainer runs **read-only,
  non-root, and bind-mounts your `$HOME` over `/root`**, which can break (a) writing/editing in
  `/testbed`, (b) the conda activation (BASH_ENV), (c) user namespaces. mini-swe-agent supports a
  singularity backend, but these HPC quirks are exactly where it can fail. **I cannot guarantee this
  remotely — the single-task pilot (Step 5) is the definitive 10-minute test.**

**Mitigations to try if the pilot's container step fails** (apply in mini-swe-agent's singularity
backend / `apptainer` flags): `--writable-tmpfs` (writable `/testbed`), `--no-home --containall`
(stop `$HOME` shadowing `/root`), and check whether Sherlock allows `--fakeroot`/user namespaces
(`apptainer config` / ask Research Computing). Send me the pilot error and I'll adjust.

**Reliable fallback — Modal (sidesteps Apptainer entirely):** run the SWE-bench environment in
Modal's cloud while Sherlock just orchestrates the agent + APIs:
```bash
pip install modal && modal token set        # one-time (free tier)
# then run any job with the modal backend instead of singularity:
ENVCLASS=modal ./slurm/submit_all.sh        # or add ENVCLASS=modal to the sbatch --export
mini-extra swebench-single -c swebench.yaml --environment-class modal \
  --model anthropic/claude-opus-4-8 --subset lite --split test -i django__django-11099 -o $SCRATCH/exp1/pilot_modal
```
If Apptainer turns into a time sink, switch to `ENVCLASS=modal` and keep moving — the token numbers
are identical (same images, same agent), only the execution host differs.

---

## Step 5 — PILOT (5 tasks, one model) — validate the whole loop cheaply
Run a single instance first to confirm Apptainer pulls the image and the agent completes:
```bash
source $PROJ/.venv/bin/activate
set -a; source $PROJ/.env; set +a
export MSWEA_GLOBAL_COST_LIMIT=5            # hard $ stop for the pilot

mini-extra swebench-single \
  --model anthropic/claude-opus-4-8 \
  --subset lite --split test \
  --environment-class singularity \
  -i django__django-11099 \
  -o $SCRATCH/exp1/pilot
```
Then a 5-task batch:
```bash
mini-extra swebench \
  --model anthropic/claude-opus-4-8 --subset lite --split test \
  --environment-class singularity \
  --slice 0:5 --workers 2 \
  -o $SCRATCH/exp1/pilot_batch
```

### 5a — Confirm the trajectory schema, then finalize the parser
```bash
python parse_trajectory.py --inspect $SCRATCH/exp1/pilot_batch/*/[!.]*.traj.json | head
```
Look at the printed keys/roles. The reliable totals (input/output/cost) parse already; if the
**T_tool / T_retry** split needs adjusting to the real field names, tell me the `--inspect` output
and I'll finalize `parse_trajectory.py` (one-line tweak). Then:
```bash
python parse_trajectory.py --runs-dir $SCRATCH/exp1/pilot_batch --model claude-opus-4-8
cat ../exp1_results/exp1_raw.csv
```

### 5b — Calibrate cost before scaling
```bash
python estimate_cost.py --tasks 90    # compare projected $/task vs the pilot's measured $/task
```
If the pilot's real $/task is much higher than "mid", trim sample size or lower the model before the full run.

---

## Step 6 — FULL RUN (each model × subset) via SLURM
Generate the filters once (Step 3), then submit all 6 jobs (3 models × {lite, verified}) in one command:
```bash
cd $PROJ/exp1_token_consumption
DRYRUN=1 ./slurm/submit_all.sh      # preview the 6 sbatch commands first
./slurm/submit_all.sh               # submit all 6  (or: ./slurm/submit_all.sh opus  for one model)
```
`submit_all.sh` sets each job's model id, output dir, and **cost cap** (Opus 350 / gpt-5.4 200 /
Gemini 200). To submit manually instead, the per-job form is:
```bash
cd $PROJ/exp1_token_consumption
sbatch --export=ALL,PROJ=$PROJ,MODEL=anthropic/claude-opus-4-8,SUBSET=lite,\
FILTERFILE=$PROJ/exp1_token_consumption/data/filter_swe_bench_lite.txt,\
OUTDIR=$SCRATCH/exp1/opus_lite,COSTLIMIT=350,WORKERS=4 slurm/run_exp1.sbatch

sbatch --export=ALL,PROJ=$PROJ,MODEL=anthropic/claude-opus-4-8,SUBSET=verified,\
FILTERFILE=$PROJ/exp1_token_consumption/data/filter_swe_bench_verified.txt,\
OUTDIR=$SCRATCH/exp1/opus_verified,COSTLIMIT=350,WORKERS=4 slurm/run_exp1.sbatch
```
Repeat with:
| MODEL (litellm id) | COSTLIMIT |
|---|---|
| `anthropic/claude-opus-4-8` | 350 |
| `openai/gpt-5.4` | 200 |
| `gemini/gemini-3.1-pro-preview` | 200 |

`MSWEA_GLOBAL_COST_LIMIT` (=COSTLIMIT) is a hard per-job $ stop. `STEP_CAP`/per-task limits come from
the swebench.yaml agent config (defaults are fine; we set step limit ~50 if needed). Monitor:
```bash
squeue -u $USER
tail -f slurm-exp1-*.out
```

---

## Step 7 — Grade (success rate) via sb-cli cloud — no Docker
Each run wrote `preds.json`. Submit per subset (get a free key at swebench.com → `SWEBENCH_API_KEY`):
```bash
export SWEBENCH_API_KEY=...    # one-time
sb-cli submit swe-bench_lite     test --predictions_path $SCRATCH/exp1/opus_lite/preds.json     --run_id opus_lite
sb-cli submit swe-bench_verified test --predictions_path $SCRATCH/exp1/opus_verified/preds.json --run_id opus_verified
# sb-cli get-report swe-bench_lite test --run_id opus_lite   -> resolved/unresolved per instance
```
(Local alternative needs Apptainer-converted images: `python -m swebench.harness.run_evaluation …` — heavier.)

---

## Step 8 — Aggregate token records
Parse every run into one CSV (pass the grading report so `resolved` is filled):
```bash
cd $PROJ/exp1_token_consumption
for m in opus:claude-opus-4-8 gpt54:gpt-5.4 gemini:gemini-3.1-pro-preview; do
  tag=${m%%:*}; model=${m##*:}
  python parse_trajectory.py --runs-dir $SCRATCH/exp1/${tag}_lite     --model $model --results report_${tag}_lite.json
  python parse_trajectory.py --runs-dir $SCRATCH/exp1/${tag}_verified --model $model --results report_${tag}_verified.json
done
```
Output: `exp1_results/exp1_raw.csv` — per (model, task): `T_input/T_output/T_tool/T_retry`, totals, steps,
cost, resolved. This is the dataset for the token-demand distribution → `T_FTE` and the paper figures.

---

## Step 9 — SWE-Lancer (later, optional → 90 tasks)
SWE-Lancer is Docker-heavy and has an unstable HF schema. When ready: export its task list to a
local `.jsonl`, then `python sample_tasks.py --local-dir data --lancer-source swelancer.jsonl` to
extend the manifest to 90, regenerate filters, and run its own harness. Flag me to wire it in.

---

## Troubleshooting
- **`curl` to api.anthropic.com fails on the node** → no outbound internet; move Exp-1 to a Docker/Modal box.
- **Apptainer image pull fails / OOM** → ensure `APPTAINER_CACHEDIR` is on `$SCRATCH`; raise `--mem`.
- **`mini-extra` not found** → `pip install mini-swe-agent` in the active venv; check `which mini-extra`.
- **403 from OpenAI** → the project lost `gpt-5.4` access again (it was flapping); re-enable in the
  OpenAI dashboard and re-test with `python smoke_test.py`.
- **Cost ran to the limit** → job stopped by `MSWEA_GLOBAL_COST_LIMIT`; lower `--workers`, trim tasks,
  or raise the cap deliberately.
- **Rate limits (429)** → lower `--workers`; litellm retries with backoff.
