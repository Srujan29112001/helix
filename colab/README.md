# Helix — Colab notebooks

Two ready-to-run notebooks. Upload either to **[colab.research.google.com](https://colab.research.google.com)**
(File → Upload notebook), then **Runtime → Run all**.

| Notebook | What it does |
|----------|--------------|
| `Helix_Colab.ipynb` | **Phase 1–2 demo** — the 7-agent LangGraph pipeline on 4 sample datasets, with self-correction. Runs offline (mock LLM). Great for explaining the architecture. |
| `Helix_RealData_Colab.ipynb` | **Real analysis** — upload your **own CSV** (e.g. Kaggle), pick the target, and get a genuine result: clean → FLAML AutoML → real metrics → SHAP → LLM report, with real self-correction. |

## Recommended test dataset
**Telco Customer Churn** — https://www.kaggle.com/datasets/blastchar/telco-customer-churn
Download the single CSV, upload it in the real-data notebook, set **target = `Churn`**.
(Its messy `TotalCharges` column triggers real auto-correction; expect ~0.84 ROC-AUC.)

Other datasets that work out of the box: Titanic (`Survived`), House Prices (`SalePrice`, regression),
Heart Disease (`target`), Mall Customers, etc. — any tabular CSV with a target column.

## Free LLM (optional, recommended)
The analysis runs for real **with or without** an LLM key. To get real agent plans + reports,
paste a **free Groq** key into the config cell:

1. Get a key (free, no card): https://console.groq.com/keys
2. In the notebook's config cell set `HELIX_LLM_API_KEY = "gsk_..."`

Alternatives (also free tier): Google **Gemini** (`gemini-2.0-flash`) or **OpenRouter** `:free` models —
see the commented lines in the config cell.

## Rebuilding the notebooks
The notebooks are generated from scripts so the code stays in sync with the backend:

```bash
python colab/build_notebook.py        # → Helix_Colab.ipynb
python colab/build_real_notebook.py   # → Helix_RealData_Colab.ipynb (embeds backend/app/analysis.py verbatim)
```
