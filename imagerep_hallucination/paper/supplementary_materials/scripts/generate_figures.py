#!/usr/bin/env python3
"""
generate_figures.py -- build the paper's real-data figures from the actual
n=1,020 (6,120-call) confirmatory harness results for each model. Reads
straight from harness_results_{gpt4o,qwen}.csv (and harness_results.csv for
Claude, if present) -- no numbers are hand-typed, everything is computed
here with the same wilson_ci()/grade_citation() logic grading.py uses for
summary.txt, so the figures and summary.txt can never silently disagree.

Usage:
    python3 scripts/generate_figures.py --out-dir results_1020

Outputs (written to paper/figures/):
    fig_accuracy_by_representation.png   -- grouped bars, one group per rep,
                                             one bar per model, Wilson 95% CI
                                             error bars
    fig_citation_quality.png             -- same layout, for the
                                             real-and-correct citation rate
                                             among attack samples
    fig_representations_example.png      -- 1x6 grid of one real rendered
                                             window across all 6
                                             representations (replaces the
                                             \\pending placeholder for
                                             Figure 1 / fig:reps)
"""

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import pandas as pd

from imgrep.config import REPRESENTATIONS, BENIGN_CLASS_NAME
from imgrep.grading import wilson_ci, grade_citation


def detect_benign_class(models):
    """The pipeline's own true_class values may be more specific than the
    config constant (e.g. 'Benign_Final' vs 'Benign') -- match by substring,
    same rule data_loader.find_benign_class() uses, but against the ACTUAL
    true_class values seen in the results, not the raw folder name."""
    for df in models.values():
        for cls in df["true_class"].unique():
            if BENIGN_CLASS_NAME.lower() in str(cls).lower():
                return cls
    sys.exit(f"Could not find a true_class containing '{BENIGN_CLASS_NAME}' in the loaded results.")

MODEL_FILES = {
    "Claude Sonnet 5": "harness_results.csv",
    "GPT-4o-mini": "harness_results_gpt4o.csv",
    "Qwen-vl-plus": "harness_results_qwen.csv",
}
MODEL_COLORS = {
    "Claude Sonnet 5": "#8B5CF6",
    "GPT-4o-mini": "#10A37F",
    "Qwen-vl-plus": "#F97316",
}

REP_LABELS = {
    "four_panel": "four_panel",
    "single_line": "single_line",
    "heatmap": "heatmap",
    "recurrence_plot": "recurrence_\nplot",
    "grayscale_matrix": "grayscale_\nmatrix",
    "rgb_stack": "rgb_stack",
}


def load_models(out_dir):
    """Returns {model_name: dataframe} for every model whose result file
    actually exists in out_dir -- so this script works whether you have
    1, 2, or 3 models' worth of real data."""
    found = {}
    for name, fname in MODEL_FILES.items():
        path = os.path.join(out_dir, fname)
        if os.path.isfile(path):
            df = pd.read_csv(path)
            df = df[df["classification"].astype(str).str.upper() != "ERROR"]
            found[name] = df
    if not found:
        sys.exit(f"No harness_results*.csv found under {out_dir} -- run a real pipeline first.")
    return found


def accuracy_table(models):
    """rows: representation, cols: model -> (p, lo, hi, n)"""
    rows = {}
    for model, df in models.items():
        for rep, g in df.groupby("representation"):
            correct = (g["classification"].astype(str).str.strip()
                       == g["true_class"].astype(str).str.strip()).sum()
            p, lo, hi = wilson_ci(int(correct), len(g))
            rows.setdefault(rep, {})[model] = (p, lo, hi, len(g))
    return rows


def citation_table(models, benign_class):
    rows = {}
    for model, df in models.items():
        df = df.copy()
        df["citation_grade"] = df.apply(
            lambda r: grade_citation(r["true_class"], r["reference_id"], benign_class), axis=1)
        for rep, g in df.groupby("representation"):
            attack_g = g[g["true_class"] != benign_class]
            correct = (attack_g["citation_grade"] == "real-and-correct").sum()
            p, lo, hi = wilson_ci(int(correct), len(attack_g))
            rows.setdefault(rep, {})[model] = (p, lo, hi, len(attack_g))
    return rows


def grouped_bar(table, models_present, title, ylabel, out_path):
    reps = [r for r in REPRESENTATIONS if r in table]
    n_models = len(models_present)
    x = np.arange(len(reps))
    width = 0.8 / max(n_models, 1)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, model in enumerate(models_present):
        vals, los, his = [], [], []
        for rep in reps:
            p, lo, hi, n = table[rep].get(model, (0, 0, 0, 0))
            vals.append(p * 100)
            los.append((p - lo) * 100)
            his.append((hi - p) * 100)
        offset = (i - (n_models - 1) / 2) * width
        ax.bar(x + offset, vals, width, yerr=[los, his], capsize=3,
               label=model, color=MODEL_COLORS.get(model, None))

    ax.set_xticks(x)
    ax.set_xticklabels([REP_LABELS.get(r, r) for r in reps], fontsize=10)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 100)
    ax.set_title(title)
    ax.legend(loc="upper right", frameon=False)
    ax.axhline(10, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.text(len(reps) - 0.5, 11.5, "10-class chance rate", fontsize=8, color="gray", ha="right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"wrote {out_path}")


def representation_grid(out_dir, out_path):
    """Grab one real sample_id that has all 6 representations rendered and
    lay them out in a 1x6 grid, for the paper's Figure 1."""
    viz_dir = os.path.join(out_dir, "viz")
    # find a class folder and a sample_id prefix with all 6 reps present
    for class_dir in sorted(glob.glob(os.path.join(viz_dir, "*"))):
        if not os.path.isdir(class_dir):
            continue
        files = os.listdir(class_dir)
        prefixes = sorted(set(f.split("__")[0] for f in files if "__" in f))
        for prefix in prefixes:
            paths = {rep: os.path.join(class_dir, f"{prefix}__{rep}.png") for rep in REPRESENTATIONS}
            if all(os.path.isfile(p) for p in paths.values()):
                fig, axes = plt.subplots(1, len(REPRESENTATIONS), figsize=(18, 3.2))
                for ax, rep in zip(axes, REPRESENTATIONS):
                    img = mpimg.imread(paths[rep])
                    ax.imshow(img)
                    ax.set_title(REP_LABELS.get(rep, rep).replace("\n", " "), fontsize=10)
                    ax.axis("off")
                fig.suptitle(f"Sample: {prefix}", fontsize=9, y=1.02)
                fig.tight_layout()
                fig.savefig(out_path, dpi=200, bbox_inches="tight")
                plt.close(fig)
                print(f"wrote {out_path} (sample: {prefix})")
                return
    print("WARNING: could not find a sample with all 6 representations rendered -- skipping grid figure.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="results_1020",
                     help="directory containing harness_results*.csv and viz/ (default: results_1020)")
    ap.add_argument("--figures-dir", default="paper/figures",
                     help="where to write the PNG figures (default: paper/figures)")
    args = ap.parse_args()

    os.makedirs(args.figures_dir, exist_ok=True)
    models = load_models(args.out_dir)
    print(f"Found real data for: {', '.join(models.keys())}")
    models_present = [m for m in MODEL_FILES if m in models]  # stable order
    benign_class = detect_benign_class(models)
    print(f"Detected benign class: {benign_class!r}")

    acc_table = accuracy_table(models)
    grouped_bar(acc_table, models_present,
                "Classification accuracy by image representation (n=1,020/bar, Wilson 95% CI)",
                "Accuracy (%)",
                os.path.join(args.figures_dir, "fig_accuracy_by_representation.png"))

    cit_table = citation_table(models, benign_class)
    grouped_bar(cit_table, models_present,
                "Citation quality by image representation (real-and-correct rate among attack samples)",
                "Real-and-correct rate (%)",
                os.path.join(args.figures_dir, "fig_citation_quality.png"))

    representation_grid(args.out_dir, os.path.join(args.figures_dir, "fig_representations_example.png"))


if __name__ == "__main__":
    main()
