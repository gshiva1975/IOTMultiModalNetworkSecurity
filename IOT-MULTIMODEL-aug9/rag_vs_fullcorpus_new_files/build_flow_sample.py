"""
build_flow_sample.py
----------------------
Stratified sample of N rows per class from the real CIC-IoT-2023 CSV dataset
(/Users/gshiva/Documents/IOT-MULTIMODEL/CSV), one row = one flow with 39
extracted features. Writes a manifest CSV that freezes the exact sampled
rows AND their serialized query_text, so the experiment script never needs
to re-touch the (multi-GB) source CSVs on later runs -- this manifest,
once written, is the single fixed input for csv_flow_experiment.py.

Sampling is memory-safe: for each class, row indices are drawn from the
known per-file row counts (no full-file load), then each source file is
scanned once to pull out only the needed rows.

Usage:
    python3 build_flow_sample.py --n-per-class 40 --seed 42 --out flow_sample_manifest.csv
"""

import argparse
import csv
import random

from csv_flow_common import (
    list_classes, class_files, CLASS_TO_ENTRY_ID, FEATURE_COLUMNS,
    serialize_row, read_specific_rows,
)


def count_rows(filepath: str) -> int:
    with open(filepath, newline="") as f:
        return sum(1 for _ in f) - 1  # minus header


def sample_class(cls: str, n: int, seed: int) -> list:
    files = class_files(cls)
    counts = [count_rows(f) for f in files]
    total = sum(counts)
    if total == 0:
        print(f"  WARNING: class {cls} has 0 data rows, skipping")
        return []
    n = min(n, total)

    rng = random.Random(seed)
    global_indices = sorted(rng.sample(range(total), n))

    # Map global indices -> (file, local_index)
    by_file = {}
    cum = 0
    fi = 0
    for gi in global_indices:
        while gi >= cum + counts[fi]:
            cum += counts[fi]
            fi += 1
        local_idx = gi - cum
        by_file.setdefault(fi, set()).add(local_idx)

    rows = []
    for fi, local_set in by_file.items():
        fpath = files[fi]
        found = read_specific_rows(fpath, local_set)
        for local_idx, values in found.items():
            rows.append((fpath, local_idx, values))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-per-class", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="flow_sample_manifest.csv")
    args = ap.parse_args()

    classes = list_classes()
    print(f"{len(classes)} classes found. Sampling {args.n_per_class}/class "
          f"(seed={args.seed})...")

    out_rows = []
    n_mapped = 0
    for ci, cls in enumerate(classes):
        # Per-class seed derived from the global seed + class name so the
        # sample is reproducible and independent of class iteration order.
        class_seed = args.seed + (hash(cls) % 1_000_000)
        sampled = sample_class(cls, args.n_per_class, class_seed)
        gt_id = CLASS_TO_ENTRY_ID.get(cls, "")
        if gt_id:
            n_mapped += 1
        for j, (fpath, local_idx, values) in enumerate(sampled):
            sample_id = f"{cls}__{j:03d}"
            query_text = serialize_row(values)
            row = {
                "sample_id": sample_id,
                "true_class": cls,
                "ground_truth_id": gt_id,  # "" means abstention-expected trial
                "source_file": fpath,
                "row_index": local_idx,
                "query_text": query_text,
            }
            out_rows.append(row)
        print(f"  [{ci+1:2d}/{len(classes)}] {cls:28s} -> {len(sampled):3d} rows "
              f"(gt={'yes:' + gt_id if gt_id else 'no (abstention-expected)'})")

    fieldnames = ["sample_id", "true_class", "ground_truth_id", "source_file",
                  "row_index", "query_text"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"\nWrote {len(out_rows)} sampled rows to {args.out}")
    print(f"{n_mapped}/{len(classes)} classes have a real ground-truth citation id; "
          f"{len(classes) - n_mapped} are abstention-expected trials.")


if __name__ == "__main__":
    main()
