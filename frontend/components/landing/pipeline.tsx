"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { RefreshCw } from "lucide-react";
import { AGENTS, type AgentId } from "@/lib/agents";
import { Container, SectionHeading } from "@/components/ui/section";
import { Reveal } from "@/components/ui/reveal";
import { alpha, cn } from "@/lib/utils";

const SNIPPETS: Record<AgentId, { label: string; lines: string[] }> = {
  planner: {
    label: "plan.md",
    lines: [
      "1. Load & validate dataset",
      "2. Exploratory data analysis",
      "3. Handle missing values",
      "4. Encode categorical features",
      "5. Train & evaluate model",
      "6. Explain with SHAP",
    ],
  },
  coder: {
    label: "step_04.py",
    lines: [
      "import pandas as pd",
      'df = pd.read_csv("your_data.csv")',
      "y = df[target]",
      "X = pd.get_dummies(df.drop(target, axis=1))",
    ],
  },
  executor: {
    label: "sandbox › stdout",
    lines: [
      "▶ running step_04.py  (network: off · fs: off)",
      "Traceback (most recent call last):",
      "TypeError: could not convert column to float",
      "✗ exited with error",
    ],
  },
  critic: {
    label: "critic › patch",
    lines: [
      "diagnosis: mixed-type column",
      "fix: pd.to_numeric(col, errors='coerce')",
      "↻ retry 1 / 5",
      "✓ step_04.py passed",
    ],
  },
  automl: {
    label: "flaml › search",
    lines: [
      "AutoML(task=auto, budget=60s)",
      "  lgbm     score 0.91  ★ best",
      "  xgboost  score 0.90",
      "  rf       score 0.88",
    ],
  },
  explainer: {
    label: "shap › values",
    lines: [
      "feature_1          +0.92",
      "feature_2          −0.78",
      "feature_3          +0.64",
      "feature_4          −0.41",
    ],
  },
  researcher: {
    label: "research › web",
    lines: [
      "searching the live web…",
      "- industry benchmarks",
      "- best practices & studies",
      "✓ synthesised domain context",
    ],
  },
  reporter: {
    label: "report.md",
    lines: [
      "## Executive summary",
      "The model reaches strong accuracy.",
      "feature_1 is the biggest driver of",
      "the outcome → focus action there.",
    ],
  },
};

export function Pipeline() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const n = AGENTS.length;

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => setActive((a) => (a + 1) % n), 2600);
    return () => clearInterval(id);
  }, [paused, n]);

  const agent = AGENTS[active];
  const snippet = SNIPPETS[agent.id];
  const Icon = agent.icon;

  return (
    <section id="pipeline" className="relative scroll-mt-24 py-24 sm:py-28">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-grid opacity-[0.18] mask-fade" />
      <Container>
        <Reveal>
          <SectionHeading
            eyebrow="The pipeline"
            title={
              <>
                Seven agents.{" "}
                <span className="text-gradient">One autonomous workflow.</span>
              </>
            }
            lead="Orchestrated by LangGraph, each agent owns one job and passes state to the next — with a self-correction loop that keeps the whole thing running."
          />
        </Reveal>

        <Reveal delay={0.1}>
          <div
            className="mt-14"
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
          >
            {/* rail */}
            <div className="relative px-2">
              <div className="absolute left-6 right-6 top-5 h-px bg-white/10 sm:top-7">
                <motion.div
                  className="h-full"
                  style={{
                    background:
                      "linear-gradient(90deg, #25d7f0, #8b5cf6, #fb7185)",
                    boxShadow: "0 0 12px rgba(37,215,240,0.6)",
                  }}
                  animate={{ width: `${(active / (n - 1)) * 100}%` }}
                  transition={{ duration: 0.6, ease: "easeInOut" }}
                />
              </div>

              <div className="relative flex justify-between gap-1">
                {AGENTS.map((a, i) => {
                  const AIcon = a.icon;
                  const isActive = i === active;
                  const isDone = i < active;
                  return (
                    <button
                      key={a.id}
                      onClick={() => setActive(i)}
                      className="group flex flex-1 flex-col items-center gap-2 outline-none"
                      aria-label={a.name}
                    >
                      <motion.span
                        className="relative grid h-10 w-10 place-items-center rounded-xl border backdrop-blur sm:h-14 sm:w-14 sm:rounded-2xl"
                        animate={{
                          scale: isActive ? 1.12 : 1,
                        }}
                        transition={{ type: "spring", stiffness: 300, damping: 20 }}
                        style={{
                          borderColor: isActive || isDone
                            ? alpha(a.accent, 0.6)
                            : "rgba(255,255,255,0.1)",
                          background: isActive
                            ? alpha(a.accent, 0.16)
                            : "rgba(255,255,255,0.03)",
                          boxShadow: isActive
                            ? `0 0 30px -4px ${alpha(a.accent, 0.7)}`
                            : "none",
                        }}
                      >
                        <AIcon
                          className="h-5 w-5 transition-colors sm:h-6 sm:w-6"
                          style={{
                            color:
                              isActive || isDone ? a.accent : "#76859f",
                          }}
                        />
                        {isActive && (
                          <motion.span
                            layoutId="pulse"
                            className="absolute inset-0 rounded-2xl"
                            style={{
                              boxShadow: `0 0 0 1px ${alpha(a.accent, 0.8)}`,
                            }}
                          />
                        )}
                      </motion.span>
                      <span
                        className={cn(
                          "hidden text-xs font-medium transition-colors sm:block",
                          isActive ? "text-white" : "text-mute",
                        )}
                      >
                        {a.name}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* self-correction loop note */}
              <div className="mt-3 flex justify-center sm:justify-start sm:pl-[28%]">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-gold/30 bg-gold/10 px-3 py-1 font-mono text-[11px] text-gold">
                  <RefreshCw className="h-3 w-3" />
                  self-correction loop · executor ⇄ critic ≤ 5×
                </span>
              </div>
            </div>

            {/* detail card */}
            <div className="mt-10 overflow-hidden rounded-2xl border border-white/10 bg-panel">
              <AnimatePresence mode="wait">
                <motion.div
                  key={agent.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.3 }}
                  className="grid gap-px bg-white/5 lg:min-h-[296px] lg:grid-cols-2"
                >
                  <div className="bg-ink/60 p-7">
                    <div className="flex items-center gap-3">
                      <span
                        className="grid h-11 w-11 place-items-center rounded-xl border"
                        style={{
                          borderColor: alpha(agent.accent, 0.4),
                          background: alpha(agent.accent, 0.12),
                        }}
                      >
                        <Icon
                          className="h-5 w-5"
                          style={{ color: agent.accent }}
                        />
                      </span>
                      <div>
                        <div className="font-mono text-[11px] uppercase tracking-wider text-mute">
                          Agent {active + 1} / {n}
                        </div>
                        <h3 className="text-xl font-semibold text-white">
                          {agent.name}
                        </h3>
                      </div>
                    </div>
                    <span
                      className="mt-4 inline-flex rounded-full px-3 py-1 font-mono text-[11px]"
                      style={{
                        color: agent.accent,
                        background: alpha(agent.accent, 0.12),
                      }}
                    >
                      {agent.tech}
                    </span>
                    <p className="mt-4 text-sm leading-relaxed text-mist">
                      {agent.detail}
                    </p>
                  </div>

                  <div className="bg-[#06080f] p-5">
                    <div className="mb-3 flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-coral/70" />
                      <span className="h-2 w-2 rounded-full bg-gold/70" />
                      <span className="h-2 w-2 rounded-full bg-acid/70" />
                      <span className="ml-2 font-mono text-[11px] text-mute">
                        {snippet.label}
                      </span>
                    </div>
                    <pre className="overflow-x-auto font-mono text-[12.5px] leading-relaxed text-mist/90">
                      {snippet.lines.map((line, i) => (
                        <div key={i} className="flex gap-3">
                          <span className="select-none text-mute/40">
                            {String(i + 1).padStart(2, "0")}
                          </span>
                          <span
                            className={cn(
                              line.startsWith("✓") && "text-acid",
                              line.startsWith("✗") && "text-coral",
                              (line.startsWith("↻") ||
                                line.includes("retry")) &&
                                "text-gold",
                              line.includes("★ best") && "text-acid",
                              line.startsWith("KeyError") && "text-coral",
                            )}
                          >
                            {line}
                          </span>
                        </div>
                      ))}
                    </pre>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
