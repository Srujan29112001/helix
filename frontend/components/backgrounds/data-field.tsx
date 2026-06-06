"use client";

import { useEffect, useRef } from "react";

interface DataFieldProps {
  className?: string;
  interactive?: boolean;
  /** Visual density multiplier (1 = default). */
  density?: number;
  colorA?: string;
  colorB?: string;
}

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

interface Packet {
  from: number;
  to: number;
  t: number;
  speed: number;
  hue: number;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

/**
 * Living network of data points: nodes drift, link when close, and
 * luminous packets stream along the connections. The core visual motif.
 */
export function DataField({
  className,
  interactive = true,
  density = 1,
  colorA = "#25d7f0",
  colorB = "#8b5cf6",
}: DataFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const rgbA = hexToRgb(colorA);
    const rgbB = hexToRgb(colorB);
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let nodes: Node[] = [];
    let packets: Packet[] = [];
    const mouse = { x: -9999, y: -9999, active: false };
    let raf = 0;
    let running = true;
    const maxDist = 150;

    const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
    const mix = (t: number) =>
      `${Math.round(lerp(rgbA[0], rgbB[0], t))},${Math.round(
        lerp(rgbA[1], rgbB[1], t),
      )},${Math.round(lerp(rgbA[2], rgbB[2], t))}`;

    const nearestNeighbor = (i: number, exclude: number) => {
      let best = -1;
      let bestD = Infinity;
      for (let j = 0; j < nodes.length; j++) {
        if (j === i || j === exclude) continue;
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const d = dx * dx + dy * dy;
        if (d < bestD) {
          bestD = d;
          best = j;
        }
      }
      return best;
    };

    const build = () => {
      const area = width * height;
      const count = Math.max(
        24,
        Math.min(96, Math.round((area / 15000) * density)),
      );
      nodes = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.22,
        r: Math.random() * 1.6 + 0.7,
      }));
      const pCount = Math.max(8, Math.round(count * 0.22));
      packets = Array.from({ length: pCount }, () => {
        const from = Math.floor(Math.random() * count);
        return {
          from,
          to: nearestNeighbor(from, -1),
          t: Math.random(),
          speed: Math.random() * 0.006 + 0.004,
          hue: Math.random(),
        };
      });
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      build();
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";

      // advance + draw nodes
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        if (!reduced) {
          n.x += n.vx;
          n.y += n.vy;
        }
        if (n.x < 0 || n.x > width) n.vx *= -1;
        if (n.y < 0 || n.y > height) n.vy *= -1;
        n.x = Math.max(0, Math.min(width, n.x));
        n.y = Math.max(0, Math.min(height, n.y));

        // mouse repulsion
        if (interactive && mouse.active) {
          const dx = n.x - mouse.x;
          const dy = n.y - mouse.y;
          const d = Math.hypot(dx, dy);
          if (d < 130 && d > 0.01) {
            const f = (1 - d / 130) * 0.6;
            n.x += (dx / d) * f;
            n.y += (dy / d) * f;
          }
        }

        const t = n.y / height;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${mix(t)},0.85)`;
        ctx.fill();
      }

      // connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.hypot(dx, dy);
          if (dist < maxDist) {
            const a = (1 - dist / maxDist) * 0.32;
            const t = (nodes[i].y + nodes[j].y) / (2 * height);
            ctx.strokeStyle = `rgba(${mix(t)},${a})`;
            ctx.lineWidth = 0.7;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // mouse links
      if (interactive && mouse.active) {
        for (let i = 0; i < nodes.length; i++) {
          const dx = nodes[i].x - mouse.x;
          const dy = nodes[i].y - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 180) {
            ctx.strokeStyle = `rgba(${mix(0.3)},${(1 - dist / 180) * 0.4})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.stroke();
          }
        }
      }

      // flowing packets
      for (const p of packets) {
        const a = nodes[p.from];
        const b = nodes[p.to];
        if (!a || !b) {
          p.from = Math.floor(Math.random() * nodes.length);
          p.to = nearestNeighbor(p.from, -1);
          p.t = 0;
          continue;
        }
        if (!reduced) p.t += p.speed;
        if (p.t >= 1) {
          p.t = 0;
          p.from = p.to;
          p.to = nearestNeighbor(p.from, p.from);
        }
        const x = lerp(a.x, b.x, p.t);
        const y = lerp(a.y, b.y, p.t);
        const grad = ctx.createRadialGradient(x, y, 0, x, y, 7);
        grad.addColorStop(0, `rgba(${mix(p.hue)},0.95)`);
        grad.addColorStop(1, `rgba(${mix(p.hue)},0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, 7, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalCompositeOperation = "source-over";
    };

    const loop = () => {
      if (running) draw();
      raf = requestAnimationFrame(loop);
    };

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
      mouse.active = true;
    };
    const onLeave = () => {
      mouse.active = false;
      mouse.x = -9999;
      mouse.y = -9999;
    };

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();
    loop();

    const io = new IntersectionObserver(
      ([entry]) => {
        running = entry.isIntersecting;
      },
      { threshold: 0 },
    );
    io.observe(canvas);

    const onVisibility = () => {
      running = !document.hidden;
    };
    document.addEventListener("visibilitychange", onVisibility);
    if (interactive) {
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseout", onLeave);
    }

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseout", onLeave);
    };
  }, [interactive, density, colorA, colorB]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={className}
      style={{ width: "100%", height: "100%", display: "block" }}
    />
  );
}
