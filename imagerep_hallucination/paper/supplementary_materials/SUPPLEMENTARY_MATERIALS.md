# Supplementary Materials

Companion archive to: **"Does the Picture Matter? Image Representation as an Unstudied Variable in
Citation-Grounded Multimodal LLM Classification of IoT Network Traffic"** (G.S. Shiva, P.S. Umakanth,
2026).

## Contents

- `src/imgrep/` -- the six image-representation renderers (`visualization_variants.py`), the fixed
  RAG-grounded prompting harness (`prompting.py`), three model clients (`claude_client.py`,
  `openai_client.py`, `qwen_client.py`), the citation corpus (`corpus.py`), and the grading rubric
  (`grading.py`, Wilson 95% CI + citation-quality classification).
- `scripts/` -- CLI entry points to reproduce the pipeline end to end (`run_pipeline.py`,
  `run_pipeline_gpt4o.py`, `run_pipeline_qwen.py`) and the figure-generation script used to build
  every figure in the paper directly from the result CSVs (`generate_figures.py`).
- `tests/` -- unit tests for prompt construction and response parsing (no API key required).
- `results/harness_results_gpt4o.csv` -- real GPT-4o-mini output, 6,120 rows (n=1,020 windows x 6
  representations), zero ERROR rows.
- `results/harness_results_qwen.csv` -- real Qwen-vl-plus output, 6,120 rows, zero ERROR rows.
- `results/manifest.csv` -- the (sample_id, representation) manifest tying every result row to its
  source traffic window and rendered image path, for full reproducibility of which underlying
  CIC-IoT-2023 data each classification was made on.
- `README.md` -- the project's own run instructions (setup, cost estimates, how to reproduce or
  extend the study).
- `requirements.txt` -- Python dependencies.

## Not included

The ~230MB of rendered PNG images themselves (`viz/`, 6,120 files) are not included here due to
size; three representative examples appear directly in the paper's Figure 1, and the full set can be
regenerated deterministically from the manifest and the original CIC-IoT-2023 dataset using
`scripts/run_pipeline.py --skip-llm` (same fixed random seed, `RNG = numpy.random.default_rng(7)`,
as documented in `src/imgrep/config.py`). The CIC-IoT-2023 dataset itself is a third-party public
benchmark (Neto et al., 2023) and is not redistributed here.

## Reproducing the results

See the main `README.md` in this archive for full setup instructions. In brief:

```
pip install -r requirements.txt
python3 scripts/run_pipeline.py --data-dir <path-to-CIC-IoT-2023> --skip-llm   # render images
export OPENAI_API_KEY=...      && python3 scripts/run_pipeline_gpt4o.py --limit 0 --yes
export DASHSCOPE_API_KEY=...   && python3 scripts/run_pipeline_qwen.py  --limit 0 --yes
python3 scripts/generate_figures.py --out-dir results
```
