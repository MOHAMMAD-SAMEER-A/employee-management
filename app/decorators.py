from functools import wraps
from flask import session, redirect, url_for, request, jsonify

def is_api_request():
    """Determine if current request targets an API endpoint or expects JSON."""
    return request.path.startswith('/api/') or request.is_json or 'application/json' in request.headers.get('Accept', '')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if is_api_request():
                return jsonify({
                    'success': False,
                    'message': 'Authentication required. Please sign in.',
                    'data': None
                }), 401
            return redirect(url_for('auth.login_view'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if is_api_request():
                return jsonify({
                    'success': False,
                    'message': 'Authentication required. Please sign in.',
                    'data': None
                }), 401
            return redirect(url_for('auth.login_view'))
        
        if session.get('role') != 'admin':
            if is_api_request():
                return jsonify({
                    'success': False,
                    'message': 'Access forbidden. Administrator privileges required.',
                    'data': None
                }), 403
            return redirect(url_for('employee.dashboard_view'))
        return f(*args, **kwargs)
    return decorated_function

def employee_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if is_api_request():
                return jsonify({
                    'success': False,
                    'message': 'Authentication required. Please sign in.',
                    'data': None
                }), 401
            return redirect(url_for('auth.login_view'))
        
        if session.get('role') not in ['employee', 'admin']:
            if is_api_request():
                return jsonify({
                    'success': False,
                    'message': 'Access forbidden.',
                    'data': None
                }), 403
            return redirect(url_for('auth.login_view'))
        return f(*args, **kwargs)
    return decorated_function
