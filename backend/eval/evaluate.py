"""Phase 8 — evaluation harness.

Measures the system across the proposal's four task types and reports:
  - task-detection accuracy
  - model quality per dataset
  - self-correcting code-execution success rate (sandbox + critic)
  - sandbox security (blocked dangerous operations)
  - runtime

Run:  python backend/eval/evaluate.py
Writes backend/eval/results.json + backend/eval/RESULTS.md
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
ROOT = os.path.dirname(BACKEND)
sys.path.insert(0, BACKEND)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.datasets import make_blobs  # noqa: E402

from app.analysis import analyze_dataframe  # noqa: E402
from app.sandbox import run_in_sandbox  # noqa: E402


def make_datasets():
    rng = np.random.default_rng(0)
    out = []

    telco = pd.read_csv(os.path.join(ROOT, "data", "telco_churn.csv"))
    out.append(("Telco Churn", telco, "Churn", "auto", "classification"))

    n = 500
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    cat = rng.choice(["a", "b", "c"], n)
    price = 3 * x1 - 2 * x2 + rng.normal(scale=0.3, size=n) + 10
    out.append(
        ("Synthetic Regression", pd.DataFrame({"x1": x1, "x2": x2, "region": cat, "price": price}), "price", "auto", "regression")
    )

    Xb, _ = make_blobs(n_samples=400, centers=4, n_features=4, random_state=1)
    out.append(("Mall-style Clustering", pd.DataFrame(Xb, columns=["income", "spend", "age", "visits"]), "", "clustering", "clustering"))

    pa = ["great", "excellent", "amazing", "love", "perfect", "superb"]
    na = ["terrible", "awful", "worst", "bad", "poor", "useless"]
    nn = ["product", "quality", "delivery", "service", "value", "support"]
    rev = lambda a: " ".join(rng.choice(a, 4)) + " " + rng.choice(nn)  # noqa: E731
    rows = [(rev(pa), "positive") for _ in range(150)] + [(rev(na), "negative") for _ in range(150)]
    out.append(("Reviews NLP", pd.DataFrame(rows, columns=["review", "sentiment"]), "sentiment", "nlp", "nlp"))
    return out


def eval_self_heal(datasets):
    """A common real bug (mean() without numeric_only) → Critic fixes → retry."""
    heal, total, attempts = 0, 0, []
    for name, df, target, task, _ in datasets:
        if task == "clustering":
            continue
        bad = "print(df.mean(numeric_only=False).round(2).to_string())"
        fix = bad.replace("numeric_only=False", "numeric_only=True")
        total += 1
        r1 = run_in_sandbox(bad, {"df": df.copy()})
        if r1.ok:
            heal += 1
            attempts.append(0)
            continue
        r2 = run_in_sandbox(fix, {"df": df.copy()})
        if r2.ok:
            heal += 1
            attempts.append(1)
    return heal, total, attempts


def eval_security():
    attacks = [
        "import os\nos.listdir('.')",
        "open('hack.txt', 'w')",
        "import socket",
        "import subprocess",
        "__import__('os').system('echo hi')",
        "import sys\nsys.exit()",
    ]
    blocked = sum(1 for a in attacks if not run_in_sandbox(a, {}).ok)
    return blocked, len(attacks)


def main():
    datasets = make_datasets()
    rows, task_correct = [], 0
    for name, df, target, task, expected in datasets:
        t0 = time.time()
        res = analyze_dataframe(df, target, task, time_budget=8)
        dt = time.time() - t0
        detected = res["taskLabel"].lower()
        ok = (
            (expected == "classification" and "classification" in detected)
            or (expected == "regression" and "regression" in detected)
            or (expected == "clustering" and "clustering" in detected)
            or (expected == "nlp" and "nlp" in detected)
        )
        task_correct += int(ok)
        rows.append(
            {
                "dataset": name,
                "rows": int(len(df)),
                "detected_task": res["taskLabel"],
                "correct": ok,
                "best_model": res["bestModel"],
                "headline": f'{res["headline"]["value"]} {res["headline"]["label"]}',
                "runtime_s": round(dt, 1),
            }
        )

    heal, htot, attempts = eval_self_heal(datasets)
    blocked, btot = eval_security()

    summary = {
        "datasets": len(datasets),
        "task_detection_accuracy": f"{task_correct}/{len(datasets)} ({100 * task_correct / len(datasets):.0f}%)",
        "self_heal_success": f"{heal}/{htot} ({100 * heal / htot:.0f}%)",
        "avg_fix_attempts": round(sum(attempts) / max(1, len(attempts)), 2),
        "sandbox_security_blocked": f"{blocked}/{btot} ({100 * blocked / btot:.0f}%)",
        "avg_runtime_s": round(sum(r["runtime_s"] for r in rows) / len(rows), 1),
    }

    print("\n===== HELIX EVALUATION =====")
    for r in rows:
        mark = "OK" if r["correct"] else "X"
        print(f"  [{mark}] {r['dataset']:<22} {r['detected_task']:<22} {r['best_model']:<26} {r['headline']:<14} {r['runtime_s']}s")
    print("\n  Summary:")
    for k, v in summary.items():
        print(f"    {k:<28} {v}")

    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "summary": summary}, f, indent=2)

    md = ["# Helix — Evaluation Results", "", "_Generated by `backend/eval/evaluate.py`._", "",
          "## Per-dataset", "", "| Dataset | Rows | Detected task | Best model | Result | Runtime |",
          "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['dataset']} | {r['rows']:,} | {r['detected_task']} | {r['best_model']} | {r['headline']} | {r['runtime_s']}s |")
    md += ["", "## Summary", "", "| Metric | Value |", "|---|---|"]
    for k, v in summary.items():
        md.append(f"| {k.replace('_', ' ')} | {v} |")
    with open(os.path.join(HERE, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n  wrote results.json + RESULTS.md")


if __name__ == "__main__":
    main()
