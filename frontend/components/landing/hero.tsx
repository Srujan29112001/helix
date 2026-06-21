import { ArrowRight, Sparkles, Workflow } from "lucide-react";
import { DataField } from "@/components/backgrounds/data-field";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/section";
import { Reveal } from "@/components/ui/reveal";
import { HeroPreview } from "@/components/landing/hero-preview";

const STATS = [
  { value: "9", label: "specialist agents" },
  { value: "≤5", label: "self-heal retries" },
  { value: "minutes", label: "not days" },
  { value: "100%", label: "explainable" },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-28 pb-20 sm:pt-36">
      {/* animated network background */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 mask-fade opacity-70">
          <DataField />
        </div>
        <div className="absolute left-1/2 top-[-10%] h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-brand/20 blur-[150px]" />
        <div className="absolute right-[8%] top-[30%] h-[360px] w-[360px] rounded-full bg-grape/20 blur-[140px]" />
      </div>

      <Container className="relative">
        <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 font-mono text-xs text-mist backdrop-blur">
              <Sparkles className="h-3.5 w-3.5 text-brand" />
              Multi-agent · Self-correcting · Explainable
            </span>
          </Reveal>

          <Reveal delay={0.06}>
            <h1 className="mt-6 text-balance text-4xl font-semibold leading-[1.05] text-white sm:text-6xl md:text-7xl">
              The autonomous{" "}
              <span className="text-gradient">data scientist</span> that writes
              its own code — and fixes it.
            </h1>
          </Reveal>

          <Reveal delay={0.12}>
            <p className="mt-6 max-w-2xl text-pretty text-base leading-relaxed text-mute sm:text-lg">
              Give Helix a CSV and a sentence. A team of AI agents plans the
              analysis, writes the Python, runs it in a secure sandbox, repairs
              its own errors, finds the best model with AutoML, and explains
              every prediction — then hands you a report.
            </p>
          </Reveal>

          <Reveal delay={0.18}>
            <div className="mt-9 flex flex-col items-center gap-3 sm:flex-row">
              <Button href="/studio" size="lg">
                Launch the Studio
                <ArrowRight className="h-4.5 w-4.5" />
              </Button>
              <Button href="/#pipeline" size="lg" variant="secondary">
                <Workflow className="h-4.5 w-4.5" />
                See the pipeline
              </Button>
            </div>
          </Reveal>
        </div>

        {/* product preview */}
        <Reveal delay={0.26} className="mx-auto mt-16 max-w-5xl">
          <HeroPreview />
        </Reveal>

        {/* stat strip */}
        <Reveal delay={0.34}>
          <div className="mx-auto mt-14 grid max-w-4xl grid-cols-2 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/5 sm:grid-cols-4">
            {STATS.map((s) => (
              <div key={s.label} className="bg-ink/60 px-6 py-5 text-center">
                <div className="font-display text-2xl font-semibold text-white sm:text-3xl">
                  {s.value}
                </div>
                <div className="mt-1 font-mono text-[11px] uppercase tracking-wider text-mute">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
