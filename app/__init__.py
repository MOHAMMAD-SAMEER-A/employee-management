import os
from flask import Flask, jsonify, render_template, request
from app.config import Config
from app.database import init_db, close_db
from app.routes.auth_routes import auth_bp
from app.routes.admin_routes import admin_bp
from app.routes.employee_routes import employee_bp

def create_app(config_class=Config):
    """Application factory for Employee Management & Task Allocation Web Application."""
    app = Flask(__name__)
    if isinstance(config_class, str):
        from app.config import config_by_name
        config_class = config_by_name.get(config_class, Config)
    app.config.from_object(config_class)

    # Safely ensure instance folder exists if writable
    try:
        if app.instance_path:
            os.makedirs(app.instance_path, exist_ok=True)
    except (OSError, PermissionError):
        pass

    # Initialize Database & Seeding
    init_db(app)
    app.teardown_appcontext(close_db)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)

    # Context processors for templates
    @app.context_processor
    def inject_global_vars():
        return {
            'app_name': 'Enterprise Core'
        }

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                'success': False,
                'message': 'Resource not found.',
                'data': None
            }), 404
        return render_template('auth/login.html', error_msg='Page not found.'), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({
                'success': False,
                'message': 'An internal server error occurred.',
                'data': None
            }), 500
        return render_template('auth/login.html', error_msg='Internal server error.'), 500

    return app
