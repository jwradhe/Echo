import pytest
from datetime import datetime
from uuid import uuid4
import pymysql
from app.db import get_db


def test_dashboard_loads(client):
    """Test dashboard page loads successfully."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_create_echo(app, client):
    """Test creating a new echo/post."""
    test_content = "Unit test " + datetime.now().isoformat(timespec="seconds")
    
    resp = client.post(
        "/create_echo",
        data={"echo": test_content},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    # Verify post was created in database
    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT content FROM Posts WHERE content = %s AND is_deleted = FALSE",
            (test_content,)
        )
        row = cursor.fetchone()
        cursor.close()
    
    assert row is not None
    assert row["content"] == test_content


def test_echo_visible_on_dashboard(client):
    """Test that created echo appears on dashboard."""
    test_content = "Dashboard test " + datetime.now().isoformat(timespec="seconds")
    
    client.post("/create_echo", data={"echo": test_content})

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert test_content.encode("utf-8") in resp.data
