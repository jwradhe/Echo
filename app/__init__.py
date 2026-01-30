import os
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, session, url_for, request, flash
from pymysql import cursors
from .config import get_config
from .db import get_db, init_connection_pool, ensure_default_user

logger = logging.getLogger(__name__)

def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    env = os.environ.get("FLASK_ENV", "development")
    config = get_config(env)
    app.config.from_object(config)
    
    logger.info(f"Loaded configuration for {env.upper()} environment")
    
    if test_config:
        app.config.update(test_config)
        logger.debug("Applied test configuration overrides")
    
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
    logging.basicConfig(
        level=log_level,
        format=app.config.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    try:
        init_connection_pool(app)
        logger.info(f"Connected to MySQL database: {app.config['MYSQL_DATABASE']}")
        ensure_default_user(app)
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e}")
        if app.config.get("ENV") == "production":
            raise
    @app.template_filter("fmt_dt")
    def fmt_dt(value) -> str:
        """
        Tar ISO-datetime som: 2026-01-26T18:49:28 (ev även med sekunder/tz)
        eller datetime object och returnerar: 2026-01-26 18:49
        """
        if not value:
            return ""
        
        # Om det är redan ett datetime object, konvertera direkt
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        
        # Annars behandla som sträng
        value = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")

    @app.route("/")
    def index():
        return redirect(url_for("dashboard"))

    @app.route("/dashboard", methods=["GET"])
    def dashboard():
        try:
            with get_db(app) as conn:
                cursor = conn.cursor(cursors.DictCursor)
                cursor.execute(
                    """
                    SELECT p.post_id, p.content, p.created_at, p.updated_at,
                           u.username, u.display_name
                    FROM Posts p
                    LEFT JOIN Users u ON p.user_id = u.user_id
                    WHERE p.is_deleted = FALSE
                    ORDER BY p.created_at DESC
                    LIMIT 50;
                    """
                )
                posts = cursor.fetchall()
                cursor.close()
            
            return render_template(
                "index.html",
                echoes=posts  # Keep variable name for template compatibility
            )
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return f"<h1>Error loading dashboard</h1><p>{str(e)}</p>", 500
    
    @app.route("/create_echo", methods=["POST"])
    def create_echo():
        from uuid import uuid4
        
        content = (request.form.get("echo") or "").strip()
        user_id = request.form.get("user_id") or "00000000-0000-0000-0000-000000000000"

        if not content:
            flash("Echo krävs.", "danger")
            return redirect(url_for("dashboard"))

        try:
            post_id = str(uuid4())
            now = datetime.now().isoformat(timespec="seconds")

            with get_db(app) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO Posts (post_id, user_id, content, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (post_id, user_id, content, now, now),
                )
                cursor.close()

            flash("Echo skapad!", "success")
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            flash(f"Fel vid skapande av echo: {str(e)}", "danger")
        
        return redirect(url_for("dashboard"))
    
    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("Du har loggats ut.", "info")
        return redirect(url_for("dashboard"))

    return app
