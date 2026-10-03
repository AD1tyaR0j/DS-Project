"""Hybrid risk engine: rule indicators + ML probabilities -> score, level, evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

from .explain import explain
from .features.sender import consistency_indicators, header_indicators, sender_indicators
from .features.text import text_indicators
from .features.url import url_indicators
from .message import Indicator, Message
from .ml import Models, top_text_terms, text_of

# Caps stop one noisy category from dominating the score.
CATEGORY_CAPS = {"language": 45, "url": 55, "sender": 45, "metadata": 35, "model": 40}
MAX_URLS = 10

LEVELS = [
    (75, "Critical", "Strong phishing or fraud signals. Do not click, reply or pay. Report and delete it."),
    (50, "High", "This is likely phishing or a scam. Do not click links, open attachments or share any details."),
    (25, "Medium", "Some warning signs. Verify the sender through a channel you trust before acting."),
    (0, "Low", "No strong warning signs found. Stay alert, and never share OTPs or passwords."),
]


@dataclass
class Assessment:
    score: int
    level: str
    advice: str
    indicators: list[Indicator]
    explanation: str
    text_probability: float | None = None
    url_probability: float | None = None
    url_reports: dict[str, list[Indicator]] = field(default_factory=dict)

    @property
    def is_phishing(self) -> bool:
        return self.score >= 50

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "advice": self.advice,
            "explanation": self.explanation,
            "text_probability": self.text_probability,
            "url_probability": self.url_probability,
            "indicators": [i.to_dict() for i in self.indicators],
            "urls": {u: [i.to_dict() for i in inds] for u, inds in self.url_reports.items()},
        }


def level_for(score: int) -> tuple[str, str]:
    for threshold, name, advice in LEVELS:
        if score >= threshold:
            return name, advice
    return LEVELS[-1][1], LEVELS[-1][2]


def _model_indicator(code: str, label: str, p: float, scale_up: int, evidence: str) -> Indicator | None:
    """Turn a probability into signed risk points. Confident-legit pulls the score down a little."""
    if p >= 0.5:
        weight = round((p - 0.5) * 2 * scale_up)
        if weight < 3:
            return None
        return Indicator(code, "model", f"AI model: {label} looks like phishing ({p:.0%})",
                         f"A machine-learning model trained on labelled phishing and legitimate examples rates this {p:.0%} likely to be malicious.",
                         weight, evidence)
    weight = -round((0.5 - p) * 2 * 10)
    if weight > -3:
        return None
    return Indicator(code, "model", f"AI model: {label} looks legitimate ({1 - p:.0%})",
                     "The machine-learning model finds this similar to legitimate messages.", weight, evidence)


class RiskEngine:
    def __init__(self, models: Models | None = None, use_llm: bool = False):
        self.models = models if models is not None else Models()
        self.use_llm = use_llm

    def analyse(self, msg: Message) -> Assessment:
        indicators: list[Indicator] = []
        if msg.channel != "url":
            indicators += text_indicators(msg.full_text)
            indicators += sender_indicators(msg)
            indicators += header_indicators(msg)
            indicators += consistency_indicators(msg)

        # URLs: score each, keep the worst one's rule indicators (avoid double counting many links).
        url_reports: dict[str, list[Indicator]] = {}
        url_probs: dict[str, float] = {}
        for u in msg.urls[:MAX_URLS]:
            url_reports[u] = url_indicators(u)
            if (p := self.models.url_proba(u)) is not None:
                url_probs[u] = p
        if url_reports:
            worst = max(url_reports, key=lambda u: (sum(i.weight for i in url_reports[u]), url_probs.get(u, 0)))
            indicators += url_reports[worst]

        text_p = self.models.text_proba(msg) if msg.channel != "url" else None
        if text_p is not None:
            terms = top_text_terms(self.models.text, text_of(msg)) if text_p >= 0.5 else []
            ind = _model_indicator("model.text", "message content", text_p, 40,
                                   ("Key phrases: " + ", ".join(terms)) if terms else "")
            if ind:
                indicators.append(ind)
        url_p = max(url_probs.values()) if url_probs else None
        if url_p is not None:
            worst_url = max(url_probs, key=url_probs.get)
            ind = _model_indicator("model.url", "link", url_p, 40 if msg.channel == "url" else 30, worst_url)
            if ind:
                indicators.append(ind)

        score = self._score(indicators)
        level, advice = level_for(score)
        indicators.sort(key=lambda i: -i.weight)
        assessment = Assessment(score, level, advice, indicators, "", text_p, url_p, url_reports)
        assessment.explanation = explain(msg, assessment, use_llm=self.use_llm)
        return assessment

    @staticmethod
    def _score(indicators: list[Indicator]) -> int:
        by_cat: dict[str, int] = {}
        for i in indicators:
            by_cat[i.category] = by_cat.get(i.category, 0) + i.weight
        total = sum(min(v, CATEGORY_CAPS.get(c, 40)) for c, v in by_cat.items())
        return max(0, min(100, total))
