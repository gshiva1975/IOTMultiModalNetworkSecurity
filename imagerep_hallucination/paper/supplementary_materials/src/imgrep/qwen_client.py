"""
qwen_client.py -- the Qwen-VL twin of claude_client.py / openai_client.py,
for running the identical representation-comparison experiment against
Alibaba's Qwen-VL multimodal models. Added so this project can substitute
Qwen for Claude Sonnet as the "primary" model, chosen specifically to save
cost (~$120 for a full 6,120-call run on Claude Sonnet 5, from a real
observed $20/1,020-call run, vs. ~$15 on the default model here,
qwen-vl-plus -- see README's cost table) without
touching any other module -- prompting.py, corpus.py, grading.py, and the
manifest format are all shared unchanged across all three model clients.

Qwen-VL is served through DashScope's OpenAI-COMPATIBLE endpoint, so this
client is almost identical to openai_client.py: same `openai` Python SDK,
same chat.completions.create call shape, same retry/backoff and resumable-
checkpoint design -- the only real differences are the base_url, the API key
env var, the model names, and the pricing table.

Results are written to a SEPARATE file, harness_results_qwen.csv, so they
sit side by side with harness_results.csv (Claude) and
harness_results_gpt4o.csv (GPT-4o-mini) without ever colliding.

Setup (once):
    pip install openai   # yes, the OpenAI SDK -- DashScope speaks its protocol
    export DASHSCOPE_API_KEY=sk-...   # from https://dashscope.console.aliyun.com/apiKey
    (or export QWEN_API_KEY=... if that's what your provider calls it)

If you're using a different Qwen-VL provider (OpenRouter, Together.ai,
Fireworks, etc.) instead of DashScope directly, set QWEN_BASE_URL to that
provider's OpenAI-compatible base URL and QWEN_API_KEY to its key; this
client doesn't hardcode DashScope, it just defaults to it.
"""

import base64
import csv
import os
import re
import sys
import time

import pandas as pd

from .prompting import build_prompt, parse_response

RESULT_COLUMNS = [
    "sample_id", "true_class", "representation", "classification", "reference_id",
    "justification", "input_tokens", "output_tokens", "raw_response",
]

# DashScope's international OpenAI-compatible endpoint. Use
# https://dashscope.aliyuncs.com/compatible-mode/v1 instead if your account
# is a China-region DashScope account (set via QWEN_BASE_URL).
DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

DEFAULT_MODEL = "qwen-vl-plus"

# Pricing as of mid-2026 (per DashScope's published rates): qwen-vl-plus
# $0.14/$0.41 per 1M input/output tokens -- the chosen default for this
# project (cheapest usable option; ~$15 for a full 6,120-call run vs. ~$120
# for Claude Sonnet 5, real observed cost, see README's cost table). qwen-vl-max $0.52/$2.08 is
# the more capable, pricier alternative -- pass --model qwen-vl-max if you
# want it for a specific run.
COST_PER_1M = {
    "qwen-vl-max": (0.52, 2.08),
    "qwen-vl-plus": (0.14, 0.41),
}
# Reuse the same per-call token estimate observed empirically on this
# project's real gpt-4o-mini pilot (17,380 in / 78 out) as a starting
# estimate -- the prompt (full RAG corpus + one image) is identical across
# model clients, so this is a reasonable first guess. Qwen's own tokenizer
# will differ somewhat; update these once you have a real Qwen pilot data
# point, the same way openai_client.py's estimate was corrected after its
# first real run.
EST_INPUT_TOKENS_PER_CALL = 17380
EST_OUTPUT_TOKENS_PER_CALL = 78


def estimate_cost(n_calls, model):
    in_price, out_price = COST_PER_1M.get(model, COST_PER_1M[DEFAULT_MODEL])
    return n_calls * (EST_INPUT_TOKENS_PER_CALL / 1e6 * in_price
                       + EST_OUTPUT_TOKENS_PER_CALL / 1e6 * out_price)


def image_data_uri(path):
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def describe_exception(e):
    """Same diagnostic-surfacing helper as openai_client.py -- the OpenAI
    SDK's error shape is identical since DashScope speaks the same
    protocol."""
    parts = [f"{type(e).__name__}"]
    msg = str(e).strip()
    if msg:
        parts.append(msg)
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            status = getattr(resp, "status_code", None)
            body = getattr(resp, "text", "") or ""
            if status is not None:
                parts.append(f"HTTP {status}")
            if body.strip():
                parts.append(body.strip()[:500])
        except Exception:
            pass
    return " | ".join(p for p in parts if p)


def build_client():
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai")
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
    if not api_key:
        sys.exit("Set DASHSCOPE_API_KEY in your environment first "
                  "(https://dashscope.console.aliyun.com/apiKey), or QWEN_API_KEY "
                  "if you're using a different OpenAI-compatible Qwen provider.")
    base_url = os.environ.get("QWEN_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base_url)


_RETRY_AFTER_RE = re.compile(r"try again in ([\d.]+)(ms|s)\b", re.IGNORECASE)

_FATAL_ERROR_MARKERS = (
    "insufficient_quota", "credit_balance_exhausted", "invalid_api_key",
    "account_deactivated", "arrearage", "unauthorized",
)


class FatalAPIError(RuntimeError):
    pass


def _suggested_wait(e, attempt):
    """Same idea as openai_client.py: respect a provider-given retry hint if
    present, otherwise a capped exponential backoff."""
    msg = str(e)
    m = _RETRY_AFTER_RE.search(msg)
    if m:
        value, unit = float(m.group(1)), m.group(2).lower()
        wait = value / 1000.0 if unit == "ms" else value
        return round(wait + 0.25, 2)
    return min(30, 2 ** attempt * 3)


def call_qwen_model(client, model, prompt, img_uri, max_tokens=400, retries=8):
    """Call a Qwen-VL model via the OpenAI-compatible chat.completions API,
    with retry/backoff for transient rate-limit / server errors. Same call
    shape as call_openai_model() in openai_client.py -- DashScope's
    compatible-mode endpoint accepts the identical
    {"type": "image_url", "image_url": {"url": ...}} content block."""
    last_err = None
    for attempt in range(retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": img_uri}},
                    ],
                }],
                max_tokens=max_tokens,
            )
            return completion.choices[0].message.content, completion.usage
        except Exception as e:
            diag = describe_exception(e)
            if any(marker in diag.lower() for marker in _FATAL_ERROR_MARKERS):
                raise FatalAPIError(
                    f"Non-retryable account error calling {model}: {diag}\n"
                    f"    This will not resolve by waiting -- fix the account issue "
                    f"(e.g. add DashScope billing credits) then re-run the script; "
                    f"already-completed calls are preserved and will be skipped.")
            last_err = e
            wait = _suggested_wait(e, attempt)
            print(f"    (retry {attempt + 1}/{retries} after error: {diag}; waiting {wait}s)")
            time.sleep(wait)
    raise RuntimeError(f"Exhausted retries calling {model}: {describe_exception(last_err)}")


def load_resumable_results(path):
    """Same resume semantics as claude_client.py / openai_client.py."""
    if not os.path.isfile(path):
        return [], set()
    existing = pd.read_csv(path)
    kept_rows, done_keys = [], set()
    for r in existing.to_dict("records"):
        cls = str(r.get("classification", "")).strip()
        if cls and cls.upper() not in ("ERROR", "NAN", ""):
            kept_rows.append(r)
            done_keys.add((r["sample_id"], r["representation"]))
    return kept_rows, done_keys


def _apply_limit(manifest, limit):
    if limit <= 0:
        return manifest
    keep_ids = (manifest[["sample_id", "true_class"]].drop_duplicates()
                .groupby("true_class", group_keys=False).head(limit)["sample_id"])
    return manifest[manifest["sample_id"].isin(keep_ids)]


def probe(manifest, class_names, model):
    """Make ONE test call (first manifest row) and print the full response
    or full error diagnostics, then return. Always run this before a full
    (paid) run."""
    try:
        import openai  # noqa: F401
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai")
    row = manifest.iloc[0]
    print(f"\n--probe: sending ONE call for sample_id={row['sample_id']} "
          f"(true_class={row['true_class']}), representation={row['representation']}, model={model} ...")
    client = build_client()
    prompt = build_prompt(row["representation"], class_names)
    try:
        img_uri = image_data_uri(row["image_path"])
        text, usage = call_qwen_model(client, model, prompt, img_uri, retries=1)
        print("\n--probe SUCCEEDED. Raw response:\n" + "-" * 40)
        print(text)
        print("-" * 40)
        print(f"Tokens: input={getattr(usage, 'prompt_tokens', '?')} "
              f"output={getattr(usage, 'completion_tokens', '?')}")
        print("\nThis model works -- rerun without --probe to do the full run.")
    except Exception as e:
        print("\n--probe FAILED.")
        print("Diagnostics: " + describe_exception(e))
        print("\nCommon causes: DASHSCOPE_API_KEY/QWEN_API_KEY not set or invalid, no billing "
              "set up on the account, the model name isn't available in your region "
              "(qwen-vl-max/qwen-vl-plus), or QWEN_BASE_URL points at the wrong region's "
              "endpoint -- check https://dashscope.console.aliyun.com/apiKey")


def run_harness(manifest, limit, class_names, out_dir, model=DEFAULT_MODEL, resume=True):
    try:
        import openai  # noqa: F401
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai")

    client = build_client()

    run_manifest = _apply_limit(manifest, limit)
    total_calls = len(run_manifest)

    out_path = os.path.join(out_dir, "harness_results_qwen.csv")
    kept_rows, done_keys = load_resumable_results(out_path) if resume else ([], set())
    if done_keys:
        print(f"--resume: found {len(done_keys)} already-completed (sample, representation) calls "
              f"in {out_path} -- skipping those, retrying any stale ERROR rows.")
        pd.DataFrame(kept_rows, columns=RESULT_COLUMNS).to_csv(out_path, index=False)

    remaining = total_calls - len(done_keys)
    n_reps = run_manifest["representation"].nunique() if len(run_manifest) else 0
    print(f"Running {total_calls} Qwen API calls ({model}, "
          f"{run_manifest['sample_id'].nunique() if len(run_manifest) else 0} samples x {n_reps} "
          f"representations, {remaining} remaining) across {len(class_names)} classes: "
          f"{', '.join(class_names)}")

    file_exists = os.path.isfile(out_path)
    csv_file = open(out_path, "a", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=RESULT_COLUMNS)
    if not file_exists:
        writer.writeheader()
        csv_file.flush()

    rows = list(kept_rows)
    done = len(done_keys)
    try:
        for _, row in run_manifest.iterrows():
            key = (row["sample_id"], row["representation"])
            if key in done_keys:
                continue
            img_uri = image_data_uri(row["image_path"])
            prompt = build_prompt(row["representation"], class_names)
            try:
                text, usage = call_qwen_model(client, model, prompt, img_uri)
                parsed = parse_response(text)
                result_row = {
                    "sample_id": row["sample_id"], "true_class": row["true_class"],
                    "representation": row["representation"], "classification": parsed["classification"],
                    "reference_id": parsed["reference_id"], "justification": parsed["justification"],
                    "input_tokens": getattr(usage, "prompt_tokens", 0),
                    "output_tokens": getattr(usage, "completion_tokens", 0),
                    "raw_response": (text or "").replace("\n", " | "),
                }
            except FatalAPIError as e:
                print(f"\nSTOPPING: {e}")
                print(f"Progress so far this run is saved in {out_path} -- "
                      f"re-run the same command after fixing the account issue and it "
                      f"will resume from here.")
                return pd.DataFrame(rows, columns=RESULT_COLUMNS)
            except Exception as e:
                sid = row.get("sample_id", "UNKNOWN_SAMPLE")
                tc = row.get("true_class", "UNKNOWN_CLASS")
                rep = row.get("representation", "UNKNOWN_REP")
                diag = describe_exception(e)
                print(f"ERROR on {sid} / {rep}: {diag}")
                result_row = {"sample_id": sid, "true_class": tc,
                               "representation": rep, "classification": "ERROR", "reference_id": "",
                               "justification": diag, "input_tokens": 0, "output_tokens": 0,
                               "raw_response": ""}
            rows.append(result_row)
            writer.writerow(result_row)
            csv_file.flush()
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{total_calls} calls done")
    finally:
        csv_file.close()

    return pd.DataFrame(rows, columns=RESULT_COLUMNS)
