import os
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, current_user, login_required
from pymysql import cursors
from .db import (
    get_db,
    init_connection_pool,
    ensure_default_user,
    ensure_default_admin,
    ensure_post_thread_controls_schema,
)

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
        ensure_post_thread_controls_schema(app)
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
    from .profile_routes import profile_bp

    @login_manager.user_loader
    def load_user(user_id: str):
        return load_user_by_id(user_id)

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        if request.path.startswith("/api/"):
            return {"error": "Authentication required"}, 401
        return redirect(url_for("auth.login", next=request.full_path))

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)

    def _is_valid_http_url(value: str) -> bool:
        if not value:
            return False
        try:
            parsed = urlparse(value)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _ensure_like_reaction_type(conn) -> str:
        """Ensure a 'like' reaction type exists and return its ID."""
        from uuid import uuid4

        cursor = conn.cursor(cursors.DictCursor)
        now = datetime.now().isoformat(timespec="seconds")
        cursor.execute("SELECT reaction_type_id FROM ReactionTypes WHERE name = %s LIMIT 1", ("like",))
        row = cursor.fetchone()
        if row and row.get("reaction_type_id"):
            reaction_type_id = row["reaction_type_id"]
            cursor.close()
            return reaction_type_id

        reaction_type_id = str(uuid4())
        cursor.execute(
            """
            INSERT INTO ReactionTypes (reaction_type_id, name, created_at, updated_at)
            VALUES (%s, %s, %s, %s);
            """,
            (reaction_type_id, "like", now, now),
        )
        cursor.close()
        return reaction_type_id

    # =================================================
    # Routes
    # =================================================

    @app.route("/")
    def index():
        try:
            default_avatar_url = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
            viewer_id = current_user.get_id() if current_user.is_authenticated else None
            search_query = (request.args.get("q") or "").strip()
            search_terms = [term for term in search_query.split() if term][:5]
            search_users = []
            search_posts = []

            with get_db(app) as conn:
                cursor = conn.cursor(cursors.DictCursor)
                cursor.execute(
                    """
                    SELECT p.post_id, p.content, p.created_at, p.updated_at,
                           u.user_id, u.username, u.display_name,
                           m.url AS profile_image_url,
                           pm.url AS post_image_url,
                           COALESCE(rc.reply_count, 0) AS reply_count,
                           COALESCE(plc.like_count, 0) AS like_count,
                           COALESCE(p.replies_closed, FALSE) AS replies_closed,
                           p.replies_closed_at,
                           p.restricted_group_id,
                           p.restricted_at,
                           CASE
                               WHEN %s IS NULL THEN FALSE
                               WHEN EXISTS (
                                   SELECT 1
                                   FROM Followers f
                                   WHERE f.follower_id = %s
                                     AND f.followed_id = p.user_id
                               ) THEN TRUE
                               ELSE FALSE
                           END AS is_followed_author,
                           CASE
                               WHEN p.restricted_group_id IS NULL THEN TRUE
                               WHEN %s IS NULL THEN FALSE
                               WHEN p.user_id = %s THEN TRUE
                               WHEN EXISTS (
                                   SELECT 1
                                   FROM GroupMembers gm
                                   WHERE gm.group_id = p.restricted_group_id
                                     AND gm.user_id = %s
                               ) THEN TRUE
                               ELSE FALSE
                           END AS can_view_replies,
                           CASE
                               WHEN p.restricted_group_id IS NOT NULL AND %s IS NOT NULL THEN
                                   CASE
                                       WHEN p.user_id = %s THEN TRUE
                                       WHEN EXISTS (
                                           SELECT 1
                                           FROM GroupMembers gm2
                                           WHERE gm2.group_id = p.restricted_group_id
                                             AND gm2.user_id = %s
                                       ) THEN TRUE
                                       ELSE FALSE
                                   END
                               WHEN p.restricted_group_id IS NULL AND COALESCE(p.replies_closed, FALSE) = FALSE THEN TRUE
                               ELSE FALSE
                           END AS can_comment_replies,
                           CASE
                               WHEN %s IS NULL THEN FALSE
                               WHEN EXISTS (
                                   SELECT 1
                                   FROM Reactions lr
                                   JOIN ReactionTypes lrt ON lrt.reaction_type_id = lr.reaction_type_id
                                   WHERE lr.post_id = p.post_id
                                     AND lr.reply_id IS NULL
                                     AND lr.user_id = %s
                                     AND lrt.name = 'like'
                               ) THEN TRUE
                               ELSE FALSE
                           END AS is_liked
                    FROM Posts p
                    LEFT JOIN Users u ON p.user_id = u.user_id
                    LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
                    LEFT JOIN (
                        SELECT m1.post_id, m1.url
                        FROM Media m1
                        JOIN (
                            SELECT post_id, MIN(created_at) AS min_created_at
                            FROM Media
                            WHERE post_id IS NOT NULL
                              AND media_type = 'image'
                              AND is_deleted = FALSE
                            GROUP BY post_id
                        ) first_media
                          ON first_media.post_id = m1.post_id
                         AND first_media.min_created_at = m1.created_at
                        WHERE m1.media_type = 'image'
                          AND m1.is_deleted = FALSE
                    ) pm ON pm.post_id = p.post_id
                    LEFT JOIN (
                        SELECT parent_post_id, COUNT(*) AS reply_count
                        FROM Replies
                        WHERE is_deleted = FALSE
                        GROUP BY parent_post_id
                    ) rc ON rc.parent_post_id = p.post_id
                    LEFT JOIN (
                        SELECT r.post_id, COUNT(DISTINCT r.user_id) AS like_count
                        FROM Reactions r
                        JOIN ReactionTypes rt ON rt.reaction_type_id = r.reaction_type_id
                        WHERE r.post_id IS NOT NULL
                          AND r.reply_id IS NULL
                          AND rt.name = 'like'
                        GROUP BY r.post_id
                    ) plc ON plc.post_id = p.post_id
                    WHERE p.is_deleted = FALSE
                    ORDER BY is_followed_author DESC, p.created_at DESC
                    LIMIT 50;
                    """,
                    (
                        viewer_id,
                        viewer_id,
                        viewer_id,
                        viewer_id,
                        viewer_id,
                        viewer_id,
                        viewer_id,
                        viewer_id,
                        viewer_id,
                        viewer_id,
                    ),
                )
                db_posts = cursor.fetchall()
                post_ids = [
                    row.get("post_id")
                    for row in db_posts
                    if row.get("post_id")
                ]
                replies_by_post = {}
                participants_by_post = {}
                if post_ids:
                    placeholders = ", ".join(["%s"] * len(post_ids))
                    cursor.execute(
                        f"""
                        SELECT r.reply_id, r.parent_post_id, r.content, r.created_at,
                               COALESCE(r.is_private_after_split, FALSE) AS is_private_after_split,
                               COALESCE(rlc.like_count, 0) AS like_count,
                               u.user_id, u.username, u.display_name,
                               m.url AS profile_image_url,
                               rm.url AS reply_image_url,
                               CASE
                                   WHEN %s IS NULL THEN FALSE
                                   WHEN EXISTS (
                                       SELECT 1
                                       FROM Reactions rr
                                       JOIN ReactionTypes rrt ON rrt.reaction_type_id = rr.reaction_type_id
                                       WHERE rr.reply_id = r.reply_id
                                         AND rr.post_id IS NULL
                                         AND rr.user_id = %s
                                         AND rrt.name = 'like'
                                   ) THEN TRUE
                                   ELSE FALSE
                               END AS is_liked
                        FROM Replies r
                        LEFT JOIN Users u ON r.user_id = u.user_id
                        LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
                        LEFT JOIN (
                            SELECT m2.reply_id, m2.url
                            FROM Media m2
                            JOIN (
                                SELECT reply_id, MIN(created_at) AS min_created_at
                                FROM Media
                                WHERE reply_id IS NOT NULL
                                  AND media_type = 'image'
                                  AND is_deleted = FALSE
                                GROUP BY reply_id
                            ) first_reply_media
                              ON first_reply_media.reply_id = m2.reply_id
                             AND first_reply_media.min_created_at = m2.created_at
                            WHERE m2.media_type = 'image'
                              AND m2.is_deleted = FALSE
                        ) rm ON rm.reply_id = r.reply_id
                        LEFT JOIN (
                            SELECT rx.reply_id, COUNT(DISTINCT rx.user_id) AS like_count
                            FROM Reactions rx
                            JOIN ReactionTypes rtx ON rtx.reaction_type_id = rx.reaction_type_id
                            WHERE rx.reply_id IS NOT NULL
                              AND rx.post_id IS NULL
                              AND rtx.name = 'like'
                            GROUP BY rx.reply_id
                        ) rlc ON rlc.reply_id = r.reply_id
                        WHERE r.is_deleted = FALSE AND r.parent_post_id IN ({placeholders})
                        ORDER BY r.created_at ASC;
                        """,
                        (viewer_id, viewer_id, *post_ids),
                    )
                    db_replies = cursor.fetchall()
                    for reply in db_replies:
                        parent_post_id = reply.get("parent_post_id")
                        if not parent_post_id:
                            continue
                        participant = {
                            "id": reply.get("user_id"),
                            "name": reply.get("display_name")
                            or reply.get("username")
                            or "Unknown",
                        }
                        if participant["id"]:
                            participants_by_post.setdefault(parent_post_id, {})
                            participants_by_post[parent_post_id][participant["id"]] = participant
                        replies_by_post.setdefault(parent_post_id, []).append(
                            {
                                "id": reply.get("reply_id"),
                                "content": reply.get("content"),
                                "timestamp": reply.get("created_at"),
                                "imageUrl": reply.get("reply_image_url"),
                                "isPrivateAfterSplit": bool(reply.get("is_private_after_split")),
                                "likes": int(reply.get("like_count") or 0),
                                "isLiked": bool(reply.get("is_liked")),
                                "author": {
                                    "id": reply.get("user_id"),
                                    "name": reply.get("display_name")
                                    or reply.get("username")
                                    or "Unknown",
                                    "avatar": reply.get("profile_image_url") or default_avatar_url,
                                },
                            }
                        )

                if search_terms:
                    user_conditions = []
                    user_params = []
                    for term in search_terms:
                        like_term = f"%{term}%"
                        user_conditions.append("(u.username LIKE %s OR COALESCE(u.display_name, '') LIKE %s)")
                        user_params.extend([like_term, like_term])

                    user_filter_sql = " AND ".join(user_conditions)
                    exclude_viewer_sql = ""
                    if viewer_id:
                        exclude_viewer_sql = "AND u.user_id <> %s"
                        user_params.append(viewer_id)

                    cursor.execute(
                        f"""
                        SELECT u.user_id, u.username, u.display_name, m.url AS profile_image_url
                        FROM Users u
                        LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
                        WHERE u.is_deleted = FALSE
                          {exclude_viewer_sql}
                          AND {user_filter_sql}
                        ORDER BY u.created_at DESC
                        LIMIT 15;
                        """,
                        tuple(user_params),
                    )
                    search_users = cursor.fetchall()

                    post_conditions = []
                    post_params = []
                    for term in search_terms:
                        like_term = f"%{term}%"
                        post_conditions.append(
                            "(p.content LIKE %s OR u.username LIKE %s OR COALESCE(u.display_name, '') LIKE %s)"
                        )
                        post_params.extend([like_term, like_term, like_term])

                    post_filter_sql = " AND ".join(post_conditions)
                    cursor.execute(
                        f"""
                        SELECT p.post_id, p.content, p.created_at,
                               u.user_id, u.username, u.display_name,
                               m.url AS profile_image_url
                        FROM Posts p
                        JOIN Users u ON u.user_id = p.user_id
                        LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
                        WHERE p.is_deleted = FALSE
                          AND u.is_deleted = FALSE
                          AND {post_filter_sql}
                        ORDER BY p.created_at DESC
                        LIMIT 20;
                        """,
                        tuple(post_params),
                    )
                    search_posts = cursor.fetchall()
                cursor.close()

            posts = []
            for row in db_posts:
                display_name = row.get("display_name") or row.get("username") or "Unknown"
                username = row.get("username") or "unknown"
                post_id = row.get("post_id")
                all_replies = replies_by_post.get(post_id, [])
                can_view_all_replies = bool(row.get("can_view_replies"))
                restricted_at = row.get("restricted_at")
                visible_comment_count = 0
                if can_view_all_replies:
                    visible_replies = all_replies
                elif row.get("restricted_group_id"):
                    visible_replies = [
                        reply for reply in all_replies if not reply.get("isPrivateAfterSplit")
                    ]
                else:
                    visible_replies = all_replies

                rendered_comments = list(visible_replies)
                if row.get("restricted_group_id") and restricted_at:
                    before_split = [reply for reply in all_replies if not reply.get("isPrivateAfterSplit")]
                    if can_view_all_replies:
                        after_split = [reply for reply in all_replies if reply.get("isPrivateAfterSplit")]
                        rendered_comments = before_split + [
                            {
                                "isMarker": True,
                                "label": "Diskussionen bröts ut här",
                                "timestamp": restricted_at,
                            }
                        ] + after_split
                    else:
                        rendered_comments = before_split + [
                            {
                                "isMarker": True,
                                "label": "Diskussionen bröts ut här",
                                "timestamp": restricted_at,
                            }
                        ]

                if row.get("replies_closed") and not row.get("restricted_group_id"):
                    rendered_comments = rendered_comments + [
                        {
                            "isMarker": True,
                            "label": "Svarstråden stängdes här",
                            "timestamp": row.get("replies_closed_at"),
                        }
                    ]

                visible_comment_count = len([reply for reply in rendered_comments if not reply.get("isMarker")])

                posts.append(
                    {
                        "id": post_id,
                        "author": {
                            "id": row.get("user_id"),
                            "name": display_name,
                            "username": username,
                            "avatar": row.get("profile_image_url") or default_avatar_url,
                        },
                        "content": row.get("content"),
                        "imageUrl": row.get("post_image_url"),
                        "timestamp": row.get("created_at"),
                        "likes": int(row.get("like_count") or 0),
                        "comments": visible_comment_count,
                        "commentsList": rendered_comments,
                        "commentParticipants": (
                            [
                                participant
                                for participant in list(participants_by_post.get(post_id, {}).values())
                                if participant.get("id") != viewer_id
                            ]
                            if can_view_all_replies
                            else []
                        ),
                        "threadClosed": bool(row.get("replies_closed")),
                        "canViewComments": True,
                        "canComment": bool(row.get("can_comment_replies")),
                        "threadRestricted": bool(row.get("restricted_group_id")),
                        "bookmarks": 0,
                        "isLiked": bool(row.get("is_liked")),
                        "isBookmarked": False,
                    }
                )
            
            return render_template(
                "index.html",
                posts=posts,  # Keep variable name for template compatibility
                default_avatar_url=default_avatar_url,
                current_user=current_user,
                search_query=search_query,
                search_users=search_users,
                search_posts=search_posts,
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
        image_url = (payload.get("image_url") or "").strip()
        user_id = current_user.get_id()

        if not content:
            return {"error": "Content is required"}, 400
        if image_url and not _is_valid_http_url(image_url):
            return {"error": "image_url must be a valid http/https URL"}, 400

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
                if image_url:
                    media_id = str(uuid4())
                    cursor.execute(
                        """
                        INSERT INTO Media (media_id, post_id, reply_id, url, media_type, created_at, updated_at)
                        VALUES (%s, %s, NULL, %s, %s, %s, %s);
                        """,
                        (media_id, post_id, image_url, "image", now, now),
                    )
                cursor.close()

            return {
                "post_id": post_id,
                "content": content,
                "image_url": image_url or None,
                "created_at": now,
                "user_id": user_id,
            }, 201
        except Exception as e:
            logger.error(f"Error creating post (api): {e}")
            return {"error": "Failed to create post"}, 500

    @app.route("/api/posts/<post_id>/like", methods=["POST"])
    @login_required
    def toggle_post_like_api(post_id):
        from uuid import uuid4

        user_id = current_user.get_id()
        now = datetime.now().isoformat(timespec="seconds")

        try:
            with get_db(app) as conn:
                cursor = conn.cursor(cursors.DictCursor)
                cursor.execute(
                    "SELECT post_id FROM Posts WHERE post_id = %s AND is_deleted = FALSE LIMIT 1",
                    (post_id,),
                )
                post = cursor.fetchone()
                if not post:
                    cursor.close()
                    return {"error": "Post not found"}, 404

                like_reaction_type_id = _ensure_like_reaction_type(conn)
                cursor.execute(
                    """
                    SELECT reaction_id
                    FROM Reactions
                    WHERE user_id = %s
                      AND post_id = %s
                      AND reply_id IS NULL
                      AND reaction_type_id = %s
                    LIMIT 1;
                    """,
                    (user_id, post_id, like_reaction_type_id),
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        """
                        DELETE FROM Reactions
                        WHERE user_id = %s
                          AND post_id = %s
                          AND reply_id IS NULL
                          AND reaction_type_id = %s;
                        """,
                        (user_id, post_id, like_reaction_type_id),
                    )
                    is_liked = False
                else:
                    cursor.execute(
                        """
                        INSERT INTO Reactions (
                            reaction_id, user_id, post_id, reply_id, reaction_type_id, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, NULL, %s, %s, %s);
                        """,
                        (str(uuid4()), user_id, post_id, like_reaction_type_id, now, now),
                    )
                    is_liked = True

                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT r.user_id) AS likes
                    FROM Reactions r
                    JOIN ReactionTypes rt ON rt.reaction_type_id = r.reaction_type_id
                    WHERE r.post_id = %s
                      AND r.reply_id IS NULL
                      AND rt.name = 'like';
                    """,
                    (post_id,),
                )
                likes_row = cursor.fetchone() or {}
                cursor.close()

            return {"post_id": post_id, "likes": int(likes_row.get("likes") or 0), "isLiked": is_liked}, 200
        except Exception as e:
            logger.error(f"Error toggling post like: {e}")
            return {"error": "Failed to toggle like"}, 500

    @app.route("/api/posts/<post_id>/comments", methods=["POST"])
    @login_required
    def create_comment_api(post_id):
        from uuid import uuid4

        default_avatar_url = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"

        if not post_id:
            return {"error": "Post ID is required"}, 400

        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        image_url = (payload.get("image_url") or "").strip()
        user_id = current_user.get_id()

        if not content:
            return {"error": "Content is required"}, 400

        if len(content) > 500:
            return {"error": "Max 500 characters"}, 400
        if image_url and not _is_valid_http_url(image_url):
            return {"error": "image_url must be a valid http/https URL"}, 400

        try:
            now = datetime.now().isoformat(timespec="seconds")
            reply_id = str(uuid4())

            with get_db(app) as conn:
                cursor = conn.cursor(cursors.DictCursor)
                cursor.execute(
                    """
                    SELECT post_id, replies_closed, restricted_group_id, user_id
                    FROM Posts
                    WHERE post_id = %s AND is_deleted = FALSE;
                    """,
                    (post_id,),
                )
                post = cursor.fetchone()
                if not post:
                    cursor.close()
                    return {"error": "Post not found"}, 404
                is_private_thread = bool(post.get("restricted_group_id"))
                if is_private_thread:
                    cursor.execute(
                        """
                        SELECT 1
                        FROM GroupMembers
                        WHERE group_id = %s AND user_id = %s
                        LIMIT 1;
                        """,
                        (post.get("restricted_group_id"), user_id),
                    )
                    is_member = cursor.fetchone() is not None
                    is_owner = post.get("user_id") == user_id
                    if not is_member and not is_owner:
                        cursor.close()
                        return {"error": "Thread is private after split"}, 403
                if post.get("replies_closed") and not is_private_thread:
                    cursor.close()
                    return {"error": "Thread is closed for replies"}, 403

                cursor.execute(
                    """
                    INSERT INTO Replies (
                        reply_id, parent_post_id, parent_reply_id, user_id, content, is_private_after_split, created_at, updated_at
                    )
                    VALUES (%s, %s, NULL, %s, %s, %s, %s, %s);
                    """,
                    (reply_id, post_id, user_id, content, is_private_thread, now, now),
                )
                if image_url:
                    cursor.execute(
                        """
                        INSERT INTO Media (media_id, post_id, reply_id, url, media_type, created_at, updated_at)
                        VALUES (%s, NULL, %s, %s, %s, %s, %s);
                        """,
                        (str(uuid4()), reply_id, image_url, "image", now, now),
                    )

                cursor.execute(
                    """
                    SELECT u.user_id, u.username, u.display_name, m.url AS profile_image_url
                    FROM Users u
                    LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
                    WHERE u.user_id = %s;
                    """,
                    (user_id,),
                )
                author = cursor.fetchone() or {}
                cursor.close()

            return {
                "reply_id": reply_id,
                "post_id": post_id,
                "content": content,
                "image_url": image_url or None,
                "created_at": now,
                "author": {
                    "id": author.get("user_id"),
                    "name": author.get("display_name") or author.get("username") or "Unknown",
                    "avatar": author.get("profile_image_url") or default_avatar_url,
                },
            }, 201
        except Exception as e:
            logger.error(f"Error creating comment (api): {e}")
            return {"error": "Failed to create comment"}, 500

    @app.route("/api/replies/<reply_id>/like", methods=["POST"])
    @login_required
    def toggle_reply_like_api(reply_id):
        from uuid import uuid4

        user_id = current_user.get_id()
        now = datetime.now().isoformat(timespec="seconds")

        try:
            with get_db(app) as conn:
                cursor = conn.cursor(cursors.DictCursor)
                cursor.execute(
                    """
                    SELECT r.reply_id, r.parent_post_id, COALESCE(r.is_private_after_split, FALSE) AS is_private_after_split,
                           p.user_id AS post_owner_id, p.restricted_group_id
                    FROM Replies r
                    LEFT JOIN Posts p ON p.post_id = r.parent_post_id
                    WHERE r.reply_id = %s
                      AND r.is_deleted = FALSE;
                    """,
                    (reply_id,),
                )
                reply = cursor.fetchone()
                if not reply:
                    cursor.close()
                    return {"error": "Reply not found"}, 404

                if reply.get("is_private_after_split") and reply.get("restricted_group_id"):
                    cursor.execute(
                        """
                        SELECT 1
                        FROM GroupMembers
                        WHERE group_id = %s AND user_id = %s
                        LIMIT 1;
                        """,
                        (reply.get("restricted_group_id"), user_id),
                    )
                    is_member = cursor.fetchone() is not None
                    is_owner = reply.get("post_owner_id") == user_id
                    if not is_member and not is_owner:
                        cursor.close()
                        return {"error": "Reply is private after split"}, 403

                like_reaction_type_id = _ensure_like_reaction_type(conn)
                cursor.execute(
                    """
                    SELECT reaction_id
                    FROM Reactions
                    WHERE user_id = %s
                      AND reply_id = %s
                      AND post_id IS NULL
                      AND reaction_type_id = %s
                    LIMIT 1;
                    """,
                    (user_id, reply_id, like_reaction_type_id),
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        """
                        DELETE FROM Reactions
                        WHERE user_id = %s
                          AND reply_id = %s
                          AND post_id IS NULL
                          AND reaction_type_id = %s;
                        """,
                        (user_id, reply_id, like_reaction_type_id),
                    )
                    is_liked = False
                else:
                    cursor.execute(
                        """
                        INSERT INTO Reactions (
                            reaction_id, user_id, post_id, reply_id, reaction_type_id, created_at, updated_at
                        )
                        VALUES (%s, %s, NULL, %s, %s, %s, %s);
                        """,
                        (str(uuid4()), user_id, reply_id, like_reaction_type_id, now, now),
                    )
                    is_liked = True

                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT r.user_id) AS likes
                    FROM Reactions r
                    JOIN ReactionTypes rt ON rt.reaction_type_id = r.reaction_type_id
                    WHERE r.reply_id = %s
                      AND r.post_id IS NULL
                      AND rt.name = 'like';
                    """,
                    (reply_id,),
                )
                likes_row = cursor.fetchone() or {}
                cursor.close()

            return {"reply_id": reply_id, "likes": int(likes_row.get("likes") or 0), "isLiked": is_liked}, 200
        except Exception as e:
            logger.error(f"Error toggling reply like: {e}")
            return {"error": "Failed to toggle reply like"}, 500

    @app.route("/api/posts/<post_id>/reply-lock", methods=["POST"])
    @login_required
    def toggle_post_reply_lock(post_id):
        payload = request.get_json(silent=True) or {}
        requested_state = payload.get("is_closed")
        if not isinstance(requested_state, bool):
            return {"error": "is_closed must be a boolean"}, 400

        user_id = current_user.get_id()
        now = datetime.now().isoformat(timespec="seconds")

        try:
            with get_db(app) as conn:
                cursor = conn.cursor(cursors.DictCursor)
                cursor.execute(
                    """
                    SELECT post_id, user_id, replies_closed, restricted_group_id
                    FROM Posts
                    WHERE post_id = %s AND is_deleted = FALSE;
                    """,
                    (post_id,),
                )
                post = cursor.fetchone()
                if not post:
                    cursor.close()
                    return {"error": "Post not found"}, 404
                if post.get("user_id") != user_id:
                    cursor.close()
                    return {"error": "Only post owner can change thread state"}, 403
                if post.get("restricted_group_id") and not requested_state:
                    cursor.close()
                    return {"error": "Thread is private after split and cannot be reopened"}, 400

                cursor.execute(
                    """
                    UPDATE Posts
                    SET replies_closed = %s,
                        replies_closed_by = %s,
                        replies_closed_at = CASE WHEN %s THEN %s ELSE NULL END,
                        updated_at = %s
                    WHERE post_id = %s;
                    """,
                    (requested_state, user_id, requested_state, now, now, post_id),
                )
                cursor.close()

            return {"post_id": post_id, "is_closed": requested_state}, 200
        except Exception as e:
            logger.error(f"Error toggling reply lock: {e}")
            return {"error": "Failed to update thread state"}, 500

    @app.route("/api/posts/<post_id>/discussion-groups", methods=["POST"])
    @login_required
    def create_discussion_group(post_id):
        from uuid import uuid4

        payload = request.get_json(silent=True) or {}
        selected_user_ids = payload.get("participant_user_ids") or []
        group_name = (payload.get("name") or "").strip()
        creator_id = current_user.get_id()

        if not isinstance(selected_user_ids, list):
            return {"error": "participant_user_ids must be a list"}, 400

        cleaned_selected_ids = [str(uid).strip() for uid in selected_user_ids if str(uid).strip()]
        cleaned_selected_ids = list(dict.fromkeys(cleaned_selected_ids))
        cleaned_selected_ids = [uid for uid in cleaned_selected_ids if uid != creator_id]

        if not cleaned_selected_ids:
            return {"error": "Choose at least one other participant"}, 400

        try:
            now = datetime.now().isoformat(timespec="seconds")
            with get_db(app) as conn:
                cursor = conn.cursor(cursors.DictCursor)
                cursor.execute(
                    """
                    SELECT post_id, user_id, content
                    FROM Posts
                    WHERE post_id = %s AND is_deleted = FALSE;
                    """,
                    (post_id,),
                )
                post = cursor.fetchone()
                if not post:
                    cursor.close()
                    return {"error": "Post not found"}, 404
                if post.get("user_id") != creator_id:
                    cursor.close()
                    return {"error": "Only post owner can split discussion"}, 403

                cursor.execute(
                    """
                    SELECT DISTINCT r.user_id, COALESCE(u.display_name, u.username, 'Unknown') AS name
                    FROM Replies r
                    LEFT JOIN Users u ON u.user_id = r.user_id
                    WHERE r.parent_post_id = %s
                      AND r.is_deleted = FALSE
                      AND u.is_deleted = FALSE
                      AND r.user_id <> %s;
                    """,
                    (post_id, creator_id),
                )
                eligible_rows = cursor.fetchall()
                eligible_map = {row["user_id"]: row["name"] for row in eligible_rows if row.get("user_id")}
                valid_selected = [uid for uid in cleaned_selected_ids if uid in eligible_map]
                if not valid_selected:
                    cursor.close()
                    return {"error": "Selected users must be commenters on this post"}, 400

                group_id = str(uuid4())
                effective_name = group_name or f"Diskussion: {post.get('content', '')[:40]}".strip()
                if not effective_name:
                    effective_name = "Ny diskussion"

                cursor.execute(
                    """
                    INSERT INTO UserGroups (
                        group_id, created_by, origin_post_id, name, description, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        group_id,
                        creator_id,
                        post_id,
                        effective_name[:255],
                        "Utbryten diskussion från kommentarstråd",
                        now,
                        now,
                    ),
                )

                member_ids = [creator_id, *valid_selected]
                unique_member_ids = list(dict.fromkeys(member_ids))
                for member_id in unique_member_ids:
                    cursor.execute(
                        """
                        INSERT INTO GroupMembers (group_id, user_id, joined_at, updated_at)
                        VALUES (%s, %s, %s, %s);
                        """,
                        (group_id, member_id, now, now),
                    )

                cursor.execute(
                    """
                    UPDATE Posts
                    SET restricted_group_id = %s,
                        restricted_at = %s,
                        replies_closed = TRUE,
                        replies_closed_by = %s,
                        replies_closed_at = %s,
                        updated_at = %s
                    WHERE post_id = %s;
                    """,
                    (group_id, now, creator_id, now, now, post_id),
                )

                cursor.close()

            return {
                "group_id": group_id,
                "name": effective_name[:255],
                "participant_count": len(unique_member_ids),
                "participants": [
                    {"id": uid, "name": eligible_map.get(uid, "Post owner")}
                    for uid in unique_member_ids
                ],
            }, 201
        except Exception as e:
            logger.error(f"Error creating discussion group: {e}")
            return {"error": "Failed to split discussion"}, 500
    
    return app
