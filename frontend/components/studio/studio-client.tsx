"use client";

import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type ReactNode,
  type RefObject,
} from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowRight,
  RotateCcw,
  Upload,
  FileSpreadsheet,
  Loader2,
  Check,
  X,
  Download,
  CornerDownLeft,
  Sparkles,
} from "lucide-react";
import { AGENTS, type AgentId } from "@/lib/agents";
import {
  DATASETS,
  datasetById,
  buildEvents,
  type Dataset,
  type StageStatus,
  type LogKind,
  type RunResults,
} from "@/lib/studio-run";
import { isLive, streamRun, streamAnalyze, type StreamHandlers } from "@/lib/api";
import { Donut, Bars, DistBars, MetricTiles } from "@/components/studio/charts";
import { Logo } from "@/components/site/logo";
import { Button } from "@/components/ui/button";
import { alpha, cn, fmt } from "@/lib/utils";

type Phase = "setup" | "running" | "done";
interface LogLine {
  id: number;
  stage: AgentId;
  text: string;
  kind: LogKind;
}

const GOAL_CHIPS = [
  "Find the key drivers and explain why.",
  "Build the most accurate model you can.",
  "Summarize the data and surface anything surprising.",
];

// Sample datasets span industries — the real path is "upload your own".
const INDUSTRY: Record<string, string> = {
  loan: "Finance",
  sales: "Retail",
  segments: "Marketing",
  reviews: "E-commerce",
};

interface Column {
  name: string;
  type: string;
}

// Lightweight client-side type inference from a sample of rows.
function inferType(vals: string[]): string {
  if (!vals.length) return "empty";
  if (vals.every((v) => v !== "" && !Number.isNaN(Number(v)))) return "number";
  if (
    vals.every((v) =>
      /^\d{4}[-/]\d{1,2}[-/]\d{1,2}|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}/.test(v),
    )
  )
    return "date";
  const uniq = new Set(vals).size;
  if (uniq <= Math.min(12, Math.max(2, Math.floor(vals.length / 2))))
    return "category";
  return "text";
}

const PROVIDERS: { id: string; label: string; models: string[] }[] = [
  {
    id: "groq",
    label: "Groq — free, fast",
    models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "deepseek-r1-distill-llama-70b"],
  },
  { id: "openai", label: "OpenAI", models: ["gpt-4o-mini", "gpt-4o"] },
  { id: "deepseek", label: "DeepSeek", models: ["deepseek-chat", "deepseek-coder"] },
  {
    id: "anthropic",
    label: "Anthropic (Claude)",
    models: ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"],
  },
  {
    id: "mistral",
    label: "Mistral",
    models: ["mistral-small-latest", "mistral-large-latest", "open-mistral-7b"],
  },
  {
    id: "openrouter",
    label: "OpenRouter — any model",
    models: [
      "deepseek/deepseek-chat",
      "anthropic/claude-3.5-sonnet",
      "openai/gpt-4o-mini",
      "meta-llama/llama-3.3-70b-instruct",
    ],
  },
  { id: "gemini", label: "Google Gemini — free", models: ["gemini-2.0-flash", "gemini-1.5-flash"] },
];

const initialStatuses = () =>
  Object.fromEntries(AGENTS.map((a) => [a.id, "queued"])) as Record<
    AgentId,
    StageStatus
  >;

const LOG_COLOR: Record<LogKind, string> = {
  info: "text-mist",
  code: "text-mist/75",
  ok: "text-acid",
  err: "text-coral",
  warn: "text-gold",
  muted: "text-mute",
};

export function StudioClient() {
  const [phase, setPhase] = useState<Phase>("setup");
  const [datasetId, setDatasetId] = useState(DATASETS[0].id);
  const [goal, setGoal] = useState(DATASETS[0].goal);
  const [custom, setCustom] = useState<{ name: string } | null>(null);
  const [customFile, setCustomFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [schema, setSchema] = useState<Column[]>([]);
  const [target, setTarget] = useState("");
  const [taskType, setTaskType] = useState("auto");
  const [dragging, setDragging] = useState(false);
  const [statuses, setStatuses] = useState<Record<AgentId, StageStatus>>(
    initialStatuses,
  );
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [tab, setTab] = useState<"activity" | "results">("activity");
  const [liveResults, setLiveResults] = useState<RunResults | null>(null);
  const [runMode, setRunMode] = useState<"sim" | "live">(
    isLive() ? "live" : "sim",
  );
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState(PROVIDERS[0].models[0]);
  const [apiKey, setApiKey] = useState("");

  const timers = useRef<number[]>([]);
  const logId = useRef(0);
  const logBox = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const ds: Dataset =
    datasetId === "custom" && custom
      ? { ...DATASETS[0], id: "custom", name: custom.name, file: custom.name, rows: 0, cols: columns.length, goal }
      : datasetById(datasetId);

  const clearTimers = () => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
  };
  useEffect(
    () => () => {
      clearTimers();
      abortRef.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (logBox.current) logBox.current.scrollTop = logBox.current.scrollHeight;
  }, [logs]);

  // persist the AI config in the browser
  useEffect(() => {
    try {
      const s = JSON.parse(localStorage.getItem("helix_llm") || "{}");
      if (s.provider) setProvider(s.provider);
      if (s.model) setModel(s.model);
      if (s.apiKey) setApiKey(s.apiKey);
    } catch {
      /* ignore */
    }
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem("helix_llm", JSON.stringify({ provider, model, apiKey }));
    } catch {
      /* ignore */
    }
  }, [provider, model, apiKey]);

  const changeProvider = (p: string) => {
    setProvider(p);
    const prov = PROVIDERS.find((x) => x.id === p);
    if (prov) setModel(prov.models[0]);
  };

  const selectDataset = (id: string) => {
    setDatasetId(id);
    setGoal(datasetById(id).goal);
    setCustom(null);
    setCustomFile(null);
    setColumns([]);
    setSchema([]);
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    setCustomFile(file);
    setCustom({ name: file.name });
    setDatasetId("custom");
    try {
      const text = await file.text();
      const lines = text.split(/\r?\n/).filter((l) => l.trim());
      const header = (lines[0] ?? "")
        .split(",")
        .map((c) => c.trim().replace(/^"|"$/g, ""))
        .filter(Boolean);
      const sampleRows = lines.slice(1, 31).map((l) => l.split(","));
      const detected: Column[] = header.map((name, i) => ({
        name,
        type: inferType(
          sampleRows.map((r) => (r[i] ?? "").trim()).filter(Boolean),
        ),
      }));
      setColumns(header);
      setSchema(detected);
      if (header.length) {
        const t = header[header.length - 1];
        setTarget(t);
        setGoal(`Analyze "${t}" and explain the key drivers.`);
      }
    } catch {
      /* ignore parse errors */
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    onFile(e.dataTransfer.files?.[0]);
  };

  const appendLog = (stage: AgentId, text: string, kind: LogKind) =>
    setLogs((l) => [...l, { id: logId.current++, stage, text, kind }]);

  const simulate = () => {
    let acc = 0;
    for (const ev of buildEvents(ds)) {
      acc += ev.delay;
      timers.current.push(
        window.setTimeout(() => {
          if (ev.status)
            setStatuses((s) => ({ ...s, [ev.stage]: ev.status! }));
          if (ev.log) appendLog(ev.stage, ev.log.text, ev.log.kind ?? "info");
        }, acc),
      );
    }
    timers.current.push(
      window.setTimeout(() => {
        setPhase("done");
        setTab("results");
      }, acc + 700),
    );
  };

  const run = () => {
    clearTimers();
    abortRef.current?.abort();
    setStatuses(initialStatuses());
    setLogs([]);
    setLiveResults(null);
    setTab("activity");
    setPhase("running");

    if (!isLive()) {
      setRunMode("sim");
      simulate();
      return;
    }

    setRunMode("live");
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const handlers: StreamHandlers = {
      onEvent: (e) => {
        if (e.status) setStatuses((s) => ({ ...s, [e.stage]: e.status! }));
        if (e.log) appendLog(e.stage, e.log.text, e.log.kind ?? "info");
      },
      onResult: (r) => setLiveResults(r),
      onDone: () => {
        setPhase("done");
        setTab("results");
      },
    };
    const llm = { provider, model, apiKey };
    const job =
      datasetId === "custom" && customFile
        ? streamAnalyze(
            customFile,
            { goal, target, task: taskType, ...llm },
            handlers,
            ctrl.signal,
          )
        : streamRun(
            { datasetId, goal, fileName: custom?.name ?? null, ...llm },
            handlers,
            ctrl.signal,
          );
    job.catch(() => {
      setRunMode("sim");
      appendLog("planner", "(api unreachable — running simulated preview)", "warn");
      simulate();
    });
  };

  const reset = () => {
    clearTimers();
    abortRef.current?.abort();
    setPhase("setup");
    setStatuses(initialStatuses());
    setLogs([]);
    setLiveResults(null);
  };

  const downloadReport = () => {
    const r = liveResults ?? ds.results;
    const text = [
      `HELIX — Analysis Report`,
      `Dataset: ${ds.name} (${ds.file})`,
      `Goal: ${goal}`,
      `Task: ${r.taskLabel}   Best model: ${r.bestModel}`,
      ``,
      `Metrics: ${r.metrics.map((m) => `${m.label} ${m.value}`).join("  ·  ")}`,
      ``,
      `Summary:`,
      ...r.report.map((p) => `  ${p}`),
      ``,
      `Recommendation:`,
      `  ${r.recommendation}`,
      ``,
      `(Simulated preview — generated by the Helix Studio UI.)`,
    ].join("\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `helix-report-${ds.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const doneCount = AGENTS.filter((a) => statuses[a.id] === "done").length;
  const progress = Math.round((doneCount / AGENTS.length) * 100);

  return (
    <div className="min-h-screen">
      {/* top bar */}
      <header className="sticky top-0 z-40 border-b border-white/10 bg-ink/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3 sm:px-8">
          <div className="flex items-center gap-4">
            <Link href="/" aria-label="Helix home">
              <Logo />
            </Link>
            <span className="hidden h-5 w-px bg-white/10 sm:block" />
            <span className="hidden font-mono text-xs uppercase tracking-[0.18em] text-mute sm:block">
              Studio
            </span>
          </div>
          <div className="flex items-center gap-3">
            {runMode === "live" ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-acid/30 bg-acid/10 px-3 py-1 font-mono text-[10px] text-acid">
                <span className="h-1.5 w-1.5 animate-glow rounded-full bg-acid" />
                live · api
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-gold/30 bg-gold/10 px-3 py-1 font-mono text-[10px] text-gold">
                <span className="h-1.5 w-1.5 animate-glow rounded-full bg-gold" />
                simulated preview
              </span>
            )}
            {phase !== "setup" && (
              <Button variant="secondary" size="sm" onClick={reset}>
                <RotateCcw className="h-4 w-4" />
                New analysis
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
        {phase === "setup" ? (
          <Setup
            ds={ds}
            datasetId={datasetId}
            goal={goal}
            custom={custom}
            columns={columns}
            schema={schema}
            target={target}
            taskType={taskType}
            provider={provider}
            model={model}
            apiKey={apiKey}
            dragging={dragging}
            setGoal={setGoal}
            setTarget={setTarget}
            setTaskType={setTaskType}
            changeProvider={changeProvider}
            setModel={setModel}
            setApiKey={setApiKey}
            selectDataset={selectDataset}
            onRun={run}
            onDrop={onDrop}
            setDragging={setDragging}
            fileInput={fileInput}
            onFile={onFile}
          />
        ) : (
          <div className="grid gap-6 lg:grid-cols-12">
            {/* left: input + pipeline */}
            <div className="lg:col-span-4">
              <div className="lg:sticky lg:top-24 space-y-4">
                <div className="rounded-2xl border border-white/10 bg-panel p-4">
                  <div className="flex items-center gap-2.5">
                    <span
                      className="grid h-9 w-9 place-items-center rounded-lg border"
                      style={{
                        borderColor: alpha(ds.accent, 0.35),
                        background: alpha(ds.accent, 0.12),
                      }}
                    >
                      <ds.icon className="h-4.5 w-4.5" style={{ color: ds.accent }} />
                    </span>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-white">
                        {ds.name}
                      </div>
                      <div className="font-mono text-[11px] text-mute">
                        {ds.rows ? `${fmt(ds.rows)} × ${ds.cols}` : `${ds.cols} columns`}
                      </div>
                    </div>
                  </div>
                  <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-mute">
                    {goal}
                  </p>
                  <div className="mt-3">
                    <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-mute">
                      <span>progress</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-brand to-grape"
                        animate={{ width: `${progress}%` }}
                        transition={{ ease: "easeOut" }}
                      />
                    </div>
                  </div>
                </div>

                <PipelinePanel statuses={statuses} />
              </div>
            </div>

            {/* right: activity / results */}
            <div className="lg:col-span-8">
              <div className="mb-4 flex items-center gap-2">
                <TabBtn active={tab === "activity"} onClick={() => setTab("activity")}>
                  Activity
                </TabBtn>
                <TabBtn
                  active={tab === "results"}
                  disabled={phase !== "done"}
                  onClick={() => phase === "done" && setTab("results")}
                >
                  Results
                  {phase === "done" && (
                    <span className="ml-1.5 h-1.5 w-1.5 rounded-full bg-acid" />
                  )}
                </TabBtn>
              </div>

              <AnimatePresence mode="wait">
                {tab === "activity" ? (
                  <motion.div
                    key="activity"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#06080f]">
                      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-coral/70" />
                        <span className="h-2.5 w-2.5 rounded-full bg-gold/70" />
                        <span className="h-2.5 w-2.5 rounded-full bg-acid/70" />
                        <span className="ml-2 font-mono text-[11px] text-mute">
                          helix · execution log
                        </span>
                      </div>
                      <div
                        ref={logBox}
                        className="scroll-thin h-[460px] overflow-y-auto p-4 font-mono text-[12.5px] leading-relaxed"
                      >
                        {logs.length === 0 && (
                          <div className="text-mute">initializing run…</div>
                        )}
                        {logs.map((l) => (
                          <motion.div
                            key={l.id}
                            initial={{ opacity: 0, x: -6 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.2 }}
                            className="flex gap-2.5"
                          >
                            <span
                              className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                              style={{ background: agentAccent(l.stage) }}
                            />
                            <span className={cn("whitespace-pre-wrap", LOG_COLOR[l.kind])}>
                              {l.text}
                            </span>
                          </motion.div>
                        ))}
                        {phase === "running" && (
                          <span className="ml-4 inline-block h-3.5 w-2 animate-blink bg-brand align-middle" />
                        )}
                      </div>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    key="results"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                  >
                    <Results
                      ds={ds}
                      results={liveResults ?? ds.results}
                      onDownload={downloadReport}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function agentAccent(id: AgentId): string {
  return AGENTS.find((a) => a.id === id)?.accent ?? "#76859f";
}

/* ------------------------------- Setup ------------------------------- */
function Setup({
  ds,
  datasetId,
  goal,
  custom,
  columns,
  schema,
  target,
  taskType,
  provider,
  model,
  apiKey,
  dragging,
  setGoal,
  setTarget,
  setTaskType,
  changeProvider,
  setModel,
  setApiKey,
  selectDataset,
  onRun,
  onDrop,
  setDragging,
  fileInput,
  onFile,
}: {
  ds: Dataset;
  datasetId: string;
  goal: string;
  custom: { name: string } | null;
  columns: string[];
  schema: Column[];
  target: string;
  taskType: string;
  provider: string;
  model: string;
  apiKey: string;
  dragging: boolean;
  setGoal: (v: string) => void;
  setTarget: (v: string) => void;
  setTaskType: (v: string) => void;
  changeProvider: (v: string) => void;
  setModel: (v: string) => void;
  setApiKey: (v: string) => void;
  selectDataset: (id: string) => void;
  onRun: () => void;
  onDrop: (e: DragEvent) => void;
  setDragging: (v: boolean) => void;
  fileInput: RefObject<HTMLInputElement | null>;
  onFile: (f: File | undefined) => void;
}) {
  const needsTarget =
    datasetId === "custom" && taskType !== "clustering" && !target;
  const disabled = !goal.trim() || needsTarget;
  const hint = needsTarget
    ? "Pick a target column to continue"
    : !goal.trim()
      ? "Describe your goal to continue"
      : apiKey
        ? `Ready · ${provider} · ${model}`
        : "Ready · offline mock (add a key for real AI narration)";
  const models = PROVIDERS.find((p) => p.id === provider)?.models ?? [];
  return (
    <div className="mx-auto max-w-4xl">
      <div className="text-center">
        <h1 className="font-display text-3xl font-semibold text-white sm:text-4xl">
          New analysis
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-sm text-mute sm:text-base">
          Bring <span className="text-mist">any tabular dataset from any field</span> —
          classification, regression, clustering or text. Start from a sample or
          upload your own; the seven agents take it from there.
        </p>
      </div>

      {/* step 1 */}
      <div className="mt-10">
        <StepLabel n={1} title="Pick a sample — or upload your own" />
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {DATASETS.map((d) => {
            const active = datasetId === d.id;
            const Icon = d.icon;
            return (
              <button
                key={d.id}
                onClick={() => selectDataset(d.id)}
                className={cn(
                  "group flex items-start gap-3 rounded-2xl border p-4 text-left transition-all",
                  active
                    ? "border-white/25 bg-white/[0.06]"
                    : "border-white/10 bg-panel hover:border-white/20",
                )}
                style={
                  active
                    ? { boxShadow: `0 0 0 1px ${alpha(d.accent, 0.5)}, 0 0 30px -10px ${alpha(d.accent, 0.7)}` }
                    : undefined
                }
              >
                <span
                  className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border"
                  style={{
                    borderColor: alpha(d.accent, 0.35),
                    background: alpha(d.accent, 0.12),
                  }}
                >
                  <Icon className="h-5 w-5" style={{ color: d.accent }} />
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-white">
                      {d.name}
                    </span>
                  </div>
                  <div className="font-mono text-[11px] text-mute">
                    {INDUSTRY[d.id] ?? "Sample"} · {d.task} · {fmt(d.rows)} ×{" "}
                    {d.cols}
                  </div>
                </div>
              </button>
            );
          })}

          {/* upload */}
          <button
            onClick={() => fileInput.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={cn(
              "flex items-center gap-3 rounded-2xl border border-dashed p-4 text-left transition-all sm:col-span-2",
              dragging
                ? "border-brand/60 bg-brand/5"
                : datasetId === "custom"
                  ? "border-white/25 bg-white/[0.06]"
                  : "border-white/15 bg-white/[0.02] hover:border-white/30",
            )}
          >
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/15 bg-white/5">
              {datasetId === "custom" ? (
                <FileSpreadsheet className="h-5 w-5 text-brand" />
              ) : (
                <Upload className="h-5 w-5 text-mute" />
              )}
            </span>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-white">
                {custom ? custom.name : "Upload your own CSV"}
              </div>
              <div className="font-mono text-[11px] text-mute">
                {custom
                  ? "ready · real analysis (FLAML + SHAP)"
                  : "any domain — finance · healthcare · retail · HR · science"}
              </div>
            </div>
            <input
              ref={fileInput}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => onFile(e.target.files?.[0] ?? undefined)}
            />
          </button>
        </div>

        {datasetId === "custom" && columns.length > 0 && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-panel p-4">
              <label className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
                Target column · what to predict
              </label>
              <select
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="mt-2 w-full rounded-lg border border-white/10 bg-ink/70 px-3 py-2 text-sm text-mist outline-none focus:border-brand/50"
              >
                {columns.map((c) => (
                  <option key={c} value={c} className="bg-ink text-mist">
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div className="rounded-2xl border border-white/10 bg-panel p-4">
              <label className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
                Task type
              </label>
              <select
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                className="mt-2 w-full rounded-lg border border-white/10 bg-ink/70 px-3 py-2 text-sm text-mist outline-none focus:border-brand/50"
              >
                <option value="auto" className="bg-ink text-mist">
                  Auto-detect
                </option>
                <option value="classification" className="bg-ink text-mist">
                  Classification
                </option>
                <option value="regression" className="bg-ink text-mist">
                  Regression
                </option>
                <option value="clustering" className="bg-ink text-mist">
                  Clustering (no target)
                </option>
                <option value="nlp" className="bg-ink text-mist">
                  NLP / text
                </option>
              </select>
            </div>
          </div>
        )}

        {datasetId === "custom" && schema.length > 0 && (
          <div className="mt-3 rounded-2xl border border-white/10 bg-panel p-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
                Detected schema · {schema.length} columns
              </span>
              <span className="font-mono text-[10px] text-mute">
                how Helix read your file
              </span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {schema.map((c) => {
                const isTarget = c.name === target;
                return (
                  <span
                    key={c.name}
                    className={cn(
                      "rounded-lg border px-2.5 py-1 text-xs",
                      isTarget
                        ? "border-brand/50 bg-brand/10 text-brand"
                        : "border-white/10 bg-white/[0.03] text-mist",
                    )}
                  >
                    {c.name}
                    <span className="ml-1.5 font-mono text-[10px] text-mute">
                      {c.type}
                      {isTarget ? " · target" : ""}
                    </span>
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* step 2 */}
      <div className="mt-10">
        <StepLabel n={2} title="Describe your goal" />
        <div className="mt-4 rounded-2xl border border-white/10 bg-panel p-4">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            rows={3}
            placeholder="e.g. Predict the target and explain why · forecast a value · find segments · analyze text"
            className="w-full resize-none bg-transparent text-sm leading-relaxed text-mist outline-none placeholder:text-mute"
          />
          <div className="mt-3 flex flex-wrap gap-2 border-t border-white/5 pt-3">
            {GOAL_CHIPS.map((c) => (
              <button
                key={c}
                onClick={() => setGoal(c)}
                className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-mute transition-colors hover:border-brand/40 hover:text-mist"
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* step 3 — AI engine */}
      <div className="mt-10">
        <div className="flex items-center gap-3">
          <span className="grid h-7 w-7 place-items-center rounded-full border border-white/15 bg-white/5 font-mono text-xs text-brand">
            3
          </span>
          <h2 className="text-lg font-semibold text-white">AI engine</h2>
          <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-mute">
            optional
          </span>
        </div>
        <div className="mt-4 grid gap-3 rounded-2xl border border-white/10 bg-panel p-4 sm:grid-cols-3">
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              Provider
            </span>
            <select
              value={provider}
              onChange={(e) => changeProvider(e.target.value)}
              className="mt-2 w-full rounded-lg border border-white/10 bg-ink/70 px-3 py-2 text-sm text-mist outline-none focus:border-brand/50"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id} className="bg-ink text-mist">
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              Model
            </span>
            <input
              list="helix-models"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="model id"
              className="mt-2 w-full rounded-lg border border-white/10 bg-ink/70 px-3 py-2 text-sm text-mist outline-none focus:border-brand/50"
            />
            <datalist id="helix-models">
              {models.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          </label>
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              API key
            </span>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="paste key (or leave blank)"
              className="mt-2 w-full rounded-lg border border-white/10 bg-ink/70 px-3 py-2 text-sm text-mist outline-none focus:border-brand/50"
            />
          </label>
        </div>
        <p className="mt-2 font-mono text-[10px] leading-relaxed text-mute">
          Key stored only in your browser. Blank = offline mock (real ML, mock narration). The ML
          model itself is auto-selected by <span className="text-mist">FLAML</span>.
        </p>
      </div>

      {/* sticky, always-visible run bar */}
      <div className="sticky bottom-0 z-30 mt-10 rounded-t-2xl border-t border-white/10 bg-ink/85 py-4 backdrop-blur-xl">
        <div className="flex items-center justify-between gap-4">
          <p className="hidden font-mono text-[11px] text-mute sm:block">{hint}</p>
          <Button size="lg" onClick={onRun} disabled={disabled} className="ml-auto">
            <Sparkles className="h-4.5 w-4.5" />
            Run analysis
            <CornerDownLeft className="h-4 w-4 opacity-70" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function StepLabel({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-7 w-7 place-items-center rounded-full border border-white/15 bg-white/5 font-mono text-xs text-brand">
        {n}
      </span>
      <h2 className="text-lg font-semibold text-white">{title}</h2>
    </div>
  );
}

/* --------------------------- PipelinePanel --------------------------- */
function PipelinePanel({
  statuses,
}: {
  statuses: Record<AgentId, StageStatus>;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-panel p-2">
      {AGENTS.map((a, i) => {
        const st = statuses[a.id];
        const Icon = a.icon;
        const active = st === "active";
        const error = st === "error";
        return (
          <div
            key={a.id}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors",
              active && "bg-white/[0.05]",
            )}
          >
            <span
              className="relative grid h-9 w-9 shrink-0 place-items-center rounded-lg border"
              style={{
                borderColor:
                  st === "queued" ? "rgba(255,255,255,0.1)" : alpha(a.accent, 0.4),
                background:
                  st === "queued" ? "rgba(255,255,255,0.03)" : alpha(a.accent, 0.12),
              }}
            >
              <Icon
                className="h-4.5 w-4.5"
                style={{ color: st === "queued" ? "#76859f" : a.accent }}
              />
              {active && (
                <span
                  className="absolute inset-0 rounded-lg"
                  style={{ boxShadow: `0 0 18px -2px ${alpha(a.accent, 0.8)}` }}
                />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "text-sm font-medium",
                    st === "queued" ? "text-mute" : "text-white",
                  )}
                >
                  {a.name}
                </span>
                {a.id === "critic" && statuses.critic === "done" && (
                  <span className="rounded-full bg-gold/15 px-1.5 py-0.5 font-mono text-[9px] text-gold">
                    1 fix
                  </span>
                )}
              </div>
              <div className="truncate font-mono text-[10px] text-mute">
                {a.tech}
              </div>
            </div>
            <StatusIcon status={st} accent={a.accent} />
          </div>
        );
      })}
    </div>
  );
}

function StatusIcon({
  status,
  accent,
}: {
  status: StageStatus;
  accent: string;
}) {
  if (status === "active")
    return <Loader2 className="h-4 w-4 animate-spin" style={{ color: accent }} />;
  if (status === "done") return <Check className="h-4 w-4 text-acid" />;
  if (status === "error")
    return (
      <span className="grid h-4 w-4 place-items-center rounded-full bg-coral/20">
        <X className="h-3 w-3 text-coral" />
      </span>
    );
  return <span className="h-1.5 w-1.5 rounded-full bg-mute/40" />;
}

function TabBtn({
  active,
  disabled,
  onClick,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center rounded-full px-4 py-1.5 text-sm transition-colors",
        active
          ? "bg-white/10 text-white"
          : "text-mute hover:text-mist disabled:opacity-40 disabled:hover:text-mute",
      )}
    >
      {children}
    </button>
  );
}

/* ------------------------------ Results ------------------------------ */
function Results({
  ds,
  results,
  onDownload,
}: {
  ds: Dataset;
  results: RunResults;
  onDownload: () => void;
}) {
  const r = results;
  const rows = r._rows ?? ds.rows;
  const tgt = r._target ?? ds.target;
  const meta: [string, string][] = [];
  if (rows) meta.push(["rows × cols", `${fmt(rows)} × ${r._cols ?? ds.cols}`]);
  meta.push(["task", r.taskLabel]);
  if (tgt && tgt !== "(unsupervised)") meta.push(["target", tgt]);
  if (r._features?.length) meta.push(["features used", String(r._features.length)]);
  return (
    <div className="space-y-4">
      {/* headline */}
      <div className="rounded-2xl border border-white/10 bg-panel p-6">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
          <Donut
            fraction={r.headline.fraction}
            value={r.headline.value}
            label={r.headline.label}
            accent={ds.accent}
          />
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="rounded-full px-2.5 py-1 font-mono text-[11px]"
                style={{ color: ds.accent, background: alpha(ds.accent, 0.12) }}
              >
                {r.taskLabel}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[11px] text-mist">
                best · {r.bestModel}
              </span>
            </div>
            <div className="mt-4">
              <MetricTiles metrics={r.metrics} />
            </div>
          </div>
        </div>
      </div>

      {/* data processing — transparency on YOUR data */}
      <div className="rounded-2xl border border-white/10 bg-panel p-6">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Data processing
          </h3>
          <span className="font-mono text-[10px] text-mute">
            what Helix did to your data
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {meta.map(([label, value]) => (
            <span
              key={label}
              className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5"
            >
              <span className="font-mono text-[10px] uppercase tracking-wider text-mute">
                {label}:{" "}
              </span>
              <span className="text-sm text-mist">{value}</span>
            </span>
          ))}
        </div>
        {r._fixes && r._fixes.length > 0 ? (
          <div className="mt-5">
            <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-mute">
              steps applied · {r._fixes.length}
            </div>
            <ul className="space-y-1.5">
              {r._fixes.map((f, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-mist"
                >
                  <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-acid" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="mt-4 text-xs text-mute">
            Cleaning, encoding and feature steps stream live in the{" "}
            <span className="text-mist">Activity</span> tab.
          </p>
        )}
      </div>

      {/* bars + dist */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            {r.barsTitle}
          </h3>
          <div className="mt-5">
            <Bars bars={r.bars} accent={ds.accent} />
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            {r.distTitle}
          </h3>
          <div className="mt-5">
            <DistBars items={r.dist} accent={ds.accent} />
          </div>
        </div>
      </div>

      {/* report */}
      <div className="rounded-2xl border border-white/10 bg-panel p-6">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Business report
          </h3>
          <Button variant="secondary" size="sm" onClick={onDownload}>
            <Download className="h-4 w-4" />
            Download
          </Button>
        </div>
        <div className="mt-4 space-y-3">
          {r.report.map((p, i) => (
            <p key={i} className="text-sm leading-relaxed text-mist">
              {p}
            </p>
          ))}
        </div>
        <div
          className="mt-5 flex items-start gap-3 rounded-xl border p-4"
          style={{
            borderColor: alpha(ds.accent, 0.3),
            background: alpha(ds.accent, 0.06),
          }}
        >
          <ArrowRight
            className="mt-0.5 h-4 w-4 shrink-0"
            style={{ color: ds.accent }}
          />
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-mute">
              Recommendation
            </div>
            <p className="mt-1 text-sm leading-relaxed text-white">
              {r.recommendation}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
