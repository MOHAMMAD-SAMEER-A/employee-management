# EnterpriseCore: Employee Management & Task Allocation System

A modular, production-ready full-stack web application designed for enterprise staff administration, payroll tracking, priority task allocation, and non-blocking asynchronous email notifications.

Built with **Python 3**, **Flask (Application Factory Pattern)**, **SQLite**, **Tailwind CSS (Dark Slate aesthetic)**, and **Vanilla JavaScript (ES6+)**.

---

## 🌟 Key Features

- **Role-Based Access Control (RBAC):** Distinct dashboards and security layers for `Administrator` and `Employee` roles with bcrypt hashed passwords and signed session cookies.
- **Executive Operations Dashboard:** Real-time KPI summary cards (Total Payroll, Active Staff, Completion Velocity, Backlog), staff directory with one-click inline payroll status toggling (`Paid` / `Unpaid`), and interactive task allocation tables.
- **Employee Workspace Portal:** Private compensation overview, payslip status tracking, and assigned work order cards with live status transitions (`Pending` ➔ `Ongoing` ➔ `Blocked` ➔ `Completed`).
- **Async Email Notifications (Zero Infrastructure):** Powered by Python's built-in `ThreadPoolExecutor`, `smtplib`, `ssl`, and `email.message.EmailMessage`:
  - **Task Assignment Alert:** Automatically alerts assigned employees when an administrator dispatches work.
  - **Blocker Escalation Alert:** Immediately notifies task creators/admins when an employee flags an operational impediment.
- **Tailwind Dark Slate UI/UX:** Inter font, Lucide icons, glassmorphism cards, glowing accents, live search/filtering, and a non-blocking toast alert system.
- **Automated Test Suite:** Comprehensive test coverage verifying auth, RBAC permissions, cross-tenant isolation, payroll status updates, task transitions, and fail-safe email execution.

---

## 📂 Project Architecture

```
Employee_Management_Web_Application/
├── run.py                          # Application entry point
├── requirements.txt                # Pinned dependencies (Flask, Flask-Bcrypt, python-dotenv)
├── .env.example                    # Environment configuration template
├── tests/
│   └── test_app.py                 # Automated unit and integration test suite
├── app/
│   ├── __init__.py                 # create_app() factory, blueprints & DB lifecycle
│   ├── config.py                   # Environment & secure cookie session settings
│   ├── database.py                 # SQLite connection manager, foreign keys & seeding
│   ├── decorators.py               # Custom RBAC decorators (@login_required, @admin_required, etc.)
│   ├── services/
│   │   ├── __init__.py
│   │   └── email_service.py        # ThreadPoolExecutor background email dispatcher
│   ├── routes/
│   │   ├── auth_routes.py          # /login, /api/auth/login, /api/auth/logout, /api/auth/me
│   │   ├── admin_routes.py         # /admin/dashboard, /api/admin/metrics, /api/admin/employees, /api/admin/tasks
│   │   └── employee_routes.py      # /employee/dashboard, /api/employee/me, /api/employee/my-tasks, /api/employee/tasks/<id>/status
│   ├── static/
│   │   ├── css/
│   │   │   └── custom.css          # Glassmorphism, animations, custom scrollbars, toast keyframes
│   │   └── js/
│   │       ├── api.js              # Unified async fetch client, toast system, formatters, logout handler
│   │       ├── admin.js            # Admin metrics, staff CRUD, 1-click payroll toggle, task dispatching
│   │       └── employee.js         # Employee portal, profile metrics, interactive task cards & blocker escalation
│   └── templates/
│       ├── base.html               # Dark slate layout with Tailwind CDN, Lucide icons, toast alert container
│       ├── auth/
│       │   └── login.html          # Glassmorphic login card with 1-click demo test credential pills
│       ├── admin/
│       │   └── dashboard.html      # Executive KPI grid, staff directory table, task allocation table, modals
│       └── employee/
│           └── dashboard.html      # Profile banner, compensation card, metrics, and live task boards
```

---

## 🚀 Quick Start Guide

### 1. Clone & Setup Environment
```bash
git clone https://github.com/MOHAMMAD-SAMEER-A/employee-management.git
cd employee-management

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Launch Development Server
```bash
python run.py
```
Open **`http://127.0.0.1:5001`** in your browser.

---

## 🔑 Pre-Seeded Demo Accounts

The local SQLite database (`instance/app.db`) automatically seeds on first launch:

| Role | Username | Password | Email |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | `admin@enterprise.internal` |
| **Staff Member** | `sarah.jenkins` | `emp123` | `sarah.j@enterprise.internal` |
| **Staff Member** | `marcus.chen` | `emp123` | `marcus.c@enterprise.internal` |

*(Convenient 1-click credential test pills are also provided directly on the `/login` screen)*

---

## 🧪 Running Tests

Execute the automated test suite:
```bash
python -m unittest discover tests
```

---

## 📧 Testing Local Email Notifications

To verify asynchronous email alerts without configuring live external SMTP credentials:
```bash
# Install aiosmtpd
pip install aiosmtpd

# Launch local SMTP sink on port 1025
python -m aiosmtpd -n -l localhost:1025
```
Emails dispatched when assigning tasks or escalating blockers will stream directly to your terminal.
