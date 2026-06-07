import {
  Brain,
  Code,
  Terminal,
  Wrench,
  Sparkles,
  ScanSearch,
  Globe,
  FileText,
  type LucideIcon,
} from "lucide-react";

export type AgentId =
  | "planner"
  | "coder"
  | "executor"
  | "critic"
  | "automl"
  | "explainer"
  | "researcher"
  | "reporter";

export interface Agent {
  id: AgentId;
  index: number;
  name: string;
  role: string;
  tech: string;
  blurb: string;
  detail: string;
  icon: LucideIcon;
  /** 6-digit hex; used inline for glows, strokes, gradients. */
  accent: string;
}

/**
 * The seven-stage autonomous pipeline. Single source of truth for the
 * landing-page workflow graph and the live Studio visualization.
 */
export const AGENTS: Agent[] = [
  {
    id: "planner",
    index: 0,
    name: "Planner",
    role: "Decomposes the goal",
    tech: "DeepSeek-Coder · CoT",
    blurb: "Turns a plain-English objective into a step-by-step analysis plan.",
    detail:
      "Uses chain-of-thought prompting to break an objective like “predict churn” into an ordered workflow: load → EDA → clean → encode → train → evaluate → explain.",
    icon: Brain,
    accent: "#8b5cf6",
  },
  {
    id: "coder",
    index: 1,
    name: "Coder",
    role: "Writes the Python",
    tech: "DeepSeek-Coder",
    blurb: "Generates executable Python for each step of the plan.",
    detail:
      "Produces pandas / scikit-learn code for cleaning, feature engineering, EDA and model training — grounded in retrieved library docs (RAG).",
    icon: Code,
    accent: "#25d7f0",
  },
  {
    id: "executor",
    index: 2,
    name: "Executor",
    role: "Runs it safely",
    tech: "E2B microVM · RestrictedPython",
    blurb: "Executes generated code in an isolated, locked-down sandbox.",
    detail:
      "Runs each cell in a hardened sandbox — an E2B microVM when configured, otherwise an in-process RestrictedPython jail with file-system and network access blocked — capturing stdout and full tracebacks for the Critic.",
    icon: Terminal,
    accent: "#38bdf8",
  },
  {
    id: "critic",
    index: 3,
    name: "Critic",
    role: "Self-heals errors",
    tech: "Traceback analysis · max 5 retries",
    blurb: "Reads tracebacks, rewrites the broken code, and retries.",
    detail:
      "The self-correction loop: on failure it diagnoses the traceback, patches the code (e.g. strips column whitespace on a KeyError) and re-executes — up to five attempts.",
    icon: Wrench,
    accent: "#fbbf24",
  },
  {
    id: "automl",
    index: 4,
    name: "AutoML",
    role: "Finds the best model",
    tech: "FLAML",
    blurb: "Searches models & hyper-parameters to maximise the metric.",
    detail:
      "FLAML automatically benchmarks candidate estimators under a time budget and returns the best-performing, tuned model.",
    icon: Sparkles,
    accent: "#9ae64a",
  },
  {
    id: "explainer",
    index: 5,
    name: "Explainer",
    role: "Explains the why",
    tech: "SHAP",
    blurb: "Quantifies what drives each prediction.",
    detail:
      "Computes SHAP values to rank global feature importance and explain individual predictions in human terms.",
    icon: ScanSearch,
    accent: "#e879f9",
  },
  {
    id: "researcher",
    index: 6,
    name: "Researcher",
    role: "Researches the web",
    tech: "Live web search",
    blurb: "Pulls real-world domain context from the live web.",
    detail:
      "Searches the live web for benchmarks, industry knowledge and best practices tied to the goal, dataset context and the model's drivers — grounding the report in the real world.",
    icon: Globe,
    accent: "#34d399",
  },
  {
    id: "reporter",
    index: 7,
    name: "Reporter",
    role: "Writes the story",
    tech: "Mistral-7B",
    blurb: "Composes a business-friendly narrative with charts.",
    detail:
      "Synthesises metrics, drivers and visuals into an executive summary with clear, actionable recommendations.",
    icon: FileText,
    accent: "#fb7185",
  },
];

export const agentById = (id: AgentId): Agent =>
  AGENTS.find((a) => a.id === id)!;
