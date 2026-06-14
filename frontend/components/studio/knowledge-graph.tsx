/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import type { RunResults } from "@/lib/studio-run";
import { fmt } from "@/lib/utils";

/**
 * Helix Knowledge Graph — a force-directed 3D map of the WHOLE analysis:
 * the target at the core, with Dataset / Drivers / Segments / Metrics / Charts /
 * Quality / Features hubs orbiting it, each expanding into real nodes. Drag to
 * orbit, hover for names, click any node for a detail panel, or search to light
 * up matches. Inspired by the portfolio Neural Map.
 */

type Detail = {
  title: string;
  kind: string;
  description: string;
  stats?: [string, string][];
  badges?: string[];
  accent?: string;
};
type GNode = { id: string; name: string; group: string; val: number; isHub?: boolean; color: string; detail: Detail };
type GLink = { source: string; target: string; kind: string; value: number; color: string };

const GROUP_COLOR: Record<string, string> = {
  root: "#ffffff",
  dataset: "#22d3ee",
  driverUp: "#25d7f0",
  driverDown: "#fb7185",
  drivers: "#7dd3fc",
  segments: "#f59e0b",
  metrics: "#34d399",
  charts: "#a78bfa",
  quality: "#9ae64a",
  features: "#818cf8",
};
const VERDICT_COLOR: Record<string, string> = {
  excellent: "#9ae64a",
  good: "#22d3ee",
  fair: "#fbbf24",
  weak: "#fb7185",
};
const LEGEND: [string, string][] = [
  ["target", "#ffffff"],
  ["dataset", "#22d3ee"],
  ["driver ↑", "#25d7f0"],
  ["driver ↓", "#fb7185"],
  ["segment", "#f59e0b"],
  ["metric", "#34d399"],
  ["chart", "#a78bfa"],
  ["feature", "#818cf8"],
];

function buildGraph(r: RunResults): { nodes: GNode[]; links: GLink[] } {
  const nodes: GNode[] = [];
  const links: GLink[] = [];
  const tgt = r._target && r._target !== "(unsupervised)" ? r._target : "Analysis";
  const push = (n: Omit<GNode, "color"> & { color?: string }) => {
    nodes.push({ ...n, color: n.color ?? GROUP_COLOR[n.group] ?? "#7dd3fc" });
  };
  const link = (source: string, target: string, kind: string, value = 0.5) => {
    const col = kind === "hub" ? "rgba(125,211,252,0.5)" : "rgba(125,211,252,0.28)";
    links.push({ source, target, kind, value, color: col });
  };

  // core
  push({
    id: "__root__", name: tgt, group: "root", val: 26, isHub: true,
    detail: {
      title: tgt, kind: "target",
      description: `${r.taskLabel} · best model ${r.bestModel} · ${r.headline.label} ${r.headline.value}. Every hub below expands a part of this analysis.`,
      badges: [r.taskLabel, `best · ${r.bestModel}`],
    },
  });

  const hub = (id: string, name: string, group: string, desc: string) => {
    push({ id, name, group, val: 15, isHub: true, detail: { title: name, kind: "section", description: desc } });
    link("__root__", id, "hub", 1);
    return id;
  };

  // DATASET
  const dh = hub("hub_dataset", "Dataset", "dataset", "What the model was trained on.");
  const dataItems: [string, string, string][] = [
    ["d_rows", `${fmt(r._rows ?? 0)} rows`, r._source_rows && r._source_rows !== r._rows ? `Trained on ${fmt(r._rows ?? 0)} of ${fmt(r._source_rows)} source rows (sampled for speed).` : `${fmt(r._rows ?? 0)} rows analysed.`],
    ["d_cols", `${r._cols ?? "?"} columns`, `${r._cols ?? "?"} columns; ${r._features?.length ?? "?"} features used after cleaning.`],
    ["d_task", r.taskLabel, `Detected task type: ${r.taskLabel}.`],
    ["d_model", r.bestModel, `Best model selected by FLAML AutoML: ${r.bestModel}.`],
  ];
  dataItems.forEach(([id, name, description]) => {
    push({ id, name, group: "dataset", val: 7, detail: { title: name, kind: "dataset", description } });
    link(dh, id, "sub");
  });

  // DRIVERS
  if (r.bars?.length) {
    const drh = hub("hub_drivers", "Drivers", "drivers", "Features that move the prediction most.");
    r.bars.slice(0, 7).forEach((b, i) => {
      const up = (b.sign ?? 1) >= 0;
      const id = `drv_${i}`;
      push({
        id, name: b.label, group: up ? "driverUp" : "driverDown", val: 6 + b.value * 14,
        detail: {
          title: b.label, kind: "driver",
          description: `${b.label} ${up ? "raises" : "lowers"} ${tgt}. Relative importance ${b.value.toFixed(2)} (1.00 = strongest driver).`,
          stats: [["importance", b.value.toFixed(2)], ["effect", up ? "↑ raises" : "↓ lowers"]],
        },
      });
      link(drh, id, "sub", b.value);
    });
  }

  // SEGMENTS
  if (r.dist?.length) {
    const sh = hub("hub_segments", "Segments", "segments", r.distTitle || "Breakdown across groups.");
    r.dist.slice(0, 7).forEach((d, i) => {
      const id = `seg_${i}`;
      push({
        id, name: String(d.label), group: "segments", val: 6 + d.value * 10,
        detail: { title: String(d.label), kind: "segment", description: `${r.distTitle}: ${d.label} = ${d.display}.`, stats: [["value", d.display]] },
      });
      link(sh, id, "sub", d.value);
    });
  }

  // METRICS
  if (r.metrics?.length) {
    const mh = hub("hub_metrics", "Metrics", "metrics", "Held-out test-set performance.");
    r.metrics.forEach((m, i) => {
      const id = `met_${i}`;
      push({ id, name: `${m.label} ${m.value}`, group: "metrics", val: 7, detail: { title: m.label, kind: "metric", description: `${m.label} on the held-out test set: ${m.value}.`, stats: [[m.label, m.value]] } });
      link(mh, id, "sub");
    });
  }

  // CHARTS (depict the rest of the dashboard)
  if (r._charts?.length) {
    const ch = hub("hub_charts", "Charts", "charts", "Every visual in the report.");
    r._charts.slice(0, 9).forEach((c, i) => {
      const id = `cht_${i}`;
      push({ id, name: c.title, group: "charts", val: 7, detail: { title: c.title, kind: `${c.type} chart`, description: c.note || `A ${c.type} chart in the report.` } });
      link(ch, id, "sub");
    });
  }

  // QUALITY
  if (r._verdict) {
    const qcol = VERDICT_COLOR[r._verdict.level] ?? "#9ae64a";
    push({ id: "hub_quality", name: "Model quality", group: "quality", val: 15, isHub: true, color: qcol, detail: { title: `Model quality · ${r._verdict.label}`, kind: "verdict", description: r._verdict.detail, accent: qcol } });
    link("__root__", "hub_quality", "hub", 1);
    if (r._quality) {
      push({ id: "q_score", name: `Data quality ${r._quality.score}/100`, group: "quality", val: 8, color: qcol, detail: { title: "Data quality", kind: "quality", description: `Score ${r._quality.score}/100 · ${r._quality.missing}% missing · ${r._quality.duplicates} duplicate rows.`, stats: [["score", `${r._quality.score}/100`], ["missing", `${r._quality.missing}%`]] } });
      link("hub_quality", "q_score", "sub");
    }
  }

  // FEATURES (top profile columns)
  if (r._profile?.length) {
    const fh = hub("hub_features", "Columns", "features", "Columns in your dataset.");
    r._profile.slice(0, 8).forEach((p, i) => {
      const id = `feat_${i}`;
      push({ id, name: p.name, group: "features", val: 5.5, detail: { title: p.name, kind: `${p.type} column`, description: `${p.name}: ${p.type} · ${p.missing}% missing · ${p.unique} unique values.`, stats: [["type", p.type], ["missing", `${p.missing}%`], ["unique", String(p.unique)]] } });
      link(fh, id, "sub");
    });
  }

  return { nodes, links };
}

export function KnowledgeGraph3D({ results, accent = "#22d3ee" }: { results: RunResults; accent?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [selected, setSelected] = useState<GNode | null>(null);
  const [query, setQuery] = useState("");
  const { nodes, links } = useMemo(() => buildGraph(results), [results]);

  // keep the latest highlight set + select handler reachable from the imperative graph
  const selectRef = useRef(setSelected);
  selectRef.current = setSelected;
  const highlight = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return null;
    return new Set(nodes.filter((n) => n.name.toLowerCase().includes(q) || n.detail.kind.toLowerCase().includes(q)).map((n) => n.id));
  }, [query, nodes]);
  const hlRef = useRef<Set<string> | null>(null);
  hlRef.current = highlight;
  const fgRef = useRef<any>(null);

  useEffect(() => {
    let fg: any;
    let cancelled = false;
    let onResize: (() => void) | null = null;
    let rotTimer: ReturnType<typeof setInterval> | null = null;
    let stopAuto: (() => void) | null = null;
    const el = ref.current;
    if (!el) return;

    (async () => {
      const fgMod = await import("3d-force-graph");
      const stMod = await import("three-spritetext");
      if (cancelled || !ref.current) return;
      const ForceGraph3D: any = fgMod.default;
      const SpriteText: any = stMod.default;

      const nodeColor = (n: any) => {
        const hl = hlRef.current;
        if (hl && hl.size) return hl.has(n.id) ? "#34d399" : "#243049";
        return n.color;
      };

      fg = ForceGraph3D()(ref.current)
        .backgroundColor("rgba(0,0,0,0)")
        .graphData({ nodes, links })
        .nodeRelSize(4)
        .nodeVal("val")
        .nodeColor(nodeColor)
        .nodeOpacity(0.92)
        .nodeLabel((n: any) => `<div style="font:600 11px Inter,sans-serif;color:#dbe7f5;background:rgba(6,10,18,.9);border:1px solid rgba(125,211,252,.35);padding:3px 7px;border-radius:6px">${n.name}</div>`)
        .enableNodeDrag(false)
        .onNodeClick((n: any) => selectRef.current(n?.detail ? n : null))
        .nodeThreeObjectExtend(true)
        .nodeThreeObject((node: any) => {
          if (!node.isHub) return null; // hubs labelled always; others via hover
          const s: any = new SpriteText(node.name);
          s.color = node.id === "__root__" ? "#ffffff" : node.color;
          s.textHeight = node.id === "__root__" ? 7 : 5.5;
          s.fontFace = "Inter, system-ui, sans-serif";
          s.fontWeight = "700";
          try { s.material.depthWrite = false; } catch { /* ignore */ }
          s.position.y = node.id === "__root__" ? 16 : 12;
          return s;
        })
        .linkColor((l: any) => l.color)
        .linkWidth((l: any) => (l.kind === "hub" ? 0.8 : 0.4 + (l.value || 0) * 1.6))
        .linkOpacity(0.5)
        .linkDirectionalParticles((l: any) => (l.kind === "hub" ? 2 : 1))
        .linkDirectionalParticleWidth(1.4)
        .linkDirectionalParticleSpeed(0.006)
        .width(ref.current.clientWidth || ref.current.parentElement?.clientWidth || 640)
        .height(ref.current.clientHeight || 480)
        .cooldownTime(8000)
        .showNavInfo(false);

      fgRef.current = fg;

      // spread the layout out a little so hubs don't clump
      try {
        fg.d3Force("charge").strength(-130);
        fg.d3Force("link").distance((l: any) => (l.kind === "hub" ? 70 : 34));
      } catch { /* ignore */ }

      let theta = 0;
      let auto = true;
      let ticks = 0;
      const radius = 320;
      fg.cameraPosition({ x: 0, y: 30, z: radius });
      const settle = () => {
        if (rotTimer) { clearInterval(rotTimer); rotTimer = null; }
        try { fg.pauseAnimation(); } catch { /* ignore */ }
      };
      // resume the render loop on interaction so drag/zoom stay smooth
      stopAuto = () => {
        auto = false;
        if (rotTimer) { clearInterval(rotTimer); rotTimer = null; }
        try { fg.resumeAnimation(); } catch { /* ignore */ }
      };
      el.addEventListener("pointerdown", stopAuto);
      el.addEventListener("wheel", stopAuto, { passive: true });
      // gentle auto-rotate for ~11s, then PAUSE rendering — a continuously
      // rendering WebGL canvas otherwise pins the main thread forever.
      rotTimer = setInterval(() => {
        if (!fg || !auto) return;
        theta += 0.0036;
        ticks += 1;
        try {
          fg.cameraPosition({ x: radius * Math.sin(theta), y: 30, z: radius * Math.cos(theta) }, undefined, 0);
        } catch { /* ignore */ }
        if (ticks > 220) { auto = false; settle(); }
      }, 50);

      onResize = () => { if (ref.current && fg) fg.width(ref.current.clientWidth); };
      window.addEventListener("resize", onResize);
    })();

    return () => {
      cancelled = true;
      fgRef.current = null;
      if (rotTimer) clearInterval(rotTimer);
      if (onResize) window.removeEventListener("resize", onResize);
      if (stopAuto && el) {
        el.removeEventListener("pointerdown", stopAuto);
        el.removeEventListener("wheel", stopAuto);
      }
      if (fg) { try { fg._destructor?.(); } catch { /* ignore */ } }
      if (el) el.innerHTML = "";
    };
  }, [nodes, links]);

  // re-apply colors when the search highlight changes
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    try {
      fg.nodeColor((n: any) => {
        const hl = hlRef.current;
        if (hl && hl.size) return hl.has(n.id) ? "#34d399" : "#243049";
        return n.color;
      });
    } catch { /* ignore */ }
  }, [highlight]);

  return (
    <div>
      {/* search / light-it-up */}
      <div className="mb-3 flex items-center gap-2 rounded-xl border border-white/10 bg-ink/70 px-3">
        <Search className="h-4 w-4 shrink-0 text-mute" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Search the map — try a driver, "metric", "chart"…'
          className="flex-1 bg-transparent py-2.5 text-sm text-mist outline-none placeholder:text-mute"
        />
        {query && (
          <button onClick={() => setQuery("")} className="p-1 text-mute hover:text-mist" aria-label="Clear">
            <X className="h-3.5 w-3.5" />
          </button>
        )}
        {highlight && (
          <span className="shrink-0 font-mono text-[10px] text-acid">{highlight.size} lit</span>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        {/* canvas */}
        <div className="relative h-[480px] overflow-hidden rounded-2xl border border-white/10 bg-[#060912]">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(34,211,238,0.6) 1px,transparent 1px),linear-gradient(90deg,rgba(34,211,238,0.6) 1px,transparent 1px)",
              backgroundSize: "44px 44px",
            }}
          />
          <div
            className="pointer-events-none absolute left-1/2 top-1/2 h-[320px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{ background: "radial-gradient(circle, rgba(34,211,238,0.16), transparent 70%)" }}
          />
          <div ref={ref} className="absolute inset-0" />
          {/* legend */}
          <div className="pointer-events-none absolute bottom-3 left-3 right-3 flex flex-wrap gap-1.5">
            {LEGEND.map(([label, color]) => (
              <span key={label} className="flex items-center gap-1 rounded bg-black/55 px-2 py-0.5 font-mono text-[9px] text-mute backdrop-blur-sm">
                <span className="h-2 w-2 rounded-full" style={{ background: color }} />
                {label}
              </span>
            ))}
          </div>
          <div className="pointer-events-none absolute right-3 top-3 rounded bg-black/55 px-2 py-1 font-mono text-[9px] text-mute backdrop-blur-sm">
            drag · scroll · click a node
          </div>
        </div>

        {/* detail side panel */}
        <div className="space-y-3">
          {selected ? (
            <div className="rounded-2xl border bg-panel p-5" style={{ borderColor: `${selected.detail.accent ?? selected.color}55` }}>
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-display text-base font-semibold leading-snug text-white">{selected.detail.title}</h4>
                <button onClick={() => setSelected(null)} className="p-1 text-mute hover:text-mist" aria-label="Close">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <span
                className="mt-2 inline-block rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider"
                style={{ color: selected.detail.accent ?? selected.color, background: `${selected.detail.accent ?? selected.color}22` }}
              >
                {selected.detail.kind}
              </span>
              <p className="mt-3 text-[13px] leading-relaxed text-mute">{selected.detail.description}</p>
              {selected.detail.stats && selected.detail.stats.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {selected.detail.stats.map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between border-t border-white/5 pt-1.5 text-xs">
                      <span className="font-mono text-[10px] uppercase tracking-wider text-mute">{k}</span>
                      <span className="text-mist">{v}</span>
                    </div>
                  ))}
                </div>
              )}
              {selected.detail.badges && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {selected.detail.badges.map((b) => (
                    <span key={b} className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-mist">{b}</span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-2xl border border-white/10 bg-panel p-5">
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-mute">Knowledge graph</div>
              <p className="text-[13px] leading-relaxed text-mute">
                The whole analysis as one map — <span className="text-mist">{results._target && results._target !== "(unsupervised)" ? results._target : "your target"}</span> at
                the core, with Dataset, Drivers, Segments, Metrics, Charts, Quality and Columns orbiting it.
              </p>
              <p className="mt-3 text-[13px] leading-relaxed text-mute">
                <span className="text-white">Drag</span> to orbit · <span className="text-white">hover</span> for names · <span className="text-white">click</span> any node for details · <span className="text-white">search</span> to light up matches.
              </p>
              <div className="mt-4 grid grid-cols-2 gap-2">
                {[
                  ["Nodes", String(nodes.length)],
                  ["Drivers", String(results.bars?.length ?? 0)],
                  ["Charts", String(results._charts?.length ?? 0)],
                  ["Segments", String(results.dist?.length ?? 0)],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
                    <div className="font-display text-lg font-semibold text-white">{v}</div>
                    <div className="font-mono text-[9px] uppercase tracking-wider text-mute">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
