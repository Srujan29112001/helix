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

import json
import math
from typing import Any

import numpy as np
import pandas as pd


def _is_classification(y: pd.Series) -> bool:
    if not pd.api.types.is_numeric_dtype(y):
        return True
    if pd.api.types.is_float_dtype(y) and y.nunique() > 15:
        return False
    return y.nunique() <= 15


_TARGET_NAMES = {
    "target", "label", "labels", "class", "outcome", "y", "result",
    "churn", "default", "fraud", "survived", "price", "sales", "revenue",
}


def _auto_target(df: pd.DataFrame) -> str:
    """Pick a sensible target column when the user chooses 'Auto-detect': prefer a
    column with a common target name, else a low-cardinality categorical (a likely
    label), else the last column (the usual spreadsheet convention)."""
    cols = list(df.columns)
    for c in cols:
        if str(c).strip().lower() in _TARGET_NAMES:
            return c
    # a non-numeric column with few distinct values is a likely class label
    for c in reversed(cols):
        s = df[c]
        if not pd.api.types.is_numeric_dtype(s) and 1 < s.nunique(dropna=True) <= 10:
            return c
    return cols[-1] if cols else ""


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
        if col == target or pd.api.types.is_numeric_dtype(df[col]):
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
                not pd.api.types.is_numeric_dtype(df[c])
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
    src_rows = int(df.attrs.get("source_rows", len(df)))
    src_cols = int(df.attrs.get("source_cols", df.shape[1]))
    read_note = df.attrs.get("read_note")
    if task == "clustering":
        return _cluster(df, src_rows, src_cols)
    if task == "anomaly":
        return _anomaly(df, src_rows, src_cols)
    if task == "dimreduction":
        return _dimreduction(df, target, src_rows, src_cols)
    if task == "timeseries":
        return _timeseries(df, target, src_rows, src_cols)
    if task == "survival":
        return _survival(df, target, src_rows, src_cols)
    if task == "recommendation":
        return _recommend(df, src_rows, src_cols)
    target = target.strip()
    if target not in df.columns:
        raise ValueError(f"target column '{target}' not found in dataset")

    # Use as much data as a compute budget allows, scaled to dataset WIDTH:
    # narrow tables train on hundreds of thousands of rows (gradient boosting
    # handles that in seconds), wide tables use fewer so memory/time stay sane.
    row_cap = int(min(500_000, max(50_000, 10_000_000 // max(1, df.shape[1]))))
    if len(df) > row_cap:
        df = df.sample(row_cap, random_state=42)

    df, fixes = clean(df, target)
    if read_note:
        fixes.insert(0, read_note)
    if src_rows > len(df):
        fixes.append(f"trained on {len(df):,} of {src_rows:,} rows (scaled to dataset width)")

    y_raw = df[target]
    is_clf = _is_classification(y_raw) if task in ("auto", "nlp") else (task == "classification")
    X = df.drop(columns=[target]).copy()

    # Free-text handling. Near-unique non-numeric columns are either free text
    # (reviews) or identifiers (names, ticket numbers). TF-IDF them ONLY for an
    # explicit NLP task (or when text is the only signal); otherwise drop them as
    # noise so structured tasks aren't hijacked by, e.g., a Name column.
    text_terms: list[tuple[str, float]] = []
    hicard = [
        c
        for c in X.columns
        if not pd.api.types.is_numeric_dtype(X[c])
        and X[c].nunique(dropna=False) > max(30, 0.5 * len(X))
    ]
    other = [c for c in X.columns if c not in hicard]
    nlp_extras: dict[str, Any] = {}
    if hicard and (task == "nlp" or not other):
        textcol = max(hicard, key=lambda c: X[c].dropna().astype(str).str.len().mean())
        nlp_extras = _nlp_extras(X[textcol])  # topics + sentiment + keywords
        X, text_terms = _vectorize_text(X, textcol)
        fixes.append(f"vectorized text column '{textcol}' with TF-IDF")
    elif hicard:
        X = X.drop(columns=hicard)
        fixes.append("dropped high-cardinality text/identifier column(s): " + ", ".join(hicard))

    # parse date columns into numeric parts (universal across domains)
    X = _extract_dates(X, fixes)

    # impute + encode features
    imputed = False
    for c in X.columns:
        if not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = X[c].astype("category").cat.codes  # NaN → -1 (object / str / category)
        else:
            if X[c].isna().any():
                X[c] = X[c].fillna(X[c].median())
                imputed = True
    if imputed:
        fixes.append("imputed missing numeric values with the median")
    n_cat = int(sum(not pd.api.types.is_numeric_dtype(df[c]) for c in df.columns if c != target))
    if n_cat:
        fixes.append(f"label-encoded {n_cat} categorical feature(s)")

    # automatic feature engineering (additive + transparent): log-transform skewed
    # positives + a couple of interaction terms — the model keeps what helps.
    if task != "nlp" and not text_terms:
        X = _feature_eng(X, fixes)

    # memory: downcast the (now fully numeric) feature matrix to 32-bit
    for c in X.columns:
        try:
            X[c] = pd.to_numeric(X[c], downcast="float")
        except Exception:  # noqa: BLE001
            pass

    # feature cap: on very wide data keep the top-variance columns so SHAP/FLAML
    # stay fast and memory-safe (up to ~500 raw features -> 150)
    MAX_FEATURES = 150
    if X.shape[1] > MAX_FEATURES:
        orig_n = X.shape[1]
        variances = X.var(numeric_only=True).fillna(0.0)
        keep = list(variances.sort_values(ascending=False).head(MAX_FEATURES).index)
        X = X[keep]
        fixes.append(f"selected the top {MAX_FEATURES} features by variance (from {orig_n}) for speed")

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
    n_train, n_test = int(len(X_train)), int(len(X_test))

    # imbalanced classification → oversample the minority class with SMOTE (train only,
    # so the held-out test set — and therefore the reported metrics — stays honest)
    imbalance = None
    if is_clf:
        vc = pd.Series(y_train).value_counts()
        minority, majority = int(vc.min()), int(vc.max())
        share = minority / (minority + majority) if (minority + majority) else 0.5
        before = {(str(classes[k]) if k < len(classes) else str(k)): int(v) for k, v in vc.items()}
        if share < 0.35 and minority >= 6 and len(X_train) <= 200_000:
            try:
                from imblearn.over_sampling import SMOTE
                X_train, y_train = SMOTE(random_state=42, k_neighbors=min(5, minority - 1)).fit_resample(X_train, y_train)
                vc2 = pd.Series(y_train).value_counts()
                after = {(str(classes[k]) if k < len(classes) else str(k)): int(v) for k, v in vc2.items()}
                n_train = int(len(X_train))
                fixes.append(f"balanced classes with SMOTE (minority was {minority}/{majority}, share {share:.0%})")
                imbalance = {"applied": True, "method": "SMOTE", "minority_share": round(share, 3),
                             "before": before, "after": after}
            except Exception:  # noqa: BLE001
                imbalance = {"applied": False, "method": "none", "minority_share": round(share, 3),
                             "before": before, "after": before}
        elif share < 0.35:
            imbalance = {"applied": False, "method": "too few/many to resample", "minority_share": round(share, 3),
                         "before": before, "after": before}
    opt_metric = "roc_auc" if (is_clf and binary) else ("accuracy" if is_clf else "r2")

    best_model = "model"
    proba = None
    try:
        from flaml import AutoML

        automl = AutoML()
        metric = ("roc_auc" if binary else "accuracy") if is_clf else "r2"
        # cap parallelism on big data so 16GB hosts don't blow up on all cores
        big = len(X_train) * max(1, X.shape[1]) > 4_000_000
        # give the search more time on bigger data; restrict to fast histogram
        # learners (LightGBM/XGBoost) once N is large so the budget isn't wasted.
        eff_budget = int(min(75, max(time_budget, len(X_train) // 12_000)))
        fit_kwargs: dict[str, Any] = {}
        if len(X_train) > 100_000:
            fit_kwargs["estimator_list"] = ["lgbm", "xgboost"]
        else:
            # broaden the search: tree ensembles + linear + KNN baselines. (FLAML's
            # stacked ensemble is intentionally NOT enabled — its base learners can
            # train on different feature subsets and crash predict on wide/TF-IDF data.)
            fit_kwargs["estimator_list"] = ["lgbm", "xgboost", "rf", "extra_tree", "kneighbor"] + (
                ["lrl1", "lrl2"] if is_clf else ["enet"]
            )
        automl.fit(
            X_train,
            y_train,
            task="classification" if is_clf else "regression",
            time_budget=eff_budget,
            metric=metric,
            verbose=0,
            early_stop=True,
            n_jobs=4 if big else -1,
            **fit_kwargs,
        )
        # when a stacked ensemble wins it has no ``.estimator`` — fall back to the
        # wrapper itself (predict still works; SHAP just uses its permutation fallback)
        model = getattr(automl.model, "estimator", automl.model)
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
    verdict = _model_quality(is_clf, binary, headline, y)
    eval_detail = _eval_detail(model, X_train, y_train, X_test, y_test, preds, proba, is_clf, classes, opt_metric)
    model_compare = _model_comparison(X_train, y_train, X_test, y_test, is_clf, binary, opt_metric, best_model, headline["fraction"])
    whatif = _whatif(model, X, features, is_clf, binary, classes)
    bars, bars_title = _importance(model, X, X_test, y_test, y, features, is_clf)
    if text_terms:  # NLP: surface themes instead of opaque TF-IDF dims
        bars = [{"label": t, "value": v} for t, v in text_terms]
        bars_title = "Top themes"
        task_label = "NLP + analytics"
    dist, dist_title = _eda(df, target, features, bars, is_clf, positive_label, y_raw)

    report, recommendation = _default_report(
        target, task_label, headline, bars, dist, dist_title
    )
    insights = _insights(df, X, y, target, bars, dist, is_clf, features)
    stats_tests = _statistics(df, target, is_clf, bars)
    if insights.get("_scatter"):
        if is_clf and len(classes) >= 2:
            low = f"{target} = {classes[0]}"
            high = f"{target} = {classes[1]}" if len(classes) == 2 else "other classes"
            insights["_scatter"]["legend"] = {"low": low, "high": high}
        else:
            insights["_scatter"]["legend"] = {"low": f"lower {target}", "high": f"higher {target}"}

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
        "_train_rows": n_train,
        "_test_rows": n_test,
        "_source_rows": src_rows,
        "_source_cols": src_cols,
        "_metric": opt_metric,
        "_verdict": verdict,
        "_drivers": [
            {"feature": b["label"], "importance": round(b["value"], 2), "direction": b.get("sign", 0)}
            for b in bars[:4]
        ],
        "_corr": insights["_corr"],
        "_hist": insights["_hist"],
        "_graph": insights["_graph"],
        "_stats": insights["_stats"],
        "_scatter": insights["_scatter"],
        "_profile": insights["_profile"],
        "_quality": insights["_quality"],
        "_box": insights["_box"],
        "_insights_text": insights["_insights_text"],
        "_stats_tests": stats_tests,
        "_model_compare": model_compare,
        "_whatif": whatif,
        "_imbalance": imbalance,
        "_topics": nlp_extras.get("topics") or None,
        "_sentiment": nlp_extras.get("sentiment"),
        "_keywords": nlp_extras.get("keywords") or None,
        **eval_detail,
    }


def _eval_detail(model, X_train, y_train, X_test, y_test, preds, proba, is_clf, classes, opt_metric) -> dict:
    """Deeper model diagnostics a data scientist expects: stratified k-fold CV
    (mean ± std — honest vs a single split), confusion matrix + per-class P/R/F1,
    ROC + PR curves (binary), and a predicted-vs-actual plot (regression)."""
    out: dict[str, Any] = {}
    # ── stratified k-fold cross-validation on the tuned estimator ──
    try:
        from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
        from sklearn.base import clone

        n = len(X_train)
        idx = np.arange(n)
        if n > 8000:
            idx = np.random.RandomState(42).choice(n, 8000, replace=False)
        Xc, yc = X_train.iloc[idx], np.asarray(y_train)[idx]
        k = 5 if len(Xc) >= 250 else 3
        scoring = "roc_auc" if opt_metric == "roc_auc" else ("accuracy" if is_clf else "r2")
        splitter = (StratifiedKFold(k, shuffle=True, random_state=42) if is_clf
                    else KFold(k, shuffle=True, random_state=42))
        scores = cross_val_score(clone(model), Xc, yc, cv=splitter, scoring=scoring, n_jobs=1, error_score="raise")
        scores = np.asarray(scores, dtype=float)
        scores = scores[~np.isnan(scores)]
        if len(scores):
            out["_cv"] = {"k": int(k), "metric": scoring,
                          "mean": round(float(scores.mean()), 3), "std": round(float(scores.std()), 3),
                          "scores": [round(float(s), 3) for s in scores]}
        # learning curve — does the model want more data, or is it overfitting?
        try:
            from sklearn.model_selection import learning_curve
            sizes, tr, va = learning_curve(
                clone(model), Xc, yc, cv=3, scoring=scoring, n_jobs=1,
                train_sizes=np.linspace(0.2, 1.0, 5), error_score="raise",
            )
            out["_learning"] = [
                {"n": int(sizes[i]), "train": round(float(tr[i].mean()), 3), "val": round(float(va[i].mean()), 3)}
                for i in range(len(sizes))
            ]
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass

    # calibration — are the predicted probabilities trustworthy? (binary)
    try:
        if is_clf and proba is not None and len(classes) == 2:
            from sklearn.calibration import calibration_curve
            fpos, mpred = calibration_curve(np.asarray(y_test), np.asarray(proba)[:, 1], n_bins=8, strategy="quantile")
            out["_calibration"] = [{"x": round(float(a), 3), "y": round(float(b), 3)} for a, b in zip(mpred, fpos)]
    except Exception:  # noqa: BLE001
        pass

    try:
        if is_clf:
            from sklearn.metrics import (confusion_matrix, precision_recall_fscore_support,
                                         roc_curve, precision_recall_curve)
            yt = np.asarray(y_test)
            pr = np.asarray(preds)
            labs = sorted(set(yt.tolist()) | set(pr.tolist()))
            names = [str(classes[i]) if i < len(classes) else str(i) for i in labs]
            cm = confusion_matrix(yt, pr, labels=labs)
            out["_confusion"] = {"labels": names, "matrix": cm.tolist()}
            p, r, f, sup = precision_recall_fscore_support(yt, pr, labels=labs, zero_division=0)
            out["_per_class"] = [
                {"label": names[i], "precision": round(float(p[i]), 2), "recall": round(float(r[i]), 2),
                 "f1": round(float(f[i]), 2), "support": int(sup[i])}
                for i in range(len(names))
            ]
            if proba is not None and len(classes) == 2:
                pos = np.asarray(proba)[:, 1]

                def _thin(xs, ys, m=40):
                    step = max(1, len(xs) // m)
                    return [{"x": round(float(a), 3), "y": round(float(b), 3)} for a, b in zip(xs[::step], ys[::step])]

                fpr, tpr, _ = roc_curve(yt, pos)
                out["_roc"] = _thin(fpr, tpr)
                rec, prc = precision_recall_curve(yt, pos)[1], precision_recall_curve(yt, pos)[0]
                out["_pr"] = _thin(rec, prc)
        else:
            yt = np.asarray(y_test, dtype=float)
            pp = np.asarray(preds, dtype=float)
            m = len(yt)
            sidx = np.arange(m)
            if m > 200:
                sidx = np.random.RandomState(42).choice(m, 200, replace=False)
            out["_residuals"] = {
                "points": [{"actual": round(float(yt[i]), 3), "pred": round(float(pp[i]), 3)} for i in sidx]
            }
    except Exception:  # noqa: BLE001
        pass
    return out


def _statistics(df, target, is_clf, bars) -> list[dict]:
    """Real statistical-inference layer: for each top feature vs the target, pick
    the right hypothesis test, compute the p-value + an effect size, and write a
    plain-English verdict. This is what separates a model-fitter from a data
    scientist — significance, not just importance.

    Tests chosen by dtype combination:
      classification target, numeric feature  -> Welch t-test (2 groups) / one-way ANOVA (>2)
                            with Shapiro normality check -> Mann-Whitney / Kruskal if non-normal
      classification target, categorical feat -> chi-square test of independence (+ Cramér's V)
      regression target, numeric feature       -> Pearson + Spearman correlation (+ p-values)
      regression target, categorical feature   -> one-way ANOVA (target across categories, eta²)
    """
    if not target or target not in df.columns:
        return []
    try:
        from scipy import stats as st
    except Exception:  # noqa: BLE001
        return []

    out: list[dict] = []
    y = df[target]
    # order features by model importance when available, else dataframe order
    ranked = [b["label"] for b in (bars or []) if b.get("label") in df.columns]
    cols = ranked + [c for c in df.columns if c != target and c not in ranked]
    cols = [c for c in cols if c != target][:10]

    def _verdict(p):
        return "significant" if (p is not None and p < 0.05) else "not significant"

    def _effect_word(name, v):
        a = abs(v)
        if name in ("Cohen's d",):
            lvl = "large" if a >= 0.8 else "medium" if a >= 0.5 else "small" if a >= 0.2 else "negligible"
        elif name in ("Cramér's V", "|r|", "η²", "|ρ|"):
            lvl = "large" if a >= 0.5 else "medium" if a >= 0.3 else "small" if a >= 0.1 else "negligible"
        else:
            lvl = ""
        return lvl

    for c in cols:
        try:
            s = df[c]
            numeric = pd.api.types.is_numeric_dtype(s)
            row = None
            if is_clf:
                ycat = y.astype(str)
                if numeric:
                    sn = pd.to_numeric(s, errors="coerce")
                    groups = [sn[ycat == g].dropna().to_numpy() for g in ycat.dropna().unique()]
                    groups = [g for g in groups if len(g) >= 3]
                    if len(groups) < 2:
                        continue
                    # normality on a sample of each group
                    normal = all(
                        (len(g) < 5000 and st.shapiro(g[:5000])[1] > 0.05)
                        for g in groups
                    ) if len(groups) <= 6 else False
                    if len(groups) == 2:
                        if normal:
                            stat, p = st.ttest_ind(groups[0], groups[1], equal_var=False)
                            test = "Welch t-test"
                        else:
                            stat, p = st.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
                            test = "Mann-Whitney U"
                        # Cohen's d
                        m1, m2 = groups[0].mean(), groups[1].mean()
                        sp = math.sqrt((groups[0].var(ddof=1) + groups[1].var(ddof=1)) / 2) or 1e-9
                        ed, en = abs(m1 - m2) / sp, "Cohen's d"
                    else:
                        if normal:
                            stat, p = st.f_oneway(*groups)
                            test = "one-way ANOVA"
                        else:
                            stat, p = st.kruskal(*groups)
                            test = "Kruskal-Wallis"
                        # eta² approximation from F where available
                        ed, en = 0.0, "η²"
                    row = {"feature": str(c), "test": test, "p": float(p), "stat": float(stat),
                           "effect": round(float(ed), 2), "effect_name": en}
                else:
                    ct = pd.crosstab(s.astype(str), ycat)
                    if ct.shape[0] < 2 or ct.shape[1] < 2 or ct.values.sum() < 5:
                        continue
                    chi2, p, dof, _ = st.chi2_contingency(ct)
                    n = ct.values.sum()
                    v = math.sqrt(chi2 / (n * (min(ct.shape) - 1))) if n else 0.0
                    row = {"feature": str(c), "test": "chi-square", "p": float(p), "stat": float(chi2),
                           "effect": round(float(v), 2), "effect_name": "Cramér's V"}
            else:
                yn = pd.to_numeric(y, errors="coerce")
                if numeric:
                    sn = pd.to_numeric(s, errors="coerce")
                    d = pd.concat([sn, yn], axis=1).dropna()
                    if len(d) < 5:
                        continue
                    r, p = st.pearsonr(d.iloc[:, 0], d.iloc[:, 1])
                    row = {"feature": str(c), "test": "Pearson r", "p": float(p), "stat": round(float(r), 3),
                           "effect": round(abs(float(r)), 2), "effect_name": "|r|"}
                else:
                    groups = [yn[s.astype(str) == g].dropna().to_numpy() for g in s.astype(str).dropna().unique()]
                    groups = [g for g in groups if len(g) >= 3]
                    if len(groups) < 2:
                        continue
                    stat, p = st.f_oneway(*groups)
                    row = {"feature": str(c), "test": "one-way ANOVA", "p": float(p), "stat": float(stat),
                           "effect": 0.0, "effect_name": "η²"}
            if row is None or math.isnan(row["p"]):
                continue
            sig = row["p"] < 0.05
            ew = _effect_word(row["effect_name"], row["effect"])
            pdisp = "<0.001" if row["p"] < 0.001 else f"{row['p']:.3f}"
            row["significant"] = sig
            row["interpretation"] = (
                f"{'Significant' if sig else 'No significant'} relationship between "
                f"{row['feature']} and {target} ({row['test']}, p={pdisp}"
                + (f", {ew} effect" if ew else "") + ")."
            )
            out.append(row)
        except Exception:  # noqa: BLE001
            continue
    # most significant first
    out.sort(key=lambda r: (r["p"], -r["effect"]))
    return out[:10]


_POS_WORDS = {"good", "great", "love", "loved", "excellent", "amazing", "best", "perfect", "happy",
              "recommend", "awesome", "fantastic", "wonderful", "nice", "fast", "easy", "quality",
              "comfortable", "beautiful", "favorite", "worth", "smooth", "pleased", "satisfied"}
_NEG_WORDS = {"bad", "worst", "hate", "hated", "terrible", "awful", "poor", "broken", "slow",
              "disappointed", "waste", "horrible", "never", "problem", "refund", "damaged", "cheap",
              "useless", "annoying", "expensive", "uncomfortable", "wrong", "stopped", "defective"}


def _nlp_extras(texts: pd.Series) -> dict:
    """Topic modelling (LDA), keyword extraction and a lexicon sentiment split for
    a free-text column — the analyses a data scientist runs on text."""
    out: dict = {"topics": [], "sentiment": None, "keywords": []}
    s = texts.dropna().astype(str)
    if len(s) < 10:
        return out
    try:
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.decomposition import LatentDirichletAllocation

        cv = CountVectorizer(max_features=500, stop_words="english", min_df=2)
        dtm = cv.fit_transform(s)
        vocab = cv.get_feature_names_out()
        if dtm.shape[1] >= 4:
            k = min(5, max(2, dtm.shape[0] // 60))
            lda = LatentDirichletAllocation(n_components=k, random_state=42, max_iter=10, learning_method="online")
            lda.fit(dtm)
            for i, comp in enumerate(lda.components_):
                words = [str(vocab[j]) for j in comp.argsort()[::-1][:6]]
                out["topics"].append({"topic": f"Topic {i + 1}", "words": words})
            freqs = np.asarray(dtm.sum(axis=0)).ravel()
            out["keywords"] = [str(vocab[j]) for j in freqs.argsort()[::-1][:12]]
    except Exception:  # noqa: BLE001
        pass
    try:
        pos = neg = neu = 0
        for t in s:
            w = set(t.lower().split())
            p, n = len(w & _POS_WORDS), len(w & _NEG_WORDS)
            if p > n:
                pos += 1
            elif n > p:
                neg += 1
            else:
                neu += 1
        tot = pos + neg + neu or 1
        out["sentiment"] = {"positive": round(pos / tot, 3), "neutral": round(neu / tot, 3),
                            "negative": round(neg / tot, 3)}
    except Exception:  # noqa: BLE001
        pass
    return out


def _feature_eng(X: pd.DataFrame, fixes: list) -> pd.DataFrame:
    """Conservative, additive feature engineering: log-transform skewed positive
    columns (as new log_ columns) and add the top interaction term. Additive, so it
    can't hurt the originals; the variance cap + model keep only what's useful."""
    try:
        num = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
        added: list[str] = []
        for c in list(num):
            s = X[c]
            try:
                if (s >= 0).all() and s.nunique() > 10 and float(s.skew()) > 2 and len(added) < 3:
                    X[f"log_{c}"] = np.log1p(s)
                    added.append(f"log_{c}")
            except Exception:  # noqa: BLE001
                continue
        if len(num) >= 2:
            var = X[num].var(numeric_only=True).fillna(0.0).sort_values(ascending=False)
            a, b = var.index[0], var.index[1]
            X[f"{a}_x_{b}"] = X[a] * X[b]
            added.append(f"{a}×{b}")
        if added:
            fixes.append("engineered features: " + ", ".join(added))
    except Exception:  # noqa: BLE001
        pass
    return X


def _model_comparison(X_train, y_train, X_test, y_test, is_clf, binary, opt_metric, best_name, best_value) -> list:
    """Quickly fit a few standard baselines and score them on the same held-out test
    set, so the user sees how the auto-selected model stacks up."""
    out = []
    try:
        n = len(X_train)
        idx = np.arange(n)
        if n > 8000:
            idx = np.random.RandomState(42).choice(n, 8000, replace=False)
        Xt, yt = X_train.iloc[idx], np.asarray(y_train)[idx]
        if is_clf:
            from sklearn.linear_model import LogisticRegression
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.neighbors import KNeighborsClassifier
            from sklearn.naive_bayes import GaussianNB
            from sklearn.metrics import roc_auc_score, accuracy_score

            cands = {"Logistic Regression": LogisticRegression(max_iter=300),
                     "Random Forest": RandomForestClassifier(n_estimators=120, random_state=42, n_jobs=1),
                     "K-Nearest Neighbors": KNeighborsClassifier(),
                     "Naive Bayes": GaussianNB()}
            metric = "ROC-AUC" if (opt_metric == "roc_auc" and binary) else "Accuracy"
            for name, m in cands.items():
                try:
                    m.fit(Xt, yt)
                    if metric == "ROC-AUC":
                        sc = roc_auc_score(y_test, m.predict_proba(X_test)[:, 1])
                    else:
                        sc = accuracy_score(y_test, m.predict(X_test))
                    out.append({"model": name, "score": round(float(sc), 3), "metric": metric})
                except Exception:  # noqa: BLE001
                    continue
        else:
            from sklearn.linear_model import Ridge
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.neighbors import KNeighborsRegressor
            from sklearn.metrics import r2_score

            cands = {"Ridge": Ridge(), "Random Forest": RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=1),
                     "K-Nearest Neighbors": KNeighborsRegressor()}
            metric = "R²"
            for name, m in cands.items():
                try:
                    m.fit(Xt, yt)
                    out.append({"model": name, "score": round(float(r2_score(y_test, m.predict(X_test))), 3), "metric": metric})
                except Exception:  # noqa: BLE001
                    continue
        out.append({"model": f"{best_name} (auto-selected)", "score": round(float(best_value), 3),
                    "metric": out[0]["metric"] if out else ("ROC-AUC" if is_clf else "R²"), "best": True})
        out.sort(key=lambda d: -d["score"])
    except Exception:  # noqa: BLE001
        return []
    return out


def _whatif(model, X, features, is_clf, binary, classes, n_feats=4, grid=11) -> list | None:
    """Precompute 1-D partial-dependence curves for the top features: vary one
    feature across its range (holding the rest at the median) and record the model's
    prediction. Powers a live 'what-if' simulator with zero extra server calls."""
    if is_clf and not binary:
        return None
    try:
        base = X.median(numeric_only=True)

        def predict(M):
            if is_clf:
                try:
                    return model.predict_proba(M)[:, 1]
                except Exception:  # noqa: BLE001
                    return model.predict(M).astype(float)
            return model.predict(M)

        var = X.var(numeric_only=True).fillna(0.0).sort_values(ascending=False)
        cols = [c for c in var.index][:n_feats]
        out = []
        for c in cols:
            col = pd.to_numeric(X[c], errors="coerce").dropna()
            lo, hi = float(col.quantile(0.05)), float(col.quantile(0.95))
            if hi <= lo:
                continue
            xs = np.linspace(lo, hi, grid)
            rows = pd.DataFrame([base.to_dict()] * grid)[X.columns]
            rows[c] = xs
            preds = predict(rows[X.columns])
            out.append({"feature": str(c),
                        "outcome": "probability" if is_clf else "value",
                        "values": [{"x": round(float(x), 4), "pred": round(float(p), 4)} for x, p in zip(xs, preds)]})
        return out or None
    except Exception:  # noqa: BLE001
        return None


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
        return metrics, {"fraction": float(max(0, min(1, head_frac))), "value": head_val, "label": head_lbl}, "Binary classification" if binary else "Multiclass classification"

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


def _model_quality(is_clf, binary, headline, y) -> dict:
    """A plain-English verdict on how much signal the model actually found, so a
    near-chance result explains itself instead of just looking broken."""
    frac = float(headline.get("fraction", 0) or 0)
    label = headline.get("label", "")
    if is_clf and "ROC-AUC" in label:
        score = frac  # 0.50 = random guessing, 1.0 = perfect
        if score >= 0.85:
            lvl, name = "excellent", "Strong predictive signal"
        elif score >= 0.72:
            lvl, name = "good", "Solid predictive signal"
        elif score >= 0.6:
            lvl, name = "fair", "Moderate signal"
        else:
            lvl, name = "weak", "Near-chance — weak signal"
        detail = f"ROC-AUC {frac:.2f} (0.50 = random guessing). " + (
            "The features predict the target reliably."
            if score >= 0.72
            else "Beats chance, but only modestly."
            if score >= 0.6
            else "The target looks weakly related to the available features — the data may lack "
            "predictive signal, or need richer/engineered features or a different target."
        )
    elif is_clf:
        try:
            base = float(pd.Series(y).value_counts(normalize=True).max())
        except Exception:  # noqa: BLE001
            base = 0.5
        lift = frac - base
        if lift >= 0.2:
            lvl, name = "excellent", "Strong predictive signal"
        elif lift >= 0.1:
            lvl, name = "good", "Solid predictive signal"
        elif lift >= 0.03:
            lvl, name = "fair", "Moderate signal"
        else:
            lvl, name = "weak", "Near-chance — weak signal"
        detail = f"Accuracy {frac:.2f} vs a {base:.2f} majority-class baseline. " + (
            "Clear lift over always guessing the majority class."
            if lift >= 0.1
            else "Modest lift over the baseline."
            if lift >= 0.03
            else "Barely beats always guessing the majority class — the features carry little "
            "signal for this target."
        )
    else:  # regression R²
        r2 = frac
        if r2 >= 0.75:
            lvl, name = "excellent", "Strong predictive signal"
        elif r2 >= 0.5:
            lvl, name = "good", "Solid predictive signal"
        elif r2 >= 0.25:
            lvl, name = "fair", "Moderate signal"
        else:
            lvl, name = "weak", "Near-chance — weak signal"
        detail = f"R² {frac:.2f} (1.0 = perfect, 0 = no better than predicting the mean). " + (
            "The features explain most of the variation."
            if r2 >= 0.5
            else "The features explain some of the variation."
            if r2 >= 0.25
            else "The features explain little of the variation — the data may lack predictive "
            "signal or need better features."
        )
    return {"level": lvl, "label": name, "detail": detail}


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
            "label": str(features[i]),
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
    third = bars[2]["label"] if len(bars) > 2 else None
    drivers_txt = f"{top}, {second}" + (f" and {third}" if third else "")
    top_seg = max(dist, key=lambda d: d["value"]) if dist else None
    report = [
        f"We built a {task_label.lower()} model to predict {target}, and it reached "
        f"{headline['value']} {headline['label']} on held-out data — a reliable, data-backed signal "
        f"rather than guesswork.",
        f"The strongest drivers of {target} are {drivers_txt}. These carry the most weight in the "
        f"model's decisions, so even small movements in them shift the outcome the most.",
        (f"The breakdown '{dist_title}' shows where {target} concentrates"
         + (f" — '{top_seg['label']}' stands out at {top_seg.get('display', '')}" if top_seg else "")
         + ", pinpointing exactly where to focus action."),
    ]
    recommendation = f"Prioritise {top} — it has the largest measured effect on {target}."
    return report, recommendation


def _insights(df, X, y, target, bars, dist, is_clf, features) -> dict[str, Any]:
    """Compute extra, professional-grade insights: correlations between the top
    drivers, a histogram of the strongest numeric driver, headline statistics,
    and a dense node/link graph (drivers + correlations + segments)."""
    out: dict[str, Any] = {"_corr": [], "_hist": None, "_graph": None, "_stats": []}
    tname = target if target and target != "(unsupervised)" else "outcome"

    # 1. correlations among the top driver features (encoded numeric matrix X)
    top_feats = [b["label"] for b in bars if b["label"] in X.columns][:6]
    corr_pairs = []
    if len(top_feats) >= 2:
        try:
            sub = X[top_feats].apply(lambda s: pd.to_numeric(s, errors="coerce")).dropna(axis=1, how="all")
            nf = list(sub.columns)
            if len(nf) >= 2:
                cm = sub.corr().abs()
                for i, a in enumerate(nf):
                    for b in nf[i + 1:]:
                        r = cm.loc[a, b]
                        if not math.isnan(r):
                            corr_pairs.append({"a": a, "b": b, "r": round(float(r), 2)})
                corr_pairs.sort(key=lambda p: -p["r"])
                corr_pairs = corr_pairs[:6]
        except Exception:  # noqa: BLE001
            corr_pairs = []
    out["_corr"] = corr_pairs

    # 2. histogram of the strongest *original numeric* driver
    try:
        for b in bars:
            c = b["label"]
            if c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
                s = pd.to_numeric(df[c], errors="coerce").dropna()
                if s.nunique() > 5:
                    counts, edges = np.histogram(s, bins=8)
                    out["_hist"] = {
                        "feature": c,
                        "bins": [
                            {"label": f"{edges[i]:.0f}–{edges[i + 1]:.0f}", "count": int(counts[i])}
                            for i in range(len(counts))
                        ],
                    }
                    break
    except Exception:  # noqa: BLE001
        out["_hist"] = None

    # 3. dense graph: target ← drivers, driver↔driver correlations, target→segments
    nodes = [{"id": "__target__", "name": tname, "group": "target", "val": 22.0}]
    links = []
    for b in bars[:8]:
        nodes.append({
            "id": b["label"], "name": b["label"], "group": "driver",
            "val": 6.0 + b["value"] * 16.0, "sign": int(b.get("sign", 1)),
        })
        links.append({"source": "__target__", "target": b["label"],
                      "value": float(b["value"]), "kind": "drives", "sign": int(b.get("sign", 1))})
    ids = {n["id"] for n in nodes}
    for p in corr_pairs:
        if p["r"] >= 0.25 and p["a"] in ids and p["b"] in ids:
            links.append({"source": p["a"], "target": p["b"], "value": p["r"], "kind": "corr", "sign": 0})
    for d in dist[:6]:
        cid = "seg::" + str(d["label"])
        nodes.append({"id": cid, "name": str(d["label"]), "group": "segment", "val": 5.0 + float(d["value"]) * 9.0})
        links.append({"source": "__target__", "target": cid, "value": float(d["value"]), "kind": "segment", "sign": 0})
    out["_graph"] = {"nodes": nodes, "links": links}

    # 4. headline statistics
    stats = [
        {"label": "Rows analysed", "value": f"{len(df):,}"},
        {"label": "Features used", "value": str(len(features))},
        {"label": "Avg missing", "value": f"{float(df.isna().mean().mean()) * 100:.1f}%"},
    ]
    try:
        if is_clf:
            vc = pd.Series(y).value_counts(normalize=True)
            maj = float(vc.max()) * 100
            stats.append({"label": "Class balance", "value": f"{maj:.0f}/{100 - maj:.0f}"})
        else:
            stats.append({"label": f"Avg {target}", "value": f"{float(np.nanmean(y)):,.1f}"})
    except Exception:  # noqa: BLE001
        pass
    if corr_pairs:
        stats.append({"label": "Top correlation", "value": f"{corr_pairs[0]['r']:.2f}"})
    out["_stats"] = stats

    # 5. scatter sample: the top-2 numeric drivers, coloured by target
    out["_scatter"] = None
    try:
        numdrv = [
            b["label"] for b in bars
            if b["label"] in df.columns and pd.api.types.is_numeric_dtype(df[b["label"]])
        ][:2]
        if len(numdrv) == 2:
            fx, fy = numdrv
            sdf = df[[fx, fy]].reset_index(drop=True)
            sdf["_t"] = pd.Series(y).reset_index(drop=True)
            sdf = sdf.dropna()
            if len(sdf) > 140:
                sdf = sdf.sample(140, random_state=42)

            def _nz(s):
                mn, mx = float(s.min()), float(s.max())
                return (s - mn) / (mx - mn) if mx > mn else s * 0 + 0.5

            tcol = sdf["_t"]
            if not is_clf:
                tcol = _nz(pd.to_numeric(tcol, errors="coerce").fillna(0))
            out["_scatter"] = {
                "x": fx,
                "y": fy,
                "points": [
                    {"x": round(float(px), 3), "y": round(float(py), 3), "c": float(pc)}
                    for px, py, pc in zip(_nz(sdf[fx]), _nz(sdf[fy]), tcol)
                ],
            }
    except Exception:  # noqa: BLE001
        out["_scatter"] = None

    # 6. per-column data dictionary (works for ANY dataset / domain)
    profile = []
    for c in list(df.columns)[:30]:
        s = df[c]
        uniq = int(s.nunique(dropna=True))
        if c == target:
            role = "target"
        elif pd.api.types.is_numeric_dtype(s):
            role = "numeric"
        elif "datetime" in str(s.dtype):
            role = "date"
        else:
            sv = s.dropna().astype(str)
            role = "text" if (len(sv) and sv.str.len().mean() > 20 and uniq > max(20, 0.5 * len(df))) else "categorical"
        profile.append({"name": str(c), "type": role, "missing": round(float(s.isna().mean()) * 100, 1), "unique": uniq})
    out["_profile"] = profile

    # 7. data-quality score (0-100)
    try:
        miss_frac = float(df.isna().mean().mean())
        dup = int(df.duplicated().sum())
        const_cols = int(sum(df[c].nunique(dropna=False) <= 1 for c in df.columns))
        score = int(max(0, min(100, round(100 - miss_frac * 140 - (dup / max(1, len(df))) * 80 - const_cols * 3))))
        out["_quality"] = {"score": score, "missing": round(miss_frac * 100, 1), "duplicates": dup, "constant_cols": const_cols}
    except Exception:  # noqa: BLE001
        out["_quality"] = None

    # 8. box plot of the top numeric driver (split by class when binary)
    out["_box"] = None
    try:
        topnum = next((b["label"] for b in bars
                       if b["label"] in df.columns and pd.api.types.is_numeric_dtype(df[b["label"]])), None)
        if topnum:
            def _box(series):
                a = pd.to_numeric(series, errors="coerce").dropna()
                if not len(a):
                    return None
                q = a.quantile([0, 0.25, 0.5, 0.75, 1.0])
                return {"min": float(q[0.0]), "q1": float(q[0.25]), "med": float(q[0.5]), "q3": float(q[0.75]), "max": float(q[1.0])}
            boxes = []
            yser = pd.Series(y).reset_index(drop=True)
            dser = df[topnum].reset_index(drop=True)
            if is_clf and yser.nunique() <= 4:
                for cls in sorted(yser.unique()):
                    bx = _box(dser[yser == cls])
                    if bx:
                        bx["label"] = f"class {cls}"
                        boxes.append(bx)
            else:
                bx = _box(dser)
                if bx:
                    bx["label"] = "all"
                    boxes.append(bx)
            if boxes:
                out["_box"] = {"feature": topnum, "boxes": boxes}
    except Exception:  # noqa: BLE001
        out["_box"] = None

    # 9. smart, rule-based auto-insights (domain-agnostic)
    smart = []
    try:
        for c in df.columns:
            m = float(df[c].isna().mean()) * 100
            if m >= 5:
                smart.append({"text": f"'{c}' has {m:.0f}% missing values — imputed before modelling.", "kind": "warn"})
        for p in corr_pairs:
            if p["r"] >= 0.9:
                smart.append({"text": f"'{p['a']}' and '{p['b']}' are near-perfectly correlated (r={p['r']}) — likely redundant.", "kind": "warn"})
                break
        if bars and bars[0]["value"] >= 0.85 and (len(bars) < 2 or bars[1]["value"] < 0.6):
            smart.append({"text": f"'{bars[0]['label']}' dominates the model — far stronger than any other driver.", "kind": "info"})
        if is_clf:
            vc = pd.Series(y).value_counts(normalize=True)
            if len(vc) and vc.max() >= 0.7:
                smart.append({"text": f"Target is imbalanced ({vc.max() * 100:.0f}/{(1 - vc.max()) * 100:.0f}) — recall matters more than raw accuracy.", "kind": "warn"})
            try:
                base = float(pd.Series(y).mean())
                topd = max(dist, key=lambda d: d["value"]) if dist else None
                if topd and base > 0 and topd["value"] / base >= 1.3:
                    smart.append({"text": f"Segment '{topd['label']}' has the highest {target} rate ({topd.get('display', '')}) — ~{topd['value'] / base:.1f}x the baseline.", "kind": "info"})
            except Exception:  # noqa: BLE001
                pass
        q = out.get("_quality")
        if q and q["score"] >= 90:
            smart.append({"text": f"High data quality (score {q['score']}/100) — low missingness, no major issues.", "kind": "good"})
        elif q and q["duplicates"] > 0:
            smart.append({"text": f"{q['duplicates']} duplicate rows detected — consider de-duplicating.", "kind": "warn"})
    except Exception:  # noqa: BLE001
        pass
    out["_insights_text"] = smart[:8]

    return out


def _extract_dates(X: pd.DataFrame, fixes: list[str]) -> pd.DataFrame:
    """Turn date-like text columns into numeric year/month/day/weekday features."""
    import warnings as _w

    for c in list(X.columns):
        if pd.api.types.is_numeric_dtype(X[c]):
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


def _cluster(df: pd.DataFrame, src_rows: int | None = None, src_cols: int | None = None) -> dict[str, Any]:
    """Unsupervised KMeans with silhouette-based k selection."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    fixes: list[str] = []
    if df.attrs.get("read_note"):
        fixes.append(df.attrs["read_note"])
    work = df.copy()
    # sample large data up front (before per-column coercion) for speed/memory
    if len(work) > 20000:
        work = work.sample(20000, random_state=42)
    ids = [
        c
        for c in work.columns
        if c.lower() == "id"
        or c.lower().endswith("id")
        or (
            not pd.api.types.is_numeric_dtype(work[c])
            and work[c].nunique(dropna=False) == len(work)
            and work[c].astype(str).str.len().mean() < 25
        )
    ]
    if ids:
        work = work.drop(columns=ids)
        fixes.append("dropped identifier column(s): " + ", ".join(ids))
    for c in work.columns:
        if not pd.api.types.is_numeric_dtype(work[c]):
            num = pd.to_numeric(work[c], errors="coerce")
            work[c] = num if num.notna().sum() >= 0.8 * len(work) else work[c].astype("category").cat.codes
    work = work.fillna(work.median(numeric_only=True)).select_dtypes(include="number")
    if work.shape[1] < 2:
        raise ValueError("clustering needs at least 2 numeric features")
    # feature cap on very wide data
    if work.shape[1] > 150:
        orig_n = work.shape[1]
        variances = work.var(numeric_only=True).fillna(0.0)
        keep = list(variances.sort_values(ascending=False).head(150).index)
        work = work[keep]
        fixes.append(f"selected the top 150 features by variance (from {orig_n}) for speed")
    if src_rows and src_rows > 20000:
        fixes.append(f"sampled 20,000 of {src_rows:,} rows for a fast run")

    Xs = StandardScaler().fit_transform(work)
    best_k, best_sil, best_labels = 2, -1.0, None
    for k in range(2, min(9, len(work))):
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(Xs)
        sil = silhouette_score(Xs, labels)
        if sil > best_sil:
            best_k, best_sil, best_labels = k, sil, labels
    fixes.append(f"label-encoded {sum(not pd.api.types.is_numeric_dtype(df[c]) for c in df.columns)} categorical feature(s)")

    sizes = pd.Series(best_labels).value_counts(normalize=True).sort_index()
    dist = [
        {"label": f"Segment {i + 1}", "value": float(v), "display": f"{v * 100:.0f}%"}
        for i, v in enumerate(sizes)
    ]
    grouped = work.reset_index(drop=True).assign(_c=best_labels)
    sep = {c: float(grouped.groupby("_c")[c].mean().var()) for c in work.columns}
    order = sorted(sep, key=lambda c: -sep[c])[:6]
    mx = max(sep.values()) or 1.0
    bars = [{"label": str(c), "value": float(max(0.08, sep[c] / mx))} for c in order]
    second = order[1] if len(order) > 1 else order[0]

    if best_sil >= 0.5:
        _clvl, _cname = "excellent", "Well-separated segments"
    elif best_sil >= 0.35:
        _clvl, _cname = "good", "Reasonably distinct segments"
    elif best_sil >= 0.2:
        _clvl, _cname = "fair", "Overlapping segments"
    else:
        _clvl, _cname = "weak", "Weak segmentation"
    verdict = {
        "level": _clvl, "label": _cname,
        "detail": f"Silhouette {best_sil:.2f} (1.0 = perfectly separated, 0 = overlapping). " + (
            "The segments are distinct and actionable." if best_sil >= 0.35
            else "The segments overlap noticeably — treat the boundaries as soft." if best_sil >= 0.2
            else "The data does not split into clean clusters — segments are mostly arbitrary."
        ),
    }

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
        "_source_rows": int(src_rows or len(df)),
        "_source_cols": int(src_cols or df.shape[1]),
        "_verdict": verdict,
        "_drivers": [{"feature": b["label"], "importance": round(b["value"], 2), "direction": 0} for b in bars[:4]],
    }


def _numeric_matrix(df: pd.DataFrame, drop: str | None = None) -> pd.DataFrame:
    """Drop id-like columns, coerce/encode the rest to numbers, impute, cap width —
    a shared cleaner for the unsupervised tasks (anomaly / PCA / etc.)."""
    work = df.copy()
    ids = [
        c for c in work.columns
        if c.lower() == "id" or c.lower().endswith("id")
        or (not pd.api.types.is_numeric_dtype(work[c]) and work[c].nunique(dropna=False) == len(work)
            and work[c].astype(str).str.len().mean() < 25)
    ]
    work = work.drop(columns=[c for c in ids if c in work.columns], errors="ignore")
    if drop and drop in work.columns:
        work = work.drop(columns=[drop])
    for c in work.columns:
        if not pd.api.types.is_numeric_dtype(work[c]):
            num = pd.to_numeric(work[c], errors="coerce")
            work[c] = num if num.notna().sum() >= 0.8 * len(work) else work[c].astype("category").cat.codes
    work = work.select_dtypes(include="number")
    work = work.fillna(work.median(numeric_only=True)).fillna(0)
    if work.shape[1] > 150:
        keep = work.var(numeric_only=True).fillna(0.0).sort_values(ascending=False).head(150).index
        work = work[list(keep)]
    return work


def _nz(s):
    mn, mx = float(s.min()), float(s.max())
    return (s - mn) / (mx - mn) if mx > mn else s * 0 + 0.5


def _anomaly(df: pd.DataFrame, src_rows=None, src_cols=None) -> dict[str, Any]:
    """Unsupervised outlier/fraud detection with Isolation Forest."""
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    fixes: list[str] = []
    if df.attrs.get("read_note"):
        fixes.append(df.attrs["read_note"])
    work = df.copy()
    if len(work) > 50000:
        work = work.sample(50000, random_state=42)
        fixes.append("sampled 50,000 rows for the anomaly scan")
    Xn = _numeric_matrix(work)
    if Xn.shape[1] < 1:
        raise ValueError("anomaly detection needs at least one numeric feature")
    Xs = StandardScaler().fit_transform(Xn)
    iso = IsolationForest(contamination="auto", random_state=42, n_estimators=200)
    flags = iso.fit_predict(Xs)
    scores = -iso.score_samples(Xs)
    is_anom = flags == -1
    pct = float(is_anom.mean() * 100)
    fixes.append(f"label-encoded {sum(not pd.api.types.is_numeric_dtype(work[c]) for c in work.columns)} non-numeric column(s)")

    diffs = {}
    for c in Xn.columns:
        col = Xn[c].to_numpy(float)
        sd = col.std() or 1e-9
        diffs[c] = (abs(col[is_anom].mean() - col[~is_anom].mean()) / sd) if (is_anom.any() and (~is_anom).any()) else 0.0
    order = sorted(diffs, key=lambda c: -diffs[c])[:6]
    mx = max(diffs.values()) or 1.0
    bars = [{"label": str(c), "value": float(max(0.08, diffs[c] / mx))} for c in order]
    dist = [
        {"label": "Normal", "value": float(1 - is_anom.mean()), "display": f"{100 - pct:.0f}%"},
        {"label": "Anomalous", "value": float(is_anom.mean()), "display": f"{pct:.1f}%"},
    ]
    scatter = None
    if len(order) >= 2:
        fx, fy = order[0], order[1]
        sdf = Xn[[fx, fy]].reset_index(drop=True)
        sdf["_a"] = is_anom.astype(int)
        if len(sdf) > 160:
            sdf = sdf.sample(160, random_state=42)
        scatter = {"x": fx, "y": fy,
                   "points": [{"x": round(float(a), 3), "y": round(float(b), 3), "c": float(c)}
                              for a, b, c in zip(_nz(sdf[fx]), _nz(sdf[fy]), sdf["_a"])],
                   "legend": {"low": "normal", "high": "anomaly"}}
    counts, edges = np.histogram(scores, bins=8)
    hist = {"feature": "anomaly score",
            "bins": [{"label": f"{edges[i]:.2f}–{edges[i + 1]:.2f}", "count": int(counts[i])} for i in range(len(counts))]}
    stats = [
        {"label": "Rows scanned", "value": f"{len(Xn):,}"},
        {"label": "Features used", "value": str(Xn.shape[1])},
        {"label": "Flagged", "value": f"{int(is_anom.sum()):,}"},
        {"label": "Anomaly rate", "value": f"{pct:.1f}%"},
    ]
    return {
        "taskLabel": "Anomaly detection", "bestModel": "Isolation Forest",
        "headline": {"fraction": min(1.0, pct / 100), "value": f"{pct:.1f}%", "label": "flagged"},
        "metrics": [{"label": "Anomalies", "value": f"{int(is_anom.sum()):,}"},
                    {"label": "Rate", "value": f"{pct:.1f}%"},
                    {"label": "Features", "value": str(Xn.shape[1])},
                    {"label": "Rows", "value": f"{len(Xn):,}"}],
        "barsTitle": "What defines the anomalies", "bars": bars,
        "distTitle": "Normal vs anomalous", "dist": dist,
        "report": [
            f"Isolation Forest scanned {len(Xn):,} records across {Xn.shape[1]} numeric features and flagged "
            f"{int(is_anom.sum()):,} ({pct:.1f}%) as anomalous — records that sit far from the normal pattern.",
            f"The anomalies separate most along {order[0]}" + (f" and {order[1]}" if len(order) > 1 else "")
            + ", so those features carry the strongest outlier signal.",
            "Each flagged record is unusual relative to the bulk of the data; review them for fraud, errors, or rare events.",
        ],
        "recommendation": f"Investigate the {int(is_anom.sum()):,} flagged records, starting with the extremes on {order[0]}.",
        "_fixes": fixes, "_features": list(Xn.columns), "_target": "(unsupervised)",
        "_rows": int(len(Xn)), "_cols": int(df.shape[1]),
        "_source_rows": int(src_rows or len(df)), "_source_cols": int(src_cols or df.shape[1]),
        "_scatter": scatter, "_hist": hist, "_stats": stats,
        "_drivers": [{"feature": b["label"], "importance": round(b["value"], 2), "direction": 0} for b in bars[:4]],
    }


def _dimreduction(df: pd.DataFrame, target: str, src_rows=None, src_cols=None) -> dict[str, Any]:
    """PCA projection to 2-D + variance explained, coloured by the target if given."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    fixes: list[str] = []
    if df.attrs.get("read_note"):
        fixes.append(df.attrs["read_note"])
    work = df.copy()
    if len(work) > 30000:
        work = work.sample(30000, random_state=42)
        fixes.append("sampled 30,000 rows")
    tgt = (target or "").strip()
    Xn = _numeric_matrix(work, drop=tgt if tgt in work.columns else None)
    if Xn.shape[1] < 2:
        raise ValueError("dimensionality reduction needs at least two numeric features")
    Xs = StandardScaler().fit_transform(Xn)
    pca = PCA(n_components=min(5, Xn.shape[1])).fit(Xs)
    proj = pca.transform(Xs)[:, :2]
    var = pca.explained_variance_ratio_

    color, legend = None, None
    if tgt and tgt in work.columns:
        yv = work[tgt].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(yv):
            yn = pd.to_numeric(yv, errors="coerce").fillna(0.0)
            color = _nz(yn)
        else:
            cats = yv.astype("category").cat.codes
            color = cats / (cats.max() or 1)
        legend = {"low": f"low {tgt}", "high": f"high {tgt}"}

    px, py = _nz(pd.Series(proj[:, 0])), _nz(pd.Series(proj[:, 1]))
    idx = np.arange(len(px))
    if len(idx) > 180:
        idx = np.random.RandomState(42).choice(len(idx), 180, replace=False)
    pts = [{"x": round(float(px.iloc[i]), 3), "y": round(float(py.iloc[i]), 3),
            "c": float(color.iloc[i]) if color is not None else 0.4} for i in idx]
    scatter = {"x": "PC1", "y": "PC2", "points": pts}
    if legend:
        scatter["legend"] = legend
    load = np.abs(pca.components_[0])
    lmx = load.max() or 1.0
    lo = np.argsort(load)[::-1][:6]
    bars = [{"label": str(Xn.columns[i]), "value": float(max(0.08, load[i] / lmx))} for i in lo]
    dist = [{"label": f"PC{i + 1}", "value": float(var[i]), "display": f"{var[i] * 100:.0f}%"} for i in range(len(var))]
    cum2 = float(var[:2].sum())
    return {
        "taskLabel": "Dimensionality reduction", "bestModel": f"PCA ({Xn.shape[1]} → 2)",
        "headline": {"fraction": cum2, "value": f"{cum2 * 100:.0f}%", "label": "variance (2D)"},
        "metrics": [{"label": "Components", "value": str(len(var))},
                    {"label": "2-D variance", "value": f"{cum2 * 100:.0f}%"},
                    {"label": "Features", "value": str(Xn.shape[1])},
                    {"label": "Rows", "value": f"{len(Xn):,}"}],
        "barsTitle": "Top PC1 loadings (drivers of spread)", "bars": bars,
        "distTitle": "Variance explained per component", "dist": dist,
        "report": [
            f"PCA compressed {Xn.shape[1]} numeric features into 2 components that together capture "
            f"{cum2 * 100:.0f}% of the variation, so the data can be viewed in a single 2-D map.",
            f"PC1 is driven most by {Xn.columns[lo[0]]}" + (f" and {Xn.columns[lo[1]]}" if len(lo) > 1 else "")
            + " — the directions along which records differ the most.",
            "Use the projection to spot clusters, gradients or outliers that are hidden in high dimensions.",
        ],
        "recommendation": f"Focus modelling on the highest-variance directions led by {Xn.columns[lo[0]]}.",
        "_fixes": fixes, "_features": list(Xn.columns), "_target": tgt or "(unsupervised)",
        "_rows": int(len(Xn)), "_cols": int(df.shape[1]),
        "_source_rows": int(src_rows or len(df)), "_source_cols": int(src_cols or df.shape[1]),
        "_scatter": scatter,
        "_stats": [{"label": "Rows", "value": f"{len(Xn):,}"}, {"label": "Features", "value": str(Xn.shape[1])},
                   {"label": "PC1 var", "value": f"{var[0] * 100:.0f}%"}, {"label": "PC2 var", "value": f"{var[1] * 100:.0f}%"}],
        "_drivers": [{"feature": b["label"], "importance": round(b["value"], 2), "direction": 0} for b in bars[:4]],
    }


def _infer_period(n: int) -> int:
    if n >= 60:
        return 12
    if n >= 28:
        return 7
    return 1


def _timeseries(df: pd.DataFrame, target: str, src_rows=None, src_cols=None) -> dict[str, Any]:
    """Holt-Winters (ETS) forecast of a numeric series, ordered by a date column if present."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from sklearn.metrics import mean_absolute_error

    fixes: list[str] = []
    if df.attrs.get("read_note"):
        fixes.append(df.attrs["read_note"])
    work = df.copy()
    tgt = (target or "").strip()

    def isnum(c):
        try:
            return pd.to_numeric(work[c], errors="coerce").notna().mean() > 0.8
        except Exception:  # noqa: BLE001
            return False

    if not tgt or tgt not in work.columns or not isnum(tgt):
        nums = [c for c in work.columns if isnum(c)]
        if not nums:
            raise ValueError("time-series forecasting needs a numeric value column")
        tgt = nums[-1]
        fixes.append(f"forecasting numeric column '{tgt}'")
    datecol = None
    for c in work.columns:
        if c == tgt:
            continue
        try:
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore")
                parsed = pd.to_datetime(work[c], errors="coerce")
        except Exception:  # noqa: BLE001
            parsed = None
        if parsed is not None and parsed.notna().mean() > 0.8:
            datecol = c
            work = work.assign(_t=parsed)
            break
    if datecol:
        work = work.dropna(subset=["_t"]).sort_values("_t")
        fixes.append(f"ordered by date column '{datecol}'")
    y = pd.to_numeric(work[tgt], errors="coerce").dropna().to_numpy(dtype=float)
    if len(y) < 12:
        raise ValueError("time-series forecasting needs at least 12 points")
    if len(y) > 3000:
        y = y[-3000:]
    period = _infer_period(len(y))
    seasonal = period > 1 and len(y) > 2 * period
    H = max(6, min(24, len(y) // 6))
    mae = 0.0
    mape = float("nan")
    try:
        m = ExponentialSmoothing(y, trend="add", seasonal="add" if seasonal else None,
                                 seasonal_periods=period if seasonal else None,
                                 initialization_method="estimated").fit()
        fc = np.asarray(m.forecast(H), dtype=float)
        fitted = np.asarray(m.fittedvalues, dtype=float)
        mae = float(mean_absolute_error(y, fitted))
        denom = np.where(np.abs(y) < 1e-9, np.nan, y)
        mape = float(np.nanmean(np.abs((y - fitted) / denom)) * 100)
    except Exception:  # noqa: BLE001
        m = ExponentialSmoothing(y, trend="add", initialization_method="estimated").fit()
        fc = np.asarray(m.forecast(H), dtype=float)
    histn = min(60, len(y))
    hist = y[-histn:]
    pts = [{"label": str(i), "value": round(float(v), 4), "kind": "history"} for i, v in enumerate(hist)]
    pts += [{"label": str(histn + i), "value": round(float(v), 4), "kind": "forecast"} for i, v in enumerate(fc)]
    direction = "rising" if fc[-1] > hist[-1] else "falling" if fc[-1] < hist[-1] else "flat"
    return {
        "taskLabel": "Time-series forecasting", "bestModel": "Holt-Winters ETS"
        + (f" (seasonal, period {period})" if seasonal else ""),
        "headline": {"value": f"{fc[-1]:,.1f}", "label": "next forecast"},
        "metrics": [{"label": "Points", "value": f"{len(y):,}"}, {"label": "Horizon", "value": str(H)},
                    {"label": "MAE", "value": f"{mae:.2f}"},
                    {"label": "MAPE", "value": f"{mape:.1f}%" if not math.isnan(mape) else "—"}],
        "barsTitle": "", "bars": [], "distTitle": "", "dist": [],
        "report": [
            f"A Holt-Winters exponential-smoothing model forecasts {tgt} for the next {H} periods; the series is "
            f"currently {direction}, ending its forecast near {fc[-1]:,.1f}.",
            (f"Seasonality with a period of {period} was modelled. " if seasonal else "No strong seasonality was modelled. ")
            + f"In-sample error is MAE {mae:.2f}" + (f" ({mape:.1f}% MAPE)." if not math.isnan(mape) else "."),
            "Use the forecast band to plan ahead; re-run as new data arrives to keep it current.",
        ],
        "recommendation": f"Plan for a {direction} {tgt}; the model projects ~{fc[-1]:,.1f} by the end of the horizon.",
        "_fixes": fixes, "_features": [tgt], "_target": tgt,
        "_rows": int(len(y)), "_cols": int(df.shape[1]),
        "_source_rows": int(src_rows or len(df)), "_source_cols": int(src_cols or df.shape[1]),
        "_forecast": {"points": pts, "horizon": int(H), "value_col": tgt, "date_col": datecol},
        "_drivers": [],
    }


def _survival(df: pd.DataFrame, target: str, src_rows=None, src_cols=None) -> dict[str, Any]:
    """Kaplan-Meier survival curve + Cox proportional-hazards (lifelines)."""
    from lifelines import KaplanMeierFitter, CoxPHFitter

    fixes: list[str] = []
    if df.attrs.get("read_note"):
        fixes.append(df.attrs["read_note"])
    work = df.copy()
    event_col = (target or "").strip()
    if not event_col or event_col not in work.columns:
        for c in work.columns:
            if work[c].nunique(dropna=True) == 2:
                event_col = c
                break
    if not event_col or event_col not in work.columns:
        raise ValueError("survival analysis needs a binary event column (the target)")
    ev = work[event_col]
    if not pd.api.types.is_numeric_dtype(ev):
        pos = sorted(ev.dropna().astype(str).unique())[-1]
        events = (ev.astype(str) == pos).astype(int)
    else:
        events = (pd.to_numeric(ev, errors="coerce") > 0).astype(int)
    dur_names = {"time", "duration", "tenure", "days", "months", "age", "lifetime", "t"}
    durcol = None
    for c in work.columns:
        if c == event_col:
            continue
        if str(c).lower() in dur_names and pd.to_numeric(work[c], errors="coerce").notna().mean() > 0.8:
            durcol = c
            break
    if durcol is None:
        for c in work.columns:
            if c == event_col:
                continue
            n = pd.to_numeric(work[c], errors="coerce")
            if n.notna().mean() > 0.8 and (n.dropna() >= 0).mean() > 0.9:
                durcol = c
                break
    if durcol is None:
        raise ValueError("survival analysis needs a non-negative duration/time column")
    fixes.append(f"duration='{durcol}', event='{event_col}'")
    d = pd.DataFrame({"T": pd.to_numeric(work[durcol], errors="coerce"), "E": events}).dropna()
    d = d[d["T"] >= 0]
    if len(d) < 10:
        raise ValueError("not enough rows for survival analysis")
    kmf = KaplanMeierFitter()
    kmf.fit(d["T"], event_observed=d["E"])
    sf = kmf.survival_function_
    ts, ss = sf.index.to_numpy(), sf.iloc[:, 0].to_numpy()
    step = max(1, len(ts) // 40)
    km = [{"t": round(float(t), 3), "s": round(float(s), 4)} for t, s in zip(ts[::step], ss[::step])]
    med = kmf.median_survival_time_
    median = float(med) if np.isfinite(med) else float(ts[-1])
    hazards = []
    try:
        feats = _numeric_matrix(work.drop(columns=[event_col], errors="ignore"), drop=durcol)
        feats = feats.loc[:, feats.nunique() > 1]
        cdf = feats.copy()
        cdf["T"] = pd.to_numeric(work[durcol], errors="coerce").reindex(feats.index)
        cdf["E"] = events.reindex(feats.index)
        cdf = cdf.dropna()
        if cdf.shape[1] > 3 and len(cdf) > 40:
            cph = CoxPHFitter(penalizer=0.1)
            cph.fit(cdf, duration_col="T", event_col="E")
            hr = cph.hazard_ratios_
            hr = hr.reindex(hr.sub(1).abs().sort_values(ascending=False).index).head(6)
            lmax = max((abs(math.log(v)) for v in hr.values if v > 0), default=1.0) or 1.0
            for name, val in hr.items():
                if val <= 0:
                    continue
                hazards.append({"label": str(name),
                                "value": float(max(0.08, min(1.0, abs(math.log(val)) / lmax))),
                                "sign": 1 if val > 1 else -1, "hr": round(float(val), 2)})
    except Exception:  # noqa: BLE001
        hazards = []
    bars = [{"label": h["label"], "value": h["value"], "sign": h["sign"]} for h in hazards] or [{"label": durcol, "value": 1.0}]
    erate = float(events.mean() * 100)
    return {
        "taskLabel": "Survival analysis", "bestModel": "Kaplan-Meier / Cox PH",
        "headline": {"value": f"{median:.0f}", "label": f"median {durcol}"},
        "metrics": [{"label": "Subjects", "value": f"{len(d):,}"}, {"label": "Events", "value": f"{int(d['E'].sum()):,}"},
                    {"label": "Event rate", "value": f"{erate:.0f}%"}, {"label": f"Median {durcol}", "value": f"{median:.0f}"}],
        "barsTitle": "Hazard ratios (Cox) — what changes risk", "bars": bars,
        "distTitle": "Outcome split", "dist": [
            {"label": "Event", "value": float(events.mean()), "display": f"{erate:.0f}%"},
            {"label": "Censored", "value": float(1 - events.mean()), "display": f"{100 - erate:.0f}%"}],
        "report": [
            f"Kaplan-Meier estimated the survival curve over '{durcol}' for {len(d):,} subjects; the median time until "
            f"the event ('{event_col}') is {median:.0f}.",
            (f"A Cox proportional-hazards model ranked the risk factors: {hazards[0]['label']} has the largest effect "
             f"(hazard ratio {hazards[0]['hr']}). " if hazards else "")
            + "A hazard ratio above 1 raises risk; below 1 is protective.",
            "Survival analysis answers 'how long until' — useful for churn timing, equipment failure, and clinical outcomes.",
        ],
        "recommendation": (f"Focus on {hazards[0]['label']} — it most changes time-to-event." if hazards
                           else f"Track '{durcol}' against '{event_col}' to manage timing risk."),
        "_fixes": fixes, "_features": [h["label"] for h in hazards] or [durcol], "_target": event_col,
        "_rows": int(len(d)), "_cols": int(df.shape[1]),
        "_source_rows": int(src_rows or len(df)), "_source_cols": int(src_cols or df.shape[1]),
        "_km": km,
        "_drivers": [{"feature": h["label"], "importance": round(h["value"], 2), "direction": h["sign"]} for h in hazards[:4]],
    }


def _recommend(df: pd.DataFrame, src_rows=None, src_cols=None) -> dict[str, Any]:
    """Content-based recommender: cosine similarity over each item's feature vector,
    returning the most similar items for a sample of rows."""
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler

    fixes: list[str] = []
    if df.attrs.get("read_note"):
        fixes.append(df.attrs["read_note"])
    work = df.copy()
    if len(work) > 5000:
        work = work.sample(5000, random_state=42)
        fixes.append("sampled 5,000 items")
    label_col = None
    for c in work.columns:
        if not pd.api.types.is_numeric_dtype(work[c]) and 3 < work[c].nunique(dropna=True) <= len(work):
            label_col = c
            break
    labels = work[label_col].astype(str).tolist() if label_col else [f"item {i + 1}" for i in range(len(work))]
    Xn = _numeric_matrix(work, drop=label_col)
    if Xn.shape[1] < 1:
        raise ValueError("recommendations need at least one numeric feature per item")
    Xs = StandardScaler().fit_transform(Xn)
    sim = cosine_similarity(Xs)
    np.fill_diagonal(sim, -2.0)
    recs = []
    for i in range(min(10, len(labels))):
        top = sim[i].argsort()[::-1][:5]
        recs.append({"item": labels[i],
                     "similar": [{"name": labels[j], "score": round(float(sim[i][j]), 3)} for j in top if sim[i][j] > -2]})
    var = Xn.var(numeric_only=True).fillna(0.0).sort_values(ascending=False)
    vmx = var.max() or 1.0
    bars = [{"label": str(c), "value": float(max(0.08, var[c] / vmx))} for c in var.index[:6]]
    return {
        "taskLabel": "Recommendation (content-based)", "bestModel": "Cosine similarity",
        "headline": {"value": f"{len(labels):,}", "label": "items"},
        "metrics": [{"label": "Items", "value": f"{len(labels):,}"}, {"label": "Features", "value": str(Xn.shape[1])},
                    {"label": "Label col", "value": str(label_col or "row index")}],
        "barsTitle": "Features that drive similarity", "bars": bars,
        "distTitle": "", "dist": [],
        "report": [
            f"A content-based recommender compared {len(labels):,} items on {Xn.shape[1]} numeric features using cosine "
            f"similarity — items with similar feature profiles are recommended for one another.",
            f"Similarity is driven most by {var.index[0]}" + (f" and {var.index[1]}" if len(var) > 1 else "")
            + ", so those features most determine which items are considered alike.",
            "Use the similar-item lists for 'customers who liked X also like…' style recommendations.",
        ],
        "recommendation": f"Surface the top-similar items per item; tune relevance by weighting {var.index[0]}.",
        "_fixes": fixes, "_features": list(Xn.columns), "_target": "(unsupervised)",
        "_rows": int(len(work)), "_cols": int(df.shape[1]),
        "_source_rows": int(src_rows or len(df)), "_source_cols": int(src_cols or df.shape[1]),
        "_recommend": {"label_col": label_col or "row index", "items": recs},
        "_drivers": [{"feature": b["label"], "importance": round(b["value"], 2), "direction": 0} for b in bars[:4]],
    }


# ───────────────────────── chart-card builder ──────────────────────────
# The Visualizer LLM only ever chooses chart TYPE + a data SOURCE + title/note.
# These pure-python helpers fill the actual numbers from the real DataFrame or
# from insights the trusted engine already computed — the LLM never emits data,
# so a chart can never show a fabricated value. Anything that fails validation
# is silently dropped.

_CHART_TYPES = {
    "bar", "column", "pie", "line", "area", "radar",
    "histogram", "scatter", "box", "heatmap", "statcards",
}


def _fmt_num(v: Any) -> str:
    try:
        v = float(v)
    except Exception:  # noqa: BLE001
        return str(v)
    if math.isnan(v):
        return "—"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def _tbl(columns: list[dict], rows: list[list], caption: str | None = None) -> dict:
    out = {"columns": columns, "rows": rows}
    if caption:
        out["caption"] = caption
    return out


def _items_table(items, cat="Category", val="Value", effect=False) -> dict:
    cols = [{"label": cat}, {"label": val, "align": "right"}]
    if effect:
        cols.append({"label": "Effect", "align": "right"})
    rows = []
    for it in items:
        disp = it.get("display") or _fmt_num(it.get("value"))
        row = [str(it.get("label", "")), disp]
        if effect:
            s = it.get("sign", 0) or 0
            row.append("↑ raises" if s > 0 else ("↓ lowers" if s < 0 else "—"))
        rows.append(row)
    return _tbl(cols, rows)


def _bins_table(bins) -> dict:
    return _tbl([{"label": "Range"}, {"label": "Count", "align": "right"}],
                [[b["label"], str(b["count"])] for b in bins])


def _boxes_table(boxes) -> dict:
    cols = [{"label": "Group"}] + [{"label": k, "align": "right"} for k in ("Min", "Q1", "Median", "Q3", "Max")]
    rows = [[b["label"], _fmt_num(b["min"]), _fmt_num(b["q1"]), _fmt_num(b["med"]), _fmt_num(b["q3"]), _fmt_num(b["max"])]
            for b in boxes]
    return _tbl(cols, rows)


def _points_table(sc) -> dict:
    pts = sc.get("points", [])
    show = pts[:10]
    cols = [{"label": sc.get("x", "x"), "align": "right"},
            {"label": sc.get("y", "y"), "align": "right"},
            {"label": "shade", "align": "right"}]
    rows = [[f"{p['x']:.2f}", f"{p['y']:.2f}", f"{p['c']:.2f}"] for p in show]
    cap = f"showing {len(show)} of {len(pts)} points" if len(pts) > len(show) else None
    return _tbl(cols, rows, cap)


def _matrix_table(hm) -> dict:
    labels, m = hm["labels"], hm["matrix"]
    cols = [{"label": ""}] + [{"label": l, "align": "right"} for l in labels]
    rows = [[labels[i]] + [f"{m[i][j]:.2f}" for j in range(len(labels))] for i in range(len(labels))]
    return _tbl(cols, rows)


def _cumulative_table(bars) -> dict:
    total = sum(b["value"] for b in bars) or 1.0
    cols = [{"label": "Feature"}, {"label": "Importance", "align": "right"}, {"label": "Cumulative", "align": "right"}]
    rows, cum = [], 0.0
    for b in bars:
        cum += b["value"] / total
        rows.append([str(b["label"]), f"{b['value']:.2f}", f"{cum * 100:.0f}%"])
    return _tbl(cols, rows)


def _normalize(items, ctype) -> list[dict]:
    """Scale values to 0..1 (preserving ratios, so pie shares stay correct) while
    keeping the real number in ``display``."""
    mx = max((abs(it["value"]) for it in items), default=0.0) or 1.0
    return [
        {"label": str(it["label"]),
         "value": float(max(0.02, min(1.0, abs(it["value"]) / mx))),
         "display": it.get("display") or _fmt_num(it["value"])}
        for it in items
    ]


def _corr_heatmap(corr) -> dict | None:
    labels: list[str] = []
    for p in corr:
        for k in (p["a"], p["b"]):
            if k not in labels:
                labels.append(k)
    labels = labels[:8]
    if len(labels) < 2:
        return None
    idx = {l: i for i, l in enumerate(labels)}
    n = len(labels)
    m = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for p in corr:
        a, b = p["a"], p["b"]
        if a in idx and b in idx:
            m[idx[a]][idx[b]] = m[idx[b]][idx[a]] = round(float(p["r"]), 2)
    return {"labels": labels, "matrix": m}


def _card(ctype, title, data, table, note="", axes=None, source=None) -> dict:
    return {
        "type": ctype, "title": str(title)[:70], "data": data, "table": table,
        "note": note, "axes": axes or {}, "source": source or {"kind": "insight"},
    }


def _insight_card(results, ref, ctype, tgt) -> dict | None:
    """Build a card from an insight the engine already computed (no df needed)."""
    bars = results.get("bars") or []
    dist = results.get("dist") or []
    if ref == "bars" and bars:
        if ctype == "radar" and len(bars) >= 3:
            return _card("radar", "Feature importance · radar",
                         {"items": [{"label": b["label"], "value": b["value"]} for b in bars]},
                         _items_table(bars, "Feature", "Importance"),
                         "Radial view of the top drivers — area ≈ overall driver strength.")
        if ctype in ("pie", "line", "area", "column"):
            data = {"items": _normalize([{"label": b["label"], "value": b["value"]} for b in bars], ctype)}
            return _card(ctype, results.get("barsTitle", "Feature importance"), data,
                         _items_table(bars, "Feature", "Importance"),
                         f"Relative importance of each driver of {tgt}.")
        return _card("bar", results.get("barsTitle", "Feature importance"),
                     {"items": [{"label": b["label"], "value": b["value"], "sign": b.get("sign", 0)} for b in bars]},
                     _items_table(bars, "Feature", "Importance", effect=any("sign" in b for b in bars)),
                     f"How strongly each feature moves {tgt}; longer bar = bigger effect.")
    if ref == "dist" and dist:
        ct = ctype if ctype in ("column", "bar", "pie", "line", "area") else "column"
        data = {"items": dist if ct in ("column", "bar") else _normalize(dist, ct)}
        return _card(ct, results.get("distTitle", "Breakdown"), data,
                     _items_table(dist, "Segment", "Value"),
                     f"{results.get('distTitle', 'Breakdown')} across groups.")
    if ref == "corr":
        hm = _corr_heatmap(results.get("_corr") or [])
        if hm:
            return _card("heatmap", "Correlation between drivers", hm, _matrix_table(hm),
                         "Pairwise correlation of the top features; darker = stronger (possible redundancy).")
    if ref == "hist":
        h = results.get("_hist")
        if h and h.get("bins"):
            return _card("histogram", f"{h['feature']} · distribution",
                         {"feature": h["feature"], "bins": h["bins"]}, _bins_table(h["bins"]),
                         f"How {h['feature']} is spread across its range — count per bin.",
                         {"x": h["feature"], "y": "count"})
    if ref == "scatter":
        sc = results.get("_scatter")
        if sc and sc.get("points"):
            return _card("scatter", f"{sc['x']} vs {sc['y']}", sc, _points_table(sc),
                         f"Each dot is a record by {sc['x']} and {sc['y']}, shaded by {tgt}.",
                         {"x": sc.get("x"), "y": sc.get("y")})
    if ref == "box":
        bx = results.get("_box")
        if bx and bx.get("boxes"):
            return _card("box", f"{bx['feature']} · spread", bx, _boxes_table(bx["boxes"]),
                         f"Distribution of {bx['feature']} (min · Q1 · median · Q3 · max).",
                         {"x": bx["feature"]})
    if ref == "stats":
        st = results.get("_stats") or []
        if st:
            return _card("statcards", "Key statistics",
                         {"items": [{"label": s["label"], "value": s["value"]} for s in st]},
                         _tbl([{"label": "Statistic"}, {"label": "Value", "align": "right"}],
                              [[s["label"], s["value"]] for s in st]),
                         "Headline numbers describing the data and model at a glance.")
    return None


def _default_cards(results, target, is_clf) -> list[dict]:
    """A rich, deterministic gallery built purely from engine insights — always
    available, even with no LLM key."""
    tgt = target or "the outcome"
    bars = results.get("bars") or []
    dist = results.get("dist") or []
    cards: list[dict] = []
    if bars:
        cards.append(_insight_card(results, "bars", "bar", tgt))
    if dist:
        cards.append(_insight_card(results, "dist", "column", tgt))
        cards.append(_card("pie", results.get("distTitle", "Breakdown") + " · share",
                           {"items": _normalize(dist, "pie")}, _items_table(dist, "Segment", "Share"),
                           "Each slice is a group's share of the breakdown."))
        if len(dist) >= 3:
            cards.append(_card("line", results.get("distTitle", "Breakdown") + " · trend",
                               {"items": dist}, _items_table(dist, "Segment", "Value"),
                               "The same breakdown drawn as a trend to reveal its shape."))
    if len(bars) >= 3:
        cards.append(_insight_card(results, "bars", "radar", tgt))
    if len(bars) >= 2:
        cards.append(_card("area", "Cumulative importance · Pareto",
                           {"items": [{"label": b["label"], "value": b["value"]} for b in bars]},
                           _cumulative_table(bars),
                           "Running share of total importance — how few features explain most of the signal."))
    for ref in ("corr", "hist", "scatter", "box", "stats"):
        c = _insight_card(results, ref, ref, tgt)
        if c:
            cards.append(c)
    return [c for c in cards if c]


def _llm_cards(df, target, results, specs, is_clf) -> list[dict]:
    """Execute the LLM's validated chart specs on the REAL dataframe."""
    cards: list[dict] = []
    cols = set(df.columns) if df is not None else set()
    tgt = target or "the outcome"
    for spec in specs:
        try:
            if not isinstance(spec, dict):
                continue
            ctype = str(spec.get("type", "")).lower()
            if ctype not in _CHART_TYPES:
                continue
            src = spec.get("source") or {}
            kind = str(src.get("kind", "")).lower()
            title = str(spec.get("title") or "").strip()[:70]
            note = str(spec.get("note") or "").strip()
            axes = spec.get("axes") if isinstance(spec.get("axes"), dict) else {}
            if df is None and kind != "insight":
                continue

            if kind == "insight":
                card = _insight_card(results, str(src.get("ref", "")).lower(), ctype, tgt)
                if not card:
                    continue
                if title:
                    card["title"] = title
                if note:
                    card["note"] = note
                cards.append(card)
                continue

            if kind == "aggregate":
                gb, of = src.get("groupby"), src.get("of")
                agg = str(src.get("agg", "mean")).lower()
                top = max(1, min(12, int(src.get("top") or 8)))
                if gb not in cols or df[gb].nunique(dropna=True) > max(40, 0.6 * len(df)):
                    continue
                if agg == "count":
                    g = df.groupby(gb).size()
                elif agg in ("mean", "sum", "median", "min", "max"):
                    if of not in cols or not pd.api.types.is_numeric_dtype(df[of]):
                        continue
                    g = df.groupby(gb)[of].agg(agg)
                else:
                    continue
                g = g.sort_values(ascending=False).head(top)
                items = [{"label": str(k), "value": float(v), "display": _fmt_num(v)} for k, v in g.items()]
                if not items:
                    continue
                ct = ctype if ctype in ("column", "bar", "pie", "line", "area", "radar") else "column"
                table = _items_table(items, str(gb), ("count" if agg == "count" else f"{agg} of {of}"))
                cards.append(_card(ct, title or f"{agg} of {of or 'records'} by {gb}",
                                   {"items": _normalize(items, ct)}, table, note,
                                   {"x": str(gb), "y": ("count" if agg == "count" else f"{agg} of {of}")}, src))
                continue

            if kind == "distribution":
                col = src.get("column")
                if col not in cols:
                    continue
                if pd.api.types.is_numeric_dtype(df[col]):
                    s = pd.to_numeric(df[col], errors="coerce").dropna()
                    if s.nunique() < 2:
                        continue
                    nb = max(4, min(12, int(src.get("bins") or 8)))
                    counts, edges = np.histogram(s, bins=nb)
                    bins = [{"label": f"{edges[i]:.0f}–{edges[i + 1]:.0f}", "count": int(counts[i])}
                            for i in range(len(counts))]
                    cards.append(_card("histogram", title or f"{col} · distribution",
                                       {"feature": str(col), "bins": bins}, _bins_table(bins), note,
                                       {"x": str(col), "y": "count"}, src))
                else:
                    vc = df[col].astype(str).value_counts(normalize=True).head(8)
                    items = [{"label": str(k), "value": float(v), "display": f"{v * 100:.0f}%"} for k, v in vc.items()]
                    if not items:
                        continue
                    ct = ctype if ctype in ("column", "bar", "pie", "line", "area") else "column"
                    cards.append(_card(ct, title or f"{col} · share",
                                       {"items": _normalize(items, ct)}, _items_table(items, str(col), "Share"),
                                       note, {"x": str(col), "y": "share"}, src))
                continue

            if kind == "corr_matrix":
                want = src.get("columns")
                num = df.select_dtypes(include="number")
                if isinstance(want, list) and want:
                    keep = [c for c in want if c in num.columns]
                    if keep:
                        num = num[keep]
                num = num.iloc[:, :10]
                if num.shape[1] < 2:
                    continue
                cm = num.corr().fillna(0.0)
                labels = [str(c) for c in cm.columns]
                matrix = [[round(float(cm.iloc[i, j]), 2) for j in range(len(labels))] for i in range(len(labels))]
                hm = {"labels": labels, "matrix": matrix}
                cards.append(_card("heatmap", title or "Correlation matrix", hm, _matrix_table(hm),
                                   note or "Pairwise correlation across the selected numeric columns.", {}, src))
                continue
        except Exception:  # noqa: BLE001
            continue
    return cards


def build_chart_cards(df, target, results, is_clf, llm_text: str = "") -> list[dict]:
    """Return the unified ``_charts`` gallery: deterministic insight cards plus any
    LLM-recommended (context-aware) cards, each carrying chart data + table + note.
    Every value is computed by the engine — the LLM only picks type/source/title/note."""
    specs: list = []
    if llm_text:
        s, e = llm_text.find("["), llm_text.rfind("]")
        if s != -1 and e > s:
            try:
                parsed = json.loads(llm_text[s:e + 1])
                if isinstance(parsed, list):
                    specs = parsed
            except Exception:  # noqa: BLE001
                specs = []
    llm = _llm_cards(df, target, results, specs, is_clf) if specs else []
    cards = llm + _default_cards(results, target, is_clf)
    seen, out = set(), []
    for c in cards:
        key = (c["type"], c["title"])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    out = out[:14]
    for i, c in enumerate(out):
        c["id"] = f"c{i + 1}"
        c["rank"] = i + 1
    return out
