from flask import Blueprint, render_template, request, jsonify, session
from flask_bcrypt import generate_password_hash
from app.database import get_db
from app.decorators import admin_required
from app.services.email_service import notify_task_dispatched

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard_view():
    """Render the Admin operations dashboard."""
    return render_template('admin/dashboard.html')

@admin_bp.route('/api/admin/metrics', methods=['GET'])
@admin_required
def get_metrics():
    """Calculate and return key organizational and operational metrics."""
    db = get_db()

    # Total payroll and staff counts (excluding admin)
    staff_row = db.execute('''
        SELECT 
            COUNT(*) AS active_staff,
            COALESCE(SUM(salary), 0.0) AS total_payroll,
            COALESCE(SUM(CASE WHEN payslip_status = 'Paid' THEN salary ELSE 0 END), 0.0) AS paid_payroll,
            COALESCE(SUM(CASE WHEN payslip_status = 'Unpaid' THEN salary ELSE 0 END), 0.0) AS unpaid_payroll,
            COALESCE(SUM(CASE WHEN payslip_status = 'Paid' THEN 1 ELSE 0 END), 0) AS paid_count,
            COALESCE(SUM(CASE WHEN payslip_status = 'Unpaid' THEN 1 ELSE 0 END), 0) AS unpaid_count
        FROM users
        WHERE role = 'employee' AND is_active = 1
    ''').fetchone()

    # Task completion and status stats
    task_row = db.execute('''
        SELECT 
            COUNT(*) AS total_tasks,
            COALESCE(SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END), 0) AS completed_tasks,
            COALESCE(SUM(CASE WHEN status = 'Ongoing' THEN 1 ELSE 0 END), 0) AS ongoing_tasks,
            COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending_tasks,
            COALESCE(SUM(CASE WHEN status = 'Blocked' THEN 1 ELSE 0 END), 0) AS blocked_tasks,
            COALESCE(SUM(CASE WHEN (priority = 'Urgent' OR status = 'Blocked') AND status != 'Completed' THEN 1 ELSE 0 END), 0) AS urgent_open_tasks
        FROM tasks
    ''').fetchone()

    total_tasks = task_row['total_tasks']
    completed_tasks = task_row['completed_tasks']
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    return jsonify({
        'success': True,
        'message': 'Metrics retrieved successfully.',
        'data': {
            'active_staff': staff_row['active_staff'],
            'total_payroll': float(staff_row['total_payroll']),
            'paid_payroll': float(staff_row['paid_payroll']),
            'unpaid_payroll': float(staff_row['unpaid_payroll']),
            'paid_count': staff_row['paid_count'],
            'unpaid_count': staff_row['unpaid_count'],
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'ongoing_tasks': task_row['ongoing_tasks'],
            'pending_tasks': task_row['pending_tasks'],
            'blocked_tasks': task_row['blocked_tasks'],
            'urgent_open_tasks': task_row['urgent_open_tasks'],
            'completion_rate': completion_rate
        }
    }), 200

@admin_bp.route('/api/admin/employees', methods=['GET'])
@admin_required
def get_employees():
    """Fetch all employee records with their active task counts."""
    db = get_db()
    cursor = db.execute('''
        SELECT 
            u.id,
            u.username,
            u.full_name,
            u.email,
            u.phone,
            u.salary,
            u.payslip_status,
            u.is_active,
            u.created_at,
            COUNT(t.id) AS total_assigned_tasks,
            COALESCE(SUM(CASE WHEN t.status = 'Completed' THEN 1 ELSE 0 END), 0) AS completed_tasks,
            COALESCE(SUM(CASE WHEN t.status != 'Completed' THEN 1 ELSE 0 END), 0) AS pending_tasks
        FROM users u
        LEFT JOIN tasks t ON u.id = t.employee_id
        WHERE u.role = 'employee' AND u.is_active = 1
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''')
    
    employees = [dict(row) for row in cursor.fetchall()]
    return jsonify({
        'success': True,
        'message': 'Employees retrieved successfully.',
        'data': employees
    }), 200

@admin_bp.route('/api/admin/employees/create', methods=['POST'])
@admin_required
def create_employee():
    """Register a new employee."""
    data = request.get_json() or {}
    
    username = (data.get('username') or '').strip().lower()
    password = (data.get('password') or '').strip()
    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    phone = (data.get('phone') or '').strip()
    salary_raw = data.get('salary', 0)
    payslip_status = data.get('payslip_status', 'Unpaid')

    if not all([username, password, full_name, email, phone]):
        return jsonify({
            'success': False,
            'message': 'All fields (Username, Password, Full Name, Email, Phone) are required.',
            'data': None
        }), 400

    try:
        salary = float(salary_raw)
        if salary < 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'message': 'Salary must be a valid non-negative number.',
            'data': None
        }), 400

    if payslip_status not in ['Paid', 'Unpaid']:
        payslip_status = 'Unpaid'

    db = get_db()
    
    # Verify uniqueness
    existing = db.execute(
        'SELECT id, username, email FROM users WHERE username = ? OR email = ?',
        (username, email)
    ).fetchone()
    
    if existing:
        field = 'Username' if existing['username'] == username else 'Email'
        return jsonify({
            'success': False,
            'message': f'{field} is already in use by another account.',
            'data': None
        }), 409

    password_hash = generate_password_hash(password).decode('utf-8')
    
    cursor = db.execute('''
        INSERT INTO users (username, password_hash, role, full_name, email, phone, salary, payslip_status, is_active)
        VALUES (?, ?, 'employee', ?, ?, ?, ?, ?, 1)
    ''', (username, password_hash, full_name, email, phone, salary, payslip_status))
    db.commit()

    new_id = cursor.lastrowid
    return jsonify({
        'success': True,
        'message': f'Employee {full_name} registered successfully.',
        'data': {
            'id': new_id,
            'username': username,
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'salary': salary,
            'payslip_status': payslip_status
        }
    }), 201

@admin_bp.route('/api/admin/employees/<int:employee_id>/toggle-payroll', methods=['PATCH'])
@admin_required
def toggle_payroll(employee_id):
    """Toggle or update an employee's payslip status."""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ? AND role = "employee"', (employee_id,)).fetchone()
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'Employee not found.',
            'data': None
        }), 404

    current_status = user['payslip_status']
    new_status = 'Unpaid' if current_status == 'Paid' else 'Paid'
    
    # Check if request explicitly passed target status
    req_data = request.get_json(silent=True) or {}
    if req_data.get('status') in ['Paid', 'Unpaid']:
        new_status = req_data.get('status')

    db.execute('UPDATE users SET payslip_status = ? WHERE id = ?', (new_status, employee_id))
    db.commit()

    return jsonify({
        'success': True,
        'message': f"Payroll status for {user['full_name']} updated to '{new_status}'.",
        'data': {
            'employee_id': employee_id,
            'payslip_status': new_status
        }
    }), 200

@admin_bp.route('/api/admin/tasks', methods=['GET'])
@admin_bp.route('/api/tasks', methods=['GET'])
@admin_required
def get_tasks():
    """Retrieve all dispatched tasks along with assignee metadata."""
    db = get_db()
    cursor = db.execute('''
        SELECT 
            t.id,
            t.employee_id,
            t.created_by,
            u.full_name AS employee_name,
            u.email AS employee_email,
            admin.full_name AS creator_name,
            admin.email AS creator_email,
            t.task_title,
            t.description,
            t.priority,
            t.status,
            t.assigned_date,
            t.due_date,
            t.updated_at
        FROM tasks t
        JOIN users u ON t.employee_id = u.id
        LEFT JOIN users admin ON t.created_by = admin.id
        ORDER BY 
            CASE t.status
                WHEN 'Blocked' THEN 1
                ELSE 2
            END ASC,
            CASE t.priority 
                WHEN 'Urgent' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                WHEN 'Low' THEN 4 
                ELSE 5 
            END ASC,
            t.due_date ASC,
            t.id DESC
    ''')
    
    tasks = [dict(row) for row in cursor.fetchall()]
    return jsonify({
        'success': True,
        'message': 'Tasks retrieved successfully.',
        'data': tasks
    }), 200

@admin_bp.route('/api/admin/tasks/create', methods=['POST'])
@admin_bp.route('/api/tasks', methods=['POST'])
@admin_required
def create_task():
    """Dispatch a new task to an employee and trigger an asynchronous email alert."""
    data = request.get_json() or {}
    
    employee_id = data.get('employee_id')
    task_title = (data.get('task_title') or '').strip()
    description = (data.get('description') or '').strip()
    priority = data.get('priority', 'Medium')
    due_date = data.get('due_date')
    creator_id = session.get('user_id', 1)

    if not employee_id or not task_title:
        return jsonify({
            'success': False,
            'message': 'Assignee Employee and Task Title are required.',
            'data': None
        }), 400

    if priority not in ['Low', 'Medium', 'High', 'Urgent']:
        priority = 'Medium'

    db = get_db()
    
    # Validate employee exists and is active
    emp = db.execute(
        'SELECT id, full_name, email FROM users WHERE id = ? AND role = "employee" AND is_active = 1',
        (employee_id,)
    ).fetchone()
    
    if not emp:
        return jsonify({
            'success': False,
            'message': 'Selected employee does not exist or is inactive.',
            'data': None
        }), 404

    cursor = db.execute('''
        INSERT INTO tasks (employee_id, created_by, task_title, description, priority, status, due_date)
        VALUES (?, ?, ?, ?, ?, 'Pending', ?)
    ''', (employee_id, creator_id, task_title, description, priority, due_date if due_date else None))
    db.commit()

    task_id = cursor.lastrowid

    # Trigger non-blocking asynchronous email notification to assigned employee
    notify_task_dispatched(
        recipient_email=emp['email'],
        assignee_name=emp['full_name'],
        title=task_title,
        priority=priority,
        due_date=due_date
    )

    return jsonify({
        'success': True,
        'message': f'Task successfully allocated to {emp["full_name"]}. Email alert dispatched.',
        'data': {
            'id': task_id,
            'employee_id': employee_id,
            'employee_name': emp['full_name'],
            'employee_email': emp['email'],
            'task_title': task_title,
            'description': description,
            'priority': priority,
            'status': 'Pending',
            'due_date': due_date
        }
    }), 201
