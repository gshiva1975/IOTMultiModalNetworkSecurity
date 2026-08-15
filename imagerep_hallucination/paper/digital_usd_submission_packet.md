# Digital USD submission packet

Digital USD is USD's institutional repository (Digital Commons/Elsevier platform) — no editorial
gatekeeping like arXiv's endorsement system, just a basic eligibility check (current USD faculty,
staff, or student). Since this hasn't been published or peer-reviewed elsewhere, it goes in as a
**working paper**, which the platform explicitly supports (see FAQ: "previously-published... OR
research data... OR working papers" are all eligible content types).

## Where to submit

**Collection:** School of Engineering: Faculty Scholarship
**Submission link:** https://digital.sandiego.edu/cgi/ir_submit.cgi?context=engineering_facpub

This is the best-fit collection given the paper's engineering/CS/security content and G.S.S.'s
`@sandiego.edu` affiliation. If your actual departmental home is elsewhere (e.g., listed separately
from Engineering), use the matching collection from https://digital.sandiego.edu/submit_research.html
instead — the process is identical either way. If your department isn't listed at all, email
Digital Initiatives at digital@sandiego.edu to have it added first.

You'll need to log in with your USD credentials — that part has to be done by you directly, not by
me.

## Metadata to paste into the form

**Title:**
Does the Picture Matter? Image Representation as an Unstudied Variable in Citation-Grounded
Multimodal LLM Classification of IoT Network Traffic

**Authors:**
1. Gangadhar Singh Shiva — University of San Diego — gshiva@sandiego.edu (corresponding author)
2. Poonam Singh Umakanth — HPE Juniper Networking, Hewlett Packard Enterprise — poonam.singh5@gmail.com

**Document type:** Working Paper (or "Article" if the form doesn't offer a Working Paper option —
either is defensible since this hasn't been peer-reviewed yet)

**Date of this version:** August 2026

**Abstract** (plain text, LaTeX stripped):

> Prior work has shown that restricting a multimodal LLM's citation menu to a small, verified
> reference corpus (retrieval-augmented, or "RAG-grounded" prompting) measurably reduces citation
> hallucination when classifying IoT network traffic rendered as images, but that this effect can
> interact with classification accuracy in model-dependent ways. That work held the image
> representation fixed — a single four-panel composite chart (packet rate, TCP flag composition,
> protocol mix, packet-size statistics) — and varied only the prompting condition. This paper asks
> the complementary question: with prompting condition held fixed at RAG-grounded, does the visual
> encoding of the identical underlying traffic data change how much the model hallucinates its
> citations? We propose and implement a six-way image-representation comparison spanning a
> deliberate annotation gradient — from a fully labeled, legended four-panel chart, through a
> single-channel line plot and a features-by-time heatmap, to two representations with zero textual
> annotation (a pairwise-similarity recurrence plot and a raw numeric-to-pixel grayscale matrix) —
> plus a sixth representation along a genuinely different axis: a 3-channel (red/green/blue)
> numeric-to-pixel encoding that is 3-dimensional (height x width x channel) rather than a 2D grid
> rendered through a colormap, mirroring multi-channel CNN-based intrusion-detection encodings. All
> six hold constant the dataset (CIC-IoT-2023), the two models under test (Qwen-vl-plus and
> GPT-4o-mini), the citation corpus, the grading rubric, and the prompting condition. To our
> knowledge, no prior work has treated image-representation choice as an independent variable for
> citation hallucination specifically, as distinct from the adjacent (but different) literatures on
> time-series-to-image encoding for CNN-based intrusion detection and on vision-encoder-level causes
> of multimodal LLM hallucination. This paper specifies the full experimental design, releases
> working, resumable experiment code (six representation renderers, a fixed RAG-grounded prompting
> harness for three model APIs, and citation-grading infrastructure reused unchanged from the prior
> study), and reports results from a real, completed run against CIC-IoT-2023 (n=1,020 windows, 10
> classes, 6 representations, 6,120 calls per model). Both models show a sharp, non-monotonic split:
> three annotated representations (four_panel, single_line, heatmap) sustain 42-80% classification
> accuracy and 31-62% correct-citation rates, while the three unannotated/dimensionality-varying
> representations (recurrence_plot, grayscale_matrix, rgb_stack) collapse to chance-level accuracy
> (approximately 10%, matching the 10-class base rate) for both models. Critically, this collapse is
> not a retreat into honest uncertainty: both models continue to volunteer confident citations at low
> unannotated-representation no-citation rates (0-16%), and Qwen-vl-plus's collapse is total —
> identical classification and citation output on literally every one of the 3,060 unannotated-image
> calls, regardless of the true class. This is evidence for hallucination-through-fabrication (a
> variant of H1) rather than hallucination-through-elaboration (H2): stripping annotation does not
> make either model behave more conservatively, it makes both models guess with undiminished
> confidence.

**Suggested disciplines** (Digital Commons controlled taxonomy — pick the closest matches offered
in the form's picklist):
- Computer Sciences
- Artificial Intelligence and Robotics
- Information Security
- Digital Communications and Networking

**Suggested keywords:**
multimodal large language models, citation hallucination, retrieval-augmented generation, IoT
network security, intrusion detection, image representation, CIC-IoT-2023, Qwen-VL, GPT-4o-mini

**Comments/disciplines note field (if offered):** "Working paper; not yet peer-reviewed. Companion
to a separate submission on prompting-condition effects (RAG-grounded vs. text-grounded vs. naive)
in the same experimental framework."

## Files to upload

**Full text (required):** `paper.pdf` (already built, in this same folder)

**Additional Files (optional but recommended)** — Digital USD explicitly supports posting
supplementary data/code alongside the article (see FAQ: "Can I post related files... data sets...
alongside my published article?"). Good candidates from this project:
- `results_1020/harness_results_gpt4o.csv` (6,120 real rows)
- `results_1020/harness_results_qwen.csv` (6,120 real rows)
- `src/imgrep/` (rendering code, prompting harness, model clients, grading logic)
- `scripts/generate_figures.py`

If you want, I can zip the code + CSVs into one `supplementary_materials.zip` ready to attach as an
Additional File — just say so.

## Copyright note

Per Digital USD's FAQ: submitting does not require a copyright transfer, you keep it. Since this
hasn't been submitted or accepted anywhere else yet, there's no publisher agreement to check before
posting — that concern only applies to already-published work.
