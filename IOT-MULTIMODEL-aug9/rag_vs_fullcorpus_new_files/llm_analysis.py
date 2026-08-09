"""
llm_analysis.py
------------------
Reads llm_results.csv (from llm_experiment.py) and produces:
  llm_summary.csv        -- per (model, strategy): N, correct-citation rate,
                             invented-ID rate, wrong-explanation-eligible
                             parse errors, abstention rate (holdout set
                             only), mean cost/latency/tokens, each with a
                             bootstrap 95% CI.
  McNemar's test results  -- printed to stdout, paired two ways:
                             (a) Claude vs GPT-4o-mini, same strategy, same
                                 queries;
                             (b) full-corpus vs RAG, same model, same
                                 queries.
This is the exact statistical treatment specified in
claude_vs_gptmini_paper/paper.tex Section 6 (Statistical Plan) -- run this
against real (non-mock) llm_results.csv and paste the output into that
paper's Results tables.

Usage:
    python3 llm_analysis.py llm_results.csv
"""

import sys
import csv
from collections import defaultdict

import numpy as np
from scipy.stats import chi2


def bootstrap_ci(hits: list, n_boot: int = 10000, seed: int = 42):
    arr = np.array(hits, dtype=float)
    if len(arr) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    boot_means = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    return float(lo), float(hi)


def mcnemar(pairs: list):
    """
    pairs: list of (outcome_a: bool, outcome_b: bool) for the SAME query
    under two paired conditions (e.g., model A vs model B, or strategy A vs
    strategy B), both scored as correct=True/False on the same item.
    Returns (b, c, chi2_stat, p_value) using the continuity-corrected
    McNemar's test. b = A right/B wrong count, c = A wrong/B right count.
    """
    b = sum(1 for a, bb in pairs if a and not bb)
    c = sum(1 for a, bb in pairs if not a and bb)
    if b + c == 0:
        return b, c, 0.0, 1.0
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    p = chi2.sf(stat, df=1)
    return b, c, stat, p


def load_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def to_bool(s):
    return s == "True"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 llm_analysis.py llm_results.csv", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    rows = load_rows(path)
    if not rows:
        print("No rows in input file.", file=sys.stderr)
        sys.exit(1)

    is_mock = any(r["model_key"].startswith("mock-") for r in rows)
    if is_mock:
        print("*** WARNING: this file contains MOCK data (model_key starts with 'mock-'). ***")
        print("*** Summary below is for harness verification only -- do NOT paste into the paper. ***\n")

    main_rows = [r for r in rows if r["is_holdout_abstention_trial"] != "True"]
    holdout_rows = [r for r in rows if r["is_holdout_abstention_trial"] == "True"]

    groups = defaultdict(list)
    for r in main_rows:
        groups[(r["model_key"], r["strategy"])].append(r)
    holdout_groups = defaultdict(list)
    for r in holdout_rows:
        holdout_groups[(r["model_key"], r["strategy"])].append(r)

    summary_rows = []
    print(f"{'Model':16s} {'Strategy':12s} {'N':>4s}  {'Correct-cite':>18s}  {'Invented-ID':>16s}  {'Abstention (holdout)':>22s}")
    for (model_key, strategy), grp in sorted(groups.items()):
        correct = [to_bool(r["correct_citation"]) if r["correct_citation"] in ("True", "False") else None for r in grp]
        correct = [c for c in correct if c is not None]
        invented = [to_bool(r["invented_id"]) for r in grp]
        cc_rate = np.mean(correct) if correct else float("nan")
        cc_lo, cc_hi = bootstrap_ci(correct) if correct else (float("nan"), float("nan"))
        inv_rate = np.mean(invented) if invented else float("nan")
        inv_lo, inv_hi = bootstrap_ci(invented) if invented else (float("nan"), float("nan"))

        hgrp = holdout_groups.get((model_key, strategy), [])
        abst = [to_bool(r["correctly_abstained"]) for r in hgrp if r["correctly_abstained"] in ("True", "False")]
        abst_rate = np.mean(abst) if abst else float("nan")
        abst_lo, abst_hi = bootstrap_ci(abst) if abst else (float("nan"), float("nan"))

        mean_cost = np.mean([float(r["cost_usd"]) for r in grp])
        mean_lat = np.mean([float(r["latency_s"]) for r in grp])
        mean_tokens = np.mean([int(r["input_tokens"]) + int(r["output_tokens"]) for r in grp])
        n_parse_err = sum(1 for r in grp if r["parse_error"] == "True")

        print(f"{model_key:16s} {strategy:12s} {len(grp):4d}  "
              f"{cc_rate:6.3f} [{cc_lo:.3f},{cc_hi:.3f}]  "
              f"{inv_rate:6.3f} [{inv_lo:.3f},{inv_hi:.3f}]  "
              f"{abst_rate:6.3f} [{abst_lo:.3f},{abst_hi:.3f}]")

        summary_rows.append({
            "model_key": model_key, "strategy": strategy, "n_main_trials": len(grp),
            "n_holdout_trials": len(hgrp),
            "correct_citation_rate": round(cc_rate, 4), "correct_citation_ci_lo": round(cc_lo, 4),
            "correct_citation_ci_hi": round(cc_hi, 4),
            "invented_id_rate": round(inv_rate, 4), "invented_id_ci_lo": round(inv_lo, 4),
            "invented_id_ci_hi": round(inv_hi, 4),
            "abstention_rate": round(abst_rate, 4) if abst else "", "abstention_ci_lo": round(abst_lo, 4) if abst else "",
            "abstention_ci_hi": round(abst_hi, 4) if abst else "",
            "mean_cost_usd": round(mean_cost, 6), "mean_latency_s": round(mean_lat, 4),
            "mean_total_tokens": round(mean_tokens, 1), "n_parse_errors": n_parse_err,
        })

    out_path = "llm_summary.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\nWrote {out_path}")

    # --- Paired McNemar's tests -------------------------------------------
    print("\nPaired McNemar's tests (correct_citation, main queries only):")
    by_key = defaultdict(dict)
    for r in main_rows:
        if r["correct_citation"] in ("True", "False"):
            by_key[(r["strategy"], r["query"])][r["model_key"]] = to_bool(r["correct_citation"])

    model_pairs_by_strategy = defaultdict(list)
    for (strategy, query), model_map in by_key.items():
        keys = list(model_map.keys())
        if len(keys) == 2:
            a, b = sorted(keys)
            model_pairs_by_strategy[strategy].append((model_map[a], model_map[b]))
    for strategy, pairs in model_pairs_by_strategy.items():
        b_, c_, stat, p = mcnemar(pairs)
        print(f"  strategy={strategy:12s} n_pairs={len(pairs):3d}  b={b_} c={c_}  "
              f"chi2={stat:.3f}  p={p:.4f}")

    by_key2 = defaultdict(dict)
    for r in main_rows:
        if r["correct_citation"] in ("True", "False"):
            by_key2[(r["model_key"], r["query"])][r["strategy"]] = to_bool(r["correct_citation"])
    strategy_pairs_by_model = defaultdict(list)
    for (model_key, query), strat_map in by_key2.items():
        keys = list(strat_map.keys())
        if len(keys) == 2:
            a, b = sorted(keys)
            strategy_pairs_by_model[model_key].append((strat_map[a], strat_map[b]))
    print("\nPaired McNemar's tests (full_corpus vs rag, correct_citation, same model):")
    for model_key, pairs in strategy_pairs_by_model.items():
        b_, c_, stat, p = mcnemar(pairs)
        print(f"  model={model_key:16s} n_pairs={len(pairs):3d}  b={b_} c={c_}  "
              f"chi2={stat:.3f}  p={p:.4f}")

    if is_mock:
        print("\n*** Reminder: all numbers above are from MOCK data. Re-run on a real "
              "(non-mock) llm_results.csv before using any of this in the paper. ***")


if __name__ == "__main__":
    main()
