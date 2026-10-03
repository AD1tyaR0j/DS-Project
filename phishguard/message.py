"""Core data types shared across the pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Message:
    """A normalised message, regardless of the channel it came from."""

    channel: str  # "email" | "sms" | "url"
    body: str = ""
    sender: str = ""  # email address, phone number or short code
    sender_name: str = ""  # display name, if any
    reply_to: str = ""
    subject: str = ""
    urls: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    anchors: list[tuple[str, str]] = field(default_factory=list)  # (href, visible text) from HTML

    @property
    def full_text(self) -> str:
        return f"{self.subject}\n{self.body}".strip()


@dataclass
class Indicator:
    """One piece of evidence contributing to the risk score."""

    code: str  # stable identifier, e.g. "url.ip_host"
    category: str  # "language" | "url" | "sender" | "metadata" | "model"
    title: str  # short human label
    detail: str  # one-sentence explanation for the user
    weight: int  # risk points contributed (can be negative for trust signals)
    evidence: str = ""  # the exact snippet / value that triggered it

    def to_dict(self) -> dict:
        return asdict(self)
