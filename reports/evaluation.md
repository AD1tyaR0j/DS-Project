# Evaluation report (2026-10-03)

Held-out 25% split. Engine verdict = phishing when score >= 50.

| System | n | Accuracy | Precision | Recall | F1 | ROC-AUC | FPR |
|---|---|---|---|---|---|---|---|
| Text model (TF-IDF + LR) | 700 | 1.000 | 1.000 | 1.000 | 1.000 | 1.0 | 0.000 |
| URL model (Gradient Boosting) | 647 | 0.992 | 0.994 | 0.991 | 0.993 | 0.9998 | 0.007 |
| Rules only: messages | 700 | 0.894 | 1.000 | 0.789 | 0.882 | 0.9948 | 0.000 |
| Hybrid engine: messages | 700 | 1.000 | 1.000 | 1.000 | 1.000 | 1.0 | 0.000 |
| Hybrid engine: email | 345 | 1.000 | 1.000 | 1.000 | 1.000 | 1.0 | 0.000 |
| Hybrid engine: SMS | 355 | 1.000 | 1.000 | 1.000 | 1.000 | 1.0 | 0.000 |
| Hybrid engine: URLs | 647 | 0.955 | 1.000 | 0.917 | 0.957 | 0.997 | 0.000 |

## Hybrid engine confusion matrix (messages)

| | Predicted legit | Predicted phish |
|---|---|---|
| **Actual legit** | 350 | 0 |
| **Actual phish** | 0 | 350 |

> Note: if these numbers come from the generated seed dataset they show the pipeline works end to end, not real-world accuracy. Import a public dataset (`scripts/import_public.py`) for meaningful results.
