import pymysql
from pymysql import cursors
from flask import Flask
from contextlib import contextmanager
from typing import Any, Generator, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_connection_pool: Optional[Any] = None


def get_connection_pool():
    """Returns the global connection pool or None if not initialized."""
    global _connection_pool
    return _connection_pool


def init_connection_pool(app: Flask) -> None:
    """Initialize MySQL connection pool."""
    global _connection_pool
    
    try:
        from dbutils.pooled_db import PooledDB

        _connection_pool = PooledDB(
            creator=pymysql,
            maxconnections=app.config.get("MYSQL_POOL_SIZE", 10),
            mincached=2,
            maxcached=5,
            maxshared=3,
            blocking=True,
            maxusage=None,
            setsession=[],
            ping=1,
            host=app.config.get("MYSQL_HOST", "localhost"),
            port=app.config.get("MYSQL_PORT", 3306),
            user=app.config.get("MYSQL_USER", "root"),
            password=app.config.get("MYSQL_PASSWORD", ""),
            database=app.config.get("MYSQL_DATABASE", "EchoDB"),
            charset="utf8mb4",
            autocommit=False,
        )
        logger.info(f"MySQL connection pool initialized for {app.config.get('MYSQL_DATABASE')}")
    except ImportError:
        logger.warning("DBUtils not available. Falling back to direct PyMySQL connections.")
        _connection_pool = None


@contextmanager
def get_db(app: Flask) -> Generator:
    """Context manager for database connections."""
    conn = None
    try:
        pool = get_connection_pool()
        if pool:
            conn = pool.connection()
        else:
            # Fallback to direct connection if pool not initialized
            conn = pymysql.connect(
                host=app.config.get("MYSQL_HOST", "localhost"),
                port=app.config.get("MYSQL_PORT", 3306),
                user=app.config.get("MYSQL_USER", "root"),
                password=app.config.get("MYSQL_PASSWORD", ""),
                database=app.config.get("MYSQL_DATABASE", "EchoDB"),
                charset="utf8mb4",
                autocommit=False,
            )
        
        # Enable foreign keys
        cursor = conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        cursor.close()
        
        yield conn
        conn.commit()
        
    except pymysql.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(app: Flask, query: str, params: tuple = (), fetch_one: bool = False) -> Any:
    """Execute query and return results."""
    with get_db(app) as conn:
        cursor = conn.cursor(cursors.DictCursor)
        try:
            cursor.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            else:
                return cursor.fetchall()
        finally:
            cursor.close()


def execute_update(app: Flask, query: str, params: tuple = ()) -> int:
    """Execute INSERT, UPDATE, or DELETE query."""
    with get_db(app) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        finally:
            cursor.close()


def init_db(app: Flask) -> None:
    """Initialize database schema from schema.sql."""
    import os
    import re
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    
    if not os.path.exists(schema_path):
        logger.warning(f"Schema file not found at {schema_path}")
        return
    
    # Connect directly to the database
    try:
        conn = pymysql.connect(
            host=app.config.get("MYSQL_HOST", "localhost"),
            port=app.config.get("MYSQL_PORT", 3306),
            user=app.config.get("MYSQL_USER", "root"),
            password=app.config.get("MYSQL_PASSWORD", ""),
            database=app.config.get("MYSQL_DATABASE", "EchoDB"),
            charset="utf8mb4",
        )
        cursor = conn.cursor()
        
        # Read schema SQL
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        # Remove comment lines and separator lines before parsing
        lines = []
        for line in schema_sql.split("\n"):
            stripped = line.strip()
            # Skip SQL comments and separator lines
            if stripped.startswith("--") or re.match(r'^-+$', stripped) or not stripped:
                continue
            lines.append(line)
        
        cleaned_sql = "\n".join(lines)
        
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]
        
        for statement in statements:
            # Skip CREATE DATABASE and USE statements
            if statement.upper().startswith("CREATE DATABASE") or statement.upper().startswith("USE "):
                continue
                
            try:
                cursor.execute(statement)
            except pymysql.Error as e:
                # Reduce noise for idempotent schema operations
                # 1061: Duplicate key name (indexes)
                # 1826: Duplicate foreign key constraint name
                if e.args and e.args[0] in (1061, 1826):
                    logger.debug(f"Schema statement skipped (already exists): {e}")
                else:
                    logger.warning(f"Schema statement error (may be benign): {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database schema initialized successfully")
        
    except pymysql.Error as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


def ensure_default_user(app: Flask) -> str:
    """Ensure default test user exists."""
    default_user_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        with get_db(app) as conn:
            cursor = conn.cursor()
            
            # Check if default user already exists
            cursor.execute(
                "SELECT user_id FROM Users WHERE user_id = %s",
                (default_user_id,)
            )
            
            if cursor.fetchone():
                logger.debug(f"Default user {default_user_id} already exists")
                cursor.close()
                return default_user_id
            
            # Create default user if it doesn't exist
            cursor.execute(
                """
                INSERT INTO Users (user_id, username, email, password_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    default_user_id,
                    "testuser",
                    "test@example.com",
                    "test_hash",
                    datetime.now().isoformat(timespec="seconds"),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            cursor.close()
            conn.commit()
            logger.info(f"Created default user {default_user_id}")
            return default_user_id
            
    except pymysql.Error as e:
        logger.error(f"Failed to ensure default user: {e}")
        return default_user_id  # Still return the ID so posts can use it
