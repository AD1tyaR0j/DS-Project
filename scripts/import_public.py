"""Append public labelled datasets to data/messages.csv and data/urls.csv.

Download the datasets yourself, then point this script at the files:

  # UCI SMS Spam Collection (tab separated: "ham<TAB>text" / "spam<TAB>text")
  python scripts/import_public.py --sms-spam path/to/SMSSpamCollection

  # Any message CSV with a text column and a label column
  python scripts/import_public.py --messages path/to/emails.csv --text-col body --label-col label --channel email

  # Any URL CSV (e.g. PhishTank export + Tranco top sites) with url + label columns
  python scripts/import_public.py --urls path/to/urls.csv --url-col url --label-col label

Labels are mapped to phish/legit: spam, phishing, malicious, bad, fraud, 1, true -> phish.
Use --replace to overwrite the seed data instead of appending to it.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
PHISH_LABELS = {"spam", "phish", "phishing", "malicious", "bad", "fraud", "scam", "1", "true", "yes", "defacement", "malware"}
MSG_COLS = ["channel", "sender", "reply_to", "subject", "body", "label"]


def to_label(value: str) -> str:
    return "phish" if str(value).strip().lower() in PHISH_LABELS else "legit"


def _write(path: Path, cols: list[str], rows: list[dict], replace: bool) -> None:
    exists = path.exists() and not replace
    with open(path, "a" if exists else "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"{'appended' if exists else 'wrote'} {len(rows)} rows -> {path}")


def import_sms_spam(path: str, replace: bool) -> None:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "\t" not in line:
                continue
            label, text = line.rstrip("\n").split("\t", 1)
            rows.append({"channel": "sms", "body": text, "label": to_label(label)})
    _write(DATA / "messages.csv", MSG_COLS, rows, replace)


def import_messages(path: str, text_col: str, label_col: str, channel: str, replace: bool) -> None:
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rows = [
            {"channel": channel, "sender": r.get("sender", r.get("from", "")), "subject": r.get("subject", ""),
             "body": r[text_col], "label": to_label(r[label_col])}
            for r in csv.DictReader(fh) if r.get(text_col)
        ]
    _write(DATA / "messages.csv", MSG_COLS, rows, replace)


def import_urls(path: str, url_col: str, label_col: str, replace: bool) -> None:
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rows = [{"url": r[url_col], "label": to_label(r[label_col])} for r in csv.DictReader(fh) if r.get(url_col)]
    _write(DATA / "urls.csv", ["url", "label"], rows, replace)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sms-spam")
    ap.add_argument("--messages")
    ap.add_argument("--urls")
    ap.add_argument("--text-col", default="text")
    ap.add_argument("--url-col", default="url")
    ap.add_argument("--label-col", default="label")
    ap.add_argument("--channel", default="email", choices=["email", "sms"])
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()
    if a.sms_spam:
        import_sms_spam(a.sms_spam, a.replace)
    if a.messages:
        import_messages(a.messages, a.text_col, a.label_col, a.channel, a.replace)
    if a.urls:
        import_urls(a.urls, a.url_col, a.label_col, a.replace)
    if not (a.sms_spam or a.messages or a.urls):
        ap.print_help()
