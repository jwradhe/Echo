from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from flask import current_app
from flask_login import UserMixin, current_user
from pymysql import IntegrityError, cursors

from .db import get_db

_password_hasher = PasswordHasher()


@dataclass
class User(UserMixin):
    user_id: str
    username: str
    email: str
    display_name: Optional[str]
    profile_image_url: Optional[str]
    is_banned: bool
    is_deleted: bool

    def get_id(self) -> str:
        return self.user_id

    @property
    def is_active(self) -> bool:
        return not self.is_banned and not self.is_deleted


def _row_to_user(row: dict) -> User:
    return User(
        user_id=row["user_id"],
        username=row["username"],
        email=row["email"],
        display_name=row.get("display_name"),
        profile_image_url=row.get("profile_image_url"),
        is_banned=bool(row.get("is_banned")),
        is_deleted=bool(row.get("is_deleted")),
    )


def load_user_by_id(user_id: str) -> Optional[User]:
    if not user_id:
        return None

    with get_db(current_app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.email, u.display_name, m.url AS profile_image_url, u.is_banned, u.is_deleted
            FROM Users u
            LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
            WHERE user_id = %s
            LIMIT 1;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()

    return _row_to_user(row) if row else None


def load_user_by_username(username: str) -> Optional[dict]:
    if not username:
        return None

    with get_db(current_app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.email, u.password_hash, u.display_name, m.url AS profile_image_url, u.is_banned, u.is_deleted
            FROM Users u
            LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
            WHERE u.username = %s
            LIMIT 1;
            """,
            (username,),
        )
        row = cursor.fetchone()
        cursor.close()

    return row


def load_user_by_email(email: str) -> Optional[dict]:
    if not email:
        return None

    with get_db(current_app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.email, u.password_hash, u.display_name, m.url AS profile_image_url, u.is_banned, u.is_deleted
            FROM Users u
            LEFT JOIN Media m ON m.media_id = u.profile_media_id AND m.is_deleted = FALSE
            WHERE u.email = %s
            LIMIT 1;
            """,
            (email,),
        )
        row = cursor.fetchone()
        cursor.close()

    return row


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def create_user(username: str, email: str, password: str, display_name: Optional[str] = None) -> User:
    user_id = str(uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    password_hash = hash_password(password)

    with get_db(current_app) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO Users (user_id, username, email, password_hash, display_name, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, username, email, password_hash, display_name, now, now),
            )
            cursor.close()
            conn.commit()
        except IntegrityError as exc:
            cursor.close()
            raise exc

    return User(
        user_id=user_id,
        username=username,
        email=email,
        display_name=display_name,
        profile_image_url=None,
        is_banned=False,
        is_deleted=False,
    )


def user_has_role(user_id: str, role_name: str) -> bool:
    if not user_id or not role_name:
        return False

    with get_db(current_app) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM UserRoles ur
            JOIN Roles r ON ur.role_id = r.role_id
            WHERE ur.user_id = %s AND r.name = %s
            LIMIT 1;
            """,
            (user_id, role_name),
        )
        row = cursor.fetchone()
        cursor.close()

    return row is not None


def assign_role(user_id: str, role_name: str) -> bool:
    if not user_id or not role_name:
        return False

    with get_db(current_app) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role_id FROM Roles WHERE name = %s LIMIT 1;", (role_name,))
        role = cursor.fetchone()

        if not role:
            cursor.close()
            return False

        now = datetime.now().isoformat(timespec="seconds")
        cursor.execute(
            """
            INSERT IGNORE INTO UserRoles (user_id, role_id, assigned_at, updated_at)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, role[0], now, now),
        )
        cursor.close()
        conn.commit()

    return True


def current_user_has_role(role_name: str) -> bool:
    if not current_user.is_authenticated:
        return False

    return user_has_role(current_user.get_id(), role_name)
