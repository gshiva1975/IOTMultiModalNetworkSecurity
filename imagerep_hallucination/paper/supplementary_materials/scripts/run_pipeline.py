#!/usr/bin/env python3
"""
run_pipeline.py -- end-to-end entry point: render each sampled traffic
window into all 5 image representations, classify every (sample,
representation) pair with Claude under a single fixed RAG-grounded prompt,
and print/save a scored summary broken out by representation.

This is the ONLY script in this project that spends real money against the
Anthropic API (run_pipeline_gpt4o.py is the OpenAI twin).

Setup (once):
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...

Usage:
    python3 scripts/run_pipeline.py --data-dir data/CSV --list-classes
    python3 scripts/run_pipeline.py --data-dir data/CSV --limit 10             # cheap pilot
    python3 scripts/run_pipeline.py --data-dir data/CSV --limit 0              # full run
    python3 scripts/run_pipeline.py --data-dir data/CSV --classes Benign,DDoS-TCP_Flood
    python3 scripts/run_pipeline.py --data-dir data/CSV --representations four_panel,grayscale_matrix

Outputs (written to --out-dir, default ./results/):
    viz/<class>/<sample_id>__<representation>.png  -- the 5 renderings per sampled window
    viz/manifest.csv                                -- one row per (sample_id, representation)
    harness_results.csv                             -- Claude's classifications + citations
    summary.txt                                     -- accuracy + citation-quality tables, by representation

Note: --limit and --samples-per-class are per-class sample (WINDOW) counts,
not manifest-row counts -- each window becomes len(--representations) rows.
So --limit 10 with the default 5 representations is 10 windows x 5 = 50 API
calls per class, not 10.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from imgrep.config import DEFAULT_DATA_DIR, DEFAULT_OUT_DIR, EMPIRICAL_COST_PER_CALL, MODEL, REPRESENTATIONS
from imgrep.data_loader import discover_classes, find_benign_class
from imgrep.visualization_variants import build_visualizations
from imgrep.claude_client import run_harness
from imgrep.grading import score_and_summarize


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                     help=f"directory containing one subfolder per class, each full of CSV part "
                          f"files (default: {DEFAULT_DATA_DIR})")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                     help=f"where to write viz/, harness_results.csv, etc. (default: {DEFAULT_OUT_DIR})")
    ap.add_argument("--classes", default=None,
                     help="comma-separated list of class subfolder names to include (default: all)")
    ap.add_argument("--benign-class", default=None,
                     help="exact class name to treat as normal traffic (default: auto-detect by "
                          "matching 'benign' in the folder name)")
    ap.add_argument("--representations", default=None,
                     help=f"comma-separated subset of representations to render/classify "
                          f"(default: all {len(REPRESENTATIONS)}: {','.join(REPRESENTATIONS)})")
    ap.add_argument("--limit", type=int, default=10,
                     help="Claude samples (WINDOWS, not rows) per class (0 = all). Default 10 for "
                          "a cheap pilot.")
    ap.add_argument("--samples-per-class", type=int, default=40,
                     help="total visualization windows to generate per class (should be >= --limit)")
    ap.add_argument("--model", default=MODEL, help=f"Claude model id (default: {MODEL})")
    ap.add_argument("--skip-llm", action="store_true",
                     help="only build visualizations (no API key needed, no cost)")
    ap.add_argument("--list-classes", action="store_true",
                     help="just print discovered classes and file counts, then exit")
    ap.add_argument("--no-resume", action="store_true",
                     help="by default, a rerun with the SAME arguments skips already-completed "
                          "calls and retries only ERROR rows. Pass this to force a clean run.")
    ap.add_argument("--yes", "-y", action="store_true",
                     help="skip the cost-estimate confirmation pause and run immediately")
    args = ap.parse_args()

    representations = args.representations.split(",") if args.representations else REPRESENTATIONS
    unknown = set(representations) - set(REPRESENTATIONS)
    if unknown:
        sys.exit(f"Unknown representation(s): {sorted(unknown)}. Valid options: {REPRESENTATIONS}")

    only_classes = set(args.classes.split(",")) if args.classes else None
    class_files = discover_classes(args.data_dir, only_classes)

    print(f"Discovered {len(class_files)} classes under {args.data_dir}:")
    for name, files in class_files.items():
        print(f"  {name}: {len(files)} file(s)")

    if args.list_classes:
        return

    benign_class = args.benign_class or find_benign_class(class_files)
    if benign_class:
        print(f"\nUsing '{benign_class}' as the normal-traffic class.")
    else:
        print("\nWARNING: could not auto-detect a benign class (no folder name contains 'benign'). "
              "Pass --benign-class explicitly if citation grading needs it.")

    if not args.skip_llm:
        windows_per_class = min(args.limit, args.samples_per_class) if args.limit > 0 else args.samples_per_class
        est_calls = sum(windows_per_class for _ in class_files) * len(representations)
        est_cost = est_calls * EMPIRICAL_COST_PER_CALL
        print(f"\nEstimated Claude API calls for this run: ~{est_calls} "
              f"({len(class_files)} classes x up to {windows_per_class} windows x "
              f"{len(representations)} representations).")
        print(f"Estimated cost: ~${est_cost:.2f} (based on the original project's observed "
              f"~${EMPIRICAL_COST_PER_CALL}/call; actual cost depends on image size and response length).")
        if not args.yes:
            print("Ctrl-C now if that's more than you want to spend, or pass --yes next time to skip this pause.")

    os.makedirs(args.out_dir, exist_ok=True)
    import json
    from imgrep.corpus import CVE_CORPUS
    with open(os.path.join(args.out_dir, "cve_corpus.json"), "w") as f:
        json.dump(CVE_CORPUS, f, indent=2)

    print(f"\nBuilding visualizations ({len(representations)} representations per window)...")
    manifest = build_visualizations(class_files, args.samples_per_class, out_dir=args.out_dir,
                                     representations=representations)

    class_names = sorted(class_files.keys())
    harness_results = None
    if not args.skip_llm:
        print("\nRunning Claude harness (this calls the Anthropic API and will incur cost)...")
        harness_results = run_harness(manifest, args.limit, class_names, out_dir=args.out_dir,
                                       resume=not args.no_resume, model=args.model)
    else:
        print("\n--skip-llm set: skipping Claude harness entirely.")

    print("\n" + "=" * 60)
    score_and_summarize(harness_results, benign_class, out_dir=args.out_dir)
    print(f"\nAll outputs saved under ./{args.out_dir}/")


if __name__ == "__main__":
    main()
