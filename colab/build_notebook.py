# Builds Helix_Colab.ipynb — a self-contained Colab notebook that runs the
# Phase 1-2 agent pipeline (LangGraph + self-correction + hybrid LLM) behind a
# Gradio UI. Run:  python colab/build_notebook.py
import json
import os

CELLS = []


def md(src):
    CELLS.append(("markdown", src))


def code(src):
    CELLS.append(("code", src))


# ───────────────────────────── Cell 1: intro ─────────────────────────────
md(
    """# 🧬 Helix — Autonomous Data Science Agent (Colab edition)

**Capstone · IIIT-H.** This is the Colab-runnable equivalent of what we've built so far
(**Phases 1–2**): the real **multi-agent pipeline** with **self-correcting code execution**,
wrapped in a simple **Gradio** UI so you can run analyses and *watch the agents work — live*.

### What this demonstrates
- A **LangGraph** state graph of 7 agents: **Planner → Coder → Executor ⇄ Critic → AutoML → Explainer → Reporter**
- The **self-correction loop**: the Executor hits an error, the Critic patches it and retries (≤ 5)
- A **hybrid LLM layer**: runs on a built-in **mock** by default (no keys needed); plug in real
  local/hosted models per agent via environment variables

### Still stubbed (next phases — identical to the web app)
- Executor doesn't run real code yet (Phase 3) · AutoML & SHAP numbers come from the dataset (Phase 4)

### ▶ How to use
1. **Runtime → Run all** (or run each cell top-to-bottom)
2. A **Gradio** app appears at the bottom with a public link
3. Pick a dataset, type a goal, click **Run analysis**, and watch the live log + results
"""
)

# ───────────────────────────── Cell 2: install ───────────────────────────
code(
    """# Install dependencies (pandas/numpy/requests already ship with Colab)
!pip install -q langgraph langchain-core gradio
print("✅ dependencies installed")"""
)

# ───────────────────────── Cell 3: optional LLM keys ──────────────────────
code(
    """import os

# ── Optional: use REAL models instead of the built-in mock ──────────────────
# Leave as-is to run fully offline with the deterministic MockLLM.
# To go HYBRID, uncomment and fill in (per-role overrides also work, e.g. HELIX_CODER_*):
#
# os.environ["HELIX_LLM_BASE_URL"] = "https://openrouter.ai/api/v1"   # any OpenAI-compatible endpoint
# os.environ["HELIX_LLM_API_KEY"]  = "sk-..."
# os.environ["HELIX_LLM_MODEL"]    = "deepseek/deepseek-coder"
#
# Example hybrid (local Coder via Ollama + hosted Reporter):
# os.environ["HELIX_CODER_BASE_URL"]    = "http://localhost:11434/v1"
# os.environ["HELIX_CODER_MODEL"]       = "deepseek-coder"
# os.environ["HELIX_REPORTER_BASE_URL"] = "https://api.groq.com/openai/v1"
# os.environ["HELIX_REPORTER_API_KEY"]  = "gsk_..."
# os.environ["HELIX_REPORTER_MODEL"]    = "mistral-saba-24b"

_live = bool(os.getenv("HELIX_LLM_API_KEY") or os.getenv("HELIX_LLM_BASE_URL"))
print("LLM mode:", "REAL / hybrid" if _live else "MOCK (offline, deterministic)")"""
)

# ───────────────────────────── Cell 4: datasets ──────────────────────────
code(
    '''# The 4 sample datasets + their result payloads (same content as the web app).
DATASETS = {
    "churn": {
        "id": "churn", "name": "Telco Customer Churn", "file": "WA_Telco_Churn.csv",
        "rows": 7043, "cols": 21, "task": "Binary classification", "target": "Churn",
        "goal": "Predict which customers will churn and identify the key drivers behind it.",
        "accent": "#25d7f0", "error": "KeyError: 'Churn'",
        "fix": "df.columns = df.columns.str.strip()",
        "results": {
            "taskLabel": "Binary classification", "bestModel": "LightGBM",
            "headline": {"fraction": 0.84, "value": "0.84", "label": "ROC-AUC"},
            "metrics": [{"label": "Accuracy", "value": "0.81"}, {"label": "ROC-AUC", "value": "0.84"},
                        {"label": "Precision", "value": "0.68"}, {"label": "Recall", "value": "0.71"}],
            "barsTitle": "SHAP feature importance",
            "bars": [{"label": "Contract type", "value": 0.92, "sign": 1}, {"label": "Tenure", "value": 0.78, "sign": -1},
                     {"label": "Monthly charges", "value": 0.64, "sign": 1}, {"label": "Tech support", "value": 0.41, "sign": -1},
                     {"label": "Online security", "value": 0.38, "sign": -1}, {"label": "Payment method", "value": 0.24, "sign": 1}],
            "distTitle": "Churn rate by contract type",
            "dist": [{"label": "Month-to-month", "value": 0.43, "display": "43%"},
                     {"label": "One year", "value": 0.11, "display": "11%"}, {"label": "Two year", "value": 0.03, "display": "3%"}],
            "report": ["The model identifies contract type as the single strongest predictor of churn. Customers on month-to-month plans churn at 43%, versus just 3% for two-year contracts.",
                       "Tenure is a strong protective factor. High monthly charges and the absence of tech support or online security further increase churn risk."],
            "recommendation": "Incentivize month-to-month customers onto annual contracts, and proactively offer tech-support bundles to high-charge, low-tenure accounts.",
        },
    },
    "sales": {
        "id": "sales", "name": "Rossmann Store Sales", "file": "rossmann_sales.csv",
        "rows": 1017209, "cols": 18, "task": "Regression", "target": "Sales",
        "goal": "Forecast daily sales for each store over the next six weeks.",
        "accent": "#9ae64a", "error": "ValueError: could not convert string to float: 'StateHoliday'",
        "fix": "df['StateHoliday'] = df['StateHoliday'].astype('category').cat.codes",
        "results": {
            "taskLabel": "Regression", "bestModel": "LightGBM Regressor",
            "headline": {"fraction": 0.93, "value": "0.93", "label": "R2 score"},
            "metrics": [{"label": "R2", "value": "0.93"}, {"label": "RMSPE", "value": "8.4%"},
                        {"label": "MAE", "value": "421"}, {"label": "RMSE", "value": "612"}],
            "barsTitle": "Feature importance",
            "bars": [{"label": "Promo", "value": 0.81, "sign": 1}, {"label": "Day of week", "value": 0.55, "sign": -1},
                     {"label": "Competition dist.", "value": 0.40, "sign": -1}, {"label": "Store type", "value": 0.33, "sign": 1},
                     {"label": "School holiday", "value": 0.18, "sign": 1}],
            "distTitle": "Average sales by day of week",
            "dist": [{"label": "Monday", "value": 0.98, "display": "9.7k"}, {"label": "Wednesday", "value": 0.71, "display": "7.0k"},
                     {"label": "Friday", "value": 0.83, "display": "8.2k"}, {"label": "Sunday", "value": 0.12, "display": "1.2k"}],
            "report": ["Running promotions is by far the largest driver of daily sales. Sales peak on Mondays and dip sharply on Sundays when many stores are closed.",
                       "Proximity to competition has a measurable negative effect, while certain store types consistently outperform. The model forecasts six weeks ahead with an 8.4% error."],
            "recommendation": "Concentrate promotional spend on high-traffic weekdays and stores facing nearby competition, where the forecasted uplift is greatest.",
        },
    },
    "segments": {
        "id": "segments", "name": "Mall Customer Segmentation", "file": "mall_customers.csv",
        "rows": 200, "cols": 5, "task": "Clustering", "target": "Segment",
        "goal": "Group customers into meaningful segments by income and spending behavior.",
        "accent": "#a78bfa", "error": "ValueError: Input X contains NaN",
        "fix": "X = StandardScaler().fit_transform(df.dropna())",
        "results": {
            "taskLabel": "Clustering", "bestModel": "KMeans (k=4)",
            "headline": {"value": "4", "label": "segments"},
            "metrics": [{"label": "Clusters", "value": "4"}, {"label": "Silhouette", "value": "0.55"},
                        {"label": "Features", "value": "2"}, {"label": "Samples", "value": "200"}],
            "barsTitle": "Defining dimensions",
            "bars": [{"label": "Spending score", "value": 0.88}, {"label": "Annual income", "value": 0.79}, {"label": "Age", "value": 0.34}],
            "distTitle": "Segment sizes",
            "dist": [{"label": "Premium", "value": 0.18, "display": "18%"}, {"label": "Careful", "value": 0.22, "display": "22%"},
                     {"label": "Budget", "value": 0.35, "display": "35%"}, {"label": "Impulsive", "value": 0.25, "display": "25%"}],
            "report": ["Four clear segments emerge along income and spending-score axes. The 'Premium' group combines high income with high spending, while a 'Careful' group earns well but spends little.",
                       "The largest cluster is budget-conscious, and an 'Impulsive' group spends beyond what their income would suggest."],
            "recommendation": "Target the 'Careful' high-income segment with premium offers to unlock latent spend, and use loyalty perks to retain the 'Premium' group.",
        },
    },
    "reviews": {
        "id": "reviews", "name": "Product Reviews", "file": "reviews.csv",
        "rows": 10000, "cols": 3, "task": "NLP + analytics", "target": "Sentiment",
        "goal": "Analyze sentiment and surface the top recurring themes in customer reviews.",
        "accent": "#fb7185", "error": "LookupError: Resource punkt not found",
        "fix": "nltk.download('punkt', quiet=True)",
        "results": {
            "taskLabel": "NLP + analytics", "bestModel": "TF-IDF + Logistic Regression",
            "headline": {"fraction": 0.62, "value": "62%", "label": "positive"},
            "metrics": [{"label": "Reviews", "value": "10k"}, {"label": "Positive", "value": "62%"},
                        {"label": "Negative", "value": "24%"}, {"label": "Neutral", "value": "14%"}],
            "barsTitle": "Top themes by frequency",
            "bars": [{"label": "Delivery speed", "value": 0.74}, {"label": "Product quality", "value": 0.66},
                     {"label": "Price / value", "value": 0.52}, {"label": "Customer support", "value": 0.39}, {"label": "Packaging", "value": 0.27}],
            "distTitle": "Sentiment distribution",
            "dist": [{"label": "Positive", "value": 0.62, "display": "62%"}, {"label": "Neutral", "value": 0.14, "display": "14%"},
                     {"label": "Negative", "value": 0.24, "display": "24%"}],
            "report": ["Overall sentiment is positive, with 62% of reviews favorable. Delivery speed is the most-discussed theme and the leading source of negative sentiment, followed by product quality.",
                       "Price and value are mentioned often and viewed favorably, while customer support, though less frequent, skews negative when raised."],
            "recommendation": "Prioritize fixing delivery reliability - it is the top theme and the biggest driver of negative reviews - and amplify the positive price-value perception in marketing.",
        },
    },
}
print("loaded", len(DATASETS), "datasets")'''
)

# ─────────────────────────── Cell 5: hybrid LLM ───────────────────────────
code(
    '''# Hybrid LLM layer: MockLLM by default; any OpenAI-compatible API when configured.
import os, requests

class MockLLM:
    is_mock = True
    def complete(self, role, context):
        if role == "planner":  return "\\n".join(context.get("plan", []))
        if role == "coder":    return "\\n".join(context.get("code", []))
        if role == "critic":   return str(context.get("fix", ""))
        if role == "reporter":
            rep = context.get("report", []); rec = context.get("recommendation", "")
            return "\\n\\n".join(rep) + (("\\n\\nRecommendation: " + rec) if rec else "")
        return ""

SYSTEM = {
    "planner": "You are a senior data scientist. Output a concise numbered analysis plan (max 6 steps), one per line, no prose.",
    "coder": "You are an expert Python data scientist. Output only runnable Python - no prose, no markdown fences.",
    "critic": "You are a debugging expert. Given a traceback, output a single corrected line that fixes it. Code only.",
    "reporter": "You are a business analyst. Write a short plain-English narrative of the findings, then a one-line recommendation.",
}

def _build_prompt(role, context):
    ds = context.get("dataset", {})
    head = "Dataset: " + str(ds.get("name", "?")) + " (" + str(ds.get("rows", "?")) + " rows x " + str(ds.get("cols", "?")) + " cols). Task: " + str(ds.get("task", "?")) + ". Target: " + str(ds.get("target", "?")) + ". "
    if role == "planner":  return head + "Goal: " + context.get("goal", "") + ". Write the plan."
    if role == "coder":    return head + "Step: " + context.get("step", "") + ". Write the Python."
    if role == "critic":   return "Traceback: " + context.get("error", "") + ". Write the fix."
    if role == "reporter": return head + "Metrics: " + context.get("metrics", "") + ". Drivers: " + context.get("drivers", "") + ". Write the report + recommendation."
    return head

class OpenAICompatibleLLM:
    is_mock = False
    def __init__(self, base_url, api_key, model):
        self.base_url = base_url.rstrip("/"); self.api_key = api_key; self.model = model
    def complete(self, role, context):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        body = {"model": self.model, "temperature": 0.2,
                "messages": [{"role": "system", "content": SYSTEM.get(role, "")},
                             {"role": "user", "content": _build_prompt(role, context)}]}
        r = requests.post(self.base_url + "/chat/completions", json=body, headers=headers, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

def _resolve(role):
    def pick(suffix):
        return os.getenv("HELIX_" + role.upper() + "_" + suffix) or os.getenv("HELIX_LLM_" + suffix, "")
    return pick("BASE_URL"), pick("API_KEY"), pick("MODEL")

def get_llm(role):
    base, key, model = _resolve(role)
    if base or key:
        return OpenAICompatibleLLM(base or "https://openrouter.ai/api/v1", key, model or "deepseek/deepseek-coder")
    return MockLLM()

print("LLM layer ready -", "MOCK" if get_llm("planner").is_mock else "REAL")'''
)

# ──────────────────── Cell 6: agents + LangGraph graph ────────────────────
code(
    '''# The 7 agents as a real LangGraph state graph (synchronous, notebook-friendly).
import time
from typing import TypedDict, Optional, Callable, Any
from langgraph.graph import StateGraph, START, END

AGENTS = [
    {"id": "planner",   "name": "Planner",   "emoji": "\\U0001F9E0", "accent": "#8b5cf6", "tech": "DeepSeek-Coder"},
    {"id": "coder",     "name": "Coder",     "emoji": "\\U0001F4BB", "accent": "#25d7f0", "tech": "DeepSeek-Coder"},
    {"id": "executor",  "name": "Executor",  "emoji": "\\u2699\\ufe0f", "accent": "#38bdf8", "tech": "Sandbox"},
    {"id": "critic",    "name": "Critic",    "emoji": "\\U0001F527", "accent": "#fbbf24", "tech": "Self-heal"},
    {"id": "automl",    "name": "AutoML",    "emoji": "\\u2728",       "accent": "#9ae64a", "tech": "FLAML"},
    {"id": "explainer", "name": "Explainer", "emoji": "\\U0001F50D", "accent": "#e879f9", "tech": "SHAP"},
    {"id": "reporter",  "name": "Reporter",  "emoji": "\\U0001F4DD", "accent": "#fb7185", "tech": "Mistral-7B"},
]
AGENT_IDS = [a["id"] for a in AGENTS]
PACE = 0.32

class RunState(TypedDict, total=False):
    dataset: dict
    goal: str
    plan: list
    code: list
    error: Optional[str]
    retries: int
    results: Optional[dict]
    emit: Any

def planner(state):
    ds, emit = state["dataset"], state["emit"]
    is_cluster = ds["task"] == "Clustering"; is_nlp = ds["task"] == "NLP + analytics"
    emit("planner", status="active")
    emit("planner", log={"text": "> objective: " + state["goal"], "kind": "muted"}); time.sleep(PACE)
    emit("planner", log={"text": "detected task -> " + ds["task"] + " | target: " + ds["target"], "kind": "info"})
    curated = ["1. load & validate dataset", "2. exploratory data analysis", "3. clean & impute missing values",
               "4. scale & select features" if is_cluster else "4. encode categorical features",
               "5. cluster & profile segments" if is_cluster else "5. train model on " + ds["target"],
               "6. extract themes & sentiment" if is_nlp else "6. evaluate & explain"]
    text = get_llm("planner").complete("planner", {"goal": state["goal"], "dataset": ds, "plan": curated})
    plan = [ln.strip() for ln in text.splitlines() if ln.strip()][:6] or curated
    emit("planner", log={"text": "drafting analysis plan...", "kind": "muted"})
    for line in plan:
        time.sleep(0.22); emit("planner", log={"text": line, "kind": "code"})
    emit("planner", log={"text": "plan ready (6 steps)", "kind": "ok"}); emit("planner", status="done")
    return {"plan": plan}

def coder(state):
    ds, emit = state["dataset"], state["emit"]
    is_nlp = ds["task"] == "NLP + analytics"
    emit("coder", status="active")
    curated = ["import pandas as pd", 'df = pd.read_csv("' + ds["file"] + '")',
               "X = TfidfVectorizer().fit_transform(df.text)" if is_nlp else 'X = df.drop("' + ds["target"] + '", axis=1)']
    text = get_llm("coder").complete("coder", {"dataset": ds, "step": "load + features", "code": curated})
    lines = [ln for ln in text.splitlines() if ln.strip()][:8] or curated
    for line in lines:
        time.sleep(0.26); emit("coder", log={"text": line, "kind": "code"})
    emit("coder", log={"text": "generated code for 6 steps", "kind": "ok"}); emit("coder", status="done")
    return {"code": lines}

def executor(state):
    ds, emit = state["dataset"], state["emit"]; retries = state.get("retries", 0)
    emit("executor", status="active")
    if retries == 0:
        emit("executor", log={"text": "> sandbox start  (fs: off | net: off)", "kind": "muted"}); time.sleep(0.4)
        emit("executor", log={"text": "loaded " + format(ds["rows"], ",") + " rows x " + str(ds["cols"]) + " cols", "kind": "info"}); time.sleep(0.45)
        emit("executor", log={"text": "Traceback (most recent call last):", "kind": "err"})
        emit("executor", log={"text": "  " + ds["error"], "kind": "err"}); emit("executor", status="error")
        return {"error": ds["error"]}
    emit("executor", log={"text": "> re-running patched code...", "kind": "muted"}); time.sleep(0.45)
    emit("executor", log={"text": "OK all 6 steps executed", "kind": "ok"}); emit("executor", status="done")
    return {"error": None}

def route_after_executor(state):
    if state.get("error") and state.get("retries", 0) < 5:
        return "critic"
    return "automl"

def critic(state):
    ds, emit = state["dataset"], state["emit"]; retries = state.get("retries", 0)
    emit("critic", status="active")
    emit("critic", log={"text": "analyzing traceback...", "kind": "muted"}); time.sleep(0.45)
    fix = get_llm("critic").complete("critic", {"error": ds["error"], "fix": ds["fix"], "dataset": ds}).strip()
    fix = fix.splitlines()[0] if fix else ds["fix"]
    emit("critic", log={"text": "patch -> " + fix, "kind": "warn"})
    emit("critic", log={"text": "retry " + str(retries + 1) + " / 5", "kind": "warn"}); time.sleep(0.35)
    emit("critic", log={"text": "OK fix applied", "kind": "ok"}); emit("critic", status="done")
    return {"retries": retries + 1, "error": None}

def automl(state):
    ds, emit = state["dataset"], state["emit"]; r = ds["results"]
    emit("automl", status="active")
    if ds["task"] == "Clustering":
        emit("automl", log={"text": "KMeans k-search  k in [2, 8]", "kind": "muted"}); time.sleep(0.4)
        emit("automl", log={"text": "  k=4  silhouette 0.55  * best", "kind": "ok"})
    else:
        emit("automl", log={"text": "flaml.AutoML(budget=60s)  searching...", "kind": "muted"}); time.sleep(0.45)
        ms = r["metrics"][1] if len(r["metrics"]) > 1 else r["metrics"][0]
        emit("automl", log={"text": "  " + r["bestModel"] + "  " + ms["label"] + " " + ms["value"] + "  * best", "kind": "ok"})
    emit("automl", log={"text": "selected -> " + r["bestModel"], "kind": "info"}); emit("automl", status="done")
    return {}

def explainer(state):
    ds, emit = state["dataset"], state["emit"]; r = ds["results"]
    emit("explainer", status="active")
    emit("explainer", log={"text": "computing SHAP values...", "kind": "muted"}); time.sleep(0.4)
    for b in r["bars"][:3]:
        sign = "-" if b.get("sign") == -1 else "+" if b.get("sign") == 1 else " "
        time.sleep(0.25)
        emit("explainer", log={"text": "  " + b["label"].ljust(18) + " " + sign + str(round(b["value"], 2)), "kind": "code"})
    emit("explainer", log={"text": "explanations ready", "kind": "ok"}); emit("explainer", status="done")
    return {}

def reporter(state):
    ds, emit = state["dataset"], state["emit"]; base = ds["results"]
    emit("reporter", status="active")
    emit("reporter", log={"text": "drafting business narrative...", "kind": "muted"}); time.sleep(0.5)
    llm = get_llm("reporter")
    drivers = ", ".join(b["label"] for b in base["bars"][:3])
    metrics = ", ".join(m["label"] + " " + m["value"] for m in base["metrics"])
    text = llm.complete("reporter", {"report": base["report"], "recommendation": base["recommendation"], "dataset": ds, "drivers": drivers, "metrics": metrics})
    results = dict(base)
    if not llm.is_mock and text:
        paras = [p.strip() for p in text.split("\\n\\n") if p.strip()]
        if paras:
            results["report"] = paras[:-1] or paras
            results["recommendation"] = paras[-1].replace("Recommendation:", "").strip()
    emit("reporter", log={"text": "OK report generated", "kind": "ok"}); emit("reporter", status="done")
    return {"results": results}

def build_graph():
    g = StateGraph(RunState)
    for name, fn in [("planner", planner), ("coder", coder), ("executor", executor), ("critic", critic),
                     ("automl", automl), ("explainer", explainer), ("reporter", reporter)]:
        g.add_node(name, fn)
    g.add_edge(START, "planner"); g.add_edge("planner", "coder"); g.add_edge("coder", "executor")
    g.add_conditional_edges("executor", route_after_executor, {"critic": "critic", "automl": "automl"})
    g.add_edge("critic", "executor"); g.add_edge("automl", "explainer")
    g.add_edge("explainer", "reporter"); g.add_edge("reporter", END)
    return g.compile()

GRAPH = build_graph()

def run_graph_sync(dataset_id, goal, emit):
    ds = dict(DATASETS[dataset_id])
    if goal:
        ds["goal"] = goal
    state = {"dataset": ds, "goal": goal or ds["goal"], "retries": 0, "error": None, "emit": emit}
    final = GRAPH.invoke(state)
    return final.get("results") or ds["results"]

print("LangGraph pipeline compiled:", " -> ".join(AGENT_IDS))'''
)

# ─────────────────────── Cell 7: Gradio UI + runner ───────────────────────
code(
    '''# Gradio UI that streams the live run (status + log + results).
import gradio as gr, threading, queue, html as _html

LOG_COLOR = {"info": "#c9d6ef", "code": "#9fb0cc", "ok": "#9ae64a", "err": "#fb7185", "warn": "#fbbf24", "muted": "#76859f"}
ACCENT = {a["id"]: a["accent"] for a in AGENTS}
LABELS = [d["name"] for d in DATASETS.values()]
LABEL_TO_ID = {d["name"]: d["id"] for d in DATASETS.values()}
ID_TO_GOAL = {d["id"]: d["goal"] for d in DATASETS.values()}

def status_html(statuses, critic_fixed=False):
    out = "<div style=\\'display:flex;gap:6px;flex-wrap:wrap\\'>"
    for a in AGENTS:
        st = statuses.get(a["id"], "queued")
        icon = {"queued": "o", "active": "...", "done": "OK", "error": "X"}[st]
        col = {"queued": "#76859f", "active": a["accent"], "done": "#9ae64a", "error": "#fb7185"}[st]
        bg = "#0e1426" if st == "queued" else a["accent"] + "22"
        tag = " <span style=\\'color:#fbbf24;font-size:9px\\'>+1 fix</span>" if (a["id"] == "critic" and critic_fixed) else ""
        out += "<div style=\\'border:1px solid " + col + "55;background:" + bg + ";border-radius:10px;padding:6px 10px;font-size:12px;color:#c9d6ef\\'>" + a["emoji"] + " " + a["name"] + " <b style=\\'color:" + col + "\\'>" + icon + "</b>" + tag + "</div>"
    return out + "</div>"

def log_html(lines):
    rows = ""
    for stage, text, kind in lines:
        rows += "<div style=\\'display:flex;gap:8px\\'><span style=\\'color:" + ACCENT.get(stage, "#76859f") + "\\'>|</span><span style=\\'color:" + LOG_COLOR.get(kind, "#c9d6ef") + ";white-space:pre-wrap\\'>" + _html.escape(text) + "</span></div>"
    if not rows:
        rows = "<span style=\\'color:#76859f\\'>waiting...</span>"
    return "<div style=\\'font-family:monospace;font-size:12.5px;background:#06080f;border:1px solid #1a2440;border-radius:10px;padding:12px;height:330px;overflow:auto\\'>" + rows + "</div>"

def _bars(bars):
    out = ""
    for b in bars:
        sign = b.get("sign")
        col = "#25d7f0" if (sign is None or sign == 1) else "#fb7185"
        w = str(int(b["value"] * 100))
        out += "<div style=\\'display:flex;align-items:center;gap:8px;margin:5px 0\\'><span style=\\'width:140px;text-align:right;font-size:12px;color:#c9d6ef\\'>" + b["label"] + "</span><div style=\\'flex:1;background:#0e1426;border-radius:6px;height:10px\\'><div style=\\'width:" + w + "%;height:10px;background:" + col + ";border-radius:6px\\'></div></div></div>"
    return out

def _dist(items):
    out = ""
    for d in items:
        w = str(int(d["value"] * 100))
        out += "<div style=\\'margin:6px 0\\'><div style=\\'display:flex;justify-content:space-between;font-size:12px;color:#c9d6ef\\'><span>" + d["label"] + "</span><span style=\\'color:#76859f\\'>" + d["display"] + "</span></div><div style=\\'background:#0e1426;border-radius:6px;height:9px;margin-top:3px\\'><div style=\\'width:" + w + "%;height:9px;background:#8b5cf6;border-radius:6px\\'></div></div></div>"
    return out

def results_html(r, accent):
    if not r:
        return "<div style=\\'color:#76859f;padding:18px\\'>No results yet - run an analysis above.</div>"
    chips = ""
    for m in r["metrics"]:
        chips += "<div style=\\'border:1px solid #1a2440;background:#0a1020;border-radius:10px;padding:10px 14px;text-align:center\\'><div style=\\'font-size:20px;font-weight:700;color:#fff\\'>" + m["value"] + "</div><div style=\\'font-size:10px;color:#76859f;text-transform:uppercase\\'>" + m["label"] + "</div></div>"
    head = "<div style=\\'display:flex;gap:10px;align-items:center;margin-bottom:12px\\'><span style=\\'font-size:30px;font-weight:700;color:" + accent + "\\'>" + r["headline"]["value"] + "</span><span style=\\'font-size:11px;color:#76859f\\'>" + r["headline"]["label"] + "</span><span style=\\'margin-left:auto;font-size:12px;color:#c9d6ef\\'>best: <b>" + r["bestModel"] + "</b></span></div>"
    paras = ""
    for p in r["report"]:
        paras += "<p style=\\'color:#c9d6ef;font-size:13px;line-height:1.6;margin:6px 0\\'>" + p + "</p>"
    rec = "<div style=\\'border:1px solid " + accent + "55;background:" + accent + "11;border-radius:10px;padding:12px;margin-top:8px\\'><b style=\\'color:" + accent + ";font-size:11px;text-transform:uppercase\\'>Recommendation</b><div style=\\'color:#fff;font-size:13px;margin-top:4px\\'>" + r["recommendation"] + "</div></div>"
    return ("<div style=\\'background:#0a1020;border:1px solid #1a2440;border-radius:14px;padding:16px\\'>" + head +
            "<div style=\\'display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px\\'>" + chips + "</div>" +
            "<div style=\\'color:#76859f;font-size:11px;text-transform:uppercase;margin:8px 0\\'>" + r["barsTitle"] + "</div>" + _bars(r["bars"]) +
            "<div style=\\'color:#76859f;font-size:11px;text-transform:uppercase;margin:14px 0 4px\\'>" + r["distTitle"] + "</div>" + _dist(r["dist"]) +
            "<div style=\\'color:#76859f;font-size:11px;text-transform:uppercase;margin:14px 0 4px\\'>Business report</div>" + paras + rec + "</div>")

def run_and_stream(dataset_label, goal):
    ds_id = LABEL_TO_ID[dataset_label]
    accent = DATASETS[ds_id]["accent"]
    q = queue.Queue()
    def emit(stage, status=None, log=None):
        q.put(("event", stage, status, log))
    def worker():
        try:
            res = run_graph_sync(ds_id, goal, emit); q.put(("result", res))
        except Exception as e:
            q.put(("error", str(e)))
        finally:
            q.put(None)
    threading.Thread(target=worker, daemon=True).start()
    statuses = {a: "queued" for a in AGENT_IDS}; lines = []; results = None; fixed = False
    yield status_html(statuses), log_html(lines), results_html(None, accent)
    while True:
        item = q.get()
        if item is None:
            break
        if item[0] == "event":
            _, stage, status, log = item
            if status:
                statuses[stage] = status
                if stage == "critic" and status == "done":
                    fixed = True
            if log:
                lines.append((stage, log["text"], log.get("kind", "info")))
            yield status_html(statuses, fixed), log_html(lines), results_html(results, accent)
        elif item[0] == "result":
            results = item[1]
        elif item[0] == "error":
            lines.append(("planner", "(error: " + item[1] + ")", "err"))
            yield status_html(statuses, fixed), log_html(lines), results_html(results, accent)
    yield status_html(statuses, fixed), log_html(lines), results_html(results, accent)

CSS = ".gradio-container{max-width:1080px !important}"
HEADER = "<div style=\\'text-align:center;padding:6px\\'><h1 style=\\'margin:0;color:#fff\\'>Helix - Autonomous Data Science Agent</h1><p style=\\'color:#76859f;margin:4px\\'>Pick a dataset, set a goal, and watch 7 agents work - with self-correction. (Phases 1-2 demo)</p></div>"

with gr.Blocks(title="Helix", css=CSS, theme=gr.themes.Base()) as demo:
    gr.HTML(HEADER)
    with gr.Row():
        with gr.Column(scale=1):
            ds_dd = gr.Dropdown(LABELS, value=LABELS[0], label="1 - Dataset")
            goal_tb = gr.Textbox(value=list(ID_TO_GOAL.values())[0], lines=3, label="2 - Goal")
            run_btn = gr.Button("Run analysis", variant="primary")
        with gr.Column(scale=2):
            status_out = gr.HTML(label="Agents")
            log_out = gr.HTML(label="Execution log")
    results_out = gr.HTML(label="Results")

    ds_dd.change(lambda lbl: ID_TO_GOAL[LABEL_TO_ID[lbl]], ds_dd, goal_tb)
    run_btn.click(run_and_stream, [ds_dd, goal_tb], [status_out, log_out, results_out])

print("Gradio app built. Run the next cell to launch.")'''
)

# ───────────────────────────── Cell 8: launch ────────────────────────────
code(
    """# Launch — opens inline and prints a public share link (good for Colab).
demo.queue().launch(share=True, debug=False)"""
)

# ──────────────────────────── assemble + write ───────────────────────────
nb = {
    "cells": [
        {
            "cell_type": t,
            "metadata": {},
            "source": s.splitlines(keepends=True),
            **({"execution_count": None, "outputs": []} if t == "code" else {}),
        }
        for (t, s) in CELLS
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out_path = os.path.join(os.path.dirname(__file__), "Helix_Colab.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print("wrote", out_path, "with", len(CELLS), "cells")

# ──────────────────── validate the core logic actually runs ───────────────
print("validating core pipeline...")
ns = {}
exec(CELLS[3][1], ns)  # datasets
exec(CELLS[4][1], ns)  # llm
exec(CELLS[5][1], ns)  # agents + graph
_events = []
def _emit(stage, status=None, log=None):
    _events.append((stage, status, log["text"] if log else None))
_res = ns["run_graph_sync"]("churn", "Predict churn and why", _emit)
_stages = [e[0] for e in _events]
assert "critic" in _stages, "critic did not run"
assert any(e[0] == "executor" and e[1] == "error" for e in _events), "no executor error"
assert _res["bestModel"] == "LightGBM", "unexpected result"
compile(CELLS[6][1], "<cell7-gradio>", "exec")  # syntax-check the gradio cell
print("OK core ran:", len(_events), "events | self-heal fired | results valid | gradio cell compiles")
