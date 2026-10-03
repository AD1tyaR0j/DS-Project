"""Generate the seed labelled dataset (data/messages.csv, data/urls.csv).

The seed data is template-based so the full pipeline runs out of the box. It deliberately
includes "hard" cases: legitimate messages that sound urgent (OTP alerts, real delivery
updates, real bank alerts) and phishing that avoids obvious keywords. Seed metrics prove
the pipeline works; they are NOT a real-world benchmark. Use scripts/import_public.py to
add public datasets for meaningful numbers.

Usage:  python scripts/build_dataset.py [--n 700] [--seed 42]
"""

from __future__ import annotations

import argparse
import csv
import random
import string
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

NAMES = ["Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Ananya", "Rahul", "Meera", "Arjun", "Kavya",
         "John", "Sarah", "David", "Emily", "Michael", "Fatima", "Chen", "Lucas", "Olivia", "Noah"]
COMPANIES = ["Acme Corp", "Brightline", "Nimbus Labs", "Orbit Systems", "Zenith Tech", "Kite Analytics"]
SITES = ["github.com", "wikipedia.org", "stackoverflow.com", "python.org", "bbc.co.uk", "nytimes.com",
         "medium.com", "reddit.com", "zoom.us", "slack.com", "notion.so", "coursera.org", "irctc.co.in",
         "swiggy.com", "zomato.com", "myntra.com", "nptel.ac.in", "galgotiasuniversity.edu.in", "kaggle.com",
         "spotify.com", "airbnb.com", "booking.com", "uber.com", "ola.com"]
OFFICIAL = {
    "PayPal": "paypal.com", "Amazon": "amazon.in", "Netflix": "netflix.com", "HDFC Bank": "hdfcbank.com",
    "ICICI Bank": "icicibank.com", "Microsoft": "microsoft.com", "Apple": "apple.com", "Google": "google.com",
    "Flipkart": "flipkart.com", "LinkedIn": "linkedin.com", "DHL": "dhl.com", "Paytm": "paytm.com",
    "Instagram": "instagram.com", "Dropbox": "dropbox.com", "SBI": "sbi.co.in",
}
SMS_IDS = {"HDFC Bank": "VM-HDFCBK", "ICICI Bank": "AD-ICICIB", "SBI": "BZ-SBIINB", "Amazon": "AX-AMAZON",
           "Flipkart": "VK-FLPKRT", "Paytm": "JD-PAYTMB", "DHL": "VM-DHLIND", "Netflix": "AD-NFLIX"}
BAD_TLDS = ["xyz", "top", "info", "online", "site", "live", "click", "support", "ru", "tk", "shop", "co", "net", "com"]
SHORT = ["bit.ly", "tinyurl.com", "cutt.ly", "rb.gy", "is.gd"]
LURE_WORDS = ["secure", "login", "verify", "account", "update", "support", "help", "service", "auth", "kyc", "billing", "alert"]


def rand_code(n=6, chars=string.ascii_letters + string.digits):
    return "".join(random.choice(chars) for _ in range(n))


def amount():
    return random.choice(["Rs 499", "Rs 1,250", "₹2,999", "₹15,000", "$49.99", "$120.00", "Rs 25", "₹10"])


def phone():
    return "+91" + str(random.choice([6, 7, 8, 9])) + "".join(random.choice(string.digits) for _ in range(9))


def typo(word: str) -> str:
    w = word.lower().replace(" ", "")
    tricks = [lambda s: s.replace("l", "1", 1), lambda s: s.replace("o", "0", 1), lambda s: s.replace("m", "rn", 1),
              lambda s: s.replace("a", "4", 1), lambda s: s + random.choice(["-secure", "-online", "s", "-in"]),
              lambda s: s[:-1] + random.choice("aeiou") if len(s) > 4 else s + "x",
              lambda s: s.replace("i", "1", 1), lambda s: s[:2] + s[3:] if len(s) > 5 else s + "s"]
    out = random.choice(tricks)(w)
    return out if out != w else w + "-verify"


# --------------------------------------------------------------------------- URLs

def legit_url() -> str:
    roll = random.random()
    if roll < 0.45:
        dom = random.choice(SITES)
    else:
        dom = random.choice(list(OFFICIAL.values()))
    sub = random.choice(["", "www.", "www.", "", "help.", "accounts.", "m.", "docs."])
    path = random.choice(["", "/", "/account", "/orders/" + rand_code(8, string.digits), "/signin",
                          "/blog/" + rand_code(6, string.ascii_lowercase), "/search?q=" + rand_code(5, string.ascii_lowercase),
                          "/settings/security", "/track?id=" + rand_code(10), "/en-in/help", "/login?next=%2Fhome"])
    scheme = "https://" if random.random() < 0.93 else "http://"
    return f"{scheme}{sub}{dom}{path}"


def phish_url() -> str:
    brand = random.choice(list(OFFICIAL))
    b = brand.lower().replace(" ", "").replace("bank", "")
    kind = random.random()
    tld = random.choice(BAD_TLDS)
    lure = random.choice(LURE_WORDS)
    path = random.choice(["/login", "/verify", "/account/update", "/signin.php", "/kyc", "/secure/confirm",
                          "/" + rand_code(10), "/wp-content/" + b + "/index.html", "/pay?ref=" + rand_code(8), ""])
    scheme = "https://" if random.random() < 0.55 else "http://"  # many phishing sites have TLS now
    if kind < 0.18:
        host = f"{typo(b)}.{tld}"
    elif kind < 0.33:
        host = f"{b}-{lure}-{random.choice(LURE_WORDS)}.{tld}"
    elif kind < 0.45:
        host = f"{b}.{lure}.{rand_code(6, string.ascii_lowercase)}.{tld}"
    elif kind < 0.55:
        host = ".".join(str(random.randint(1, 254)) for _ in range(4))
        path = f"/{b}{path}"
    elif kind < 0.65:
        return f"https://{random.choice(SHORT)}/{rand_code(6)}"
    elif kind < 0.73:
        host = f"{rand_code(random.randint(7, 12), string.ascii_lowercase + string.digits)}.{tld}"
        path = path or "/" + lure
    elif kind < 0.80:
        host = f"www.{b}.com@{rand_code(8, string.ascii_lowercase)}.{tld}"
    elif kind < 0.87:  # quiet phish: plausible-looking non-brand domain
        host = f"{random.choice(['my', 'get', 'go', 'e'])}{random.choice(['parcel', 'refund', 'rewards', 'docs', 'portal'])}{random.choice(['hub', 'now', 'center', 'online'])}.com"
    elif kind < 0.93:
        host = f"{lure}-{b}.{random.choice(['com', 'net', 'in', 'co'])}"
    else:
        host = f"{rand_code(6, string.ascii_lowercase)}.{random.choice(['000webhostapp.com', 'weebly.com', 'firebaseapp.com', 'web.app', 'ngrok.io'])}"
        path = f"/{b}{path}"
    return f"{scheme}{host}{path}"


# ----------------------------------------------------------------------- messages

def legit_email() -> dict:
    name, brand = random.choice(NAMES), random.choice(list(OFFICIAL))
    dom = OFFICIAL[brand]
    company = random.choice(COMPANIES)
    cdom = company.lower().replace(" ", "") + ".com"
    t = random.randrange(10)
    if t == 0:
        return dict(sender=f"{brand} <no-reply@{dom}>", subject=f"Your {brand} order has shipped",
                    body=f"Hi {name},\n\nGood news! Your order #{rand_code(9, string.digits)} has shipped and will arrive by {random.choice(['Monday', 'Tuesday', 'Friday'])}. "
                         f"You can track it any time at https://www.{dom}/orders.\n\nThanks for shopping with us.")
    if t == 1:
        return dict(sender=f"{random.choice(NAMES)} <{random.choice(NAMES).lower()}@{cdom}>", subject=random.choice(["Notes from today's meeting", "Q3 report draft", "Lunch on Friday?", "Re: project timeline"]),
                    body=f"Hi {name},\n\nAttaching the notes from today. Can you review the second section before our sync on {random.choice(['Wednesday', 'Thursday'])}? "
                         f"The shared folder is on {random.choice(['https://docs.google.com/document/d/' + rand_code(16), 'https://' + cdom + '/wiki/' + rand_code(5)])}.\n\nThanks,\n{random.choice(NAMES)}")
    if t == 2:
        return dict(sender=f"{brand} Security <security@{dom}>", subject="New sign-in to your account",
                    body=f"Hi {name}, we noticed a new sign-in to your {brand} account from Chrome on Windows. If this was you, you don't need to do anything. "
                         f"If not, open the {brand} app or go to https://{dom}/security to review your activity. We will never ask for your password by email.")
    if t == 3:
        return dict(sender=f"{brand} <statements@{dom}>", subject=f"Your monthly statement is ready",
                    body=f"Dear {name},\n\nYour statement for {random.choice(['August', 'September', 'October'])} is now available. Log in through our official website or app to view it. "
                         f"Amount due: {amount()}. Due date: {random.randint(1, 28)}th.\n\nThis is an automated message.")
    if t == 4:
        return dict(sender=f"Newsletter <news@{random.choice(SITES)}>", subject=random.choice(["This week's top stories", "Your weekly digest", "5 tips for better sleep", "New courses this month"]),
                    body=f"Hello {name}, here's what's new this week. Read more at https://{random.choice(SITES)}/blog/{rand_code(6, string.ascii_lowercase)}. "
                         f"You're receiving this because you subscribed. Unsubscribe any time.")
    if t == 5:  # legit but urgent-sounding
        return dict(sender=f"IT Helpdesk <it@{cdom}>", subject="Reminder: password expires in 3 days",
                    body=f"Hi {name}, your corporate password expires in 3 days. Please change it from your laptop using Ctrl+Alt+Del > Change password, "
                         f"or visit the internal portal https://sso.{cdom}. Contact the helpdesk on ext. {random.randint(1000, 9999)} if you need help.")
    if t == 6:
        return dict(sender=f"{brand} <billing@{dom}>", subject="Payment received - thank you",
                    body=f"Hi {name}, we've received your payment of {amount()}. Receipt number {rand_code(10)}. No further action is needed.")
    if t == 7:
        return dict(sender=f"{random.choice(NAMES)} {random.choice(['Sharma', 'Patel', 'Smith', 'Khan'])} <recruiting@{cdom}>", subject="Interview schedule - Software Engineer",
                    body=f"Dear {name},\n\nThank you for applying to {company}. We would like to invite you for a technical interview next week. "
                         f"Please pick a slot using the calendar link on our careers page https://{cdom}/careers. There is no fee at any stage of our hiring process.\n\nRegards,\nTalent team")
    if t == 8:
        return dict(sender=f"{brand} <no-reply@{dom}>", subject="Verify your email address",
                    body=f"Hi {name}, thanks for signing up! Please confirm this is your email address by entering the code {rand_code(6, string.digits)} in the app. "
                         f"If you didn't create an account, you can ignore this email.")
    return dict(sender=f"{random.choice(NAMES)} <{random.choice(NAMES).lower()}{random.randint(1, 99)}@gmail.com>", subject=random.choice(["Photos from the trip", "Happy birthday!", "Dinner plans", "Book recommendation"]),
                body=f"Hey {name}! {random.choice(['Here are the photos from last weekend', 'Hope you have a great day', 'Are we still on for Saturday?', 'You have to read this one'])}. "
                     f"{random.choice(['Talk soon!', 'Call me later.', 'Miss you guys.', ''])}")


def phish_email() -> dict:
    name, brand = random.choice(NAMES), random.choice(list(OFFICIAL))
    url = phish_url()
    b = brand.lower().replace(" ", "")
    fake_dom = random.choice([f"{typo(b)}.com", f"{b}-{random.choice(LURE_WORDS)}.{random.choice(BAD_TLDS)}",
                              f"{random.choice(['mail', 'notify', 'alerts', 'service'])}{random.randint(1, 999)}.{random.choice(BAD_TLDS)}",
                              "gmail.com", "outlook.com", f"{rand_code(7, string.ascii_lowercase)}.com"])
    greet = random.choice(["Dear Customer", "Dear User", "Dear Valued Member", f"Hello {name}", f"Hi {name}", "Dear Account Holder", ""])
    t = random.randrange(10)
    if t == 0:
        subj, body = f"Your {brand} account has been suspended", f"{greet},\n\nWe detected unusual activity and your account has been temporarily suspended. To restore access, verify your account within 24 hours: {url}\n\nFailure to verify will result in permanent closure.\n\n{brand} Security Team"
    elif t == 1:
        subj, body = "Action required: update your payment details", f"{greet}, your recent payment could not be processed. Please update your billing information immediately to avoid service interruption. Update now: {url}"
    elif t == 2:
        subj, body = "Congratulations! You've been selected", f"{greet}, you have won a {random.choice(['iPhone 16', 'Rs 50,000 voucher', '$1000 gift card', 'free trip'])} in our annual customer draw! Claim your prize here {url} before it expires today. A small processing fee of {amount()} applies."
    elif t == 3:
        subj, body = f"Invoice #{rand_code(6, string.digits)} overdue", f"{greet},\n\nPlease find the overdue invoice attached. Kindly review and make payment at {url} to avoid late penalties.\n\nAccounts Department"
    elif t == 4:  # CEO / BEC fraud, no link
        subj, body = random.choice(["Quick favour", "Are you available?", "Urgent request"]), f"Hi {name}, I'm in a meeting and can't talk. I need you to buy {random.choice(['5', '8', '10'])} Google Play gift cards for a client today. Keep this confidential for now. Send me the codes once done. I'll reimburse you.\n\nSent from my iPhone"
    elif t == 5:
        subj, body = "Tax refund notification", f"{greet}, after the annual calculation of your fiscal activity, you are eligible to receive a tax refund of {amount()}. Income Tax Department requires you to submit the refund request: {url}"
    elif t == 6:
        subj, body = "Shared document: Q3_Salary_Revision.pdf", f"{random.choice(NAMES)} has shared a document with you via {random.choice(['DocuSign', 'Dropbox', 'OneDrive'])}. Sign in with your email password to view: {url}"
    elif t == 7:
        subj, body = "Work from home opportunity", f"{greet}! Part time job available. Earn Rs {random.choice(['3,000', '5,000', '8,000'])} per day by liking YouTube videos. No experience needed. Contact our HR on Telegram or register here: {url}. Registration fee {amount()} only."
    elif t == 8:  # quieter phish
        subj, body = random.choice(["Your mailbox is almost full", "Document review", "Delivery attempt failed"]), f"{greet}, {random.choice(['your storage quota is 98% used. Messages may stop arriving.', 'a document needs your review.', 'we could not deliver your package because the address was incomplete.'])} Please use the link below.\n{url}"
    else:
        subj, body = "KYC update pending", f"{greet}, your {brand} KYC is pending. Your account will be blocked today. Update KYC by sharing your PAN and OTP at {url} or reply with your card number."
    sender = f"{random.choice([brand, brand + ' Support', brand + ' Security', 'Customer Service', 'Admin'])} <{random.choice(['support', 'security', 'no-reply', 'service', 'admin'])}@{fake_dom}>"
    if t == 4:
        sender = f"{random.choice(NAMES)} {random.choice(['Sharma', 'Smith'])} (CEO) <ceo.office{random.randint(1, 99)}@gmail.com>"
    reply_to = f"help@{rand_code(6, string.ascii_lowercase)}.{random.choice(BAD_TLDS)}" if random.random() < 0.3 else ""
    return dict(sender=sender, subject=subj, body=body, reply_to=reply_to)


def legit_sms() -> dict:
    brand = random.choice(list(SMS_IDS))
    t = random.randrange(8)
    if t == 0:
        return dict(sender=SMS_IDS[brand], body=f"{rand_code(6, string.digits)} is your OTP for login. Valid for 10 minutes. Do not share it with anyone. -{brand}")
    if t == 1:
        return dict(sender=SMS_IDS[brand], body=f"{amount()} debited from A/c XX{random.randint(1000, 9999)} on {random.randint(1, 28)}-10-26 to UPI/{random.choice(NAMES).upper()}. Not you? Call {random.choice(['18002586161', '18001080'])}. -{brand}")
    if t == 2:
        return dict(sender=SMS_IDS.get("Amazon"), body=f"Your Amazon order #{rand_code(7, string.digits)} has been delivered. Rate your experience in the Amazon app.")
    if t == 3:
        return dict(sender=phone(), body=random.choice(["Hey, running 10 min late, order for me pls", "Call me when you're free", "Reached home. Thanks for today!", "Can you send me the notes from class?", "Happy birthday!! Party tonight?"]))
    if t == 4:
        return dict(sender=SMS_IDS["DHL"], body=f"Your DHL shipment {rand_code(10, string.digits)} is out for delivery today. Track: https://www.dhl.com/in-en/home/tracking.html")
    if t == 5:
        return dict(sender=SMS_IDS[brand], body=f"Dear Customer, your credit card statement is generated. Total due {amount()}. Pay by {random.randint(1, 28)}th via app or netbanking to avoid late fee. -{brand}")
    if t == 6:
        return dict(sender="VM-IRCTCI", body=f"PNR {rand_code(10, string.digits)}: Train {random.randint(10000, 22999)} confirmed, Coach B{random.randint(1, 6)} Berth {random.randint(1, 72)}. Happy journey.")
    return dict(sender=SMS_IDS["Flipkart"], body=f"Big Billion Days start tomorrow! Shop on the Flipkart app for deals on mobiles. T&C apply. To opt out reply STOP.")


def phish_sms() -> dict:
    brand = random.choice(list(OFFICIAL))
    url = phish_url()
    t = random.randrange(9)
    sender = phone() if random.random() < 0.7 else random.choice(["AD-ALERTS", "VK-NOTICE", "INFO", "BX-OFFER"])
    if t == 0:
        body = f"Dear Customer, your {brand} account will be blocked today. Update your KYC immediately: {url}"
    elif t == 1:
        body = f"India Post: Your parcel is on hold due to incomplete address. Pay {amount()} redelivery fee at {url} within 24 hrs."
    elif t == 2:
        body = f"Congratulations! You have won {amount()} cashback from {brand}. Claim your reward now {url}"
    elif t == 3:
        body = f"Your electricity connection will be disconnected tonight at 9:30 PM as previous bill was not updated. Contact officer {phone()} immediately."
    elif t == 4:
        body = f"{brand}: Unusual login detected. If this wasn't you, verify your account at {url}"
    elif t == 5:
        body = f"Hi, I am from {brand} HR. Part time job, earn Rs 5000 daily from home. WhatsApp {phone()} for details."
    elif t == 6:
        body = f"Your {brand} reward points worth {amount()} expire today! Redeem now: {url}"
    elif t == 7:
        body = f"Mom, I lost my phone, this is my new number. Can you send {amount()} urgently? I'll explain later."
    else:
        body = f"Refund of {amount()} initiated for your order. To receive it, share the OTP sent to your phone with our agent or visit {url}"
    return dict(sender=sender, body=body)


def build(n: int, seed: int) -> None:
    random.seed(seed)
    DATA.mkdir(exist_ok=True)
    rows = []
    for _ in range(n):
        rows.append({"channel": "email", **{"reply_to": ""}, **legit_email(), "label": "legit"})
        rows.append({"channel": "email", **phish_email(), "label": "phish"})
        rows.append({"channel": "sms", "subject": "", "reply_to": "", **legit_sms(), "label": "legit"})
        rows.append({"channel": "sms", "subject": "", "reply_to": "", **phish_sms(), "label": "phish"})
    random.shuffle(rows)
    cols = ["channel", "sender", "reply_to", "subject", "body", "label"]
    with open(DATA / "messages.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

    urls = [(legit_url(), "legit") for _ in range(n * 2)] + [(phish_url(), "phish") for _ in range(n * 2)]
    urls = list(dict.fromkeys(urls))
    random.shuffle(urls)
    with open(DATA / "urls.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["url", "label"])
        w.writerows(urls)
    print(f"wrote {len(rows)} messages and {len(urls)} urls to {DATA}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=700, help="examples per (channel, label) bucket")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    build(a.n, a.seed)
