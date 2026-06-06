"use client";

import { motion } from "motion/react";
import type { ResultBar, DistItem } from "@/lib/studio-run";
import { alpha } from "@/lib/utils";

export function Donut({
  fraction,
  value,
  label,
  accent = "#25d7f0",
}: {
  fraction?: number;
  value: string;
  label: string;
  accent?: string;
}) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const frac = fraction ?? 1;
  const off = c * (1 - frac);
  return (
    <div className="relative grid h-36 w-36 place-items-center">
      <svg viewBox="0 0 128 128" className="h-36 w-36 -rotate-90">
        <circle cx="64" cy="64" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" />
        <motion.circle
          cx="64"
          cy="64"
          r={r}
          fill="none"
          stroke="url(#donutGrad)"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: off }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        />
        <defs>
          <linearGradient id="donutGrad" x1="0" y1="0" x2="128" y2="128">
            <stop offset="0" stopColor={accent} />
            <stop offset="1" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute text-center">
        <div className="font-display text-3xl font-semibold text-white">{value}</div>
        <div className="font-mono text-[10px] uppercase tracking-wider text-mute">{label}</div>
      </div>
    </div>
  );
}

export function Bars({ bars, accent }: { bars: ResultBar[]; accent: string }) {
  const diverging = bars.some((b) => b.sign !== undefined);

  if (!diverging) {
    return (
      <div className="space-y-3">
        {bars.map((b, i) => (
          <div key={b.label} className="grid grid-cols-[130px_1fr] items-center gap-3">
            <span className="truncate text-right text-xs text-mist">{b.label}</span>
            <div className="h-2.5 overflow-hidden rounded-full bg-white/5">
              <motion.div
                className="h-full rounded-full"
                style={{ background: `linear-gradient(90deg, ${alpha(accent, 0.45)}, ${accent})` }}
                initial={{ width: 0 }}
                animate={{ width: `${b.value * 100}%` }}
                transition={{ duration: 0.8, delay: 0.15 + i * 0.07, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      <div className="grid grid-cols-[130px_1fr] gap-3">
        <span />
        <div className="flex justify-between font-mono text-[9px] uppercase tracking-wider text-mute">
          <span>decreases</span>
          <span>increases</span>
        </div>
      </div>
      {bars.map((b, i) => {
        const positive = (b.sign ?? 1) >= 0;
        const col = positive ? "#25d7f0" : "#fb7185";
        return (
          <div key={b.label} className="grid grid-cols-[130px_1fr] items-center gap-3">
            <span className="truncate text-right text-xs text-mist">{b.label}</span>
            <div className="relative h-4">
              <div className="absolute left-1/2 top-0 h-full w-px bg-white/15" />
              <motion.div
                className="absolute top-1/2 h-2.5 -translate-y-1/2 rounded-sm"
                style={
                  positive
                    ? { background: col, boxShadow: `0 0 10px ${alpha(col, 0.6)}`, left: "50%" }
                    : { background: col, boxShadow: `0 0 10px ${alpha(col, 0.6)}`, right: "50%" }
                }
                initial={{ width: 0 }}
                animate={{ width: `${b.value * 50}%` }}
                transition={{ duration: 0.7, delay: 0.15 + i * 0.07, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function DistBars({ items, accent }: { items: DistItem[]; accent: string }) {
  return (
    <div className="space-y-3">
      {items.map((d, i) => (
        <div key={d.label}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-mist">{d.label}</span>
            <span className="font-mono text-mute">{d.display}</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-white/5">
            <motion.div
              className="h-full rounded-full"
              style={{ background: `linear-gradient(90deg, ${alpha(accent, 0.4)}, ${accent})` }}
              initial={{ width: 0 }}
              animate={{ width: `${d.value * 100}%` }}
              transition={{ duration: 0.8, delay: 0.1 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MetricTiles({
  metrics,
}: {
  metrics: { label: string; value: string }[];
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {metrics.map((m) => (
        <div key={m.label} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3 text-center">
          <div className="font-display text-xl font-semibold text-white">{m.value}</div>
          <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-mute">{m.label}</div>
        </div>
      ))}
    </div>
  );
}
