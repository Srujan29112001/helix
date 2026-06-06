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
        return ""


_SYSTEM = {
    "planner": "You are a senior data scientist. Given a dataset description and a goal, output a concise numbered analysis plan (max 6 steps). One step per line, no prose.",
    "coder": "You are an expert Python data scientist. Output only runnable Python for the requested step — no explanations, no markdown fences.",
    "critic": "You are a Python debugging expert. Given code and its traceback, output the corrected FULL Python script that fixes the error. Output only the code — no markdown fences, no prose.",
    "reporter": "You are a business analyst. Write a short, plain-English narrative of the findings for a non-technical stakeholder, then a one-line recommendation.",
}


class OpenAICompatibleLLM(LLMProvider):
    """Any OpenAI-compatible chat endpoint: OpenRouter, Together, Groq, Ollama, vLLM."""

    is_mock = False

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def acomplete(self, role: str, context: dict[str, Any]) -> str:
        import httpx

        user = _build_user_prompt(role, context)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM.get(role, "You are a helpful assistant.")},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
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

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def acomplete(self, role: str, context: dict[str, Any]) -> str:
        import httpx

        payload = {
            "model": self.model,
            "max_tokens": 1024,
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
        return head + f"Step: {context.get('step','')}{ref}\nWrite the Python."
    if role == "critic":
        return (
            f"This Python failed:\n{context.get('code', '')}\n\n"
            f"Traceback:\n{context.get('error', '')}\n\n"
            "Output the corrected full script."
        )
    if role == "reporter":
        return head + (
            f"Metrics: {context.get('metrics','')}\n"
            f"Key drivers: {context.get('drivers','')}\nWrite the report + recommendation."
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
    "anthropic": ("https://api.anthropic.com/v1", "anthropic"),
}

_DEFAULT_MODEL = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "mistral": "mistral-small-latest",
    "openrouter": "deepseek/deepseek-chat",
    "gemini": "gemini-2.0-flash",
    "anthropic": "claude-3-5-haiku-latest",
}


def make_llm(provider: str, model: str | None, api_key: str | None) -> LLMProvider:
    """Build a provider from an explicit (provider, model, key) — e.g. sent from the UI."""
    if not api_key:
        return MockLLM()
    base, kind = PROVIDERS.get(provider, PROVIDERS["groq"])
    model = model or _DEFAULT_MODEL.get(provider, "llama-3.3-70b-versatile")
    if kind == "anthropic":
        return AnthropicLLM(base, api_key, model)
    return OpenAICompatibleLLM(base, api_key, model)


# Per-request override, set by the API endpoint from the UI's config.
_override: ContextVar[dict | None] = ContextVar("helix_llm_override", default=None)


def set_llm_override(provider: str | None, model: str | None, api_key: str | None) -> None:
    _override.set(
        {"provider": provider or "groq", "model": model, "api_key": api_key} if api_key else None
    )


def _resolve(role: str) -> tuple[str, str, str]:
    def pick(suffix: str) -> str:
        return os.getenv(f"HELIX_{role.upper()}_{suffix}") or os.getenv(
            f"HELIX_LLM_{suffix}", ""
        )

    return pick("BASE_URL"), pick("API_KEY"), pick("MODEL")


def get_llm(role: str) -> LLMProvider:
    cfg = _override.get()
    if cfg and cfg.get("api_key"):
        return make_llm(cfg["provider"], cfg.get("model"), cfg["api_key"])
    base_url, api_key, model = _resolve(role)
    if base_url or api_key:
        return OpenAICompatibleLLM(
            base_url=base_url or "https://api.groq.com/openai/v1",
            api_key=api_key,
            model=model or "llama-3.3-70b-versatile",
        )
    return MockLLM()
