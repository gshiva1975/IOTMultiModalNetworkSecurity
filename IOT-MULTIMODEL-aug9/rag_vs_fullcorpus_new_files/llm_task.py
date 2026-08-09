"""
llm_task.py
------------
Prompt construction and response parsing for the citation-grounded
classification task, shared by both models (Claude, GPT-4o-mini) and both
context-construction strategies (full-corpus, RAG) so the only thing that
differs between conditions is what's IN the context block -- the
instructions, output format, and parsing logic are held fixed, per the
paired-comparison design in the companion paper.

Task (same definition as claude_vs_gptmini_paper/paper.tex Section 4.1):
given a natural-language finding description and a context block of
candidate grounding entries, the model must return a cited entry id drawn
ONLY from the ids shown, or explicitly abstain if none apply.
"""

import json
import re

SYSTEM_PROMPT = (
    "You are a security-triage assistant. You will be shown a set of "
    "reference entries (each with an ID, name, and description) and a "
    "single observed finding. Your job is to (1) classify the finding in "
    "one short phrase, (2) cite the ID of the reference entry that matches "
    "it, drawing that ID ONLY from the entries shown to you -- never invent "
    "an ID that was not shown -- or set cited_id to null if none of the "
    "shown entries actually match, and (3) give a one-sentence "
    "justification that is consistent with the cited entry's actual "
    "description. Respond with ONLY a JSON object of the form "
    '{"classification": "...", "cited_id": "..." or null, '
    '"justification": "..."}. No other text.'
)


def build_user_prompt(context_entries: list[dict], query_text: str, entry_text_fn) -> str:
    """
    context_entries: list of corpus entry dicts (the ones actually shown --
    i.e., CallResult.retrieved_ids resolved back to full entries).
    entry_text_fn: the same entry_text() function used to build the
    retrieval index, so the model sees exactly the same serialization the
    retriever scored against.
    """
    lines = ["Reference entries shown to you:"]
    shown_ids = []
    for e in context_entries:
        lines.append(f"- ID: {e['id']} | {entry_text_fn(e)}")
        shown_ids.append(e["id"])
    lines.append("")
    lines.append(f"Observed finding: {query_text}")
    lines.append("")
    lines.append("Respond with the JSON object only.")
    # Machine-readable debug markers, used ONLY by MockClient (see
    # llm_clients.py) to fabricate a plausible mock response without a real
    # model call. Real models are instructed to ignore anything that isn't
    # part of the task and will not see these as meaningful -- they are
    # inert to Claude/GPT-4o-mini but let the mock harness self-check
    # against the same ground truth without a second code path.
    lines.append(f"[[SHOWN_IDS:{','.join(shown_ids)}]]")
    return "\n".join(lines)


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_response(raw_text: str) -> dict:
    """
    Returns {"classification": str|None, "cited_id": str|None,
    "justification": str|None, "parse_error": bool}.
    A parse_error is itself a data point worth keeping (a model that can't
    even follow the output format is a separate failure mode from citation
    accuracy) rather than being silently dropped.
    """
    match = _JSON_BLOCK_RE.search(raw_text or "")
    if not match:
        return {"classification": None, "cited_id": None, "justification": None, "parse_error": True}
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"classification": None, "cited_id": None, "justification": None, "parse_error": True}
    return {
        "classification": obj.get("classification"),
        "cited_id": obj.get("cited_id"),
        "justification": obj.get("justification"),
        "parse_error": False,
    }
