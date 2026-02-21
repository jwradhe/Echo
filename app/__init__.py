import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, current_user, login_required
from pymysql import cursors
from .db import get_db, init_connection_pool, ensure_default_user, ensure_default_admin

logger = logging.getLogger(__name__)

def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    project_root = Path(__file__).resolve().parents[1]
    base_env_file = project_root / ".env"
    env_hint = os.environ.get("FLASK_ENV", "development")
    if env_hint != "testing" and base_env_file.exists():
        load_dotenv(base_env_file, override=True)

    env = os.environ.get("FLASK_ENV", "development")
    if env not in ("development", "testing"):
        env_file = project_root / f".env.{env}"
        if env_file.exists():
            load_dotenv(env_file, override=True)
    from .config import get_config
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
        if env == "development":
            ensure_default_admin(app)
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

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"
    login_manager.init_app(app)

    from .auth import load_user_by_id
    from .auth_routes import auth_bp

    @login_manager.user_loader
    def load_user(user_id: str):
        return load_user_by_id(user_id)

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        if request.path.startswith("/api/"):
            return {"error": "Authentication required"}, 401
        return redirect(url_for("auth.login", next=request.full_path))

    app.register_blueprint(auth_bp)

    # =================================================
    # Routes
    # =================================================

    @app.route("/")
    def index():
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
                db_posts = cursor.fetchall()
                cursor.close()

            posts = []
            for row in db_posts:
                display_name = row.get("display_name") or row.get("username") or "Unknown"
                username = row.get("username") or "unknown"
                posts.append(
                    {
                        "id": row.get("post_id"),
                        "author": {
                            "name": display_name,
                            "username": username,
                            "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
                        },
                        "content": row.get("content"),
                        "timestamp": row.get("created_at"),
                        "likes": 0,
                        "comments": 0,
                        "bookmarks": 0,
                        "isLiked": False,
                        "isBookmarked": False,
                    }
                )
            
            return render_template(
                "index.html",
                posts=posts,  # Keep variable name for template compatibility
                current_user=current_user
            )
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return f"<h1>Error loading dashboard</h1><p>{str(e)}</p>", 500

    @app.route("/dashboard")
    def dashboard():
        return index()
    
    @app.route("/create_echo", methods=["POST"])
    @login_required
    def create_echo():
        from uuid import uuid4
        
        content = (request.form.get("echo") or "").strip()
        user_id = current_user.get_id()

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

    @app.route("/edit_echo/<post_id>", methods=["POST"])
    @login_required
    def edit_echo(post_id):
        user_id = current_user.get_id()

        if not post_id:
            flash("Ogiltigt echo ID.", "danger")
            return redirect(url_for("dashboard"))

        if request.is_json:
            data = request.get_json()
            new_content = data.get("content", "").strip()
        else:
            new_content = request.form.get("content", "").strip()

        if not new_content:
            if request.is_json:
                return jsonify({"success": False, "error": "Innehållet får inte vara tomt."}), 400
            flash("Innehållet får inte vara tomt.", "danger")
            return redirect(url_for("dashboard"))

        if len(new_content) > 500:
            if request.is_json:
                return jsonify({"success": False, "error": "Max 500 tecken."}), 400
            flash("Max 500 tecken.", "danger")
            return redirect(url_for("dashboard"))

        try:
            with get_db(app) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE Posts
                    SET content = %s
                    WHERE post_id = %s AND user_id = %s AND is_deleted = FALSE;
                    """,
                    (new_content, post_id, user_id),
                )
                cursor.close()

            if request.is_json:
                return jsonify({"success": True})

            flash("Echo uppdaterad!", "success")
        except Exception as e:
            logger.error(f"Error updating post: {e}")
            if request.is_json:
                return jsonify({"success": False, "error": str(e)}), 500
            flash(f"Fel vid uppdatering av echo: {str(e)}", "danger")

        return redirect(url_for("dashboard"))

    @app.route("/delete_echo/<post_id>", methods=["POST"])
    @login_required
    def delete_echo(post_id):
        user_id = current_user.get_id()

        if not post_id:
            flash("Ogiltigt echo ID.", "danger")
            return redirect(url_for("dashboard"))

        try:
            with get_db(app) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE Posts
                    SET is_deleted = TRUE
                    WHERE post_id = %s AND user_id = %s;
                    """,
                    (post_id, user_id),
                )
                cursor.close()

            flash("Echo borttagen!", "success")
        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            flash(f"Fel vid borttagning av echo: {str(e)}", "danger")

        return redirect(url_for("dashboard"))

    @app.route("/api/posts", methods=["POST"])
    @login_required
    def create_post_api():
        from uuid import uuid4

        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        user_id = current_user.get_id()

        if not content:
            return {"error": "Content is required"}, 400

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

            return {
                "post_id": post_id,
                "content": content,
                "created_at": now,
                "user_id": user_id,
            }, 201
        except Exception as e:
            logger.error(f"Error creating post (api): {e}")
            return {"error": "Failed to create post"}, 500
    
    return app
