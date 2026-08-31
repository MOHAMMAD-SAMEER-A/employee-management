import sqlite3
import os
from pathlib import Path
from flask import g, current_app
from flask_bcrypt import generate_password_hash

def get_db():
    """Obtain a thread-local SQLite connection with row_factory and foreign keys enabled."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        # Ensure instance directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON;')
    return g.db

def close_db(e=None):
    """Close the SQLite database connection if it exists."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    """Initialize database tables, apply schema updates, and run automatic seeding."""
    with app.app_context():
        db = get_db()
        
        # Create users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'employee')) NOT NULL DEFAULT 'employee',
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                salary REAL NOT NULL DEFAULT 0.00,
                payslip_status TEXT CHECK(payslip_status IN ('Paid', 'Unpaid')) NOT NULL DEFAULT 'Unpaid',
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Create tasks table (with Blocked status and created_by reference)
        db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                created_by INTEGER DEFAULT 1,
                task_title TEXT NOT NULL,
                description TEXT,
                priority TEXT CHECK(priority IN ('Low', 'Medium', 'High', 'Urgent')) DEFAULT 'Medium',
                status TEXT CHECK(status IN ('Pending', 'Ongoing', 'Completed', 'Blocked')) DEFAULT 'Pending',
                assigned_date DATE DEFAULT (DATE('now')),
                due_date DATE,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
            );
        ''')
        db.commit()

        # Check and migrate columns if needed for existing DBs
        try:
            cursor = db.execute("PRAGMA table_info(tasks);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'created_by' not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN created_by INTEGER REFERENCES users (id) ON DELETE SET NULL;")
                db.commit()
        except Exception:
            pass
        
        # Auto-seed initial records if users table is empty
        cursor = db.execute('SELECT COUNT(*) as count FROM users;')
        user_count = cursor.fetchone()['count']
        
        if user_count == 0:
            seed_initial_data(db)

def seed_initial_data(db):
    """Seed default administrative credentials, sample employee accounts, and initial tasks."""
    # Password hashes
    admin_pw = generate_password_hash('admin123').decode('utf-8')
    emp_pw = generate_password_hash('emp123').decode('utf-8')
    
    # 1. Admin account
    db.execute('''
        INSERT INTO users (username, password_hash, role, full_name, email, phone, salary, payslip_status, is_active)
        VALUES (?, ?, 'admin', ?, ?, ?, ?, 'Paid', 1)
    ''', (
        'admin',
        admin_pw,
        'Executive Administrator',
        'admin@enterprise.internal',
        '+1 (555) 019-2834',
        135000.00
    ))
    admin_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    
    # 2. Sample Employees
    db.execute('''
        INSERT INTO users (username, password_hash, role, full_name, email, phone, salary, payslip_status, is_active)
        VALUES (?, ?, 'employee', ?, ?, ?, ?, 'Paid', 1)
    ''', (
        'sarah.jenkins',
        emp_pw,
        'Sarah Jenkins',
        'sarah.j@enterprise.internal',
        '+1 (555) 234-5678',
        84000.00
    ))
    sarah_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    
    db.execute('''
        INSERT INTO users (username, password_hash, role, full_name, email, phone, salary, payslip_status, is_active)
        VALUES (?, ?, 'employee', ?, ?, ?, ?, 'Unpaid', 1)
    ''', (
        'marcus.chen',
        emp_pw,
        'Marcus Chen',
        'marcus.c@enterprise.internal',
        '+1 (555) 876-5432',
        92500.00
    ))
    marcus_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    
    # 3. Sample Tasks
    db.execute('''
        INSERT INTO tasks (employee_id, created_by, task_title, description, priority, status, assigned_date, due_date)
        VALUES (?, ?, ?, ?, 'High', 'Completed', DATE('now', '-4 days'), DATE('now', '+2 days'))
    ''', (
        sarah_id,
        admin_id,
        'Deploy Infrastructure to AWS EU Cluster',
        'Configure ECS tasks, provision application load balancers, and setup Route53 health checks.'
    ))
    
    db.execute('''
        INSERT INTO tasks (employee_id, created_by, task_title, description, priority, status, assigned_date, due_date)
        VALUES (?, ?, ?, ?, 'Urgent', 'Ongoing', DATE('now', '-2 days'), DATE('now', '+3 days'))
    ''', (
        sarah_id,
        admin_id,
        'Implement OAuth2 Token Refresh Flow',
        'Update frontend API client interceptor to handle transparent 401 token renewals and backoff retries.'
    ))
    
    db.execute('''
        INSERT INTO tasks (employee_id, created_by, task_title, description, priority, status, assigned_date, due_date)
        VALUES (?, ?, ?, ?, 'Medium', 'Pending', DATE('now', '-1 days'), DATE('now', '+5 days'))
    ''', (
        marcus_id,
        admin_id,
        'Security Audit & Dependency Upgrades',
        'Run vulnerability scans across all Python and JavaScript modules, resolve CVE alerts and test regressions.'
    ))
    
    db.commit()
