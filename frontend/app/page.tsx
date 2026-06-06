import { Navbar } from "@/components/site/navbar";
import { Footer } from "@/components/site/footer";
import { Hero } from "@/components/landing/hero";
import { Marquee } from "@/components/landing/marquee";
import { Problem } from "@/components/landing/problem";
import { Pipeline } from "@/components/landing/pipeline";
import { Capabilities } from "@/components/landing/capabilities";
import { UseCases } from "@/components/landing/use-cases";
import { Stack } from "@/components/landing/stack";
import { CTA } from "@/components/landing/cta";

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="relative">
        <Hero />
        <Marquee />
        <Problem />
        <Pipeline />
        <Capabilities />
        <UseCases />
        <Stack />
        <CTA />
      </main>
      <Footer />
    </>
  );
}
