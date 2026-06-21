import { ArrowRight } from "lucide-react";
import { DataField } from "@/components/backgrounds/data-field";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/section";
import { Reveal } from "@/components/ui/reveal";

export function CTA() {
  return (
    <section className="relative py-12">
      <Container>
        <Reveal>
          <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-panel px-6 py-16 text-center sm:px-12 sm:py-20">
            <div className="pointer-events-none absolute inset-0 opacity-50 mask-fade">
              <DataField interactive={false} density={0.7} />
            </div>
            <div className="pointer-events-none absolute left-1/2 top-0 h-[300px] w-[600px] -translate-x-1/2 rounded-full bg-brand/20 blur-[120px]" />

            <div className="relative mx-auto max-w-2xl">
              <h2 className="text-balance text-3xl font-semibold leading-tight text-white sm:text-5xl">
                Meet your{" "}
                <span className="text-gradient">autonomous analyst</span>.
              </h2>
              <p className="mx-auto mt-5 max-w-xl text-pretty text-base text-mute sm:text-lg">
                Upload a dataset, type a goal, and watch nine agents turn it
                into a decision — in minutes.
              </p>
              <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Button href="/studio" size="lg">
                  Launch the Studio
                  <ArrowRight className="h-4.5 w-4.5" />
                </Button>
                <Button href="/#pipeline" size="lg" variant="secondary">
                  Explore the pipeline
                </Button>
              </div>
            </div>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
