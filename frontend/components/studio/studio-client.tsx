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
  ArrowDown,
  RotateCcw,
  Upload,
  FileSpreadsheet,
  Loader2,
  Check,
  X,
  Download,
  CornerDownLeft,
  Sparkles,
  Eye,
  EyeOff,
  Globe,
  BarChart3,
  Gauge,
  FileText,
  Network,
} from "lucide-react";
import { AGENTS, type AgentId, type Agent } from "@/lib/agents";
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
import {
  Donut,
  Bars,
  DistBars,
  MetricTiles,
  Pie,
  MetricsBars,
  StatCards,
  Histogram,
  Radar,
  Scatter,
  SmartInsights,
  DataProfile,
  QualityGauge,
  BoxPlot,
  CumulativeArea,
  LineChart,
  ChartCard,
} from "@/components/studio/charts";
import { KnowledgeGraph3D } from "@/components/studio/knowledge-graph";
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

const CONTEXT_PRESETS = [
  "Finance",
  "Healthcare",
  "Retail",
  "HR",
  "Telecom",
  "E-commerce",
  "Marketing",
  "B2B",
  "B2C",
  "Manufacturing",
];

// the 5 LLM-driven agent roles
const LLM_ROLES = [
  { id: "planner", name: "Planner" },
  { id: "coder", name: "Coder" },
  { id: "critic", name: "Critic" },
  { id: "visualizer", name: "Visualizer" },
  { id: "reporter", name: "Reporter" },
  { id: "researcher", name: "Researcher" },
];
type RoleLLM = Record<string, { provider: string; model: string; apiKey: string }>;
const emptyRoleLLM = (): RoleLLM =>
  Object.fromEntries(LLM_ROLES.map((r) => [r.id, { provider: "", model: "", apiKey: "" }]));

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
  {
    id: "zai",
    label: "Z.ai (GLM)",
    models: ["glm-4.6", "glm-4.5", "glm-4.5-air", "glm-4.5-flash"],
  },
];

const initialStatuses = () =>
  Object.fromEntries(AGENTS.map((a) => [a.id, "queued"])) as Record<
    AgentId,
    StageStatus
  >;

const VERDICT_STYLE: Record<string, { color: string; ring: string; tag: string }> = {
  excellent: { color: "#9ae64a", ring: "rgba(154,230,74,0.30)", tag: "Excellent" },
  good: { color: "#25d7f0", ring: "rgba(37,215,240,0.30)", tag: "Good" },
  fair: { color: "#fbbf24", ring: "rgba(251,191,36,0.30)", tag: "Fair" },
  weak: { color: "#fb7185", ring: "rgba(251,113,133,0.30)", tag: "Weak signal" },
};

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
  const [tab, setTab] = useState<"pipeline" | "activity" | "results">("pipeline");
  const [liveResults, setLiveResults] = useState<RunResults | null>(null);
  const [runMode, setRunMode] = useState<"sim" | "live">(
    isLive() ? "live" : "sim",
  );
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState(PROVIDERS[0].models[0]);
  const [apiKey, setApiKey] = useState("");
  const [e2bKey, setE2bKey] = useState("");
  const [contextTags, setContextTags] = useState<string[]>([]);
  const [llmMode, setLlmMode] = useState<"single" | "perRole">("single");
  const [roleLLM, setRoleLLM] = useState<RoleLLM>(emptyRoleLLM);

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
      if (s.e2bKey) setE2bKey(s.e2bKey);
      if (s.llmMode) setLlmMode(s.llmMode);
      if (s.roleLLM) setRoleLLM({ ...emptyRoleLLM(), ...s.roleLLM });
    } catch {
      /* ignore */
    }
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem(
        "helix_llm",
        JSON.stringify({ provider, model, apiKey, e2bKey, llmMode, roleLLM }),
      );
    } catch {
      /* ignore */
    }
  }, [provider, model, apiKey, e2bKey, llmMode, roleLLM]);

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
    setTab("pipeline");
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
    const buildLLMs = () => {
      const def = { provider, model, api_key: apiKey };
      if (llmMode === "single") return apiKey ? { default: def } : undefined;
      const out: Record<string, { provider: string; model?: string; api_key: string }> = {};
      if (apiKey) out.default = def;
      for (const role of LLM_ROLES) {
        const c = roleLLM[role.id];
        if (c?.apiKey)
          out[role.id] = {
            provider: c.provider || provider || "groq",
            model: c.model || undefined,
            api_key: c.apiKey,
          };
      }
      return Object.keys(out).length ? out : undefined;
    };
    const llm = { provider, model, apiKey, llms: buildLLMs() };
    const job =
      datasetId === "custom" && customFile
        ? streamAnalyze(
            customFile,
            { goal, target, task: taskType, ...llm, e2bKey, context: contextTags.join(", ") },
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

  // group the streamed log lines by agent for the transparent Pipeline view
  const logsByStage = logs.reduce<Record<string, LogLine[]>>((acc, l) => {
    (acc[l.stage] ||= []).push(l);
    return acc;
  }, {});
  const pipeCtx = {
    goal,
    dataset: ds.name,
    rows: ds.rows,
    cols: ds.cols,
    target: datasetId === "custom" ? target || "(auto-detect)" : ds.target,
    task: datasetId === "custom" ? taskType : ds.task,
    provider: apiKey ? `${provider} · ${model}` : "offline mock",
    sandbox: e2bKey ? "E2B microVM" : "RestrictedPython",
  };
  const criticFixes = (logsByStage["critic"] || []).filter((l) =>
    l.text.includes("patched the code"),
  ).length;

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
            e2bKey={e2bKey}
            contextTags={contextTags}
            llmMode={llmMode}
            roleLLM={roleLLM}
            dragging={dragging}
            setGoal={setGoal}
            setTarget={setTarget}
            setTaskType={setTaskType}
            changeProvider={changeProvider}
            setModel={setModel}
            setApiKey={setApiKey}
            setE2bKey={setE2bKey}
            setContextTags={setContextTags}
            setLlmMode={setLlmMode}
            setRoleLLM={setRoleLLM}
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

                <PipelinePanel statuses={statuses} criticFixes={criticFixes} />
              </div>
            </div>

            {/* right: activity / results */}
            <div className="lg:col-span-8">
              <div className="mb-4 flex items-center gap-2">
                <TabBtn active={tab === "pipeline"} onClick={() => setTab("pipeline")}>
                  Pipeline
                </TabBtn>
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

              <AnimatePresence initial={false}>
                {tab === "pipeline" ? (
                  <motion.div
                    key="pipeline"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <PipelineFlow
                      statuses={statuses}
                      logsByStage={logsByStage}
                      results={phase === "done" ? liveResults ?? ds.results : liveResults}
                      ctx={pipeCtx}
                      phase={phase}
                    />
                  </motion.div>
                ) : tab === "activity" ? (
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
  e2bKey,
  contextTags,
  llmMode,
  roleLLM,
  dragging,
  setGoal,
  setTarget,
  setTaskType,
  changeProvider,
  setModel,
  setApiKey,
  setE2bKey,
  setContextTags,
  setLlmMode,
  setRoleLLM,
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
  e2bKey: string;
  contextTags: string[];
  llmMode: "single" | "perRole";
  roleLLM: RoleLLM;
  dragging: boolean;
  setGoal: (v: string) => void;
  setTarget: (v: string) => void;
  setTaskType: (v: string) => void;
  changeProvider: (v: string) => void;
  setModel: (v: string) => void;
  setApiKey: (v: string) => void;
  setE2bKey: (v: string) => void;
  setContextTags: (v: string[]) => void;
  setLlmMode: (v: "single" | "perRole") => void;
  setRoleLLM: (v: RoleLLM) => void;
  selectDataset: (id: string) => void;
  onRun: () => void;
  onDrop: (e: DragEvent) => void;
  setDragging: (v: boolean) => void;
  fileInput: RefObject<HTMLInputElement | null>;
  onFile: (f: File | undefined) => void;
}) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [showE2bKey, setShowE2bKey] = useState(false);
  const [showRoleKeys, setShowRoleKeys] = useState(false);
  const [ctxInput, setCtxInput] = useState("");
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

        {/* dataset context tags → feed the Researcher */}
        <div className="mt-3 rounded-2xl border border-white/10 bg-panel p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              Dataset context
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-mute">
              optional · feeds the Researcher
            </span>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-white/10 bg-ink/70 px-2.5 py-2">
            {contextTags.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1.5 rounded-lg border border-brand/40 bg-brand/10 px-2.5 py-1 text-xs text-brand"
              >
                {t}
                <button
                  type="button"
                  onClick={() => setContextTags(contextTags.filter((x) => x !== t))}
                  aria-label={`remove ${t}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            <input
              value={ctxInput}
              onChange={(e) => setCtxInput(e.target.value)}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === ",") && ctxInput.trim()) {
                  e.preventDefault();
                  const t = ctxInput.trim().replace(/,+$/, "");
                  if (t && !contextTags.includes(t)) setContextTags([...contextTags, t]);
                  setCtxInput("");
                } else if (e.key === "Backspace" && !ctxInput && contextTags.length) {
                  setContextTags(contextTags.slice(0, -1));
                }
              }}
              placeholder={
                contextTags.length ? "add another…" : "e.g. telecom · B2C · monthly billing · churn"
              }
              className="min-w-[150px] flex-1 bg-transparent text-sm text-mist outline-none placeholder:text-mute"
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {CONTEXT_PRESETS.filter((p) => !contextTags.includes(p)).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setContextTags([...contextTags, p])}
                className="rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-xs text-mute transition-colors hover:border-brand/40 hover:text-mist"
              >
                + {p}
              </button>
            ))}
          </div>
          <p className="mt-2 font-mono text-[10px] leading-relaxed text-mute">
            Describe your data&apos;s domain/business so the{" "}
            <span className="text-acid">Researcher</span> agent can pull relevant real-world context
            from the live web.
          </p>
        </div>
      </div>

      {/* step 3 — AI engine */}
      <div className="mt-10">
        <div className="flex flex-wrap items-center gap-3">
          <span className="grid h-7 w-7 place-items-center rounded-full border border-white/15 bg-white/5 font-mono text-xs text-brand">
            3
          </span>
          <h2 className="text-lg font-semibold text-white">AI engine</h2>
          <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-mute">
            optional
          </span>
          <div className="ml-auto flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1">
            <button
              type="button"
              onClick={() => setLlmMode("single")}
              className={cn(
                "rounded-full px-3 py-1 text-xs transition-colors",
                llmMode === "single" ? "bg-brand/15 text-brand" : "text-mute hover:text-mist",
              )}
            >
              One model
            </button>
            <button
              type="button"
              onClick={() => setLlmMode("perRole")}
              className={cn(
                "rounded-full px-3 py-1 text-xs transition-colors",
                llmMode === "perRole" ? "bg-brand/15 text-brand" : "text-mute hover:text-mist",
              )}
            >
              Per-agent
            </button>
          </div>
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
            <div className="relative mt-2">
              <input
                type={showApiKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="paste key (or leave blank)"
                className="w-full rounded-lg border border-white/10 bg-ink/70 px-3 py-2 pr-10 text-sm text-mist outline-none focus:border-brand/50"
              />
              <button
                type="button"
                onClick={() => setShowApiKey((v) => !v)}
                aria-label={showApiKey ? "Hide API key" : "Show API key"}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-mute transition-colors hover:text-mist"
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>
        </div>
        <p className="mt-2 font-mono text-[10px] leading-relaxed text-mute">
          {llmMode === "perRole"
            ? "Default — used by any agent you don't override below. "
            : "Key stored only in your browser. Blank = offline mock (real ML, mock narration). "}
          The ML model itself is auto-selected by <span className="text-mist">FLAML</span>.
        </p>

        {llmMode === "perRole" && (
          <div className="mt-3 rounded-2xl border border-white/10 bg-panel p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
                Per-agent models · use a different LLM per role
              </span>
              <button
                type="button"
                onClick={() => setShowRoleKeys(!showRoleKeys)}
                className="font-mono text-[10px] text-mute transition-colors hover:text-mist"
              >
                {showRoleKeys ? "hide keys" : "show keys"}
              </button>
            </div>
            <div className="space-y-2">
              {LLM_ROLES.map((role) => {
                const c = roleLLM[role.id];
                const models =
                  PROVIDERS.find((p) => p.id === (c.provider || provider))?.models ?? [];
                const set = (patch: Partial<{ provider: string; model: string; apiKey: string }>) =>
                  setRoleLLM({ ...roleLLM, [role.id]: { ...c, ...patch } });
                return (
                  <div key={role.id} className="rounded-lg border border-white/10 bg-white/[0.02] p-2.5">
                    <div className="mb-1.5 text-xs font-medium text-mist">{role.name}</div>
                    <div className="grid gap-2 sm:grid-cols-3">
                      <select
                        value={c.provider}
                        onChange={(e) => set({ provider: e.target.value })}
                        className="rounded-lg border border-white/10 bg-ink/70 px-2.5 py-1.5 text-xs text-mist outline-none focus:border-brand/50"
                      >
                        <option value="" className="bg-ink text-mist">
                          use default
                        </option>
                        {PROVIDERS.map((p) => (
                          <option key={p.id} value={p.id} className="bg-ink text-mist">
                            {p.label}
                          </option>
                        ))}
                      </select>
                      <input
                        list={`m-${role.id}`}
                        value={c.model}
                        onChange={(e) => set({ model: e.target.value })}
                        placeholder="model"
                        className="rounded-lg border border-white/10 bg-ink/70 px-2.5 py-1.5 text-xs text-mist outline-none focus:border-brand/50"
                      />
                      <datalist id={`m-${role.id}`}>
                        {models.map((m) => (
                          <option key={m} value={m} />
                        ))}
                      </datalist>
                      <input
                        type={showRoleKeys ? "text" : "password"}
                        value={c.apiKey}
                        onChange={(e) => set({ apiKey: e.target.value })}
                        placeholder="key (or default)"
                        className="rounded-lg border border-white/10 bg-ink/70 px-2.5 py-1.5 text-xs text-mist outline-none focus:border-brand/50"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="mt-2 font-mono text-[10px] leading-relaxed text-mute">
              Leave a row blank to use the default above. Mix providers freely — e.g. a coder model
              for the Coder, a cheaper one for the Reporter.
            </p>
          </div>
        )}

        <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              Secure execution · E2B microVM key
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-mute">
              optional
            </span>
          </div>
          <div className="relative mt-2">
            <input
              type={showE2bKey ? "text" : "password"}
              value={e2bKey}
              onChange={(e) => setE2bKey(e.target.value)}
              placeholder="e2b_… (blank = RestrictedPython sandbox)"
              className="w-full rounded-lg border border-white/10 bg-ink/70 px-3 py-2 pr-10 text-sm text-mist outline-none focus:border-brand/50"
            />
            <button
              type="button"
              onClick={() => setShowE2bKey((v) => !v)}
              aria-label={showE2bKey ? "Hide key" : "Show key"}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-mute transition-colors hover:text-mist"
            >
              {showE2bKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className="mt-2 font-mono text-[10px] leading-relaxed text-mute">
            With a key, agent-generated code runs in an isolated{" "}
            <span className="text-mist">E2B microVM</span> (true VM isolation + hard
            timeout). Blank = in-process RestrictedPython. Stored only in your browser ·
            free key at <span className="text-mist">e2b.dev</span>.
          </p>
        </div>
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
  criticFixes,
}: {
  statuses: Record<AgentId, StageStatus>;
  criticFixes: number;
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
                {a.id === "critic" &&
                  statuses.critic === "done" &&
                  (criticFixes > 0 ? (
                    <span className="rounded-full bg-gold/15 px-1.5 py-0.5 font-mono text-[9px] text-gold">
                      {criticFixes} fix{criticFixes > 1 ? "es" : ""}
                    </span>
                  ) : (
                    <span className="rounded-full bg-white/5 px-1.5 py-0.5 font-mono text-[9px] text-mute">
                      no fixes
                    </span>
                  ))}
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

/* --------------------------- Pipeline view --------------------------- */
const STAGE_IO: Record<AgentId, { in: string; out: string }> = {
  planner: { in: "Goal + dataset schema", out: "Step-by-step analysis plan" },
  coder: { in: "Plan + retrieved DS docs (RAG)", out: "Executable Python" },
  executor: { in: "Generated code + your data", out: "Sandbox stdout + cleaning" },
  critic: { in: "Traceback from a failure", out: "Patched code → retry" },
  automl: { in: "Cleaned, encoded features", out: "Best model + metrics" },
  explainer: { in: "Trained model", out: "SHAP feature attributions" },
  visualizer: { in: "Findings + column profile + context", out: "Best-fit charts (type + table + note)" },
  researcher: { in: "Goal + context + drivers", out: "Live web research synthesis" },
  reporter: { in: "Metrics + drivers + insights + research", out: "Business narrative" },
};

function StatusBadge({ status, accent }: { status: StageStatus; accent: string }) {
  if (status === "active")
    return (
      <span
        className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-[9px]"
        style={{ color: accent, background: alpha(accent, 0.14) }}
      >
        <Loader2 className="h-3 w-3 animate-spin" /> running
      </span>
    );
  if (status === "done")
    return (
      <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-acid/15 px-2 py-0.5 font-mono text-[9px] text-acid">
        <Check className="h-3 w-3" /> done
      </span>
    );
  if (status === "error")
    return (
      <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-coral/15 px-2 py-0.5 font-mono text-[9px] text-coral">
        <X className="h-3 w-3" /> error
      </span>
    );
  return (
    <span className="shrink-0 rounded-full bg-white/5 px-2 py-0.5 font-mono text-[9px] text-mute">
      queued
    </span>
  );
}

function StageCard({
  agent,
  status,
  logs,
  io,
  index,
}: {
  agent: Agent;
  status: StageStatus;
  logs: LogLine[];
  io: { in: string; out: string };
  index: number;
}) {
  const accent = agent.accent;
  const active = status === "active";
  const done = status === "done";
  const queued = status === "queued";
  const Icon = agent.icon;
  return (
    <div className="relative pl-16">
      {index < AGENTS.length - 1 && (
        <div className="absolute bottom-[-12px] left-[31px] top-14 w-px bg-white/10">
          <motion.div
            className="w-full"
            style={{ background: `linear-gradient(${accent}, ${alpha(accent, 0.1)})` }}
            initial={{ height: 0 }}
            animate={{ height: done ? "100%" : "0%" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        </div>
      )}
      <span
        className="absolute left-2 top-2 grid h-12 w-12 place-items-center rounded-xl border"
        style={{
          borderColor: alpha(accent, queued ? 0.15 : 0.5),
          background: alpha(accent, queued ? 0.04 : 0.14),
        }}
      >
        <Icon className="h-5 w-5" style={{ color: queued ? "#76859f" : accent }} />
        {active && (
          <span
            className="absolute inset-0 rounded-xl"
            style={{ boxShadow: `0 0 22px -2px ${alpha(accent, 0.9)}` }}
          />
        )}
      </span>
      <div
        className={cn(
          "rounded-2xl border bg-panel p-4",
          active ? "border-white/25" : "border-white/10",
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2">
              <span className="font-mono text-[9px] text-mute">
                {index + 1}/{AGENTS.length}
              </span>
              <span className="text-sm font-semibold text-white">{agent.name}</span>
              <span className="truncate font-mono text-[10px] text-mute">{agent.tech}</span>
            </div>
            <div className="text-xs text-mute">{agent.role}</div>
          </div>
          <StatusBadge status={status} accent={accent} />
        </div>

        <div className="mt-3 flex items-start gap-2">
          <span
            className="shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider"
            style={{ color: accent, background: alpha(accent, 0.14) }}
          >
            in
          </span>
          <span className="text-[12px] text-mist">{io.in}</span>
        </div>
        <ArrowDown className="my-1 ml-1.5 h-3 w-3 text-mute" />
        <div className="flex items-start gap-2">
          <span
            className="shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider"
            style={{ color: accent, background: alpha(accent, 0.14) }}
          >
            out
          </span>
          <span className="text-[12px] text-mute">{io.out}</span>
        </div>

        {logs.length > 0 ? (
          <div className="scroll-thin mt-2 max-h-44 overflow-auto rounded-lg border border-white/10 bg-[#06080f] p-3 font-mono text-[11.5px] leading-relaxed">
            {logs.map((l) => (
              <div key={l.id} className={cn("whitespace-pre-wrap", LOG_COLOR[l.kind])}>
                {l.text}
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-2 rounded-lg border border-dashed border-white/10 p-3 text-[11px] text-mute">
            {queued ? "waiting for the upstream stage…" : active ? "working…" : "—"}
          </div>
        )}
      </div>
    </div>
  );
}

function PipelineFlow({
  statuses,
  logsByStage,
  results,
  ctx,
  phase,
}: {
  statuses: Record<AgentId, StageStatus>;
  logsByStage: Record<string, LogLine[]>;
  results: RunResults | null;
  ctx: {
    goal: string;
    dataset: string;
    rows: number;
    cols: number;
    target: string;
    task: string;
    provider: string;
    sandbox: string;
  };
  phase: Phase;
}) {
  const inChips: [string, string][] = [
    ["dataset", ctx.dataset],
    ["size", ctx.rows ? `${fmt(ctx.rows)} × ${ctx.cols}` : `${ctx.cols} cols`],
    ["goal", ctx.goal],
    ["target", ctx.target],
    ["task", ctx.task],
    ["AI engine", ctx.provider],
    ["sandbox", ctx.sandbox],
  ];
  return (
    <div className="space-y-3">
      <div
        className="rounded-2xl border p-4"
        style={{ borderColor: alpha("#8b5cf6", 0.3), background: alpha("#8b5cf6", 0.05) }}
      >
        <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
          <Upload className="h-3.5 w-3.5" /> Input
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {inChips.map(([k, v]) => (
            <span key={k} className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-mute">{k}: </span>
              <span className="text-mist">{v}</span>
            </span>
          ))}
        </div>
      </div>

      {AGENTS.map((a, i) => (
        <StageCard
          key={a.id}
          agent={a}
          status={statuses[a.id]}
          logs={logsByStage[a.id] || []}
          io={STAGE_IO[a.id]}
          index={i}
        />
      ))}

      {results && phase === "done" && (
        <div
          className="rounded-2xl border p-4"
          style={{ borderColor: alpha("#9ae64a", 0.3), background: alpha("#9ae64a", 0.05) }}
        >
          <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
            <Check className="h-3.5 w-3.5 text-acid" /> Final output
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1">
              <span className="font-mono text-[10px] uppercase text-mute">model: </span>
              <span className="text-mist">{results.bestModel}</span>
            </span>
            <span className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1">
              <span className="font-mono text-[10px] uppercase text-mute">
                {results.headline.label}:{" "}
              </span>
              <span className="text-mist">{results.headline.value}</span>
            </span>
            {results.bars.slice(0, 3).map((b) => (
              <span key={b.label} className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1">
                <span className="font-mono text-[10px] uppercase text-mute">driver: </span>
                <span className="text-mist">{b.label}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
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
  const [researchOn, setResearchOn] = useState(true);
  const rows = r._rows ?? ds.rows;
  const srcRows = r._source_rows;
  const tgt = r._target ?? ds.target;
  const hasCharts = !!(r._charts && r._charts.length);
  const meta: [string, string][] = [];
  if (rows)
    meta.push([
      "rows × cols",
      srcRows && srcRows !== rows
        ? `${fmt(srcRows)} → ${fmt(rows)} sampled × ${r._cols ?? ds.cols}`
        : `${fmt(rows)} × ${r._cols ?? ds.cols}`,
    ]);
  meta.push(["task", r.taskLabel]);
  if (tgt && tgt !== "(unsupervised)") meta.push(["target", tgt]);
  if (r._features?.length) meta.push(["features used", String(r._features.length)]);

  // auto-generated headline insights
  const topSeg = r.dist.length
    ? r.dist.reduce((a, b) => (b.value > a.value ? b : a), r.dist[0])
    : null;
  const findings: { label: string; value: string }[] = [
    { label: "Best model", value: `${r.bestModel} · ${r.headline.value} ${r.headline.label}` },
  ];
  if (r.bars[0])
    findings.push({
      label: "Strongest driver",
      value: `${r.bars[0].label} — ${(r.bars[0].sign ?? 1) >= 0 ? "raises" : "lowers"} ${tgt}`,
    });
  if (topSeg) findings.push({ label: "Key segment", value: `${topSeg.label} · ${topSeg.display}` });
  if (r._corr && r._corr[0])
    findings.push({
      label: "Top correlation",
      value: `${r._corr[0].a} ~ ${r._corr[0].b}  (r=${r._corr[0].r})`,
    });
  const balance = r._stats?.find((s) => s.label === "Class balance" || s.label.startsWith("Avg "));
  if (balance) findings.push({ label: balance.label, value: balance.value });

  const showResearch = researchOn && !!r._research;
  const reportParas = researchOn ? r.report : r._report_base ?? r.report;
  const rec = researchOn ? r.recommendation : r._recommendation_base ?? r.recommendation;

  const verdict = r._verdict;
  const vs = verdict ? VERDICT_STYLE[verdict.level] ?? VERDICT_STYLE.fair : null;

  return (
    <div className="space-y-4">
      {/* model-quality verdict — frames the result honestly (esp. weak signal) */}
      {verdict && vs && (
        <div
          className="flex items-start gap-3 rounded-2xl border p-4"
          style={{ borderColor: vs.ring, background: alpha(vs.color, 0.06) }}
        >
          <span
            className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg"
            style={{ background: alpha(vs.color, 0.16), color: vs.color }}
          >
            <Gauge className="h-4.5 w-4.5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-white">Model quality · {verdict.label}</span>
              <span
                className="rounded-full px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider"
                style={{ color: vs.color, background: alpha(vs.color, 0.14) }}
              >
                {vs.tag}
              </span>
            </div>
            <p className="mt-1 text-[13px] leading-relaxed text-mute">{verdict.detail}</p>
          </div>
        </div>
      )}

      {/* web research comparison toggle */}
      {r._research && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-acid/25 bg-acid/[0.04] p-4">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-acid" />
            <span className="text-sm text-mist">Web research influence</span>
            <span className="hidden font-mono text-[10px] text-mute sm:inline">
              compare the report with vs without the live research agent
            </span>
          </div>
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1">
            <button
              type="button"
              onClick={() => setResearchOn(true)}
              className={cn(
                "rounded-full px-3 py-1 text-xs transition-colors",
                researchOn ? "bg-acid/15 text-acid" : "text-mute hover:text-mist",
              )}
            >
              On
            </button>
            <button
              type="button"
              onClick={() => setResearchOn(false)}
              className={cn(
                "rounded-full px-3 py-1 text-xs transition-colors",
                !researchOn ? "bg-white/10 text-white" : "text-mute hover:text-mist",
              )}
            >
              Off
            </button>
          </div>
        </div>
      )}

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
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-mute">
                Model performance · held-out test set
              </div>
              <MetricTiles metrics={r.metrics} />
            </div>
          </div>
        </div>
      </div>

      {/* key findings */}
      {findings.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-panel p-6">
          <h3 className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Key findings
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {findings.map((f, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3"
              >
                <span
                  className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                  style={{ background: ds.accent }}
                />
                <div className="min-w-0">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-mute">
                    {f.label}
                  </div>
                  <div className="text-sm text-mist">{f.value}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* smart insights — auto-generated */}
      {r._insights_text && r._insights_text.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-panel p-6">
          <div className="mb-4 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand" />
            <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
              Smart insights · auto-detected
            </h3>
          </div>
          <SmartInsights items={r._insights_text} />
        </div>
      )}

      {/* key statistics */}
      {r._stats && r._stats.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-panel p-6">
          <h3 className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Key statistics
          </h3>
          <StatCards stats={r._stats} />
        </div>
      )}

      {/* data quality + data dictionary */}
      {(r._quality || (r._profile && r._profile.length > 0)) && (
        <div className="grid gap-4 lg:grid-cols-2">
          {r._quality && (
            <div className="rounded-2xl border border-white/10 bg-panel p-6">
              <h3 className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-mute">
                Data quality
              </h3>
              <QualityGauge quality={r._quality} />
            </div>
          )}
          {r._profile && r._profile.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-panel p-6">
              <h3 className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-mute">
                Data dictionary · {r._profile.length} columns
              </h3>
              <DataProfile profile={r._profile} />
            </div>
          )}
        </div>
      )}

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

      {/* recommended charts — LLM-chosen, context-aware, each with table + note */}
      {hasCharts && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <BarChart3 className="h-4 w-4 text-brand" />
            <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
              Recommended charts · chosen for this dataset
            </h3>
            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-mute">
              {r._charts!.length} · chart + data table + note
            </span>
          </div>
          <div className="space-y-5">
            {r._charts!.map((c) => (
              <ChartCard key={c.id} card={c} accent={ds.accent} />
            ))}
          </div>
        </div>
      )}

      {/* fixed chart grid — fallback when no recommended charts (mock / sample / no key) */}
      {!hasCharts && (
        <>
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

      {/* more insights: metric-comparison bars + distribution pie */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Model performance · metric comparison
          </h3>
          <div className="mt-5">
            <MetricsBars metrics={r.metrics} accent={ds.accent} />
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            {r.distTitle} · share
          </h3>
          <div className="mt-5">
            <Pie
              items={r.dist.map((d) => ({ label: d.label, value: d.value }))}
              accent={ds.accent}
            />
          </div>
        </div>
      </div>

      {/* radar + histogram */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Feature importance · radar
          </h3>
          <div className="mt-4">
            <Radar bars={r.bars} accent={ds.accent} />
          </div>
        </div>
        {r._hist && (
          <div className="rounded-2xl border border-white/10 bg-panel p-5">
            <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
              {r._hist.feature} · distribution (histogram)
            </h3>
            <div className="mt-5">
              <Histogram bins={r._hist.bins} accent={ds.accent} />
            </div>
          </div>
        )}
      </div>

      {/* line charts: distribution trend + cumulative importance (always shown) */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            {r.distTitle} · line trend
          </h3>
          <div className="mt-4">
            <LineChart items={r.dist} accent={ds.accent} />
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Cumulative importance · Pareto (line)
          </h3>
          <div className="mt-4">
            <CumulativeArea bars={r.bars} accent={ds.accent} />
          </div>
        </div>
      </div>

      {/* box plot */}
      {r._box && r._box.boxes.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            {r._box.feature} · box plot{r._box.boxes.length > 1 ? ` by ${tgt}` : ""}
          </h3>
          <div className="mt-5">
            <BoxPlot data={r._box} accent={ds.accent} />
          </div>
        </div>
      )}

      {/* scatter */}
      {r._scatter && r._scatter.points.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-panel p-5">
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            {r._scatter.x} vs {r._scatter.y} · scatter (coloured by {tgt})
          </h3>
          <div className="mx-auto mt-4 max-w-lg">
            <Scatter data={r._scatter} />
          </div>
        </div>
      )}
        </>
      )}

      {/* knowledge graph — the whole analysis as one interactive map */}
      <div className="rounded-2xl border border-white/10 bg-panel p-5 sm:p-6">
        <div className="mb-4 flex items-center gap-2">
          <Network className="h-4 w-4 text-brand" />
          <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
            Knowledge graph · the whole analysis, mapped
          </h3>
        </div>
        <KnowledgeGraph3D results={r} accent={ds.accent} />
      </div>

      {/* research & domain context — live web */}
      {showResearch && r._research && (r._research.synthesis || r._research.hits.length > 0) && (
        <div className="rounded-2xl border border-white/10 bg-panel p-6">
          <div className="mb-3 flex items-center gap-2">
            <Globe className="h-4 w-4 text-acid" />
            <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
              Research &amp; domain context · live web
            </h3>
          </div>
          {r._research.synthesis && (
            <p className="text-sm leading-relaxed text-mist">{r._research.synthesis}</p>
          )}
          {r._research.hits.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="font-mono text-[10px] uppercase tracking-wider text-mute">
                Sources · {r._research.hits.length}
              </div>
              {r._research.hits.map((h, i) => (
                <a
                  key={i}
                  href={h.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-xl border border-white/10 bg-white/[0.03] p-3 transition-colors hover:border-acid/40"
                >
                  <div className="truncate text-sm text-mist">{h.title || h.url}</div>
                  {h.snippet && (
                    <div className="mt-0.5 line-clamp-2 text-xs text-mute">{h.snippet}</div>
                  )}
                  <div className="mt-1 truncate font-mono text-[10px] text-acid/70">{h.url}</div>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {/* business report — premium, scannable layout */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-panel">
        {/* header band */}
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-6 py-4"
          style={{ background: `linear-gradient(90deg, ${alpha(ds.accent, 0.1)}, transparent)` }}
        >
          <div className="flex items-center gap-2.5">
            <span
              className="grid h-8 w-8 place-items-center rounded-lg"
              style={{ background: alpha(ds.accent, 0.16), color: ds.accent }}
            >
              <FileText className="h-4.5 w-4.5" />
            </span>
            <div>
              <h3 className="text-sm font-semibold text-white">Business report</h3>
              <div className="font-mono text-[10px] uppercase tracking-wider text-mute">
                executive findings &amp; actions
              </div>
            </div>
            {r._research && (
              <span
                className={cn(
                  "ml-1 rounded-full px-2 py-0.5 font-mono text-[9px]",
                  researchOn ? "bg-acid/15 text-acid" : "bg-white/5 text-mute",
                )}
              >
                {researchOn ? "research-enriched" : "data-only"}
              </span>
            )}
          </div>
          <Button variant="secondary" size="sm" onClick={onDownload}>
            <Download className="h-4 w-4" />
            Download
          </Button>
        </div>

        {/* report meta strip */}
        <div className="flex flex-wrap gap-2 border-b border-white/10 px-6 py-3">
          {[
            ["model", r.bestModel],
            [r.headline.label, r.headline.value],
            ...(verdict ? [["quality", verdict.label] as [string, string]] : []),
            ["trained on", `${fmt(rows)}${srcRows && srcRows !== rows ? ` / ${fmt(srcRows)}` : ""} rows`],
          ].map(([k, v]) => (
            <span key={k} className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-mute">{k}: </span>
              <span className="text-xs text-mist">{v}</span>
            </span>
          ))}
        </div>

        {/* narrative */}
        <div className="px-6 py-5">
          {reportParas.length > 0 && (
            <p
              className="border-l-2 pl-4 text-[15px] leading-relaxed text-white"
              style={{ borderColor: ds.accent }}
            >
              {reportParas[0]}
            </p>
          )}
          <div className="mt-4 space-y-3.5">
            {reportParas.slice(1).map((p, i) => (
              <div key={i} className="flex gap-3">
                <span
                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: alpha(ds.accent, 0.7) }}
                />
                <p className="max-w-prose text-[13.5px] leading-relaxed text-mist">{p}</p>
              </div>
            ))}
          </div>

          {/* recommendation callout */}
          <div
            className="mt-6 flex items-start gap-3 rounded-xl border p-4"
            style={{ borderColor: alpha(ds.accent, 0.35), background: alpha(ds.accent, 0.07) }}
          >
            <span
              className="grid h-7 w-7 shrink-0 place-items-center rounded-lg"
              style={{ background: alpha(ds.accent, 0.16), color: ds.accent }}
            >
              <ArrowRight className="h-4 w-4" />
            </span>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-mute">
                Recommendation
              </div>
              <p className="mt-1 text-sm font-medium leading-relaxed text-white">{rec}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
