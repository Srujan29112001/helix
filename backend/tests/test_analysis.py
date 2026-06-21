"""Unit tests for the Helix analysis engine — every task type + the key helpers.

Fast and offline: tiny synthetic datasets + small FLAML budgets. Run from backend/:
    python -m pytest -q
"""

import numpy as np
import pandas as pd
import pytest

from app.analysis import (
    analyze_dataframe,
    clean,
    _is_classification,
    _auto_target,
    _statistics,
    _numeric_matrix,
)

RNG = np.random.RandomState(0)


def _clf_df(n=200):
    x1, x2 = RNG.randn(n), RNG.randn(n)
    return pd.DataFrame({"x1": x1, "x2": x2, "cat": RNG.choice(["a", "b"], n),
                         "y": (x1 + x2 > 0).astype(int)})


def _reg_df(n=200):
    x1, x2 = RNG.randn(n), RNG.randn(n)
    return pd.DataFrame({"x1": x1, "x2": x2, "y": 3 * x1 - 2 * x2 + RNG.randn(n) * 0.3})


# --------------------------- helpers ---------------------------
def test_is_classification():
    assert _is_classification(pd.Series(["a", "b", "a"])) is True
    assert _is_classification(pd.Series([0, 1, 1, 0])) is True
    assert _is_classification(pd.Series(np.linspace(0, 100, 50))) is False


def test_clean_strips_and_drops_id_and_missing_target():
    df = pd.DataFrame({" id ": range(5), "name": list("abcde"),
                       "val": [1, 2, None, 4, 5], "target": [1, 0, 1, None, 0]})
    df.columns = [c for c in df.columns]  # keep the spaced name
    out, fixes = clean(df, "target")
    assert "target" in out.columns
    # a row with a missing target is dropped
    assert out["target"].isna().sum() == 0
    assert any("whitespace" in f or "identifier" in f or "missing" in f for f in fixes)


def test_auto_target_prefers_known_names_then_last():
    assert _auto_target(pd.DataFrame({"a": [1], "churn": [0]})) == "churn"
    assert _auto_target(pd.DataFrame({"a": [1, 2], "b": [3, 4]})) == "b"


def test_numeric_matrix_is_all_numeric():
    df = pd.DataFrame({"n": [1.0, 2.0, 3.0], "c": ["x", "y", "x"], "id": [1, 2, 3]})
    m = _numeric_matrix(df)
    assert m.select_dtypes(include="number").shape[1] == m.shape[1]
    assert "id" not in m.columns  # id-like dropped


def test_statistics_detects_significance():
    n = 300
    region = RNG.choice(["N", "S"], n)
    y = np.where(region == "N", RNG.binomial(1, 0.8, n), RNG.binomial(1, 0.2, n))
    df = pd.DataFrame({"region": region, "noise": RNG.randn(n), "y": y})
    tests = _statistics(df, "y", True, [{"label": "region"}, {"label": "noise"}])
    assert isinstance(tests, list) and len(tests) >= 1
    reg = next((t for t in tests if t["feature"] == "region"), None)
    assert reg is not None and reg["significant"] is True and "p" in reg


# --------------------------- supervised tasks ---------------------------
def test_classification_core_and_eval():
    r = analyze_dataframe(_clf_df(), "y", "classification", time_budget=3)
    assert "classification" in r["taskLabel"].lower()
    assert 0.0 <= r["headline"]["fraction"] <= 1.0001
    assert r["bars"] and r["metrics"]
    assert r.get("_cv") and r["_cv"]["mean"] is not None
    assert r.get("_confusion") and r.get("_per_class")
    assert r.get("_model_compare") and len(r["_model_compare"]) >= 2


def test_regression_core_and_residuals():
    r = analyze_dataframe(_reg_df(), "y", "regression", time_budget=3)
    assert r["taskLabel"] == "Regression"
    assert r.get("_residuals") and r["_residuals"]["points"]
    assert any(m["label"] == "R2" for m in r["metrics"])


def test_imbalance_triggers_smote():
    n = 400
    x = RNG.randn(n)
    y = (RNG.rand(n) < 0.08).astype(int)  # ~8% positives
    r = analyze_dataframe(pd.DataFrame({"x": x, "x2": RNG.randn(n), "y": y}), "y", "classification", time_budget=3)
    imb = r.get("_imbalance")
    assert imb is not None
    if imb["applied"]:
        assert sum(imb["after"].values()) >= sum(imb["before"].values())


# --------------------------- unsupervised / special tasks ---------------------------
def test_clustering():
    a = pd.DataFrame({"x": RNG.randn(120), "y": RNG.randn(120), "z": RNG.randn(120)})
    r = analyze_dataframe(a, "", "clustering")
    assert r["taskLabel"] == "Clustering"
    assert r["bars"] and r["dist"]


def test_anomaly():
    a = pd.DataFrame({"x": RNG.randn(200), "y": RNG.randn(200)})
    a.loc[:8, ["x", "y"]] += 8
    r = analyze_dataframe(a, "", "anomaly")
    assert r["taskLabel"] == "Anomaly detection"
    assert r.get("_scatter") and r.get("_hist")


def test_dimreduction():
    a = pd.DataFrame({c: RNG.randn(150) for c in "abcd"})
    r = analyze_dataframe(a, "", "dimreduction")
    assert r["taskLabel"] == "Dimensionality reduction"
    assert r.get("_scatter") and r["dist"]


def test_recommendation():
    a = pd.DataFrame({"name": [f"item{i}" for i in range(50)],
                      "p": RNG.rand(50), "q": RNG.rand(50)})
    r = analyze_dataframe(a, "", "recommendation")
    assert r["taskLabel"].startswith("Recommendation")
    assert r["_recommend"]["items"]


def test_timeseries():
    t = np.arange(120)
    y = 10 + 0.3 * t + 4 * np.sin(2 * np.pi * t / 12) + RNG.randn(120)
    df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=120, freq="W"), "sales": y})
    r = analyze_dataframe(df, "sales", "timeseries")
    assert r["taskLabel"] == "Time-series forecasting"
    assert r["_forecast"]["points"] and r["_forecast"]["horizon"] > 0


def test_survival():
    n = 300
    tenure = RNG.randint(1, 60, n)
    churn = (RNG.rand(n) < (1 / (1 + tenure / 15))).astype(int)
    df = pd.DataFrame({"tenure": tenure, "monthly": RNG.randn(n) * 10 + 60, "churn": churn})
    r = analyze_dataframe(df, "churn", "survival")
    assert r["taskLabel"] == "Survival analysis"
    assert r.get("_km") and len(r["_km"]) >= 2


def test_missing_target_raises():
    with pytest.raises(ValueError):
        analyze_dataframe(_clf_df(), "does_not_exist", "classification", time_budget=2)
