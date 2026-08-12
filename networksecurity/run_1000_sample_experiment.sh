#!/usr/bin/env bash
# run_1000_sample_experiment.sh
#
# Confirmatory run for "Grounding Reduces Citation Hallucination in Multimodal
# LLM Zero-Shot Classification of IoT-Botnet Traffic" (CitationMultmodelNWThreatDetection).
#
# Scale: 30 samples/class x 34 classes = 1,020 samples x 3 conditions
#        = 3,060 Claude Sonnet calls (~$19) + 3,060 GPT-4o-mini calls (~$1)
#        = ~$20 total, real pricing as of Aug 2026 (check networksecurity/README.md
#          for current per-call cost assumptions before running -- pricing note in
#          config.py says the $2/$10-per-M rate it's based on is valid through
#          Aug 31 2026).
#
# (Scaled down from an original 60/class, ~$40 plan to 30/class, ~$20, per
# explicit request to cut cost -- still ~7x the current 141-sample pilot.)
#
# --data-dir now points at the FULL 34-class CIC-IoT-2023 dataset
# (/Users/gshiva/Documents/IOT-MULTIMODEL/CSV), not the local networksecurity/data/CSV/
# folder -- that local copy only has 10 of the 34 classes, which silently
# scoped the first attempt at this run down to 300 samples instead of 1,020.
#
# --out-dir is a FRESH folder (results_1000_v2/), not results_1000/ (the first,
# now-invalid attempt). Two independent reasons this can't just resume into
# results_1000/:
#   1. Every one of its 900 Claude Sonnet rows is an ERROR (account usage-limit
#      quota, resets 2026-09-01) -- zero real Claude data to preserve.
#   2. Its 628 real GPT-4o-mini rows were generated against a manifest built
#      from only 10 classes. visualization.py's sampling uses ONE shared,
#      sequential RNG (np.random.default_rng(7)) walked across
#      sorted(class_files) in order -- expanding 10 classes to 34 shifts that
#      sorted order and changes which packet windows get drawn for EVERY
#      class, including the original 10. Re-running with the full dataset
#      would silently overwrite those classes' images with different content
#      while the old sample_ids in results_1000/harness_results_gpt4o.csv kept
#      pointing at what's now stale metadata -- not safe to resume across a
#      class-set change, so this run starts clean instead.
#      (results_1000/ is left on disk as a record of the diagnostic; it is
#      not used by this script and can be deleted once you no longer need it.)
#
# IMPORTANT: this still does NOT touch results/ (the 141-sample pilot the
# current paper draft is based on). Pilot = Study 1, this = confirmatory
# Study 2.
#
# RESUME BEHAVIOR (within THIS run, once started, still fully safe):
#   - Both run_pipeline.py and run_pipeline_gpt4o.py skip any (sample_id, condition)
#     pair that already succeeded on a prior attempt, and retry only ERROR rows.
#   - Do NOT change --data-dir, --samples-per-class, or the class set between
#     attempts at THIS run once it's started, or the manifest will regenerate
#     differently and resume will not line up (see reason 2 above).
#   - If interrupted (Ctrl-C, network error, API quota hit), just re-run this
#     same script again -- it will skip everything already done in
#     results_1000_v2/.
#
# Usage:
#   cd networksecurity
#   export ANTHROPIC_API_KEY=sk-ant-...
#   export OPENAI_API_KEY=sk-...
#   ./run_1000_sample_experiment.sh

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

echo "=== Step 1/2: Claude Sonnet run (${SAMPLES_PER_CLASS}/class, ~3,060 calls, ~\$19) ==="
python3 scripts/run_pipeline.py \
  --data-dir "${DATA_DIR}" \
  --out-dir "${OUT_DIR}" \
  --limit "${LIMIT}" \
  --samples-per-class "${SAMPLES_PER_CLASS}" \
  --yes

echo ""
echo "=== Step 2/2: GPT-4o-mini run on the SAME manifest (~3,060 calls, ~\$1) ==="
python3 scripts/run_pipeline_gpt4o.py \
  --manifest "${OUT_DIR}/viz/manifest.csv" \
  --out-dir "${OUT_DIR}" \
  --limit "${LIMIT}" \
  --model gpt-4o-mini \
  --yes

echo ""
echo "Done. Results in ${OUT_DIR}/:"
echo "  harness_results.csv       -- Claude Sonnet, 3 conditions x 1,020 samples"
echo "  harness_results_gpt4o.csv -- GPT-4o-mini, 3 conditions x 1,020 samples (same images)"
echo "  baseline_results.csv      -- z-score / Isolation Forest"
echo "  summary.txt / summary_gpt4o.txt"
echo ""
echo "If interrupted at any point, just re-run this script -- both steps resume"
echo "from where they left off and will not re-pay for completed calls."
