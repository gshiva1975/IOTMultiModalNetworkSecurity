"""
llm_clients.py
---------------
Unified client wrappers for the live-model comparison (Claude API vs.
GPT-4o-mini), used by llm_experiment.py to run the citation-grounded
classification task under both context-construction strategies
(full-corpus / RAG).

Three client types:
  AnthropicClient    -- real call via the `anthropic` package.
  OpenAIClient        -- real call via the `openai` package.
  MockClient          -- deterministic, no-network stand-in used ONLY to
                          verify the experiment harness itself runs
                          end-to-end (prompt building, response parsing,
                          CSV writing, statistics) before real API keys are
                          available. MockClient responses are NOT real
                          model output and must never be reported as
                          experimental results -- see README / paper
                          Limitations sections.

Both real clients raise a clear, actionable error at construction time if
their API key environment variable is missing, rather than failing deep
inside a 45-query x 2-strategy loop.

Pricing constants below are PLACEHOLDERS and are flagged as such -- verify
against each provider's current published pricing before reporting cost
numbers in the paper (this mirrors the existing INPUT_PRICE_PER_MTOK_USD
placeholder already disclosed in cost_model.py for the retrieval-context
cost estimate).
"""

import os
import time
import random
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# PLACEHOLDER pricing -- verify against provider docs before citing in the
# paper. Figures are USD per 1M tokens, input/output, as of this writing.
# ---------------------------------------------------------------------------
PRICING_USD_PER_MTOK = {
    "claude-sonnet-5":      {"input": 3.00, "output": 15.00},   # PLACEHOLDER -- verify
    "claude-opus-5":        {"input": 15.00, "output": 75.00},  # PLACEHOLDER -- verify
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},  # PLACEHOLDER -- verify
    "gpt-4o-mini":          {"input": 0.15, "output": 0.60},    # PLACEHOLDER -- verify
    "mock-model":           {"input": 0.0, "output": 0.0},
}


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    cost_usd: float
    model: str
    error: str = ""   # non-empty if the call failed; text will be "" in that case


def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING_USD_PER_MTOK.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens / 1_000_000) * p["input"] + (output_tokens / 1_000_000) * p["output"]


class AnthropicClient:
    """Real Claude API client. Requires ANTHROPIC_API_KEY in the environment."""

    def __init__(self, model: str = "claude-sonnet-5", max_tokens: int = 512):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set in the environment. "
                "Set it before running llm_experiment.py without --mock, e.g.:\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            )
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "The 'anthropic' package is not installed. Run: "
                "pip install anthropic --break-system-packages"
            ) from e
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        t0 = time.perf_counter()
        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                # NOTE: `temperature` is deliberately omitted. This model
                # rejects it outright with a 400 "temperature is deprecated
                # for this model" error (confirmed live, 2026-08 -- see
                # llm_experiment.py run history / paper Limitations). The
                # companion paper's protocol calls for temperature-0
                # decoding for reproducibility; since that parameter isn't
                # accepted here, this is a disclosed deviation from the
                # original protocol, not a silent one.
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            latency = time.perf_counter() - t0
            text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
            in_tok = resp.usage.input_tokens
            out_tok = resp.usage.output_tokens
            return LLMResponse(
                text=text, input_tokens=in_tok, output_tokens=out_tok,
                latency_s=latency, cost_usd=_cost(self.model, in_tok, out_tok),
                model=self.model,
            )
        except Exception as e:  # noqa: BLE001 -- deliberately broad: log and continue the sweep
            latency = time.perf_counter() - t0
            return LLMResponse(
                text="", input_tokens=0, output_tokens=0, latency_s=latency,
                cost_usd=0.0, model=self.model, error=str(e),
            )


class OpenAIClient:
    """Real GPT-4o-mini client. Requires OPENAI_API_KEY in the environment."""

    def __init__(self, model: str = "gpt-4o-mini", max_tokens: int = 512):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set in the environment. "
                "Set it before running llm_experiment.py without --mock, e.g.:\n"
                "  export OPENAI_API_KEY=sk-...\n"
            )
        try:
            import openai
        except ImportError as e:
            raise RuntimeError(
                "The 'openai' package is not installed. Run: "
                "pip install openai --break-system-packages"
            ) from e
        self.model = model
        self.max_tokens = max_tokens
        self._client = openai.OpenAI(api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        t0 = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            latency = time.perf_counter() - t0
            text = resp.choices[0].message.content or ""
            in_tok = resp.usage.prompt_tokens
            out_tok = resp.usage.completion_tokens
            return LLMResponse(
                text=text, input_tokens=in_tok, output_tokens=out_tok,
                latency_s=latency, cost_usd=_cost(self.model, in_tok, out_tok),
                model=self.model,
            )
        except Exception as e:  # noqa: BLE001
            latency = time.perf_counter() - t0
            return LLMResponse(
                text="", input_tokens=0, output_tokens=0, latency_s=latency,
                cost_usd=0.0, model=self.model, error=str(e),
            )


class MockClient:
    """
    NOT a real model. Deterministic stand-in used only to verify the
    experiment harness (prompt construction, response parsing, CSV
    schema, statistics computation) runs correctly end-to-end without
    network access or API keys.

    Behavior: with probability p_correct, "cites" the ground-truth id if it
    is present in the shown context; otherwise abstains or cites a random
    shown id, deterministically seeded so mock runs are reproducible. This
    produces plausible-looking but ENTIRELY FABRICATED metrics -- any run
    using MockClient must be labeled as a dry run in every output file and
    must never be copied into the paper's Results tables.
    """

    def __init__(self, model: str = "mock-model", p_correct: float = 0.7, seed: int = 42):
        self.model = model
        self.p_correct = p_correct
        self._rng = random.Random(seed)

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """
        Real-client-compatible entry point: parses only the [[SHOWN_IDS:...]]
        debug marker from the prompt (harmless -- it's a redundant restatement
        of IDs already shown in the reference-entries list above it, not
        secret information). Ground truth is deliberately NOT embedded in
        the shared prompt text, because that text is also sent verbatim to
        the real Claude/GPT-4o-mini clients -- leaking the answer into the
        prompt would silently invalidate the real experiment. Without a
        ground-truth signal, this fallback path can only guess among shown
        ids; call generate_with_truth() instead (llm_experiment.py does this
        automatically for mock clients) for a more meaningful self-test of
        the harness's scoring logic.
        """
        shown_ids = []
        for line in user_prompt.splitlines():
            if line.startswith("[[SHOWN_IDS:"):
                shown_ids = line[len("[[SHOWN_IDS:"):-2].split(",") if line.endswith("]]") else []
                shown_ids = [s for s in shown_ids if s]
        return self._simulate(shown_ids, ground_truth_id=None)

    def generate_with_truth(self, system_prompt: str, user_prompt: str,
                             ground_truth_id, shown_ids: list) -> LLMResponse:
        """
        Mock-only path: ground_truth_id and shown_ids are passed directly by
        llm_experiment.py (out of band, never inserted into the actual
        prompt text) so the mock's self-test can meaningfully exercise the
        correct/incorrect/abstain scoring logic without ever risking leaking
        the answer into a real model's prompt.
        """
        return self._simulate(shown_ids, ground_truth_id)

    def _simulate(self, shown_ids: list, ground_truth_id) -> LLMResponse:
        t0 = time.perf_counter()
        gt_id = ground_truth_id
        roll = self._rng.random()
        if gt_id and gt_id in shown_ids and roll < self.p_correct:
            cited = gt_id
        elif roll < self.p_correct + 0.1 and shown_ids:
            cited = self._rng.choice(shown_ids)  # plausible wrong-but-shown citation
        else:
            cited = None  # abstain

        if cited:
            text = (
                f'{{"classification": "mock finding", "cited_id": "{cited}", '
                f'"justification": "mock justification referencing {cited}."}}'
            )
        else:
            text = (
                '{"classification": "mock finding", "cited_id": null, '
                '"justification": "none of the shown entries clearly apply."}'
            )
        latency = time.perf_counter() - t0
        approx_in = max(1, sum(len(s) for s in shown_ids) // 4 + 50)
        approx_out = max(1, len(text) // 4)
        return LLMResponse(
            text=text, input_tokens=approx_in, output_tokens=approx_out,
            latency_s=latency, cost_usd=0.0, model=self.model,
        )


def get_client(key: str):
    """
    key in {"claude", "gpt4o-mini", "mock-claude", "mock-gpt4o-mini"}.
    Returns a client with a .generate(system_prompt, user_prompt) -> LLMResponse method.
    """
    if key == "claude":
        return AnthropicClient(model="claude-sonnet-5")
    if key == "gpt4o-mini":
        return OpenAIClient(model="gpt-4o-mini")
    if key == "mock-claude":
        return MockClient(model="mock-claude", p_correct=0.75, seed=1)
    if key == "mock-gpt4o-mini":
        return MockClient(model="mock-gpt4o-mini", p_correct=0.60, seed=2)
    raise ValueError(f"Unknown client key: {key}")
