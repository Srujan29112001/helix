import { Container, SectionHeading } from "@/components/ui/section";
import { Reveal, RevealGroup, RevealItem } from "@/components/ui/reveal";

const GROUPS = [
  {
    title: "Language models",
    accent: "#8b5cf6",
    items: ["DeepSeek-Coder", "Mistral-7B"],
  },
  {
    title: "Orchestration",
    accent: "#25d7f0",
    items: ["LangGraph", "LangChain", "Pydantic"],
  },
  {
    title: "Execution & safety",
    accent: "#38bdf8",
    items: ["RestrictedPython", "Sandbox runtime"],
  },
  {
    title: "ML & AutoML",
    accent: "#9ae64a",
    items: ["scikit-learn", "FLAML", "pandas", "NumPy"],
  },
  {
    title: "Explainability",
    accent: "#e879f9",
    items: ["SHAP"],
  },
  {
    title: "Retrieval · RAG",
    accent: "#fbbf24",
    items: ["ChromaDB", "FAISS", "sentence-transformers"],
  },
  {
    title: "Evaluation",
    accent: "#fb7185",
    items: ["RAGAS", "DSPy"],
  },
  {
    title: "Interface",
    accent: "#25d7f0",
    items: ["Next.js", "FastAPI", "Tailwind"],
  },
];

export function Stack() {
  return (
    <section id="stack" className="relative scroll-mt-24 py-24 sm:py-28">
      <Container>
        <Reveal>
          <SectionHeading
            eyebrow="Tech stack"
            title={
              <>
                Open models,{" "}
                <span className="text-gradient-cool">production tooling</span>.
              </>
            }
            lead="A pragmatic stack of open-source LLMs, battle-tested ML libraries and a modern web interface."
          />
        </Reveal>

        <RevealGroup className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {GROUPS.map((g) => (
            <RevealItem key={g.title}>
              <div className="h-full rounded-2xl border border-white/10 bg-panel p-5">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{
                      background: g.accent,
                      boxShadow: `0 0 10px 1px ${g.accent}`,
                    }}
                  />
                  <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">
                    {g.title}
                  </h3>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {g.items.map((it) => (
                    <span
                      key={it}
                      className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-sm text-mist transition-colors hover:border-white/20"
                    >
                      {it}
                    </span>
                  ))}
                </div>
              </div>
            </RevealItem>
          ))}
        </RevealGroup>
      </Container>
    </section>
  );
}
