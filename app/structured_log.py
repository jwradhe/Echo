"""
Structured JSON logging for security and auth events.
All events are logged to a dedicated 'echo.security' logger
so they can be filtered separately from general app logs.
"""
import json
import logging
from datetime import datetime, timezone
from flask import request

security_logger = logging.getLogger("echo.security")


def _entry(event: str, **fields) -> str:
    return json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "ip": _get_ip(),
        **fields,
    })


def _get_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


# ── Auth ──────────────────────────────────────────────────────────────────────

def log_login_success(user_id: str, username: str) -> None:
    security_logger.info(_entry("login_success", user_id=user_id, username=username))


def log_login_failure(username: str, reason: str) -> None:
    security_logger.warning(_entry("login_failure", username=username, reason=reason))


def log_register_success(user_id: str, username: str) -> None:
    security_logger.info(_entry("register_success", user_id=user_id, username=username))


def log_register_failure(username: str, reason: str) -> None:
    security_logger.warning(_entry("register_failure", username=username, reason=reason))


def log_logout(user_id: str) -> None:
    security_logger.info(_entry("logout", user_id=user_id))


# ── Security ──────────────────────────────────────────────────────────────────

def log_rate_limit(endpoint: str) -> None:
    security_logger.warning(_entry("rate_limit_hit", endpoint=endpoint))


def log_unauthorized(path: str, method: str) -> None:
    security_logger.warning(_entry("unauthorized_access", path=path, method=method))


def log_error(route: str, user_id: str | None, error: str) -> None:
    security_logger.error(_entry("error", route=route, user_id=user_id, error=error))
