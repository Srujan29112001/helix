# Helix deck — image guide

Everything the **22-slide deck** (`Helix_Project_Deck.pptx`, built by
`build_project_deck.py`) uses for imagery. **All 11 images are already embedded** —
the deck is complete as-is. This file documents what each image is and how to
replace any of them.

Rebuild any time with:

```bash
python presentation/build_project_deck.py
```

The script auto-embeds every file in `presentation/assets/` by name and draws a
labelled placeholder for anything missing.

---

## 1. Real app screenshots — ✅ captured (live, on a telco-churn run)

Captured headless via Playwright at 2880×1620 (16:9) against the live app.

| File | Slide | Screen |
|------|-------|--------|
| `05_landing.png` | 2 | Landing hero — "writes its own code — and fixes it" |
| `06_studio.png` | 10 | Studio setup (samples, upload, goal, target, task, AI engine) |
| `10_pipeline.png` | 11 | Pipeline mid-stream — Planner plan, Coder RAG docs, Critic "1 fix" |
| `11_results_telco.png` | 12 | Results on **Telco Churn** — verdict 0.83, metrics, key findings |

**To re-capture** after a UI change: run the frontend (`npm run dev`, backend up,
`.env.local → NEXT_PUBLIC_API_URL=http://localhost:8000`) and screenshot a 16:9
crop, or re-run the Playwright capture. Keep the same filenames and the deck
re-embeds them automatically.

---

## 2. Hero / section art — ✅ reused from your "HELIX" deck

These eight visuals were extracted from your existing
*HELIX — The Autonomous Data Scientist* deck, recompressed (≈300–430 KB each, was
4–6 MB), and reused — so the rebuilt deck is fully imaged with no regeneration
needed.

| File | Slide | What it is |
|------|-------|-----------|
| `art_hero.jpg` | 1 | Neural-mandala title hero |
| `art_problem.jpg` | 3 | "The problem" illustration |
| `diagram_architecture.png` | 5 | The full system-architecture diagram (kept as PNG for crisp labels) |
| `art_backend.jpg` | 13 | Code-monitor / backend art (landscape) |
| `art_brain.jpg` | 15 | AI-brain art (LLM providers) |
| `art_security.jpg` | 19 | Shield art (security) |
| `art_conclusion.jpg` | 22 | Future-city closing hero |

---

## 3. Optional — regenerate a hero with nanobanana 2

Only do this if you want a *different* image. Drop the new file in
`presentation/assets/` under the **same filename** and re-run the build. Portrait
heroes are placed full-height on the right (use a ~2:3 portrait, e.g. 1440×2160);
keep the dark navy palette (#04060F) so text stays readable on the left.

**`art_hero.jpg` — title (Slide 1)**
```
A dark, premium abstract illustration of an autonomous AI "data scientist": a
glowing neural network / mandala of interconnected nodes on a near-black navy
background (#04060F), electric cyan (#25D7F0) and violet (#8B5CF6) light, faint
circuit traces and binary digits. Portrait 2:3, denser toward the centre-right,
fading into dark on the left. No text, no logos, no faces. Sleek, cinematic.
```

**`art_problem.jpg` — the problem (Slide 3)**
```
Dark conceptual illustration of an analytics bottleneck: an overwhelmed analyst at
a desk buried in spreadsheets and tangled data pipes, one small cyan glow of
insight far away. Near-black navy background, coral-red (#FB7185) accents, muted
tones. Portrait 2:3, no text, no readable faces. Editorial, moody.
```

**`art_brain.jpg` — AI models (Slide 15)**
```
A glowing AI brain made of interconnected neural nodes and circuit traces on a
near-black navy field (#04060F), electric cyan (#25D7F0) and violet (#8B5CF6)
light with pink accents. Portrait 2:3, centered, no text, no face. High-tech,
premium.
```

**`art_security.jpg` — security (Slide 19)**
```
A luminous translucent shield wrapped in circuit traces and orbiting energy rings
on a dark navy background (#04060F), electric cyan (#25D7F0) glow with subtle
lightning. Portrait 2:3, centered, no text. Sleek, protective, high-tech.
```

**`art_conclusion.jpg` — closing (Slide 22)**
```
A futuristic data-city at dusk: glowing skyline of light-trails and data streams
resolving upward, near-black navy to cyan/violet gradient (#04060F → #25D7F0 →
#8B5CF6), warm horizon accent. Portrait 2:3, cinematic, no text. Optimistic,
forward-looking.
```

**`art_backend.jpg` — backend (Slide 13)** — landscape (~16:10)
```
A developer workstation at night: a monitor showing clean glowing Python code, a
desk with subtle plants, cyan/violet rim light on a near-black navy scene
(#04060F). Landscape, no readable text on screen, no face. Sleek, focused.
```

**`diagram_architecture.png` (Slide 5)** — this is a real labelled diagram, not AI
art; keep it as-is (or redraw natively). If you must regenerate as an image, see
the architecture prompt in the prior guide — but the native diagram is clearer.
