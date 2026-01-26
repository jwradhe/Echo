from datetime import datetime
import sqlite3
from app import create_app

# =====================================================
# Helpers
# =====================================================

def exec_sql(db_path: str, sql: str, params=()):
    con = sqlite3.connect(db_path)
    try:
        con.execute(sql, params)
        con.commit()
    finally:
        con.close()

def fetch_one(db_path: str, sql: str, params=()):
    con = sqlite3.connect(db_path)
    try:
        return con.execute(sql, params).fetchone()
    finally:
        con.close()

# =====================================================
# Test Data
# =====================================================

echo = "Unit test " + datetime.now().isoformat(timespec="seconds")

# =====================================================
# Tests
# =====================================================

def test_dashboard_loads(tmp_path):
    db_path = tmp_path / "app.db"
    app = create_app({"TESTING": True, "DB_PATH": str(db_path)})
    client = app.test_client()

    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_create_echo(tmp_path):
    db_path = tmp_path / "app.db"
    app = create_app({"TESTING": True, "DB_PATH": str(db_path)})
    client = app.test_client()

    resp = client.post(
        "/create_echo",
        data={"echo": echo, "status": "published"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    row = fetch_one(str(db_path), "SELECT echo, status FROM echoes WHERE echo = ?", (echo,))
    assert row is not None
    assert row[0] == echo
    assert row[1] == "published"

def test_echo_visible_on_dashboard(tmp_path):
    db_path = tmp_path / "app.db"
    app = create_app({"TESTING": True, "DB_PATH": str(db_path)})
    client = app.test_client()

    client.post("/create_echo", data={"echo": echo, "status": "published"})

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert echo.encode("utf-8") in resp.data
