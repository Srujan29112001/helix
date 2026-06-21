import type { AgentId } from "@/lib/agents";
import type { RunResults, StageStatus, LogKind } from "@/lib/studio-run";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

/** Whether a backend is configured. When false, the Studio simulates locally. */
export const isLive = () => API_URL.length > 0;

export interface LLMConfig {
  provider?: string;
  model?: string;
  apiKey?: string;
  temperature?: number;
  /** optional per-role config: { default: {...}, coder: {provider, model, api_key, temperature}, ... } */
  llms?: Record<string, { provider?: string; model?: string; api_key?: string; temperature?: number }>;
}

export interface RunRequest extends LLMConfig {
  datasetId: string;
  goal: string;
  fileName?: string | null;
}

export interface AnalyzeRequest extends LLMConfig {
  goal: string;
  target: string;
  task?: string;
  e2bKey?: string;
  context?: string;
}

interface ServerEvent {
  stage: AgentId;
  status?: StageStatus | null;
  log?: { text: string; kind?: LogKind } | null;
}

type ServerMsg =
  | { t: "start"; dataset: string }
  | ({ t: "event" } & ServerEvent)
  | { t: "result"; results: RunResults }
  | { t: "done" };

export interface StreamHandlers {
  onEvent: (e: ServerEvent) => void;
  onResult: (r: RunResults) => void;
  onDone: () => void;
}

/** Reads a fetch Response as a Server-Sent Events stream and dispatches handlers. */
async function consumeSSE(res: Response, handlers: StreamHandlers): Promise<void> {
  if (!res.ok || !res.body) throw new Error(`request failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      let msg: ServerMsg;
      try {
        msg = JSON.parse(payload) as ServerMsg;
      } catch {
        continue;
      }
      if (msg.t === "event") handlers.onEvent(msg);
      else if (msg.t === "result") handlers.onResult(msg.results);
      else if (msg.t === "done") handlers.onDone();
    }
  }
}

/** Run a sample dataset (scripted/LLM pipeline) and stream events. */
export async function streamRun(
  req: RunRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  await consumeSSE(res, handlers);
}

/** Upload a real CSV and stream a genuine analysis (FLAML + SHAP). */
export async function streamAnalyze(
  file: File,
  req: AnalyzeRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  form.append("target", req.target);
  form.append("goal", req.goal);
  form.append("task", req.task ?? "auto");
  form.append("provider", req.provider ?? "groq");
  form.append("model", req.model ?? "");
  form.append("apiKey", req.apiKey ?? "");
  form.append("e2bKey", req.e2bKey ?? "");
  form.append("context", req.context ?? "");
  form.append("llms", req.llms ? JSON.stringify(req.llms) : "");
  form.append("temperature", String(req.temperature ?? 0.2));
  const res = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    body: form,
    signal,
  });
  await consumeSSE(res, handlers);
}
