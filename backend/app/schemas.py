"""Request models. Field names match the JSON the frontend sends."""

from __future__ import annotations

from pydantic import BaseModel


class RunRequest(BaseModel):
    datasetId: str = "churn"
    goal: str = ""
    fileName: str | None = None
    provider: str = "groq"
    model: str | None = None
    apiKey: str | None = None
    temperature: float | None = None
    # optional per-role config: {"default": {...}, "<role>": {provider, model, api_key, temperature}}
    llms: dict | None = None


class AskRequest(BaseModel):
    question: str
    results: dict = {}
    provider: str = "groq"
    model: str | None = None
    apiKey: str | None = None
    temperature: float | None = None
    llms: dict | None = None


class ExportRequest(BaseModel):
    results: dict = {}
    goal: str = ""
    dataset: str = "dataset"
    format: str = "pptx"  # "pptx" | "md"
