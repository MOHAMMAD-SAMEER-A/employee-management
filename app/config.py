import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

def get_database_path():
    """Determine database path safely handling local and read-only serverless environments."""
    if os.environ.get('DATABASE_PATH'):
        return os.environ.get('DATABASE_PATH')
    
    # Serverless runtime indicators (Vercel, AWS Lambda)
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('LAMBDA_TASK_ROOT'):
        return '/tmp/app.db'
    
    try:
        inst_dir = BASE_DIR / 'instance'
        inst_dir.mkdir(parents=True, exist_ok=True)
        return str(inst_dir / 'app.db')
    except (OSError, PermissionError):
        return '/tmp/app.db'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'enterprise-super-secret-key-3dd0d6d8')
    DATABASE = get_database_path()
    
    # Secure Session Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production environments
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # JSON Settings
    JSON_SORT_KEYS = False

    # SMTP & Asynchronous Email Notification Settings
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'TaskCorp Alerts <notifications@enterprise.internal>')
