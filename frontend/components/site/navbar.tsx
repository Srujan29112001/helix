"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { Logo } from "@/components/site/logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const LINKS = [
  { label: "Pipeline", href: "/#pipeline" },
  { label: "Capabilities", href: "/#capabilities" },
  { label: "Use cases", href: "/#use-cases" },
  { label: "Stack", href: "/#stack" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div className="mx-auto w-full max-w-7xl px-4 pt-3 sm:px-6 sm:pt-4">
        <nav
          className={cn(
            "flex items-center justify-between gap-4 rounded-2xl border px-4 py-2.5 transition-all duration-300",
            scrolled
              ? "border-white/10 bg-ink/70 backdrop-blur-xl shadow-[0_8px_40px_-12px_rgba(0,0,0,0.8)]"
              : "border-transparent bg-transparent",
          )}
        >
          <Link href="/" aria-label="Helix home">
            <Logo />
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="rounded-lg px-3.5 py-2 text-sm text-mute transition-colors hover:text-white"
              >
                {l.label}
              </Link>
            ))}
          </div>

          <div className="hidden items-center gap-2 md:flex">
            <Button href="/studio" size="sm" variant="ghost">
              Sign in
            </Button>
            <Button href="/studio" size="sm">
              Launch Studio
              <ArrowUpRight className="h-4 w-4" />
            </Button>
          </div>

          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="grid h-10 w-10 place-items-center rounded-lg border border-white/10 bg-white/5 text-white md:hidden"
            aria-label="Toggle menu"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </nav>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="mx-auto mt-2 w-full max-w-7xl px-4 sm:px-6 md:hidden"
          >
            <div className="glass flex flex-col gap-1 rounded-2xl p-3">
              {LINKS.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="rounded-xl px-4 py-3 text-sm text-mist transition-colors hover:bg-white/5"
                >
                  {l.label}
                </Link>
              ))}
              <Button href="/studio" className="mt-1 w-full">
                Launch Studio
                <ArrowUpRight className="h-4 w-4" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
