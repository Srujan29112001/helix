"""Builds the Helix capstone *project deck* — 20 slides, dark brand-matched,
for a mixed audience (non-tech -> learners -> data scientists -> professors ->
business leaders).

Screenshots and AI-generated images auto-embed when present in presentation/assets/
with the filenames below; otherwise a labelled placeholder frame is drawn so the
deck is always complete. See presentation/IMAGE_GUIDE.md for the shot list + the
nanobanana prompts.

Run:  python presentation/build_project_deck.py  ->  presentation/Helix_Project_Deck.pptx
"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ----------------------------- palette -----------------------------
INK = RGBColor(0x04, 0x06, 0x0F)
INK2 = RGBColor(0x09, 0x0E, 0x1A)
PANEL = RGBColor(0x0C, 0x12, 0x24)
EDGE = RGBColor(0x1A, 0x24, 0x40)
CYAN = RGBColor(0x25, 0xD7, 0xF0)
VIOLET = RGBColor(0x8B, 0x5C, 0xF6)
AZURE = RGBColor(0x38, 0xBD, 0xF8)
IRIS = RGBColor(0xA7, 0x8B, 0xFA)
MAGENTA = RGBColor(0xE8, 0x79, 0xF9)
ACID = RGBColor(0x9A, 0xE6, 0x4A)
GOLD = RGBColor(0xFB, 0xBF, 0x24)
CORAL = RGBColor(0xFB, 0x71, 0x85)
TEAL = RGBColor(0x2D, 0xD4, 0xBF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MIST = RGBColor(0xC9, 0xD6, 0xEF)
MUTE = RGBColor(0x76, 0x85, 0x9F)

HEAD = "Segoe UI Semibold"
BODY = "Segoe UI"
MONO = "Consolas"

CENTER, LEFT = PP_ALIGN.CENTER, PP_ALIGN.LEFT
MID, TOP = MSO_ANCHOR.MIDDLE, MSO_ANCHOR.TOP

HERE = os.path.dirname(__file__)
ASSETS = os.path.join(HERE, "assets")

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# 9 agents — name + accent colour (matches lib/agents.ts ordering)
AGENTS9 = [
    ("Planner", VIOLET), ("Coder", CYAN), ("Executor", AZURE), ("Critic", GOLD),
    ("AutoML", ACID), ("Explainer", MAGENTA), ("Visualizer", TEAL),
    ("Researcher", IRIS), ("Reporter", CORAL),
]


# ----------------------------- helpers -----------------------------
def slide(bg=INK):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    r.fill.solid()
    r.fill.fore_color.rgb = bg
    r.line.fill.background()
    r.shadow.inherit = False
    return s


def text(s, x, y, w, h, runs, align=LEFT, anchor=TOP, space=2):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if isinstance(runs[0], tuple):
        runs = [runs]
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        for t, size, color, bold, font in para:
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size)
            r.font.color.rgb = color
            r.font.bold = bold
            r.font.name = font
    return tb


def one(s, x, y, w, h, t, size, color, bold=False, font=BODY, align=LEFT, anchor=TOP):
    return text(s, x, y, w, h, [[(t, size, color, bold, font)]], align=align, anchor=anchor)


def box(s, x, y, w, h, fill=PANEL, line=EDGE, line_w=1.0, radius=0.08):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = radius
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return shp


def frame(s, x, y, w, h, color, w_pt=1.25):
    """Outline-only rectangle (used to border an embedded screenshot)."""
    shp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.background()
    shp.line.color.rgb = color
    shp.line.width = Pt(w_pt)
    shp.shadow.inherit = False
    return shp


def dot(s, x, y, d, color):
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid()
    c.fill.fore_color.rgb = color
    c.line.fill.background()
    c.shadow.inherit = False
    return c


def eyebrow(s, x, y, label, color=CYAN):
    dot(s, x, y + 0.05, 0.12, color)
    one(s, x + 0.22, y - 0.05, 8, 0.4, label.upper(), 12, MUTE, True, MONO)


def title(s, x, y, t, w=11.6, size=33):
    one(s, x, y, w, 1.1, t, size, WHITE, True, HEAD)


def footer(s, n, label):
    one(s, 11.4, 7.04, 1.7, 0.3, f"Helix · {n:02d}", 9, MUTE, False, MONO, align=PP_ALIGN.RIGHT)
    one(s, 1.0, 7.04, 8, 0.3, label, 9, MUTE, False, MONO)


def embed(s, x, y, w, h, fname, tag, caption, accent=CYAN):
    """Embed assets/<fname> if it exists, else draw a labelled placeholder frame."""
    full = os.path.join(ASSETS, fname)
    if os.path.exists(full):
        s.shapes.add_picture(full, Inches(x), Inches(y), Inches(w), Inches(h))
        frame(s, x, y, w, h, EDGE, 1.0)
        return True
    box(s, x, y, w, h, INK2, accent, 1.25)
    one(s, x + 0.2, y + 0.18, w - 0.4, 0.3, fname, 9.5, accent, True, MONO)
    one(s, x, y + h / 2 - 0.5, w, 0.4, tag, 14, accent, True, MONO, CENTER, MID)
    one(s, x + 0.4, y + h / 2 + 0.05, w - 0.8, 0.7, caption, 11.5, MUTE, False, BODY, CENTER, MID)
    return False


# ============================ 1 — Title ============================
s = slide(INK)
embed(s, 7.6, 0.0, 5.73, 7.5, "01_hero.png", "NANOBANANA #1", "abstract neural / data hero art (right third)", VIOLET)
box(s, 0, 0, 7.7, 7.5, INK, None)  # keep left column clean over any bleed
for i, (_, c) in enumerate(AGENTS9):
    dot(s, 1.0 + i * 0.40, 1.75, 0.2, c)
text(s, 1.0, 2.45, 7.0, 1.4, [[("Helix", 74, WHITE, True, HEAD), (".", 74, CYAN, True, HEAD)]])
text(s, 1.02, 3.75, 6.6, 1.2, [[("Autonomous Data Science Agent ", 23, MIST, False, BODY),
                                ("with Self-Correcting Code Execution", 23, CYAN, True, BODY)]])
one(s, 1.04, 5.05, 6.4, 0.9, "From a CSV and one plain-English sentence to a business-ready report — automatically, by a team of nine AI agents.", 14.5, MUTE, False, BODY)
box(s, 1.0, 6.3, 4.6, 0.7, INK2, EDGE)
one(s, 1.25, 6.3, 4.3, 0.7, "Capstone Project  ·  IIIT-H  ·  Srujan", 13, MIST, False, MONO, anchor=MID)
footer(s, 1, "title")

# ============================ 2 — Problem ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "The problem", CORAL)
title(s, 1.0, 1.2, "Insight is trapped behind a bottleneck")
probs = [
    ("Scarce expertise", "Business teams queue for a data scientist to answer even simple questions — days of delay for a single chart.", CORAL),
    ("Repetitive grind", "60–70% of an analyst's time goes to cleaning CSVs, fixing missing values and rewriting near-identical EDA code.", GOLD),
    ("Brittle iteration", "Code breaks, someone reads the traceback, patches it, reruns — a slow loop that is painful for non-experts.", IRIS),
]
for i, (h, b, c) in enumerate(probs):
    x = 1.0 + i * 3.85
    box(s, x, 2.6, 3.55, 3.4, PANEL, EDGE)
    dot(s, x + 0.35, 2.98, 0.28, c)
    one(s, x + 0.35, 3.55, 3, 0.5, h, 19, WHITE, True, HEAD)
    one(s, x + 0.35, 4.15, 2.95, 1.7, b, 13.5, MUTE, False, BODY)
one(s, 1.0, 6.35, 11.3, 0.5, "The result: data piles up, but decisions wait on a handful of specialists.", 14, MIST, False, BODY)
footer(s, 2, "problem")

# ============================ 3 — Solution ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "The solution")
title(s, 1.0, 1.2, "An AI team that does the entire workflow")
flow = ["Upload a CSV", "Plain-English goal", "9 agents work", "Self-correct on error", "Business report"]
for i, step in enumerate(flow):
    x = 1.0 + i * 2.32
    box(s, x, 2.85, 2.05, 0.95, INK2, CYAN if i in (0, 4) else EDGE)
    one(s, x, 2.85, 2.05, 0.95, step, 13, MIST, True, BODY, CENTER, MID)
    if i < len(flow) - 1:
        one(s, x + 2.0, 2.85, 0.34, 0.95, "›", 24, MUTE, True, BODY, CENTER, MID)
box(s, 1.0, 4.4, 11.3, 1.95, PANEL, EDGE)
text(s, 1.4, 4.75, 10.6, 1.3, [
    [('“Predict which customers will churn and explain the key drivers.”', 18, WHITE, True, BODY)],
    [("→  ~0.84 ROC-AUC, top drivers = contract type & tenure, the right charts, a live-web context pass, and a plain-English report with a recommendation — in minutes, with no human in the loop.", 14.5, ACID, False, BODY)],
], space=10)
footer(s, 3, "solution")

# ============================ 4 — Who it's for ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "Audience", ACID)
title(s, 1.0, 1.2, "One product, five kinds of user")
aud = [
    ("Non-technical users", "Ask in English, get a data-backed answer + plain explanation — no data team.", CORAL),
    ("Data scientists", "Automate the boring 60–70% (cleaning, EDA, baselines) and focus on judgement.", CYAN),
    ("Students & learners", "A transparent, explainable reference for the whole ML + AI-agent workflow.", ACID),
    ("Professors / evaluators", "Multi-agent orchestration, self-correction, AutoML, explainability, RAG — working together.", IRIS),
    ("Business leaders", "A 'data scientist in a box' — faster decisions without growing headcount.", GOLD),
]
for i, (h, b, c) in enumerate(aud):
    x = 1.0 + (i % 3) * 3.85
    y = 2.45 + (i // 3) * 2.05
    box(s, x, y, 3.55, 1.8, PANEL, EDGE)
    dot(s, x + 0.32, y + 0.34, 0.22, c)
    one(s, x + 0.72, y + 0.26, 2.7, 0.5, h, 15.5, WHITE, True, HEAD)
    one(s, x + 0.32, y + 0.86, 3.0, 0.85, b, 12, MUTE, False, BODY)
footer(s, 4, "audience")

# ============================ 5 — Landing (screenshot) ============================
s = slide(INK)
eyebrow(s, 1.0, 0.8, "The product · live", CYAN)
title(s, 1.0, 1.15, "A premium, production web app — not a notebook")
embed(s, 1.0, 2.15, 8.4, 4.7, "05_landing.png", "SCREENSHOT", "Landing page — hero + 'nine agents' pipeline section", CYAN)
pts = [
    ("Next.js + React", "A genuinely premium UI the proposal's Gradio can't match."),
    ("Tells the story", "Explains the 9 agents, the self-heal loop and the use-cases."),
    ("One click in", "Straight to the Studio to run a real analysis."),
]
for i, (h, b) in enumerate(pts):
    y = 2.2 + i * 1.55
    box(s, 9.7, y, 2.6, 1.4, PANEL, EDGE)
    one(s, 9.9, y + 0.18, 2.3, 0.4, h, 13.5, CYAN, True, HEAD)
    one(s, 9.9, y + 0.62, 2.3, 0.7, b, 10.5, MUTE, False, BODY)
footer(s, 5, "landing")

# ============================ 6 — The Studio + fields ============================
s = slide(INK)
eyebrow(s, 1.0, 0.8, "How you use it", ACID)
title(s, 1.0, 1.15, "The Studio — set it up in four fields")
embed(s, 1.0, 2.15, 7.0, 4.7, "06_studio.png", "SCREENSHOT", "Studio setup — sample/upload, goal, target, task, AI engine", ACID)
fields = [
    ("Dataset", "Pick a sample or upload CSV / Excel / Parquet / JSON, or paste a URL / Google-Sheet."),
    ("Goal", "Your question in plain English — feeds the Planner & Reporter."),
    ("Target + Task", "Column to predict (or Auto) and the task (or Auto-detect) — hides for clustering."),
    ("AI engine", "Provider, model, per-agent temperature & key — keys stay in your browser."),
]
for i, (h, b) in enumerate(fields):
    y = 2.2 + i * 1.18
    box(s, 8.3, y, 4.0, 1.05, PANEL, EDGE)
    one(s, 8.5, y + 0.13, 3.7, 0.4, h, 13.5, WHITE, True, HEAD)
    one(s, 8.5, y + 0.5, 3.7, 0.5, b, 10.5, MUTE, False, BODY)
footer(s, 6, "studio")

# ============================ 7 — Architecture ============================
s = slide(INK)
eyebrow(s, 1.0, 0.75, "Architecture", VIOLET)
title(s, 1.0, 1.1, "Nine agents, orchestrated by LangGraph")
# two rows of agent chips
for i, (name, c) in enumerate(AGENTS9):
    col = i % 5
    row = i // 5
    x = 1.0 + col * 2.32
    y = 2.5 + row * 1.25
    box(s, x, y, 2.05, 1.0, INK2, c, 1.5)
    one(s, x, y + 0.16, 2.05, 0.4, name, 13, WHITE, True, BODY, CENTER)
    one(s, x, y + 0.56, 2.05, 0.35, "agent", 9, MUTE, False, MONO, CENTER)
box(s, 3.5, 5.15, 6.3, 0.62, INK2, GOLD)
one(s, 3.5, 5.15, 6.3, 0.62, "↺  self-correction loop · Executor ⇄ Critic · ≤ 5 retries", 13, GOLD, True, MONO, CENTER, MID)
one(s, 1.0, 6.1, 11.3, 0.8, "Each agent is a node in a LangGraph state graph; a conditional edge loops Executor↔Critic until the code runs. The backend streams Server-Sent Events so you watch every step live.", 13, MUTE, False, BODY)
footer(s, 7, "architecture")

# ============================ 8 — The 9 agents (table) ============================
s = slide(INK)
eyebrow(s, 1.0, 0.8, "The nine agents", IRIS)
title(s, 1.0, 1.15, "Who does what — and with which tool")
rows = [
    ("Planner", "Break the goal into an ordered analysis plan", "LLM (chain-of-thought)"),
    ("Coder", "Write Python for each step", "LLM · RAG-grounded"),
    ("Executor", "Run the code safely, capture stdout / errors", "RestrictedPython / E2B"),
    ("Critic", "Read tracebacks, rewrite the code, retry ≤5", "LLM — self-correction"),
    ("AutoML", "Search models + hyper-parameters", "FLAML"),
    ("Explainer", "Quantify what drives predictions (+ direction)", "SHAP"),
    ("Visualizer", "Pick the best chart per finding (engine fills data)", "LLM + engine"),
    ("Researcher", "Pull live real-world context from the web", "DuckDuckGo / Tavily"),
    ("Reporter", "Write the business narrative + recommendation", "LLM"),
]
box(s, 1.0, 2.15, 11.3, 4.7, PANEL, EDGE)
hdr = ["Agent", "Job", "Tech"]
xs = [1.4, 3.5, 9.2]
for j, htxt in enumerate(hdr):
    one(s, xs[j], 2.4, 3.5, 0.4, htxt, 12, MUTE, True, MONO)
for i, (a, j, t) in enumerate(rows):
    y = 2.92 + i * 0.43
    one(s, xs[0], y, 2.1, 0.4, a, 13, AGENTS9[i][1], True, BODY)
    one(s, xs[1], y, 5.7, 0.4, j, 12.5, MIST, False, BODY)
    one(s, xs[2], y, 3.1, 0.4, t, 11.5, MUTE, False, MONO)
footer(s, 8, "agents")

# ============================ 9 — Self-correcting execution ============================
s = slide(INK2)
eyebrow(s, 1.0, 0.85, "The headline capability", GOLD)
title(s, 1.0, 1.2, "Self-correcting code execution")
steps = [
    ("Coder writes Python", "df.mean(numeric_only=False)", CYAN),
    ("Executor runs it (sandbox)", "TypeError: could not convert string…", CORAL),
    ("Critic reads the traceback", "diagnosis → numeric_only=True", GOLD),
    ("Re-run → clean output", "tenure 32.37 · charges 64.76 ✓", ACID),
]
for i, (h, code, c) in enumerate(steps):
    y = 2.55 + i * 0.92
    dot(s, 1.0, y + 0.1, 0.3, c)
    one(s, 1.5, y, 5, 0.5, h, 16, WHITE, True, BODY)
    box(s, 6.6, y - 0.06, 5.7, 0.62, INK, EDGE)
    one(s, 6.8, y - 0.06, 5.4, 0.62, code, 12.5, c, False, MONO, anchor=MID)
box(s, 1.0, 6.35, 11.3, 0.7, INK, GOLD)
one(s, 1.0, 6.35, 11.3, 0.7, "Real tracebacks → real fixes, up to 5 times. RestrictedPython blocks the file-system, network and dangerous imports.", 12.5, GOLD, True, BODY, CENTER, MID)
footer(s, 9, "self-correction")

# ============================ 10 — Live pipeline (screenshot) ============================
s = slide(INK)
eyebrow(s, 1.0, 0.8, "Watch it work", AZURE)
title(s, 1.0, 1.15, "Full transparency — every step, live")
embed(s, 1.0, 2.15, 8.4, 4.7, "10_pipeline.png", "SCREENSHOT", "Pipeline tab — agents streaming code, stdout, the self-heal loop", AZURE)
pts = [
    ("Colab-style", "Complete code, stdout and tracebacks — never truncated."),
    ("Prompt & logic", "Each agent's exact system prompt + sandbox rules on tap."),
    ("See the heal", "The Critic's diagnosis and corrected code, in real time."),
]
for i, (h, b) in enumerate(pts):
    y = 2.2 + i * 1.55
    box(s, 9.7, y, 2.6, 1.4, PANEL, EDGE)
    one(s, 9.9, y + 0.18, 2.3, 0.4, h, 13.5, AZURE, True, HEAD)
    one(s, 9.9, y + 0.62, 2.3, 0.7, b, 10.5, MUTE, False, BODY)
footer(s, 10, "pipeline")

# ============================ 11 — Results dashboard (screenshot) ============================
s = slide(INK)
eyebrow(s, 1.0, 0.8, "The payoff", MAGENTA)
title(s, 1.0, 1.15, "A results dashboard anyone can read")
embed(s, 1.0, 2.15, 8.4, 4.7, "11_results_telco.png", "SCREENSHOT", "Results tab on Telco Churn — verdict, charts, report, knowledge graph", MAGENTA)
pts = [
    ("Honest verdict", "Grades the signal from strong to near-chance."),
    ("Interactive charts", "Hover any point/line for the exact value; real axis ticks."),
    ("Business report", "Narrative + recommendation, grounded in live web context."),
]
for i, (h, b) in enumerate(pts):
    y = 2.2 + i * 1.55
    box(s, 9.7, y, 2.6, 1.4, PANEL, EDGE)
    one(s, 9.9, y + 0.18, 2.3, 0.4, h, 13.5, MAGENTA, True, HEAD)
    one(s, 9.9, y + 0.62, 2.3, 0.7, b, 10.5, MUTE, False, BODY)
footer(s, 11, "results")

# ============================ 12 — Nine task types ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "Breadth", TEAL)
title(s, 1.0, 1.2, "Nine task types, auto-detected")
tasks = [
    ("Classification", "binary + multiclass", CYAN),
    ("Regression", "predict a number", AZURE),
    ("Clustering", "find segments (k by silhouette)", IRIS),
    ("NLP + analytics", "topics · sentiment · keywords", MAGENTA),
    ("Anomaly detection", "Isolation Forest", CORAL),
    ("Dimensionality reduction", "PCA → 2-D map", VIOLET),
    ("Time-series forecasting", "Holt-Winters ETS + seasonality", GOLD),
    ("Survival analysis", "Kaplan-Meier + Cox PH", TEAL),
    ("Recommendation", "content-based similarity", ACID),
]
for i, (h, b, c) in enumerate(tasks):
    x = 1.0 + (i % 3) * 3.85
    y = 2.5 + (i // 3) * 1.42
    box(s, x, y, 3.55, 1.22, PANEL, EDGE)
    dot(s, x + 0.32, y + 0.3, 0.2, c)
    one(s, x + 0.68, y + 0.2, 2.8, 0.45, h, 14.5, WHITE, True, HEAD)
    one(s, x + 0.32, y + 0.66, 3.1, 0.45, b, 11, MUTE, False, MONO)
footer(s, 12, "tasks")

# ============================ 13 — Statistical rigor ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "Rigor", CYAN)
title(s, 1.0, 1.2, "Statistics + model evaluation, not just a score")
left = [
    "Auto-picks the right test: Welch t / Mann-Whitney, ANOVA / Kruskal,",
    "chi-square, Pearson — each with a p-value, an effect size (Cohen's d,",
    "Cramér's V, |r|) and a plain-English verdict.",
]
box(s, 1.0, 2.45, 5.55, 4.0, PANEL, EDGE)
one(s, 1.3, 2.7, 5.0, 0.4, "Statistical significance", 15, CYAN, True, HEAD)
one(s, 1.3, 3.25, 5.0, 1.6, " ".join(left), 12.5, MIST, False, BODY)
one(s, 1.3, 4.95, 5.0, 1.3, "So a weak dataset explains itself instead of looking broken — the honest answer, with the maths to back it.", 12.5, MUTE, False, BODY)
ev = ["Stratified k-fold cross-validation (mean ± std)", "Confusion matrix + per-class P / R / F1",
      "ROC & precision-recall curves", "Calibration + learning curves", "Residuals (predicted vs actual)",
      "Model-comparison table vs baselines"]
box(s, 6.75, 2.45, 5.55, 4.0, PANEL, EDGE)
one(s, 7.05, 2.7, 5.0, 0.4, "Model evaluation · diagnostics", 15, MAGENTA, True, HEAD)
for i, e in enumerate(ev):
    y = 3.3 + i * 0.5
    dot(s, 7.05, y + 0.08, 0.13, MAGENTA)
    one(s, 7.3, y, 4.9, 0.45, e, 12.5, MIST, False, BODY)
footer(s, 13, "statistics")

# ============================ 14 — Explainability + charts + graph ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "Explainability", MAGENTA)
title(s, 1.0, 1.2, "Why — not just what")
cards = [
    ("SHAP drivers", "Quantifies what drives every prediction, with direction — contract type & tenure push churn up.", MAGENTA),
    ("Recommended charts", "The Visualizer picks the chart type; the engine fills every number from real data, so a chart can never show a fabricated value.", TEAL),
    ("3D knowledge graph", "The whole analysis as an explorable force-directed map — target, drivers, segments, metrics, charts, columns.", CYAN),
]
for i, (h, b, c) in enumerate(cards):
    x = 1.0 + i * 3.85
    box(s, x, 2.5, 3.55, 3.5, PANEL, EDGE)
    dot(s, x + 0.35, 2.85, 0.26, c)
    one(s, x + 0.35, 3.4, 3.0, 0.5, h, 16.5, WHITE, True, HEAD)
    one(s, x + 0.35, 4.0, 2.95, 1.9, b, 12.5, MUTE, False, BODY)
footer(s, 14, "explainability")

# ============================ 15 — Beyond modeling ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "Beyond the model", ACID)
title(s, 1.0, 1.2, "An analyst's full toolkit")
caps = [
    ("Imbalance · SMOTE", "Oversamples the minority class (train only) when classes are skewed.", CORAL),
    ("Feature engineering", "Log-transforms skew, adds the top interaction — transparently logged.", ACID),
    ("What-if simulator", "Move a feature with a slider, watch the prediction respond.", GOLD),
    ("Ask the data", "Grounded natural-language Q&A over your own results.", CYAN),
    ("Exports", "Download a .pptx deck, a Markdown report, or the .py script.", IRIS),
    ("Big-data ingest", "CSV · Excel · Parquet · JSON · URL · Google Sheets, up to ~3M rows.", AZURE),
]
for i, (h, b, c) in enumerate(caps):
    x = 1.0 + (i % 3) * 3.85
    y = 2.5 + (i // 3) * 2.0
    box(s, x, y, 3.55, 1.75, PANEL, EDGE)
    dot(s, x + 0.32, y + 0.32, 0.22, c)
    one(s, x + 0.72, y + 0.26, 2.7, 0.5, h, 14.5, WHITE, True, HEAD)
    one(s, x + 0.32, y + 0.85, 3.05, 0.8, b, 11.5, MUTE, False, BODY)
footer(s, 15, "toolkit")

# ============================ 16 — The engine (analysis.py) ============================
s = slide(INK2)
eyebrow(s, 1.0, 0.85, "Under the hood", AZURE)
title(s, 1.0, 1.2, "The engine — one deterministic pipeline")
stages = ["Clean & encode", "Detect task", "FLAML AutoML", "SHAP explain", "EDA + stats", "Build charts", "Quality verdict"]
scolors = [CYAN, AZURE, ACID, MAGENTA, IRIS, TEAL, GOLD]
for i, (st, c) in enumerate(zip(stages, scolors)):
    x = 1.0 + i * 1.64
    box(s, x, 2.7, 1.45, 1.0, INK, c, 1.4)
    one(s, x + 0.05, 2.7, 1.35, 1.0, st, 11, MIST, True, BODY, CENTER, MID)
    if i < len(stages) - 1:
        one(s, x + 1.42, 2.7, 0.25, 1.0, "›", 18, MUTE, True, BODY, CENTER, MID)
one(s, 1.0, 4.15, 11.3, 0.8, "analysis.py turns a raw dataframe into a full RunResults object. The LLM never invents a number — it only chooses chart types and writes prose; pure Python computes every metric on the real, cleaned data.", 13.5, MIST, False, BODY)
box(s, 1.0, 5.35, 11.3, 1.15, PANEL, EDGE)
one(s, 1.3, 5.55, 10.8, 0.4, "Big-data path:", 12.5, GOLD, True, MONO)
one(s, 1.3, 5.95, 10.8, 0.45, "striped read-sample · width-scaled training (≤500k rows) · 150-feature cap · float32 downcast · streaming heartbeat so long fits never time out.", 12, MUTE, False, BODY)
footer(s, 16, "engine")

# ============================ 17 — Tech stack ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "Tech stack", IRIS)
title(s, 1.0, 1.2, "Production tooling — and why each choice")
groups = [
    ("Next.js 16 + React 19", "A genuinely premium UI; type-safe event contract.", CYAN),
    ("FastAPI + SSE", "Async Python API that streams agent events live.", AZURE),
    ("LangGraph", "Purpose-built for multi-agent, looping, stateful flows.", VIOLET),
    ("pandas + scikit-learn", "The standard data-wrangling + ML toolkit.", ACID),
    ("FLAML AutoML", "Finds a good model under a time budget.", GOLD),
    ("SHAP", "The standard for explainability — 'here's why'.", MAGENTA),
    ("ChromaDB + MiniLM", "RAG grounds the Coder in real recipes.", TEAL),
    ("RestrictedPython + E2B", "Sandbox the agent's code — jail by default.", CORAL),
]
for i, (h, b, c) in enumerate(groups):
    x = 1.0 + (i % 2) * 5.85
    y = 2.4 + (i // 2) * 1.12
    box(s, x, y, 5.5, 0.95, PANEL, EDGE)
    dot(s, x + 0.3, y + 0.38, 0.18, c)
    one(s, x + 0.65, y + 0.13, 4.7, 0.4, h, 13.5, WHITE, True, HEAD)
    one(s, x + 0.65, y + 0.52, 4.7, 0.4, b, 11, MUTE, False, BODY)
footer(s, 17, "tech-stack")

# ============================ 18 — LLMs + transparency ============================
s = slide(INK)
eyebrow(s, 1.0, 0.85, "Pluggable & transparent", GOLD)
title(s, 1.0, 1.2, "Bring your own model — see everything")
box(s, 1.0, 2.45, 5.55, 4.0, PANEL, EDGE)
one(s, 1.3, 2.7, 5.0, 0.4, "Eight providers, one interface", 15, CYAN, True, HEAD)
prov = "Groq · OpenAI · DeepSeek · Mistral · OpenRouter · Google Gemini · Z.ai (GLM) · Anthropic (Claude)"
one(s, 1.3, 3.25, 5.0, 0.9, prov, 13, MIST, False, MONO)
one(s, 1.3, 4.35, 5.0, 1.9, "One model for all agents or a different model per agent. A temperature slider (global or per-agent). Optional E2B microVM key. With no key, Helix runs a deterministic mock for the narration while still doing real ML (FLAML + SHAP). Keys live only in your browser.", 12.5, MUTE, False, BODY)
box(s, 6.75, 2.45, 5.55, 4.0, PANEL, EDGE)
one(s, 7.05, 2.7, 5.0, 0.4, "Nothing hidden", 15, GOLD, True, HEAD)
tr = ["Exact system prompt + logic per agent", "RestrictedPython / E2B sandbox rules shown",
      "Complete code + stdout + tracebacks, live", "Every chart ships a data table + 'how to read'",
      "Data-processing card: every cleaning step", "Honest model-quality verdict band"]
for i, e in enumerate(tr):
    y = 3.3 + i * 0.5
    dot(s, 7.05, y + 0.08, 0.13, GOLD)
    one(s, 7.3, y, 4.9, 0.45, e, 12.5, MIST, False, BODY)
footer(s, 18, "llms")

# ============================ 19 — Quality / engineering ============================
s = slide(INK2)
eyebrow(s, 1.0, 0.85, "Engineering quality", ACID)
title(s, 1.0, 1.2, "Built to be reliable")
stats = [("9", "task types", CYAN), ("8", "LLM providers", VIOLET), ("70", "RAG recipes", ACID), ("CI", "pytest on push", GOLD)]
for i, (v, l, c) in enumerate(stats):
    x = 1.0 + i * 2.85
    box(s, x, 2.5, 2.6, 1.5, PANEL, EDGE)
    one(s, x, 2.62, 2.6, 0.8, v, 36, c, True, HEAD, CENTER)
    one(s, x, 3.5, 2.6, 0.4, l, 12, MUTE, False, MONO, CENTER)
pts = [
    ("Tested", "A pytest suite covers every task type + the engine helpers; GitHub Actions runs tests, typecheck and a production build on every push."),
    ("Honest", "A model-quality verdict grades each result; weak-signal data is labelled, not dressed up."),
    ("Deployed", "Frontend on Vercel, backend on Hugging Face Spaces — running end-to-end."),
]
for i, (h, b) in enumerate(pts):
    y = 4.35 + i * 0.84
    box(s, 1.0, y, 11.3, 0.74, PANEL, EDGE)
    one(s, 1.3, y + 0.06, 2.0, 0.6, h, 13.5, ACID, True, HEAD, anchor=MID)
    one(s, 3.2, y + 0.06, 8.9, 0.6, b, 11.5, MUTE, False, BODY, anchor=MID)
footer(s, 19, "quality")

# ============================ 20 — Closing ============================
s = slide(INK)
for i, (_, c) in enumerate(AGENTS9):
    dot(s, 1.0 + i * 0.40, 1.85, 0.2, c)
text(s, 1.0, 2.6, 11.5, 1.6, [[("From a CSV to a decision —", 40, WHITE, True, HEAD)],
                              [("autonomously.", 40, CYAN, True, HEAD)]], space=4)
box(s, 1.0, 4.7, 11.3, 1.2, PANEL, EDGE)
text(s, 1.3, 4.92, 10.8, 0.9, [
    [("Live:  ", 13.5, MUTE, False, MONO), ("Vercel (Studio)", 13.5, MIST, True, MONO),
     ("   ·   Backend:  ", 13.5, MUTE, False, MONO), ("Hugging Face Spaces", 13.5, MIST, True, MONO)],
    [("9 agents · self-correcting · AutoML + SHAP · 9 task types · RAG · live research · full transparency", 12.5, MUTE, False, BODY)],
], space=8)
one(s, 1.0, 6.45, 11, 0.5, "Thank you.   ·   Capstone Project · IIIT-H", 16, MUTE, True, BODY)
footer(s, 20, "closing")

# ----------------------------- save -----------------------------
out_path = os.path.join(HERE, "Helix_Project_Deck.pptx")
prs.save(out_path)
n = len(prs.slides._sldIdLst)
embedded = sum(os.path.exists(os.path.join(ASSETS, f)) for f in
               ["01_hero.png", "05_landing.png", "06_studio.png", "10_pipeline.png", "11_results_telco.png"])
print(f"saved {out_path} · {n} slides · {embedded}/5 image assets embedded")
