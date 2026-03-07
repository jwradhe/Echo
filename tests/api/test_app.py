from datetime import datetime
from io import BytesIO
from uuid import uuid4
import pymysql
from PIL import Image
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


def _login_user(client, username: str, password: str) -> None:
    resp = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 302


def _logout_user(client) -> None:
    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302


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


def test_api_comments_requires_login(client, app):
    """Comment API should return 401 when unauthenticated."""
    post_id = str(uuid4())
    now = datetime.now().isoformat(timespec="seconds")

    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT user_id FROM Users WHERE is_deleted = FALSE LIMIT 1")
        user_row = cursor.fetchone()
        assert user_row is not None
        cursor.execute(
            """
            INSERT INTO Posts (post_id, user_id, content, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (post_id, user_row["user_id"], "Comment auth test post", now, now),
        )
        conn.commit()
        cursor.close()

    resp = client.post(f"/api/posts/{post_id}/comments", json={"content": "Test"})
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


def test_create_comment_authenticated(app, client):
    """Authenticated user can comment on an existing post."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    post_content = "Post for comment " + datetime.now().isoformat(timespec="seconds")
    create_resp = client.post("/api/posts", json={"content": post_content})
    assert create_resp.status_code == 201
    post_id = create_resp.get_json()["post_id"]

    comment_content = "Comment test " + datetime.now().isoformat(timespec="seconds")
    comment_resp = client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": comment_content},
    )
    assert comment_resp.status_code == 201

    payload = comment_resp.get_json()
    assert payload["post_id"] == post_id
    assert payload["content"] == comment_content

    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT content, parent_post_id
            FROM Replies
            WHERE parent_post_id = %s AND content = %s AND is_deleted = FALSE
            """,
            (post_id, comment_content),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    assert row["parent_post_id"] == post_id
    assert row["content"] == comment_content


def test_closed_thread_blocks_new_comments(app, client):
    """Post owner can close thread and new comments are blocked."""
    owner_suffix = datetime.now().isoformat(timespec="seconds").replace(":", "") + "_owner"
    owner = _register_user(client, owner_suffix)
    assert owner["response"].status_code == 302

    create_resp = client.post("/api/posts", json={"content": "Thread lock post"})
    assert create_resp.status_code == 201
    post_id = create_resp.get_json()["post_id"]

    _logout_user(client)
    commenter_suffix = datetime.now().isoformat(timespec="seconds").replace(":", "") + "_commenter"
    commenter = _register_user(client, commenter_suffix)
    assert commenter["response"].status_code == 302

    first_comment = client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": "First comment before lock"},
    )
    assert first_comment.status_code == 201

    _logout_user(client)
    _login_user(client, owner["username"], owner["password"])

    lock_resp = client.post(
        f"/api/posts/{post_id}/reply-lock",
        json={"is_closed": True},
    )
    assert lock_resp.status_code == 200
    assert lock_resp.get_json()["is_closed"] is True

    _logout_user(client)
    _login_user(client, commenter["username"], commenter["password"])

    blocked_comment = client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": "Should be blocked"},
    )
    assert blocked_comment.status_code == 403


def test_split_discussion_selects_commenters(app, client):
    """Owner can split discussion and select specific commenters."""
    owner_suffix = datetime.now().isoformat(timespec="seconds").replace(":", "") + "_split_owner"
    owner = _register_user(client, owner_suffix)
    assert owner["response"].status_code == 302

    create_resp = client.post("/api/posts", json={"content": "Split this discussion"})
    assert create_resp.status_code == 201
    post_id = create_resp.get_json()["post_id"]

    _logout_user(client)
    commenter_a = _register_user(client, datetime.now().isoformat(timespec="seconds").replace(":", "") + "_a")
    assert commenter_a["response"].status_code == 302
    comment_a_content = "A comment before split from selected user"
    comment_a_resp = client.post(f"/api/posts/{post_id}/comments", json={"content": comment_a_content})
    assert comment_a_resp.status_code == 201

    _logout_user(client)
    commenter_b = _register_user(client, datetime.now().isoformat(timespec="seconds").replace(":", "") + "_b")
    assert commenter_b["response"].status_code == 302
    comment_b_content = "B comment before split from non-selected user"
    comment_b_resp = client.post(f"/api/posts/{post_id}/comments", json={"content": comment_b_content})
    assert comment_b_resp.status_code == 201

    _logout_user(client)
    _login_user(client, owner["username"], owner["password"])

    # Resolve commenter_a user id and retry with valid payload
    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT user_id FROM Users WHERE username = %s", (commenter_a["username"],))
        commenter_a_row = cursor.fetchone()
        cursor.execute("SELECT user_id FROM Users WHERE username = %s", (owner["username"],))
        owner_row = cursor.fetchone()
        cursor.close()

    assert commenter_a_row is not None
    assert owner_row is not None

    split_resp = client.post(
        f"/api/posts/{post_id}/discussion-groups",
        json={
            "name": "Utbrytning test",
            "participant_user_ids": [commenter_a_row["user_id"]],
        },
    )
    assert split_resp.status_code == 201
    payload = split_resp.get_json()
    group_id = payload["group_id"]

    reopen_resp = client.post(
        f"/api/posts/{post_id}/reply-lock",
        json={"is_closed": False},
    )
    assert reopen_resp.status_code == 400

    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT name, origin_post_id, created_by FROM UserGroups WHERE group_id = %s",
            (group_id,),
        )
        group_row = cursor.fetchone()
        cursor.execute(
            "SELECT user_id FROM GroupMembers WHERE group_id = %s ORDER BY user_id",
            (group_id,),
        )
        member_rows = cursor.fetchall()
        cursor.execute("SELECT user_id FROM Users WHERE username = %s", (commenter_b["username"],))
        commenter_b_row = cursor.fetchone()
        cursor.close()

    assert group_row is not None
    assert group_row["name"] == "Utbrytning test"
    assert group_row["origin_post_id"] == post_id
    assert group_row["created_by"] == owner_row["user_id"]
    assert commenter_b_row is not None

    member_ids = {row["user_id"] for row in member_rows}
    assert owner_row["user_id"] in member_ids
    assert commenter_a_row["user_id"] in member_ids
    assert commenter_b_row["user_id"] not in member_ids

    _logout_user(client)
    _login_user(client, commenter_a["username"], commenter_a["password"])
    private_after_split_content = "Only selected users should see this after split"
    allowed_reply_resp = client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": private_after_split_content},
    )
    assert allowed_reply_resp.status_code == 201
    selected_dashboard_resp = client.get("/dashboard")
    assert selected_dashboard_resp.status_code == 200
    assert private_after_split_content.encode("utf-8") in selected_dashboard_resp.data

    _logout_user(client)
    _login_user(client, commenter_b["username"], commenter_b["password"])
    blocked_reply_resp = client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": "Should not be allowed after split"},
    )
    assert blocked_reply_resp.status_code == 403
    dashboard_resp = client.get("/dashboard")
    assert dashboard_resp.status_code == 200
    assert comment_a_content.encode("utf-8") in dashboard_resp.data
    assert comment_b_content.encode("utf-8") in dashboard_resp.data
    assert private_after_split_content.encode("utf-8") not in dashboard_resp.data


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


def test_get_profile_api_by_username(client):
    """Profile API should return profile payload for existing user."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    resp = client.get(f"/api/profile/{result['username']}")
    assert resp.status_code == 200

    payload = resp.get_json()
    assert payload["username"] == result["username"]
    assert "posts_count" in payload
    assert "followers_count" in payload
    assert "following_count" in payload


def test_update_profile_api_authenticated(app, client):
    """Authenticated user can update profile fields via API."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    resp = client.put(
        "/api/profile",
        json={
            "display_name": "Updated Display Name",
            "bio": "Updated bio from API test",
        },
    )
    assert resp.status_code == 200

    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT display_name, bio FROM Users WHERE username = %s",
            (result["username"],),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    assert row["display_name"] == "Updated Display Name"
    assert row["bio"] == "Updated bio from API test"


def test_delete_profile_api_authenticated(app, client):
    """Authenticated user can soft-delete profile via API."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    resp = client.delete("/api/profile")
    assert resp.status_code == 200

    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT is_deleted FROM Users WHERE username = %s",
            (result["username"],),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    assert row["is_deleted"] == 1

    # Session should be invalidated by API delete
    post_resp = client.post("/api/posts", json={"content": "should fail"})
    assert post_resp.status_code == 401


def test_update_profile_picture_authenticated(app, client):
    """Authenticated user can upload a valid profile image."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    image_io = BytesIO()
    image = Image.new("RGB", (1024, 1024), color=(0, 120, 255))
    image.save(image_io, format="PNG")
    image_io.seek(0)

    resp = client.post(
        "/profile/picture",
        data={"profile_picture": (image_io, "avatar.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT m.url, m.media_type
            FROM Users u
            JOIN Media m ON m.media_id = u.profile_media_id
            WHERE u.username = %s
            LIMIT 1
            """,
            (result["username"],),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    assert row["media_type"] == "image/webp"
    assert row["url"].endswith(".webp")


def test_update_profile_picture_invalid_format_rejected(app, client):
    """Uploading non-image file should be rejected and not persisted."""
    suffix = datetime.now().isoformat(timespec="seconds").replace(":", "")
    result = _register_user(client, suffix)
    assert result["response"].status_code == 302

    fake_file = BytesIO(b"not-an-image")
    resp = client.post(
        "/profile/picture",
        data={"profile_picture": (fake_file, "avatar.txt")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with get_db(app) as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT profile_media_id FROM Users WHERE username = %s LIMIT 1",
            (result["username"],),
        )
        row = cursor.fetchone()
        cursor.close()

    assert row is not None
    assert row["profile_media_id"] is None
