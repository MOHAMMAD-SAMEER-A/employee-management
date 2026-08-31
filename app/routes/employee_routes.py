from flask import Blueprint, render_template, request, jsonify, session
from app.database import get_db
from app.decorators import employee_required
from app.services.email_service import notify_task_blocked

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/employee/dashboard')
@employee_required
def dashboard_view():
    """Render the Employee portal dashboard."""
    return render_template('employee/dashboard.html')

@employee_bp.route('/api/employee/me', methods=['GET'])
@employee_required
def get_my_profile():
    """Fetch current employee's personal profile and task stats."""
    user_id = session.get('user_id')
    db = get_db()
    
    user = db.execute('''
        SELECT 
            id, username, full_name, email, phone, salary, payslip_status, created_at
        FROM users 
        WHERE id = ? AND is_active = 1
    ''', (user_id,)).fetchone()

    if not user:
        return jsonify({
            'success': False,
            'message': 'Employee profile not found.',
            'data': None
        }), 404

    # Calculate employee's task metrics
    task_stats = db.execute('''
        SELECT 
            COUNT(*) AS total_tasks,
            COALESCE(SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END), 0) AS completed_tasks,
            COALESCE(SUM(CASE WHEN status = 'Ongoing' THEN 1 ELSE 0 END), 0) AS ongoing_tasks,
            COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending_tasks,
            COALESCE(SUM(CASE WHEN status = 'Blocked' THEN 1 ELSE 0 END), 0) AS blocked_tasks
        FROM tasks
        WHERE employee_id = ?
    ''', (user_id,)).fetchone()

    total = task_stats['total_tasks']
    completed = task_stats['completed_tasks']
    completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

    profile_data = dict(user)
    profile_data['metrics'] = {
        'total_tasks': total,
        'completed_tasks': completed,
        'ongoing_tasks': task_stats['ongoing_tasks'],
        'pending_tasks': task_stats['pending_tasks'],
        'blocked_tasks': task_stats['blocked_tasks'],
        'completion_rate': completion_rate
    }

    return jsonify({
        'success': True,
        'message': 'Profile retrieved successfully.',
        'data': profile_data
    }), 200

@employee_bp.route('/api/employee/my-tasks', methods=['GET'])
@employee_required
def get_my_tasks():
    """Retrieve all tasks assigned to the current employee."""
    user_id = session.get('user_id')
    db = get_db()
    
    cursor = db.execute('''
        SELECT 
            id,
            employee_id,
            created_by,
            task_title,
            description,
            priority,
            status,
            assigned_date,
            due_date,
            updated_at
        FROM tasks
        WHERE employee_id = ?
        ORDER BY 
            CASE status
                WHEN 'Blocked' THEN 1
                WHEN 'Ongoing' THEN 2
                WHEN 'Pending' THEN 3
                WHEN 'Completed' THEN 4
                ELSE 5
            END ASC,
            CASE priority 
                WHEN 'Urgent' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                WHEN 'Low' THEN 4 
                ELSE 5 
            END ASC,
            due_date ASC
    ''', (user_id,))
    
    tasks = [dict(row) for row in cursor.fetchall()]
    return jsonify({
        'success': True,
        'message': 'Tasks retrieved successfully.',
        'data': tasks
    }), 200

@employee_bp.route('/api/employee/tasks/<int:task_id>/status', methods=['PATCH'])
@employee_bp.route('/api/tasks/<int:task_id>/status', methods=['PATCH'])
@employee_required
def update_task_status(task_id):
    """Update progress status on an assigned task and escalate blockers asynchronously."""
    user_id = session.get('user_id')
    data = request.get_json() or {}
    new_status = data.get('status')
    blocker_comment = (data.get('comment') or data.get('blocker_comment') or '').strip()

    if new_status not in ['Pending', 'Ongoing', 'Completed', 'Blocked']:
        return jsonify({
            'success': False,
            'message': "Invalid status. Must be 'Pending', 'Ongoing', 'Completed', or 'Blocked'.",
            'data': None
        }), 400

    db = get_db()
    task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

    if not task:
        return jsonify({
            'success': False,
            'message': 'Task not found.',
            'data': None
        }), 404

    # Security check: Non-admins can only mutate their own tasks
    if task['employee_id'] != user_id and session.get('role') != 'admin':
        return jsonify({
            'success': False,
            'message': 'Access forbidden. You cannot modify tasks assigned to other employees.',
            'data': None
        }), 403

    # Update database record
    db.execute('''
        UPDATE tasks 
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, task_id))
    db.commit()

    # Trigger Blocker Escalation Email if new_status is Blocked
    if new_status == 'Blocked':
        # Retrieve task creator info or fallback to primary admin
        creator = None
        if task['created_by']:
            creator = db.execute(
                'SELECT username, email, full_name FROM users WHERE id = ? AND is_active = 1',
                (task['created_by'],)
            ).fetchone()

        if not creator:
            creator = db.execute(
                'SELECT username, email, full_name FROM users WHERE role = "admin" AND is_active = 1 ORDER BY id ASC LIMIT 1'
            ).fetchone()

        # Fetch current assignee name
        assignee_name = session.get('full_name') or 'Assigned Employee'

        if creator and creator['email']:
            notify_task_blocked(
                admin_email=creator['email'],
                admin_username=creator['username'],
                assignee_name=assignee_name,
                title=task['task_title'],
                comment=blocker_comment if blocker_comment else 'Roadblock reported by employee during execution.'
            )

    return jsonify({
        'success': True,
        'message': f"Task status updated to '{new_status}'." + (" Blocker alert escalated to administrator." if new_status == 'Blocked' else ""),
        'data': {
            'task_id': task_id,
            'status': new_status,
            'comment': blocker_comment if new_status == 'Blocked' else None
        }
    }), 200
