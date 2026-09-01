import sqlite3
import os
from flask import g, current_app
from werkzeug.security import generate_password_hash

def get_db():
    if "db" not in g:
        db_path = current_app.config.get("DATABASE") or current_app.config.get("DATABASE_PATH") or "/tmp/app.db"
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        g.db = sqlite3.connect(db_path, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db(app=None):
    if app is not None:
        with app.app_context():
            _do_init_db()
    else:
        _do_init_db()

def _do_init_db():
    db = get_db()
    
    db.executescript("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('admin', 'employee')) NOT NULL DEFAULT 'employee',
        full_name TEXT,
        phone TEXT,
        salary REAL DEFAULT 0.0,
        payslip_status TEXT DEFAULT 'Paid',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        department_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        designation TEXT NOT NULL,
        salary REAL NOT NULL DEFAULT 0.0,
        phone TEXT,
        joining_date DATE NOT NULL,
        status TEXT CHECK(status IN ('Active', 'On Leave', 'Terminated')) NOT NULL DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        task_title TEXT,
        description TEXT,
        assigned_to INTEGER,
        employee_id INTEGER,
        created_by INTEGER NOT NULL DEFAULT 1,
        priority TEXT CHECK(priority IN ('Low', 'Medium', 'High', 'Urgent', 'Critical')) NOT NULL DEFAULT 'Medium',
        status TEXT CHECK(status IN ('Pending', 'Ongoing', 'In Progress', 'Completed', 'Blocked')) NOT NULL DEFAULT 'Pending',
        assigned_date DATE DEFAULT (DATE('now')),
        due_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (employee_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS task_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        old_status TEXT NOT NULL,
        new_status TEXT NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)
    db.commit()
    seed_data(db)

def seed_data(db):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        return

    departments = [
        ("Engineering", "Software Architecture, Platform Infrastructure, and Quality Engineering"),
        ("Product & Design", "Product Strategy, UX/UI Design, and Systems Management"),
        ("Operations", "DevOps, Corporate Infrastructure, and Security Compliance"),
        ("Human Resources", "Talent Acquisition, People Operations, and Compliance")
    ]
    cursor.executemany("INSERT INTO departments (name, description) VALUES (?, ?)", departments)

    admin_pw = generate_password_hash("Admin@12345")
    emp_pw = generate_password_hash("Employee@12345")

    cursor.execute(
        "INSERT INTO users (username, email, password_hash, role, full_name, phone, salary, payslip_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("admin", "admin@enterprise.internal", admin_pw, "admin", "Executive Administrator", "+1-555-0100", 135000.0, "Paid")
    )
    admin_id = cursor.lastrowid

    employees_data = [
        ("alex.chen", "alex.chen@enterprise.internal", "Alex Chen", 1, "Lead Systems Architect", 145000.0, "+1-555-0101", "2023-01-15"),
        ("sarah.jenkins", "sarah.jenkins@enterprise.internal", "Sarah Jenkins", 2, "Senior Product Designer", 120000.0, "+1-555-0102", "2023-03-01"),
        ("marcus.vance", "marcus.vance@enterprise.internal", "Marcus Vance", 3, "DevOps & Infrastructure Lead", 132000.0, "+1-555-0103", "2023-06-10")
    ]

    for username, email, full_name, dept_id, designation, salary, phone, joining_date in employees_data:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, full_name, phone, salary, payslip_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, email, emp_pw, "employee", full_name, phone, salary, "Paid")
        )
        u_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO employees (user_id, department_id, full_name, designation, salary, phone, joining_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')""",
            (u_id, dept_id, full_name, designation, salary, phone, joining_date)
        )

    db.commit()
