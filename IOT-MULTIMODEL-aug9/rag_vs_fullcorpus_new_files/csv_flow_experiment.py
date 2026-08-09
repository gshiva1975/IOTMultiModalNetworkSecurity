"""
csv_flow_experiment.py
------------------------
Real-dataset citation-grounded classification experiment over the CIC-IoT-2023
flow-feature CSVs (39 features/row), using the sample built by
build_flow_sample.py and the same 15-entry real CAPEC/CVE corpus + strategy
implementations (strategies.py) + clients (llm_clients.py) already validated
in the K3s/CVE version of this experiment.

*** RESUMABLE / CHECKPOINTED BY DESIGN ***
Every trial result is appended to the output CSV and flushed to disk
IMMEDIATELY after that single API call returns -- not batched in memory and
written once at the end. On startup, the script reads whatever output CSV
already exists and skips any (sample_id, model_key, strategy) combination
that already has a SUCCESSFUL row (api_error == ""). Rows that previously
errored are retried. This means:
  - Ctrl-C, a crash, a network drop, or a rate-limit error mid-run loses at
    most the one in-flight call, never previously-completed (and paid-for)
    work.
  - Re-running the exact same command is always safe and cheap: it will
    make zero API calls if every trial already succeeded.

Usage:
    # 1) Build the sample once (writes flow_sample_manifest.csv):
    python3 build_flow_sample.py --n-per-class 40 --seed 42

    # 2) Dry run (no API keys, no network, no real cost) to verify the
    #    harness end-to-end:
    python3 csv_flow_experiment.py --mock

    # 3) Real run (requires ANTHROPIC_API_KEY and OPENAI_API_KEY):
    python3 csv_flow_experiment.py

    # If interrupted for any reason, just run the exact same command again --
    # it resumes automatically from csv_flow_results.csv.
"""

import argparse
import csv
import os
import sys

from real_corpus import REAL_ANCHOR_ENTRIES
from strategies import FullCorpusStrategy, RAGStrategy
from llm_clients import get_client
from llm_task import SYSTEM_PROMPT, build_user_prompt, parse_response
from corpus import entry_text

FIELDNAMES = [
    "sample_id", "true_class", "model_key", "model", "strategy",
    "ground_truth_id", "shown_ids", "cited_id", "classification",
    "justification", "parse_error", "invented_id", "correct_citation",
    "correctly_abstained", "is_abstention_expected",
    "input_tokens", "output_tokens", "cost_usd", "latency_s", "api_error",
]


def build_corpus() -> list:
    return [
        {"id": eid, "kind": kind, "name": name, "attack_families": families,
         "description": desc, "source_url": "(see real_corpus.py)"}
        for eid, kind, name, families, desc in REAL_ANCHOR_ENTRIES
    ]


def load_manifest(path: str) -> list:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_done_keys(out_path: str) -> set:
    """(sample_id, model_key, strategy) tuples that already have a
    successful (api_error == '') row in the existing output file."""
    done = set()
    if not os.path.exists(out_path):
        return done
    with open(out_path, newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("api_error"):
                done.add((row["sample_id"], row["model_key"], row["strategy"]))
    return done


def run_trial(strategy, client, model_key: str, corpus_by_id: dict,
              sample_id: str, true_class: str, query_text: str,
              ground_truth_id: str, k: int) -> dict:
    gt = ground_truth_id or "__NONE__"
    call = strategy.query(query_text, gt, k=k)
    shown_entries = [corpus_by_id[i] for i in call.retrieved_ids if i in corpus_by_id]
    user_prompt = build_user_prompt(shown_entries, query_text, entry_text)

    if hasattr(client, "generate_with_truth"):
        resp = client.generate_with_truth(SYSTEM_PROMPT, user_prompt,
                                           ground_truth_id or None, call.retrieved_ids)
    else:
        resp = client.generate(SYSTEM_PROMPT, user_prompt)
    parsed = parse_response(resp.text)

    cited_id = parsed["cited_id"]
    invented_id = bool(cited_id) and cited_id not in call.retrieved_ids
    is_abstention_expected = not bool(ground_truth_id)
    correct_citation = (cited_id == ground_truth_id) if ground_truth_id else None
    correctly_abstained = (cited_id is None) if is_abstention_expected else None

    return {
        "sample_id": sample_id,
        "true_class": true_class,
        "model_key": model_key,
        "model": resp.model,
        "strategy": strategy.name,
        "ground_truth_id": ground_truth_id or "",
        "shown_ids": "|".join(call.retrieved_ids),
        "cited_id": cited_id or "",
        "classification": parsed["classification"] or "",
        "justification": (parsed["justification"] or "").replace("\n", " "),
        "parse_error": parsed["parse_error"],
        "invented_id": invented_id,
        "correct_citation": correct_citation,
        "correctly_abstained": correctly_abstained,
        "is_abstention_expected": is_abstention_expected,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
        "cost_usd": round(resp.cost_usd, 8),
        "latency_s": round(resp.latency_s, 4),
        "api_error": resp.error,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default="flow_sample_manifest.csv")
    ap.add_argument("--out", default="csv_flow_results.csv")
    ap.add_argument("--k", type=int, default=5, help="Entries retrieved per RAG query.")
    ap.add_argument("--mock", action="store_true",
                     help="No real API calls -- harness self-test only.")
    args = ap.parse_args()

    if not os.path.exists(args.manifest):
        print(f"ERROR: manifest {args.manifest} not found. Run build_flow_sample.py first.",
              file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(args.manifest)
    corpus = build_corpus()
    corpus_by_id = {e["id"]: e for e in corpus}
    model_keys = ["mock-claude", "mock-gpt4o-mini"] if args.mock else ["claude", "gpt4o-mini"]

    done = load_done_keys(args.out)
    if done:
        print(f"Resuming: {len(done)} (sample, model, strategy) trials already "
              f"succeeded in {args.out} and will be skipped.")

    file_exists = os.path.exists(args.out)
    out_f = open(args.out, "a", newline="")
    writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES)
    if not file_exists:
        writer.writeheader()
        out_f.flush()

    clients = {}
    for model_key in model_keys:
        try:
            clients[model_key] = get_client(model_key)
        except RuntimeError as e:
            print(f"ERROR setting up client '{model_key}': {e}", file=sys.stderr)
            print("Skipping this model. Use --mock to test the harness without API keys.",
                  file=sys.stderr)

    strategies = {}
    for strategy_cls in (FullCorpusStrategy, RAGStrategy):
        strat = strategy_cls(corpus) if strategy_cls is FullCorpusStrategy \
            else strategy_cls(corpus, embedder_kind="tfidf")
        strat.build_index()
        strategies[strat.name] = strat

    total_planned = len(manifest) * len(model_keys) * len(strategies)
    n_run = 0
    n_skipped = 0
    n_errors = 0

    print(f"{'MOCK ' if args.mock else ''}run: {len(manifest)} samples x "
          f"{len(model_keys)} models x {len(strategies)} strategies "
          f"= {total_planned} planned trials ({len(done)} already done).")

    for row in manifest:
        sample_id = row["sample_id"]
        true_class = row["true_class"]
        query_text = row["query_text"]
        ground_truth_id = row["ground_truth_id"]

        for model_key, client in clients.items():
            for strat_name, strat in strategies.items():
                key = (sample_id, model_key, strat_name)
                if key in done:
                    n_skipped += 1
                    continue

                result = run_trial(strat, client, model_key, corpus_by_id,
                                    sample_id, true_class, query_text,
                                    ground_truth_id, args.k)
                writer.writerow(result)
                out_f.flush()
                os.fsync(out_f.fileno())

                n_run += 1
                if result["api_error"]:
                    n_errors += 1
                else:
                    done.add(key)  # so a mid-run failure elsewhere doesn't redo this

                if n_run % 20 == 0:
                    print(f"  {n_run} new trials run this session "
                          f"({n_skipped} skipped as already-done, {n_errors} errors so far)")

    out_f.close()
    print(f"\nDone. {n_run} new trials this session, {n_skipped} skipped "
          f"(already had a successful result), {n_errors} API errors this session.")
    print(f"Results (cumulative, all sessions) are in {args.out}.")
    if args.mock:
        print("Reminder: --mock rows use model_key starting with 'mock-' and are NOT "
              "real experimental data.")
    if n_errors:
        print(f"NOTE: {n_errors} trials errored this run and were NOT marked done -- "
              f"just re-run this exact command to retry only those.")


if __name__ == "__main__":
    main()
