import pytest

from app import create_app, defang, defang_text
from phishguard.engine import RiskEngine, level_for
from phishguard.ml import Models
from phishguard.parsers import from_email_fields, from_sms, from_url
from phishguard.storage import History


class NoModels(Models):
    def __init__(self):
        self.text = None
        self.url = None


@pytest.fixture
def rules_engine():
    return RiskEngine(models=NoModels())


def test_levels():
    assert level_for(0)[0] == "Low" and level_for(30)[0] == "Medium"
    assert level_for(60)[0] == "High" and level_for(90)[0] == "Critical"


def test_obvious_phish_scores_high_on_rules_alone(rules_engine):
    msg = from_email_fields(
        "PayPal Security <alert@paypa1-secure.top>", "Account suspended",
        "Dear Customer, your account will be suspended within 24 hours. Verify your account: http://paypa1-secure.top/login",
    )
    a = rules_engine.analyse(msg)
    assert a.score >= 75 and a.level == "Critical" and a.is_phishing
    assert a.explanation.startswith("Risk level CRITICAL")
    assert any(i.code == "url.typosquat" for i in a.indicators)


def test_legit_message_scores_low(rules_engine):
    a = rules_engine.analyse(from_sms("482913 is your OTP for login. Do not share it with anyone. -HDFC Bank", "VM-HDFCBK"))
    assert a.score < 25 and a.level == "Low"


def test_score_is_bounded_and_traceable(rules_engine):
    a = rules_engine.analyse(from_url("http://www.paypal.com@192.168.0.1:8080/paypal/login/verify/account.exe"))
    assert 0 <= a.score <= 100
    assert a.indicators and all(i.evidence for i in a.indicators)


def test_history_roundtrip(tmp_path, rules_engine):
    h = History(tmp_path / "h.db")
    msg = from_url("https://bit.ly/abc")
    a = rules_engine.analyse(msg)
    i = h.save(msg, a)
    row = h.get(i)
    assert row["score"] == a.score and row["result"]["level"] == a.level
    h.set_feedback(i, "phish")
    assert h.get(i)["feedback"] == "phish"
    assert h.stats()["total"] == 1
    h.delete(i)
    assert h.get(i) is None


def test_defang():
    assert defang("https://evil.top/x") == "hxxps://evil[.]top/x"
    assert "hxxp://a[.]xyz" in defang_text("go to http://a.xyz now")


@pytest.fixture
def client(tmp_path, rules_engine):
    app = create_app(db_path=tmp_path / "app.db", engine=rules_engine)
    app.config["TESTING"] = True
    return app.test_client()


def test_pages_render(client):
    for path in ["/", "/?channel=sms", "/?channel=url", "/history", "/metrics"]:
        assert client.get(path).status_code == 200, path


def test_analyse_flow(client):
    r = client.post("/analyse", data={"channel": "sms", "sender": "+919876543210",
                                      "body": "Your parcel is on hold. Pay Rs 25 redelivery fee at http://indiapost-help.top/pay"})
    assert r.status_code == 302 and "/result/" in r.headers["Location"]
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "risk" in page and "hxxp://indiapost-help[.]top" in page
    assert 'href="http://indiapost' not in page  # links are never rendered clickable
    assert "parcel" in client.get("/history").get_data(as_text=True)


def test_empty_submission_is_rejected(client):
    r = client.post("/analyse", data={"channel": "email"}, follow_redirects=True)
    assert "Paste a message" in r.get_data(as_text=True)


def test_json_api(client):
    r = client.post("/api/analyse", json={"channel": "url", "url": "http://192.168.1.1/login"})
    body = r.get_json()
    assert r.status_code == 200 and body["score"] > 0 and "indicators" in body and "id" in body
    assert client.post("/api/analyse", json={"channel": "fax"}).status_code == 400
