/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useRef } from "react";
import type { ResultBar } from "@/lib/studio-run";

/**
 * 3D force-directed knowledge graph. Uses the backend's rich `graph`
 * (target + drivers + driver↔driver correlations + segment nodes) when present,
 * else a target→drivers star from `bars`. Nodes: white = target, cyan/coral =
 * driver (raises/lowers), gold = segment. Links: cyan/coral = drives, purple =
 * correlation, gold = segment. Uses the stable default (trackball) controls plus
 * a gentle manual auto-rotate that yields the moment you interact.
 */
export function KnowledgeGraph3D({
  bars,
  target,
  taskLabel,
  graph,
}: {
  bars: ResultBar[];
  target: string;
  taskLabel: string;
  graph?: { nodes: any[]; links: any[] } | null;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let fg: any;
    let cancelled = false;
    let onResize: (() => void) | null = null;
    let rotTimer: ReturnType<typeof setInterval> | null = null;
    let stopAuto: (() => void) | null = null;
    const el = ref.current;
    if (!el) return;

    const groupColor = (g: string, sign = 1) =>
      g === "target" ? "#ffffff" : g === "segment" ? "#fbbf24" : sign >= 0 ? "#25d7f0" : "#fb7185";
    const linkColor = (k: string, sign = 1) =>
      k === "corr" ? "#a78bfa" : k === "segment" ? "#fbbf24" : sign >= 0 ? "#25d7f0" : "#fb7185";

    (async () => {
      const fgMod = await import("3d-force-graph");
      const stMod = await import("three-spritetext");
      if (cancelled || !ref.current) return;
      const ForceGraph3D: any = fgMod.default;
      const SpriteText: any = stMod.default;

      const tgt = target && target !== "(unsupervised)" ? target : "outcome";
      let nodes: any[];
      let links: any[];
      if (graph && Array.isArray(graph.nodes) && graph.nodes.length) {
        nodes = graph.nodes.map((nd: any) => ({ ...nd, color: groupColor(nd.group, nd.sign ?? 1) }));
        links = (graph.links || []).map((l: any) => ({ ...l, color: linkColor(l.kind, l.sign ?? 1) }));
      } else {
        nodes = [
          { id: "__target__", name: tgt, group: "target", val: 20, color: "#ffffff" },
          ...bars.map((b) => ({
            id: b.label,
            name: b.label,
            group: "driver",
            val: 6 + b.value * 16,
            sign: b.sign ?? 1,
            color: (b.sign ?? 1) >= 0 ? "#25d7f0" : "#fb7185",
          })),
        ];
        links = bars.map((b) => ({
          source: "__target__",
          target: b.label,
          value: b.value,
          kind: "drives",
          color: (b.sign ?? 1) >= 0 ? "#25d7f0" : "#fb7185",
        }));
      }

      fg = ForceGraph3D()(ref.current)
        .backgroundColor("rgba(0,0,0,0)")
        .graphData({ nodes, links })
        .nodeRelSize(4)
        .nodeVal("val")
        .nodeColor("color")
        .nodeOpacity(0.9)
        .enableNodeDrag(false)
        .nodeThreeObjectExtend(true)
        .nodeThreeObject((node: any) => {
          const s: any = new SpriteText(node.name);
          s.color = node.group === "target" ? "#ffffff" : node.color;
          s.textHeight = node.group === "target" ? 7 : node.group === "segment" ? 4 : 5;
          s.fontFace = "Inter, system-ui, sans-serif";
          try {
            s.material.depthWrite = false;
          } catch {
            /* ignore */
          }
          s.position.y = node.group === "target" ? 16 : 10;
          return s;
        })
        .linkColor((l: any) => l.color)
        .linkWidth((l: any) => 0.4 + (l.value || 0) * 2.5)
        .linkOpacity(0.4)
        .linkDirectionalParticles((l: any) => (l.kind === "corr" ? 0 : 2))
        .linkDirectionalParticleWidth((l: any) => 1 + (l.value || 0) * 2)
        .linkDirectionalParticleSpeed((l: any) => 0.004 + (l.value || 0) * 0.01)
        .width(ref.current.clientWidth)
        .height(380)
        .showNavInfo(false);

      // gentle manual auto-rotate that stops as soon as the user interacts
      let theta = 0;
      let auto = true;
      const radius = 250;
      fg.cameraPosition({ x: 0, y: 40, z: radius });
      stopAuto = () => {
        auto = false;
      };
      el.addEventListener("pointerdown", stopAuto);
      el.addEventListener("wheel", stopAuto, { passive: true });
      rotTimer = setInterval(() => {
        if (!fg || !auto) return;
        theta += 0.004;
        try {
          fg.cameraPosition({ x: radius * Math.sin(theta), y: 40, z: radius * Math.cos(theta) }, undefined, 0);
        } catch {
          /* ignore */
        }
      }, 50);

      onResize = () => {
        if (ref.current && fg) fg.width(ref.current.clientWidth);
      };
      window.addEventListener("resize", onResize);
    })();

    return () => {
      cancelled = true;
      if (rotTimer) clearInterval(rotTimer);
      if (onResize) window.removeEventListener("resize", onResize);
      if (stopAuto && el) {
        el.removeEventListener("pointerdown", stopAuto);
        el.removeEventListener("wheel", stopAuto);
      }
      if (fg) {
        try {
          fg._destructor?.();
        } catch {
          /* ignore */
        }
      }
      if (el) el.innerHTML = "";
    };
  }, [bars, target, taskLabel, graph]);

  return (
    <div
      ref={ref}
      className="h-[380px] w-full overflow-hidden rounded-xl border border-white/10 bg-[#070a12]"
    />
  );
}
