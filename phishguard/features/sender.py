"""Sender, reply-to, header and link-consistency checks."""

from __future__ import annotations

import re

from ..message import Indicator, Message
from .brands import BRAND_DOMAINS, FREE_MAIL_DOMAINS
from .url import find_typosquat, registered_domain, split_host

BANK_WORDS = re.compile(r"\b(bank|banking|account|card|kyc|upi|wallet|payment|support|security|helpdesk|service)\b", re.I)


def _domain_of(address: str) -> str:
    return address.rsplit("@", 1)[-1].lower().strip(">").strip() if "@" in address else ""


def mentioned_brands(text: str) -> set[str]:
    low = text.lower().replace(" ", "")
    return {b for b in BRAND_DOMAINS if len(b) >= 4 and b in low}


def sender_indicators(msg: Message) -> list[Indicator]:
    out: list[Indicator] = []

    def add(code, title, detail, weight, evidence):
        out.append(Indicator(f"sender.{code}", "sender", title, detail, weight, evidence))

    if msg.channel == "email" and msg.sender:
        dom = _domain_of(msg.sender)
        reg = registered_domain(dom) if dom else ""
        name_brands = mentioned_brands(msg.sender_name + " " + msg.sender.split("@")[0])
        official_for = {b for b, ds in BRAND_DOMAINS.items() if reg in ds}

        for brand in sorted(name_brands - official_for):
            if reg and reg not in BRAND_DOMAINS[brand]:
                add("display_spoof", f"Sender claims to be '{brand}' but isn't",
                    f"The sender uses the name '{brand}' but the email actually comes from {reg}.", 30,
                    f"{msg.sender_name} <{msg.sender}>")
                break

        if reg in FREE_MAIL_DOMAINS and (name_brands or BANK_WORDS.search(msg.sender_name)):
            add("freemail_brand", "Company message sent from a free email account",
                f"Organisations send from their own domain, not from {reg}.", 20, msg.sender)

        if dom and (ts := find_typosquat(dom)):
            add("typosquat", f"Sender domain imitates '{ts[0]}'",
                f"{ts[1]} looks like {ts[0]}'s domain but is a different one.", 35, msg.sender)

        if msg.reply_to:
            rdom = registered_domain(_domain_of(msg.reply_to))
            if rdom and reg and rdom != reg:
                add("reply_mismatch", "Replies go to a different address",
                    f"The message is from {reg} but replies are sent to {rdom}. Attackers do this to receive your answers.", 15,
                    f"Reply-To: {msg.reply_to}")

        if official_for and not out:
            add("official", "Sent from an official company domain",
                f"{reg} belongs to a known organisation (note: sender addresses can be forged; check the header results).", -5,
                msg.sender)

    if msg.channel == "sms" and msg.sender:
        digits = re.sub(r"\D", "", msg.sender)
        looks_personal = len(digits) >= 10 and not re.search(r"[A-Za-z]", msg.sender)
        if looks_personal and (mentioned_brands(msg.body) or BANK_WORDS.search(msg.body)):
            add("personal_number", "Bank/company SMS from a personal number",
                "Banks and companies send SMS from registered short codes or sender IDs (e.g. VM-HDFCBK), not ordinary mobile numbers.", 15,
                msg.sender)
    return out


def header_indicators(msg: Message) -> list[Indicator]:
    out: list[Indicator] = []
    auth = (msg.headers.get("Authentication-Results", "") + " " + msg.headers.get("Received-SPF", "")).lower()
    for check, weight in (("spf", 15), ("dkim", 15), ("dmarc", 20)):
        if re.search(rf"\b{check}=(fail|softfail|permerror)", auth) or (check == "spf" and auth.strip().startswith(("fail", "softfail"))):
            out.append(Indicator(f"meta.{check}_fail", "metadata", f"{check.upper()} check failed",
                                 f"The email failed the {check.upper()} authentication check, so the sender address may be forged.",
                                 weight, check + "=fail"))
    rp = msg.headers.get("Return-Path", "")
    if rp and msg.sender:
        rp_dom, from_dom = registered_domain(_domain_of(rp)), registered_domain(_domain_of(msg.sender))
        if rp_dom and from_dom and rp_dom != from_dom:
            out.append(Indicator("meta.return_path", "metadata", "Bounce address doesn't match sender",
                                 f"The technical return address is at {rp_dom} while the visible sender is {from_dom}.",
                                 8, f"Return-Path: {rp}"))
    return out


def consistency_indicators(msg: Message) -> list[Indicator]:
    """Cross-checks between what the message says and where its links go."""
    out: list[Indicator] = []

    for href, text in msg.anchors:
        shown = re.search(r"(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", text.lower())
        if not shown or not href.lower().startswith(("http", "www")):
            continue
        shown_reg = registered_domain(shown.group(1))
        real_reg = registered_domain(split_host(href)[1])
        if shown_reg and real_reg and shown_reg != real_reg:
            out.append(Indicator("link.text_mismatch", "url", "Link text hides a different destination",
                                 f"The link shows '{shown_reg}' but actually opens {real_reg}.", 30, f"{text} → {href}"))
            break

    brands = mentioned_brands(msg.full_text + " " + msg.sender_name)
    if brands and msg.urls:
        link_regs = {registered_domain(split_host(u)[1]) for u in msg.urls}
        for brand in sorted(brands):
            official = BRAND_DOMAINS[brand]
            if link_regs and not (link_regs & official):
                out.append(Indicator("link.brand_mismatch", "url", f"Talks about {brand} but links elsewhere",
                                     f"The message is about {brand}, yet none of its links go to {brand}'s official site "
                                     f"({', '.join(sorted(link_regs))[:80]}).", 20, ", ".join(sorted(link_regs))[:120]))
                break
    return out
