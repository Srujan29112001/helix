import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "relative grid place-items-center overflow-hidden rounded-xl border border-white/10 bg-gradient-to-br from-white/10 to-white/0",
        className,
      )}
    >
      <span className="absolute inset-0 bg-[radial-gradient(120%_120%_at_30%_20%,rgba(37,215,240,0.35),transparent_60%)]" />
      <svg
        viewBox="0 0 32 32"
        fill="none"
        className="relative h-[62%] w-[62%]"
        aria-hidden
      >
        <defs>
          <linearGradient id="helix-mark" x1="2" y1="2" x2="30" y2="30">
            <stop offset="0" stopColor="#25d7f0" />
            <stop offset="1" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
        <g stroke="url(#helix-mark)" strokeWidth="1.6" strokeLinecap="round">
          <path d="M8 10 L16 16 L24 8" />
          <path d="M16 16 L24 23" />
          <path d="M16 16 L9 24" />
        </g>
        <g fill="#25d7f0">
          <circle cx="8" cy="10" r="2.4" />
          <circle cx="24" cy="8" r="2.1" fill="#a78bfa" />
          <circle cx="24" cy="23" r="2.1" fill="#8b5cf6" />
          <circle cx="9" cy="24" r="1.9" fill="#38bdf8" />
        </g>
        <circle cx="16" cy="16" r="3.1" fill="#ffffff" />
      </svg>
    </span>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <LogoMark className="h-9 w-9" />
      <span className="font-display text-lg font-semibold tracking-tight text-white">
        Helix
        <span className="text-brand">.</span>
      </span>
    </span>
  );
}
