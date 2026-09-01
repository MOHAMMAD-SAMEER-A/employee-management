import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "prod-enterprise-secret-key-98765")
    
    # Handle Vercel serverless read-only filesystem
    if os.getenv("VERCEL"):
        DATABASE_PATH = "/tmp/app.db"
    else:
        DATABASE_PATH = os.path.join(BASE_DIR, "instance", "app.db")
        
    DATABASE = DATABASE_PATH
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("VERCEL") is not None

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}
