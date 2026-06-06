"""Real-analysis run: narrates the 7 agents while doing genuine ML on an
uploaded dataset. The LLM (mock or real) drives Planner/Coder/Critic/Reporter;
the trusted analysis engine does the actual cleaning, modeling, and SHAP.

The cleaning "fixes" the engine really applies are surfaced as the Critic's
self-correction — so on a messy dataset (e.g. Telco's blank TotalCharges) the
self-heal beat is genuinely real, not scripted.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

import pandas as pd

from .analysis import analyze_dataframe, clean
from .llm import get_llm
from .rag import retrieve
from .sandbox import run_in_sandbox, strip_code_fences

Emit = Callable[..., Awaitable[None]]


async def run_real(
    df: pd.DataFrame,
    target: str,
    goal: str,
    task: str,
    emit: Emit,
    time_budget: int = 20,
) -> dict[str, Any]:
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
    await emit("planner", log={"text": f"dataset: {rows:,} rows x {cols} cols  |  target: {target}", "kind": "info"})
    curated_plan = [
        "1. load & validate dataset",
        "2. profile & clean columns",
        "3. encode categorical features",
        f"4. train model to predict {target}",
        "5. evaluate on held-out data",
        "6. explain drivers with SHAP",
    ]
    text = await get_llm("planner").acomplete("planner", {"goal": goal, "dataset": ds_info, "plan": curated_plan})
    plan = [ln.strip() for ln in text.splitlines() if ln.strip()][:6] or curated_plan
    await emit("planner", log={"text": "analysis plan:", "kind": "muted"})
    for line in plan:
        await _p(0.18)
        await emit("planner", log={"text": line, "kind": "code"})
    await emit("planner", log={"text": "plan ready", "kind": "ok"})
    await emit("planner", status="done")

    # ── Coder: write a real analysis snippet (RAG-grounded) ──────────────
    await emit("coder", status="active")
    await emit("coder", log={"text": "retrieving library docs (ChromaDB RAG)...", "kind": "muted"})
    docs = await loop.run_in_executor(None, lambda: retrieve(f"{goal} {target}", 2))
    for d in docs[:2]:
        await emit("coder", log={"text": "  doc: " + d[:66] + "...", "kind": "muted"})
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
    for line in gen.splitlines()[:8]:
        await _p(0.18)
        await emit("coder", log={"text": line, "kind": "code"})
    await emit("coder", log={"text": "code generated", "kind": "ok"})
    await emit("coder", status="done")

    # ── Executor + Critic: run in the sandbox, self-correct real failures ─
    await emit("executor", status="active")
    await emit("executor", log={"text": "> RestrictedPython sandbox  (fs: off | net: off)", "kind": "muted"})
    await _p(0.3)
    await emit("executor", log={"text": f"loaded {rows:,} rows x {cols} cols", "kind": "info"})

    current = gen
    ran_ok = False
    for attempt in range(5):
        res = await loop.run_in_executor(None, lambda c=current: run_in_sandbox(c, {"df": df.copy()}))
        if res.ok:
            for line in (res.stdout or "").strip().splitlines()[:8]:
                await emit("executor", log={"text": "  " + line, "kind": "code"})
            await emit("executor", log={"text": "OK generated code executed", "kind": "ok"})
            ran_ok = True
            break
        await emit("executor", log={"text": "Traceback: " + res.error, "kind": "err"})
        await emit("executor", status="error")
        await emit("critic", status="active")
        await emit("critic", log={"text": "reading traceback...", "kind": "muted"})
        await _p(0.4)
        fixed = await get_llm("critic").acomplete(
            "critic", {"error": res.error, "code": current, "fix": curated_fix, "dataset": ds_info}
        )
        fixed = strip_code_fences(fixed.strip()) or curated_fix
        await emit("critic", log={"text": f"patched the code, retry {attempt + 1}/5", "kind": "warn"})
        await emit("critic", status="done")
        current = fixed
        await emit("executor", status="active")
        await emit("executor", log={"text": "> re-running patched code...", "kind": "muted"})
    if not ran_ok:
        await emit("executor", log={"text": "could not auto-fix in 5 tries; using the trusted engine", "kind": "warn"})

    # surface the real data-cleaning the engine applies
    try:
        _, fixes = clean(df, target)
    except Exception:  # noqa: BLE001
        fixes = []
    for f in fixes[:4]:
        await emit("executor", log={"text": "auto-clean: " + f, "kind": "muted"})

    await emit("executor", log={"text": "training models (FLAML AutoML, ~20s)...", "kind": "muted"})
    results = await loop.run_in_executor(None, lambda: analyze_dataframe(df, target, task, time_budget))
    await emit("executor", log={"text": f"OK trained on {results['_rows']:,} rows", "kind": "ok"})
    await emit("executor", status="done")

    # ── AutoML ───────────────────────────────────────────────────────────
    await emit("automl", status="active")
    await emit("automl", log={"text": "model search complete", "kind": "muted"})
    await _p(0.3)
    hv = results["headline"]
    await emit("automl", log={"text": f"  best: {results['bestModel']}  {hv['label']} {hv['value']}  * best", "kind": "ok"})
    await emit("automl", log={"text": f"task detected -> {results['taskLabel']}", "kind": "info"})
    await emit("automl", status="done")

    # ── Explainer ────────────────────────────────────────────────────────
    await emit("explainer", status="active")
    await emit("explainer", log={"text": "computing " + results["barsTitle"] + "...", "kind": "muted"})
    await _p(0.3)
    for b in results["bars"][:4]:
        sign = "-" if b.get("sign") == -1 else "+"
        await _p(0.22)
        await emit("explainer", log={"text": "  " + str(b["label"]).ljust(18) + " " + sign + str(round(b["value"], 2)), "kind": "code"})
    await emit("explainer", log={"text": "explanations ready", "kind": "ok"})
    await emit("explainer", status="done")

    # ── Reporter ─────────────────────────────────────────────────────────
    await emit("reporter", status="active")
    await emit("reporter", log={"text": "drafting business narrative...", "kind": "muted"})
    await _p(0.4)
    llm = get_llm("reporter")
    drivers = ", ".join(str(d["feature"]) for d in results["_drivers"])
    metrics = ", ".join(m["label"] + " " + m["value"] for m in results["metrics"])
    rtext = await llm.acomplete(
        "reporter",
        {"report": results["report"], "recommendation": results["recommendation"], "dataset": ds_info, "drivers": drivers, "metrics": metrics},
    )
    if not llm.is_mock and rtext:
        paras = [p.strip() for p in rtext.split("\n\n") if p.strip()]
        if paras:
            results["report"] = paras[:-1] or paras
            results["recommendation"] = paras[-1].replace("Recommendation:", "").strip()
    await emit("reporter", log={"text": "OK report generated", "kind": "ok"})
    await emit("reporter", status="done")

    return results


async def _p(s: float = 0.32) -> None:
    await asyncio.sleep(s)
