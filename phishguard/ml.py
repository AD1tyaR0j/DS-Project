"""Machine-learning models: a text classifier and a URL classifier."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .features.url import FEATURE_NAMES, url_vector
from .message import Message

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
TEXT_MODEL = MODEL_DIR / "text_model.joblib"
URL_MODEL = MODEL_DIR / "url_model.joblib"


def message_to_text(channel: str, sender: str, subject: str, body: str) -> str:
    """Flatten a message into the string the text model sees. Sender domain is a useful token."""
    dom = sender.rsplit("@", 1)[-1] if "@" in sender else sender
    return f"[{channel}] from:{dom} {subject} \n {body}"


def text_of(msg: Message) -> str:
    return message_to_text(msg.channel, msg.sender, msg.subject, msg.body)


def build_text_model() -> Pipeline:
    features = FeatureUnion([
        ("words", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=40000)),
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True, max_features=60000)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")),
    ])


def build_url_model() -> GradientBoostingClassifier:
    return GradientBoostingClassifier(n_estimators=250, max_depth=3, learning_rate=0.08, random_state=0)


def url_matrix(urls: list[str]) -> np.ndarray:
    return np.array([url_vector(u) for u in urls], dtype=float)


STOP_TERMS = {"and", "the", "to", "a", "of", "in", "is", "for", "on", "you", "your", "this", "it", "or", "be", "at",
              "by", "we", "our", "with", "http", "https", "www", "com", "the link", "link", "from", "sms", "email"}


def top_text_terms(model: Pipeline, text: str, k: int = 6) -> list[str]:
    """Word n-grams in this message that pushed the text model most towards 'phish'."""
    union: FeatureUnion = model.named_steps["features"]
    words: TfidfVectorizer = dict(union.transformer_list)["words"]
    coef = model.named_steps["clf"].coef_[0][: len(words.vocabulary_)]
    vec = words.transform([text]).tocoo()
    contrib = sorted(((v * coef[j], j) for j, v in zip(vec.col, vec.data)), reverse=True)
    names = words.get_feature_names_out()
    terms = [names[j] for c, j in contrib if c > 0 and names[j] not in STOP_TERMS
             and not names[j].startswith(("from", "sms ", "email "))
             and not all(w in STOP_TERMS for w in names[j].split())]
    return terms[:k]


def top_url_features(model: GradientBoostingClassifier, k: int = 3) -> list[str]:
    order = np.argsort(model.feature_importances_)[::-1][:k]
    return [FEATURE_NAMES[i] for i in order]


class Models:
    """Lazily loaded trained models. Missing models degrade gracefully to rules only."""

    def __init__(self, model_dir: Path = MODEL_DIR):
        self.text = joblib.load(model_dir / TEXT_MODEL.name) if (model_dir / TEXT_MODEL.name).exists() else None
        self.url = joblib.load(model_dir / URL_MODEL.name) if (model_dir / URL_MODEL.name).exists() else None

    @property
    def available(self) -> bool:
        return self.text is not None or self.url is not None

    def text_proba(self, msg: Message) -> float | None:
        if self.text is None or not (msg.body or msg.subject):
            return None
        return float(self.text.predict_proba([text_of(msg)])[0][1])

    def url_proba(self, url: str) -> float | None:
        if self.url is None:
            return None
        return float(self.url.predict_proba(url_matrix([url]))[0][1])


def save(model, path: Path) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, path)

