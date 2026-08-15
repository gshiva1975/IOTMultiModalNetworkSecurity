"""
prompting.py -- builds the single, fixed RAG-grounded prompt sent to the
model for every call in this study.

Unlike the original networksecurity/ project (which varies prompting
condition: naive / cve_text_grounded / rag_grounded), THIS project holds
prompting condition fixed at rag_grounded -- the condition the original
confirmatory study found generally best for citation quality -- and varies
the IMAGE REPRESENTATION instead (see config.REPRESENTATIONS and
visualization_variants.py). Holding the prompt fixed and swapping only the
image is what makes representation the clean, isolated independent
variable.

Each representation gets its own short REPRESENTATION_DESCRIPTIONS entry
describing what the image shows and how to read it. This is necessary, not
optional: some representations (recurrence_plot, grayscale_matrix) carry NO
axis labels, legend, or colorbar by design (see visualization_variants.py),
so the model has no way to know what it's looking at without a caption. The
description says only what a caption on a real figure would say (what the
axes/encoding mean) -- it never states the classification or which
CAPEC/CVE ID to cite, so it isn't doing the model's job for it.
"""

from .corpus import CVE_CORPUS

REPRESENTATION_DESCRIPTIONS = {
    "four_panel": (
        "The image has four labeled panels for a sequence of consecutive traffic windows (each "
        "window summarizes ~100 packets): (1) packet rate over time, (2) TCP flag composition, "
        "(3) protocol mix (stacked area), and (4) average and standard deviation of packet size. "
        "Axis labels and a legend are shown on each panel."
    ),
    "single_line": (
        "The image is a single labeled line plot of packet rate (packets/sec) over a sequence of "
        "consecutive traffic windows (each window summarizes ~100 packets). No other traffic "
        "feature (TCP flags, protocol mix, packet size) is shown in this representation."
    ),
    "heatmap": (
        "The image is a heatmap. Each row is one traffic feature (packet rate, 5 TCP flag "
        "fractions, 6 protocol-mix fractions, and average/std packet size -- row labels are shown "
        "on the left) and each column is one consecutive traffic window (~100 packets each). "
        "Color encodes that feature's min-max normalized value in that window, per the colorbar."
    ),
    "recurrence_plot": (
        "The image is a recurrence plot: a square grayscale image with NO axis labels, legend, or "
        "colorbar. Pixel (i, j) encodes the normalized similarity between the full traffic-feature "
        "vector of window i and window j (darker = more similar / smaller distance, lighter = less "
        "similar). Both axes run over the same sequence of consecutive traffic windows (~100 "
        "packets each), in the same order, so the diagonal is always darkest (a window compared to "
        "itself)."
    ),
    "grayscale_matrix": (
        "The image is a raw grayscale matrix with NO axis labels, legend, or colorbar. Each row is "
        "one consecutive traffic window (~100 packets) and each column is one traffic feature "
        "(packet rate, 5 TCP flag fractions, 6 protocol-mix fractions, average/std packet size, in "
        "that fixed left-to-right order). Each pixel's brightness is that feature's min-max "
        "normalized value in that window (black = low, white = high). This is a direct "
        "numeric-to-pixel encoding with no chart annotation of any kind."
    ),
    "rgb_stack": (
        "The image is a 3-channel (red/green/blue) numeric-to-pixel image with NO axis labels, "
        "legend, or colorbar. Each row is one consecutive traffic window (~100 packets). The red "
        "channel encodes packet rate and the 5 TCP flag fractions, the green channel encodes the 6 "
        "protocol-mix fractions, and the blue channel encodes average/std packet size (padded with "
        "black to match the other channels' width). Each channel was independently min-max "
        "normalized before being combined into one color image, the same way a standard color "
        "photograph combines three separate grayscale channels -- so color in this image reflects "
        "which feature group is elevated, not a literal RGB photograph of anything."
    ),
}


def response_format(class_names):
    return (
        "Respond in EXACTLY this format, nothing else:\n"
        f"CLASSIFICATION: <one of: {', '.join(class_names)}>\n"
        "REFERENCE_ID: <a CVE-YYYY-NNNNN or CAPEC-NNN ID you believe explains this traffic, or N/A>\n"
        "JUSTIFICATION: <2-4 sentences explaining your classification and, if applicable, why you "
        "cited that reference ID>"
    )


def build_prompt(representation, class_names):
    """Always RAG-grounded: the reference database is serialized into every
    prompt and the model is told to cite ONLY from it. Only the image-context
    description at the top varies, by representation."""
    context = REPRESENTATION_DESCRIPTIONS.get(representation)
    if context is None:
        raise ValueError(f"Unknown representation: {representation}")
    intro = f"You are analyzing a visualization of IoT network traffic captured from the CIC-IoT-2023 dataset. {context}"
    ref_text = "\n\n".join(f"[{e['capec_id']}] {e['name']}: {e['description']}"
                            for e in CVE_CORPUS["capec_entries"])
    note = ("" if CVE_CORPUS["capec_entries"] else
            "(No verified reference entries are available for this run's classes -- say N/A.)")
    fmt = response_format(class_names)
    return (f"{intro}\n\nReference database of known attack patterns:\n\n{ref_text}{note}\n\n"
            f"Classify this traffic. Cite ONLY a reference ID from the database above, or N/A if "
            f"none apply -- even if you recognize the traffic, do not cite anything not listed "
            f"here. {fmt}")


def parse_response(text):
    out = {"classification": None, "reference_id": None, "justification": None}
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("CLASSIFICATION:"):
            out["classification"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("REFERENCE_ID:"):
            out["reference_id"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("JUSTIFICATION:"):
            out["justification"] = line.split(":", 1)[1].strip()
    return out
