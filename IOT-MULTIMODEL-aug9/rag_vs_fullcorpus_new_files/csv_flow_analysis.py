"""
csv_flow_analysis.py
-----------------------
Reads csv_flow_results.csv (from csv_flow_experiment.py, the real
CIC-IoT-2023 flow-feature run) and produces:
  csv_flow_summary.csv     -- per (model_key, strategy): N, correct-citation
                               rate (on the 19/34 classes with a real
                               ground-truth id), invented-ID rate,
                               abstention rate (on the 15/34 classes with no
                               matching real corpus entry), mean
                               cost/latency/tokens, each with a bootstrap
                               95% CI.
  csv_flow_by_class.csv    -- per (model_key, strategy, true_class):
                               accuracy/abstention breakdown, for a
                               per-class table in the paper.
  Paired McNemar's tests, printed to stdout, same two comparisons as
  llm_analysis.py: Claude vs GPT-4o-mini (same strategy, same sample), and
  full-corpus vs RAG (same model, same sample).

Usage:
    python3 csv_flow_analysis.py csv_flow_results.csv
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
    b = sum(1 for a, bb in pairs if a and not bb)
    c = sum(1 for a, bb in pairs if not a and bb)
    if b + c == 0:
        return b, c, 0.0, 1.0
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    p = chi2.sf(stat, df=1)
    return b, c, stat, p


def to_bool(s):
    return s == "True"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 csv_flow_analysis.py csv_flow_results.csv", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("No rows in input file.", file=sys.stderr)
        sys.exit(1)

    has_mock = any(r["model_key"].startswith("mock-") for r in rows)
    all_mock = has_mock and all(r["model_key"].startswith("mock-") for r in rows)
    is_mock = all_mock
    if all_mock:
        print("*** WARNING: this file contains ONLY MOCK data (model_key starts with 'mock-'). ***")
        print("*** Summary below is for harness verification only -- do NOT paste into the paper. ***\n")
    elif has_mock:
        n_mock = sum(1 for r in rows if r["model_key"].startswith("mock-"))
        print(f"*** NOTE: {n_mock} rows are MOCK (from an earlier --mock harness check that "
              f"wrote to the same default output file as the real run). These are EXCLUDED "
              f"from every metric below -- only real 'claude'/'gpt4o-mini' rows are analyzed. ***\n")
        rows = [r for r in rows if not r["model_key"].startswith("mock-")]

    n_errors = sum(1 for r in rows if r["api_error"])
    if n_errors:
        print(f"*** {n_errors} rows have a non-empty api_error (failed calls) -- these "
              f"are EXCLUDED from every metric below, not counted as wrong citations. "
              f"Re-run csv_flow_experiment.py (same command) once your API access is "
              f"restored to fill them in; that will only retry these, nothing else. ***\n")

    ok_rows = [r for r in rows if not r["api_error"]]
    ground_truth_rows = [r for r in ok_rows if r["is_abstention_expected"] != "True"]
    abstention_rows = [r for r in ok_rows if r["is_abstention_expected"] == "True"]

    groups = defaultdict(list)
    for r in ground_truth_rows:
        groups[(r["model_key"], r["strategy"])].append(r)
    abst_groups = defaultdict(list)
    for r in abstention_rows:
        abst_groups[(r["model_key"], r["strategy"])].append(r)

    summary_rows = []
    print(f"{'Model':16s} {'Strategy':12s} {'N':>4s}  {'Correct-cite':>18s}  "
          f"{'Invented-ID':>16s}  {'Correct-abstain':>18s}")
    for (model_key, strategy), grp in sorted(groups.items()):
        correct = [to_bool(r["correct_citation"]) for r in grp if r["correct_citation"] in ("True", "False")]
        invented = [to_bool(r["invented_id"]) for r in grp]
        cc_rate = np.mean(correct) if correct else float("nan")
        cc_lo, cc_hi = bootstrap_ci(correct) if correct else (float("nan"), float("nan"))
        inv_rate = np.mean(invented) if invented else float("nan")
        inv_lo, inv_hi = bootstrap_ci(invented) if invented else (float("nan"), float("nan"))

        agrp = abst_groups.get((model_key, strategy), [])
        abst = [to_bool(r["correctly_abstained"]) for r in agrp if r["correctly_abstained"] in ("True", "False")]
        abst_rate = np.mean(abst) if abst else float("nan")
        abst_lo, abst_hi = bootstrap_ci(abst) if abst else (float("nan"), float("nan"))

        mean_cost = np.mean([float(r["cost_usd"]) for r in grp + agrp])
        mean_lat = np.mean([float(r["latency_s"]) for r in grp + agrp])
        mean_tokens = np.mean([int(r["input_tokens"]) + int(r["output_tokens"]) for r in grp + agrp])
        total_cost = sum(float(r["cost_usd"]) for r in grp + agrp)
        n_parse_err = sum(1 for r in grp + agrp if r["parse_error"] == "True")

        print(f"{model_key:16s} {strategy:12s} {len(grp):4d}  "
              f"{cc_rate:6.3f} [{cc_lo:.3f},{cc_hi:.3f}]  "
              f"{inv_rate:6.3f} [{inv_lo:.3f},{inv_hi:.3f}]  "
              f"{abst_rate:6.3f} [{abst_lo:.3f},{abst_hi:.3f}]  "
              f"(total_cost=${total_cost:.4f})")

        summary_rows.append({
            "model_key": model_key, "strategy": strategy,
            "n_ground_truth_trials": len(grp), "n_abstention_trials": len(agrp),
            "correct_citation_rate": round(cc_rate, 4), "correct_citation_ci_lo": round(cc_lo, 4),
            "correct_citation_ci_hi": round(cc_hi, 4),
            "invented_id_rate": round(inv_rate, 4), "invented_id_ci_lo": round(inv_lo, 4),
            "invented_id_ci_hi": round(inv_hi, 4),
            "correctly_abstained_rate": round(abst_rate, 4) if abst else "",
            "correctly_abstained_ci_lo": round(abst_lo, 4) if abst else "",
            "correctly_abstained_ci_hi": round(abst_hi, 4) if abst else "",
            "mean_cost_usd": round(mean_cost, 6), "total_cost_usd": round(total_cost, 4),
            "mean_latency_s": round(mean_lat, 4),
            "mean_total_tokens": round(mean_tokens, 1), "n_parse_errors": n_parse_err,
        })

    with open("csv_flow_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print("\nWrote csv_flow_summary.csv")

    grand_total_cost = sum(float(r["cost_usd"]) for r in rows)
    print(f"Grand total spend across all {len(rows)} rows: ${grand_total_cost:.4f}")

    # --- Per-class breakdown -----------------------------------------------
    by_class = defaultdict(list)
    for r in ok_rows:
        by_class[(r["model_key"], r["strategy"], r["true_class"])].append(r)
    class_rows = []
    for (model_key, strategy, cls), grp in sorted(by_class.items()):
        is_gt = grp[0]["is_abstention_expected"] != "True"
        if is_gt:
            correct = [to_bool(r["correct_citation"]) for r in grp if r["correct_citation"] in ("True", "False")]
            rate = np.mean(correct) if correct else float("nan")
            metric = "correct_citation_rate"
        else:
            abst = [to_bool(r["correctly_abstained"]) for r in grp if r["correctly_abstained"] in ("True", "False")]
            rate = np.mean(abst) if abst else float("nan")
            metric = "correctly_abstained_rate"
        class_rows.append({
            "model_key": model_key, "strategy": strategy, "true_class": cls,
            "n": len(grp), "metric": metric, "rate": round(rate, 4) if rate == rate else "",
        })
    with open("csv_flow_by_class.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(class_rows[0].keys()))
        writer.writeheader()
        writer.writerows(class_rows)
    print("Wrote csv_flow_by_class.csv")

    # --- Paired McNemar's tests, keyed on sample_id (not query text) -------
    print("\nPaired McNemar's tests (correct_citation, ground-truth samples only):")
    by_key = defaultdict(dict)
    for r in ground_truth_rows:
        if r["correct_citation"] in ("True", "False"):
            by_key[(r["strategy"], r["sample_id"])][r["model_key"]] = to_bool(r["correct_citation"])
    model_pairs_by_strategy = defaultdict(list)
    for (strategy, sample_id), model_map in by_key.items():
        keys = list(model_map.keys())
        if len(keys) == 2:
            a, b = sorted(keys)
            model_pairs_by_strategy[strategy].append((model_map[a], model_map[b]))
    for strategy, pairs in sorted(model_pairs_by_strategy.items()):
        b_, c_, stat, p = mcnemar(pairs)
        print(f"  strategy={strategy:12s} n_pairs={len(pairs):3d}  b={b_} c={c_}  "
              f"chi2={stat:.3f}  p={p:.4f}")

    by_key2 = defaultdict(dict)
    for r in ground_truth_rows:
        if r["correct_citation"] in ("True", "False"):
            by_key2[(r["model_key"], r["sample_id"])][r["strategy"]] = to_bool(r["correct_citation"])
    strategy_pairs_by_model = defaultdict(list)
    for (model_key, sample_id), strat_map in by_key2.items():
        keys = list(strat_map.keys())
        if len(keys) == 2:
            a, b = sorted(keys)
            strategy_pairs_by_model[model_key].append((strat_map[a], strat_map[b]))
    print("\nPaired McNemar's tests (full_corpus vs rag, correct_citation, same model):")
    for model_key, pairs in sorted(strategy_pairs_by_model.items()):
        b_, c_, stat, p = mcnemar(pairs)
        print(f"  model={model_key:16s} n_pairs={len(pairs):3d}  b={b_} c={c_}  "
              f"chi2={stat:.3f}  p={p:.4f}")

    if is_mock:
        print("\n*** Reminder: all numbers above are from MOCK data. Re-run on a real "
              "(non-mock) csv_flow_results.csv before using any of this in the paper. ***")


if __name__ == "__main__":
    main()
