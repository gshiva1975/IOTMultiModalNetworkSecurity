"""Unit tests for prompt construction and response parsing. No network needed."""

import pytest

from imgrep.prompting import build_prompt, parse_response, response_format, REPRESENTATION_DESCRIPTIONS
from imgrep.corpus import CVE_CORPUS
from imgrep.config import REPRESENTATIONS

CLASS_NAMES = ["Benign", "DDoS-TCP_Flood", "XSS"]


def test_every_representation_has_a_description():
    for rep in REPRESENTATIONS:
        assert rep in REPRESENTATION_DESCRIPTIONS


def test_every_representation_prompt_contains_full_corpus():
    # Every representation is RAG-grounded -- the corpus must be fully
    # serialized into every prompt regardless of representation.
    for rep in REPRESENTATIONS:
        p = build_prompt(rep, CLASS_NAMES)
        for entry in CVE_CORPUS["capec_entries"]:
            assert entry["capec_id"] in p, f"{rep}: missing {entry['capec_id']}"


def test_every_representation_prompt_restricts_citation():
    for rep in REPRESENTATIONS:
        p = build_prompt(rep, CLASS_NAMES)
        assert "ONLY a reference ID from the database above" in p


def test_unannotated_representations_say_so_in_the_prompt():
    # recurrence_plot, grayscale_matrix, and rgb_stack have no axis
    # labels/legend/colorbar in the actual image -- the prompt's description
    # must say that explicitly, since it's the model's only source of that
    # information.
    for rep in ("recurrence_plot", "grayscale_matrix", "rgb_stack"):
        p = build_prompt(rep, CLASS_NAMES)
        assert "NO axis labels" in p


def test_representation_prompts_differ_only_in_context_not_instructions():
    # The classify/cite instructions and response format must be byte-identical
    # across representations -- only the image-context description should vary.
    prompts = {rep: build_prompt(rep, CLASS_NAMES) for rep in REPRESENTATIONS}
    for rep, p in prompts.items():
        assert "Classify this traffic. Cite ONLY a reference ID from the database above" in p
        assert response_format(CLASS_NAMES) in p


def test_unknown_representation_raises():
    with pytest.raises(ValueError):
        build_prompt("not_a_real_representation", CLASS_NAMES)


def test_parse_response_roundtrip():
    text = (
        "CLASSIFICATION: DDoS-TCP_Flood\n"
        "REFERENCE_ID: CAPEC-482\n"
        "JUSTIFICATION: Rate spikes with SYN flags match a TCP flood signature."
    )
    parsed = parse_response(text)
    assert parsed["classification"] == "DDoS-TCP_Flood"
    assert parsed["reference_id"] == "CAPEC-482"
    assert "TCP flood" in parsed["justification"]


def test_parse_response_handles_missing_fields():
    parsed = parse_response("CLASSIFICATION: Benign\n")
    assert parsed["classification"] == "Benign"
    assert parsed["reference_id"] is None
    assert parsed["justification"] is None
