import {
  Crosshair,
  TrendingUp,
  Boxes,
  MessageSquareText,
} from "lucide-react";
import { Container, SectionHeading } from "@/components/ui/section";
import { Reveal, RevealGroup, RevealItem } from "@/components/ui/reveal";
import { alpha } from "@/lib/utils";

const CASES = [
  {
    icon: Crosshair,
    accent: "#25d7f0",
    industry: "Finance",
    kind: "Binary classification",
    question: "Which applicants will default on a loan?",
    output: "0.86 ROC-AUC · drivers: credit score, debt-to-income, income",
  },
  {
    icon: TrendingUp,
    accent: "#9ae64a",
    industry: "Retail",
    kind: "Regression",
    question: "How much will each store sell?",
    output: "Per-store forecast · seasonality + promo effects quantified",
  },
  {
    icon: Boxes,
    accent: "#a78bfa",
    industry: "Marketing",
    kind: "Clustering",
    question: "What natural customer groups exist?",
    output: "4 segments · budget, premium, occasional, high-value",
  },
  {
    icon: MessageSquareText,
    accent: "#fb7185",
    industry: "E-commerce",
    kind: "NLP + text",
    question: "What are people actually saying?",
    output: "Sentiment split · top themes: delivery, quality, support",
  },
];

const INDUSTRIES = [
  "Finance",
  "Healthcare",
  "Retail",
  "Marketing",
  "HR",
  "Manufacturing",
  "Education",
  "Logistics",
  "Energy",
  "SaaS",
];

export function UseCases() {
  return (
    <section id="use-cases" className="relative scroll-mt-24 py-24 sm:py-28">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-dots opacity-[0.15] mask-fade" />
      <Container>
        <Reveal>
          <SectionHeading
            eyebrow="Any industry · any data"
            title={
              <>
                One agent.{" "}
                <span className="text-gradient">Every industry.</span>
              </>
            }
            lead="These are just examples — Helix works on any tabular dataset from any field. Upload yours and ask in plain English."
          />
        </Reveal>

        <RevealGroup className="mt-14 grid gap-5 sm:grid-cols-2">
          {CASES.map((c) => {
            const Icon = c.icon;
            return (
              <RevealItem key={c.industry}>
                <div className="group relative h-full overflow-hidden rounded-2xl border border-white/10 bg-panel p-7 transition-all duration-300 hover:-translate-y-1 hover:border-white/20">
                  <div
                    className="absolute inset-x-0 top-0 h-px opacity-60"
                    style={{
                      background: `linear-gradient(90deg, transparent, ${c.accent}, transparent)`,
                    }}
                  />
                  <div className="flex items-center justify-between">
                    <span
                      className="grid h-12 w-12 place-items-center rounded-xl border"
                      style={{
                        borderColor: alpha(c.accent, 0.35),
                        background: alpha(c.accent, 0.12),
                      }}
                    >
                      <Icon className="h-6 w-6" style={{ color: c.accent }} />
                    </span>
                    <span
                      className="rounded-full px-3 py-1 font-mono text-[11px] uppercase tracking-wider"
                      style={{
                        color: c.accent,
                        background: alpha(c.accent, 0.1),
                      }}
                    >
                      {c.industry}
                    </span>
                  </div>

                  <h3 className="mt-6 text-xl font-semibold text-white">
                    {c.question}
                  </h3>
                  <div className="mt-2 font-mono text-xs text-mute">
                    {c.kind}
                  </div>

                  <div className="mt-5 flex items-start gap-2 rounded-xl border border-white/5 bg-white/[0.02] p-3">
                    <span
                      className="mt-0.5 font-mono text-xs"
                      style={{ color: c.accent }}
                    >
                      →
                    </span>
                    <p className="text-sm leading-relaxed text-mist">
                      {c.output}
                    </p>
                  </div>
                </div>
              </RevealItem>
            );
          })}
        </RevealGroup>

        <Reveal delay={0.1}>
          <div className="mt-12 flex flex-wrap items-center justify-center gap-2.5">
            {INDUSTRIES.map((x) => (
              <span
                key={x}
                className="rounded-full border border-white/10 bg-white/[0.03] px-3.5 py-1.5 text-sm text-mute transition-colors hover:border-white/20 hover:text-mist"
              >
                {x}
              </span>
            ))}
            <span className="rounded-full border border-brand/30 bg-brand/10 px-3.5 py-1.5 text-sm text-brand">
              + any CSV
            </span>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
