"""Tests for the export module, the LLM mock layer, and the RAG retriever."""

from app.export import build_pptx, build_markdown
from app.llm import MockLLM, make_llm, get_llm
from app.rag import retrieve, _DOCS

import asyncio

_RESULTS = {
    "taskLabel": "Binary classification",
    "bestModel": "LightGBM",
    "headline": {"fraction": 0.84, "value": "0.84", "label": "ROC-AUC"},
    "metrics": [{"label": "Accuracy", "value": "0.81"}, {"label": "F1", "value": "0.78"}],
    "bars": [{"label": "tenure", "value": 0.9, "sign": -1}, {"label": "charges", "value": 0.6, "sign": 1}],
    "dist": [{"label": "North", "value": 0.4, "display": "40%"}],
    "distTitle": "rate by region",
    "report": ["We built a model.", "Tenure is the top driver."],
    "recommendation": "Prioritise tenure.",
    "_verdict": {"level": "good", "label": "Solid predictive signal", "detail": "ROC-AUC 0.84."},
    "_stats_tests": [{"feature": "tenure", "test": "Welch t-test", "p": 0.0001, "significant": True}],
}


def test_build_pptx_returns_valid_zip():
    data = build_pptx(_RESULTS, goal="predict churn", dataset="demo")
    assert isinstance(data, (bytes, bytearray)) and len(data) > 5000
    assert data[:2] == b"PK"  # pptx is a zip container


def test_build_markdown():
    md = build_markdown(_RESULTS, goal="predict churn", dataset="demo").decode("utf-8")
    assert "# Helix Analysis" in md
    assert "Recommendation" in md and "tenure" in md


def test_rag_has_grown_and_retrieves():
    assert len(_DOCS) >= 40
    docs = retrieve("oversample imbalanced minority class SMOTE", 2)
    assert any("SMOTE" in d or "minority" in d for d in docs)


def test_mockllm_is_deterministic_and_no_key():
    assert isinstance(get_llm("planner"), MockLLM)  # no override / no env key
    assert make_llm("groq", None, None).is_mock is True
    out = asyncio.run(MockLLM().acomplete("planner", {"plan": ["1. load", "2. clean"]}))
    assert "1. load" in out
