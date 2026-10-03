"""Social-engineering language patterns, each with an explanation and evidence snippet."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..message import Indicator


@dataclass(frozen=True)
class Pattern:
    code: str
    title: str
    detail: str
    weight: int
    regex: re.Pattern


def _p(code: str, title: str, detail: str, weight: int, *phrases: str) -> Pattern:
    return Pattern(code, title, detail, weight, re.compile("|".join(phrases), re.I))


PATTERNS: list[Pattern] = [
    _p("urgency", "Creates a false sense of urgency",
       "Scammers rush you so you act before thinking. Real organisations rarely demand action within hours.", 12,
       r"\burgent(ly)?\b", r"\bimmediate(ly)?\b", r"\bact now\b", r"within \d+ ?(hours?|hrs?|minutes?|mins?)",
       r"\b(expires?|expiring) (today|soon|in)\b", r"\blast (chance|warning|reminder)\b", r"\bfinal (notice|warning)\b",
       r"\basap\b", r"\btime[- ]sensitive\b", r"\bright away\b", r"\btoday only\b"),
    _p("threat", "Threatens negative consequences",
       "The message threatens account closure, fines or legal action to frighten you into complying.", 15,
       r"\b(account|card|service|number|sim|wallet)\b.{0,40}\b(suspend|suspended|lock|locked|block|blocked|clos(e|ed)|deactivat\w*|terminat\w*|disabled)\b",
       r"\blegal action\b", r"\barrest(ed)? warrant\b", r"\bpenalt(y|ies)\b", r"\bpolice\b.{0,30}\b(case|complaint)\b",
       r"\bwill be (charged|fined|reported)\b"),
    _p("credential_request", "Asks you to log in or verify your account",
       "Phishing usually leads to a fake login page that steals your username and password.", 18,
       r"\bverify (your )?(account|identity|details|information|email)\b", r"\bconfirm (your )?(account|identity|password|details)\b",
       r"\bupdate (your )?(account|payment|billing|bank|kyc|card) (details|information|info)?\b",
       r"\b(log ?in|sign ?in) (now |here )?to (restore|unlock|verify|avoid|continue|reactivate)\b",
       r"\bre-?activate your account\b", r"\bunusual (sign[- ]in|login) activity\b", r"\bkyc\b.{0,30}\b(update|pending|expired?)\b"),
    _p("sensitive_data", "Requests sensitive information",
       "No genuine bank or company will ask for your OTP, PIN, CVV or full card number by message.", 25,
       r"\b(shar(e|ing)|send(ing)?|enter(ing)?|provid(e|ing)|tell|reply with|confirm(ing)?|verify(ing)?|updat(e|ing)|submit(ting)?)\b.{0,30}\b(otp|pin|cvv|password|card number|aadhaar|pan( card)?|ssn|social security|bank details|login details)\b",
       r"\b(otp|cvv|pin)\b.{0,20}\b(to|for) (verify|confirm|complete|receive)\b"),
    _p("prize", "Promises a prize, refund or reward",
       "Unexpected winnings, refunds and cashback are classic bait to get you to click or pay.", 15,
       r"\byou('ve| have)? (won|been selected)\b", r"\bcongratulations\b", r"\blottery\b", r"\bjackpot\b",
       r"\bclaim (your )?(prize|reward|refund|gift|cashback|bonus)\b", r"\b(free|win) (iphone|gift card|voucher)\b",
       r"\b(refund|cashback) of\b", r"\bselected (as|for) (a )?winner\b"),
    _p("payment_request", "Asks for money or unusual payment",
       "Requests to pay fees, buy gift cards or transfer crypto are strong signs of fraud.", 18,
       r"\b(processing|registration|clearance|customs|delivery|redelivery|release) fee\b", r"\bgift ?cards?\b.{0,30}\b(buy|purchase|send)\b",
       r"\b(buy|purchase|send)\b.{0,30}\bgift ?cards?\b", r"\b(bitcoin|btc|usdt|crypto)\b.{0,30}\b(send|transfer|pay|wallet)\b",
       r"\bwire (transfer|the money)\b", r"\b(transfer|send|pay)\b.{0,20}\b(rs\.?|inr|₹|\$|usd)\s?\d", r"\bpay (a|the) small (fee|amount)\b"),
    _p("job_scam", "Too-good-to-be-true job offer",
       "Easy money for little work, or paying to get a job, is a common recruitment scam.", 15,
       r"\bwork from home\b.{0,60}\b(earn|income|salary)\b", r"\bearn\b.{0,20}(rs\.?|₹|\$|inr)\s?[\d,]+.{0,20}\b(per|a|/)\s?(day|daily|hour|week)\b",
       r"\bpart[- ]time (job|work)\b.{0,60}\b(earn|daily|salary)\b", r"\bno experience (needed|required)\b",
       r"\blike (videos|youtube videos|posts) and earn\b", r"\b(telegram|whatsapp)\b.{0,30}\b(hr|recruiter|task)\b"),
    _p("delivery_scam", "Fake delivery problem",
       "Fake 'parcel on hold' messages trick you into paying fees or entering card details.", 14,
       r"\b(package|parcel|shipment|delivery)\b.{0,40}\b(on hold|held|could not be delivered|failed|pending|undeliverable|returned)\b",
       r"\b(reschedule|confirm) (your )?(delivery|address)\b", r"\bincomplete (address|house number)\b"),
    _p("generic_greeting", "Generic greeting",
       "Your real bank or provider normally addresses you by name, not 'Dear Customer'.", 6,
       r"\bdear (valued )?(customer|user|client|member|account ?holder|sir|madam|sir/madam|beneficiary|friend)\b",
       r"\bhello (customer|user)\b"),
    _p("click_bait", "Pushes you to click a link",
       "The message is built around getting you to click, which is where the attack happens.", 6,
       r"\bclick (here|the link|below|on the link|this link)\b", r"\btap (here|the link)\b", r"\bopen the (attached|link)\b",
       r"\bdownload the (attached|app|apk)\b"),
    _p("secrecy", "Asks you to keep it secret",
       "Being told to keep a request confidential (e.g. from colleagues or family) is a manipulation tactic.", 12,
       r"\bkeep (this|it) (confidential|between us|secret)\b", r"\bdon'?t (tell|inform) (anyone|your)\b",
       r"\bi('m| am) (in a meeting|busy).{0,40}\b(gift cards?|transfer|favou?r)\b"),
    _p("authority", "Claims to be a government or authority body",
       "Scammers pose as tax, police, customs or regulators because people fear them. These bodies don't demand payment by message.", 10,
       r"\b(irs|income tax department|tax refund|customs department|cyber ?cell|cbi|rbi|reserve bank|trai|fbi)\b"),
]

CATEGORY = "language"


def _snippet(text: str, m: re.Match, pad: int = 35) -> str:
    start, end = max(0, m.start() - pad), min(len(text), m.end() + pad)
    s = text[start:end].replace("\n", " ").strip()
    return ("…" if start > 0 else "") + s + ("…" if end < len(text) else "")


def text_indicators(text: str) -> list[Indicator]:
    out: list[Indicator] = []
    for p in PATTERNS:
        m = p.regex.search(text)
        if m:
            out.append(Indicator(f"text.{p.code}", CATEGORY, p.title, p.detail, p.weight, _snippet(text, m)))

    letters = [c for c in text if c.isalpha()]
    if len(letters) > 30 and sum(c.isupper() for c in letters) / len(letters) > 0.5:
        out.append(Indicator("text.shouting", CATEGORY, "Written mostly in capital letters",
                             "Heavy use of capitals is a pressure tactic rarely used by real companies.", 5,
                             text[:60]))
    if text.count("!") >= 3:
        out.append(Indicator("text.exclaim", CATEGORY, "Lots of exclamation marks",
                             "Excessive exclamation marks are typical of scam and spam messages.", 3, "!" * min(text.count("!"), 6)))
    return out


def text_flags(text: str) -> dict[str, int]:
    """Binary pattern hits, used as extra features in evaluation."""
    return {p.code: int(bool(p.regex.search(text))) for p in PATTERNS}
