"""Train the text and URL models on data/messages.csv and data/urls.csv.

A fixed 25% test split (stratified, seed 42) is held out and never used for training,
so scripts/evaluate.py reports honest held-out numbers.

Usage:  python scripts/train.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402

from phishguard import ml  # noqa: E402

SEED = 42
TEST_SIZE = 0.25


def load_messages() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "messages.csv", keep_default_na=False)
    df["text"] = [ml.message_to_text(c, s, sub, b) for c, s, sub, b in zip(df.channel, df.sender, df.subject, df.body)]
    df["y"] = (df.label == "phish").astype(int)
    return df


def load_urls() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "urls.csv", keep_default_na=False)
    df["y"] = (df.label == "phish").astype(int)
    return df


def split(df: pd.DataFrame):
    return train_test_split(df, test_size=TEST_SIZE, random_state=SEED, stratify=df.y)


def main() -> None:
    msgs_train, msgs_test = split(load_messages())
    text_model = ml.build_text_model().fit(msgs_train.text, msgs_train.y)
    ml.save(text_model, ml.TEXT_MODEL)
    print(f"text model: trained on {len(msgs_train)} messages "
          f"(held-out accuracy {text_model.score(msgs_test.text, msgs_test.y):.3f})")

    urls_train, urls_test = split(load_urls())
    url_model = ml.build_url_model().fit(ml.url_matrix(list(urls_train.url)), urls_train.y)
    ml.save(url_model, ml.URL_MODEL)
    print(f"url model:  trained on {len(urls_train)} urls "
          f"(held-out accuracy {url_model.score(ml.url_matrix(list(urls_test.url)), urls_test.y):.3f})")
    print(f"saved to {ml.MODEL_DIR}")


if __name__ == "__main__":
    main()
