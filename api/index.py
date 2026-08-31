import sys
import os

# Add root project directory to sys.path for Vercel serverless environment
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
