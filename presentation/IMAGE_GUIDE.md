# Helix deck — image guide

Everything the **20-slide deck** (`Helix_Project_Deck.pptx`) needs for its imagery.

The build script (`build_project_deck.py`) auto-embeds any file that exists in
`presentation/assets/` with the exact filename below; anything missing is drawn
as a labelled placeholder frame so the deck is always complete. **Drop a file in,
re-run the script, done:**

```bash
python presentation/build_project_deck.py
```

---

## 1. App screenshots — ✅ already captured

These four are already in `presentation/assets/` (captured headless at 1440×810 @2×
against the live app on `localhost:3000`, telco-churn run). They are **embedded** in
the current deck. Re-capture only if the UI changes — instructions kept here for that.

| File | Slide | Screen | State captured |
|------|-------|--------|----------------|
| `05_landing.png` | 5 | Landing page | Hero — "writes its own code — and fixes it" |
| `06_studio.png` | 6 | Studio | "New analysis" setup (samples, upload, goal, Run) |
| `10_pipeline.png` | 10 | Pipeline tab | Mid-stream — Planner plan, Coder RAG docs, Critic "1 fix" |
| `11_results_telco.png` | 11 | Results tab | **Telco churn** — verdict 0.83, metrics, key findings |

**To re-capture** (after a UI change): start the frontend (`npm run dev`, with
`.env.local → NEXT_PUBLIC_API_URL=http://localhost:8000` and the backend running),
then re-run the Playwright capture, or grab them by hand:
- Landing: `localhost:3000`, top of page.
- Studio: `localhost:3000/studio`, the setup step.
- Pipeline: upload `data/telco_churn.csv`, target **Churn**, task **Classification**,
  click **Run analysis**, screenshot the Pipeline tab while agents stream.
- Results: wait for the run to finish, open the **Results** tab, screenshot the top
  (verdict band + metrics + key findings).

> Tip: a 16:9 crop (e.g. 1440×810) drops straight into the slide frames.

---

## 2. AI image to generate — nanobanana 2

Only **one** image is needed (the title-slide hero). Optional extras are listed after.

### ⭐ REQUIRED — `01_hero.png` (Slide 1, title)

> **Filename:** `presentation/assets/01_hero.png`  ·  **Aspect:** portrait-ish 3:4
> (it fills the right third of a 16:9 slide; ~1100×1500 px is plenty).

**Prompt:**
```
A dark, premium abstract illustration of an autonomous AI "data scientist" —
a glowing neural network of interconnected nodes flowing into a clean data
dashboard. Deep near-black navy background (#04060F) with a soft radial glow.
Nodes and connection lines in electric cyan (#25D7F0) and violet (#8B5CF6),
with subtle accents of acid-green and gold. A faint grid and scattered data
points / tiny bar-chart and line-chart glyphs woven into the network. Elegant,
minimal, high-tech, cinematic depth of field, no text, no logos, no human faces.
Vertical composition, the network denser toward the top-right, fading into dark
empty space on the left so it blends into a dark slide. Style: modern SaaS hero
art, sleek, sophisticated, slightly futuristic.
```
*Negative / avoid:* text, watermarks, logos, human faces, cluttered edges, bright
white background, cartoonish look.

---

### Optional extras (only if you want more imagery)

The deck's technical diagrams (architecture, self-heal loop, engine pipeline) are
already drawn natively in PowerPoint — crisp and on-brand — so **no diagram images
are required**. These are purely optional decorative backgrounds:

**`opt_closing_bg.png`** — could sit behind Slide 20 (closing). Not wired in by
default; add an `embed(...)` call if you want it.
```
Ultra-wide dark abstract banner: a single luminous data-pipeline line travelling
left to right across a near-black navy field (#04060F), starting as a messy CSV
grid on the left and resolving into a clean glowing upward chart on the right.
Electric cyan (#25D7F0) to violet (#8B5CF6) gradient along the line, soft bloom,
faint particles. Minimal, cinematic, no text, no faces. 16:9.
```

**`opt_problem_art.png`** — optional accent for Slide 2 (the problem).
```
Dark minimal conceptual illustration: a long queue of small abstract figures
waiting in front of a single glowing data terminal, representing a bottleneck.
Near-black navy background, coral-red (#FB7185) and muted tones, one cyan glow
at the terminal. Flat, elegant, no text, no detailed faces. 16:9.
```

---

## 3. Diagram prompts (alternative, if you'd rather generate them than use the native ones)

If you prefer AI-generated diagrams over the built-in PowerPoint shapes, here are
prompts that match the deck's content. (Recommended: keep the native ones — they're
accurate and editable.)

**Architecture (Slide 7):**
```
Clean technical diagram on a dark navy background (#04060F): nine labelled nodes
in a horizontal pipeline — Planner, Coder, Executor, Critic, AutoML, Explainer,
Visualizer, Researcher, Reporter — connected left to right by glowing arrows.
A curved feedback arrow loops from "Critic" back to "Executor" labelled
"self-correction ≤5". Each node a rounded chip with a distinct accent colour
(violet, cyan, azure, gold, acid-green, magenta, teal, iris, coral). Minimal,
flat, modern, crisp labels, no clutter. 16:9.
```

**Engine pipeline (Slide 16):**
```
Horizontal flow diagram on dark navy (#04060F): seven stages connected by arrows —
"Clean & encode → Detect task → FLAML AutoML → SHAP explain → EDA + stats →
Build charts → Quality verdict". Each stage a rounded chip with a cyan/violet/
acid-green accent and a tiny matching icon. Sleek, minimal, technical, no extra
text. 16:9.
```
