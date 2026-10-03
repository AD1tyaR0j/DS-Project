"""Brands commonly impersonated in phishing, mapped to their real domains."""

BRAND_DOMAINS: dict[str, set[str]] = {
    "paypal": {"paypal.com", "paypal.me"},
    "apple": {"apple.com", "icloud.com"},
    "microsoft": {"microsoft.com", "live.com", "outlook.com", "office.com", "microsoftonline.com"},
    "office365": {"office.com", "microsoft.com"},
    "outlook": {"outlook.com", "live.com"},
    "google": {"google.com", "gmail.com", "youtube.com"},
    "gmail": {"gmail.com", "google.com"},
    "amazon": {"amazon.com", "amazon.in", "amazon.co.uk", "amazonaws.com"},
    "netflix": {"netflix.com"},
    "facebook": {"facebook.com", "fb.com", "meta.com"},
    "instagram": {"instagram.com"},
    "whatsapp": {"whatsapp.com", "whatsapp.net"},
    "linkedin": {"linkedin.com"},
    "dropbox": {"dropbox.com"},
    "docusign": {"docusign.com", "docusign.net"},
    "adobe": {"adobe.com"},
    "chase": {"chase.com"},
    "wellsfargo": {"wellsfargo.com"},
    "bankofamerica": {"bankofamerica.com"},
    "hdfc": {"hdfcbank.com"},
    "hdfcbank": {"hdfcbank.com"},
    "icici": {"icicibank.com"},
    "icicibank": {"icicibank.com"},
    "sbi": {"sbi.co.in", "onlinesbi.sbi", "onlinesbi.com"},
    "axisbank": {"axisbank.com"},
    "paytm": {"paytm.com"},
    "phonepe": {"phonepe.com"},
    "flipkart": {"flipkart.com"},
    "dhl": {"dhl.com"},
    "fedex": {"fedex.com"},
    "usps": {"usps.com"},
    "indiapost": {"indiapost.gov.in"},
    "irs": {"irs.gov"},
    "coinbase": {"coinbase.com"},
    "binance": {"binance.com"},
    "steam": {"steampowered.com", "steamcommunity.com"},
}

ALL_OFFICIAL_DOMAINS: set[str] = set().union(*BRAND_DOMAINS.values())

# Free webmail providers: a "bank" writing from one of these is a red flag.
FREE_MAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.co.in", "hotmail.com", "outlook.com", "live.com",
    "aol.com", "protonmail.com", "proton.me", "icloud.com", "mail.com", "gmx.com",
    "yandex.com", "zoho.com", "rediffmail.com",
}
