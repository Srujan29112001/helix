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
