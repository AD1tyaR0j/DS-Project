"""Evaluate on the held-out split: ML models alone, rules alone, and the full hybrid engine.

Writes reports/metrics.json and reports/evaluation.md.

Usage:  python scripts/evaluate.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.metrics import (  # noqa: E402
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)

from phishguard import ml  # noqa: E402
from phishguard.engine import RiskEngine  # noqa: E402
from phishguard.parsers import from_email_fields, from_sms, from_url  # noqa: E402
from scripts.train import load_messages, load_urls, split  # noqa: E402

REPORTS = ROOT / "reports"
THRESHOLD = 50  # "High" or above counts as a phishing verdict


def metrics(y_true, y_pred, y_score) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y_true)),
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_true, y_score), 4) if len(set(y_true)) > 1 else None,
        "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def to_message(row):
    if row.channel == "sms":
        return from_sms(row.body, row.sender)
    return from_email_fields(row.sender, row.subject, row.body, getattr(row, "reply_to", ""))


def main() -> None:
    models = ml.Models()
    if not models.available:
        sys.exit("No trained models found. Run: python scripts/train.py")
    results: dict = {"date": date.today().isoformat(), "threshold": THRESHOLD}

    _, msgs = split(load_messages())
    _, urls = split(load_urls())

    # 1. ML models alone
    p_text = models.text.predict_proba(msgs.text)[:, 1]
    results["text_model"] = metrics(msgs.y, (p_text >= 0.5).astype(int), p_text)
    p_url = models.url.predict_proba(ml.url_matrix(list(urls.url)))[:, 1]
    results["url_model"] = metrics(urls.y, (p_url >= 0.5).astype(int), p_url)

    # 2. Rules alone vs 3. full hybrid engine, on messages (per channel too)
    rules_only = RiskEngine(models=_NoModels())
    hybrid = RiskEngine(models=models)
    for name, engine in (("rules_only", rules_only), ("hybrid_engine", hybrid)):
        scores = [engine.analyse(to_message(r)).score for r in msgs.itertuples()]
        msgs[f"{name}_score"] = scores
        results[name] = metrics(msgs.y, [int(s >= THRESHOLD) for s in scores], [s / 100 for s in scores])
        for ch in ("email", "sms"):
            sub = msgs[msgs.channel == ch]
            if len(sub):
                results[f"{name}_{ch}"] = metrics(sub.y, [int(s >= THRESHOLD) for s in sub[f"{name}_score"]],
                                                  [s / 100 for s in sub[f"{name}_score"]])

    url_scores = [hybrid.analyse(from_url(u)).score for u in urls.url]
    results["hybrid_engine_urls"] = metrics(urls.y, [int(s >= THRESHOLD) for s in url_scores], [s / 100 for s in url_scores])

    # Hardest mistakes, useful for error analysis
    msgs["err"] = (msgs.hybrid_engine_score >= THRESHOLD).astype(int) != msgs.y
    worst = msgs[msgs.err].head(8)
    results["sample_errors"] = [
        {"label": r.label, "score": int(r.hybrid_engine_score), "channel": r.channel, "text": (r.subject + " | " + r.body)[:160]}
        for r in worst.itertuples()
    ]

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (REPORTS / "evaluation.md").write_text(render_md(results), encoding="utf-8")
    print(render_md(results))


class _NoModels(ml.Models):
    def __init__(self):
        self.text = None
        self.url = None


def render_md(r: dict) -> str:
    rows = [
        ("Text model (TF-IDF + LR)", "text_model"), ("URL model (Gradient Boosting)", "url_model"),
        ("Rules only: messages", "rules_only"), ("Hybrid engine: messages", "hybrid_engine"),
        ("Hybrid engine: email", "hybrid_engine_email"), ("Hybrid engine: SMS", "hybrid_engine_sms"),
        ("Hybrid engine: URLs", "hybrid_engine_urls"),
    ]
    out = [f"# Evaluation report ({r['date']})", "",
           f"Held-out 25% split. Engine verdict = phishing when score >= {r['threshold']}.", "",
           "| System | n | Accuracy | Precision | Recall | F1 | ROC-AUC | FPR |",
           "|---|---|---|---|---|---|---|---|"]
    for label, key in rows:
        if key in r:
            m = r[key]
            out.append(f"| {label} | {m['n']} | {m['accuracy']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | "
                       f"{m['f1']:.3f} | {m['roc_auc'] if m['roc_auc'] is not None else '-'} | {m['false_positive_rate']:.3f} |")
    cm = r["hybrid_engine"]["confusion_matrix"]
    out += ["", "## Hybrid engine confusion matrix (messages)", "",
            "| | Predicted legit | Predicted phish |", "|---|---|---|",
            f"| **Actual legit** | {cm['tn']} | {cm['fp']} |", f"| **Actual phish** | {cm['fn']} | {cm['tp']} |", ""]
    if r.get("sample_errors"):
        out += ["## Sample errors", ""]
        out += [f"- `{e['label']}` scored {e['score']} ({e['channel']}): {e['text']}" for e in r["sample_errors"]]
        out.append("")
    out += ["> Note: if these numbers come from the generated seed dataset they show the pipeline works end to end, "
            "not real-world accuracy. Import a public dataset (`scripts/import_public.py`) for meaningful results."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main()
