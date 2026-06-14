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
from fastapi.responses import StreamingResponse

from .datasets import dataset_summaries, get_dataset
from .events import build_events
from .llm import set_llm_override
from .pipeline import run_pipeline
from .real_run import run_real
from .schemas import RunRequest

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


def _read_capped(path: str, max_rows: int = 250_000) -> tuple["pd.DataFrame", int, int]:
    """Read a CSV, systematically down-sampling huge files so a 3M-row upload never
    blows up memory. Records the true source size in ``df.attrs`` for transparency."""
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


def _llm_config(llms, provider, model, api_key) -> dict | None:
    """Build the per-role LLM config from an explicit ``llms`` map (dict or JSON
    string) or fall back to the legacy single provider/model/apiKey fields."""
    if isinstance(llms, str) and llms.strip():
        try:
            llms = json.loads(llms)
        except Exception:  # noqa: BLE001
            llms = None
    if isinstance(llms, dict) and llms:
        return llms
    if api_key:
        return {"default": {"provider": provider or "groq", "model": model, "api_key": api_key}}
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
        set_llm_override(_llm_config(req.llms, req.provider, req.model, req.apiKey))
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
):
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(stage: str, status: str | None = None, log: dict | None = None) -> None:
        await queue.put({"t": "event", "stage": stage, "status": status, "log": log})

    async def driver() -> None:
        set_llm_override(_llm_config(llms, provider, model, api_key))
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


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    target: str = Form(""),
    goal: str = Form(""),
    task: str = Form("auto"),
    provider: str = Form("groq"),
    model: str = Form(""),
    apiKey: str = Form(""),
    e2bKey: str = Form(""),
    context: str = Form(""),
    llms: str = Form(""),
) -> StreamingResponse:
    filename = file.filename or "uploaded.csv"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        df, _src_rows, _src_cols = _read_capped(tmp_path)
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
            df, target, goal, task, filename, provider, model, apiKey, e2bKey, context, llms
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
