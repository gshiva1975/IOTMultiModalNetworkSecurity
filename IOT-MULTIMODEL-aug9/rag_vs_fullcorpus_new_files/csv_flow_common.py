"""
csv_flow_common.py
-------------------
Shared constants/helpers for the CIC-IoT-2023 flow-feature citation-grounded
experiment (real dataset, real 39-feature CSV rows -- NOT the earlier
K3s/CVE synthetic-query task). Reuses the same 15-entry REAL_ANCHOR_ENTRIES
corpus from real_corpus.py as the grounding reference, because 19 of the 34
real CIC-IoT-2023 classes already have a directly-matching real CAPEC/CVE
entry in that corpus (verified below) -- no new corpus needed.

Ground-truth mapping is derived programmatically from each entry's
attack_families list (the same list already used and disclosed in
real_corpus.py), not hand-picked for this script, so it can't silently
drift out of sync with the anchor corpus.

Classes with NO matching real entry (15 of 34, including Benign_Final) are
legitimate abstention-expected trials: a correct model should cite nothing,
exactly like the existing HELD_OUT_ABSTENTION_QUERIES design in
llm_experiment.py. This is not a gap to be papered over -- it's disclosed
directly in the paper as the honest ground-truth coverage of a small,
verified real corpus.
"""

import os
import csv

from real_corpus import REAL_ANCHOR_ENTRIES

import os as _os
# Defaults to the real dataset location on your machine. Override with
# CIC_CSV_ROOT if you run this from somewhere else.
CSV_ROOT = _os.environ.get("CIC_CSV_ROOT", "/Users/gshiva/Documents/IOT-MULTIMODEL/CSV")

# All 39 feature columns, in the order they appear in the source CSVs
# (confirmed via `head -1` on a real file in this dataset).
FEATURE_COLUMNS = [
    "Header_Length", "Protocol Type", "Time_To_Live", "Rate",
    "fin_flag_number", "syn_flag_number", "rst_flag_number", "psh_flag_number",
    "ack_flag_number", "ece_flag_number", "cwr_flag_number",
    "ack_count", "syn_count", "fin_count", "rst_count",
    "HTTP", "HTTPS", "DNS", "Telnet", "SMTP", "SSH", "IRC", "TCP", "UDP",
    "DHCP", "ARP", "ICMP", "IGMP", "IPv", "LLC",
    "Tot sum", "Min", "Max", "AVG", "Std", "Tot size", "IAT", "Number", "Variance",
]


def list_classes() -> list:
    return sorted(
        d for d in os.listdir(CSV_ROOT)
        if os.path.isdir(os.path.join(CSV_ROOT, d))
    )


def class_files(cls: str) -> list:
    d = os.path.join(CSV_ROOT, cls)
    return sorted(
        os.path.join(d, f) for f in os.listdir(d) if f.endswith(".csv")
    )


def build_class_to_entry_id() -> dict:
    """
    class_name -> real corpus entry id, derived from REAL_ANCHOR_ENTRIES'
    attack_families lists (real_corpus.py), for every class that has one.
    A few classes (e.g. Mirai-udpplain) are listed under more than one real
    CVE's attack_families; last-entry-in-list wins deterministically. This
    is a disclosed simplification (multiple real CVEs are plausible causes
    for the same traffic class) -- see paper Limitations.
    """
    mapping = {}
    for eid, kind, name, families, desc in REAL_ANCHOR_ENTRIES:
        for fam in families:
            mapping[fam] = eid
    return mapping


CLASS_TO_ENTRY_ID = build_class_to_entry_id()


def serialize_row(values: dict) -> str:
    """
    Render one CSV row as the 'observed finding' text shown to the model.
    Deliberately literal (raw feature=value pairs, no interpretive
    paraphrase) so the model does the classification work itself rather
    than being handed an English description that already leaks the
    answer -- consistent with this project's no-answer-leakage discipline
    (see llm_clients.py MockClient docstring for the same principle applied
    to the mock harness).
    """
    parts = [f"{col}={values[col]}" for col in FEATURE_COLUMNS if col in values]
    return "Observed network flow, extracted feature vector: " + ", ".join(parts) + "."


def read_specific_rows(filepath: str, local_row_indices: set) -> dict:
    """
    Single pass over one CSV file, returning {local_row_index: {col: val}}
    for exactly the requested 0-based data-row indices (row 0 = first row
    after the header). Avoids loading full multi-hundred-thousand-row files
    into memory at once.
    """
    wanted = set(local_row_indices)
    out = {}
    if not wanted:
        return out
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i in wanted:
                out[i] = row
                wanted.discard(i)
                if not wanted:
                    break
    return out
