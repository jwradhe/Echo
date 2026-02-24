"""
Application configuration for different environments.
Handles development, testing, and production settings.
"""
import os
from datetime import timedelta


class Config:
    """Base configuration shared across all environments."""
    
    # Flask Core
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    TESTING = False
    PROPAGATE_EXCEPTIONS = None
    PRESERVE_CONTEXT_ON_EXCEPTION = None
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get("PERMANENT_SESSION_LIFETIME_DAYS", "7")))
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() == "true"
    SESSION_COOKIE_HTTPONLY = os.environ.get("SESSION_COOKIE_HTTPONLY", "True").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    
    # Database Configuration (MySQL)
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "EchoDB")
    
    # Connection Pool Configuration
    MYSQL_POOL_SIZE = int(os.environ.get("MYSQL_POOL_SIZE", "10"))
    MYSQL_POOL_MAX_OVERFLOW = int(os.environ.get("MYSQL_POOL_MAX_OVERFLOW", "5"))
    MYSQL_POOL_TIMEOUT = int(os.environ.get("MYSQL_POOL_TIMEOUT", "30"))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Profile image upload configuration
    PROFILE_IMAGE_MAX_BYTES = int(os.environ.get("PROFILE_IMAGE_MAX_BYTES", str(5 * 1024 * 1024)))
    PROFILE_IMAGE_MAX_DIMENSION = int(os.environ.get("PROFILE_IMAGE_MAX_DIMENSION", "512"))
    PROFILE_IMAGE_UPLOAD_SUBDIR = os.environ.get("PROFILE_IMAGE_UPLOAD_SUBDIR", "uploads/profile")
    
    @staticmethod
    def get_database_url():
        """Build database URL from configuration."""
        host = os.environ.get("MYSQL_HOST", "localhost")
        port = os.environ.get("MYSQL_PORT", "3306")
        user = os.environ.get("MYSQL_USER", "root")
        password = os.environ.get("MYSQL_PASSWORD", "")
        database = os.environ.get("MYSQL_DATABASE", "EchoDB")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    ENV = "development"
    DEBUG = True
    TESTING = False
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
    
    MYSQL_POOL_SIZE = int(os.environ.get("MYSQL_POOL_SIZE", "10"))
    MYSQL_POOL_MAX_OVERFLOW = int(os.environ.get("MYSQL_POOL_MAX_OVERFLOW", "5"))
    
    LOG_LEVEL = "DEBUG"
    PROPAGATE_EXCEPTIONS = True
    PRESERVE_CONTEXT_ON_EXCEPTION = True


class TestingConfig(Config):
    """Testing environment configuration."""
    
    ENV = "testing"
    DEBUG = True
    TESTING = True
    
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "EchoDB_test")
    MYSQL_POOL_SIZE = int(os.environ.get("MYSQL_POOL_SIZE", "1"))
    MYSQL_POOL_MAX_OVERFLOW = int(os.environ.get("MYSQL_POOL_MAX_OVERFLOW", "0"))
    
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = "DEBUG"
    PROPAGATE_EXCEPTIONS = True
    PRESERVE_CONTEXT_ON_EXCEPTION = True


class ProductionConfig(Config):
    """Production environment configuration."""
    
    ENV = "production"
    DEBUG = False
    TESTING = False
    
    def __init__(self):
        super().__init__()
        if not os.environ.get("MYSQL_HOST") or not os.environ.get("MYSQL_USER") or not os.environ.get("MYSQL_PASSWORD"):
            raise ValueError(
                "Production requires MYSQL_HOST, MYSQL_USER, and MYSQL_PASSWORD "
                "environment variables to be set."
            )
    
    MYSQL_POOL_SIZE = int(os.environ.get("MYSQL_POOL_SIZE", "20"))
    MYSQL_POOL_MAX_OVERFLOW = int(os.environ.get("MYSQL_POOL_MAX_OVERFLOW", "10"))
    
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    LOG_LEVEL = "WARNING"
    PROPAGATE_EXCEPTIONS = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False


def get_config(env: str = None) -> Config:
    """Get configuration for the specified environment."""
    if env is None:
        env = os.environ.get("FLASK_ENV", "development").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "dev": DevelopmentConfig,
        "testing": TestingConfig,
        "test": TestingConfig,
        "production": ProductionConfig,
        "prod": ProductionConfig,
    }
    
    config_class = config_map.get(env)
    if config_class is None:
        raise ValueError(f"Unknown environment: {env}")
    
    return config_class()
