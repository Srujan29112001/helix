"""Real tabular analysis engine.

Takes an arbitrary CSV (as a DataFrame) + a target column and runs a genuine
ML workflow: clean → encode → train (FLAML AutoML, sklearn fallback) → evaluate
→ explain (SHAP, importance fallback) → EDA. Returns results in the same shape
the frontend already renders (``RunResults``), plus the list of cleaning
"fixes" applied (which the agents narrate as self-correction).

Everything is wrapped defensively so it degrades gracefully on messy data
instead of crashing.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _is_classification(y: pd.Series) -> bool:
    if y.dtype == object or str(y.dtype) == "category":
        return True
    if pd.api.types.is_float_dtype(y) and y.nunique() > 15:
        return False
    return y.nunique() <= 15


def clean(df: pd.DataFrame, target: str) -> tuple[pd.DataFrame, list[str]]:
    fixes: list[str] = []
    df = df.copy()

    stripped = {c: c.strip() for c in df.columns}
    if any(k != v for k, v in stripped.items()):
        df = df.rename(columns=stripped)
        fixes.append("stripped whitespace from column names")
    target = target.strip()

    # coerce numeric-looking object columns (e.g. Telco 'TotalCharges' has blanks)
    for col in df.columns:
        if col == target or df[col].dtype != object:
            continue
        coerced = pd.to_numeric(df[col], errors="coerce")
        valid = coerced.notna().sum()
        if valid >= 0.8 * len(df) and valid > 0:
            bad = int(df[col].notna().sum() - valid)
            df[col] = coerced
            if bad:
                fixes.append(f"coerced '{col}' to numeric ({bad} bad values -> NaN)")

    # drop id-like columns (name-based, or all-unique *string* keys — not continuous numbers)
    id_cols = [
        c
        for c in df.columns
        if c != target
        and (
            c.lower() == "id"
            or c.lower().endswith("id")
            or (
                df[c].dtype == object
                and df[c].nunique(dropna=False) == len(df)
                and df[c].astype(str).str.len().mean() < 25  # short keys, not free text
            )
        )
    ]
    if id_cols:
        df = df.drop(columns=id_cols)
        fixes.append("dropped identifier column(s): " + ", ".join(id_cols))

    # drop rows with a missing target
    before = len(df)
    df = df.dropna(subset=[target])
    if len(df) < before:
        fixes.append(f"dropped {before - len(df)} rows with a missing target")

    return df, fixes


def analyze_dataframe(
    df: pd.DataFrame,
    target: str,
    task: str = "auto",
    time_budget: int = 20,
) -> dict[str, Any]:
    df.columns = [c.strip() for c in df.columns]
    if task == "clustering":
        return _cluster(df)
    target = target.strip()
    if target not in df.columns:
        raise ValueError(f"target column '{target}' not found in dataset")

    df, fixes = clean(df, target)

    # sample very large data for speed
    if len(df) > 30000:
        df = df.sample(30000, random_state=42)
        fixes.append("sampled 30,000 rows for a fast run")

    y_raw = df[target]
    is_clf = _is_classification(y_raw) if task in ("auto", "nlp") else (task == "classification")
    X = df.drop(columns=[target]).copy()

    # NLP: detect & TF-IDF a free-text feature column
    text_terms: list[tuple[str, float]] = []
    for c in list(X.columns):
        if X[c].dtype == object:
            s = X[c].dropna().astype(str)
            if len(s) and s.str.len().mean() > 20 and s.nunique() >= 15:
                X, text_terms = _vectorize_text(X, c)
                fixes.append(f"vectorized text column '{c}' with TF-IDF")
                break

    # parse date columns into numeric parts (universal across domains)
    X = _extract_dates(X, fixes)

    # impute + encode features
    imputed = False
    for c in X.columns:
        if X[c].dtype == object or str(X[c].dtype) == "category":
            X[c] = X[c].astype("category").cat.codes  # NaN → -1
        else:
            if X[c].isna().any():
                X[c] = X[c].fillna(X[c].median())
                imputed = True
    if imputed:
        fixes.append("imputed missing numeric values with the median")
    n_cat = int(sum(df[c].dtype == object for c in df.columns if c != target))
    if n_cat:
        fixes.append(f"label-encoded {n_cat} categorical feature(s)")

    features = list(X.columns)

    # target encoding
    classes: list[Any] = []
    positive_label = None
    if is_clf:
        ycat = y_raw.astype("category")
        classes = list(ycat.cat.categories)
        y = ycat.cat.codes.to_numpy()
        binary = len(classes) == 2
        if binary:
            positive_label = classes[1]
    else:
        y = pd.to_numeric(y_raw, errors="coerce").to_numpy()
        binary = False

    from sklearn.model_selection import train_test_split

    strat = y if (is_clf and pd.Series(y).value_counts().min() >= 2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=strat
    )

    best_model = "model"
    proba = None
    try:
        from flaml import AutoML

        automl = AutoML()
        metric = ("roc_auc" if binary else "accuracy") if is_clf else "r2"
        automl.fit(
            X_train,
            y_train,
            task="classification" if is_clf else "regression",
            time_budget=time_budget,
            metric=metric,
            verbose=0,
            early_stop=True,
        )
        model = automl.model.estimator
        best_model = {
            "lgbm": "LightGBM",
            "xgboost": "XGBoost",
            "rf": "Random Forest",
            "extra_tree": "Extra Trees",
            "catboost": "CatBoost",
            "lrl1": "Logistic Regression",
            "lrl2": "Logistic Regression",
        }.get(str(automl.best_estimator), str(automl.best_estimator))
        preds = automl.predict(X_test)
        if is_clf:
            try:
                proba = automl.predict_proba(X_test)
            except Exception:
                proba = None
    except Exception:
        from sklearn.ensemble import (
            HistGradientBoostingClassifier,
            HistGradientBoostingRegressor,
        )

        if is_clf:
            model = HistGradientBoostingClassifier(random_state=42).fit(X_train, y_train)
            preds = model.predict(X_test)
            try:
                proba = model.predict_proba(X_test)
            except Exception:
                proba = None
        else:
            model = HistGradientBoostingRegressor(random_state=42).fit(X_train, y_train)
            preds = model.predict(X_test)
        best_model = "HistGradientBoosting"

    metrics, headline, task_label = _score(is_clf, binary, y_test, preds, proba)
    bars, bars_title = _importance(model, X, X_test, y_test, y, features, is_clf)
    if text_terms:  # NLP: surface themes instead of opaque TF-IDF dims
        bars = [{"label": t, "value": v} for t, v in text_terms]
        bars_title = "Top themes"
        task_label = "NLP + analytics"
    dist, dist_title = _eda(df, target, features, bars, is_clf, positive_label, y_raw)

    report, recommendation = _default_report(
        target, task_label, headline, bars, dist, dist_title
    )

    return {
        "taskLabel": task_label,
        "bestModel": best_model,
        "headline": headline,
        "metrics": metrics,
        "barsTitle": bars_title,
        "bars": bars,
        "distTitle": dist_title,
        "dist": dist,
        "report": report,
        "recommendation": recommendation,
        # extra metadata for the agents / self-heal narration
        "_fixes": fixes,
        "_features": features,
        "_target": target,
        "_rows": int(len(df)),
        "_cols": int(df.shape[1]),
        "_drivers": [
            {"feature": b["label"], "importance": round(b["value"], 2), "direction": b.get("sign", 0)}
            for b in bars[:4]
        ],
    }


def _score(is_clf, binary, y_test, preds, proba):
    if is_clf:
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        acc = accuracy_score(y_test, preds)
        metrics = [{"label": "Accuracy", "value": f"{acc:.2f}"}]
        head_frac, head_val, head_lbl = acc, f"{acc:.2f}", "Accuracy"
        if binary and proba is not None:
            try:
                auc = roc_auc_score(y_test, proba[:, 1])
                metrics.append({"label": "ROC-AUC", "value": f"{auc:.2f}"})
                head_frac, head_val, head_lbl = auc, f"{auc:.2f}", "ROC-AUC"
            except Exception:
                pass
        avg = "binary" if binary else "macro"
        metrics.append({"label": "Precision", "value": f"{precision_score(y_test, preds, average=avg, zero_division=0):.2f}"})
        metrics.append({"label": "Recall", "value": f"{recall_score(y_test, preds, average=avg, zero_division=0):.2f}"})
        metrics.append({"label": "F1", "value": f"{f1_score(y_test, preds, average=avg, zero_division=0):.2f}"})
        return metrics[:4], {"fraction": float(max(0, min(1, head_frac))), "value": head_val, "label": head_lbl}, "Binary classification" if binary else "Multiclass classification"

    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    r2 = r2_score(y_test, preds)
    rmse = math.sqrt(mean_squared_error(y_test, preds))
    mae = mean_absolute_error(y_test, preds)
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = np.where(np.abs(y_test) < 1e-9, np.nan, y_test)
        mape = np.nanmean(np.abs((y_test - preds) / denom)) * 100
    metrics = [
        {"label": "R2", "value": f"{r2:.2f}"},
        {"label": "RMSE", "value": f"{rmse:.0f}" if rmse >= 10 else f"{rmse:.2f}"},
        {"label": "MAE", "value": f"{mae:.0f}" if mae >= 10 else f"{mae:.2f}"},
        {"label": "MAPE", "value": f"{mape:.1f}%" if not math.isnan(mape) else "—"},
    ]
    return metrics, {"fraction": float(max(0, min(1, r2))), "value": f"{r2:.2f}", "label": "R2 score"}, "Regression"


def _importance(model, X, X_test, y_test, y, features, is_clf):
    importances = None
    signs = None
    title = "Feature importance"
    try:
        import shap

        sample = X_test.sample(min(200, len(X_test)), random_state=42)
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(sample)
        arr = sv[1] if isinstance(sv, list) and len(sv) > 1 else (sv[0] if isinstance(sv, list) else sv)
        arr = np.asarray(arr)
        if arr.ndim == 3:  # (n, features, classes)
            arr = arr[:, :, -1]
        importances = np.abs(arr).mean(axis=0)
        signs = np.sign(arr.mean(axis=0))
        title = "SHAP feature importance"
    except Exception:
        try:
            importances = np.asarray(model.feature_importances_, dtype=float)
        except Exception:
            from sklearn.inspection import permutation_importance

            pi = permutation_importance(model, X_test, y_test, n_repeats=4, random_state=42)
            importances = pi.importances_mean
        signs = []
        for c in features:
            try:
                corr = np.corrcoef(X[c].to_numpy(dtype=float), np.asarray(y, dtype=float))[0, 1]
                signs.append(np.sign(corr) if not math.isnan(corr) else 1)
            except Exception:
                signs.append(1)
        signs = np.asarray(signs)

    importances = np.nan_to_num(np.asarray(importances, dtype=float))
    order = np.argsort(importances)[::-1][:6]
    top = importances[order[0]] if len(order) and importances[order[0]] > 0 else 1.0
    bars = [
        {
            "label": str(features[i])[:22],
            "value": float(max(0.04, min(1.0, importances[i] / top))),
            "sign": int(signs[i]) if signs is not None and signs[i] != 0 else 1,
        }
        for i in order
    ]
    return bars, title


def _eda(df, target, features, bars, is_clf, positive_label, y_raw):
    try:
        if is_clf and positive_label is not None:
            cand = [
                b["label"]
                for b in bars
                if b["label"] in df.columns and df[b["label"]].nunique() <= 8
            ]
            col = cand[0] if cand else None
            if col is None:
                for c in df.columns:
                    if c != target and df[c].nunique() <= 8:
                        col = c
                        break
            if col is not None:
                rate = df.groupby(col)[target].apply(lambda s: (s == positive_label).mean())
                rate = rate.sort_values(ascending=False).head(5)
                items = [
                    {"label": str(k), "value": float(v), "display": f"{v * 100:.0f}%"}
                    for k, v in rate.items()
                ]
                return items, f"{target} rate by {col}"
        else:
            num = [b["label"] for b in bars if b["label"] in df.columns and pd.api.types.is_numeric_dtype(df[b["label"]])]
            col = num[0] if num else None
            if col is not None:
                binned = pd.qcut(df[col], q=4, duplicates="drop")
                grp = df.groupby(binned, observed=True)[target].mean()
                m = grp.max() or 1
                items = [
                    {"label": str(k), "value": float(v / m), "display": f"{v:.0f}" if v >= 10 else f"{v:.2f}"}
                    for k, v in grp.items()
                ]
                return items, f"Average {target} by {col}"
    except Exception:
        pass
    # fallback: target distribution
    vc = y_raw.value_counts(normalize=True).head(5)
    items = [{"label": str(k), "value": float(v), "display": f"{v * 100:.0f}%"} for k, v in vc.items()]
    return items, f"{target} distribution"


def _default_report(target, task_label, headline, bars, dist, dist_title):
    top = bars[0]["label"] if bars else "the top feature"
    second = bars[1]["label"] if len(bars) > 1 else "other factors"
    report = [
        f"The {task_label.lower()} model reached {headline['value']} {headline['label']} on held-out data. {top} is the single strongest driver of {target}, followed by {second}.",
        f"The breakdown '{dist_title}' shows where {target} concentrates, giving a clear, data-backed view to act on.",
    ]
    recommendation = f"Prioritise {top} — it has the largest measured effect on {target}."
    return report, recommendation


def _extract_dates(X: pd.DataFrame, fixes: list[str]) -> pd.DataFrame:
    """Turn date-like text columns into numeric year/month/day/weekday features."""
    import warnings as _w

    for c in list(X.columns):
        if X[c].dtype != object:
            continue
        s = X[c].dropna().astype(str)
        if not len(s) or s.str.len().mean() > 30:
            continue
        if s.str.contains(r"[-/:]", regex=True).mean() < 0.6:
            continue
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            parsed = pd.to_datetime(X[c], errors="coerce")
        if parsed.notna().mean() > 0.8:
            X[f"{c}_year"] = parsed.dt.year
            X[f"{c}_month"] = parsed.dt.month
            X[f"{c}_day"] = parsed.dt.day
            X[f"{c}_dow"] = parsed.dt.dayofweek
            X = X.drop(columns=[c])
            fixes.append(f"parsed '{c}' as datetime -> year/month/day/weekday")
    return X


def _vectorize_text(X: pd.DataFrame, col: str):
    """TF-IDF a free-text column; return (new_X, [(term, weight), ...])."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(max_features=60, stop_words="english")
    mat = vec.fit_transform(X[col].fillna("").astype(str))
    means = np.asarray(mat.mean(axis=0)).ravel()
    vocab = vec.get_feature_names_out()
    order = means.argsort()[::-1][:6]
    top = float(means[order[0]]) if len(order) and means[order[0]] > 0 else 1.0
    terms = [(str(vocab[i]), float(max(0.08, means[i] / top))) for i in order]
    tf = pd.DataFrame(
        mat.toarray(),
        columns=[f"tf_{i}" for i in range(mat.shape[1])],
        index=X.index,
    )
    return X.drop(columns=[col]).join(tf), terms


def _cluster(df: pd.DataFrame) -> dict[str, Any]:
    """Unsupervised KMeans with silhouette-based k selection."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    fixes: list[str] = []
    work = df.copy()
    ids = [
        c
        for c in work.columns
        if c.lower() == "id"
        or c.lower().endswith("id")
        or (
            work[c].dtype == object
            and work[c].nunique(dropna=False) == len(work)
            and work[c].astype(str).str.len().mean() < 25
        )
    ]
    if ids:
        work = work.drop(columns=ids)
        fixes.append("dropped identifier column(s): " + ", ".join(ids))
    for c in work.columns:
        if work[c].dtype == object:
            num = pd.to_numeric(work[c], errors="coerce")
            work[c] = num if num.notna().sum() >= 0.8 * len(work) else work[c].astype("category").cat.codes
    work = work.fillna(work.median(numeric_only=True)).select_dtypes(include="number")
    if work.shape[1] < 2:
        raise ValueError("clustering needs at least 2 numeric features")
    if len(work) > 20000:
        work = work.sample(20000, random_state=42)
        fixes.append("sampled 20,000 rows for a fast run")

    Xs = StandardScaler().fit_transform(work)
    best_k, best_sil, best_labels = 2, -1.0, None
    for k in range(2, min(9, len(work))):
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(Xs)
        sil = silhouette_score(Xs, labels)
        if sil > best_sil:
            best_k, best_sil, best_labels = k, sil, labels
    fixes.append(f"label-encoded {sum(df[c].dtype == object for c in df.columns)} categorical feature(s)")

    sizes = pd.Series(best_labels).value_counts(normalize=True).sort_index()
    dist = [
        {"label": f"Segment {i + 1}", "value": float(v), "display": f"{v * 100:.0f}%"}
        for i, v in enumerate(sizes)
    ]
    grouped = work.reset_index(drop=True).assign(_c=best_labels)
    sep = {c: float(grouped.groupby("_c")[c].mean().var()) for c in work.columns}
    order = sorted(sep, key=lambda c: -sep[c])[:6]
    mx = max(sep.values()) or 1.0
    bars = [{"label": str(c)[:22], "value": float(max(0.08, sep[c] / mx))} for c in order]
    second = order[1] if len(order) > 1 else order[0]

    return {
        "taskLabel": "Clustering",
        "bestModel": f"KMeans (k={best_k})",
        "headline": {"value": str(best_k), "label": "segments"},
        "metrics": [
            {"label": "Clusters", "value": str(best_k)},
            {"label": "Silhouette", "value": f"{best_sil:.2f}"},
            {"label": "Features", "value": str(work.shape[1])},
            {"label": "Samples", "value": str(len(work))},
        ],
        "barsTitle": "Defining dimensions",
        "bars": bars,
        "distTitle": "Segment sizes",
        "dist": dist,
        "report": [
            f"K-Means found {best_k} natural segments (silhouette {best_sil:.2f}). They separate most along {order[0]} and {second}.",
            "Each segment groups rows with a similar profile — ready for targeted strategies.",
        ],
        "recommendation": f"Profile the largest segment and differentiate strategy along {order[0]}.",
        "_fixes": fixes,
        "_features": list(work.columns),
        "_target": "(unsupervised)",
        "_rows": int(len(work)),
        "_cols": int(df.shape[1]),
        "_drivers": [{"feature": b["label"], "importance": round(b["value"], 2), "direction": 0} for b in bars[:4]],
    }
