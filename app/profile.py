from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import uuid4
from flask import current_app
from pymysql import cursors
from .db import get_db

def create_profile(user_id: str, display_name: Optional[str] = None, bio: Optional[str] = None) -> bool:
    if not user_id:
        return False

    now = datetime.now().isoformat(timespec="seconds")

    with get_db(current_app) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE Users
            SET display_name = %s,
                bio = %s,
                updated_at = %s
            WHERE user_id = %s AND is_deleted = FALSE
            """,
            (display_name, bio, now, user_id),
        )
        updated_rows = cursor.rowcount
        cursor.close()

    return updated_rows > 0


def get_profile_by_user_id(user_id: str) -> Optional[dict]:
    if not user_id:
        return None

    with get_db(current_app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        cursor.execute(
            """
            SELECT
                u.user_id,
                u.username,
                u.email,
                u.display_name,
                u.bio,
                m.url AS profile_image_url,
                u.created_at,
                (
                    SELECT COUNT(*)
                    FROM Posts p
                    WHERE p.user_id = u.user_id AND p.is_deleted = FALSE
                ) AS posts_count,
                (
                    SELECT COUNT(*)
                    FROM Followers f
                    WHERE f.followed_id = u.user_id
                ) AS followers_count,
                (
                    SELECT COUNT(*)
                    FROM Followers f
                    WHERE f.follower_id = u.user_id
                ) AS following_count
            FROM Users u
            LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
            WHERE u.user_id = %s AND u.is_deleted = FALSE
            LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()

    return row


def get_profile_by_username(username: str) -> Optional[dict]:
    if not username:
        return None

    with get_db(current_app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        cursor.execute(
            """
            SELECT
                u.user_id,
                u.username,
                u.email,
                u.display_name,
                u.bio,
                m.url AS profile_image_url,
                u.created_at,
                (
                    SELECT COUNT(*)
                    FROM Posts p
                    WHERE p.user_id = u.user_id AND p.is_deleted = FALSE
                ) AS posts_count,
                (
                    SELECT COUNT(*)
                    FROM Followers f
                    WHERE f.followed_id = u.user_id
                ) AS followers_count,
                (
                    SELECT COUNT(*)
                    FROM Followers f
                    WHERE f.follower_id = u.user_id
                ) AS following_count
            FROM Users u
            LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
            WHERE u.username = %s AND u.is_deleted = FALSE
            LIMIT 1
            """,
            (username,),
        )
        row = cursor.fetchone()
        cursor.close()

    return row


def list_recent_posts_for_user(user_id: str, limit: int = 20) -> list[dict]:
    if not user_id:
        return []

    safe_limit = max(1, min(limit, 50))

    with get_db(current_app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        cursor.execute(
            """
            SELECT post_id, content, created_at, updated_at
            FROM Posts
            WHERE user_id = %s AND is_deleted = FALSE
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, safe_limit),
        )
        rows = cursor.fetchall()
        cursor.close()

    return rows


def update_profile(user_id: str, display_name: Optional[str], bio: Optional[str]) -> bool:
    if not user_id:
        return False

    now = datetime.now().isoformat(timespec="seconds")

    with get_db(current_app) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE Users
            SET display_name = %s,
                bio = %s,
                updated_at = %s
            WHERE user_id = %s AND is_deleted = FALSE
            """,
            (display_name, bio, now, user_id),
        )
        updated_rows = cursor.rowcount
        cursor.close()

    return updated_rows > 0


def delete_profile(user_id: str) -> bool:
    if not user_id:
        return False

    now = datetime.now().isoformat(timespec="seconds")

    with get_db(current_app) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE Users
            SET is_deleted = TRUE,
                deleted_at = %s,
                updated_at = %s
            WHERE user_id = %s AND is_deleted = FALSE
            """,
            (now, now, user_id),
        )
        updated_rows = cursor.rowcount
        cursor.close()

    return updated_rows > 0


def upsert_profile_image(user_id: str, media_url: str, media_type: str = "image/webp") -> bool:
    if not user_id or not media_url:
        return False

    now = datetime.now().isoformat(timespec="seconds")

    with get_db(current_app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        cursor.execute(
            """
            SELECT profile_media_id
            FROM Users
            WHERE user_id = %s AND is_deleted = FALSE
            LIMIT 1
            """,
            (user_id,),
        )
        user_row = cursor.fetchone()
        if not user_row:
            cursor.close()
            return False

        media_id = user_row.get("profile_media_id")

        if media_id:
            cursor.execute(
                """
                UPDATE Media
                SET url = %s,
                    media_type = %s,
                    is_deleted = FALSE,
                    deleted_at = NULL,
                    deleted_by = NULL,
                    updated_at = %s
                WHERE media_id = %s
                """,
                (media_url, media_type, now, media_id),
            )
        else:
            media_id = str(uuid4())
            cursor.execute(
                """
                INSERT INTO Media (media_id, post_id, reply_id, url, media_type, is_deleted, created_at, updated_at)
                VALUES (%s, NULL, NULL, %s, %s, FALSE, %s, %s)
                """,
                (media_id, media_url, media_type, now, now),
            )
            cursor.execute(
                """
                UPDATE Users
                SET profile_media_id = %s,
                    updated_at = %s
                WHERE user_id = %s AND is_deleted = FALSE
                """,
                (media_id, now, user_id),
            )

        cursor.close()

    return True