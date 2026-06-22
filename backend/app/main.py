"""Helix API — Phase 1.

Streams agent events to the Studio over Server-Sent Events. The event producer
is currently a scripted mock (``events.build_events``); Phase 2 swaps it for the
real LangGraph pipeline behind the same ``/api/run`` contract.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from .datasets import dataset_summaries, get_dataset
from .events import build_events
from .llm import set_llm_override
from .pipeline import run_pipeline
from .real_run import run_real
from .schemas import AskRequest, ExportRequest, RunRequest
from .llm import get_llm

# Load backend/.env (e.g. Groq key) if present.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Helix API", version="0.1.0")

_origins = [
    o.strip()
    for o in os.getenv("HELIX_CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
_allow_all = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=not _allow_all,  # browsers forbid credentials + "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "helix", "phase": 1}


@app.get("/api/datasets")
async def datasets() -> list[dict]:
    return dataset_summaries()


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _count_data_rows(path: str) -> int:
    """Cheap streamed newline count (no DataFrame) → approx data-row count."""
    n = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            n += chunk.count(b"\n")
    return max(0, n - 1)  # minus header


def _read_capped(path: str, filename: str = "", max_rows: int = 500_000) -> tuple["pd.DataFrame", int, int]:
    """Read a tabular file (CSV / Excel / Parquet / JSON), systematically
    down-sampling huge CSVs so a 3M-row upload never blows up memory. Records the
    true source size in ``df.attrs`` for transparency."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"
    if ext in ("xlsx", "xls", "parquet", "pq", "json"):
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(path)
        elif ext in ("parquet", "pq"):
            df = pd.read_parquet(path)
        else:
            df = pd.read_json(path)
        cols = int(df.shape[1])
        approx = int(len(df))
        if approx > max_rows:
            df = df.sample(max_rows, random_state=42)
            df.attrs["read_note"] = f"read-sampled {len(df):,} of {approx:,} rows ({ext})"
        df.attrs["source_rows"] = approx
        df.attrs["source_cols"] = cols
        return df, approx, cols
    cols = int(pd.read_csv(path, nrows=0).shape[1])
    approx = _count_data_rows(path)
    if approx <= max_rows:
        df = pd.read_csv(path)
        df.attrs["source_rows"] = int(len(df))
        df.attrs["source_cols"] = cols
        return df, int(len(df)), cols
    frac = max_rows / approx
    parts = [chunk.sample(frac=frac, random_state=42)
             for chunk in pd.read_csv(path, chunksize=100_000)]
    df = pd.concat(parts, ignore_index=True)
    df.attrs["source_rows"] = approx
    df.attrs["source_cols"] = cols
    df.attrs["read_note"] = f"read-sampled {len(df):,} of ~{approx:,} rows at upload (big-data mode)"
    return df, approx, cols


def _llm_config(llms, provider, model, api_key, temperature="0.2", max_tokens="") -> dict | None:
    """Build the per-role LLM config from an explicit ``llms`` map (dict or JSON
    string) or fall back to the legacy single provider/model/apiKey fields.
    Each role config may carry its own ``temperature`` and ``max_tokens``."""
    if isinstance(llms, str) and llms.strip():
        try:
            llms = json.loads(llms)
        except Exception:  # noqa: BLE001
            llms = None
    if isinstance(llms, dict) and llms:
        return llms
    if api_key:
        cfg = {"provider": provider or "groq", "model": model,
               "api_key": api_key, "temperature": temperature}
        if str(max_tokens).strip():
            cfg["max_tokens"] = max_tokens
        return {"default": cfg}
    return None


async def _fallback(req: RunRequest, queue: "asyncio.Queue", reason: str) -> None:
    """Scripted mock so a pipeline failure never breaks the demo."""
    ds = dict(get_dataset(req.datasetId))
    if req.goal:
        ds["goal"] = req.goal
    await queue.put(
        {
            "t": "event",
            "stage": "planner",
            "status": None,
            "log": {"text": f"(pipeline error: {reason} — running scripted fallback)", "kind": "warn"},
        }
    )
    for e in build_events(ds):
        await asyncio.sleep(e["delay"] / 1000)
        await queue.put(
            {"t": "event", "stage": e["stage"], "status": e.get("status"), "log": e.get("log")}
        )
    await queue.put({"t": "result", "results": ds["results"]})


async def _stream(req: RunRequest):
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(stage: str, status: str | None = None, log: dict | None = None) -> None:
        await queue.put({"t": "event", "stage": stage, "status": status, "log": log})

    async def driver() -> None:
        set_llm_override(_llm_config(req.llms, req.provider, req.model, req.apiKey,
                                     req.temperature if req.temperature is not None else "0.2"))
        try:
            results = await run_pipeline(req.datasetId, req.goal, req.fileName, emit)
            await queue.put({"t": "result", "results": results})
        except Exception as exc:  # noqa: BLE001
            await _fallback(req, queue, str(exc))
        finally:
            await queue.put(None)

    task = asyncio.create_task(driver())
    yield _sse({"t": "start", "dataset": req.fileName or get_dataset(req.datasetId)["name"]})
    while True:
        item = await queue.get()
        if item is None:
            break
        yield _sse(item)
    await task
    yield _sse({"t": "done"})


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@app.post("/api/run")
async def run(req: RunRequest) -> StreamingResponse:
    return StreamingResponse(_stream(req), media_type="text/event-stream", headers=_SSE_HEADERS)


async def _analyze_stream(
    df: "pd.DataFrame",
    target: str,
    goal: str,
    task: str,
    filename: str,
    provider: str,
    model: str,
    api_key: str,
    e2b_key: str,
    context: str,
    llms: str,
    temperature: str = "0.2",
    max_tokens: str = "",
):
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(stage: str, status: str | None = None, log: dict | None = None) -> None:
        await queue.put({"t": "event", "stage": stage, "status": status, "log": log})

    async def driver() -> None:
        set_llm_override(_llm_config(llms, provider, model, api_key, temperature, max_tokens))
        try:
            results = await run_real(df, target, goal, task, emit, e2b_key=e2b_key, context=context)
            await queue.put({"t": "result", "results": results})
        except Exception as exc:  # noqa: BLE001
            await queue.put(
                {"t": "event", "stage": "reporter", "status": "error",
                 "log": {"text": "analysis error: " + str(exc), "kind": "err"}}
            )
        finally:
            await queue.put(None)

    job = asyncio.create_task(driver())
    yield _sse({"t": "start", "dataset": filename})
    while True:
        item = await queue.get()
        if item is None:
            break
        yield _sse(item)
    await job
    yield _sse({"t": "done"})


def _sheet_csv_url(u: str) -> str:
    """Turn a Google Sheets share link into its CSV-export URL; pass others through."""
    if "docs.google.com/spreadsheets" in u:
        import re
        m = re.search(r"/d/([a-zA-Z0-9-_]+)", u)
        if m:
            gid = re.search(r"[#&?]gid=(\d+)", u)
            return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid.group(1) if gid else '0'}"
    return u


@app.post("/api/analyze")
async def analyze(
    file: UploadFile | None = File(None),
    dataUrl: str = Form(""),
    target: str = Form(""),
    goal: str = Form(""),
    task: str = Form("auto"),
    provider: str = Form("groq"),
    model: str = Form(""),
    apiKey: str = Form(""),
    e2bKey: str = Form(""),
    context: str = Form(""),
    llms: str = Form(""),
    temperature: str = Form("0.2"),
    maxTokens: str = Form(""),
) -> StreamingResponse:
    filename = (file.filename if file else None) or (dataUrl.split("?")[0].rsplit("/", 1)[-1] if dataUrl else None) or "uploaded.csv"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            if file is not None:
                shutil.copyfileobj(file.file, tmp)
            elif dataUrl.strip():
                import httpx
                resp = httpx.get(_sheet_csv_url(dataUrl.strip()), timeout=40, follow_redirects=True)
                resp.raise_for_status()
                tmp.write(resp.content)
                if not filename or "." not in filename:
                    filename = "data.csv"
            else:
                raise ValueError("no file or data URL provided")
            tmp_path = tmp.name
        df, _src_rows, _src_cols = _read_capped(tmp_path, filename)
    except Exception as exc:  # noqa: BLE001
        err = str(exc)

        async def _err_stream():
            yield _sse({"t": "start", "dataset": filename})
            yield _sse({"t": "event", "stage": "planner", "status": "error",
                        "log": {"text": "could not read CSV: " + err, "kind": "err"}})
            yield _sse({"t": "done"})

        return StreamingResponse(_err_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return StreamingResponse(
        _analyze_stream(
            df, target, goal, task, filename, provider, model, apiKey, e2bKey, context, llms, temperature, maxTokens
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


# ── Transparency: expose the exact prompts + per-agent logic the backend runs ──
_AGENT_LOGIC: dict[str, str] = {
    "planner": "Reasons step-by-step (chain-of-thought) over the goal + dataset schema to emit a concise numbered analysis plan.",
    "coder": "Writes real pandas/scikit-learn Python for the plan, grounded in docs retrieved from the ChromaDB RAG store so it hallucinates fewer APIs.",
    "executor": "Runs the generated code in a sandbox and captures stdout + full tracebacks. Engine: E2B microVM when an E2B key is set (true VM isolation + hard timeout), otherwise an in-process RestrictedPython jail.",
    "critic": "Reads the traceback from a failed run, diagnoses the cause, and rewrites the FULL corrected script — looping with the Executor up to 5 times until the code runs clean (self-correcting execution).",
    "automl": "FLAML searches estimators (LightGBM, XGBoost, Random Forest, Extra Trees, …) under a time budget that scales with data size and returns the best-tuned model by the chosen metric.",
    "explainer": "Computes SHAP values (TreeExplainer) to rank global feature importance AND its direction (raises vs lowers the target), with a permutation-importance fallback.",
    "visualizer": "Chooses the BEST chart type per finding for this dataset/context and may request safe aggregations — but the engine fills every number from the real data, so a chart can never show a fabricated value (invalid specs are dropped).",
    "researcher": "Builds queries from the goal, context tags and the model's drivers, runs live web search (Tavily if keyed, else keyless DuckDuckGo), and synthesises real-world domain context with cited sources.",
    "reporter": "Writes the board-ready business narrative + a prioritised recommendation from the metrics, drivers, segments, data quality, the model-quality verdict and (optionally) the live research — honestly flagging weak signal.",
}

_SANDBOX_INFO = {
    "default_engine": "RestrictedPython (in-process AST jail) — used when no E2B key is set",
    "hardened_engine": "E2B microVM (remote, true VM isolation + hard timeout) — used when an E2B key is set",
    "allowed_imports": ["pandas", "numpy", "math", "statistics", "random", "datetime",
                        "collections", "itertools", "functools", "re", "json", "sklearn", "scipy"],
    "blocked": ["open / file I/O", "os, sys, socket, subprocess", "any import outside the allow-list",
                "dunder / underscore attribute access (sandbox-escape vector)", "network access"],
    "captured": "stdout (via PrintCollector) and the last line of any traceback, returned as SandboxResult(ok, stdout, error, engine).",
}


@app.get("/api/prompts")
async def prompts() -> dict:
    """Return the exact system prompt + plain-English logic for every agent, so the
    Studio can show users what is really running behind each stage."""
    from .llm import _SYSTEM

    roles = ["planner", "coder", "executor", "critic", "automl",
             "explainer", "visualizer", "researcher", "reporter"]
    llm_roles = {"planner", "coder", "critic", "reporter", "researcher", "visualizer"}
    return {
        "agents": {
            r: {
                "llm": r in llm_roles,
                "system": _SYSTEM.get(r, ""),
                "logic": _AGENT_LOGIC.get(r, ""),
            }
            for r in roles
        },
        "sandbox": _SANDBOX_INFO,
    }


def _summarize_results(r: dict) -> str:
    """Compact text summary of a results dict for the analyst Q&A grounding."""
    if not isinstance(r, dict):
        return ""
    h = r.get("headline", {}) or {}
    parts = [
        f"Task: {r.get('taskLabel', '?')}. Best model: {r.get('bestModel', '?')}. "
        f"Headline: {h.get('value', '')} {h.get('label', '')}.",
        "Metrics: " + ", ".join(f"{m.get('label')} {m.get('value')}" for m in (r.get("metrics") or [])),
        "Top drivers: " + ", ".join(
            f"{b.get('label')} (importance {round(float(b.get('value', 0)), 2)}"
            + (", raises" if b.get("sign", 0) and b["sign"] > 0 else ", lowers" if b.get("sign", 0) and b["sign"] < 0 else "")
            + ")" for b in (r.get("bars") or [])[:6]),
    ]
    if r.get("distTitle"):
        parts.append(f"{r['distTitle']}: " + ", ".join(
            f"{d.get('label')} {d.get('display')}" for d in (r.get("dist") or [])[:6]))
    if r.get("_stats_tests"):
        parts.append("Significance: " + "; ".join(
            f"{t.get('feature')} {t.get('test')} p={'<0.001' if t.get('p', 1) < 0.001 else round(t.get('p', 1), 3)}"
            + (" (sig)" if t.get("significant") else " (n.s.)") for t in r["_stats_tests"][:6]))
    if r.get("_cv"):
        cv = r["_cv"]
        parts.append(f"{cv.get('k')}-fold CV {cv.get('metric')}: {cv.get('mean')} ± {cv.get('std')}.")
    v = r.get("_verdict") or {}
    if v:
        parts.append(f"Model quality: {v.get('label')} — {v.get('detail')}")
    if r.get("_corr"):
        parts.append("Correlations: " + ", ".join(f"{c.get('a')}~{c.get('b')} r={c.get('r')}" for c in r["_corr"][:5]))
    if r.get("recommendation"):
        parts.append("Recommendation: " + str(r["recommendation"]))
    return "\n".join(p for p in parts if p)


@app.post("/api/ask")
async def ask(req: AskRequest) -> dict:
    """Answer a natural-language question about an analysis, grounded in its results."""
    set_llm_override(_llm_config(req.llms, req.provider, req.model, req.apiKey,
                                 req.temperature if req.temperature is not None else "0.2"))
    llm = get_llm("analyst")
    if getattr(llm, "is_mock", True):
        return {"answer": "Connect an AI key in the Studio's AI engine to chat about your results."}
    summary = _summarize_results(req.results)
    try:
        answer = await llm.acomplete("analyst", {"question": req.question, "summary": summary})
    except Exception as exc:  # noqa: BLE001
        return {"answer": "Could not reach the model: " + str(exc)}
    return {"answer": (answer or "").strip()}


@app.post("/api/export")
async def export(req: ExportRequest) -> Response:
    """Export the results as a PowerPoint deck (.pptx) or a Markdown report."""
    from . import export as exporter

    safe = "".join(c for c in (req.dataset or "analysis") if c.isalnum() or c in "-_") or "analysis"
    if req.format == "md":
        data = exporter.build_markdown(req.results, req.goal, req.dataset)
        return Response(content=data, media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="helix-{safe}.md"'})
    data = exporter.build_pptx(req.results, req.goal, req.dataset)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="helix-{safe}.pptx"'},
    )
