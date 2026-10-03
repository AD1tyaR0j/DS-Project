# PhishGuard

**Explainable phishing and digital-fraud detection for emails, SMS and links.**

PhishGuard analyses a suspicious message *before* you act on it. It checks the language, the sender, the links and the email headers, combines rule-based evidence with machine-learning models, and gives you a risk score (0–100), a risk level, and a plain-language explanation of every warning sign.

It only warns. It never opens links, deletes messages, or replies.

See [PROJECT.md](PROJECT.md) for the full problem statement, requirements and architecture.

## Features

| Requirement | How PhishGuard does it |
|---|---|
| Analyse text, sender, URLs and metadata | Parsers for raw `.eml` files, email fields, SMS text and single URLs |
| Spot phishing / impersonation patterns | 12 social-engineering language patterns (urgency, threats, OTP/CVV requests, prizes, job and delivery scams, CEO fraud…), display-name spoofing, free-mail "banks", reply-to tricks, SMS from personal numbers |
| Detect deceptive URLs | 24 lexical features: look-alike domains (`paypa1`, `arnazon`, `micros0ft`), brand-in-wrong-domain, raw IPs, `@` tricks, punycode, shorteners, risky TLDs, executable downloads, and link text that hides a different destination. URLs are **never visited**. |
| Explain, don't just classify | Each indicator carries a title, an explanation and the exact evidence snippet; the explanation is generated from them (optionally rewritten by Claude) |
| Risk level with indicators | Hybrid score = capped rule points + ML probabilities → Low / Medium / High / Critical |
| Warning / review interface | Flask web app with a colour-coded verdict, evidence list, defanged links and a "was this right?" feedback button |
| History | Every analysis is stored in SQLite with filters by risk level and user feedback |
| Evaluation | Held-out test split; reports accuracy, precision, recall, F1, ROC-AUC, FPR and confusion matrix for each model, rules-only and the hybrid engine |

**Channels covered:** Email and SMS (plus standalone link checks).

## Quick start

```bash
pip install -r requirements.txt
```

```bash
python scripts/build_dataset.py
```

```bash
python scripts/train.py
```

```bash
python scripts/evaluate.py
```

```bash
python run.py
```

Then open http://127.0.0.1:5000.

Run the tests:

```bash
python -m pytest -q
```

### Optional: LLM explanations

Set `ANTHROPIC_API_KEY` and `PHISHGUARD_LLM=1` before `python run.py`. Claude (`claude-opus-5-5` by default, override with `PHISHGUARD_LLM_MODEL`) rewrites the explanation using only the evidence PhishGuard found. If the API is unavailable, the built-in template explanation is used.

## How the score works

1. **Rules** produce indicators, each worth risk points (negative points for trust signals such as an official domain).
2. **Text model** (TF-IDF word + character n-grams → Logistic Regression) and **URL model** (Gradient Boosting on the 24 URL features) produce probabilities. These become indicators too, so the score stays traceable.
3. Points are summed per category with caps (language 45, url 55, sender 45, metadata 35, model 40) so no single category dominates, then clamped to 0–100.

| Score | Level | Advice |
|---|---|---|
| 0–24 | Low | No strong warning signs |
| 25–49 | Medium | Verify the sender through a channel you trust |
| 50–74 | High | Likely a scam, don't click or reply |
| 75–100 | Critical | Strong phishing signals, report and delete |

## Dataset and evaluation

`scripts/build_dataset.py` generates a **seed dataset** (2,800 labelled email/SMS messages and ~2,600 URLs) from templates, including deliberately hard cases such as genuine OTP and delivery messages and phishing without obvious keywords. It lets the whole pipeline run out of the box.

Latest results on the held-out 25% split are in [reports/evaluation.md](reports/evaluation.md) and on the **Evaluation** page of the app.

> ⚠️ **Read the seed numbers carefully.** Because seed messages come from templates, the ML models score close to 100% on them. That proves the pipeline works end to end, **not** that it reaches that accuracy in the real world. The rules-only row is a better guide to the generalising part of the system.

For meaningful numbers, import public datasets with the same column layout:

```bash
python scripts/import_public.py --sms-spam path/to/SMSSpamCollection
```

```bash
python scripts/import_public.py --urls path/to/phishing_urls.csv --url-col url --label-col label
```

Then re-run `train.py` and `evaluate.py`. Good sources: UCI SMS Spam Collection, Nazario phishing corpus + Enron (email), PhishTank / OpenPhish + Tranco top sites (URLs).

## JSON API

```bash
curl -X POST http://127.0.0.1:5000/api/analyse -H "Content-Type: application/json" -d "{\"channel\": \"url\", \"url\": \"http://paypa1-login.xyz/verify\"}"
```

`channel` is `email` (`sender`, `reply_to`, `subject`, `body`), `sms` (`sender`, `body`) or `url` (`url`). Pass `"save": false` to skip history. `GET /api/history` lists recent results. This API is what a future browser extension would call.

## Project layout

```
phishguard/
  message.py          Message and Indicator types
  parsers.py          .eml / email fields / SMS / URL -> Message
  features/
    url.py            URL features + indicators (look-alikes, IPs, shorteners…)
    text.py           social-engineering language patterns
    sender.py         sender, header (SPF/DKIM/DMARC) and link-consistency checks
    brands.py         commonly impersonated brands and their real domains
  ml.py               text + URL models
  engine.py           hybrid risk scoring
  explain.py          template explanations (+ optional Claude rewrite)
  storage.py          SQLite history
app/                  Flask UI + JSON API
scripts/              build_dataset, import_public, train, evaluate
data/                 labelled datasets
reports/              evaluation output
tests/                pytest suite
```

## Roadmap

- Browser extension that checks links in Gmail / web pages through the JSON API
- Screenshot input (OCR) for messages shared as images
- Domain-age / reputation lookups (WHOIS, Safe Browsing) as optional online signals
- Retraining from user feedback stored in history
