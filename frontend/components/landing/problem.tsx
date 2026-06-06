import { Hourglass, Repeat2, Bug } from "lucide-react";
import { Container, SectionHeading } from "@/components/ui/section";
import { Reveal, RevealGroup, RevealItem } from "@/components/ui/reveal";

const PROBLEMS = [
  {
    icon: Hourglass,
    stat: "Every question",
    title: "The data bottleneck",
    body: "Business teams ask “why are customers churning?” — then wait days in a queue for a data scientist to answer.",
    accent: "#fb7185",
  },
  {
    icon: Repeat2,
    stat: "60–70%",
    title: "Repetitive grind",
    body: "Most analyst time is spent cleaning messy CSVs, handling missing values and rewriting near-identical EDA — not on insight.",
    accent: "#fbbf24",
  },
  {
    icon: Bug,
    stat: "Fix · rerun · repeat",
    title: "Brittle iteration",
    body: "Code fails, you read the traceback, patch it, run again. For non-experts the debugging loop is slow and painful.",
    accent: "#a78bfa",
  },
];

export function Problem() {
  return (
    <section className="relative py-24 sm:py-28">
      <Container>
        <Reveal>
          <SectionHeading
            eyebrow="The problem"
            title={
              <>
                Insight is trapped behind a{" "}
                <span className="text-gradient-cool">bottleneck</span>.
              </>
            }
            lead="Organizations sit on valuable data but struggle to turn it into decisions — slowed by scarce expertise, repetitive prep, and fragile code."
          />
        </Reveal>

        <RevealGroup className="mt-14 grid gap-5 md:grid-cols-3">
          {PROBLEMS.map((p) => {
            const Icon = p.icon;
            return (
              <RevealItem key={p.title}>
                <div className="group relative h-full overflow-hidden rounded-2xl border border-white/10 bg-panel p-6 transition-colors hover:border-white/20">
                  <div
                    className="absolute -right-10 -top-10 h-32 w-32 rounded-full opacity-20 blur-2xl transition-opacity group-hover:opacity-40"
                    style={{ background: p.accent }}
                  />
                  <div
                    className="relative grid h-11 w-11 place-items-center rounded-xl border"
                    style={{
                      borderColor: `${p.accent}40`,
                      background: `${p.accent}14`,
                    }}
                  >
                    <Icon className="h-5 w-5" style={{ color: p.accent }} />
                  </div>
                  <div
                    className="relative mt-5 font-mono text-xs uppercase tracking-[0.18em]"
                    style={{ color: p.accent }}
                  >
                    {p.stat}
                  </div>
                  <h3 className="relative mt-2 text-lg font-semibold text-white">
                    {p.title}
                  </h3>
                  <p className="relative mt-2 text-sm leading-relaxed text-mute">
                    {p.body}
                  </p>
                </div>
              </RevealItem>
            );
          })}
        </RevealGroup>
      </Container>
    </section>
  );
}
