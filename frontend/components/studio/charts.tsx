"use client";

import { Fragment, type ReactNode } from "react";
import { motion } from "motion/react";
import type {
  ResultBar,
  DistItem,
  ChartCard as ChartCardData,
  ChartTable,
} from "@/lib/studio-run";
import { alpha, cn } from "@/lib/utils";

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
          <div key={b.label} className="grid grid-cols-[118px_1fr_34px] items-center gap-3">
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
            <span className="text-right font-mono text-[10px] text-mute">{b.value.toFixed(2)}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      <div className="grid grid-cols-[118px_1fr_34px] gap-3">
        <span />
        <div className="flex justify-between font-mono text-[9px] uppercase tracking-wider text-mute">
          <span>decreases</span>
          <span>increases</span>
        </div>
        <span />
      </div>
      {bars.map((b, i) => {
        const positive = (b.sign ?? 1) >= 0;
        const col = positive ? "#25d7f0" : "#fb7185";
        return (
          <div key={b.label} className="grid grid-cols-[118px_1fr_34px] items-center gap-3">
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
            <span className="text-right font-mono text-[10px]" style={{ color: col }}>
              {positive ? "+" : "−"}
              {b.value.toFixed(2)}
            </span>
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
    <div className="flex flex-wrap gap-2">
      {metrics.map((m) => (
        <div
          key={m.label}
          className="min-w-[84px] flex-1 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3 text-center"
        >
          <div className="font-display text-xl font-semibold text-white">{m.value}</div>
          <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-mute">{m.label}</div>
        </div>
      ))}
    </div>
  );
}

export function Pie({
  items,
  accent = "#25d7f0",
}: {
  items: { label: string; value: number }[];
  accent?: string;
}) {
  const COLORS = [accent, "#8b5cf6", "#9ae64a", "#fb7185", "#fbbf24", "#38bdf8", "#f472b6"];
  const vals = items.map((d) => Math.max(0, d.value));
  const total = vals.reduce((s, v) => s + v, 0) || 1;
  const C = 70;
  const R = 64;
  let cum = 0;
  const segs = items.map((d, i) => {
    const frac = vals[i] / total;
    const start = cum;
    cum += frac;
    const a0 = 2 * Math.PI * start - Math.PI / 2;
    const a1 = 2 * Math.PI * cum - Math.PI / 2;
    const x0 = C + R * Math.cos(a0);
    const y0 = C + R * Math.sin(a0);
    const x1 = C + R * Math.cos(a1);
    const y1 = C + R * Math.sin(a1);
    const large = frac > 0.5 ? 1 : 0;
    return {
      label: d.label,
      frac,
      color: COLORS[i % COLORS.length],
      full: frac >= 0.999,
      path: `M ${C} ${C} L ${x0.toFixed(2)} ${y0.toFixed(2)} A ${R} ${R} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)} Z`,
    };
  });
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <svg viewBox="0 0 140 140" className="h-36 w-36 shrink-0">
        {segs.map((s) =>
          s.full ? (
            <circle key={s.label} cx={C} cy={C} r={R} fill={s.color} opacity={0.92} />
          ) : (
            <motion.path
              key={s.label}
              d={s.path}
              fill={s.color}
              stroke="#0a0d16"
              strokeWidth="1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.92 }}
              transition={{ duration: 0.5 }}
            />
          ),
        )}
      </svg>
      <div className="w-full space-y-1.5">
        {segs.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-xs">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: s.color }} />
            <span className="truncate text-mist">{s.label}</span>
            <span className="ml-auto font-mono text-mute">{(s.frac * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Horizontal bar chart for 0..1 / percentage quality metrics (accuracy, F1, …). */
export function MetricsBars({
  metrics,
  accent = "#25d7f0",
}: {
  metrics: { label: string; value: string }[];
  accent?: string;
}) {
  const parsed = metrics
    .map((m) => {
      const isPct = m.value.trim().endsWith("%");
      const num = parseFloat(m.value.replace(/[^0-9.\-]/g, ""));
      let frac = NaN;
      if (!Number.isNaN(num)) frac = isPct ? num / 100 : num <= 1 ? num : NaN;
      return { ...m, frac };
    })
    .filter((m) => !Number.isNaN(m.frac) && m.frac >= 0 && m.frac <= 1.0001);
  if (!parsed.length) return null;
  return (
    <div className="space-y-3">
      {parsed.map((m, i) => (
        <div key={m.label} className="grid grid-cols-[96px_1fr_42px] items-center gap-3">
          <span className="truncate text-right text-xs text-mist">{m.label}</span>
          <div className="h-2.5 overflow-hidden rounded-full bg-white/5">
            <motion.div
              className="h-full rounded-full"
              style={{ background: `linear-gradient(90deg, ${alpha(accent, 0.45)}, ${accent})` }}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(1, m.frac) * 100}%` }}
              transition={{ duration: 0.8, delay: 0.1 + i * 0.07, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
          <span className="text-right font-mono text-[11px] text-mute">{m.value}</span>
        </div>
      ))}
    </div>
  );
}

/** Compact key-statistic cards. */
export function StatCards({ stats }: { stats: { label: string; value: string }[] }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      {stats.map((s) => (
        <div key={s.label} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3">
          <div className="truncate font-display text-lg font-semibold text-white">{s.value}</div>
          <div className="mt-0.5 font-mono text-[9px] uppercase tracking-wider text-mute">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

/** Vertical histogram (column chart) for a numeric feature's distribution. */
export function Histogram({
  bins,
  accent = "#25d7f0",
}: {
  bins: { label: string; count: number }[];
  accent?: string;
}) {
  const max = Math.max(...bins.map((b) => b.count), 1);
  return (
    <div>
      <div className="flex h-44 items-end gap-1.5">
        {bins.map((b, i) => (
          <div key={i} className="flex h-full flex-1 flex-col items-center justify-end">
            <span className="mb-1 font-mono text-[9px] text-mute">{b.count}</span>
            <motion.div
              className="w-full rounded-t"
              style={{ background: `linear-gradient(180deg, ${accent}, ${alpha(accent, 0.3)})` }}
              initial={{ height: 0 }}
              animate={{ height: `${(b.count / max) * 86}%` }}
              transition={{ duration: 0.7, delay: 0.1 + i * 0.05, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-1.5">
        {bins.map((b, i) => (
          <span key={i} className="flex-1 truncate text-center font-mono text-[8px] text-mute">
            {b.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Scatter plot of two features, coloured by the target, with a legend. */
export function Scatter({
  data,
}: {
  data: {
    x: string;
    y: string;
    points: { x: number; y: number; c: number }[];
    legend?: { low: string; high: string };
  };
}) {
  const W = 300;
  const H = 230;
  const P = 26;
  const col = (c: number) => (c >= 0.5 ? "#fb7185" : "#25d7f0");
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <line x1={P} y1={H - P} x2={W - 8} y2={H - P} stroke="rgba(255,255,255,0.15)" />
        <line x1={P} y1={8} x2={P} y2={H - P} stroke="rgba(255,255,255,0.15)" />
        {data.points.map((pt, i) => (
          <circle
            key={i}
            cx={P + pt.x * (W - P - 14)}
            cy={H - P - pt.y * (H - P - 14)}
            r="3"
            fill={col(pt.c)}
            opacity={0.65}
          />
        ))}
      </svg>
      <div className="mt-1 flex items-center justify-between font-mono text-[9px] text-mute">
        <span>{data.x} →</span>
        <span>↑ {data.y}</span>
      </div>
      {data.legend && (
        <div className="mt-3 flex flex-wrap items-center justify-center gap-4 text-[11px] text-mist">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#25d7f0" }} />
            {data.legend.low}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#fb7185" }} />
            {data.legend.high}
          </span>
        </div>
      )}
    </div>
  );
}

/** Line chart of an ordered breakdown/distribution. */
export function LineChart({ items, accent = "#25d7f0" }: { items: DistItem[]; accent?: string }) {
  if (items.length < 2) return null;
  const W = 300;
  const H = 190;
  const P = 30;
  const max = Math.max(...items.map((d) => d.value), 0.0001);
  const xs = (i: number) => P + (items.length > 1 ? i / (items.length - 1) : 0) * (W - P - 10);
  const ys = (v: number) => H - P - (v / max) * (H - P - 14);
  const line = items.map((d, i) => `${xs(i).toFixed(1)},${ys(d.value).toFixed(1)}`).join(" ");
  const area = `${xs(0)},${H - P} ${line} ${xs(items.length - 1)},${H - P}`;
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <line x1={P} y1={H - P} x2={W - 8} y2={H - P} stroke="rgba(255,255,255,0.15)" />
        <line x1={P} y1={8} x2={P} y2={H - P} stroke="rgba(255,255,255,0.15)" />
        <polygon points={area} fill={alpha(accent, 0.12)} />
        <polyline points={line} fill="none" stroke={accent} strokeWidth="2" />
        {items.map((d, i) => (
          <g key={i}>
            <circle cx={xs(i)} cy={ys(d.value)} r="3.5" fill={accent} />
            <text x={xs(i)} y={ys(d.value) - 7} fontSize="8" fill="#9fb0c9" textAnchor="middle">
              {d.display}
            </text>
          </g>
        ))}
      </svg>
      <div className="mt-1 flex gap-1">
        {items.map((d, i) => (
          <span key={i} className="flex-1 truncate text-center font-mono text-[8px] text-mute">
            {d.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Radar / spider chart of feature importance. */
export function Radar({ bars, accent = "#25d7f0" }: { bars: ResultBar[]; accent?: string }) {
  const items = bars.slice(0, 6);
  const n = items.length;
  if (n < 3) return <Bars bars={bars} accent={accent} />;
  const C = 120;
  const R = 88;
  const ang = (i: number) => (2 * Math.PI * i) / n - Math.PI / 2;
  const at = (i: number, rad: number): [number, number] => [
    +(C + rad * Math.cos(ang(i))).toFixed(1),
    +(C + rad * Math.sin(ang(i))).toFixed(1),
  ];
  const rings = [0.25, 0.5, 0.75, 1];
  const poly = items.map((b, i) => at(i, R * Math.max(0.05, b.value)).join(",")).join(" ");
  return (
    <svg viewBox="0 0 240 240" className="mx-auto h-60 w-full max-w-[300px]">
      {rings.map((r) => (
        <polygon
          key={r}
          points={items.map((_, i) => at(i, R * r).join(",")).join(" ")}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="1"
        />
      ))}
      {items.map((_, i) => {
        const [x, y] = at(i, R);
        return <line key={i} x1={C} y1={C} x2={x} y2={y} stroke="rgba(255,255,255,0.08)" />;
      })}
      <polygon points={poly} fill={alpha(accent, 0.25)} stroke={accent} strokeWidth="2" />
      {items.map((b, i) => {
        const [x, y] = at(i, R * Math.max(0.05, b.value));
        return <circle key={b.label} cx={x} cy={y} r="2.5" fill={accent} />;
      })}
      {items.map((b, i) => {
        const [lx, ly] = at(i, R + 16);
        return (
          <text
            key={b.label}
            x={lx}
            y={ly}
            fontSize="8"
            fill="#9fb0c9"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {b.label.length > 13 ? b.label.slice(0, 12) + "…" : b.label}
          </text>
        );
      })}
    </svg>
  );
}

/** Auto-generated, rule-based "smart insights" with severity colour. */
export function SmartInsights({ items }: { items: { text: string; kind: string }[] }) {
  const color = (k: string) => (k === "warn" ? "#fbbf24" : k === "good" ? "#9ae64a" : "#25d7f0");
  return (
    <ul className="space-y-2.5">
      {items.map((it, i) => (
        <li
          key={i}
          className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3"
        >
          <span
            className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
            style={{ background: color(it.kind), boxShadow: `0 0 8px ${alpha(color(it.kind), 0.7)}` }}
          />
          <span className="text-sm leading-relaxed text-mist">{it.text}</span>
        </li>
      ))}
    </ul>
  );
}

/** Per-column data dictionary table — works for any dataset. */
export function DataProfile({
  profile,
}: {
  profile: { name: string; type: string; missing: number; unique: number }[];
}) {
  const typeColor = (t: string) =>
    t === "target" ? "#fb7185"
      : t === "numeric" ? "#25d7f0"
      : t === "date" ? "#9ae64a"
      : t === "text" ? "#a78bfa"
      : "#fbbf24";
  return (
    <div className="scroll-thin max-h-72 overflow-auto">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-panel">
          <tr className="font-mono text-[10px] uppercase tracking-wider text-mute">
            <th className="py-2 pr-4">Column</th>
            <th className="py-2 pr-4">Type</th>
            <th className="py-2 pr-4">Missing</th>
            <th className="py-2">Unique</th>
          </tr>
        </thead>
        <tbody>
          {profile.map((p) => (
            <tr key={p.name} className="border-t border-white/5">
              <td className="max-w-[160px] truncate py-2 pr-4 text-mist">{p.name}</td>
              <td className="py-2 pr-4">
                <span
                  className="rounded px-1.5 py-0.5 font-mono text-[10px]"
                  style={{ color: typeColor(p.type), background: alpha(typeColor(p.type), 0.12) }}
                >
                  {p.type}
                </span>
              </td>
              <td className="py-2 pr-4 font-mono text-mute">{p.missing}%</td>
              <td className="py-2 font-mono text-mute">{p.unique}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Data-quality score gauge with components. */
export function QualityGauge({
  quality,
}: {
  quality: { score: number; missing: number; duplicates: number; constant_cols: number };
}) {
  const s = quality.score;
  const color = s >= 85 ? "#9ae64a" : s >= 60 ? "#fbbf24" : "#fb7185";
  const r = 34;
  const c = 2 * Math.PI * r;
  const off = c * (1 - s / 100);
  return (
    <div className="flex items-center gap-5">
      <div className="relative grid h-24 w-24 shrink-0 place-items-center">
        <svg viewBox="0 0 88 88" className="h-24 w-24 -rotate-90">
          <circle cx="44" cy="44" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="8" />
          <motion.circle
            cx="44"
            cy="44"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={c}
            initial={{ strokeDashoffset: c }}
            animate={{ strokeDashoffset: off }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <div className="absolute text-center">
          <div className="font-display text-xl font-semibold text-white">{s}</div>
          <div className="font-mono text-[8px] text-mute">/ 100</div>
        </div>
      </div>
      <div className="space-y-1.5 text-xs text-mute">
        <div>Missing values: <span className="text-mist">{quality.missing}%</span></div>
        <div>Duplicate rows: <span className="text-mist">{quality.duplicates}</span></div>
        <div>Constant columns: <span className="text-mist">{quality.constant_cols}</span></div>
      </div>
    </div>
  );
}

/** Horizontal box plots (min · q1 · median · q3 · max), shared scale. */
export function BoxPlot({
  data,
  accent = "#25d7f0",
}: {
  data: { feature: string; boxes: { label: string; min: number; q1: number; med: number; q3: number; max: number }[] };
  accent?: string;
}) {
  const all = data.boxes.flatMap((b) => [b.min, b.max]);
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const sc = (v: number) => (hi > lo ? ((v - lo) / (hi - lo)) * 100 : 50);
  const colors = [accent, "#fb7185", "#9ae64a", "#fbbf24"];
  return (
    <div className="space-y-4">
      {data.boxes.map((b, i) => {
        const col = colors[i % colors.length];
        return (
          <div key={b.label}>
            <div className="mb-1 flex justify-between text-[11px]">
              <span className="text-mist">{b.label}</span>
              <span className="font-mono text-mute">median {b.med.toFixed(0)}</span>
            </div>
            <div className="relative h-6">
              <div
                className="absolute top-1/2 h-px -translate-y-1/2 bg-white/25"
                style={{ left: `${sc(b.min)}%`, width: `${sc(b.max) - sc(b.min)}%` }}
              />
              <div
                className="absolute top-1/2 h-4 -translate-y-1/2 rounded"
                style={{
                  left: `${sc(b.q1)}%`,
                  width: `${Math.max(1, sc(b.q3) - sc(b.q1))}%`,
                  background: alpha(col, 0.3),
                  border: `1px solid ${col}`,
                }}
              />
              <div
                className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2"
                style={{ left: `${sc(b.med)}%`, background: col }}
              />
            </div>
          </div>
        );
      })}
      <div className="font-mono text-[9px] text-mute">
        range {lo.toFixed(0)} – {hi.toFixed(0)} · {data.feature}
      </div>
    </div>
  );
}

/** Cumulative feature-importance (Pareto) area + line. */
export function CumulativeArea({ bars, accent = "#25d7f0" }: { bars: ResultBar[]; accent?: string }) {
  const total = bars.reduce((s, b) => s + b.value, 0) || 1;
  let cum = 0;
  const pts = bars.map((b) => {
    cum += b.value / total;
    return { y: cum, label: b.label };
  });
  const W = 300;
  const H = 190;
  const P = 26;
  const xs = (i: number) => P + (pts.length > 1 ? i / (pts.length - 1) : 0) * (W - P - 10);
  const ys = (y: number) => H - P - y * (H - P - 12);
  const line = pts.map((p, i) => `${xs(i).toFixed(1)},${ys(p.y).toFixed(1)}`).join(" ");
  const area = `${xs(0)},${H - P} ${line} ${xs(pts.length - 1)},${H - P}`;
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <line x1={P} y1={H - P} x2={W - 8} y2={H - P} stroke="rgba(255,255,255,0.15)" />
        <line x1={P} y1={8} x2={P} y2={H - P} stroke="rgba(255,255,255,0.15)" />
        <line x1={P} y1={ys(0.8)} x2={W - 8} y2={ys(0.8)} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />
        <polygon points={area} fill={alpha(accent, 0.18)} />
        <polyline points={line} fill="none" stroke={accent} strokeWidth="2" />
        {pts.map((p, i) => (
          <circle key={i} cx={xs(i)} cy={ys(p.y)} r="3" fill={accent} />
        ))}
        <text x={W - 10} y={ys(0.8) - 4} fontSize="8" fill="#76859f" textAnchor="end">
          80%
        </text>
      </svg>
      <div className="mt-1 flex justify-between font-mono text-[9px] text-mute">
        <span>{pts[0]?.label}</span>
        <span>cumulative importance →</span>
      </div>
    </div>
  );
}

/** Correlation heatmap — a coloured grid of pairwise values. */
export function Heatmap({
  labels,
  matrix,
  accent = "#25d7f0",
}: {
  labels: string[];
  matrix: number[][];
  accent?: string;
}) {
  const n = labels.length;
  if (!n || !matrix.length) return null;
  const short = (s: string, k: number) => (s.length > k ? s.slice(0, k) + "…" : s);
  return (
    <div className="scroll-thin overflow-auto">
      <div
        className="inline-grid gap-0.5"
        style={{ gridTemplateColumns: `84px repeat(${n}, minmax(26px, 1fr))` }}
      >
        <div />
        {labels.map((l, i) => (
          <div
            key={i}
            title={l}
            className="truncate px-1 py-1 text-center font-mono text-[8px] text-mute"
          >
            {short(l, 6)}
          </div>
        ))}
        {matrix.map((row, ri) => (
          <Fragment key={ri}>
            <div
              title={labels[ri]}
              className="truncate py-1 pr-1 text-right font-mono text-[9px] text-mute"
            >
              {short(labels[ri], 11)}
            </div>
            {row.map((v, ci) => (
              <div
                key={ci}
                title={`${labels[ri]} ~ ${labels[ci]}: ${v}`}
                className="grid aspect-square place-items-center rounded-sm font-mono text-[8px]"
                style={{
                  background: alpha(accent, Math.max(0.05, Math.min(1, Math.abs(v)))),
                  color: Math.abs(v) > 0.6 ? "#06080f" : "#9fb0c9",
                }}
              >
                {v.toFixed(1)}
              </div>
            ))}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

/** The data behind a chart, as a compact scrollable table. */
export function ChartDataTable({ table }: { table: ChartTable }) {
  if (!table || !table.columns?.length) return null;
  return (
    <div className="scroll-thin max-h-60 overflow-auto rounded-lg border border-white/10 bg-white/[0.02]">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-panel">
          <tr className="font-mono text-[10px] uppercase tracking-wider text-mute">
            {table.columns.map((c, i) => (
              <th key={i} className={cn("px-3 py-2", c.align === "right" && "text-right")}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, ri) => (
            <tr key={ri} className="border-t border-white/5">
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className={cn(
                    "px-3 py-1.5",
                    table.columns[ci]?.align === "right"
                      ? "text-right font-mono text-mute"
                      : "text-mist",
                  )}
                >
                  {String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.caption && (
        <div className="px-3 py-1.5 font-mono text-[9px] text-mute">{table.caption}</div>
      )}
    </div>
  );
}

/** A short "how to read this" note for a chart. */
export function ChartNote({ text }: { text: string }) {
  if (!text) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
      <div className="mb-1 font-mono text-[9px] uppercase tracking-wider text-mute">
        How to read this
      </div>
      <p className="text-[12px] leading-relaxed text-mute">{text}</p>
    </div>
  );
}

/** Unified chart card: an LLM-chosen chart + its data table + an explanatory note.
 *  Every value comes from the engine; the dispatcher just picks the right primitive. */
export function ChartCard({
  card,
  accent = "#25d7f0",
}: {
  card: ChartCardData;
  accent?: string;
}) {
  const d = card.data ?? {};
  const items = d.items ?? [];
  let chart: ReactNode;
  switch (card.type) {
    case "bar":
      chart = <Bars bars={items as ResultBar[]} accent={accent} />;
      break;
    case "column":
      chart = <DistBars items={items as DistItem[]} accent={accent} />;
      break;
    case "pie":
      chart = <Pie items={items.map((x) => ({ label: x.label, value: x.value }))} accent={accent} />;
      break;
    case "line":
      chart = <LineChart items={items as DistItem[]} accent={accent} />;
      break;
    case "area":
      chart = <CumulativeArea bars={items as ResultBar[]} accent={accent} />;
      break;
    case "radar":
      chart = <Radar bars={items as ResultBar[]} accent={accent} />;
      break;
    case "histogram":
      chart = <Histogram bins={d.bins ?? []} accent={accent} />;
      break;
    case "scatter":
      chart =
        d.x && d.y && d.points ? (
          <Scatter data={{ x: d.x, y: d.y, points: d.points, legend: d.legend }} />
        ) : null;
      break;
    case "box":
      chart =
        d.feature && d.boxes ? (
          <BoxPlot data={{ feature: d.feature, boxes: d.boxes }} accent={accent} />
        ) : null;
      break;
    case "heatmap":
      chart = <Heatmap labels={d.labels ?? []} matrix={d.matrix ?? []} accent={accent} />;
      break;
    case "statcards":
      chart = <StatCards stats={items.map((x) => ({ label: x.label, value: String(x.display ?? x.value) }))} />;
      break;
    default:
      chart = <Bars bars={items as ResultBar[]} accent={accent} />;
  }
  const ax = card.axes ?? {};
  return (
    <div className="rounded-2xl border border-white/10 bg-panel p-5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-mute">{card.title}</h3>
        <span
          className="shrink-0 rounded-full px-2 py-0.5 font-mono text-[9px]"
          style={{ color: accent, background: alpha(accent, 0.14) }}
        >
          {card.type}
        </span>
      </div>
      <div className="mt-4 grid gap-5 lg:grid-cols-[1.45fr_1fr]">
        <div className="min-w-0">
          {chart}
          {(ax.x || ax.y) && (
            <div className="mt-2 flex justify-between font-mono text-[9px] text-mute">
              <span>{ax.x ? `x · ${ax.x}` : ""}</span>
              <span>{ax.y ? `y · ${ax.y}` : ""}</span>
            </div>
          )}
        </div>
        <div className="space-y-3">
          <ChartDataTable table={card.table} />
          <ChartNote text={card.note} />
        </div>
      </div>
    </div>
  );
}
