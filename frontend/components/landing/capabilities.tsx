import {
  RefreshCw,
  ScanSearch,
  Sparkles,
  ShieldCheck,
  Database,
  Network,
} from "lucide-react";
import { Container, SectionHeading } from "@/components/ui/section";
import { Reveal, RevealGroup, RevealItem } from "@/components/ui/reveal";
import { alpha, cn } from "@/lib/utils";

const FEATURES = [
  {
    icon: RefreshCw,
    title: "Self-correcting execution",
    body: "When generated code throws, the Critic reads the traceback, rewrites the offending lines, and retries — up to five times — until it runs clean. No human in the loop.",
    accent: "#fbbf24",
    span: "md:col-span-3",
    big: true,
  },
  {
    icon: ScanSearch,
    title: "Explainable by default",
    body: "Every model ships with SHAP attributions, so you always know which features drove a prediction — and can defend it.",
    accent: "#e879f9",
    span: "md:col-span-3",
    big: true,
  },
  {
    icon: Sparkles,
    title: "AutoML model search",
    body: "FLAML benchmarks and tunes estimators under a time budget, returning the best model automatically.",
    accent: "#9ae64a",
    span: "md:col-span-2",
  },
  {
    icon: ShieldCheck,
    title: "Secure sandbox",
    body: "Code runs in RestrictedPython with file-system and network access blocked — generated code can't touch your machine.",
    accent: "#38bdf8",
    span: "md:col-span-2",
  },
  {
    icon: Database,
    title: "RAG-grounded code",
    body: "A ChromaDB vector store of library docs grounds the Coder, cutting hallucinated APIs.",
    accent: "#25d7f0",
    span: "md:col-span-2",
  },
  {
    icon: Network,
    title: "Multi-agent orchestration",
    body: "LangGraph wires the nine agents into a single stateful graph — with branching, retries and shared memory — so the workflow is observable end to end.",
    accent: "#8b5cf6",
    span: "md:col-span-6",
    wide: true,
  },
];

export function Capabilities() {
  return (
    <section id="capabilities" className="relative scroll-mt-24 py-24 sm:py-28">
      <Container>
        <Reveal>
          <SectionHeading
            eyebrow="Capabilities"
            title={
              <>
                Engineered for trust,{" "}
                <span className="text-gradient-cool">speed and rigor</span>.
              </>
            }
            lead="Everything you'd expect from a careful data scientist — automated, sandboxed and explainable."
          />
        </Reveal>

        <RevealGroup className="mt-14 grid gap-4 md:grid-cols-6">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <RevealItem key={f.title} className={cn(f.span)}>
                <div className="group relative h-full overflow-hidden rounded-2xl border border-white/10 bg-panel p-6 transition-all duration-300 hover:border-white/20">
                  <div
                    className="absolute -right-12 -top-12 h-40 w-40 rounded-full opacity-[0.12] blur-3xl transition-opacity duration-300 group-hover:opacity-25"
                    style={{ background: f.accent }}
                  />
                  <div
                    className={cn(
                      "relative flex items-start gap-4",
                      f.wide && "md:items-center",
                    )}
                  >
                    <span
                      className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border"
                      style={{
                        borderColor: alpha(f.accent, 0.35),
                        background: alpha(f.accent, 0.12),
                      }}
                    >
                      <Icon className="h-6 w-6" style={{ color: f.accent }} />
                    </span>
                    <div className={cn(f.wide && "md:max-w-2xl")}>
                      <h3 className="text-lg font-semibold text-white">
                        {f.title}
                      </h3>
                      <p className="mt-2 text-sm leading-relaxed text-mute">
                        {f.body}
                      </p>
                    </div>

                    {f.wide && (
                      <div className="ml-auto hidden items-center gap-2 lg:flex">
                        {["plan", "code", "run", "heal", "model", "explain"].map(
                          (s, i, arr) => (
                            <div key={s} className="flex items-center gap-2">
                              <span className="rounded-md border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[10px] text-mute">
                                {s}
                              </span>
                              {i < arr.length - 1 && (
                                <span className="text-mute/40">→</span>
                              )}
                            </div>
                          ),
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </RevealItem>
            );
          })}
        </RevealGroup>
      </Container>
    </section>
  );
}
