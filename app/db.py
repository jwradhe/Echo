import sqlite3
from flask import Flask

# =====================================================
# Database Helpers
# =====================================================

def get_db(app: Flask):
    """
    Returnerar en SQLite-connection baserat på appens DB_PATH
    """
    conn = sqlite3.connect(app.config["DB_PATH"])
    conn.row_factory = sqlite3.Row

    # settings
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;") 
    return conn


def init_db(app: Flask):
    """
    Skapar databasen och echoes-tabellen om den inte redan finns
    """
    with get_db(app) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS echoes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              echo TEXT NOT NULL,

              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              edited_at  TEXT,

              status TEXT NOT NULL DEFAULT 'published'
            );
            """
        )

        # Index för snabb feed (ORDER BY created_at DESC)
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_echoes_created_at
            ON echoes(created_at DESC);
            """
        )
