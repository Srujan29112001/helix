"""Sample datasets + their (currently canned) result payloads.

Result keys mirror the frontend ``RunResults`` type in
``frontend/lib/studio-run.ts`` exactly, so live-streamed results render
without any client-side mapping. In later phases these dicts are produced by
the real agent pipeline instead of being hard-coded here.
"""

from __future__ import annotations

from typing import Any

DATASETS: dict[str, dict[str, Any]] = {
    "loan": {
        "id": "loan",
        "name": "Loan Default Risk",
        "file": "loan_applications.csv",
        "rows": 32581,
        "cols": 12,
        "task": "Binary classification",
        "target": "default",
        "goal": "Predict which loan applicants will default and identify the key risk factors.",
        "accent": "#25d7f0",
        "error": "ValueError: could not convert string to float: 'RENT'",
        "fix": "df = pd.get_dummies(df, columns=['home_ownership'])",
        "results": {
            "taskLabel": "Binary classification",
            "bestModel": "LightGBM",
            "headline": {"fraction": 0.86, "value": "0.86", "label": "ROC-AUC"},
            "metrics": [
                {"label": "Accuracy", "value": "0.84"},
                {"label": "ROC-AUC", "value": "0.86"},
                {"label": "Precision", "value": "0.79"},
                {"label": "Recall", "value": "0.66"},
            ],
            "barsTitle": "SHAP feature importance",
            "bars": [
                {"label": "Credit score", "value": 0.94, "sign": -1},
                {"label": "Debt-to-income", "value": 0.81, "sign": 1},
                {"label": "Loan amount", "value": 0.62, "sign": 1},
                {"label": "Annual income", "value": 0.55, "sign": -1},
                {"label": "Employment length", "value": 0.38, "sign": -1},
                {"label": "Interest rate", "value": 0.3, "sign": 1},
            ],
            "distTitle": "Default rate by credit band",
            "dist": [
                {"label": "Poor (<580)", "value": 0.34, "display": "34%"},
                {"label": "Fair (580-669)", "value": 0.17, "display": "17%"},
                {"label": "Good (670-739)", "value": 0.08, "display": "8%"},
                {"label": "Excellent (740+)", "value": 0.03, "display": "3%"},
            ],
            "report": [
                "Credit score is the single strongest predictor of default - applicants below 580 default at 34%, versus just 3% above 740. A high debt-to-income ratio sharply raises risk.",
                "Larger loan amounts and higher interest rates increase default probability, while higher income and longer employment history are protective.",
            ],
            "recommendation": "Tighten approval for low-credit, high-DTI applicants and price interest rates to the modelled risk rather than flat tiers.",
        },
    },
    "sales": {
        "id": "sales",
        "name": "Rossmann Store Sales",
        "file": "rossmann_sales.csv",
        "rows": 1017209,
        "cols": 18,
        "task": "Regression",
        "target": "Sales",
        "goal": "Forecast daily sales for each store over the next six weeks.",
        "accent": "#9ae64a",
        "error": "ValueError: could not convert string to float: 'StateHoliday'",
        "fix": "df['StateHoliday'] = df['StateHoliday'].astype('category').cat.codes",
        "results": {
            "taskLabel": "Regression",
            "bestModel": "LightGBM Regressor",
            "headline": {"fraction": 0.93, "value": "0.93", "label": "R² score"},
            "metrics": [
                {"label": "R²", "value": "0.93"},
                {"label": "RMSPE", "value": "8.4%"},
                {"label": "MAE", "value": "421"},
                {"label": "RMSE", "value": "612"},
            ],
            "barsTitle": "Feature importance",
            "bars": [
                {"label": "Promo", "value": 0.81, "sign": 1},
                {"label": "Day of week", "value": 0.55, "sign": -1},
                {"label": "Competition dist.", "value": 0.40, "sign": -1},
                {"label": "Store type", "value": 0.33, "sign": 1},
                {"label": "School holiday", "value": 0.18, "sign": 1},
            ],
            "distTitle": "Average sales by day of week",
            "dist": [
                {"label": "Monday", "value": 0.98, "display": "9.7k"},
                {"label": "Wednesday", "value": 0.71, "display": "7.0k"},
                {"label": "Friday", "value": 0.83, "display": "8.2k"},
                {"label": "Sunday", "value": 0.12, "display": "1.2k"},
            ],
            "report": [
                "Running promotions is by far the largest driver of daily sales, lifting revenue materially whenever active. Sales peak on Mondays and dip sharply on Sundays when many stores are closed.",
                "Proximity to competition has a measurable negative effect, while certain store types consistently outperform. The model forecasts six weeks ahead with an 8.4% error.",
            ],
            "recommendation": "Concentrate promotional spend on high-traffic weekdays and stores facing nearby competition, where the forecasted uplift is greatest.",
        },
    },
    "segments": {
        "id": "segments",
        "name": "Mall Customer Segmentation",
        "file": "mall_customers.csv",
        "rows": 200,
        "cols": 5,
        "task": "Clustering",
        "target": "Segment",
        "goal": "Group customers into meaningful segments by income and spending behavior.",
        "accent": "#a78bfa",
        "error": "ValueError: Input X contains NaN",
        "fix": "X = StandardScaler().fit_transform(df.dropna())",
        "results": {
            "taskLabel": "Clustering",
            "bestModel": "KMeans (k=4)",
            "headline": {"value": "4", "label": "segments"},
            "metrics": [
                {"label": "Clusters", "value": "4"},
                {"label": "Silhouette", "value": "0.55"},
                {"label": "Features", "value": "2"},
                {"label": "Samples", "value": "200"},
            ],
            "barsTitle": "Defining dimensions",
            "bars": [
                {"label": "Spending score", "value": 0.88},
                {"label": "Annual income", "value": 0.79},
                {"label": "Age", "value": 0.34},
            ],
            "distTitle": "Segment sizes",
            "dist": [
                {"label": "Premium (high $, high spend)", "value": 0.18, "display": "18%"},
                {"label": "Careful (high $, low spend)", "value": 0.22, "display": "22%"},
                {"label": "Budget (low $, low spend)", "value": 0.35, "display": "35%"},
                {"label": "Impulsive (low $, high spend)", "value": 0.25, "display": "25%"},
            ],
            "report": [
                "Four clear segments emerge along income and spending-score axes. The most valuable “Premium” group combines high income with high spending, while a sizeable “Careful” group earns well but spends little.",
                "The largest cluster is budget-conscious, and a notable “Impulsive” group spends beyond what their income would suggest.",
            ],
            "recommendation": "Target the “Careful” high-income segment with premium offers to unlock latent spend, and use loyalty perks to retain the “Premium” group.",
        },
    },
    "reviews": {
        "id": "reviews",
        "name": "Product Reviews",
        "file": "reviews.csv",
        "rows": 10000,
        "cols": 3,
        "task": "NLP + analytics",
        "target": "Sentiment",
        "goal": "Analyze sentiment and surface the top recurring themes in customer reviews.",
        "accent": "#fb7185",
        "error": "LookupError: Resource punkt not found",
        "fix": "nltk.download('punkt', quiet=True)",
        "results": {
            "taskLabel": "NLP + analytics",
            "bestModel": "TF-IDF + Logistic Regression",
            "headline": {"fraction": 0.62, "value": "62%", "label": "positive"},
            "metrics": [
                {"label": "Reviews", "value": "10k"},
                {"label": "Positive", "value": "62%"},
                {"label": "Negative", "value": "24%"},
                {"label": "Neutral", "value": "14%"},
            ],
            "barsTitle": "Top themes by frequency",
            "bars": [
                {"label": "Delivery speed", "value": 0.74},
                {"label": "Product quality", "value": 0.66},
                {"label": "Price / value", "value": 0.52},
                {"label": "Customer support", "value": 0.39},
                {"label": "Packaging", "value": 0.27},
            ],
            "distTitle": "Sentiment distribution",
            "dist": [
                {"label": "Positive", "value": 0.62, "display": "62%"},
                {"label": "Neutral", "value": 0.14, "display": "14%"},
                {"label": "Negative", "value": 0.24, "display": "24%"},
            ],
            "report": [
                "Overall sentiment is positive, with 62% of reviews favorable. Delivery speed is the most-discussed theme and the leading source of negative sentiment, followed closely by product quality.",
                "Price and value are mentioned often and generally viewed favorably, while customer support, though less frequent, skews negative when raised.",
            ],
            "recommendation": "Prioritize fixing delivery reliability — it is the top theme and the biggest driver of negative reviews — and amplify the positive price-value perception in marketing.",
        },
    },
}


def get_dataset(dataset_id: str) -> dict[str, Any]:
    return DATASETS.get(dataset_id, DATASETS["loan"])


def dataset_summaries() -> list[dict[str, Any]]:
    """Lightweight metadata for the dataset picker (no results)."""
    keys = ("id", "name", "file", "rows", "cols", "task", "target", "goal", "accent")
    return [{k: d[k] for k in keys} for d in DATASETS.values()]
