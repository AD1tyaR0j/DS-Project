from phishguard.features.sender import consistency_indicators, header_indicators, sender_indicators
from phishguard.features.text import text_indicators
from phishguard.features.url import find_typosquat, registered_domain, url_features, url_indicators
from phishguard.parsers import extract_urls, from_email_fields, from_sms, parse_eml


def codes(indicators):
    return {i.code for i in indicators}


# ---------------------------------------------------------------- URLs

def test_registered_domain_handles_multi_part_suffixes():
    assert registered_domain("www.sbi.co.in") == "sbi.co.in"
    assert registered_domain("a.b.paypal.com") == "paypal.com"


def test_official_domain_is_a_trust_signal():
    assert codes(url_indicators("https://www.paypal.com/signin")) == {"url.official"}


def test_ip_host_and_brand_in_path():
    c = codes(url_indicators("http://192.168.4.2/hdfc/login.php"))
    assert "url.ip_host" in c


def test_typosquats_are_detected():
    for url in ["http://paypa1-secure.xyz", "https://arnazon.in", "https://micros0ft-support.com"]:
        assert "url.typosquat" in codes(url_indicators(url)), url


def test_similar_but_unrelated_domains_are_not_typosquats():
    for host in ["stream.com", "github.com", "phase.io", "google.com"]:
        assert find_typosquat(host) is None, host


def test_at_symbol_trick_and_shortener():
    assert "url.at_symbol" in codes(url_indicators("http://www.paypal.com@evil.xyz/login"))
    assert "url.shortener" in codes(url_indicators("https://bit.ly/3xYz"))


def test_url_features_are_numeric_and_complete():
    from phishguard.features.url import FEATURE_NAMES
    f = url_features("http://secure.login.account.amazon.verify-user.top/a")
    assert list(f) == FEATURE_NAMES
    assert f["num_subdomains"] >= 3 and f["brand_impersonation"] == 1.0


def test_malformed_url_does_not_crash():
    url_indicators("http://[::1")
    url_features("")


# ---------------------------------------------------------------- language

def test_social_engineering_language():
    c = codes(text_indicators(
        "URGENT: Dear Customer, your account will be suspended. Verify your account and share your OTP now."))
    assert {"text.urgency", "text.threat", "text.credential_request", "text.sensitive_data", "text.generic_greeting"} <= c


def test_payment_and_job_scams():
    assert "text.payment_request" in codes(text_indicators("Pay the redelivery fee of Rs 25 to release your parcel"))
    assert "text.job_scam" in codes(text_indicators("Part time job! Earn Rs 5,000 per day. No experience needed"))


def test_ordinary_message_has_no_language_flags():
    assert text_indicators("Hi Priya, notes from today's meeting are attached. See you Thursday.") == []


# ---------------------------------------------------------------- sender / headers / consistency

def test_display_name_spoof_and_reply_to_mismatch():
    msg = from_email_fields("PayPal Support <support@paypal-alerts.info>", "Hi", "body", "x@gmail.com")
    assert {"sender.display_spoof", "sender.reply_mismatch"} <= codes(sender_indicators(msg))


def test_official_sender_is_trusted():
    msg = from_email_fields("Amazon <no-reply@amazon.in>", "Order shipped", "Your order shipped.")
    assert codes(sender_indicators(msg)) == {"sender.official"}


def test_bank_sms_from_personal_number():
    msg = from_sms("Your HDFC bank account is blocked, update KYC", "+919812345678")
    assert "sender.personal_number" in codes(sender_indicators(msg))
    assert sender_indicators(from_sms("482913 is your OTP. -HDFC Bank", "VM-HDFCBK")) == []


def test_link_text_mismatch_in_html():
    msg = from_email_fields("a@b.com", "", '<a href="http://evil.top/x">https://www.amazon.in/orders</a>')
    assert "link.text_mismatch" in codes(consistency_indicators(msg))


def test_failed_authentication_headers():
    raw = (b"From: PayPal <service@paypal.com>\r\nTo: you@example.com\r\nSubject: Hi\r\n"
           b"Authentication-Results: mx.example.com; spf=fail smtp.mailfrom=evil.top; dkim=none; dmarc=fail\r\n"
           b"Return-Path: <bounce@evil.top>\r\n\r\nHello")
    c = codes(header_indicators(parse_eml(raw)))
    assert {"meta.spf_fail", "meta.dmarc_fail", "meta.return_path"} <= c


# ---------------------------------------------------------------- parsers

def test_extract_urls_from_text_and_html():
    urls = extract_urls('Go to http://a.xyz/p, or <a href="https://b.com/q">here</a> or www.c.top now.')
    assert urls[:1] == ["https://b.com/q"] and "http://a.xyz/p" in urls and "www.c.top" in urls


def test_parse_multipart_eml_prefers_plain_text():
    raw = (b"From: Bob <bob@example.com>\r\nSubject: Test\r\nMIME-Version: 1.0\r\n"
           b"Content-Type: multipart/alternative; boundary=XX\r\n\r\n"
           b"--XX\r\nContent-Type: text/plain\r\n\r\nPlain body http://p.com\r\n"
           b"--XX\r\nContent-Type: text/html\r\n\r\n<p>HTML <a href=\"http://h.com\">link</a></p>\r\n--XX--\r\n")
    msg = parse_eml(raw)
    assert msg.sender == "bob@example.com" and msg.sender_name == "Bob"
    assert "Plain body" in msg.body
    assert {"http://h.com", "http://p.com"} <= set(msg.urls)
