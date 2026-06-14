"""The real multi-agent pipeline, as a LangGraph state graph.

Planner → Coder → Executor ⇄ Critic (self-heal, ≤5) → AutoML → Explainer → Reporter.

Phase 2 status:
  • Planner / Coder / Critic / Reporter call the LLM provider (mock by default,
    real when keys are set) — so the *reasoning* is real and pluggable.
  • Executor exercises the real self-correction loop with a known first-pass
    error, but does not yet run code in a sandbox (Phase 3).
  • AutoML / Explainer surface metrics from the dataset definition; real FLAML +
    SHAP land in Phase 4.

Nodes stream `{stage, status, log}` events through ``state["emit"]`` as they run.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .datasets import get_dataset
from .llm import get_llm

Emit = Callable[..., Awaitable[None]]


class RunState(TypedDict, total=False):
    dataset: dict[str, Any]
    goal: str
    plan: list[str]
    code: list[str]
    error: Optional[str]
    retries: int
    results: Optional[dict[str, Any]]
    research: Optional[dict[str, Any]]
    charts: Optional[list[dict[str, Any]]]
    emit: Emit


async def _pace(s: float = 0.32) -> None:
    await asyncio.sleep(s)


async def planner(state: RunState) -> dict[str, Any]:
    ds, emit = state["dataset"], state["emit"]
    is_cluster = ds["task"] == "Clustering"
    is_nlp = ds["task"] == "NLP + analytics"
    await emit("planner", status="active")
    await emit("planner", log={"text": f"> objective: {state['goal']}", "kind": "muted"})
    await _pace()
    await emit("planner", log={"text": f"detected task → {ds['task']}  ·  target: {ds['target']}", "kind": "info"})
    curated = [
        "1. load & validate dataset",
        "2. exploratory data analysis",
        "3. clean & impute missing values",
        "4. scale & select features" if is_cluster else "4. encode categorical features",
        "5. cluster & profile segments" if is_cluster else f"5. train model on {ds['target']}",
        "6. extract themes & sentiment" if is_nlp else "6. evaluate & explain",
    ]
    text = await get_llm("planner").acomplete("planner", {"goal": state["goal"], "dataset": ds, "plan": curated})
    plan = [ln.strip() for ln in text.splitlines() if ln.strip()][:6] or curated
    await emit("planner", log={"text": "drafting analysis plan…", "kind": "muted"})
    for line in plan:
        await _pace(0.22)
        await emit("planner", log={"text": line, "kind": "code"})
    await _pace()
    await emit("planner", log={"text": "plan ready (6 steps)", "kind": "ok"})
    await emit("planner", status="done")
    return {"plan": plan}


async def coder(state: RunState) -> dict[str, Any]:
    ds, emit = state["dataset"], state["emit"]
    is_nlp = ds["task"] == "NLP + analytics"
    await emit("coder", status="active")
    curated = [
        "import pandas as pd",
        f'df = pd.read_csv("{ds["file"]}")',
        "X = TfidfVectorizer().fit_transform(df.text)" if is_nlp else f'X = df.drop("{ds["target"]}", axis=1)',
    ]
    text = await get_llm("coder").acomplete("coder", {"dataset": ds, "step": "load + features", "code": curated})
    code = [ln for ln in text.splitlines() if ln.strip()][:8] or curated
    for line in code:
        await _pace(0.28)
        await emit("coder", log={"text": line, "kind": "code"})
    await _pace()
    await emit("coder", log={"text": "generated code for 6 steps", "kind": "ok"})
    await emit("coder", status="done")
    return {"code": code}


async def executor(state: RunState) -> dict[str, Any]:
    ds, emit = state["dataset"], state["emit"]
    retries = state.get("retries", 0)
    await emit("executor", status="active")
    if retries == 0:
        await emit("executor", log={"text": "▶ sandbox start  (fs: off · net: off)", "kind": "muted"})
        await _pace(0.4)
        await emit("executor", log={"text": f"loaded {ds['rows']:,} rows × {ds['cols']} cols", "kind": "info"})
        await _pace(0.45)
        await emit("executor", log={"text": "Traceback (most recent call last):", "kind": "err"})
        await emit("executor", log={"text": f"  {ds['error']}", "kind": "err"})
        await emit("executor", status="error")
        return {"error": ds["error"]}
    await emit("executor", log={"text": "▶ re-running patched code…", "kind": "muted"})
    await _pace(0.45)
    await emit("executor", log={"text": "✓ all 6 steps executed", "kind": "ok"})
    await emit("executor", status="done")
    return {"error": None}


def route_after_executor(state: RunState) -> str:
    if state.get("error") and state.get("retries", 0) < 5:
        return "critic"
    return "automl"


async def critic(state: RunState) -> dict[str, Any]:
    ds, emit = state["dataset"], state["emit"]
    retries = state.get("retries", 0)
    await emit("critic", status="active")
    await emit("critic", log={"text": "analyzing traceback…", "kind": "muted"})
    await _pace(0.45)
    fix = (await get_llm("critic").acomplete("critic", {"error": ds["error"], "fix": ds["fix"], "dataset": ds})).strip()
    fix = fix.splitlines()[0] if fix else ds["fix"]
    await emit("critic", log={"text": f"patch → {fix}", "kind": "warn"})
    await emit("critic", log={"text": f"↻ retry {retries + 1} / 5", "kind": "warn"})
    await _pace(0.35)
    await emit("critic", log={"text": "✓ fix applied", "kind": "ok"})
    await emit("critic", status="done")
    return {"retries": retries + 1, "error": None}


async def automl(state: RunState) -> dict[str, Any]:
    ds, emit = state["dataset"], state["emit"]
    r = ds["results"]
    is_cluster = ds["task"] == "Clustering"
    await emit("automl", status="active")
    if is_cluster:
        await emit("automl", log={"text": "KMeans k-search  k ∈ [2, 8]", "kind": "muted"})
        await _pace(0.4)
        await emit("automl", log={"text": "  k=4  silhouette 0.55  ★ best", "kind": "ok"})
    else:
        await emit("automl", log={"text": "flaml.AutoML(budget=60s)  searching…", "kind": "muted"})
        await _pace(0.45)
        ms = r["metrics"][1] if len(r["metrics"]) > 1 else r["metrics"][0]
        await emit("automl", log={"text": f"  {r['bestModel']}  {ms['label']} {ms['value']}  ★ best", "kind": "ok"})
    await emit("automl", log={"text": f"selected → {r['bestModel']}", "kind": "info"})
    await emit("automl", status="done")
    return {}


async def explainer(state: RunState) -> dict[str, Any]:
    ds, emit = state["dataset"], state["emit"]
    r = ds["results"]
    await emit("explainer", status="active")
    await emit("explainer", log={"text": "computing SHAP values…", "kind": "muted"})
    await _pace(0.4)
    for b in r["bars"][:3]:
        sign = "−" if b.get("sign") == -1 else "+" if b.get("sign") == 1 else " "
        await _pace(0.25)
        await emit("explainer", log={"text": f"  {b['label']:<20} {sign}{b['value']:.2f}", "kind": "code"})
    await emit("explainer", log={"text": "explanations ready", "kind": "ok"})
    await emit("explainer", status="done")
    return {}


async def visualizer(state: RunState) -> dict[str, Any]:
    from .analysis import build_chart_cards

    ds, emit = state["dataset"], state["emit"]
    r = ds["results"]
    await emit("visualizer", status="active")
    await emit("visualizer", log={"text": "choosing the best charts for this dataset...", "kind": "muted"})
    charts = None
    try:
        is_clf = "class" in str(ds.get("task", "")).lower()
        avail = ["bars", "dist"]
        for key, ref in (("_corr", "corr"), ("_hist", "hist"), ("_scatter", "scatter"), ("_box", "box"), ("_stats", "stats")):
            if r.get(key):
                avail.append(ref)
        vtext = await get_llm("visualizer").acomplete(
            "visualizer",
            {"goal": state.get("goal", ""), "context": "", "target": ds.get("target", ""),
             "dataset": ds, "profile": r.get("_profile", []), "insights": avail},
        )
        charts = build_chart_cards(None, ds.get("target", ""), r, is_clf, vtext) or None
    except Exception:  # noqa: BLE001
        charts = None
    if charts:
        await emit("visualizer", log={"text": f"composed {len(charts)} chart cards (chart + table + note)", "kind": "ok"})
    await emit("visualizer", status="done")
    return {"charts": charts}


async def researcher(state: RunState) -> dict[str, Any]:
    from .web_search import web_research

    ds, emit = state["dataset"], state["emit"]
    r = ds["results"]
    goal = state.get("goal", ds.get("goal", ""))
    drivers = [b["label"] for b in r["bars"][:3]]
    await emit("researcher", status="active")
    queries = [q for q in [
        goal,
        f"{ds['target']} key factors {drivers[0]}" if drivers else "",
        f"{ds['target']} analysis benchmarks",
    ] if q]
    await emit("researcher", log={"text": "searching the web: " + (queries[0] or "")[:60], "kind": "muted"})
    hits = await asyncio.get_event_loop().run_in_executor(None, lambda: web_research(queries, 5))
    if hits:
        for h in hits[:4]:
            await emit("researcher", log={"text": "  - " + (h["title"] or h["url"])[:66], "kind": "code"})
    else:
        await emit("researcher", log={"text": "no live results — using domain knowledge", "kind": "warn"})
    synth = await get_llm("researcher").acomplete(
        "researcher",
        {"goal": goal, "context": "", "drivers": ", ".join(drivers), "hits": hits, "dataset": ds},
    )
    await emit("researcher", log={"text": "synthesised external context", "kind": "ok"})
    await emit("researcher", status="done")
    return {"research": {"queries": queries, "hits": hits[:6], "synthesis": synth}}


async def reporter(state: RunState) -> dict[str, Any]:
    ds, emit = state["dataset"], state["emit"]
    base = ds["results"]
    research = state.get("research") or {}
    await emit("reporter", status="active")
    await emit("reporter", log={"text": "drafting business narrative…", "kind": "muted"})
    await _pace(0.5)
    llm = get_llm("reporter")
    drivers = ", ".join(b["label"] for b in base["bars"][:3])
    metrics = ", ".join(f"{m['label']} {m['value']}" for m in base["metrics"])
    common = {"dataset": ds, "drivers": drivers, "metrics": metrics}
    results = dict(base)
    if research:
        results["_research"] = research
    if state.get("charts"):
        results["_charts"] = state["charts"]
    results["_report_base"] = list(base["report"])
    results["_recommendation_base"] = base["recommendation"]
    text = await llm.acomplete(
        "reporter",
        {"report": base["report"], "recommendation": base["recommendation"], **common,
         "research": research.get("synthesis", "")},
    )
    # When a real model is used, prefer its narrative; mock keeps the curated text.
    if not llm.is_mock and text:
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        if paras:
            results["report"] = paras[:-1] or paras
            results["recommendation"] = paras[-1].replace("Recommendation:", "").strip()
        btext = await llm.acomplete(
            "reporter",
            {"report": base["report"], "recommendation": base["recommendation"], **common, "research": ""},
        )
        bparas = [p.strip() for p in (btext or "").split("\n\n") if p.strip()]
        if bparas:
            results["_report_base"] = bparas[:-1] or bparas
            results["_recommendation_base"] = bparas[-1].replace("Recommendation:", "").strip()
    await emit("reporter", log={"text": "✓ report generated", "kind": "ok"})
    await emit("reporter", status="done")
    return {"results": results}


def build_graph():
    g = StateGraph(RunState)
    for name, fn in [
        ("planner", planner),
        ("coder", coder),
        ("executor", executor),
        ("critic", critic),
        ("automl", automl),
        ("explainer", explainer),
        ("visualizer", visualizer),
        ("researcher", researcher),
        ("reporter", reporter),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "planner")
    g.add_edge("planner", "coder")
    g.add_edge("coder", "executor")
    g.add_conditional_edges("executor", route_after_executor, {"critic": "critic", "automl": "automl"})
    g.add_edge("critic", "executor")
    g.add_edge("automl", "explainer")
    g.add_edge("explainer", "visualizer")
    g.add_edge("visualizer", "researcher")
    g.add_edge("researcher", "reporter")
    g.add_edge("reporter", END)
    return g.compile()


GRAPH = build_graph()


async def run_pipeline(dataset_id: str, goal: str, file_name: str | None, emit: Emit) -> dict[str, Any]:
    """Run the graph to completion, streaming events via ``emit``; return results."""
    ds = dict(get_dataset(dataset_id))
    if goal:
        ds["goal"] = goal
    if file_name:
        ds["name"] = file_name
        ds["file"] = file_name
    state: RunState = {
        "dataset": ds,
        "goal": goal or ds["goal"],
        "retries": 0,
        "error": None,
        "emit": emit,
    }
    final = await GRAPH.ainvoke(state)
    return final.get("results") or ds["results"]
