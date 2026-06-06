import { Check, Loader2, FileSpreadsheet, CornerDownLeft } from "lucide-react";
import { AGENTS } from "@/lib/agents";
import { alpha } from "@/lib/utils";

type Status = "done" | "active" | "queued";

const STATUS: Record<string, Status> = {
  planner: "done",
  coder: "done",
  executor: "done",
  critic: "done",
  automl: "done",
  explainer: "active",
  reporter: "queued",
};

const FEATURES = [
  { label: "Top driver", value: 0.92, color: "#fb7185" },
  { label: "2nd driver", value: 0.78, color: "#25d7f0" },
  { label: "3rd driver", value: 0.64, color: "#a78bfa" },
  { label: "4th driver", value: 0.41, color: "#9ae64a" },
];

function Donut({ value }: { value: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const off = c * (1 - value);
  return (
    <div className="relative grid h-24 w-24 place-items-center">
      <svg viewBox="0 0 80 80" className="h-24 w-24 -rotate-90">
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="7"
        />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke="url(#donutG)"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
        />
        <defs>
          <linearGradient id="donutG" x1="0" y1="0" x2="80" y2="80">
            <stop offset="0" stopColor="#25d7f0" />
            <stop offset="1" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute text-center">
        <div className="font-display text-xl font-semibold text-white">84%</div>
        <div className="font-mono text-[9px] uppercase tracking-wider text-mute">
          ROC-AUC
        </div>
      </div>
    </div>
  );
}

export function HeroPreview() {
  return (
    <div className="glass relative overflow-hidden rounded-[26px] p-2 shadow-[0_40px_120px_-40px_rgba(37,215,240,0.35)]">
      {/* scanline */}
      <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden rounded-[26px]">
        <div className="animate-scan h-1/3 w-full bg-gradient-to-b from-transparent via-brand/[0.06] to-transparent" />
      </div>

      <div className="relative rounded-[20px] border border-white/10 bg-ink/80">
        {/* window bar */}
        <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
          <div className="flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-coral/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-gold/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-acid/80" />
          </div>
          <div className="flex-1 text-center font-mono text-xs text-mute">
            helix · studio
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-acid/30 bg-acid/10 px-2.5 py-1 font-mono text-[10px] text-acid">
            <span className="h-1.5 w-1.5 animate-glow rounded-full bg-acid" />
            running
          </span>
        </div>

        <div className="grid gap-px bg-white/5 md:grid-cols-12">
          {/* Objective */}
          <div className="bg-ink/90 p-4 md:col-span-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              Objective
            </div>
            <div className="mt-3 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-mist">
              <FileSpreadsheet className="h-3.5 w-3.5 text-brand" />
              your_data.csv
              <span className="font-mono text-[10px] text-mute">12,480×24</span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-mist">
              “Predict the outcome and explain the key drivers behind it.”
            </p>
            <div className="mt-4 inline-flex items-center gap-2 rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-[#04060f]">
              Run analysis
              <CornerDownLeft className="h-3.5 w-3.5" />
            </div>
          </div>

          {/* Agents */}
          <div className="bg-ink/90 p-4 md:col-span-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              Agents
            </div>
            <ul className="mt-3 space-y-2">
              {AGENTS.map((a) => {
                const s = STATUS[a.id];
                const Icon = a.icon;
                return (
                  <li key={a.id} className="flex items-center gap-2.5">
                    <span
                      className="grid h-6 w-6 place-items-center rounded-md border"
                      style={{
                        borderColor: alpha(a.accent, 0.3),
                        background: alpha(a.accent, 0.1),
                      }}
                    >
                      <Icon className="h-3 w-3" style={{ color: a.accent }} />
                    </span>
                    <span className="flex-1 text-xs text-mist">{a.name}</span>
                    {a.id === "critic" && (
                      <span className="rounded-full bg-gold/15 px-1.5 py-0.5 font-mono text-[9px] text-gold">
                        +1 fix
                      </span>
                    )}
                    {s === "done" && (
                      <Check className="h-3.5 w-3.5 text-acid" />
                    )}
                    {s === "active" && (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-brand" />
                    )}
                    {s === "queued" && (
                      <span className="h-1.5 w-1.5 rounded-full bg-mute/50" />
                    )}
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Result */}
          <div className="bg-ink/90 p-4 md:col-span-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
              Result
            </div>
            <div className="mt-2 flex items-center gap-3">
              <Donut value={0.84} />
              <div className="space-y-1">
                <div className="font-mono text-[10px] uppercase tracking-wider text-mute">
                  best model
                </div>
                <div className="text-sm font-semibold text-white">LightGBM</div>
                <div className="font-mono text-[10px] text-acid">
                  ✓ FLAML · 12 trials
                </div>
              </div>
            </div>
            <div className="mt-3 space-y-2">
              <div className="font-mono text-[10px] uppercase tracking-wider text-mute">
                SHAP drivers
              </div>
              {FEATURES.map((f) => (
                <div key={f.label} className="flex items-center gap-2">
                  <span className="w-24 truncate text-[11px] text-mist">
                    {f.label}
                  </span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                    <span
                      className="block h-full rounded-full"
                      style={{
                        width: `${f.value * 100}%`,
                        background: `linear-gradient(90deg, ${alpha(
                          f.color,
                          0.5,
                        )}, ${f.color})`,
                      }}
                    />
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
