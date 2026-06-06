import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Logo } from "@/components/site/logo";
import { Container } from "@/components/ui/section";

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.5v-1.8c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.6.8.5 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5Z" />
    </svg>
  );
}

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Studio", href: "/studio" },
      { label: "Pipeline", href: "/#pipeline" },
      { label: "Capabilities", href: "/#capabilities" },
      { label: "Use cases", href: "/#use-cases" },
    ],
  },
  {
    title: "Technology",
    links: [
      { label: "Tech stack", href: "/#stack" },
      { label: "LangGraph", href: "/#stack" },
      { label: "FLAML AutoML", href: "/#stack" },
      { label: "SHAP", href: "/#stack" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="relative mt-24 overflow-hidden border-t border-white/10 bg-ink-2">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-brand/50 to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-dots opacity-[0.35] mask-fade-b" />
      <Container className="relative py-14">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div className="max-w-sm">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-mute">
              An autonomous, multi-agent data science system. It plans, codes,
              executes, self-corrects, models, explains and reports — from a CSV
              and a sentence.
            </p>
            <div className="mt-5 flex items-center gap-3">
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-white/5 text-mute transition-colors hover:text-white"
                aria-label="GitHub"
              >
                <GithubIcon className="h-4.5 w-4.5" />
              </a>
            </div>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h3 className="font-mono text-xs uppercase tracking-[0.18em] text-mute">
                {col.title}
              </h3>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      className="text-sm text-mist/80 transition-colors hover:text-brand"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-white/10 pt-6 text-sm text-mute sm:flex-row sm:items-center">
          <p>
            © {new Date().getFullYear()} Helix · Capstone Project ·{" "}
            <span className="text-mist/70">IIIT-H</span>
          </p>
          <Link
            href="/studio"
            className="inline-flex items-center gap-1.5 text-mist/80 transition-colors hover:text-brand"
          >
            Try the live Studio
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </Container>
    </footer>
  );
}
