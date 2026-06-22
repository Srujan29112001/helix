"""Real-analysis run: narrates the 7 agents while doing genuine ML on an
uploaded dataset. The LLM (mock or real) drives Planner/Coder/Critic/Reporter;
the trusted analysis engine does the actual cleaning, modeling, and SHAP.

The cleaning "fixes" the engine really applies are surfaced as the Critic's
self-correction — so on a messy dataset (e.g. Telco's blank TotalCharges) the
self-heal beat is genuinely real, not scripted.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Awaitable, Callable

import pandas as pd

from .analysis import analyze_dataframe, build_chart_cards, clean, _is_classification, _auto_target
from .llm import get_llm
from .rag import retrieve
from .sandbox import execute_code, strip_code_fences
from .web_search import web_research

Emit = Callable[..., Awaitable[None]]


async def run_real(
    df: pd.DataFrame,
    target: str,
    goal: str,
    task: str,
    emit: Emit,
    time_budget: int = 20,
    e2b_key: str = "",
    context: str = "",
) -> dict[str, Any]:
    # resolve an "Auto-detect" target for supervised tasks before anything narrates it
    # (clustering/anomaly/dim-reduction are unsupervised → never auto-pick a target)
    auto_target = False
    if task not in ("clustering", "anomaly", "dimreduction", "recommendation") and (not target or target.strip().lower() == "auto"):
        target = _auto_target(df)
        auto_target = True
    rows, cols = df.shape
    ds_info = {
        "name": "uploaded dataset",
        "rows": int(rows),
        "cols": int(cols),
        "task": task if task != "auto" else "to be detected",
        "target": target,
        "columns": list(df.columns)[:40],
    }
    goal = goal or f"Analyze {target} and explain the key drivers."
    loop = asyncio.get_event_loop()

    # ── Planner ──────────────────────────────────────────────────────────
    await emit("planner", status="active")
    await emit("planner", log={"text": "> objective: " + goal, "kind": "muted"})
    await _p()
    tgt_label = f"{target} (auto-detected)" if auto_target else target
    await emit("planner", log={"text": f"dataset: {rows:,} rows x {cols} cols  |  target: {tgt_label}", "kind": "info"})
    curated_plan = [
        "1. load & validate dataset",
        "2. profile & clean columns",
        "3. encode categorical features",
        f"4. train model to predict {target}",
        "5. evaluate on held-out data",
        "6. explain drivers with SHAP",
    ]
    text = await get_llm("planner").acomplete("planner", {"goal": goal, "dataset": ds_info, "plan": curated_plan})
    plan = [ln.strip() for ln in text.splitlines() if ln.strip()] or curated_plan
    await emit("planner", log={"text": "analysis plan:", "kind": "muted"})
    for line in plan:
        await _p(0.18)
        await emit("planner", log={"text": line, "kind": "code"})
    await emit("planner", log={"text": "plan ready", "kind": "ok"})
    await emit("planner", status="done")

    # ── Coder: write a real analysis snippet (RAG-grounded) ──────────────
    await emit("coder", status="active")
    await emit("coder", log={"text": "retrieving library docs (ChromaDB RAG)...", "kind": "muted"})
    docs = await loop.run_in_executor(None, lambda: retrieve(f"{goal} {target}", 3))
    for d in docs:
        await emit("coder", log={"text": "  RAG doc: " + d, "kind": "muted"})
    safe_target = target.replace('"', "").replace("\\", "")
    curated_code = (
        'print("rows:", df.shape[0], " cols:", df.shape[1])\n'
        f'print("target {safe_target}:", df["{safe_target}"].nunique(), "unique")\n'
        'print("column means:")\n'
        "print(df.mean(numeric_only=False).round(2).to_string())"
    )
    curated_fix = curated_code.replace("numeric_only=False", "numeric_only=True")
    gen = await get_llm("coder").acomplete(
        "coder",
        {"dataset": ds_info, "step": "profile the dataset", "code": [curated_code], "docs": docs},
    )
    gen = strip_code_fences(gen) or curated_code
    code_lines = gen.splitlines()
    await emit("coder", log={"text": "# generated analysis code:", "kind": "muted"})
    for line in code_lines:
        await _p(0.08)
        await emit("coder", log={"text": line or " ", "kind": "code"})
    await emit("coder", log={"text": f"code generated ({len(code_lines)} lines)", "kind": "ok"})
    await emit("coder", status="done")

    # ── Executor + Critic: run in the sandbox, self-correct real failures ─
    await emit("executor", status="active")
    sandbox_label = (
        "E2B microVM  (isolated VM | hard timeout)"
        if (e2b_key or os.getenv("E2B_API_KEY"))
        else "RestrictedPython sandbox  (fs: off | net: off)"
    )
    await emit("executor", log={"text": "> " + sandbox_label, "kind": "muted"})
    await _p(0.3)
    await emit("executor", log={"text": f"loaded {rows:,} rows x {cols} cols", "kind": "info"})

    current = gen
    ran_ok = False
    fixes = 0
    for attempt in range(5):
        await emit("executor", log={"text": f">>> executing code (attempt {attempt + 1})", "kind": "muted"})
        res = await loop.run_in_executor(None, lambda c=current: execute_code(c, df, e2b_key))
        if res.ok:
            await emit("executor", log={"text": "--- stdout ---", "kind": "muted"})
            for line in (res.stdout or "").rstrip().splitlines() or ["(no output)"]:
                await emit("executor", log={"text": line, "kind": "code"})
            await emit("executor", log={"text": f"OK code executed in {res.engine} (exit 0)", "kind": "ok"})
            ran_ok = True
            break
        # show the FULL traceback the sandbox returned
        await emit("executor", log={"text": "--- traceback ---", "kind": "err"})
        for line in str(res.error).splitlines() or [str(res.error)]:
            await emit("executor", log={"text": line, "kind": "err"})
        await emit("executor", status="error")
        # Critic: diagnose + emit the full corrected script
        await emit("critic", status="active")
        await emit("critic", log={"text": "reading traceback + diagnosing the failure...", "kind": "muted"})
        await _p(0.4)
        fixed = await get_llm("critic").acomplete(
            "critic", {"error": res.error, "code": current, "fix": curated_fix, "dataset": ds_info}
        )
        fixed = strip_code_fences(fixed.strip()) or curated_fix
        fixes += 1
        # concise diagnosis = the exception line of the traceback (the full
        # traceback was already streamed above); keep this line readable.
        _err_lines = [ln.strip() for ln in str(res.error).splitlines() if ln.strip()]
        diag = (_err_lines[-1] if _err_lines else str(res.error))[:160]
        await emit("critic", log={"text": f"diagnosis: {diag}", "kind": "warn"})
        await emit("critic", log={"text": "root cause identified — rewriting the script", "kind": "muted"})
        await emit("critic", log={"text": "# corrected code:", "kind": "muted"})
        for line in fixed.splitlines():
            await emit("critic", log={"text": line or " ", "kind": "code"})
        await emit("critic", log={"text": f"patched the code -> retry {attempt + 1}/5", "kind": "warn"})
        await emit("critic", status="done")
        current = fixed
        await emit("executor", status="active")
        await emit("executor", log={"text": ">>> re-running patched code...", "kind": "muted"})
    if not ran_ok:
        await emit("executor", log={"text": "could not auto-fix in 5 tries; using the trusted engine", "kind": "warn"})
    # the Critic only runs on a failure — if the code passed first try, say so
    # explicitly so the agent never looks stuck at "queued".
    if fixes == 0:
        await emit("critic", status="active")
        await emit("critic", log={"text": "code passed on the first try — no self-correction needed", "kind": "muted"})
        await emit("critic", status="done")

    # surface the real data-cleaning the engine applies
    try:
        _, fixes = clean(df, target)
    except Exception:  # noqa: BLE001
        fixes = []
    if auto_target:
        await emit("executor", log={"text": f"auto-detected target column: '{target}'", "kind": "info"})
    for f in fixes:
        await emit("executor", log={"text": "auto-clean: " + f, "kind": "muted"})

    await emit("executor", log={"text": "training models (FLAML AutoML, scaled to data size)...", "kind": "muted"})
    # run training off-thread and heartbeat every few seconds so big-data fits
    # (which can run a minute+) never trip an idle-connection timeout.
    fit_task = loop.run_in_executor(None, lambda: analyze_dataframe(df, target, task, time_budget))
    waited = 0
    while not fit_task.done():
        await asyncio.sleep(5)
        waited += 5
        await emit("executor", log={"text": f"  …model search in progress ({waited}s)", "kind": "muted"})
    results = await fit_task
    if auto_target:
        results.setdefault("_fixes", []).insert(0, f"auto-detected target column '{target}'")
    tr, te = results.get("_train_rows"), results.get("_test_rows")
    if tr and te:
        await emit("executor", log={"text": f"train/test split: {tr:,} train / {te:,} test (80/20)", "kind": "info"})
    await emit("executor", log={"text": f"OK trained on {results['_rows']:,} rows", "kind": "ok"})
    await emit("executor", status="done")

    # ── AutoML ───────────────────────────────────────────────────────────
    await emit("automl", status="active")
    opt = results.get("_metric")
    await emit("automl", log={"text": f"FLAML model search complete (optimized {opt})" if opt else "model search complete", "kind": "muted"})
    await _p(0.3)
    hv = results["headline"]
    await emit("automl", log={"text": f"  best model: {results['bestModel']}  ({hv['label']} {hv['value']})  * best", "kind": "ok"})
    await emit("automl", log={"text": f"task detected -> {results['taskLabel']}", "kind": "info"})
    # transparent: stream every evaluation metric on the held-out test set
    await emit("automl", log={"text": "test-set metrics:", "kind": "muted"})
    for m in results.get("metrics", []):
        await _p(0.16)
        await emit("automl", log={"text": "  " + str(m["label"]).ljust(12) + " " + str(m["value"]), "kind": "code"})
    v = results.get("_verdict")
    if v:
        vkind = "ok" if v["level"] in ("excellent", "good") else ("warn" if v["level"] == "weak" else "info")
        await emit("automl", log={"text": f"model quality: {v['label']} — {v['detail']}", "kind": vkind})
    await emit("automl", status="done")

    # ── Explainer ────────────────────────────────────────────────────────
    await emit("explainer", status="active")
    await emit("explainer", log={"text": "computing " + results["barsTitle"] + " (SHAP)...", "kind": "muted"})
    await _p(0.3)
    await emit("explainer", log={"text": "feature".ljust(20) + "importance  effect", "kind": "muted"})
    for b in results["bars"]:
        sign = b.get("sign", 0)
        eff = "raises" if sign > 0 else ("lowers" if sign < 0 else "")
        await _p(0.1)
        await emit("explainer", log={"text": "  " + str(b["label"]).ljust(18) + " " + f"{b['value']:.2f}".ljust(10) + " " + eff, "kind": "code"})
    st_tests = results.get("_stats_tests") or []
    if st_tests:
        await emit("explainer", log={"text": "statistical tests (feature ~ target):", "kind": "muted"})
        for t in st_tests[:8]:
            pv = "<0.001" if t["p"] < 0.001 else f"{t['p']:.3f}"
            tag = "sig" if t["significant"] else "n.s."
            await emit("explainer", log={"text": "  " + str(t["feature"])[:18].ljust(18) + " " + str(t["test"]).ljust(14) + " p=" + pv + " [" + tag + "]", "kind": "code"})
    await emit("explainer", log={"text": f"explanations ready ({len(results['bars'])} features ranked)", "kind": "ok"})
    await emit("explainer", status="done")

    # ── Visualizer: LLM picks the best charts; the engine fills real data ─
    await emit("visualizer", status="active")
    await emit("visualizer", log={"text": "choosing the best charts for this dataset...", "kind": "muted"})
    try:
        if task == "clustering" or not target:
            clean_df, is_clf = df, False
        else:
            clean_df, _ = clean(df, target)
            is_clf = _is_classification(clean_df[target]) if target in clean_df.columns else False
        avail = [ref for key, ref in (
            ("_corr", "corr"), ("_hist", "hist"), ("_scatter", "scatter"), ("_box", "box"),
        ) if results.get(key)]
        if results.get("bars"):
            avail.append("bars")
        if results.get("dist"):
            avail.append("dist")
        if results.get("_stats"):
            avail.append("stats")
        vtext = await get_llm("visualizer").acomplete(
            "visualizer",
            {"goal": goal, "context": context, "target": target, "dataset": ds_info,
             "profile": results.get("_profile", []), "insights": avail},
        )
        cards = await loop.run_in_executor(
            None, lambda: build_chart_cards(clean_df, target, results, is_clf, vtext)
        )
        results["_charts"] = cards or None
        if cards:
            await emit("visualizer", log={"text": "chart plan (type · title):", "kind": "muted"})
            for c in cards:
                await emit("visualizer", log={"text": f"  {str(c['type']).ljust(10)} · {c['title']}", "kind": "code"})
            await emit("visualizer", log={"text": f"composed {len(cards)} chart cards (chart + table + note)", "kind": "ok"})
    except Exception as exc:  # noqa: BLE001
        results["_charts"] = None
        await emit("visualizer", log={"text": "chart selection skipped: " + str(exc), "kind": "warn"})
    await emit("visualizer", status="done")

    # ── Researcher: live web research for domain context ─────────────────
    await emit("researcher", status="active")
    drivers_list = [str(d["feature"]) for d in results["_drivers"]]
    ctx_prefix = (context + " ") if context else ""
    queries = [q for q in [
        f"{ctx_prefix}{goal}".strip(),
        f"{ctx_prefix}{target} key factors {drivers_list[0]}".strip() if drivers_list else "",
        f"{ctx_prefix}{target} analysis benchmarks".strip(),
    ] if q]
    await emit("researcher", log={"text": "search queries:", "kind": "muted"})
    for q in queries:
        await emit("researcher", log={"text": "  ? " + q, "kind": "code"})
    hits = await loop.run_in_executor(None, lambda: web_research(queries, 5))
    if hits:
        await emit("researcher", log={"text": f"--- {len(hits)} live sources ---", "kind": "muted"})
        for h in hits:
            await emit("researcher", log={"text": "  - " + (h["title"] or h["url"]), "kind": "code"})
            if h.get("url"):
                await emit("researcher", log={"text": "    " + h["url"], "kind": "muted"})
    else:
        await emit("researcher", log={"text": "no live results — using domain knowledge", "kind": "warn"})
    research_text = await get_llm("researcher").acomplete(
        "researcher",
        {"goal": goal, "context": context, "drivers": ", ".join(drivers_list), "hits": hits, "dataset": ds_info},
    )
    await emit("researcher", log={"text": "--- synthesis ---", "kind": "muted"})
    for line in (research_text or "").splitlines() or [research_text or ""]:
        if line.strip():
            await emit("researcher", log={"text": line, "kind": "code"})
    await emit("researcher", log={"text": "synthesised external context", "kind": "ok"})
    await emit("researcher", status="done")
    results["_research"] = {"queries": queries, "hits": hits[:6], "synthesis": research_text}

    # ── Reporter ─────────────────────────────────────────────────────────
    await emit("reporter", status="active")
    await emit("reporter", log={"text": "drafting business narrative...", "kind": "muted"})
    await _p(0.4)
    llm = get_llm("reporter")
    drivers = ", ".join(
        f"{d['feature']} ({'increases' if d.get('direction', 0) >= 0 else 'decreases'} it)"
        for d in results["_drivers"]
    )
    metrics = ", ".join(m["label"] + " " + m["value"] for m in results["metrics"])
    breakdown = results.get("distTitle", "") + " — " + ", ".join(
        f"{d['label']}: {d.get('display', round(d['value'], 2))}" for d in results.get("dist", [])[:5]
    )
    stats = "; ".join(f"{s['label']} {s['value']}" for s in results.get("_stats", []))
    corr = "; ".join(f"{c['a']}~{c['b']} r={c['r']}" for c in results.get("_corr", []))
    q = results.get("_quality") or {}
    quality = (
        f"score {q.get('score', '?')}/100, {q.get('missing', '?')}% missing, "
        f"{q.get('duplicates', 0)} duplicate rows" if q else ""
    )
    smart = " | ".join(s["text"] for s in results.get("_insights_text", [])[:6])
    common = {
        "dataset": ds_info, "drivers": drivers, "metrics": metrics, "breakdown": breakdown,
        "stats": stats, "correlations": corr, "quality": quality, "smart": smart,
        "verdict": (results.get("_verdict") or {}).get("detail", ""),
        "sigtests": "; ".join(t["interpretation"] for t in (results.get("_stats_tests") or [])[:5]),
    }
    orig_report = list(results["report"])
    orig_rec = results["recommendation"]
    # baseline (no web research) defaults to the curated text
    results["_report_base"] = orig_report
    results["_recommendation_base"] = orig_rec

    def _parse(txt: str):
        paras = [p.strip() for p in (txt or "").split("\n\n") if p.strip()]
        if not paras:
            return None, None
        return (paras[:-1] or paras), paras[-1].replace("Recommendation:", "").strip()

    # WITH live web research
    rtext = await llm.acomplete(
        "reporter", {"report": orig_report, "recommendation": orig_rec, **common, "research": research_text}
    )
    if not llm.is_mock and rtext:
        rep, rec = _parse(rtext)
        if rep:
            results["report"], results["recommendation"] = rep, rec
        # WITHOUT web research — the baseline, for the comparison toggle
        btext = await llm.acomplete(
            "reporter", {"report": orig_report, "recommendation": orig_rec, **common, "research": ""}
        )
        brep, brec = _parse(btext)
        if brep:
            results["_report_base"], results["_recommendation_base"] = brep, brec
    await emit("reporter", log={"text": "OK report generated", "kind": "ok"})
    await emit("reporter", status="done")

    return results


async def _p(s: float = 0.32) -> None:
    await asyncio.sleep(s)
