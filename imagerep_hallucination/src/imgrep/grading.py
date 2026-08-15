"""
grading.py -- statistical scoring and citation-quality grading.

Ported unchanged from ../../networksecurity/src/networksecurity/grading.py
except for the groupby axis: the original project's independent variable was
prompting *condition*; this project's is image *representation*, so
score_and_summarize() below groups by a "representation" column instead of
"condition". wilson_ci() and grade_citation() are byte-for-byte identical --
the citation-quality rubric doesn't depend on which axis is being compared.

wilson_ci() is used everywhere a percentage is reported in this project,
instead of a plain successes/n ratio -- it's much better calibrated than a
normal approximation at small n.

grade_citation() implements the citation-quality rubric: given a model's
cited reference_id and the true class, decide whether that citation is a
real, correctly-matched reference; a real but too-broad/generic one; a real
ID describing the wrong attack family; no citation at all; or an
unverified ID not yet checked against MITRE/NVD.
"""

import os

from .corpus import CVE_CORPUS, known_reference_map, generic_ids, wrong_family_ids


def wilson_ci(successes, n, z=1.96):
    """Wilson score interval for a binomial proportion. Returns
    (point_estimate, lo, hi) as fractions in [0, 1]."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5)) / denom
    return (p, max(0.0, center - half), min(1.0, center + half))


def fmt_ci(successes, n):
    p, lo, hi = wilson_ci(successes, n)
    return f"{p*100:.1f}% [{lo*100:.1f}-{hi*100:.1f}%] (n={n})"


def grade_citation(true_class, reference_id, benign_class):
    """Grade a single citation. Returns one of: n/a-benign, no-citation,
    real-and-correct, real-but-generic, real-but-wrong-family, or an
    UNVERIFIED-prefixed string for IDs not in the corpus at all."""
    if true_class == benign_class:
        return "n/a-benign"
    ref = str(reference_id).strip()
    if ref.upper() in ("N/A", "NAN", "NONE", ""):
        return "no-citation"
    known_refs = known_reference_map()
    if ref in wrong_family_ids():
        return "real-but-wrong-family"
    if ref in generic_ids():
        return "real-but-generic"
    if ref not in known_refs:
        return "UNVERIFIED (not yet checked against MITRE/NVD -- verify manually before citing in a paper)"
    if true_class in known_refs[ref]:
        return "real-and-correct"
    return "real-but-wrong-family"


def score_and_summarize(harness_results, benign_class, out_dir):
    """Prints (and returns as a list of lines, also written to summary.txt)
    accuracy and citation-quality tables broken out by image REPRESENTATION
    (this project's independent variable) instead of by prompting condition.
    No non-LLM baseline detectors here -- those don't have a representation
    axis to compare against, so this study doesn't run them (see the
    original networksecurity/ project for that comparison)."""
    lines = []

    def log(s=""):
        print(s)
        lines.append(s)

    if harness_results is not None:
        harness_results = harness_results.copy()
        harness_results["correct"] = (harness_results["classification"].str.strip()
                                       == harness_results["true_class"].str.strip())
        log("=== Classification accuracy by image representation (Wilson 95% CI) ===")
        for rep, g in harness_results.groupby("representation"):
            log(f"  {rep:>18}: {fmt_ci(int(g['correct'].sum()), len(g))}")

        harness_results["citation_grade"] = harness_results.apply(
            lambda r: grade_citation(r["true_class"], r["reference_id"], benign_class), axis=1)
        log("\n=== Citation quality by image representation (counts, and 95% CI on "
            "'real-and-correct' rate among attack samples) ===")
        for rep, g in harness_results.groupby("representation"):
            log(f"\n  {rep}:")
            log("  " + str(g["citation_grade"].value_counts()).replace("\n", "\n  "))
            attack_g = g[g["true_class"] != benign_class]
            n_attack = len(attack_g)
            n_correct = int((attack_g["citation_grade"] == "real-and-correct").sum())
            n_unverified = int(attack_g["citation_grade"].str.startswith("UNVERIFIED").sum())
            log(f"  -> real-and-correct rate among attack samples: {fmt_ci(n_correct, n_attack)}")
            if n_unverified:
                log(f"  -> WARNING: {n_unverified} citation(s) reference an ID not in the "
                    f"verified corpus -- check these against capec.mitre.org/nvd.nist.gov "
                    f"before treating them as fabricated OR as correct.")

    with open(os.path.join(out_dir, "summary.txt"), "w") as f:
        f.write("\n".join(lines))
    return lines
