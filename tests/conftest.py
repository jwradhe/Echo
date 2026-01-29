import os
import pytest

# Configure test environment BEFORE any app imports
# Use environment variables if set (for CI), otherwise use local defaults
os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret-key-for-testing')
os.environ.setdefault('MYSQL_HOST', 'localhost')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('MYSQL_USER', 'root')
os.environ.setdefault('MYSQL_PASSWORD', 'administrator')
os.environ.setdefault('MYSQL_DATABASE', 'EchoDB_test')
os.environ.setdefault('MYSQL_POOL_SIZE', '1')
os.environ.setdefault('MYSQL_POOL_MAX_OVERFLOW', '0')
os.environ.setdefault('MYSQL_POOL_TIMEOUT', '30')
os.environ.setdefault('LOG_LEVEL', 'WARNING')  # Reduce log noise in tests
os.environ.setdefault('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
os.environ.setdefault('PERMANENT_SESSION_LIFETIME_DAYS', '7')
os.environ.setdefault('SESSION_COOKIE_SECURE', 'False')
os.environ.setdefault('SESSION_COOKIE_HTTPONLY', 'True')
os.environ.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')

# Now safe to import app
from app import create_app
from app.db import get_db


@pytest.fixture(scope="session")
def app():
    """Create test Flask app once for all tests."""
    app = create_app()
    app.config["TESTING"] = True
    
    # Initialize database schema for tests
    with app.app_context():
        from app.db import init_db, ensure_default_user
        init_db(app)
        ensure_default_user(app)
    
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean test database before each test."""
    with get_db(app) as conn:
        cursor = conn.cursor()
        # Clean tables in reverse order of foreign key dependencies
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DELETE FROM Posts WHERE 1=1")
        cursor.execute("DELETE FROM Users WHERE user_id != '00000000-0000-0000-0000-000000000000'")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        cursor.close()
        conn.commit()
    yield
