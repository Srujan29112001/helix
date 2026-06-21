"""Hybrid LLM provider layer.

Each agent role resolves its own provider, so you can mix a local model for one
role with an API for another (the "hybrid" decision). With no configuration the
``MockLLM`` runs everything deterministically — the pipeline works end-to-end
with zero keys, and you add real models later by setting env vars.

Per-role config (ROLE ∈ planner|coder|critic|reporter), falling back to global:
  HELIX_<ROLE>_API_KEY   / HELIX_LLM_API_KEY
  HELIX_<ROLE>_BASE_URL  / HELIX_LLM_BASE_URL   (OpenAI-compatible /chat/completions)
  HELIX_<ROLE>_MODEL     / HELIX_LLM_MODEL
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any


class LLMProvider:
    is_mock: bool = True

    async def acomplete(self, role: str, context: dict[str, Any]) -> str:  # noqa: D401
        raise NotImplementedError


class MockLLM(LLMProvider):
    """Deterministic stub. Returns curated content carried in ``context`` so the
    no-key demo is clean and stable."""

    is_mock = True

    async def acomplete(self, role: str, context: dict[str, Any]) -> str:
        if role == "planner":
            return "\n".join(context.get("plan", []))
        if role == "coder":
            return "\n".join(context.get("code", []))
        if role == "critic":
            return str(context.get("fix", ""))
        if role == "reporter":
            report = context.get("report", [])
            rec = context.get("recommendation", "")
            return "\n\n".join(report) + (f"\n\nRecommendation: {rec}" if rec else "")
        if role == "researcher":
            hits = context.get("hits", [])
            goal = context.get("goal", "this analysis")
            if hits:
                return f"External research surfaced {len(hits)} relevant sources on {goal}. " + hits[0].get("snippet", "")[:170]
            return (
                f"No live web results were available, so this draws on general domain knowledge: {goal} "
                "typically hinges on the drivers the model surfaced above."
            )
        if role == "visualizer":
            # empty -> the engine falls back to its deterministic chart gallery
            return ""
        return ""


_SYSTEM = {
    "planner": "You are a senior data scientist. Given a dataset description and a goal, output a concise numbered analysis plan (max 6 steps). One step per line, no prose.",
    "coder": (
        "You are an expert Python data scientist writing for a RESTRICTED sandbox. "
        "A pandas DataFrame named `df` is ALREADY loaded in memory — never read files, never call "
        "read_csv/read_excel/open. Allowed imports: pandas, numpy, sklearn, math, statistics, re, json. "
        "NEVER import matplotlib, seaborn, plotly, os, sys, or any plotting/network library, and do not "
        "create plots. For numeric aggregations (mean/sum/std/var/corr) ALWAYS pass numeric_only=True to "
        "avoid string-dtype errors, but NEVER pass numeric_only to describe() — use df.describe(include='all'). "
        "Only compute and print() short text summaries. "
        "Output only runnable Python — no explanations, no markdown fences."
    ),
    "critic": (
        "You are a Python debugging expert. Given code and its traceback, output the corrected FULL Python "
        "script that fixes the error. The DataFrame `df` is already loaded — never read files and never import "
        "matplotlib/plotting libraries. If the error is a reduction on string dtype (e.g. \"Cannot perform "
        "reduction 'mean' with string dtype\"), add numeric_only=True to that aggregation — but NEVER to "
        "describe() (use df.describe(include='all')). Output only the code — no markdown fences, no prose."
    ),
    "reporter": (
        "You are a senior data/business analyst writing a professional, board-ready findings report. "
        "Write 6-7 substantial paragraphs in plain English for executives, weaving in the SPECIFIC numbers you "
        "are given — cite metric values, driver directions, segment rates, correlations and key statistics: "
        "(1) an executive summary of what was predicted and how reliable it is; (2) the strongest drivers and the "
        "business meaning of each direction; (3) what the segment/breakdown pattern reveals, with the actual rates; "
        "(4) notable correlations and which feature→target relationships are STATISTICALLY SIGNIFICANT "
        "(cite the test and p-value, e.g. 'significant by chi-square, p<0.001') vs likely chance; "
        "(5) data quality and the automated observations provided; "
        "(6) the risks, caveats and limits of the model — and if the model-quality verdict indicates weak or "
        "near-chance signal, say so honestly and explain the target is hard to predict from these features rather "
        "than overclaiming. Then a final paragraph starting with 'Recommendation:' "
        "giving 2-3 concrete, prioritised actions. Be specific and quantitative, never generic. No markdown, no "
        "bullet points, no headings."
    ),
    "researcher": (
        "You are a research analyst with live web access. Given the analysis goal, the dataset's domain context, "
        "the model's key drivers, and real web search results, write 3-4 sentences of external, domain-aware "
        "context that complements the analysis: what the field/industry already knows about these drivers, "
        "relevant benchmarks, regulations or best practices. Ground claims in the provided search snippets; if no "
        "results are available, use general domain knowledge and say it is not live. Be specific — no fluff, no markdown."
    ),
    "visualizer": (
        "You are a data-visualization expert choosing the BEST charts for a specific dataset, goal and industry. "
        "Output ONLY a JSON array (no prose, no markdown fences) of at most 8 chart specs, ordered most to least "
        "important for the user's goal and context. You MUST NOT invent or output any numeric data — choose only the "
        "chart type, a data source the engine will compute on the real data, a concise title (<=60 chars), a one-line "
        "note explaining what the chart shows and how to read it, and optional axis labels. "
        "Allowed type: column|bar|line|area|pie|radar|histogram|scatter|box|heatmap|statcards. "
        "Each spec is {\"type\":...,\"source\":{...},\"title\":...,\"note\":...,\"axes\":{\"x\":...,\"y\":...}}. "
        "source.kind is one of: "
        "\"aggregate\" {\"kind\":\"aggregate\",\"groupby\":<col>,\"of\":<numeric col or null>,\"agg\":\"mean|sum|count|median|min|max\",\"top\":<int>}; "
        "\"distribution\" {\"kind\":\"distribution\",\"column\":<col>,\"bins\":<int>}; "
        "\"corr_matrix\" {\"kind\":\"corr_matrix\",\"columns\":[<numeric cols>]}; "
        "\"insight\" {\"kind\":\"insight\",\"ref\":\"bars|dist|corr|hist|scatter|box|stats\"}. "
        "Reference ONLY column names from the provided profile. Favour aggregate/distribution charts that reveal the "
        "story for THIS domain, and match the chart type to the finding (line for trends, pie for shares, heatmap for "
        "correlations, box for spread, scatter for relationships, histogram for a single column's distribution)."
    ),
}


class OpenAICompatibleLLM(LLMProvider):
    """Any OpenAI-compatible chat endpoint: OpenRouter, Together, Groq, Ollama, vLLM."""

    is_mock = False

    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.2):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    async def acomplete(self, role: str, context: dict[str, Any]) -> str:
        import httpx

        user = _build_user_prompt(role, context)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM.get(role, "You are a helpful assistant.")},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


class AnthropicLLM(LLMProvider):
    """Anthropic Claude — native Messages API (not OpenAI-compatible)."""

    is_mock = False

    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.2):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    async def acomplete(self, role: str, context: dict[str, Any]) -> str:
        import httpx

        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": self.temperature,
            "system": _SYSTEM.get(role, "You are a helpful assistant."),
            "messages": [{"role": "user", "content": _build_user_prompt(role, context)}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.base_url}/messages", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"].strip()


def _build_user_prompt(role: str, context: dict[str, Any]) -> str:
    ds = context.get("dataset", {})
    head = (
        f"Dataset: {ds.get('name','?')} ({ds.get('rows','?')} rows × {ds.get('cols','?')} cols)\n"
        f"Task: {ds.get('task','?')}   Target: {ds.get('target','?')}\n"
    )
    if role == "planner":
        return head + f"Goal: {context.get('goal','')}\nWrite the plan."
    if role == "coder":
        docs = context.get("docs", [])
        ref = ("\nRelevant docs:\n" + "\n".join(f"- {d}" for d in docs)) if docs else ""
        return head + (
            f"Step: {context.get('step','')}{ref}\n"
            "The DataFrame `df` is already loaded — do NOT read any file and do NOT import "
            "matplotlib/seaborn or plot. Use only pandas/numpy and print() concise text summaries.\n"
            "Write the Python."
        )
    if role == "critic":
        return (
            f"This Python failed:\n{context.get('code', '')}\n\n"
            f"Traceback:\n{context.get('error', '')}\n\n"
            "Output the corrected full script."
        )
    if role == "reporter":
        return head + (
            f"Model-quality verdict: {context.get('verdict','')}\n"
            f"Metrics (held-out test set): {context.get('metrics','')}\n"
            f"Key drivers (most to least important; sign = effect direction): {context.get('drivers','')}\n"
            f"Breakdown — {context.get('breakdown','')}\n"
            f"Key statistics: {context.get('stats','')}\n"
            f"Notable correlations: {context.get('correlations','')}\n"
            f"Statistical significance tests: {context.get('sigtests','') or '(none)'}\n"
            f"Data quality: {context.get('quality','')}\n"
            f"Automated observations: {context.get('smart','')}\n"
            f"External web research: {context.get('research','')}\n"
            "Write the 6-7 paragraph professional report citing these specific numbers (weave in the external "
            "research where relevant, and include a data-quality paragraph), then the final 'Recommendation:' "
            "paragraph with 2-3 prioritised actions."
        )
    if role == "researcher":
        hits = context.get("hits", [])
        src = "\n".join(f"- {h.get('title','')}: {h.get('snippet','')}" for h in hits[:5]) or "(no live results — use domain knowledge)"
        return head + (
            f"Goal: {context.get('goal','')}\n"
            f"Dataset context: {context.get('context','') or '(none given)'}\n"
            f"Model's key drivers: {context.get('drivers','')}\n"
            f"Web search results:\n{src}\n"
            "Write the 3-4 sentence external research synthesis."
        )
    if role == "visualizer":
        prof = context.get("profile", []) or []
        nums = [p["name"] for p in prof if p.get("type") == "numeric"]
        cats = [p["name"] for p in prof if p.get("type") in ("categorical", "date")]
        plines = "\n".join(
            f"- {p['name']} ({p.get('type','?')}, {p.get('unique','?')} unique, {p.get('missing','?')}% missing)"
            for p in prof[:40]
        ) or "(no profile)"
        avail = ", ".join(context.get("insights", [])) or "(none)"
        return head + (
            f"Goal: {context.get('goal','')}\n"
            f"Industry / context tags: {context.get('context','') or '(none)'}\n"
            f"Target: {context.get('target','')}\n"
            f"Numeric columns: {', '.join(nums) or '(none)'}\n"
            f"Categorical / date columns: {', '.join(cats) or '(none)'}\n"
            f"Column profile:\n{plines}\n"
            f"Pre-computed engine insights available as source.ref: {avail}\n"
            "Return the JSON array of up to 8 chart specs now."
        )
    return head


# provider id -> (base url, kind)
PROVIDERS: dict[str, tuple[str, str]] = {
    "groq": ("https://api.groq.com/openai/v1", "openai"),
    "openai": ("https://api.openai.com/v1", "openai"),
    "deepseek": ("https://api.deepseek.com", "openai"),
    "mistral": ("https://api.mistral.ai/v1", "openai"),
    "openrouter": ("https://openrouter.ai/api/v1", "openai"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "openai"),
    "zai": ("https://api.z.ai/api/paas/v4", "openai"),
    "anthropic": ("https://api.anthropic.com/v1", "anthropic"),
}

_DEFAULT_MODEL = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "mistral": "mistral-small-latest",
    "openrouter": "deepseek/deepseek-chat",
    "gemini": "gemini-2.0-flash",
    "zai": "glm-4.6",
    "anthropic": "claude-3-5-haiku-latest",
}


def _clamp_temp(temperature) -> float:
    try:
        return max(0.0, min(2.0, float(temperature)))
    except (TypeError, ValueError):
        return 0.2


def make_llm(provider: str, model: str | None, api_key: str | None, temperature: float = 0.2) -> LLMProvider:
    """Build a provider from an explicit (provider, model, key, temperature) — e.g. sent from the UI."""
    if not api_key:
        return MockLLM()
    base, kind = PROVIDERS.get(provider, PROVIDERS["groq"])
    model = model or _DEFAULT_MODEL.get(provider, "llama-3.3-70b-versatile")
    temp = _clamp_temp(temperature)
    if kind == "anthropic":
        return AnthropicLLM(base, api_key, model, temp)
    return OpenAICompatibleLLM(base, api_key, model, temp)


# Per-request override, set by the API endpoint from the UI's config.
_override: ContextVar[dict | None] = ContextVar("helix_llm_override", default=None)


def set_llm_override(config: dict | None) -> None:
    """Per-request LLM config from the UI.

    ``config`` maps a role (or the special key ``"default"``) to a
    ``{provider, model, api_key}`` dict. A role without its own entry falls back
    to ``"default"``. This supports BOTH one shared model for every agent
    (``{"default": {...}}``) and a different model per agent
    (``{"default": {...}, "coder": {...}, "reporter": {...}}``). ``None`` clears it.
    """
    _override.set(config or None)


def _resolve(role: str) -> tuple[str, str, str]:
    def pick(suffix: str) -> str:
        return os.getenv(f"HELIX_{role.upper()}_{suffix}") or os.getenv(
            f"HELIX_LLM_{suffix}", ""
        )

    return pick("BASE_URL"), pick("API_KEY"), pick("MODEL")


def get_llm(role: str) -> LLMProvider:
    cfg = _override.get() or {}
    rc = cfg.get(role) or cfg.get("default")
    if rc and rc.get("api_key"):
        # temperature: role-specific, else the default entry's, else 0.2
        temp = rc.get("temperature")
        if temp is None:
            temp = (cfg.get("default") or {}).get("temperature", 0.2)
        return make_llm(rc.get("provider") or "groq", rc.get("model"), rc["api_key"], temp)
    base_url, api_key, model = _resolve(role)
    if base_url or api_key:
        return OpenAICompatibleLLM(
            base_url=base_url or "https://api.groq.com/openai/v1",
            api_key=api_key,
            model=model or "llama-3.3-70b-versatile",
        )
    return MockLLM()
