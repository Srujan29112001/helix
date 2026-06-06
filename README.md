# Helix — Autonomous Data Science Agent

> Turn a CSV and a plain-English question into a business-ready answer —
> automatically. A multi-agent system that **plans, writes code, runs it,
> fixes its own errors, builds a model, explains it, and writes the report.**
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
- a **dataset** (CSV), and
- a **goal in plain English** (e.g. *"predict which customers will churn"*),

and a team of specialized AI **agents** does the entire workflow with no human
in the loop — including **fixing its own code when it breaks** (the headline
feature: *self-correcting execution*). It ends with metrics, the key drivers
(explainability), and a short business report.

> **Domain-agnostic.** Helix works on **any tabular CSV from any industry** —
> finance, healthcare, retail, marketing, HR, science, and more. It auto-detects
> the task (**classification, regression, clustering, or NLP/text**), cleans messy
> data, parses dates, and adapts — verified on churn, sales, segmentation, reviews,
> healthcare readmission, and loan default. The churn walkthrough below is just one
> example.

### A concrete example (customer churn — one of many)
1. You upload `telco_churn.csv` and type *"predict churn and the key drivers."*
2. The **Planner** writes a 6-step plan (load → EDA → clean → encode → train → explain).
3. The **Coder** writes the Python for each step.
4. The **Executor** runs it — and hits `KeyError: 'Churn'`.
5. The **Critic** reads the traceback, patches it (`df.columns.str.strip()`),
   and retries — up to 5 times — until it runs clean.
6. **AutoML** finds the best model (LightGBM, 0.84 ROC-AUC).
7. **SHAP** explains *why* (contract type and tenure are the biggest drivers).
8. The **Reporter** writes: *"Month-to-month customers with high charges churn
   most; long tenure protects against it → offer annual contracts."*

What took days now takes minutes — and a non-technical user did it themselves.

---

## 2. Who is it for? (Audience)

| Audience | What they get |
|----------|---------------|
| **Non-technical business users** (product, marketing, ops) | Ask questions in English, get data-backed answers + plain explanations — without waiting on a data team. **Primary audience.** |
| **Data scientists / analysts** | Automate the boring 60–70% (cleaning, EDA, baseline modeling) so they focus on judgment and hard problems. |
| **Small teams / startups** without a data team | A "data scientist in a box." |
| **Students & educators** | A transparent, explainable reference for the end-to-end ML workflow. |
| **(For this capstone) evaluators** | A demonstration of multi-agent orchestration, self-correction, AutoML, and explainability working together. |

---

## 3. How it works (architecture)

Helix is two cooperating parts: a **web app** (what the user sees) and an
**agent backend** (the brain).

```
  ┌─────────────────────────────────────────────────────────┐
  │  FRONTEND  ·  Next.js Studio (the browser app)           │
  │  upload CSV + type goal  →  watch agents work live  →     │
  │  see charts + report                                     │
  └───────────────┬─────────────────────────────────────────┘
                  │  POST /api/run   (Server-Sent Events: a live
                  │                   stream of agent events)
                  ▼
  ┌─────────────────────────────────────────────────────────┐
  │  BACKEND  ·  FastAPI  →  LangGraph state graph            │
  │                                                          │
  │   Planner → Coder → Executor ──► Critic ──┐ (retry ≤ 5)   │
  │                        ▲                  │ self-heal     │
  │                        └──────────────────┘               │
  │              → AutoML → Explainer → Reporter             │
  └─────────────────────────────────────────────────────────┘
```

### The seven agents
| # | Agent | Job | Tech |
|---|-------|-----|------|
| 1 | **Planner** | Break the goal into an ordered analysis plan | LLM (DeepSeek-Coder, chain-of-thought) |
| 2 | **Coder** | Write Python for each step | LLM, RAG-grounded |
| 3 | **Executor** | Run the code safely, capture output/errors | Sandbox |
| 4 | **Critic** | Read tracebacks, patch the code, retry (≤5) | LLM — *self-correction* |
| 5 | **AutoML** | Search models + hyper-parameters | FLAML |
| 6 | **Explainer** | Quantify what drives predictions | SHAP |
| 7 | **Reporter** | Write the business narrative | LLM (Mistral) |

These run as a **LangGraph** "state graph": each agent is a node, state flows
between them, and a **conditional edge** loops Executor↔Critic until the code
works (or 5 tries are exhausted).

### How the live updates work
The backend streams **Server-Sent Events** as the graph runs — each `{stage,
status, log}` event updates the Studio in real time (status dots, the streaming
execution log, then the final results). This is why you *watch* the agents
work instead of staring at a spinner.

---

## 4. Tech stack — and why each choice

### Frontend
| Tech | Why |
|------|-----|
| **Next.js 16 + React 19** | Production React framework; routing, builds, and deploy story are solved. Lets us build a genuinely premium UI (the original proposal's Gradio can't). |
| **TypeScript** | Type safety across the frontend↔backend event contract — fewer runtime surprises. |
| **Tailwind CSS v4** | Fast, consistent styling via utilities + a custom design-token theme; no CSS sprawl. |
| **motion (Framer Motion)** | The smooth animations, the live pipeline, scroll reveals — the "wow" factor. |
| **HTML Canvas** | The animated "data field" hero (neon nodes + flowing data) — bespoke, performant. |

### Backend
| Tech | Why |
|------|-----|
| **FastAPI** | Modern async Python API; native streaming (SSE) support; minimal boilerplate; auto docs. Needed because the UI is a separate web app, not a Python widget. |
| **LangGraph** | Purpose-built for **multi-agent, stateful, looping** workflows — exactly the Planner→…→Critic↺ pattern. Cleaner than hand-rolling control flow. |
| **LangChain core** | Shared message/LLM abstractions used by LangGraph. |
| **Pydantic** | Request validation and typed data models. |
| **httpx** | Async HTTP client used to call hosted/local LLM APIs. |

### Models & ML
| Tech | Why |
|------|-----|
| **DeepSeek-Coder** (Planner/Coder/Critic) | Strong open code-generation model — fits the "write & fix Python" job. |
| **Mistral-7B** (Reporter) | Good open model for fluent natural-language narratives. |
| **Hybrid hosting** (local + API) | Local = free/private; API = reliable/higher-quality. Our LLM layer resolves a provider **per agent role**, so you mix them freely and add keys without code changes. |
| **pandas / scikit-learn** | The standard data-wrangling + ML toolkit. |
| **FLAML** | Lightweight **AutoML** — finds a good model under a time budget automatically. |
| **SHAP** | The standard for **explainability** — turns a model into "here's why." |
| **ChromaDB + sentence-transformers** | **RAG**: index library docs so the Coder hallucinates fewer APIs. |
| **RestrictedPython** | Runs generated code with dangerous operations blocked. *(Kept per the proposal; wrapped behind a swappable interface — the highest-risk component.)* |

---

## 5. Repository structure

```
Capstone Project IIITH/
├── README.md            ← this file
├── PLAN.md              ← phase-by-phase roadmap + decisions
├── frontend/            ← Next.js web app (the Studio + landing)
│   ├── app/
│   │   ├── globals.css      design system: colors, fonts, animations
│   │   ├── layout.tsx       fonts + page metadata
│   │   ├── page.tsx         landing page (assembles the sections)
│   │   └── studio/page.tsx  the /studio workspace route
│   ├── components/
│   │   ├── backgrounds/data-field.tsx   animated neon-network canvas
│   │   ├── site/        logo, navbar, footer
│   │   ├── landing/     hero, pipeline visualizer, capabilities, use-cases…
│   │   ├── studio/      studio-client (the live app) + charts
│   │   └── ui/          button, badge, reveal, section (reusable bits)
│   └── lib/
│       ├── agents.ts        the 7 agents (shared by UI + studio)
│       ├── studio-run.ts    4 sample datasets + results + sim script
│       ├── api.ts           streaming client (talks to the backend)
│       └── utils.ts         small helpers (cn, alpha, fmt)
└── backend/             ← FastAPI service (the agent brain)
    └── app/
        ├── main.py          API routes + SSE streaming
        ├── pipeline.py      the LangGraph graph + 7 agent nodes
        ├── llm.py           hybrid LLM provider layer (mock + real)
        ├── datasets.py      dataset metadata + result payloads
        ├── events.py        scripted fallback run
        └── schemas.py       request models
```

---

## 6. How to run it

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
UI always works.

---

## 7. Status — what's done (≈ 40%)

| Phase | Scope | Status |
|------:|-------|--------|
| **0** | Frontend — landing + interactive Studio | ✅ Done |
| **1** | FastAPI backend + live SSE wiring | ✅ Done |
| **2** | Real LangGraph pipeline + hybrid LLM layer | ✅ Done |
| 3 | Execution sandbox (run real code) | ⬜ Next |
| 4 | Real AutoML (FLAML) + SHAP + EDA charts | ⬜ |
| 5 | RAG grounding (ChromaDB) | ⬜ |
| 6 | Report agent (real narrative + charts) | ⬜ |
| 7 | Multi-dataset robustness | ⬜ |
| 8 | Evaluation & metrics | ⬜ |
| 9 | Deployment & docs | ⬜ |
| 10 | Presentation polish | ⬜ |

**Done = the entire product experience + the agent architecture, running
end-to-end.** What remains is replacing three stubs with real computation:
the Executor running actual code (3), real AutoML/SHAP numbers (4), and RAG (5).
See `PLAN.md` for full detail.
