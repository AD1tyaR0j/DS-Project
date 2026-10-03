"""Turn raw input (an .eml file, form fields, SMS text, a URL) into a Message."""

from __future__ import annotations

import email
import html
import re
from email import policy
from email.utils import parseaddr

from .message import Message

URL_RE = re.compile(
    r"""(?xi)
    \b(
      (?:https?://|www\.)[^\s<>"'()]+
      |
      (?:[a-z0-9-]+\.)+(?:com|net|org|info|xyz|top|io|co|in|ru|cn|ly|me|biz|online|site|club|live|app|link|click|shop|support|tk|ml|ga|cf|gq)(?:/[^\s<>"'()]*)?
    )
    """
)
HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
ANCHOR_RE = re.compile(r"""(?is)<a\s[^>]*href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""")
TAG_RE = re.compile(r"<[^>]+>")


def extract_urls(text: str) -> list[str]:
    """Find URLs in free text and HTML href attributes, de-duplicated, in order."""
    found: list[str] = []
    for m in HREF_RE.finditer(text):
        found.append(m.group(1))
    for m in URL_RE.finditer(text):
        found.append(m.group(1).rstrip(".,;:!?"))
    seen, out = set(), []
    for u in found:
        if u.lower().startswith(("mailto:", "tel:", "#")):
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_anchors(raw_html: str) -> list[tuple[str, str]]:
    return [
        (href.strip(), html.unescape(TAG_RE.sub("", text)).strip())
        for href, text in ANCHOR_RE.findall(raw_html)
    ]


def html_to_text(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", text)
    return html.unescape(TAG_RE.sub(" ", text))


def from_email_fields(
    sender: str = "", subject: str = "", body: str = "", reply_to: str = ""
) -> Message:
    name, addr = parseaddr(sender)
    _, reply_addr = parseaddr(reply_to)
    return Message(
        channel="email",
        sender=addr or sender.strip(),
        sender_name=name,
        reply_to=reply_addr,
        subject=subject,
        body=body,
        urls=extract_urls(body),
        anchors=extract_anchors(body),
    )


def parse_eml(raw: bytes | str) -> Message:
    """Parse a raw RFC-822 email (the contents of an .eml file)."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="replace")
    msg = email.message_from_bytes(raw, policy=policy.default)

    plain, html_part = "", ""
    for part in msg.walk() if msg.is_multipart() else [msg]:
        ctype = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        try:
            content = part.get_content()
        except Exception:  # malformed parts should not kill the analysis
            continue
        if ctype == "text/plain" and not plain:
            plain = content
        elif ctype == "text/html" and not html_part:
            html_part = content

    body = plain or html_to_text(html_part)
    urls = extract_urls(html_part + "\n" + body)
    name, addr = parseaddr(str(msg.get("From", "")))
    _, reply_addr = parseaddr(str(msg.get("Reply-To", "")))
    headers = {
        k: str(msg.get(k, ""))
        for k in ("Authentication-Results", "Received-SPF", "Return-Path", "Date", "Message-ID")
        if msg.get(k)
    }
    return Message(
        channel="email",
        sender=addr,
        sender_name=name,
        reply_to=reply_addr,
        subject=str(msg.get("Subject", "")),
        body=body,
        urls=urls,
        headers=headers,
        anchors=extract_anchors(html_part),
    )


def from_sms(text: str, sender: str = "") -> Message:
    return Message(channel="sms", sender=sender.strip(), body=text, urls=extract_urls(text))


def from_url(url: str) -> Message:
    url = url.strip()
    return Message(channel="url", body=url, urls=[url] if url else [])
