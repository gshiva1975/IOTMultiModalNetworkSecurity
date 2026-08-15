"""
visualization_variants.py -- render the SAME underlying traffic window into
six different image representations. This is the new project's core
technical contribution: the original networksecurity/ project rendered every
window as one fixed four-panel composite; this project renders every sampled
window six different ways and treats the representation as the independent
variable (see config.REPRESENTATIONS and paper/paper.tex).

All six encode the identical feature set (config.REP_FEATURES: packet rate,
5 TCP-flag fractions, 6 protocol-mix fractions, avg/std packet size) over the
same GROUP_SIZE-row window -- only the VISUAL ENCODING differs. The first
five are ordered deliberately from richest annotation to none; the sixth
(rgb_stack) is a genuinely different axis -- 3-dimensional rather than 2D --
rather than a further step along the annotation gradient:

  four_panel        -- the original composite: 4 labeled subplots, legends,
                        a title. (baseline / positive control)
  single_line       -- one labeled line plot, ONE channel only (packet rate).
                        Tests whether reducing channels (not just annotation)
                        changes citation behavior.
  heatmap           -- features x time heatmap with row labels + colorbar.
                        Same information as four_panel, denser encoding,
                        still fully annotated.
  recurrence_plot   -- a time x time pairwise-similarity image (a standard
                        time-series-to-image technique). NO axis labels,
                        legend, or colorbar -- structure only.
  grayscale_matrix  -- a raw numeric-to-pixel grayscale image (mirrors the
                        "traffic-as-bytes" encoding used in several CNN-based
                        network-IDS papers). NO annotation of any kind.
                        2D (height x width, 1 channel).
  rgb_stack         -- a 3-channel (R/G/B) numeric-to-pixel image: three
                        feature groups (flags, protocol mix, packet size)
                        stacked as color channels, the way a photograph
                        stacks 3 grayscale channels. NO annotation. The only
                        representation here that is 3D (height x width x 3)
                        rather than a 2D grid, mirroring multi-channel
                        CNN-IDS encodings (e.g. CiNeT).

sample_windows() and distribute_across_files() are copied unchanged from
../../networksecurity/src/networksecurity/visualization.py -- window
selection doesn't depend on representation.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import FLAG_COLS, PROTO_COLS, REP_FEATURES, GROUP_SIZE, RNG, DEFAULT_OUT_DIR, REPRESENTATIONS

_EPS = 1e-9


def sample_windows(df, n_samples, group_size, rng):
    max_start = len(df) - group_size
    if max_start <= 0:
        return []
    starts = rng.choice(max_start, size=min(n_samples, max_start), replace=False)
    return sorted(starts.tolist())


def distribute_across_files(total, n_files):
    """Split `total` samples as evenly as possible across n_files files."""
    base, remainder = divmod(total, n_files)
    return [base + (1 if i < remainder else 0) for i in range(n_files)]


def _minmax(mat, axis):
    """Column- or row-wise min-max normalize to [0, 1], with an epsilon to
    avoid divide-by-zero for a constant feature within a window."""
    lo = mat.min(axis=axis, keepdims=True)
    hi = mat.max(axis=axis, keepdims=True)
    return (mat - lo) / (hi - lo + _EPS)


def render_four_panel(df_slice, class_name, sample_id):
    """The original networksecurity/ composite, unchanged."""
    fig, axes = plt.subplots(4, 1, figsize=(7, 8), sharex=True)
    x = np.arange(len(df_slice))
    axes[0].plot(x, df_slice["Rate"].to_numpy(), color="#c53030", linewidth=1.2)
    axes[0].set_ylabel("Rate (pkt/s)")
    axes[0].set_title(f"{class_name} — sample {sample_id} (four_panel)", fontsize=10)
    for c in FLAG_COLS:
        axes[1].plot(x, df_slice[c].to_numpy(), linewidth=1.0, label=c.replace("_flag_number", ""))
    axes[1].set_ylabel("TCP flag frac.")
    axes[1].legend(fontsize=6, ncol=5, loc="upper right")
    bottom = np.zeros(len(df_slice))
    colors = plt.cm.tab10(np.linspace(0, 1, len(PROTO_COLS)))
    for c, col in zip(PROTO_COLS, colors):
        vals = df_slice[c].to_numpy()
        axes[2].fill_between(x, bottom, bottom + vals, color=col, alpha=0.8, label=c)
        bottom += vals
    axes[2].set_ylabel("Protocol mix")
    axes[2].legend(fontsize=6, ncol=6, loc="upper right")
    axes[3].plot(x, df_slice["AVG"].to_numpy(), color="#2b6cb0", label="avg pkt size")
    axes[3].plot(x, df_slice["Std"].to_numpy(), color="#805ad5", label="std pkt size")
    axes[3].set_ylabel("Packet size")
    axes[3].set_xlabel("Window index (each = ~100 pkts)")
    axes[3].legend(fontsize=6, loc="upper right")
    fig.tight_layout()
    return fig


def render_single_line(df_slice, class_name, sample_id):
    """One labeled line plot, packet rate only -- fewer channels than every
    other representation, to isolate 'less information' from 'less
    annotation'."""
    fig, ax = plt.subplots(figsize=(6, 3))
    x = np.arange(len(df_slice))
    ax.plot(x, df_slice["Rate"].to_numpy(), color="#c53030", linewidth=1.4)
    ax.set_ylabel("Rate (pkt/s)")
    ax.set_xlabel("Window index (each = ~100 pkts)")
    ax.set_title(f"{class_name} — sample {sample_id} (single_line)", fontsize=9)
    fig.tight_layout()
    return fig


def render_heatmap(df_slice, class_name, sample_id):
    """features x time heatmap. Same REP_FEATURES as four_panel, same
    information content, denser/fully-annotated encoding."""
    mat = df_slice[REP_FEATURES].to_numpy().T  # (n_features, n_windows)
    mat = _minmax(mat, axis=1)  # normalize each feature (row) independently
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(mat, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_yticks(range(len(REP_FEATURES)))
    ax.set_yticklabels(REP_FEATURES, fontsize=6)
    ax.set_xlabel("Window index (each = ~100 pkts)")
    ax.set_title(f"{class_name} — sample {sample_id} (heatmap)", fontsize=9)
    fig.colorbar(im, ax=ax, label="normalized value", fraction=0.03, pad=0.02)
    fig.tight_layout()
    return fig


def render_recurrence_plot(df_slice, class_name, sample_id):
    """Time x time pairwise-distance image: pixel (i, j) = normalized
    Euclidean distance between window i's and window j's full REP_FEATURES
    vector (each feature independently min-max normalized first, so no
    single feature's scale dominates the distance). No axis labels, legend,
    or colorbar -- deliberately structure-only, per the representation
    gradient this study tests."""
    mat = df_slice[REP_FEATURES].to_numpy()  # (n_windows, n_features)
    mat = _minmax(mat, axis=0)  # normalize each feature (column) independently
    diffs = mat[:, None, :] - mat[None, :, :]
    dist = np.sqrt((diffs ** 2).sum(axis=-1))
    dist = dist / (dist.max() + _EPS)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.imshow(dist, cmap="gray_r", vmin=0, vmax=1)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout(pad=0)
    return fig


def render_grayscale_matrix(df_slice, class_name, sample_id):
    """Raw numeric-to-pixel grayscale image: row = window, column =
    REP_FEATURES entry (fixed order), pixel brightness = that feature's
    min-max normalized value in that window. No axis labels, legend, or
    colorbar -- mirrors the 'traffic-as-bytes' encoding used in several
    CNN-based network-IDS papers."""
    mat = df_slice[REP_FEATURES].to_numpy()  # (n_windows, n_features)
    mat = _minmax(mat, axis=0)  # normalize each feature (column) independently
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(mat, cmap="gray", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout(pad=0)
    return fig


# The three feature groups combined into the red/green/blue channels of
# render_rgb_stack(). Chosen semantically (flags vs. protocol mix vs. packet
# size) rather than by even split, so each channel carries one coherent
# signal type -- matches the "one feature group per convolutional input
# channel" convention used in several multi-channel CNN-IDS encodings.
_RGB_R_COLS = ["Rate"] + FLAG_COLS   # 6 columns
_RGB_G_COLS = PROTO_COLS              # 6 columns
_RGB_B_COLS = ["AVG", "Std"]          # 2 columns -- zero-padded to match width


def render_rgb_stack(df_slice, class_name, sample_id):
    """3-channel (red/green/blue) numeric-to-pixel image -- the only
    representation in this study that is genuinely 3-dimensional
    (height x width x channel) rather than a 2D grid rendered through a
    colormap. Red = rate + TCP flags, green = protocol mix, blue =
    avg/std packet size (zero-padded from 2 to 6 columns so all three
    channels share one width). Each channel is independently min-max
    normalized before being stacked, the same way a standard RGB photograph
    combines three separate grayscale channels. No axis labels, legend, or
    colorbar -- the direct network-traffic analogue of the multi-channel /
    bijective encodings used in several recent CNN-based intrusion-detection
    papers (e.g. CiNeT's network-to-image encoding)."""
    width = max(len(_RGB_R_COLS), len(_RGB_G_COLS), len(_RGB_B_COLS))

    def channel(cols):
        mat = df_slice[cols].to_numpy().astype(float)
        mat = _minmax(mat, axis=0)
        if mat.shape[1] < width:
            mat = np.concatenate([mat, np.zeros((mat.shape[0], width - mat.shape[1]))], axis=1)
        return mat

    rgb = np.stack([channel(_RGB_R_COLS), channel(_RGB_G_COLS), channel(_RGB_B_COLS)], axis=-1)
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(rgb, aspect="auto", vmin=0, vmax=1)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout(pad=0)
    return fig


RENDER_FUNCS = {
    "four_panel": render_four_panel,
    "single_line": render_single_line,
    "heatmap": render_heatmap,
    "recurrence_plot": render_recurrence_plot,
    "grayscale_matrix": render_grayscale_matrix,
    "rgb_stack": render_rgb_stack,
}


def build_visualizations(class_files, samples_per_class, out_dir=DEFAULT_OUT_DIR, representations=None):
    """class_files: {class_name: [csv paths]}. For every sampled window,
    renders EVERY representation in `representations` (default:
    config.REPRESENTATIONS) and writes one manifest row per
    (sample_id, representation) pair -- so the same window is compared
    across representations, not a fresh independent draw per representation.
    Loads one source file at a time (not all files for a class concatenated
    in memory), same as the original project."""
    representations = representations or REPRESENTATIONS
    manifest_rows = []
    for class_name, files in class_files.items():
        class_dir = os.path.join(out_dir, "viz", class_name)
        os.makedirs(class_dir, exist_ok=True)
        per_file_budget = distribute_across_files(samples_per_class, len(files))

        total_windows = 0
        total_rows_seen = 0
        sample_counter = 0
        for file_path, budget in zip(files, per_file_budget):
            if budget <= 0:
                continue
            df = pd.read_csv(file_path)
            total_rows_seen += len(df)
            starts = sample_windows(df, budget, GROUP_SIZE, RNG)
            for start in starts:
                df_slice = df.iloc[start:start + GROUP_SIZE]
                sample_id = f"{class_name}_{sample_counter:04d}"
                sample_counter += 1
                for rep in representations:
                    fig = RENDER_FUNCS[rep](df_slice, class_name, sample_id)
                    img_path = os.path.join(class_dir, f"{sample_id}__{rep}.png")
                    fig.savefig(img_path, dpi=120)
                    plt.close(fig)
                    manifest_rows.append({
                        "sample_id": sample_id, "true_class": class_name, "representation": rep,
                        "source_file": file_path, "row_start": int(start),
                        "row_end": int(start + GROUP_SIZE), "image_path": img_path,
                    })
                total_windows += 1
            del df  # free memory before loading the next part file

        print(f"  {class_name}: {total_windows} windows x {len(representations)} representations "
              f"from {len(files)} file(s), {total_rows_seen} rows seen")

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(os.path.join(out_dir, "viz", "manifest.csv"), index=False)
    return manifest
