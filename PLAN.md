# Helix — Autonomous Data Science Agent · Project Plan

> Capstone (IIIT-H). An autonomous, multi-agent system that turns a CSV + a
> plain-English goal into a business-ready report — planning, coding, executing,
> **self-correcting**, modelling (AutoML), explaining (SHAP) and reporting.
>
> _"Helix" is a working brand name — easy to change._

## Architecture at a glance

```
  Next.js Studio (browser)
        │  POST /api/run   (SSE stream of agent events + artifacts)
        ▼
  FastAPI backend  ──►  LangGraph state graph
                          ├─ Planner   (LLM, chain-of-thought)
                          ├─ Coder     (LLM, RAG-grounded)
                          ├─ Executor  (sandbox)  ◄─┐ retry ≤5
                          ├─ Critic    (LLM)  ──────┘ self-heal
                          ├─ AutoML    (FLAML)
                          ├─ Explainer (SHAP)
                          └─ Reporter  (LLM)
```

The frontend already speaks this event model (stages + log lines + results).
The backend's job is to emit the *real* version of what the Studio currently
simulates.

---

## Phase status

| Phase | Scope | Status |
|------:|-------|--------|
| **0** | **Frontend** — landing + interactive Studio (simulated run) | ✅ **Done** |
| **1** | **Backend skeleton + Studio wired to a live SSE stream (mocked agents)** | ✅ **Done** |
| **2** | **Real LangGraph pipeline + hybrid LLM layer (mock default)** | ✅ **Done** |
| **4** | **Real analysis on any uploaded CSV — FLAML + SHAP + EDA + free API LLM (Groq)** | ✅ **Done** |
| **3** | **RestrictedPython sandbox — runs LLM-generated code, real self-correction** | ✅ **Done** |
| **5** | **RAG grounding — ChromaDB + MiniLM embeddings, grounds the Coder** | ✅ **Done** |
| **6** | **Report agent — LLM narrative + charts + downloadable** | ✅ **Done** |
| **7** | **All 4 task types on uploads — classification, regression, clustering, NLP** | ✅ **Done** |
| **8** | **Evaluation harness — 100% task detection / self-heal / security** | ✅ **Done** |
| **9** | **Deployment — Dockerfiles + compose + DEPLOY.md** | ✅ **Done** |
| **10** | **Presentation deck (`presentation/Helix_Capstone.pptx`)** | ✅ **Done** |

Target: **presentation ~June 21**.

---

## Phase 0 — Frontend ✅ (done)

- Next.js 16 + React 19 + TypeScript + Tailwind v4 + `motion`.
- **Landing**: animated data-field hero, 7-agent pipeline visualizer, capabilities,
  use cases, tech stack, CTA.
- **Studio** (`/studio`): dataset picker + CSV upload, goal input, **live**
  pipeline with self-heal, streaming execution log, results (donut, SHAP bars,
  EDA, business report + download).
- Runs a **simulated** pipeline today — clearly labelled, and a perfect demo
  fallback. Swapping it for the real backend stream is Phase 1.

## Phase 1 — Backend skeleton + wiring ✅ (done)
- `backend/` FastAPI app: `GET /health`, `GET /api/datasets`, `POST /api/run`
  (**SSE** stream of `{stage, status, log}` events → `result` → `done`). CORS
  configured; mocked event producer (`events.build_events`) locks the contract.
- Frontend: `lib/api.ts` fetch-streaming client; Studio uses the live stream
  when `NEXT_PUBLIC_API_URL` is set, with **automatic fallback to simulation**
  if the backend is unreachable. Badge shows live vs. simulated.
- Verified end-to-end: live run streams from FastAPI and renders real results.

## Phase 2 — Core agent pipeline (LangGraph) ✅ (done)
- Real `langgraph` `StateGraph` (`backend/app/pipeline.py`): 7 nodes with a
  conditional self-heal edge `executor → critic → executor` (retry ≤5),
  streaming `{stage, status, log}` events through a queue to SSE.
- Hybrid LLM layer (`backend/app/llm.py`): `MockLLM` by default (zero keys),
  `OpenAICompatibleLLM` for any hosted/local model, resolved **per agent role**
  via env (the "hybrid" decision). Planner/Coder/Critic/Reporter call it.
- Automatic fallback to the scripted mock if the graph errors, so the demo
  never breaks. Verified end-to-end live in the Studio.
- _Still stubbed (next phases):_ Executor runs no real code yet (Phase 3);
  AutoML/SHAP numbers come from the dataset definition (Phase 4).

## Phase 3 — Execution sandbox & safety
- Isolated execution that can actually run pandas / scikit-learn, capturing
  stdout, tracebacks and artifacts, with **time + memory limits** and no
  network/filesystem escape. (See open decision below.)

## Phase 4 — AutoML + SHAP + EDA
- FLAML for model search; SHAP for global/local importance.
- Generate real charts (matplotlib/plotly → PNG/JSON) + metrics; stream to UI.

## Phase 5 — RAG grounding
- ChromaDB + `sentence-transformers`; index pandas/sklearn/FLAML/SHAP docs;
  retrieve to ground the Coder and cut hallucinated APIs.

## Phase 6 — Report agent
- LLM narrative from metrics + drivers; markdown report with embedded charts;
  downloadable (UI already has the button).

## Phase 7 — Multi-dataset robustness
- Validate all four task types (classification, regression, clustering, NLP);
  large-dataset handling (sampling), schema/edge-case handling.

## Phase 8 — Evaluation & metrics
- Self-heal success rate, executable-code rate, model quality, report quality
  (RAGAS/DSPy or a lightweight custom harness).

## Phase 9 — Deployment & docs
- Deploy backend + frontend; secrets; README + architecture docs.

## Phase 10 — Presentation polish
- Demo script, refreshed slides, the simulated mode as a safe fallback.

---

## Decisions

1. **LLM hosting → Hybrid.** Mix local open models with an API for reliability
   (e.g. local Coder + API Reporter, or local-first with API fallback). The LLM
   layer is built as a provider interface so either backend works per-agent.
2. **Execution sandbox → RestrictedPython** (as proposed). Implement with proper
   guards + a curated `safe_globals` so pandas/sklearn run; wrap behind a
   swappable `Executor` interface so we can harden to subprocess/Docker if it
   proves too restrictive in testing. _(Highest-risk component — watch in Phase 3.)_
3. **Deploy target** — TBD (revisit at Phase 9; the hybrid LLM choice keeps GPU
   optional).
