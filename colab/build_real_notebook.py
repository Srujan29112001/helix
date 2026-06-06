# Builds Helix_RealData_Colab.ipynb — upload your own CSV (Kaggle etc.) and run a
# GENUINE analysis: clean -> FLAML AutoML -> real metrics -> SHAP -> LLM report,
# narrated by the 7 agents with real self-correction. Run:
#   python colab/build_real_notebook.py
import json
import os

HERE = os.path.dirname(__file__)
CELLS = []


def md(src):
    CELLS.append(("markdown", src))


def code(src):
    CELLS.append(("code", src))


# ───────────────────────────── intro ─────────────────────────────
md(
    """# 🧬 Helix — Real Analysis on YOUR data (Colab)

Upload any tabular **CSV** (e.g. from Kaggle), pick the **target column**, and Helix runs a
*genuine* end-to-end analysis — not a canned demo:

**clean → encode → FLAML AutoML → real metrics → SHAP explainability → LLM report**,
narrated live by the 7 agents, with **real self-correction** on messy columns.

### Recommended test dataset
**Telco Customer Churn** — https://www.kaggle.com/datasets/blastchar/telco-customer-churn
(download the single CSV; target column = `Churn`). It has a genuinely messy `TotalCharges`
column that triggers real auto-correction.

### Use a FREE LLM (optional but recommended)
Paste a free **Groq** key in the config cell to get real LLM plans/reports. Without a key the
agents use an offline mock — **the ML analysis still runs for real either way**.

### ▶ Steps
1. **Runtime → Run all**  (first cell installs FLAML/SHAP — ~1 min)
2. Scroll to the Gradio app, **upload your CSV**, pick the **target**, click **Run real analysis**
"""
)

# ───────────────────────────── install ─────────────────────────────
code(
    """!pip install -q gradio "flaml[automl]" shap scikit-learn requests RestrictedPython chromadb
print("✅ dependencies installed")"""
)

# ───────────────────────────── Groq config ─────────────────────────────
code(
    '''import os

# ── FREE-tier API model (recommended: Groq). Paste your key to enable real LLM. ──
# Get a key (free, no card): https://console.groq.com/keys
os.environ["HELIX_LLM_BASE_URL"] = "https://api.groq.com/openai/v1"
os.environ["HELIX_LLM_API_KEY"]  = ""   # <-- paste gsk_... here (leave blank = offline mock)
os.environ["HELIX_LLM_MODEL"]    = "llama-3.3-70b-versatile"

# Alternatives (free tier, OpenAI-compatible):
#   Gemini:     base "https://generativelanguage.googleapis.com/v1beta/openai", model "gemini-2.0-flash"
#   OpenRouter: base "https://openrouter.ai/api/v1", model "deepseek/deepseek-chat-v3-0324:free"

print("LLM:", ("REAL - " + os.getenv("HELIX_LLM_MODEL")) if os.getenv("HELIX_LLM_API_KEY") else "MOCK (offline; paste a key above for real LLM)")'''
)

# ───────────────────────────── LLM layer (sync) ─────────────────────────────
code(
    '''import os, requests

class MockLLM:
    is_mock = True
    def complete(self, role, context):
        if role == "planner":  return "\\n".join(context.get("plan", []))
        if role == "coder":    return "\\n".join(context.get("code", []))
        if role == "reporter":
            return "\\n\\n".join(context.get("report", [])) + "\\n\\nRecommendation: " + context.get("recommendation", "")
        return ""

SYSTEM = {
    "planner": "You are a senior data scientist. Output a concise numbered analysis plan (max 6 steps), one per line, no prose.",
    "coder": "You are an expert Python data scientist. Output only runnable Python, no prose.",
    "reporter": "You are a business analyst. Write a short plain-English narrative of the findings, then a one-line recommendation.",
}

def _prompt(role, ctx):
    ds = ctx.get("dataset", {})
    head = "Dataset: " + str(ds.get("name","?")) + " (" + str(ds.get("rows","?")) + " rows x " + str(ds.get("cols","?")) + " cols). Task: " + str(ds.get("task","?")) + ". Target: " + str(ds.get("target","?")) + ". "
    if role == "planner":  return head + "Goal: " + ctx.get("goal","") + ". Write the plan."
    if role == "coder":    return head + "Write Python to load and model the data."
    if role == "reporter": return head + "Metrics: " + ctx.get("metrics","") + ". Drivers: " + ctx.get("drivers","") + ". Write the report + a one-line recommendation."
    return head

class APILLM:
    is_mock = False
    def __init__(self, base, key, model):
        self.base = base.rstrip("/"); self.key = key; self.model = model
    def complete(self, role, ctx):
        h = {"Content-Type": "application/json", "Authorization": "Bearer " + self.key}
        body = {"model": self.model, "temperature": 0.2,
                "messages": [{"role":"system","content":SYSTEM.get(role,"")},{"role":"user","content":_prompt(role,ctx)}]}
        r = requests.post(self.base + "/chat/completions", json=body, headers=h, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

class AnthropicLLM:
    is_mock = False
    def __init__(self, base, key, model):
        self.base = base.rstrip("/"); self.key = key; self.model = model
    def complete(self, role, ctx):
        h = {"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {"model": self.model, "max_tokens": 1024, "system": SYSTEM.get(role, ""), "messages": [{"role": "user", "content": _prompt(role, ctx)}]}
        r = requests.post(self.base + "/messages", json=body, headers=h, timeout=60)
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "openai", "llama-3.3-70b-versatile"),
    "openai": ("https://api.openai.com/v1", "openai", "gpt-4o-mini"),
    "deepseek": ("https://api.deepseek.com", "openai", "deepseek-chat"),
    "mistral": ("https://api.mistral.ai/v1", "openai", "mistral-small-latest"),
    "openrouter": ("https://openrouter.ai/api/v1", "openai", "deepseek/deepseek-chat"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "openai", "gemini-2.0-flash"),
    "anthropic": ("https://api.anthropic.com/v1", "anthropic", "claude-3-5-haiku-latest"),
}

def make_llm(provider, model, key):
    if not key:
        return MockLLM()
    base, kind, default = PROVIDERS.get(provider, PROVIDERS["groq"])
    model = model or default
    return AnthropicLLM(base, key, model) if kind == "anthropic" else APILLM(base, key, model)

def get_llm(role):
    base = os.getenv("HELIX_" + role.upper() + "_BASE_URL") or os.getenv("HELIX_LLM_BASE_URL", "")
    key  = os.getenv("HELIX_" + role.upper() + "_API_KEY")  or os.getenv("HELIX_LLM_API_KEY", "")
    model = os.getenv("HELIX_" + role.upper() + "_MODEL")   or os.getenv("HELIX_LLM_MODEL", "")
    if key:
        return APILLM(base or "https://api.groq.com/openai/v1", key, model or "llama-3.3-70b-versatile")
    return MockLLM()

print("LLM layer ready -", "MOCK" if get_llm("planner").is_mock else "REAL")'''
)

# ───────────── analysis engine (verbatim from backend/app/analysis.py) ─────────────
with open(os.path.join(HERE, "..", "backend", "app", "analysis.py"), encoding="utf-8") as f:
    engine_src = f.read()
code("# === Real analysis engine (identical to the local backend) ===\n" + engine_src)

# Sandbox (Phase 3) + RAG (Phase 5), embedded verbatim from the backend.
with open(os.path.join(HERE, "..", "backend", "app", "sandbox.py"), encoding="utf-8") as f:
    sandbox_src = f.read()
code("# === RestrictedPython sandbox (Phase 3) — identical to the backend ===\n" + sandbox_src)

with open(os.path.join(HERE, "..", "backend", "app", "rag.py"), encoding="utf-8") as f:
    rag_src = f.read()
code("# === ChromaDB RAG (Phase 5) — identical to the backend ===\n" + rag_src)

# ───────────────────────── agents + real run (sync) ─────────────────────────
code(
    '''import time

AGENTS = [
    {"id": "planner",   "name": "Planner",   "emoji": "\\U0001F9E0", "accent": "#8b5cf6"},
    {"id": "coder",     "name": "Coder",     "emoji": "\\U0001F4BB", "accent": "#25d7f0"},
    {"id": "executor",  "name": "Executor",  "emoji": "\\u2699\\ufe0f", "accent": "#38bdf8"},
    {"id": "critic",    "name": "Critic",    "emoji": "\\U0001F527", "accent": "#fbbf24"},
    {"id": "automl",    "name": "AutoML",    "emoji": "\\u2728",       "accent": "#9ae64a"},
    {"id": "explainer", "name": "Explainer", "emoji": "\\U0001F50D", "accent": "#e879f9"},
    {"id": "reporter",  "name": "Reporter",  "emoji": "\\U0001F4DD", "accent": "#fb7185"},
]
AGENT_IDS = [a["id"] for a in AGENTS]

def run_real_sync(df, target, goal, task, emit, llm=None):
    if llm is None:
        llm = get_llm("planner")
    rows, cols = df.shape
    ds_info = {"name": "uploaded dataset", "rows": int(rows), "cols": int(cols), "task": task, "target": target, "columns": list(df.columns)[:40]}
    goal = goal or ("Analyze " + target + " and explain the key drivers.")

    emit("planner", status="active")
    emit("planner", log={"text": "> objective: " + goal, "kind": "muted"}); time.sleep(0.3)
    emit("planner", log={"text": "dataset: " + format(rows, ",") + " rows x " + str(cols) + " cols | target: " + target, "kind": "info"})
    curated = ["1. load & validate dataset", "2. profile & clean columns", "3. encode features", "4. train model to predict " + target, "5. evaluate on held-out data", "6. explain drivers with SHAP"]
    plan = [l.strip() for l in llm.complete("planner", {"goal": goal, "dataset": ds_info, "plan": curated}).splitlines() if l.strip()][:6] or curated
    for l in plan:
        time.sleep(0.16); emit("planner", log={"text": l, "kind": "code"})
    emit("planner", status="done")

    emit("coder", status="active")
    emit("coder", log={"text": "retrieving library docs (ChromaDB RAG)...", "kind": "muted"})
    docs = retrieve(goal + " " + target, 2)
    for d in docs[:2]:
        emit("coder", log={"text": "  doc: " + d[:66] + "...", "kind": "muted"})
    curated = "print('rows:', df.shape[0], 'cols:', df.shape[1])\\nprint('column means:')\\nprint(df.mean(numeric_only=False).round(2).to_string())"
    curated_fix = curated.replace("numeric_only=False", "numeric_only=True")
    gen = strip_code_fences(llm.complete("coder", {"dataset": ds_info, "step": "profile the dataset", "code": [curated], "docs": docs})) or curated
    for l in gen.splitlines()[:8]:
        time.sleep(0.15); emit("coder", log={"text": l, "kind": "code"})
    emit("coder", status="done")

    emit("executor", status="active")
    emit("executor", log={"text": "> RestrictedPython sandbox  (fs: off | net: off)", "kind": "muted"}); time.sleep(0.3)
    emit("executor", log={"text": "loaded " + format(rows, ",") + " rows x " + str(cols) + " cols", "kind": "info"})
    current = gen; ran_ok = False
    for attempt in range(5):
        res = run_in_sandbox(current, {"df": df.copy()})
        if res.ok:
            for l in (res.stdout or "").strip().splitlines()[:8]:
                emit("executor", log={"text": "  " + l, "kind": "code"})
            emit("executor", log={"text": "OK generated code executed", "kind": "ok"}); ran_ok = True; break
        emit("executor", log={"text": "Traceback: " + res.error, "kind": "err"}); emit("executor", status="error")
        emit("critic", status="active"); emit("critic", log={"text": "reading traceback...", "kind": "muted"}); time.sleep(0.4)
        fixed = strip_code_fences(llm.complete("critic", {"error": res.error, "code": current, "fix": curated_fix}).strip()) or curated_fix
        emit("critic", log={"text": "patched the code, retry " + str(attempt + 1) + "/5", "kind": "warn"}); emit("critic", status="done")
        current = fixed
        emit("executor", status="active"); emit("executor", log={"text": "> re-running patched code...", "kind": "muted"})
    if not ran_ok:
        emit("executor", log={"text": "could not auto-fix; using the trusted engine", "kind": "warn"})
    try:
        _, fixes = clean(df, target)
    except Exception:
        fixes = []
    for fx in fixes[:4]:
        emit("executor", log={"text": "auto-clean: " + fx, "kind": "muted"})
    emit("executor", log={"text": "training models (FLAML AutoML, ~20s)...", "kind": "muted"})
    results = analyze_dataframe(df, target, task, 20)
    emit("executor", log={"text": "OK trained on " + format(results["_rows"], ",") + " rows", "kind": "ok"}); emit("executor", status="done")

    emit("automl", status="active"); hv = results["headline"]
    emit("automl", log={"text": "  best: " + results["bestModel"] + "  " + hv["label"] + " " + hv["value"] + "  * best", "kind": "ok"})
    emit("automl", log={"text": "task detected -> " + results["taskLabel"], "kind": "info"}); emit("automl", status="done")

    emit("explainer", status="active"); emit("explainer", log={"text": "computing " + results["barsTitle"] + "...", "kind": "muted"}); time.sleep(0.3)
    for b in results["bars"][:4]:
        sign = "-" if b.get("sign") == -1 else "+"; time.sleep(0.2)
        emit("explainer", log={"text": "  " + str(b["label"]).ljust(18) + " " + sign + str(round(b["value"], 2)), "kind": "code"})
    emit("explainer", status="done")

    emit("reporter", status="active"); emit("reporter", log={"text": "drafting business narrative...", "kind": "muted"}); time.sleep(0.4)
    drivers = ", ".join(str(d["feature"]) for d in results["_drivers"]); metrics = ", ".join(m["label"] + " " + m["value"] for m in results["metrics"])
    rtext = llm.complete("reporter", {"report": results["report"], "recommendation": results["recommendation"], "dataset": ds_info, "drivers": drivers, "metrics": metrics})
    if not llm.is_mock and rtext:
        paras = [p.strip() for p in rtext.split("\\n\\n") if p.strip()]
        if paras:
            results["report"] = paras[:-1] or paras; results["recommendation"] = paras[-1].replace("Recommendation:", "").strip()
    emit("reporter", log={"text": "OK report generated", "kind": "ok"}); emit("reporter", status="done")
    return results

print("real-run ready:", " -> ".join(AGENT_IDS))'''
)

# ───────────────────────────── Gradio UI ─────────────────────────────
code(
    '''import gradio as gr, threading, queue, html as _html, pandas as pd

LOG_COLOR = {"info": "#c9d6ef", "code": "#9fb0cc", "ok": "#9ae64a", "err": "#fb7185", "warn": "#fbbf24", "muted": "#76859f"}
ACCENT = {a["id"]: a["accent"] for a in AGENTS}

def status_html(statuses, fixed=False):
    out = "<div style=\\'display:flex;gap:6px;flex-wrap:wrap\\'>"
    for a in AGENTS:
        st = statuses.get(a["id"], "queued")
        icon = {"queued": "o", "active": "...", "done": "OK", "error": "X"}[st]
        col = {"queued": "#76859f", "active": a["accent"], "done": "#9ae64a", "error": "#fb7185"}[st]
        bg = "#0e1426" if st == "queued" else a["accent"] + "22"
        tag = " <span style=\\'color:#fbbf24;font-size:9px\\'>fixed</span>" if (a["id"] == "critic" and fixed) else ""
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
        col = "#25d7f0" if b.get("sign", 1) >= 0 else "#fb7185"
        w = str(int(b["value"] * 100))
        out += "<div style=\\'display:flex;align-items:center;gap:8px;margin:5px 0\\'><span style=\\'width:150px;text-align:right;font-size:12px;color:#c9d6ef\\'>" + str(b["label"]) + "</span><div style=\\'flex:1;background:#0e1426;border-radius:6px;height:10px\\'><div style=\\'width:" + w + "%;height:10px;background:" + col + ";border-radius:6px\\'></div></div></div>"
    return out

def _dist(items):
    out = ""
    for d in items:
        w = str(int(d["value"] * 100))
        out += "<div style=\\'margin:6px 0\\'><div style=\\'display:flex;justify-content:space-between;font-size:12px;color:#c9d6ef\\'><span>" + str(d["label"]) + "</span><span style=\\'color:#76859f\\'>" + str(d["display"]) + "</span></div><div style=\\'background:#0e1426;border-radius:6px;height:9px;margin-top:3px\\'><div style=\\'width:" + w + "%;height:9px;background:#8b5cf6;border-radius:6px\\'></div></div></div>"
    return out

def results_html(r, accent="#25d7f0"):
    if not r:
        return "<div style=\\'color:#76859f;padding:18px\\'>No results yet - upload a CSV and run.</div>"
    chips = ""
    for m in r["metrics"]:
        chips += "<div style=\\'border:1px solid #1a2440;background:#0a1020;border-radius:10px;padding:10px 14px;text-align:center\\'><div style=\\'font-size:20px;font-weight:700;color:#fff\\'>" + m["value"] + "</div><div style=\\'font-size:10px;color:#76859f;text-transform:uppercase\\'>" + m["label"] + "</div></div>"
    head = "<div style=\\'display:flex;gap:10px;align-items:center;margin-bottom:12px\\'><span style=\\'font-size:30px;font-weight:700;color:" + accent + "\\'>" + r["headline"]["value"] + "</span><span style=\\'font-size:11px;color:#76859f\\'>" + r["headline"]["label"] + "</span><span style=\\'margin-left:auto;font-size:12px;color:#c9d6ef\\'>best: <b>" + r["bestModel"] + "</b></span></div>"
    paras = ""
    for p in r["report"]:
        paras += "<p style=\\'color:#c9d6ef;font-size:13px;line-height:1.6;margin:6px 0\\'>" + _html.escape(p) + "</p>"
    rec = "<div style=\\'border:1px solid " + accent + "55;background:" + accent + "11;border-radius:10px;padding:12px;margin-top:8px\\'><b style=\\'color:" + accent + ";font-size:11px;text-transform:uppercase\\'>Recommendation</b><div style=\\'color:#fff;font-size:13px;margin-top:4px\\'>" + _html.escape(r["recommendation"]) + "</div></div>"
    return ("<div style=\\'background:#0a1020;border:1px solid #1a2440;border-radius:14px;padding:16px\\'>" + head +
            "<div style=\\'display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px\\'>" + chips + "</div>" +
            "<div style=\\'color:#76859f;font-size:11px;text-transform:uppercase;margin:8px 0\\'>" + r["barsTitle"] + "</div>" + _bars(r["bars"]) +
            "<div style=\\'color:#76859f;font-size:11px;text-transform:uppercase;margin:14px 0 4px\\'>" + r["distTitle"] + "</div>" + _dist(r["dist"]) +
            "<div style=\\'color:#76859f;font-size:11px;text-transform:uppercase;margin:14px 0 4px\\'>Business report</div>" + paras + rec + "</div>")

def on_upload(path):
    if not path:
        return gr.update(choices=[], value=None)
    try:
        cols = list(pd.read_csv(path, nrows=5).columns)
        return gr.update(choices=cols, value=cols[-1] if cols else None)
    except Exception:
        return gr.update(choices=[], value=None)

def run_and_stream(path, goal, target, task, provider, model, key):
    if not path:
        yield "<div style=\\'color:#fb7185\\'>Upload a CSV first.</div>", "", ""
        return
    if not target:
        yield "<div style=\\'color:#fb7185\\'>Pick a target column.</div>", "", ""
        return
    df = pd.read_csv(path)
    llm = make_llm(provider, model, key) if key else get_llm("planner")
    q = queue.Queue()
    def emit(stage, status=None, log=None):
        q.put(("event", stage, status, log))
    def worker():
        try:
            res = run_real_sync(df, target, goal, task, emit, llm); q.put(("result", res))
        except Exception as e:
            q.put(("error", str(e)))
        finally:
            q.put(None)
    threading.Thread(target=worker, daemon=True).start()
    statuses = {a: "queued" for a in AGENT_IDS}; lines = []; results = None; fixed = False
    yield status_html(statuses), log_html(lines), results_html(None)
    while True:
        item = q.get()
        if item is None:
            break
        if item[0] == "event":
            _, stage, status, log = item
            if status:
                statuses[stage] = status
                if stage == "critic" and status == "done": fixed = True
            if log:
                lines.append((stage, log["text"], log.get("kind", "info")))
            yield status_html(statuses, fixed), log_html(lines), results_html(results)
        elif item[0] == "result":
            results = item[1]
        elif item[0] == "error":
            lines.append(("reporter", "(error: " + item[1] + ")", "err"))
            yield status_html(statuses, fixed), log_html(lines), results_html(results)
    yield status_html(statuses, fixed), log_html(lines), results_html(results)

HEADER = "<div style=\\'text-align:center;padding:6px\\'><h1 style=\\'margin:0;color:#fff\\'>Helix - Real Analysis on your data</h1><p style=\\'color:#76859f;margin:4px\\'>Upload a CSV, pick the target, and watch 7 agents run a genuine FLAML + SHAP analysis with self-correction.</p></div>"

with gr.Blocks(title="Helix - Real Data", css=".gradio-container{max-width:1080px !important}", theme=gr.themes.Base()) as demo:
    gr.HTML(HEADER)
    with gr.Row():
        with gr.Column(scale=1):
            file_in = gr.File(label="1 - Upload CSV", file_types=[".csv"], type="filepath")
            target_in = gr.Dropdown(choices=[], label="2 - Target column (what to predict)")
            task_in = gr.Radio(["auto", "classification", "regression"], value="auto", label="Task")
            goal_in = gr.Textbox(value="Analyze the target and explain the key drivers.", lines=2, label="Goal")
            provider_in = gr.Dropdown(["groq", "openai", "deepseek", "anthropic", "mistral", "openrouter", "gemini"], value="groq", label="AI provider")
            model_in = gr.Textbox(value="", placeholder="(optional) model id e.g. llama-3.3-70b-versatile", label="Model")
            key_in = gr.Textbox(value="", type="password", placeholder="(optional) paste key for real LLM", label="API key")
            run_btn = gr.Button("Run real analysis", variant="primary")
        with gr.Column(scale=2):
            status_out = gr.HTML()
            log_out = gr.HTML()
    results_out = gr.HTML()

    file_in.change(on_upload, file_in, target_in)
    run_btn.click(run_and_stream, [file_in, goal_in, target_in, task_in, provider_in, model_in, key_in], [status_out, log_out, results_out])

print("Gradio app built - run the next cell to launch.")'''
)

# ───────────────────────────── launch ─────────────────────────────
code(
    """demo.queue().launch(share=True, debug=False)"""
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
out_path = os.path.join(HERE, "Helix_RealData_Colab.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print("wrote", out_path, "with", len(CELLS), "cells")

# ──────────────────── validate: run a real analysis end-to-end ───────────────
print("validating real run on data/telco_churn.csv ...")
import warnings
warnings.filterwarnings("ignore")
ns = {}
exec(CELLS[3][1], ns)  # LLM layer
exec(CELLS[4][1], ns)  # analysis engine
exec(CELLS[5][1], ns)  # sandbox
exec(CELLS[6][1], ns)  # rag
exec(CELLS[7][1], ns)  # agents + run_real_sync
import pandas as _pd
_df = _pd.read_csv(os.path.join(HERE, "..", "data", "telco_churn.csv"))
_events = []
def _emit(stage, status=None, log=None):
    _events.append((stage, status, log["text"] if log else None))
_res = ns["run_real_sync"](_df, "Churn", "Predict churn", "auto", _emit)
_st = [e[0] for e in _events]
assert "critic" in _st and any(e[0] == "executor" and e[1] == "error" for e in _events), "self-heal missing"
assert _res["headline"]["label"] and _res["bestModel"], "no results"
compile(CELLS[8][1], "<gradio>", "exec")
print("OK real run:", len(_events), "events | best:", _res["bestModel"], _res["headline"]["value"], _res["headline"]["label"], "| gradio compiles")
