"""Builds the scripted timeline of agent events for a run.

This is the **mock** producer for Phase 1: it emits exactly the event shape the
real LangGraph pipeline will emit in Phase 2 (``stage`` / ``status`` / ``log``),
so the frontend contract is locked now and the agent internals can be filled in
later without touching the client.
"""

from __future__ import annotations

from typing import Any


def build_events(ds: dict[str, Any]) -> list[dict[str, Any]]:
    r = ds["results"]
    is_cluster = ds["task"] == "Clustering"
    is_nlp = ds["task"] == "NLP + analytics"
    ev: list[dict[str, Any]] = []

    def push(delay, stage, log=None, status=None):
        item: dict[str, Any] = {"delay": delay, "stage": stage}
        if status:
            item["status"] = status
        if log:
            item["log"] = log
        ev.append(item)

    def log(text, kind="info"):
        return {"text": text, "kind": kind}

    # Planner
    push(200, "planner", status="active")
    push(500, "planner", log(f"> objective: {ds['goal']}", "muted"))
    push(700, "planner", log(f"detected task → {ds['task']}  ·  target: {ds['target']}", "info"))
    push(500, "planner", log("drafting analysis plan…", "muted"))
    plan = [
        "1. load & validate dataset",
        "2. exploratory data analysis",
        "3. clean & impute missing values",
        "4. scale & select features" if is_cluster else "4. encode categorical features",
        "5. cluster & profile segments" if is_cluster else f"5. train model on {ds['target']}",
        "6. extract themes & sentiment" if is_nlp else "6. evaluate & explain",
    ]
    for line in plan:
        push(260, "planner", log(line, "code"))
    push(400, "planner", log("plan ready (6 steps)", "ok"), status="done")

    # Coder
    push(300, "coder", status="active")
    push(450, "coder", log("import pandas as pd", "code"))
    push(350, "coder", log(f'df = pd.read_csv("{ds["file"]}")', "code"))
    push(
        400,
        "coder",
        log(
            "X = TfidfVectorizer().fit_transform(df.text)"
            if is_nlp
            else f'X = df.drop("{ds["target"]}", axis=1)',
            "code",
        ),
    )
    push(400, "coder", log("generated code for 6 steps", "ok"), status="done")

    # Executor → error
    push(300, "executor", status="active")
    push(450, "executor", log("▶ sandbox start  (fs: off · net: off)", "muted"))
    push(500, "executor", log(f"loaded {ds['rows']:,} rows × {ds['cols']} cols", "info"))
    push(600, "executor", log("Traceback (most recent call last):", "err"))
    push(250, "executor", log(f"  {ds['error']}", "err"), status="error")

    # Critic → fix
    push(400, "critic", status="active")
    push(500, "critic", log("analyzing traceback…", "muted"))
    push(550, "critic", log(f"patch → {ds['fix']}", "warn"))
    push(450, "critic", log("↻ retry 1 / 5", "warn"))
    push(500, "critic", log("✓ step passed", "ok"), status="done")

    # Executor resume
    push(300, "executor", log("▶ re-running patched code…", "muted"), status="active")
    push(550, "executor", log("✓ all 6 steps executed", "ok"), status="done")

    # AutoML
    push(350, "automl", status="active")
    if is_cluster:
        push(450, "automl", log("KMeans k-search  k ∈ [2, 8]", "muted"))
        push(400, "automl", log("  k=3  silhouette 0.49", "code"))
        push(350, "automl", log("  k=4  silhouette 0.55  ★ best", "ok"))
    else:
        push(450, "automl", log("flaml.AutoML(budget=60s)  searching…", "muted"))
        ms = r["metrics"][1] if len(r["metrics"]) > 1 else r["metrics"][0]
        push(400, "automl", log(f"  {r['bestModel']}  {ms['label']} {ms['value']}  ★ best", "ok"))
    push(450, "automl", log(f"selected → {r['bestModel']}", "info"), status="done")

    # Explainer
    push(350, "explainer", status="active")
    push(
        450,
        "explainer",
        log(
            "profiling segments…"
            if is_cluster
            else "extracting themes (LDA + sentiment)…"
            if is_nlp
            else "computing SHAP values…",
            "muted",
        ),
    )
    for b in r["bars"][:3]:
        sign = "−" if b.get("sign") == -1 else "+" if b.get("sign") == 1 else " "
        push(300, "explainer", log(f"  {b['label']:<20} {sign}{b['value']:.2f}", "code"))
    push(400, "explainer", log("explanations ready", "ok"), status="done")

    # Reporter
    push(350, "reporter", status="active")
    push(500, "reporter", log("drafting business narrative (Mistral-7B)…", "muted"))
    push(700, "reporter", log("✓ report generated", "ok"), status="done")

    return ev
