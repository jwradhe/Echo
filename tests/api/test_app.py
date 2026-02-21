from datetime import datetime
import pymysql
from app.db import get_db


def _register_user(client, suffix: str) -> dict:
    username = f"testuser_{suffix}"
    email = f"testuser_{suffix}@example.com"
    password = "TestPassword123"

    resp = client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "display_name": "Test User",
        },
        follow_redirects=False,
    )

    return {"response": resp, "username": username, "email": email, "password": password}


def test_dashboard_loads(client):
    """Test dashboard page loads successfully."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_create_echo_requires_login(client):
    """Protected routes should redirect to login when unauthenticated."""
    resp = client.post("/create_echo", data={"echo": "Test"}, follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")


def test_api_posts_requires_login(client):
    """API should return 401 when not authenticated."""
    resp = client.post("/api/posts", json={"content": "Test"})
    assert resp.status_code == 401


def test_create_echo_authenticated(app, client):
    """Test creating a new echo/post with an authenticated user."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

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
            (test_content,),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    assert row["content"] == test_content


def test_echo_visible_on_dashboard(client):
    """Test that created echo appears on dashboard for logged-in user."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    test_content = "Dashboard test " + datetime.now().isoformat(timespec="seconds")
    client.post("/create_echo", data={"echo": test_content})

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert test_content.encode("utf-8") in resp.data

def test_edit_echo_authenticated(app, client):
    """Test editing an existing echo/post with an authenticated user."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    # Create a new echo
    original_content = "Edit test " + datetime.now().isoformat(timespec="seconds")
    client.post("/create_echo", data={"echo": original_content})

    # Get the post ID from the database
    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT post_id FROM Posts WHERE content = %s AND is_deleted = FALSE",
            (original_content,),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    post_id = row["post_id"]

    # Edit the echo
    updated_content = "Updated " + original_content
    resp = client.post(
        f"/edit_echo/{post_id}",
        data={"content": updated_content},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    # Verify post was updated in database
    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT content FROM Posts WHERE post_id = %s AND is_deleted = FALSE",
            (post_id,),
        )
        row = cursor.fetchone()
        cursor.close()

    # Delete the test post to clean up
    with get_db(app) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Posts SET is_deleted = TRUE WHERE post_id = %s", (post_id,))
        conn.commit()
        cursor.close()

    assert row is not None
    assert row["content"] == updated_content

def test_delete_echo_authenticated(app, client):
    """Test deleting an existing echo/post with an authenticated user."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    # Create a new echo
    test_content = "Delete test " + datetime.now().isoformat(timespec="seconds")
    client.post("/create_echo", data={"echo": test_content})

    # Get the post ID from the database
    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT post_id FROM Posts WHERE content = %s AND is_deleted = FALSE",
            (test_content,),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    post_id = row["post_id"]

    # Delete the echo
    resp = client.post(
        f"/delete_echo/{post_id}",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    # Verify post was marked as deleted in database
    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT is_deleted FROM Posts WHERE post_id = %s",
            (post_id,),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    assert row["is_deleted"] == 1
