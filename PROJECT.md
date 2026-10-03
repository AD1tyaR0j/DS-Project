# PhishGuard: AI-Powered Phishing and Digital Fraud Defense

**Domain:** Cybersecurity / Artificial Intelligence
**Difficulty:** Medium-Hard

---

## 1. Background

Digital fraud increasingly works by convincing users rather than defeating complex technical infrastructure. Phishing messages can look like legitimate emails, SMS messages, social-media messages, payment requests, job offers or account alerts. Attackers also use automation and AI-assisted techniques to make social-engineering messages more convincing and to send them at scale.

Most consumer security tools either depend on manually reported threats or show generic warnings without explaining *why* a particular message is suspicious. This project builds an intelligent system that looks at the context, language, links, sender behaviour and other indicators of a message **before** the user interacts with it.

## 2. Problem Statement

Develop an AI-powered system that analyses potentially suspicious digital messages and identifies phishing, impersonation, scam or social-engineering characteristics before a user acts on them.

The system accepts inputs such as emails, SMS messages, URLs or message text and generates a **risk assessment supported by understandable evidence**. It focuses on **detection and explanation**, never on automatically taking irreversible action.

For this proof of concept we pick **two communication channels, Email and SMS**, and demonstrate the complete pipeline from input analysis to risk explanation and user warning. Standalone URL checks are supported as a third, lighter input mode.

## 3. Expected Solution (requirements checklist)

| # | Requirement | Where it lives |
|---|-------------|----------------|
| R1 | Analyse message text, sender information, URLs and available metadata | `phishguard/features/*`, `phishguard/parsers.py` |
| R2 | Identify suspicious patterns associated with phishing and impersonation | `phishguard/features/text.py`, `phishguard/features/sender.py` |
| R3 | Detect malicious or deceptive URLs using feature analysis | `phishguard/features/url.py`, URL classifier |
| R4 | Generate an understandable risk explanation, not just a binary result | `phishguard/explain.py` |
| R5 | Assign a risk level with supporting indicators | `phishguard/engine.py` |
| R6 | Provide a user-facing warning / review interface | `app/` (Flask web UI) |
| R7 | Keep a history of analysed messages and results | `phishguard/storage.py` (SQLite) |
| R8 | Evaluate against a labelled dataset of legitimate and malicious examples | `scripts/evaluate.py`, `reports/` |

## 4. Expected Outcomes

- Better identification of phishing and digital-fraud attempts
- Less dependence on users spotting scams on their own
- Explainable warnings that help users understand suspicious behaviour
- Measurable detection performance on a suitable evaluation dataset

## 5. Architecture

```
            ┌──────────────────────── Input ─────────────────────────┐
            │  Email (raw .eml or fields) │ SMS text │ single URL     │
            └──────────────┬──────────────────────────────────────────┘
                           ▼
                 parsers.py → Message(channel, sender, reply_to,
                                      subject, body, urls, headers)
                           ▼
   ┌───────────────┬───────────────┬────────────────┬──────────────────┐
   │ Text features │ URL features  │ Sender features│ Header/metadata  │
   │ (urgency,     │ (IP host,     │ (display-name  │ (SPF/DKIM result,│
   │  credential   │  look-alike   │  spoofing,     │  reply-to        │
   │  asks, money, │  domains,     │  free-mail     │  mismatch)       │
   │  threats …)   │  shorteners…) │  brand claims) │                  │
   └──────┬────────┴──────┬────────┴───────┬────────┴────────┬─────────┘
          ▼               ▼                ▼                 ▼
   ML text model    ML URL model     Rule indicators (weighted, with evidence)
   (TF-IDF + LR)    (Gradient Boost)
          └───────────────┴────────┬───────┘
                                   ▼
                 engine.py → risk score 0–100, level, indicators
                                   ▼
                 explain.py → plain-language explanation
                 (template-based; optional LLM rewrite with Claude)
                                   ▼
               Web UI warning + SQLite history + evaluation reports
```

### Risk levels

| Score | Level | User guidance |
|-------|-------|---------------|
| 0–24 | **Low** | Looks normal. Stay alert. |
| 25–49 | **Medium** | Some warning signs. Verify the sender through a separate channel. |
| 50–74 | **High** | Likely phishing or scam. Do not click links or reply. |
| 75–100 | **Critical** | Strong phishing / fraud signals. Report and delete. |

The score blends the ML probabilities with the weighted rule indicators, so every point on the score can be traced back to a listed piece of evidence.

## 6. Tech Stack

- **Python 3.10+**
- **scikit-learn**: TF-IDF + Logistic Regression (text), Gradient Boosting (URL features)
- **Flask**: review/warning web interface
- **SQLite**: analysis history
- **Anthropic Claude API (optional)**: rewrites the explanation in friendlier language when `ANTHROPIC_API_KEY` is set; the system works fully offline without it
- **pytest**: tests

## 7. Dataset and Evaluation

- `data/messages.csv`: labelled email + SMS examples (`channel, sender, subject, body, label`), where label is `phish` or `legit`.
- `data/urls.csv`: labelled URLs (`url, label`).
- The repo ships with a **generated seed dataset** (`scripts/build_dataset.py`) so the pipeline runs end-to-end out of the box. Seed-data metrics show the pipeline works; they are **not** a real-world benchmark.
- For real numbers, drop in public datasets with the same columns:
  - UCI SMS Spam Collection (SMS)
  - Enron / Nazario phishing corpus (email)
  - PhishTank / OpenPhish + Tranco top sites (URLs)
- Metrics reported: accuracy, precision, recall, F1, ROC-AUC and the confusion matrix, for the ML models alone **and** for the full hybrid engine.

## 8. Milestones

1. ✅ Spec (this document)
2. Core feature extractors (text, URL, sender, headers) + message parsers
3. Dataset builder, ML models, training script
4. Risk engine + explanation generator
5. SQLite history
6. Flask web UI: analyse, result warning, history, metrics
7. Evaluation script + report
8. Tests, README, demo instructions
9. *(Stretch)* Browser extension that calls the local API to check links in Gmail/web pages

## 9. Non-goals / Safety

- The system **never** deletes, blocks, forwards or replies to messages. It only warns.
- No live fetching of suspicious URLs by default (avoids visiting attacker infrastructure). All URL analysis is lexical/structural.
- Message history stays in a local SQLite file.
