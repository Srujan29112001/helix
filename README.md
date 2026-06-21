# Helix — Autonomous Data Science Agent

> Turn a CSV and a plain-English question into a business-ready answer —
> automatically. A **nine-agent** system that **plans, writes code, runs it,
> fixes its own errors, builds a model, explains it, picks the right charts,
> researches the live web, and writes the report.**
>
> Capstone project · IIIT-H. ("Helix" is a working name — easy to change.)

---

## 1. What is this project?

### The problem
Organizations sit on huge amounts of data but struggle to turn it into
decisions, because of three bottlenecks:

1. **Dependency on scarce experts** — business teams must queue for a data
   scientist to answer even simple questions ("why are customers leaving?").
2. **Repetitive grunt work** — 60–70% of an analyst's time goes to cleaning
   CSVs, handling missing values, and rewriting near-identical analysis code.
3. **Brittle iteration** — code breaks, someone reads the traceback, patches
   it, reruns… a slow loop that is painful for non-experts.

### The solution
**Helix** is an autonomous "AI data scientist." You give it:
- a **dataset** (any CSV), and
- a **goal in plain English** (e.g. *"predict which customers will churn"*),

and a team of specialized AI **agents** does the entire workflow with no human
in the loop — including **fixing its own code when it breaks** (the headline
feature: *self-correcting execution*). It ends with metrics, the key drivers
(explainability), a gallery of the right charts, a live-web context pass, and a
short business report with a recommendation.

> **Domain-agnostic.** Helix works on **any tabular CSV from any industry** —
> finance, healthcare, retail, marketing, HR, science, and more. It auto-detects
> the task (**classification, regression, clustering, or NLP/text**), cleans messy
> data, parses dates, and adapts — verified on churn, sales, segmentation, reviews,
> insurance, Titanic, penguins and loan default.

### A concrete example (customer churn — one of many)
1. You upload `telco_churn.csv` and type *"predict churn and the key drivers."*
2. The **Planner** writes a step-by-step plan (load → EDA → clean → encode → train → explain).
3. The **Coder** writes the Python for each step (grounded by RAG).
4. The **Executor** runs it in a sandbox — and hits a `TypeError`.
5. The **Critic** reads the traceback, rewrites the script, and retries — up to
   5 times — until it runs clean.
6. **AutoML** (FLAML) finds the best model (LightGBM, ~0.84 ROC-AUC).
7. **SHAP** explains *why* (contract type and tenure are the biggest drivers).
8. The **Visualizer** picks the best chart per finding; the **Researcher** pulls
   live web context; the **Reporter** writes the business narrative + a recommendation.

What took days now takes minutes — and a non-technical user did it themselves.

---

## 2. Who is it for?

| Audience | What they get |
|----------|---------------|
| **Non-technical business users** | Ask questions in English, get data-backed answers + plain explanations — without a data team. **Primary audience.** |
| **Data scientists / analysts** | Automate the boring 60–70% (cleaning, EDA, baseline modeling) so they focus on judgment. |
| **Small teams / startups** | A "data scientist in a box." |
| **Students & educators** | A transparent, explainable reference for the end-to-end ML + AI-agent workflow. |
| **Evaluators** | A demonstration of multi-agent orchestration, self-correction, AutoML, explainability, and RAG working together. |

---

## 3. How it works (architecture)

Helix is two cooperating parts: a **web app** (the Studio) and an **agent
backend** (the brain), linked by a live Server-Sent-Events stream.

```
  ┌─────────────────────────────────────────────────────────┐
  │  FRONTEND · Next.js Studio (the browser app)             │
  │  upload CSV + type goal → watch agents work live →       │
  │  read the dashboard (charts, 3D graph, business report)  │
  └───────────────┬─────────────────────────────────────────┘
                  │  POST /api/analyze  (Server-Sent Events:
                  │                      a live stream of agent events)
                  ▼
  ┌─────────────────────────────────────────────────────────┐
  │  BACKEND · FastAPI → LangGraph state graph               │
  │                                                          │
  │   Planner → Coder → Executor ──► Critic ──┐ (retry ≤ 5)  │
  │                        ▲                  │ self-heal    │
  │                        └──────────────────┘              │
  │     → AutoML → Explainer → Visualizer → Researcher       │
  │     → Reporter                                           │
  └─────────────────────────────────────────────────────────┘
```

### The nine agents
| # | Agent | Job | Tech |
|---|-------|-----|------|
| 1 | **Planner** | Break the goal into an ordered analysis plan | LLM (chain-of-thought) |
| 2 | **Coder** | Write Python for each step | LLM, RAG-grounded |
| 3 | **Executor** | Run the code safely, capture stdout/errors | Sandbox (RestrictedPython / E2B microVM) |
| 4 | **Critic** | Read tracebacks, rewrite the code, retry (≤5) | LLM — *self-correction* |
| 5 | **AutoML** | Search models + hyper-parameters | FLAML |
| 6 | **Explainer** | Quantify what drives predictions (+ direction) | SHAP |
| 7 | **Visualizer** | Pick the best chart per finding (engine fills real data) | LLM + engine |
| 8 | **Researcher** | Pull live real-world context from the web | DuckDuckGo / Tavily |
| 9 | **Reporter** | Write the business narrative + recommendation | LLM |

These run as a **LangGraph** "state graph": each agent is a node, state flows
between them, and a **conditional edge** loops Executor↔Critic until the code
works (or 5 tries are exhausted). The backend streams **Server-Sent Events** so
you *watch* the agents work — full code, full output, prompts and logic per
stage — instead of staring at a spinner.

---

## 4. Highlights

- **Self-correcting code execution** — the Executor↔Critic loop reads real
  tracebacks and rewrites the code until it runs (up to 5 tries).
- **Big-data ready** — handles files up to ~3M rows: a striped read-sample,
  width-scaled training (up to ~500k rows), a 150-feature cap, 32-bit downcast,
  and a streaming heartbeat so long fits never time out.
- **Honest model-quality verdict** — grades every result from *Strong
  predictive signal* to *Near-chance — weak signal*, so a weak dataset explains
  itself instead of looking broken.
- **Recommended-charts gallery** — the Visualizer chooses chart types (bar,
  column, pie, line, area, radar, histogram, scatter, box, heatmap, statcards);
  the engine fills every number from the real data, so **a chart can never show
  a fabricated value**. Each card ships with a data table + a "how to read this" note.
- **3D Knowledge Graph** — the whole analysis as an explorable force-directed
  map (target, drivers, segments, metrics, charts, quality, columns) with
  hover, click-for-detail, and search.
- **Live web research** — the Researcher grounds the report in real sources,
  with an On/Off toggle to compare the report *with vs without* it.
- **Full transparency** — the Studio shows the **exact system prompt + logic**
  for every agent, the **RestrictedPython / E2B sandbox** rules, and the complete
  code + stdout + tracebacks streamed live (Colab-style).
- **Pluggable LLMs + controls** — one model for all agents *or* a different
  model per agent, a **temperature** slider (global or per-agent), and an
  optional **E2B microVM** key. Keys live only in your browser.

### Providers & models
Bring your own key for any of: **Groq** (free, fast), **OpenAI**, **DeepSeek**,
**Mistral**, **OpenRouter**, **Google Gemini** (free), **Z.ai (GLM)**,
**Anthropic (Claude)**. With no key, Helix runs a deterministic mock for the
narration while still doing **real ML** (FLAML + SHAP).

---

## 5. Tech stack — and why each choice

### Frontend
| Tech | Why |
|------|-----|
| **Next.js 16 + React 19** | Production React framework; a genuinely premium UI (the proposal's Gradio can't). |
| **TypeScript** | Type-safe frontend↔backend event contract. |
| **Tailwind CSS v4** | Fast, consistent styling via utilities + design tokens. |
| **motion (Framer Motion)** | Animations, the live pipeline, scroll reveals. |
| **3d-force-graph + three** | The interactive 3D knowledge graph. |

### Backend
| Tech | Why |
|------|-----|
| **FastAPI** | Modern async Python API with native SSE streaming; minimal boilerplate. |
| **LangGraph** | Purpose-built for **multi-agent, stateful, looping** workflows — the Planner→…→Critic↺ pattern. |
| **Pydantic / httpx** | Request validation; async HTTP to LLM providers. |
| **pandas / scikit-learn** | The standard data-wrangling + ML toolkit. |
| **FLAML** | Lightweight **AutoML** — finds a good model under a time budget. |
| **SHAP** | The standard for **explainability** — "here's why," with direction. |
| **ChromaDB + MiniLM** | **RAG**: ground the Coder in real recipes; fewer hallucinated APIs. |
| **RestrictedPython + E2B** | Sandbox the agent's code — in-process jail by default, hardened microVM with a key. |
| **ddgs / Tavily** | Live web research for the Researcher. |

---

## 6. Repository structure

```
Capstone Project IIITH/
├── README.md            ← this file
├── frontend/            ← Next.js web app (the Studio + landing)
│   ├── app/                 landing + /studio route
│   ├── components/
│   │   ├── landing/         hero, pipeline visualizer, capabilities, use-cases…
│   │   └── studio/
│   │       ├── studio-client.tsx   the live Studio (setup, pipeline, results)
│   │       ├── charts.tsx          chart primitives + ChartCard (chart+table+note)
│   │       └── knowledge-graph.tsx 3D force-directed analysis map
│   └── lib/
│       ├── agents.ts        the 9 agents (shared by UI + studio)
│       ├── studio-run.ts    sample datasets + the RunResults contract
│       └── api.ts           streaming client (SSE)
└── backend/             ← FastAPI service (the agent brain)
    └── app/
        ├── main.py          API routes + SSE streaming + big-data ingest + /api/prompts
        ├── real_run.py      the 9-agent run on an uploaded CSV
        ├── pipeline.py      the LangGraph graph (sample datasets)
        ├── analysis.py      the ML engine: clean → FLAML → SHAP → EDA → charts → verdict
        ├── llm.py           pluggable LLM layer (mock + real, per-role, temperature)
        ├── sandbox.py       RestrictedPython + E2B microVM executor
        ├── rag.py           ChromaDB + MiniLM retrieval (Coder grounding)
        ├── web_search.py    live web research (DuckDuckGo / Tavily)
        └── schemas.py       request models
```

---

## 7. How to run it

**Backend:**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
# create .env.local with:  NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev          # → http://localhost:3000  (Studio at /studio)
```

With no backend running, the Studio falls back to a built-in simulation, so the
UI always works. `docker compose up --build` runs both halves at once.

---

## 8. Deployment

| Half | Hosted on | Notes |
|------|-----------|-------|
| **Frontend** (Next.js Studio) | **Vercel** | Set `NEXT_PUBLIC_API_URL` to the backend Space URL. |
| **Backend** (FastAPI + ML) | **Hugging Face Spaces** (Docker) | Free 16 GB RAM — enough for FLAML + SHAP. Sleeps when idle (first request ~30–60s to wake). |

See `DEPLOY.md` for full instructions. **Status: complete and deployed** — the
entire product experience, the 9-agent architecture, real ML (FLAML + SHAP),
the sandbox, RAG, live research, and the full dashboard, running end-to-end.
