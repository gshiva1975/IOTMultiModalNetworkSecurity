# imagerep_hallucination

Does the image representation of network traffic change how much a multimodal LLM hallucinates its
citations? A sibling project to `../networksecurity/`, which studied *prompting condition*
(naive / text-grounded / RAG-grounded) as the independent variable at a fixed image representation.
This project holds prompting condition fixed at **RAG-grounded** (the condition the original study
found best for citation quality) and instead varies the **image representation** — six different
ways of drawing the exact same underlying traffic window, from a fully labeled four-panel chart,
through a raw unannotated grayscale matrix, to a genuinely 3-dimensional (height x width x 3-channel)
RGB-stack encoding. See `paper/paper.tex` for the full motivation, related work, and methodology; the
sections below are about running the code.

## What's reused vs. new

Reused byte-for-byte from `../networksecurity/src/networksecurity/`: `corpus.py` (the hand-verified
CAPEC/CVE reference corpus) and `data_loader.py` (class/file discovery). `grading.py` is reused with
only a cosmetic change (groups by "representation" instead of "condition" — the underlying
`wilson_ci()` and `grade_citation()` logic is untouched). Everything else is new:

- `src/imgrep/visualization_variants.py` — the six image-representation renderers (the core new
  contribution; see the module docstring and `paper/paper.tex` Section 3.2 for what each one is).
- `src/imgrep/prompting.py` — a single fixed RAG-grounded prompt, with a per-representation caption
  swapped in (necessary for the two representations that carry no in-image labels at all).
- `src/imgrep/claude_client.py` / `src/imgrep/openai_client.py` — the same resumable-checkpoint
  harness pattern as the original project, adapted to loop over `(sample_id, representation)` pairs
  instead of `(sample_id, condition)` pairs.
- `scripts/run_pipeline.py` / `scripts/run_pipeline_gpt4o.py` — CLI entry points.

## Quick start

```bash
cd imagerep_hallucination
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or copy .env.example to .env and fill it in

# Point --data-dir at a folder laid out as one subfolder per class, each full of CSV traffic
# files -- same layout as ../networksecurity/data/CSV/ (see "Data layout" below). If you already
# have that dataset downloaded for the original project, just point --data-dir at it directly;
# nothing needs to be copied.
python3 scripts/run_pipeline.py --data-dir data/CSV --list-classes            # free, no API call
python3 scripts/run_pipeline.py --data-dir data/CSV --skip-llm                # render images only, no cost
python3 scripts/run_pipeline.py --data-dir data/CSV --limit 3 --samples-per-class 3 --yes  # cheap pilot
```

`--limit` and `--samples-per-class` count **windows (samples)**, not manifest rows — each window
gets rendered into all 6 representations, so `--limit 3` is `3 windows x 6 representations = 18`
Claude calls per class, not 3. Run `--skip-llm` first if you just want to inspect the rendered
images before spending anything.

### Example: cheap two-class pilot

```bash
python3 scripts/run_pipeline.py --data-dir data/CSV \
    --classes Benign,DDoS-TCP_Flood --limit 5 --samples-per-class 5 --yes
```

10 windows total (5/class) x 6 representations = 60 Claude API calls, ~$0.37 at the observed
~$0.0061/call rate from the original project's pilot (representation doesn't change token cost
materially — same image size, same fixed prompt length). Drop `--classes` to run every class
discovered under `--data-dir`.

### Restricting which representations run

```bash
python3 scripts/run_pipeline.py --data-dir data/CSV --representations four_panel,grayscale_matrix \
    --limit 10 --samples-per-class 10
```

Useful for a fast two-point comparison (richest vs. no annotation) before committing to the full
6-way run.

### Cost at full scale, by model

Following the original project's 34-class, 30-samples/class confirmatory design (6,120 calls for a
full run, 1,020 for a 5/class pilot). Claude Sonnet 5's figures are now REAL, observed numbers (the
n=1,020 confirmatory run actually cost $20.00 total — $0.0196/call — see `config.EMPIRICAL_COST_PER_CALL`).
The other three model rows are built from the real per-call token count (17,380 input + 78 output
tokens/call) observed on this project's own 600-call gpt-4o-mini pilot and carried across model
clients as a proxy — update the relevant `EST_INPUT_TOKENS_PER_CALL` constant in each client once
you have a real pilot data point for that specific model:

| Model | $/1M in, out | Full run (6,120 calls) | Pilot (1,020 calls) |
|---|---|---|---|
| Claude Sonnet 5 | $2.00 / $10.00 | ~$120 (confirmed real) | $20.00 (confirmed real) |
| Qwen-vl-max | $0.52 / $2.08 | ~$56 | ~$9 |
| GPT-4o-mini | $0.15 / $0.60 | ~$16 (confirmed real) | ~$3 |
| Qwen-vl-plus | $0.14 / $0.41 | ~$15 | ~$3 |

Claude Sonnet is still meaningfully more expensive here than in the original `networksecurity/`
project's own cost table — that project's $0.0061/call figure was averaged across three prompting
conditions, only one of which (rag-grounded) stuffs the full reference corpus into the prompt. This
project uses rag-grounded on *every* call (see `config.FIXED_CONDITION`), so every call pays the
expensive, full-corpus-stuffed cost, not a cheaper blended average — see the comment in `config.py`'s
`EMPIRICAL_COST_PER_CALL` for the full explanation. This is also why Qwen-vl-max can look more
expensive than gpt-4o-mini per call despite being far cheaper than Sonnet: gpt-4o-mini's own price
per token ($0.15/$0.60) is unusually low even by 2026 standards, undercutting Qwen-vl-max
($0.52/$2.08) on raw per-token price even though Qwen-vl-max is the more capable model in that pair.

Each script prints its own pre-run cost estimate (built from the constants above) before spending
anything, and pauses for confirmation unless `--yes` is passed.

## Cross-model comparison (GPT-4o-mini)

Run the Claude pipeline first (or with `--skip-llm` if you only want the images and manifest, not a
paid Claude run) to produce `viz/manifest.csv`, then:

```bash
pip install openai
export OPENAI_API_KEY=sk-...
python3 scripts/run_pipeline_gpt4o.py --out-dir results --probe          # 1 test call, sanity check
python3 scripts/run_pipeline_gpt4o.py --out-dir results --limit 5 --yes  # cheap pilot
python3 scripts/run_pipeline_gpt4o.py --out-dir results --limit 0 --yes  # full run
```

`--probe` always runs one test call first and prints the full response or full error diagnostics —
run this before any paid run, especially the first time on a new OpenAI account (catches
missing/invalid API keys, no billing method, or no access to the model before spending anything on
the full run).

## Using Qwen-VL instead of Claude Sonnet

Qwen-VL substitutes for Claude Sonnet as the "primary" model in this study — chosen specifically to
save cost (~$120 for a full run on Claude Sonnet 5, real observed cost, vs. ~$15 on the model used
here, see the cost table above). It's served through DashScope's OpenAI-compatible endpoint, so setup is nearly
identical to the GPT-4o-mini path above — same `openai` SDK, different base URL and key.

```bash
pip install openai
export DASHSCOPE_API_KEY=sk-...   # https://dashscope.console.aliyun.com/apiKey
python3 scripts/run_pipeline_qwen.py --out-dir results --probe          # 1 test call, sanity check
python3 scripts/run_pipeline_qwen.py --out-dir results --limit 5 --yes  # cheap pilot
python3 scripts/run_pipeline_qwen.py --out-dir results --limit 0 --yes  # full run
```

**Default model: `qwen-vl-plus`** ($0.14/$0.41 per 1M input/output tokens — the chosen model for
this study). `qwen-vl-max` is also available as a pricier, more capable alternative
($0.52/$2.08 per 1M tokens) if you want it for a specific run — pass `--model qwen-vl-max`. At the
per-call token estimate carried over from the gpt-4o-mini pilot (~17,380 in / ~78 out, since the
prompt shape is identical across model clients), a full 6,120-call run is roughly **~$15 with
qwen-vl-plus** or ~$56 with qwen-vl-max — update `EST_INPUT_TOKENS_PER_CALL`/
`EST_OUTPUT_TOKENS_PER_CALL` in `src/imgrep/qwen_client.py` once you have a real Qwen pilot data
point, the same way the GPT-4o-mini estimate was corrected after its first real run (see the note
in that file).

If you're using a different OpenAI-compatible Qwen provider (OpenRouter, Together.ai, Fireworks,
etc.) instead of DashScope directly, set `QWEN_BASE_URL` to that provider's base URL and
`QWEN_API_KEY` to its key — `qwen_client.py` doesn't hardcode DashScope, it just defaults to it.

Results land in a separate file, `harness_results_qwen.csv`, so they never collide with the Claude
or GPT-4o-mini result files, and can be compared side by side.

## Resume behavior

Both harnesses write results incrementally, one row per `(sample_id, representation)` API call. A
rerun with the *same* arguments automatically skips already-completed calls and retries only rows
that errored last time (rate limits, network drops, billing issues) — so an interruption never
re-spends money on work you already paid for. Pass `--no-resume` to force a clean run instead.

## Data layout

Same as `../networksecurity/`: one subfolder per class under `--data-dir`, each holding one or more
CSV part files (real CIC-IoT-2023 traffic-feature exports):

```
data/CSV/BenignTraffic/BenignTraffic.pcap.csv
data/CSV/DDoS-TCP_Flood/DDoS-TCP_Flood.pcap.csv
data/CSV/DDoS-SynonymousIP_Flood/DDoS-SynonymousIP_Flood.pcap.csv
data/CSV/DDoS-SynonymousIP_Flood/DDoS-SynonymousIP_Flood1.pcap.csv
...
```

`data/` is gitignored — this repo ships code only, not the dataset. Note: a tiny synthetic
`data/CSV/` (random numbers, not real traffic) may already be present from development smoke-testing
of the rendering code; delete it and point `--data-dir` at your real CIC-IoT-2023 export before
running anything you intend to use for the paper.

## Outputs (written to `--out-dir`, default `./results/`)

```
viz/<class>/<sample_id>__<representation>.png   -- the 6 renderings per sampled window
viz/manifest.csv                                 -- one row per (sample_id, representation)
harness_results.csv                              -- Claude's classifications + citations
harness_results_gpt4o.csv                        -- GPT-4o-mini's (separate file, same schema)
harness_results_qwen.csv                         -- Qwen-VL's (separate file, same schema)
summary.txt                                      -- accuracy + citation-quality tables, by representation
```

## Tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

Covers prompt construction (every representation gets a full corpus, the citation restriction, and
correct captioning for the two unlabeled representations) and response parsing. No API key needed —
these are the same pure, network-free unit tests the original project uses for its equivalent
modules.

## Filling in the paper's placeholder results

`paper/paper.tex` is a complete draft — introduction, related work, fully specified methodology,
declared hypotheses (H1/H2), and limitations — with the Results and Discussion sections marked
`\pending{...}` in red. Once a real run against CIC-IoT-2023 completes for both models:

1. Pull the "Classification accuracy by image representation" and "Citation quality by image
   representation" tables straight out of `results/summary.txt`.
2. Fill in Section 4 (Results) with those tables, one per model.
3. Fill in Section 5 (Discussion) by checking whether citation quality moves monotonically with the
   annotation gradient (four_panel → single_line/heatmap → recurrence_plot/grayscale_matrix) — that's
   the H1-vs-H2 test the paper sets up.
4. Update the Declarations section (Authors' contributions, data/code availability link) and remove
   the remaining `\pending{}` markers.
