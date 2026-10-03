"""Flask review / warning interface for PhishGuard."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for

from phishguard.engine import LEVELS, RiskEngine
from phishguard.ml import Models
from phishguard.parsers import URL_RE, from_email_fields, from_sms, from_url, parse_eml
from phishguard.storage import DEFAULT_DB, History

ROOT = Path(__file__).resolve().parent.parent
MAX_EML_BYTES = 2 * 1024 * 1024


def defang(url: str) -> str:
    """Make a URL safe to display: not clickable, not auto-linked by mail clients."""
    return re.sub(r"^http", "hxxp", url.strip(), flags=re.I).replace(".", "[.]")


def defang_text(text: str) -> str:
    """Defang every URL inside a piece of free text, leaving the rest untouched."""
    return URL_RE.sub(lambda m: defang(m.group(0)), text)


def build_message(form, files):
    channel = form.get("channel", "email")
    if channel == "email":
        eml = files.get("eml")
        if eml and eml.filename:
            raw = eml.read(MAX_EML_BYTES + 1)
            if len(raw) > MAX_EML_BYTES:
                raise ValueError("The .eml file is larger than 2 MB.")
            return parse_eml(raw)
        return from_email_fields(form.get("sender", ""), form.get("subject", ""), form.get("body", ""), form.get("reply_to", ""))
    if channel == "sms":
        return from_sms(form.get("body", ""), form.get("sender", ""))
    if channel == "url":
        return from_url(form.get("url", ""))
    raise ValueError(f"Unknown channel: {channel}")


def create_app(db_path: str | Path | None = None, engine: RiskEngine | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("PHISHGUARD_SECRET", "dev-only-change-me")
    app.config["MAX_CONTENT_LENGTH"] = MAX_EML_BYTES + 64 * 1024
    history = History(db_path or os.environ.get("PHISHGUARD_DB", DEFAULT_DB))
    engine = engine or RiskEngine(Models(), use_llm=os.environ.get("PHISHGUARD_LLM", "0") == "1")
    app.jinja_env.filters["defang"] = defang
    app.jinja_env.filters["defang_text"] = defang_text

    @app.context_processor
    def globals_():
        return {"models_loaded": engine.models.available, "levels": [lvl for _, lvl, _ in reversed(LEVELS)]}

    @app.get("/")
    def index():
        return render_template("index.html", channel=request.args.get("channel", "email"))

    @app.post("/analyse")
    def analyse():
        try:
            msg = build_message(request.form, request.files)
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("index"))
        if not (msg.body.strip() or msg.subject.strip() or msg.urls):
            flash("Paste a message, upload an .eml file or enter a URL to analyse.")
            return redirect(url_for("index", channel=msg.channel))
        assessment = engine.analyse(msg)
        analysis_id = history.save(msg, assessment)
        return redirect(url_for("result", analysis_id=analysis_id))

    @app.get("/result/<int:analysis_id>")
    def result(analysis_id: int):
        row = history.get(analysis_id) or abort(404)
        return render_template("result.html", row=row, r=row["result"])

    @app.post("/result/<int:analysis_id>/feedback")
    def feedback(analysis_id: int):
        history.get(analysis_id) or abort(404)
        history.set_feedback(analysis_id, request.form.get("verdict", ""))
        flash("Thanks, your feedback was saved.")
        return redirect(url_for("result", analysis_id=analysis_id))

    @app.post("/result/<int:analysis_id>/delete")
    def delete(analysis_id: int):
        history.delete(analysis_id)
        flash("Removed from history.")
        return redirect(url_for("history_view"))

    @app.get("/history")
    def history_view():
        level = request.args.get("level") or None
        return render_template("history.html", rows=history.recent(200, level), level=level, stats=history.stats())

    @app.get("/metrics")
    def metrics():
        path = ROOT / "reports" / "metrics.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        return render_template("metrics.html", m=data)

    # JSON API: lets other clients (e.g. a browser extension) use the same engine.
    @app.post("/api/analyse")
    def api_analyse():
        payload = request.get_json(silent=True) or {}
        try:
            msg = build_message(payload, {})
        except ValueError as e:
            return jsonify(error=str(e)), 400
        assessment = engine.analyse(msg)
        out = assessment.to_dict()
        if payload.get("save", True):
            out["id"] = history.save(msg, assessment)
        return jsonify(out)

    @app.get("/api/history")
    def api_history():
        return jsonify([{k: v for k, v in r.items() if k != "body"} for r in history.recent(int(request.args.get("limit", 50)))])

    return app
