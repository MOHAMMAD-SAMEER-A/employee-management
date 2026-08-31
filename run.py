import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']
    print(f"🚀 Starting Employee Management Web Application on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
