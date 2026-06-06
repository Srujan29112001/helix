const ITEMS = [
  "LangGraph",
  "DeepSeek-Coder",
  "Mistral-7B",
  "FLAML AutoML",
  "SHAP",
  "ChromaDB · RAG",
  "RestrictedPython",
  "scikit-learn",
  "pandas",
  "sentence-transformers",
];

export function Marquee() {
  return (
    <section className="relative border-y border-white/5 bg-ink-2/60 py-6">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-ink-2 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-ink-2 to-transparent" />
      <div className="flex overflow-hidden">
        <div className="animate-marquee flex shrink-0 items-center gap-10 pr-10">
          {ITEMS.concat(ITEMS).map((item, i) => (
            <span
              key={i}
              className="flex items-center gap-2 whitespace-nowrap font-mono text-sm text-mute"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-brand/60" />
              {item}
            </span>
          ))}
        </div>
        <div
          className="animate-marquee flex shrink-0 items-center gap-10 pr-10"
          aria-hidden
        >
          {ITEMS.concat(ITEMS).map((item, i) => (
            <span
              key={i}
              className="flex items-center gap-2 whitespace-nowrap font-mono text-sm text-mute"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-brand/60" />
              {item}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
