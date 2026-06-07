import {
  Crosshair,
  TrendingUp,
  Boxes,
  MessageSquareText,
  type LucideIcon,
} from "lucide-react";
import type { AgentId } from "@/lib/agents";

export type StageStatus = "queued" | "active" | "done" | "error";

export type LogKind = "info" | "code" | "ok" | "err" | "warn" | "muted";

export interface RunEvent {
  /** ms to wait before applying this event (relative to previous). */
  delay: number;
  stage: AgentId;
  status?: StageStatus;
  log?: { text: string; kind?: LogKind };
}

export interface ResultBar {
  label: string;
  value: number; // magnitude 0..1
  sign?: 1 | -1; // direction (for SHAP-style); omit for neutral
}

export interface DistItem {
  label: string;
  value: number; // 0..1
  display: string;
}

export interface GraphNode {
  id: string;
  name: string;
  group: string; // "target" | "driver" | "segment"
  val: number;
  sign?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  value: number;
  kind: string; // "drives" | "corr" | "segment"
  sign?: number;
}

export interface RunResults {
  taskLabel: string;
  bestModel: string;
  headline: { fraction?: number; value: string; label: string };
  metrics: { label: string; value: string }[];
  barsTitle: string;
  bars: ResultBar[];
  distTitle: string;
  dist: DistItem[];
  report: string[];
  recommendation: string;
  // transparency: what the backend did to the data (present on real runs)
  _fixes?: string[];
  _features?: string[];
  _target?: string;
  _rows?: number;
  _cols?: number;
  _train_rows?: number;
  _test_rows?: number;
  _metric?: string;
  _corr?: { a: string; b: string; r: number }[];
  _hist?: { feature: string; bins: { label: string; count: number }[] } | null;
  _graph?: { nodes: GraphNode[]; links: GraphLink[] } | null;
  _stats?: { label: string; value: string }[];
  _scatter?: { x: string; y: string; points: { x: number; y: number; c: number }[] } | null;
  _profile?: { name: string; type: string; missing: number; unique: number }[];
  _quality?: { score: number; missing: number; duplicates: number; constant_cols: number } | null;
  _box?: {
    feature: string;
    boxes: { label: string; min: number; q1: number; med: number; q3: number; max: number }[];
  } | null;
  _insights_text?: { text: string; kind: string }[];
  _research?: {
    queries: string[];
    hits: { title: string; snippet: string; url: string }[];
    synthesis: string;
  } | null;
  _report_base?: string[];
  _recommendation_base?: string;
}

export interface Dataset {
  id: string;
  name: string;
  file: string;
  rows: number;
  cols: number;
  task: string;
  target: string;
  goal: string;
  accent: string;
  icon: LucideIcon;
  error: string;
  fix: string;
  results: RunResults;
}

export const DATASETS: Dataset[] = [
  {
    id: "loan",
    name: "Loan Default Risk",
    file: "loan_applications.csv",
    rows: 32581,
    cols: 12,
    task: "Binary classification",
    target: "default",
    goal: "Predict which loan applicants will default and identify the key risk factors.",
    accent: "#25d7f0",
    icon: Crosshair,
    error: "ValueError: could not convert string to float: 'RENT'",
    fix: "df = pd.get_dummies(df, columns=['home_ownership'])",
    results: {
      taskLabel: "Binary classification",
      bestModel: "LightGBM",
      headline: { fraction: 0.86, value: "0.86", label: "ROC-AUC" },
      metrics: [
        { label: "Accuracy", value: "0.84" },
        { label: "ROC-AUC", value: "0.86" },
        { label: "Precision", value: "0.79" },
        { label: "Recall", value: "0.66" },
        { label: "F1", value: "0.72" },
      ],
      barsTitle: "SHAP feature importance",
      bars: [
        { label: "Credit score", value: 0.94, sign: -1 },
        { label: "Debt-to-income", value: 0.81, sign: 1 },
        { label: "Loan amount", value: 0.62, sign: 1 },
        { label: "Annual income", value: 0.55, sign: -1 },
        { label: "Employment length", value: 0.38, sign: -1 },
        { label: "Interest rate", value: 0.3, sign: 1 },
      ],
      distTitle: "Default rate by credit band",
      dist: [
        { label: "Poor (<580)", value: 0.34, display: "34%" },
        { label: "Fair (580–669)", value: 0.17, display: "17%" },
        { label: "Good (670–739)", value: 0.08, display: "8%" },
        { label: "Excellent (740+)", value: 0.03, display: "3%" },
      ],
      report: [
        "Credit score is the single strongest predictor of default — applicants below 580 default at 34%, versus just 3% above 740. A high debt-to-income ratio sharply raises risk.",
        "Larger loan amounts and higher interest rates increase default probability, while higher income and longer employment history are protective.",
      ],
      recommendation:
        "Tighten approval for low-credit, high-DTI applicants and price interest rates to the modelled risk rather than flat tiers.",
    },
  },
  {
    id: "sales",
    name: "Rossmann Store Sales",
    file: "rossmann_sales.csv",
    rows: 1017209,
    cols: 18,
    task: "Regression",
    target: "Sales",
    goal: "Forecast daily sales for each store over the next six weeks.",
    accent: "#9ae64a",
    icon: TrendingUp,
    error: "ValueError: could not convert string to float: 'StateHoliday'",
    fix: "df['StateHoliday'] = df['StateHoliday'].astype('category').cat.codes",
    results: {
      taskLabel: "Regression",
      bestModel: "LightGBM Regressor",
      headline: { fraction: 0.93, value: "0.93", label: "R² score" },
      metrics: [
        { label: "R²", value: "0.93" },
        { label: "RMSPE", value: "8.4%" },
        { label: "MAE", value: "421" },
        { label: "RMSE", value: "612" },
      ],
      barsTitle: "Feature importance",
      bars: [
        { label: "Promo", value: 0.81, sign: 1 },
        { label: "Day of week", value: 0.55, sign: -1 },
        { label: "Competition dist.", value: 0.4, sign: -1 },
        { label: "Store type", value: 0.33, sign: 1 },
        { label: "School holiday", value: 0.18, sign: 1 },
      ],
      distTitle: "Average sales by day of week",
      dist: [
        { label: "Monday", value: 0.98, display: "9.7k" },
        { label: "Wednesday", value: 0.71, display: "7.0k" },
        { label: "Friday", value: 0.83, display: "8.2k" },
        { label: "Sunday", value: 0.12, display: "1.2k" },
      ],
      report: [
        "Running promotions is by far the largest driver of daily sales, lifting revenue materially whenever active. Sales peak on Mondays and dip sharply on Sundays when many stores are closed.",
        "Proximity to competition has a measurable negative effect, while certain store types consistently outperform. The model forecasts six weeks ahead with an 8.4% error.",
      ],
      recommendation:
        "Concentrate promotional spend on high-traffic weekdays and stores facing nearby competition, where the forecasted uplift is greatest.",
    },
  },
  {
    id: "segments",
    name: "Mall Customer Segmentation",
    file: "mall_customers.csv",
    rows: 200,
    cols: 5,
    task: "Clustering",
    target: "Segment",
    goal: "Group customers into meaningful segments by income and spending behavior.",
    accent: "#a78bfa",
    icon: Boxes,
    error: "ValueError: Input X contains NaN",
    fix: "X = StandardScaler().fit_transform(df.dropna())",
    results: {
      taskLabel: "Clustering",
      bestModel: "KMeans (k=4)",
      headline: { value: "4", label: "segments" },
      metrics: [
        { label: "Clusters", value: "4" },
        { label: "Silhouette", value: "0.55" },
        { label: "Features", value: "2" },
        { label: "Samples", value: "200" },
      ],
      barsTitle: "Defining dimensions",
      bars: [
        { label: "Spending score", value: 0.88 },
        { label: "Annual income", value: 0.79 },
        { label: "Age", value: 0.34 },
      ],
      distTitle: "Segment sizes",
      dist: [
        { label: "Premium (high $, high spend)", value: 0.18, display: "18%" },
        { label: "Careful (high $, low spend)", value: 0.22, display: "22%" },
        { label: "Budget (low $, low spend)", value: 0.35, display: "35%" },
        { label: "Impulsive (low $, high spend)", value: 0.25, display: "25%" },
      ],
      report: [
        "Four clear segments emerge along income and spending-score axes. The most valuable “Premium” group combines high income with high spending, while a sizeable “Careful” group earns well but spends little.",
        "The largest cluster is budget-conscious, and a notable “Impulsive” group spends beyond what their income would suggest.",
      ],
      recommendation:
        "Target the “Careful” high-income segment with premium offers to unlock latent spend, and use loyalty perks to retain the “Premium” group.",
    },
  },
  {
    id: "reviews",
    name: "Product Reviews",
    file: "reviews.csv",
    rows: 10000,
    cols: 3,
    task: "NLP + analytics",
    target: "Sentiment",
    goal: "Analyze sentiment and surface the top recurring themes in customer reviews.",
    accent: "#fb7185",
    icon: MessageSquareText,
    error: "LookupError: Resource punkt not found",
    fix: "nltk.download('punkt', quiet=True)",
    results: {
      taskLabel: "NLP + analytics",
      bestModel: "TF-IDF + Logistic Regression",
      headline: { fraction: 0.62, value: "62%", label: "positive" },
      metrics: [
        { label: "Reviews", value: "10k" },
        { label: "Positive", value: "62%" },
        { label: "Negative", value: "24%" },
        { label: "Neutral", value: "14%" },
      ],
      barsTitle: "Top themes by frequency",
      bars: [
        { label: "Delivery speed", value: 0.74 },
        { label: "Product quality", value: 0.66 },
        { label: "Price / value", value: 0.52 },
        { label: "Customer support", value: 0.39 },
        { label: "Packaging", value: 0.27 },
      ],
      distTitle: "Sentiment distribution",
      dist: [
        { label: "Positive", value: 0.62, display: "62%" },
        { label: "Neutral", value: 0.14, display: "14%" },
        { label: "Negative", value: 0.24, display: "24%" },
      ],
      report: [
        "Overall sentiment is positive, with 62% of reviews favorable. Delivery speed is the most-discussed theme and the leading source of negative sentiment, followed closely by product quality.",
        "Price and value are mentioned often and generally viewed favorably, while customer support, though less frequent, skews negative when raised.",
      ],
      recommendation:
        "Prioritize fixing delivery reliability — it is the top theme and the biggest driver of negative reviews — and amplify the positive price-value perception in marketing.",
    },
  },
];

export const datasetById = (id: string): Dataset =>
  DATASETS.find((d) => d.id === id) ?? DATASETS[0];

/** Build the scripted timeline of events for a simulated run. */
export function buildEvents(ds: Dataset): RunEvent[] {
  const r = ds.results;
  const isCluster = ds.task === "Clustering";
  const isNlp = ds.task === "NLP + analytics";
  const ev: RunEvent[] = [];
  const push = (
    delay: number,
    stage: AgentId,
    log?: { text: string; kind?: LogKind },
    status?: StageStatus,
  ) => ev.push({ delay, stage, log, status });

  // Planner
  push(200, "planner", undefined, "active");
  push(500, "planner", { text: `> objective: ${ds.goal}`, kind: "muted" });
  push(700, "planner", {
    text: `detected task → ${ds.task}  ·  target: ${ds.target}`,
    kind: "info",
  });
  push(500, "planner", { text: "drafting analysis plan…", kind: "muted" });
  [
    "1. load & validate dataset",
    "2. exploratory data analysis",
    "3. clean & impute missing values",
    isCluster ? "4. scale & select features" : "4. encode categorical features",
    isCluster ? "5. cluster & profile segments" : `5. train model on ${ds.target}`,
    isNlp ? "6. extract themes & sentiment" : "6. evaluate & explain",
  ].forEach((line, i) => push(260, "planner", { text: line, kind: "code" }));
  push(400, "planner", { text: "plan ready (6 steps)", kind: "ok" }, "done");

  // Coder
  push(300, "coder", undefined, "active");
  push(450, "coder", { text: "import pandas as pd", kind: "code" });
  push(350, "coder", {
    text: `df = pd.read_csv("${ds.file}")`,
    kind: "code",
  });
  push(400, "coder", {
    text: isNlp
      ? "X = TfidfVectorizer().fit_transform(df.text)"
      : `X = df.drop("${ds.target}", axis=1)`,
    kind: "code",
  });
  push(400, "coder", { text: "generated code for 6 steps", kind: "ok" }, "done");

  // Executor → error
  push(300, "executor", undefined, "active");
  push(450, "executor", {
    text: "▶ sandbox start  (fs: off · net: off)",
    kind: "muted",
  });
  push(500, "executor", {
    text: `loaded ${ds.rows.toLocaleString()} rows × ${ds.cols} cols`,
    kind: "info",
  });
  push(600, "executor", { text: "Traceback (most recent call last):", kind: "err" });
  push(250, "executor", { text: `  ${ds.error}`, kind: "err" }, "error");

  // Critic → fix
  push(400, "critic", undefined, "active");
  push(500, "critic", { text: "analyzing traceback…", kind: "muted" });
  push(550, "critic", { text: `patch → ${ds.fix}`, kind: "warn" });
  push(450, "critic", { text: "↻ retry 1 / 5", kind: "warn" });
  push(500, "critic", { text: "✓ step passed", kind: "ok" }, "done");

  // Executor resume
  push(300, "executor", { text: "▶ re-running patched code…", kind: "muted" }, "active");
  push(550, "executor", { text: "✓ all 6 steps executed", kind: "ok" }, "done");

  // AutoML
  push(350, "automl", undefined, "active");
  if (isCluster) {
    push(450, "automl", { text: "KMeans k-search  k ∈ [2, 8]", kind: "muted" });
    push(400, "automl", { text: "  k=3  silhouette 0.49", kind: "code" });
    push(350, "automl", { text: "  k=4  silhouette 0.55  ★ best", kind: "ok" });
  } else {
    push(450, "automl", {
      text: "flaml.AutoML(budget=60s)  searching…",
      kind: "muted",
    });
    push(400, "automl", { text: `  best model → ${r.bestModel}  ★`, kind: "ok" });
    push(300, "automl", { text: "test-set metrics:", kind: "muted" });
    r.metrics.forEach((m) =>
      push(220, "automl", { text: `  ${m.label.padEnd(12)} ${m.value}`, kind: "code" }),
    );
  }
  push(450, "automl", { text: `selected → ${r.bestModel}`, kind: "info" }, "done");

  // Explainer
  push(350, "explainer", undefined, "active");
  push(450, "explainer", {
    text: isCluster
      ? "profiling segments…"
      : isNlp
        ? "extracting themes (LDA + sentiment)…"
        : "computing SHAP values…",
    kind: "muted",
  });
  r.bars.slice(0, 3).forEach((b) => {
    const s = b.sign === -1 ? "−" : b.sign === 1 ? "+" : " ";
    push(300, "explainer", {
      text: `  ${b.label.padEnd(20)} ${s}${b.value.toFixed(2)}`,
      kind: "code",
    });
  });
  push(400, "explainer", { text: "explanations ready", kind: "ok" }, "done");

  // Researcher
  push(350, "researcher", undefined, "active");
  push(500, "researcher", {
    text: `searching the web: ${ds.goal}`.slice(0, 62),
    kind: "muted",
  });
  push(420, "researcher", { text: "  - industry benchmarks & best practices", kind: "code" });
  push(380, "researcher", { text: "  - related studies & domain context", kind: "code" });
  push(450, "researcher", { text: "synthesised external context", kind: "ok" }, "done");

  // Reporter
  push(350, "reporter", undefined, "active");
  push(500, "reporter", { text: "drafting business narrative (Mistral-7B)…", kind: "muted" });
  push(700, "reporter", { text: "✓ report generated", kind: "ok" }, "done");

  return ev;
}
