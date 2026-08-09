"""
llm_experiment.py
-------------------
2x2 comparison: {full_corpus, rag} context-construction strategy x
{claude, gpt4o-mini} model, on the citation-grounded classification task,
using the same 15 real CAPEC/CVE anchor entries and 45-query set already
established and verified in this project (real_corpus.py).

This is the code behind claude_vs_gptmini_paper/paper.tex's empty Results
table -- run this (with real API keys) and feed the output CSVs into
llm_analysis.py to fill that table in.

Usage:
    # Dry run: verifies the harness itself works, with NO real API calls,
    # NO network access, and NO real model output. Mock results are
    # written with model names "mock-claude" / "mock-gpt4o-mini" so they
    # can never be confused with real results downstream.
    python3 llm_experiment.py --mock

    # Real run (requires ANTHROPIC_API_KEY and OPENAI_API_KEY in the
    # environment):
    python3 llm_experiment.py --corpus-size 15

Outputs:
    llm_results.csv   -- one row per (model, strategy, query) trial
    llm_summary.csv   -- aggregated metrics per (model, strategy), written
                          by llm_analysis.py after this script finishes
"""

import argparse
import csv
import sys
import time

from corpus import entry_text, _distractor_entry
from real_corpus import REAL_ANCHOR_ENTRIES, REAL_ANCHOR_QUERIES_ALL
from strategies import FullCorpusStrategy, RAGStrategy
from llm_clients import get_client
from llm_task import SYSTEM_PROMPT, build_user_prompt, parse_response

# ---------------------------------------------------------------------------
# Held-out abstention set: security observations that do NOT correspond to
# any of the 15 real anchor entries, used to measure whether each
# (model, strategy) condition correctly abstains rather than forcing a
# citation onto the nearest wrong entry. ground_truth_id=None throughout.
# ---------------------------------------------------------------------------
HELD_OUT_ABSTENTION_QUERIES = [
    ("The device's firmware update mechanism accepts unsigned binaries over an unencrypted HTTP connection.", None),
    ("A user reported that the mobile companion app stores the Wi-Fi password in plaintext in a world-readable file.", None),
    ("The gateway's Bluetooth Low Energy pairing process does not require a PIN or passkey confirmation.", None),
    ("An audit found that decommissioned devices were resold with the previous owner's cloud account still linked.", None),
    ("The vendor's cloud API allows any authenticated user to query telemetry for device IDs they do not own.", None),
]


def build_real_corpus(target_size: int, seed: int = 42) -> list[dict]:
    import random
    if target_size < len(REAL_ANCHOR_ENTRIES):
        raise ValueError(f"target_size must be >= {len(REAL_ANCHOR_ENTRIES)}")
    rng = random.Random(seed)
    corpus = []
    for eid, kind, name, families, desc in REAL_ANCHOR_ENTRIES:
        corpus.append({"id": eid, "kind": kind, "name": name, "attack_families": families,
                        "description": desc, "source_url": "(see real_corpus.py)"})
    for i in range(target_size - len(REAL_ANCHOR_ENTRIES)):
        corpus.append(_distractor_entry(i, rng))
    random.Random(seed + 1).shuffle(corpus)
    return corpus


def run_trial(strategy, client, model_key: str, corpus_by_id: dict, query_text: str,
              ground_truth_id, k: int) -> dict:
    call = strategy.query(query_text, ground_truth_id or "__NONE__", k=k)
    shown_entries = [corpus_by_id[i] for i in call.retrieved_ids if i in corpus_by_id]
    user_prompt = build_user_prompt(shown_entries, query_text, entry_text)

    # Mock clients get ground truth out-of-band (never inserted into the
    # actual prompt text) so their self-test is meaningful without ever
    # risking leaking the answer into a real model's prompt -- see
    # llm_clients.py MockClient docstring.
    if hasattr(client, "generate_with_truth"):
        resp = client.generate_with_truth(SYSTEM_PROMPT, user_prompt, ground_truth_id, call.retrieved_ids)
    else:
        resp = client.generate(SYSTEM_PROMPT, user_prompt)
    parsed = parse_response(resp.text)

    cited_id = parsed["cited_id"]
    invented_id = bool(cited_id) and cited_id not in call.retrieved_ids
    correct_citation = (cited_id == ground_truth_id) if ground_truth_id is not None else None
    correctly_abstained = (cited_id is None) if ground_truth_id is None else None

    return {
        "model_key": model_key,
        "model": resp.model,
        "strategy": strategy.name,
        "query": query_text,
        "ground_truth_id": ground_truth_id or "",
        "shown_ids": "|".join(call.retrieved_ids),
        "cited_id": cited_id or "",
        "classification": parsed["classification"] or "",
        "justification": (parsed["justification"] or "").replace("\n", " "),
        "parse_error": parsed["parse_error"],
        "invented_id": invented_id,
        "correct_citation": correct_citation,
        "correctly_abstained": correctly_abstained,
        "is_holdout_abstention_trial": ground_truth_id is None,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
        "cost_usd": round(resp.cost_usd, 8),
        "latency_s": round(resp.latency_s, 4),
        "api_error": resp.error,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-size", type=int, default=15,
                     help="Corpus size (>=15; 15 = real anchors only, no synthetic padding). "
                          "Larger sizes cost more real API calls -- start small.")
    ap.add_argument("--k", type=int, default=5, help="Entries retrieved per RAG query.")
    ap.add_argument("--mock", action="store_true",
                     help="Run with MockClient (no network, no real model calls, no API keys). "
                          "Verifies the harness only -- output is NOT real experimental data.")
    ap.add_argument("--n-queries", type=int, default=None,
                     help="Optional cap on number of main queries (of 45) for a cheap smoke test.")
    ap.add_argument("--out", default="llm_results.csv")
    args = ap.parse_args()

    model_keys = ["mock-claude", "mock-gpt4o-mini"] if args.mock else ["claude", "gpt4o-mini"]

    corpus = build_real_corpus(args.corpus_size)
    corpus_by_id = {e["id"]: e for e in corpus}

    main_queries = list(REAL_ANCHOR_QUERIES_ALL)
    if args.n_queries is not None:
        main_queries = main_queries[: args.n_queries]
    all_queries = main_queries + HELD_OUT_ABSTENTION_QUERIES

    print(f"{'MOCK ' if args.mock else ''}run: corpus_size={len(corpus)}, "
          f"models={model_keys}, main_queries={len(main_queries)}, "
          f"holdout_abstention_queries={len(HELD_OUT_ABSTENTION_QUERIES)}, k={args.k}")
    if args.mock:
        print("*** MOCK MODE: no real API calls are being made. Results are fabricated "
              "for harness verification only and must not be used in the paper. ***")

    rows = []
    for model_key in model_keys:
        try:
            client = get_client(model_key)
        except RuntimeError as e:
            print(f"\nERROR setting up client '{model_key}': {e}", file=sys.stderr)
            print("Skipping this model. Use --mock to test the harness without API keys.",
                  file=sys.stderr)
            continue

        for strategy_cls in (FullCorpusStrategy, RAGStrategy):
            if strategy_cls is FullCorpusStrategy:
                strat = strategy_cls(corpus)
            else:
                strat = strategy_cls(corpus, embedder_kind="tfidf")
            strat.build_index()

            n_errors = 0
            for i, (q_text, gt_id) in enumerate(all_queries):
                row = run_trial(strat, client, model_key, corpus_by_id, q_text, gt_id, args.k)
                rows.append(row)
                if row["api_error"]:
                    n_errors += 1
                if (i + 1) % 10 == 0 or (i + 1) == len(all_queries):
                    print(f"  {model_key:16s} {strat.name:12s} {i + 1:3d}/{len(all_queries)} "
                          f"trials done ({n_errors} API errors so far)")

    if not rows:
        print("\nNo trials were run (no client could be set up). Nothing written.", file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} trial rows to {args.out}")
    if args.mock:
        print("Reminder: this file contains MOCK data (model column starts with 'mock-'). "
              "Run again without --mock and with real API keys for paper-usable results.")


if __name__ == "__main__":
    main()
