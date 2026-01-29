import os
import pytest

# Configure test environment BEFORE any app imports
os.environ['FLASK_ENV'] = 'testing'
os.environ['FLASK_SECRET_KEY'] = 'test-secret-key-for-testing'
os.environ['MYSQL_HOST'] = 'localhost'
os.environ['MYSQL_PORT'] = '3306'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = 'administrator'
os.environ['MYSQL_DATABASE'] = 'EchoDB_test'
os.environ['MYSQL_POOL_SIZE'] = '1'
os.environ['MYSQL_POOL_MAX_OVERFLOW'] = '0'
os.environ['MYSQL_POOL_TIMEOUT'] = '30'
os.environ['LOG_LEVEL'] = 'WARNING'  # Reduce log noise in tests
os.environ['LOG_FORMAT'] = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
os.environ['PERMANENT_SESSION_LIFETIME_DAYS'] = '7'
os.environ['SESSION_COOKIE_SECURE'] = 'False'
os.environ['SESSION_COOKIE_HTTPONLY'] = 'True'
os.environ['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Now safe to import app
from app import create_app
from app.db import get_db
import pymysql


@pytest.fixture(scope="session")
def app():
    """Create test Flask app once for all tests."""
    app = create_app()
    app.config["TESTING"] = True
    
    # Initialize database schema for tests
    with app.app_context():
        from app.db import init_db
        init_db(app)
    
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
