from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_bcrypt import check_password_hash
from app.database import get_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Root redirect logic based on current authentication state and role."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard_view'))
        return redirect(url_for('employee.dashboard_view'))
    return redirect(url_for('auth.login_view'))

@auth_bp.route('/login', methods=['GET'])
def login_view():
    """Render the login page if not authenticated."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard_view'))
        return redirect(url_for('employee.dashboard_view'))
    return render_template('auth/login.html')

@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """Handle asynchronous login requests."""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Both username and password are required.',
            'data': None
        }), 400

    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({
            'success': False,
            'message': 'Invalid username or password credentials.',
            'data': None
        }), 401

    # Establish session
    session.clear()
    session.permanent = True
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['full_name'] = user['full_name']
    session['email'] = user['email']

    redirect_url = url_for('admin.dashboard_view') if user['role'] == 'admin' else url_for('employee.dashboard_view')

    return jsonify({
        'success': True,
        'message': f'Welcome back, {user["full_name"]}!',
        'data': {
            'user_id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'role': user['role'],
            'redirect_url': redirect_url
        }
    }), 200

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Handle user logout asynchronously."""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'You have been logged out successfully.',
        'data': {
            'redirect_url': url_for('auth.login_view')
        }
    }), 200

@auth_bp.route('/api/auth/me', methods=['GET'])
def api_current_user():
    """Return currently authenticated user session state."""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not authenticated.',
            'data': None
        }), 401

    return jsonify({
        'success': True,
        'message': 'User session active.',
        'data': {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role'),
            'full_name': session.get('full_name'),
            'email': session.get('email')
        }
    }), 200
