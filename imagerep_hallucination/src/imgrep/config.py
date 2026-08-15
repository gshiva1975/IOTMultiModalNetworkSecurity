"""
config.py -- central constants for the imgrep (image-representation) pipeline.

This project is a sibling of ../../networksecurity/, reusing its corpus,
grading, and data-loading logic unchanged. The independent variable here is
NOT prompting condition (that's held fixed at rag_grounded, the condition
the original study found generally best for citation quality) -- it's the
IMAGE REPRESENTATION of the same underlying traffic window. See
visualization_variants.py for the five encodings and paper/paper.tex for
the motivating question.

Nothing here calls the network or reads the filesystem; it's pure
configuration, safe to import from anywhere (including tests) without side
effects.
"""

import numpy as np

# Same fixed seed as the original project, so which traffic windows get
# sampled is deterministic across runs, all else equal.
RNG = np.random.default_rng(7)

DEFAULT_DATA_DIR = "data/CSV"
DEFAULT_OUT_DIR = "results"

BENIGN_CLASS_NAME = "Benign"

# Rows per rendered traffic-visualization window (~100 packets/window in the
# underlying CIC-IoT-2023 feature aggregation). Same as the original project
# so windows are directly comparable.
GROUP_SIZE = 30

MODEL = "claude-sonnet-5"

# REAL, OBSERVED figure (not a proxy) -- from the actual n=1,020 Claude
# Sonnet 5 confirmatory run against this project's manifest: $20 total /
# 1,020 calls = $0.0196078.../call. This superseded an earlier proxy
# estimate of $0.0355/call (which had applied the gpt-4o-mini pilot's token
# count to Sonnet pricing) -- the real run came in lower, most likely
# because Sonnet's actual response length and/or DashScope-independent
# tokenization differs from the cross-model proxy assumption. Do not reuse
# the original networksecurity project's $0.0061/call figure here either --
# that one was averaged across THREE prompting conditions (only one of
# which, rag-grounded, stuffs the full reference corpus into the prompt),
# while this project uses rag-grounded on EVERY call (see FIXED_CONDITION
# above), so every call pays the expensive, full-corpus-stuffed cost.
EMPIRICAL_COST_PER_CALL = 20 / 1020  # == 0.0196078..., real: $20 for 1,020 calls

FLAG_COLS = ["fin_flag_number", "syn_flag_number", "rst_flag_number", "psh_flag_number", "ack_flag_number"]
PROTO_COLS = ["TCP", "UDP", "HTTP", "HTTPS", "ICMP", "DNS"]
FEATURES = ["Rate"] + FLAG_COLS + ["TCP", "UDP", "HTTP", "HTTPS", "AVG", "Std", "IAT"]

# The channels shown in EVERY representation below (same underlying data,
# five different visual encodings of it) -- deliberately excludes IAT so
# every representation encodes an identical information set and only the
# ENCODING varies, not the underlying data available to the model.
REP_FEATURES = ["Rate"] + FLAG_COLS + PROTO_COLS + ["AVG", "Std"]

# The new independent variable. The first five are ordered deliberately from
# richest visual annotation (axis labels, legends, a titled multi-panel
# layout) to zero annotation (a bare numeric-to-pixel grayscale image); the
# sixth (rgb_stack) is a genuinely 3-dimensional encoding (height x width x
# 3 color channels) rather than a further step along that 2D gradient -- see
# visualization_variants.py docstring for what each one is and why it's
# there.
REPRESENTATIONS = [
    "four_panel",        # original composite: 4 labeled/legended subplots
    "single_line",       # single labeled line plot, one channel only (Rate)
    "heatmap",            # features x time heatmap, axis labels + colorbar
    "recurrence_plot",    # time x time similarity-structure image, unlabeled
    "grayscale_matrix",   # raw numeric-to-pixel grayscale image, unlabeled (2D, 1 channel)
    "rgb_stack",          # 3 feature groups as R/G/B channels (3D, 3 channels), unlabeled
]

# Prompting condition is held fixed at RAG-grounded for every call in this
# study -- see prompting.py.
FIXED_CONDITION = "rag_grounded"

RESULT_COLUMNS = [
    "sample_id", "true_class", "representation", "classification", "reference_id",
    "justification", "input_tokens", "output_tokens", "raw_response",
]
