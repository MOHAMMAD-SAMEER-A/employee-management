import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def get_database_path():
    """Dynamically determine writable database path for serverless and local environments."""
    if os.getenv("DATABASE_PATH"):
        return os.getenv("DATABASE_PATH")
    
    # Check for serverless/read-only runtime indicators
    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT"):
        return "/tmp/app.db"

    # Test write permissions on local instance directory
    try:
        inst_dir = BASE_DIR / "instance"
        inst_dir.mkdir(parents=True, exist_ok=True)
        test_file = inst_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return str(inst_dir / "app.db")
    except Exception:
        return "/tmp/app.db"

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "prod-enterprise-secret-key-98765")
    DATABASE_PATH = get_database_path()
    DATABASE = DATABASE_PATH
    
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("VERCEL") is not None or os.getenv("VERCEL_ENV") is not None

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}
