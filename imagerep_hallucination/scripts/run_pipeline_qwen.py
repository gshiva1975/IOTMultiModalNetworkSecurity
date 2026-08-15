#!/usr/bin/env python3
"""
run_pipeline_qwen.py -- run the SAME representation-comparison experiment
against Qwen-VL (qwen-vl-plus by default -- the chosen model for this study,
~$15 for a full 6,120-call run vs. ~$120 on Claude Sonnet 5 (real observed
cost); qwen-vl-max is
also available as a pricier, more capable alternative), against the EXACT
SAME rendered images and manifest.csv the other model runs use -- a
like-for-like cross-model comparison, not a fresh independent draw. Run
scripts/run_pipeline.py first (with --skip-llm if you don't also want a
paid Claude run) to build viz/manifest.csv.

Qwen-VL is used here in place of Claude Sonnet, without changing anything
else about the study design -- same manifest, same fixed RAG-grounded
prompt, same corpus, same grading rubric.

Setup (once):
    pip install openai   # DashScope speaks the OpenAI protocol
    export DASHSCOPE_API_KEY=sk-...   # https://dashscope.console.aliyun.com/apiKey
    (or QWEN_API_KEY / QWEN_BASE_URL if using a different OpenAI-compatible
    Qwen provider, e.g. OpenRouter or Together.ai)

Usage:
    python3 scripts/run_pipeline_qwen.py --out-dir results --probe        # 1 test call
    python3 scripts/run_pipeline_qwen.py --out-dir results --limit 10     # cheap pilot
    python3 scripts/run_pipeline_qwen.py --out-dir results --limit 0      # full run
    python3 scripts/run_pipeline_qwen.py --out-dir results --model qwen-vl-max --limit 0  # pricier, more capable
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd

from imgrep.config import DEFAULT_OUT_DIR
from imgrep.data_loader import find_benign_class
from imgrep.qwen_client import run_harness, probe, estimate_cost, DEFAULT_MODEL
from imgrep.grading import score_and_summarize


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                     help=f"directory containing viz/manifest.csv from a prior run_pipeline.py "
                          f"run (default: {DEFAULT_OUT_DIR})")
    ap.add_argument("--benign-class", default=None,
                     help="exact class name for citation grading (default: auto-detect)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                     help=f"Qwen-VL model id (default: {DEFAULT_MODEL}; try qwen-vl-max for a "
                          f"pricier, more capable option)")
    ap.add_argument("--limit", type=int, default=10,
                     help="samples (WINDOWS, not rows) per class (0 = all). Default 10.")
    ap.add_argument("--probe", action="store_true",
                     help="make ONE test call and print the result, then exit -- always run this "
                          "before a full paid run")
    ap.add_argument("--no-resume", action="store_true",
                     help="force a clean run instead of skipping already-completed calls")
    ap.add_argument("--yes", "-y", action="store_true",
                     help="skip the cost-estimate confirmation pause")
    args = ap.parse_args()

    manifest_path = os.path.join(args.out_dir, "viz", "manifest.csv")
    if not os.path.isfile(manifest_path):
        sys.exit(f"{manifest_path} not found -- run scripts/run_pipeline.py first (add --skip-llm "
                  f"if you only want the images, not a paid Claude run).")
    manifest = pd.read_csv(manifest_path)
    class_names = sorted(manifest["true_class"].unique().tolist())
    class_files = {c: [] for c in class_names}  # only used by find_benign_class, which needs just names
    benign_class = args.benign_class or find_benign_class(class_files)

    if args.probe:
        probe(manifest, class_names, args.model)
        return

    windows_per_class = manifest.groupby("true_class")["sample_id"].nunique()
    est_windows = sum(min(args.limit, n) if args.limit > 0 else n for n in windows_per_class)
    n_reps = manifest["representation"].nunique()
    est_calls = est_windows * n_reps
    est_cost = estimate_cost(est_calls, args.model)
    print(f"Estimated Qwen API calls: ~{est_calls} ({est_windows} windows x {n_reps} "
          f"representations, model={args.model}).")
    print(f"Estimated cost: ~${est_cost:.2f}.")
    if not args.yes:
        print("Ctrl-C now if that's more than you want to spend, or pass --yes next time to skip this pause.")

    harness_results = run_harness(manifest, args.limit, class_names, out_dir=args.out_dir,
                                   model=args.model, resume=not args.no_resume)

    print("\n" + "=" * 60)
    score_and_summarize(harness_results, benign_class, out_dir=args.out_dir)
    print(f"\nAll outputs saved under ./{args.out_dir}/")


if __name__ == "__main__":
    main()
