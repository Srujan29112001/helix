"""Lightweight RAG over data-science documentation (Phase 5).

A curated corpus of pandas / scikit-learn / FLAML / SHAP recipes is embedded
with a local MiniLM model (ChromaDB's default, ONNX — no GPU) and stored in
ChromaDB. The Coder retrieves the most relevant snippets to ground its code,
cutting hallucinated APIs.

Falls back to a keyword match if ChromaDB/embeddings are unavailable, so the
pipeline never breaks.
"""

from __future__ import annotations

_DOCS: list[tuple[str, str]] = [
    ("pandas-missing", "Handle missing values: fill numeric columns with df.fillna(df.median(numeric_only=True)); fill categoricals with the mode df['c'].fillna(df['c'].mode()[0])."),
    ("pandas-encode", "Encode categorical features for tree models with label codes: df['c'] = df['c'].astype('category').cat.codes; or one-hot via pd.get_dummies(df, columns=cols)."),
    ("pandas-numeric", "Coerce a numeric column stored as text: pd.to_numeric(df['c'], errors='coerce'). Aggregate only numeric columns with df.mean(numeric_only=True) to avoid TypeErrors."),
    ("flaml-automl", "FLAML AutoML: from flaml import AutoML; m=AutoML(); m.fit(X_train, y_train, task='classification', time_budget=30, metric='roc_auc'); preds=m.predict(X_test)."),
    ("sklearn-split", "Train/test split: from sklearn.model_selection import train_test_split; X_tr,X_te,y_tr,y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)."),
    ("sklearn-metrics", "Classification metrics: accuracy_score, roc_auc_score(y, proba[:,1]), precision_score, recall_score, f1_score. Regression: r2_score, mean_squared_error, mean_absolute_error."),
    ("shap-explain", "Explain a tree model with SHAP: import shap; e=shap.TreeExplainer(model); vals=e.shap_values(X_sample); rank features by abs(vals).mean(0); sign by vals.mean(0)."),
    ("eda-basic", "Quick EDA: df.shape, df.describe(), df['target'].value_counts(normalize=True), and df.corr(numeric_only=True) to find correlations with the target."),
]

_collection = None
_failed = False


def _get_collection():
    global _collection, _failed
    if _collection is not None or _failed:
        return _collection
    try:
        import chromadb

        client = chromadb.Client()
        col = client.get_or_create_collection("ds_docs")
        if col.count() == 0:
            col.add(ids=[d[0] for d in _DOCS], documents=[d[1] for d in _DOCS])
        _collection = col
    except Exception:
        _failed = True
        _collection = None
    return _collection


def _keyword_fallback(query: str, k: int) -> list[str]:
    q = set(query.lower().split())
    scored = sorted(_DOCS, key=lambda d: -len(q & set(d[1].lower().split())))
    return [d[1] for d in scored[:k]]


def retrieve(query: str, k: int = 2) -> list[str]:
    """Return the k most relevant documentation snippets for a query."""
    col = _get_collection()
    if col is not None:
        try:
            res = col.query(query_texts=[query], n_results=min(k, len(_DOCS)))
            docs = res.get("documents") if res else None
            if docs and docs[0]:
                return docs[0]
        except Exception:
            pass
    return _keyword_fallback(query, k)
