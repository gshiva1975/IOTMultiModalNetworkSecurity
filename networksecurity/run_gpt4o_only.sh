#!/usr/bin/env bash
# run_gpt4o_only.sh
#
# Runs ONLY the GPT-4o-mini leg of the confirmatory experiment now, across
# the full 34-class CIC-IoT-2023 dataset, without touching the Claude Sonnet
# API at all (which is still blocked by an account usage cap that resets
# 2026-09-01 per Anthropic's own error message -- see run_1000_sample_experiment.sh
# for the full history of the first, invalid 10-class attempt).
#
# Scale: 30 samples/class x 34 classes = 1,020 samples x 3 conditions
#        = 3,060 GPT-4o-mini calls, ~$1.32 at current $0.15/$0.60-per-1M pricing.
#
# How this avoids Claude entirely:
#   Step 1 calls run_pipeline.py with --skip-llm. That flag still builds the
#   real image manifest (viz/manifest.csv, 1,020 samples across all 34
#   classes) and runs the two non-LLM baselines -- it just skips the Claude
#   API call loop, so no Claude cost, no Claude errors, no API key needed for
#   that step at all.
#   Step 2 then runs GPT-4o-mini classification against that manifest.
#
# Writes to results_1000_v2/ -- the SAME out-dir + data-dir + samples-per-class
# this run will use once you add the Claude Sonnet leg after Sep 1. The
# manifest is built from a fixed-seed RNG (np.random.default_rng(7)) walked
# deterministically over the class list, so as long as --data-dir and
# --samples-per-class stay identical between this run and the later Claude
# run, re-running Step 1 then will reproduce the EXACT same manifest and
# sample_ids -- these GPT-4o-mini results will still line up correctly with
# the Claude results added later. Do not change those two flags in between.
#
# Usage:
#   cd networksecurity
#   export OPENAI_API_KEY=sk-...
#   ./run_gpt4o_only.sh

set -euo pipefail
cd "$(dirname "$0")"

DATA_DIR="/Users/gshiva/Documents/IOT-MULTIMODEL/CSV"
OUT_DIR="results_1000_v2"
LIMIT=30
SAMPLES_PER_CLASS=30

if [ ! -d "${DATA_DIR}" ]; then
  echo "ERROR: ${DATA_DIR} not found. Edit DATA_DIR at the top of this script"
  echo "to point at wherever the full 34-class CIC-IoT-2023 CSV dataset lives"
  echo "on this machine."
  exit 1
fi

echo "=== Step 1/2: build image manifest + run non-LLM baselines (no Claude, no cost) ==="
python3 scripts/run_pipeline.py \
  --data-dir "${DATA_DIR}" \
  --out-dir "${OUT_DIR}" \
  --samples-per-class "${SAMPLES_PER_CLASS}" \
  --skip-llm \
  --yes

echo ""
echo "=== Step 2/2: GPT-4o-mini run (${SAMPLES_PER_CLASS}/class, ~3,060 calls, ~\$1.32) ==="
python3 scripts/run_pipeline_gpt4o.py \
  --manifest "${OUT_DIR}/viz/manifest.csv" \
  --out-dir "${OUT_DIR}" \
  --limit "${LIMIT}" \
  --model gpt-4o-mini \
  --yes

echo ""
echo "Done. Results in ${OUT_DIR}/:"
echo "  viz/manifest.csv          -- 1,020 real images across all 34 classes"
echo "  harness_results_gpt4o.csv -- GPT-4o-mini, 3 conditions x 1,020 samples"
echo "  baseline_results.csv      -- z-score / Isolation Forest"
echo "  summary_gpt4o.txt"
echo ""
echo "No Claude data yet -- that comes later via run_1000_sample_experiment.sh"
echo "once your Anthropic account's usage cap resets (2026-09-01). Do NOT change"
echo "DATA_DIR or SAMPLES_PER_CLASS before then, or the manifest will regenerate"
echo "differently and the Claude run won't line up with this GPT-4o-mini data."
echo ""
echo "If interrupted at any point, just re-run this script -- it resumes from"
echo "where it left off and will not re-pay for completed calls."
