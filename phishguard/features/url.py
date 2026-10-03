"""Lexical / structural URL analysis. Never fetches the URL."""

from __future__ import annotations

import ipaddress
import math
import re
from collections import Counter
from urllib.parse import urlsplit

from ..message import Indicator
from .brands import ALL_OFFICIAL_DOMAINS, BRAND_DOMAINS

MULTI_PART_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "co.in", "org.in", "net.in", "gov.in", "ac.in",
    "com.au", "net.au", "org.au", "co.jp", "com.br", "com.cn", "co.za", "com.mx",
}
SUSPICIOUS_TLDS = {
    "xyz", "top", "tk", "ml", "ga", "cf", "gq", "club", "online", "site", "live", "click",
    "link", "work", "support", "buzz", "rest", "icu", "cam", "monster", "shop", "info", "ru",
}
SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly", "rebrand.ly",
    "cutt.ly", "shorturl.at", "rb.gy", "tiny.cc", "s.id", "t.ly",
}
SUSPICIOUS_WORDS = (
    "login", "log-in", "signin", "sign-in", "verify", "verification", "secure", "account",
    "update", "confirm", "banking", "password", "wallet", "unlock", "suspend", "billing",
    "kyc", "reward", "claim", "gift", "free", "bonus", "webscr", "auth",
)
RISKY_EXTENSIONS = (".exe", ".scr", ".apk", ".zip", ".rar", ".js", ".vbs", ".bat", ".msi", ".iso")
HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t"})

FEATURE_NAMES = [
    "url_length", "host_length", "path_length", "num_dots_host", "num_subdomains",
    "num_hyphens_host", "num_digits_host", "has_ip", "has_at", "is_https", "has_port",
    "suspicious_tld", "is_shortener", "has_punycode", "num_query_params", "num_special",
    "host_entropy", "suspicious_words", "brand_impersonation", "typosquat", "is_official",
    "risky_extension", "pct_encoded", "double_slash_path",
]


def _normalise(url: str) -> str:
    url = url.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "http://" + url
    return url


def split_host(url: str) -> tuple[str, str, str]:
    """Return (scheme, host, rest) for a URL, host lower-cased without port/userinfo."""
    try:
        parts = urlsplit(_normalise(url))
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:  # e.g. malformed IPv6 brackets
        return "", "", url
    rest = parts.path + (("?" + parts.query) if parts.query else "")
    return parts.scheme.lower(), host, rest


def registered_domain(host: str) -> str:
    """Best-effort eTLD+1 without a public-suffix download."""
    if _is_ip(host):
        return host
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return bool(re.fullmatch(r"(0x[0-9a-f]+|\d{8,10})", host))  # hex / decimal IPs


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    return -sum(c / len(s) * math.log2(c / len(s)) for c in counts.values())


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_official(host: str) -> bool:
    return registered_domain(host) in ALL_OFFICIAL_DOMAINS


def find_brand_impersonation(host: str, rest: str) -> str | None:
    """A brand name appears in the host/path but the domain does not belong to that brand."""
    reg = registered_domain(host)
    haystack = (host + rest).lower().replace("-", "").replace(".", " ")
    for brand, domains in BRAND_DOMAINS.items():
        if len(brand) < 4:  # avoid false hits for short names like "sbi", "irs"
            continue
        if brand in haystack and reg not in domains:
            return brand
    return None


def find_typosquat(host: str) -> tuple[str, str] | None:
    """Domain label is a near-miss of a brand (paypa1, arnazon, micros0ft...)."""
    reg = registered_domain(host)
    if reg in ALL_OFFICIAL_DOMAINS or _is_ip(host):
        return None
    # Check the whole label plus every hyphen/dot token: "paypa1-secure-login.xyz" -> "paypa1".
    labels = host.split(".")[:-1]
    tokens = {reg.split(".")[0].replace("-", "")}
    for label in labels:
        tokens.update(t for t in label.split("-") if len(t) >= 4)
    for token in tokens:
        deglyphed = token.translate(HOMOGLYPHS).replace("rn", "m").replace("vv", "w")
        for brand in BRAND_DOMAINS:
            if len(brand) < 5 or token == brand:
                continue
            if deglyphed == brand:
                return brand, reg
            if len(brand) < 6:  # edit distance on short names (steam/stream, chase/phase) is too noisy
                continue
            max_dist = 1 if len(brand) < 8 else 2
            if abs(len(token) - len(brand)) <= max_dist and levenshtein(token, brand) <= max_dist:
                return brand, reg
    return None


def url_features(url: str) -> dict[str, float]:
    scheme, host, rest = split_host(url)
    raw = url.strip()
    reg = registered_domain(host) if host else ""
    labels = host.split(".") if host else []
    reg_labels = reg.count(".") + 1 if reg and not _is_ip(host) else len(labels)
    lower = raw.lower()
    path = urlsplit(_normalise(raw)).path.lower() if host else ""
    return {
        "url_length": len(raw),
        "host_length": len(host),
        "path_length": len(rest),
        "num_dots_host": host.count("."),
        "num_subdomains": max(0, len(labels) - reg_labels),
        "num_hyphens_host": host.count("-"),
        "num_digits_host": sum(ch.isdigit() for ch in host),
        "has_ip": float(bool(host) and _is_ip(host)),
        "has_at": float("@" in raw.split("?")[0]),
        "is_https": float(scheme == "https"),
        "has_port": float(bool(re.search(r"://[^/]+:\d+", _normalise(raw)))),
        "suspicious_tld": float(host.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS) if host else 0.0,
        "is_shortener": float(reg in SHORTENERS or host in SHORTENERS),
        "has_punycode": float("xn--" in host),
        "num_query_params": rest.count("&") + (1 if "?" in rest else 0),
        "num_special": sum(lower.count(c) for c in "~_=%+!*$"),
        "host_entropy": round(_entropy(host), 3),
        "suspicious_words": sum(w in lower for w in SUSPICIOUS_WORDS),
        "brand_impersonation": float(bool(host) and find_brand_impersonation(host, rest) is not None),
        "typosquat": float(bool(host) and find_typosquat(host) is not None),
        "is_official": float(reg in ALL_OFFICIAL_DOMAINS),
        "risky_extension": float(path.endswith(RISKY_EXTENSIONS)),
        "pct_encoded": float(lower.count("%") >= 3),
        "double_slash_path": float("//" in rest),
    }


def url_vector(url: str) -> list[float]:
    f = url_features(url)
    return [float(f[name]) for name in FEATURE_NAMES]


def url_indicators(url: str) -> list[Indicator]:
    """Rule-based, human-readable findings for one URL."""
    scheme, host, rest = split_host(url)
    f = url_features(url)
    reg = registered_domain(host) if host else ""
    out: list[Indicator] = []

    def add(code, title, detail, weight):
        out.append(Indicator(f"url.{code}", "url", title, detail, weight, url))

    if f["is_official"]:
        add("official", "Link goes to a known official domain",
            f"{reg} is the genuine domain of a well-known organisation.", -10)
    if f["has_ip"]:
        add("ip_host", "Link uses a raw IP address",
            f"The link points to {host} instead of a named website. Legitimate companies almost never do this.", 25)
    if f["has_at"]:
        add("at_symbol", "Link contains an '@' trick",
            "Everything before '@' in a link is ignored by the browser, so the real destination is hidden.", 20)
    if (brand := find_brand_impersonation(host, rest)) if host else None:
        add("brand_mismatch", f"Mentions '{brand}' but is not {brand}'s website",
            f"The link uses the name '{brand}' while actually going to {reg}.", 30)
    if (ts := find_typosquat(host)) if host else None:
        add("typosquat", f"Look-alike of '{ts[0]}'",
            f"{ts[1]} is spelled to look like {ts[0]} but is a different domain.", 35)
    if f["has_punycode"]:
        add("punycode", "Internationalised (punycode) domain",
            "The domain uses special characters that can imitate normal letters.", 20)
    if f["is_shortener"]:
        add("shortener", "Shortened link hides the destination",
            f"{reg or host} is a URL shortener, so you cannot see where the link really goes.", 12)
    if f["suspicious_tld"] and not f["is_official"]:
        add("tld", f"Unusual domain ending '.{host.rsplit('.', 1)[-1]}'",
            "This domain ending is cheap and frequently used in scam campaigns.", 10)
    if f["num_subdomains"] >= 3:
        add("deep_subdomains", "Many nested subdomains",
            f"{host} stacks {int(f['num_subdomains'])} subdomains, a trick to push the real domain out of view.", 10)
    if f["num_hyphens_host"] >= 3:
        add("hyphens", "Many hyphens in the domain",
            "Domains like secure-login-account-update are typical of phishing kits.", 8)
    if f["suspicious_words"] >= 2 and not f["is_official"]:
        add("keywords", "Login / verification words in the link",
            "The link contains words like 'verify', 'login' or 'account' on a non-official site.", 10)
    if scheme == "http" and url.strip().lower().startswith("http://"):
        add("no_https", "Not using HTTPS",
            "The connection is not encrypted. Never enter passwords on such pages.", 5)
    if f["has_port"]:
        add("port", "Non-standard port in link", "The link specifies an unusual network port.", 8)
    if f["risky_extension"]:
        add("download", "Link downloads a program or archive",
            "The link points directly to an executable or archive file, which may be malware.", 25)
    if f["url_length"] > 100:
        add("long", "Very long link", "Unusually long links are often used to hide the real domain.", 5)
    return out
