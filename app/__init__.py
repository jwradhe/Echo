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

    # -------------------------------------------------
    #
    # -------------------------------------------------
    current_user = {
        "name": "John Doe",
        "username": "johndoe",
        "avatar": "https://images.unsplash.com/photo-1701463387028-3947648f1337?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=100"
    }

    posts = [
        {
            "id": 1,
            "author": {
                "name": "Echo",
                "username": "echo",
                "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
            },
            "content": "Welcome to Echo! Share your thoughts with the world.",
            "timestamp": "2026-01-28T12:58:00Z",
            "likes": 0,
            "comments": 0,
            "bookmarks": 0,
            "isLiked": False,
            "isBookmarked": False
        },
        {
            "id": 2,
            "author": {
                "name": "Sarah Johnson",
                "username": "sarahj",
                "avatar": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop"
            },
            "content": "Just launched my new portfolio website! 🚀 Check it out and let me know what you think. Built with Flask and Bootstrap.",
            "timestamp": "2026-01-28T11:30:00Z",
            "likes": 124,
            "comments": 15,
            "bookmarks": 23,
            "isLiked": False,
            "isBookmarked": False
        },
        {
            "id": 3,
            "author": {
                "name": "Alex Chen",
                "username": "alexchen",
                "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop"
            },
            "content": "Hot take: Python has made me a better developer. The simplicity and readability really help! 💯",
            "timestamp": "2026-01-28T10:15:00Z",
            "likes": 89,
            "comments": 34,
            "bookmarks": 12,
            "isLiked": True,
            "isBookmarked": False
        },
        {
            "id": 4,
            "author": {
                "name": "Emma Rodriguez",
                "username": "emmarodriguez",
                "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop"
            },
            "content": "Working on an exciting new AI project. Can't wait to share more details soon! The future of technology is here.",
            "timestamp": "2026-01-28T09:00:00Z",
            "likes": 256,
            "comments": 67,
            "bookmarks": 45,
            "isLiked": False,
            "isBookmarked": True
        }
    ]
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
                #posts = cursor.fetchall()
                cursor.close()
            
            return render_template(
                "index.html",
                posts=posts  # Keep variable name for template compatibility
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
            return redirect(url_for("/"))

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
        
        return redirect(url_for("/"))
    
    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("Du har loggats ut.", "info")
        return redirect(url_for("/"))

    return app
