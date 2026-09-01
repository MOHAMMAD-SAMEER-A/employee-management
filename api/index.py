import sys
import os
from pathlib import Path

# Add project root to sys.path for Vercel Serverless environment
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app

# Instantiate Flask WSGI application for Vercel
app = create_app(os.getenv("FLASK_ENV", "production"))
handler = app

if __name__ == "__main__":
    app.run()
