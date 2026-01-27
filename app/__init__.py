import os
from datetime import datetime
from flask import Flask, render_template, redirect, session, url_for, request, flash
from .db import get_db, init_db

# =====================================================
# Flask App Factory
# =====================================================

def create_app(test_config: dict | None = None) -> Flask:
    """
    Skapar och konfigurerar Flask-applikationen.
    Används både för runtime och tester.
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

    # -------------------------------------------------
    # App Configuration
    # -------------------------------------------------
    default_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.db")
    app.config.update(
        DB_PATH=default_db,
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    # -------------------------------------------------
    # Initiera databasen
    # -------------------------------------------------
    init_db(app)

    # =================================================
    # Template Filters
    # =================================================
    @app.template_filter("fmt_dt")
    def fmt_dt(value: str) -> str:
        """
        Tar ISO-datetime som: 2026-01-26T18:49:28 (ev även med sekunder/tz)
        och returnerar: 2026-01-26 18:49
        """
        if not value:
            return ""
        # Hantera ev 'Z' eller timezone
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")

    # =================================================
    # Routes
    # =================================================

    @app.route("/")
    def index():
        """
        Root → redirect till dashboard
        """
        return redirect(url_for("dashboard"))

    @app.route("/dashboard", methods=["GET"])
    def dashboard():
        """
        Startsidan som visar alla Echo meddelanden
        """
        with get_db(app) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM echoes
                ORDER BY created_at DESC;
                """
            ).fetchall()

        return render_template(
            "index.html",
            echoes=rows
        )
    
    @app.route("/create_echo", methods=["POST"])
    def create_echo():
        """
        Skapar en ny echo
        """
        echo = (request.form.get("echo") or "").strip()
        status = (request.form.get("status") or "draft").strip()
        user_id = 1  # Temporär hårdkodad user_id för demoändamål

        if not echo:
            flash("Echo krävs.", "danger")
            return redirect(url_for("dashboard"))

        now = datetime.now().isoformat(timespec="seconds")

        with get_db(app) as conn:
            conn.execute(
                """
                INSERT INTO echoes (echo, status, user_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (echo, status, user_id, now),
            )

        flash("Echo skapad!", "success")
        return redirect(url_for("dashboard"))
    
    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("Du har loggats ut.", "info")
        return redirect(url_for("dashboard"))

    return app
