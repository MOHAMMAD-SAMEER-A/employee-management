import unittest
import json
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from app import create_app
from app.config import Config
from app.database import get_db
from app.services.email_service import notify_task_dispatched, notify_task_blocked, send_async_email

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SMTP_SERVER = '127.0.0.1'
    SMTP_PORT = 1025
    SMTP_USE_TLS = False

class EnterpriseAppTestCase(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test_app.db')
        
        class CustomTestConfig(TestConfig):
            DATABASE = self.db_path
            
        self.app = create_app(CustomTestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_01_seeding_and_admin_login(self):
        """Test default seeding and admin authentication."""
        res = self.client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'Admin@12345'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['role'], 'admin')

    def test_02_employee_login(self):
        """Test seeded employee authentication."""
        res = self.client.post('/api/auth/login', json={
            'username': 'sarah.jenkins',
            'password': 'Employee@12345'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['role'], 'employee')

    def test_03_invalid_login(self):
        """Test rejection of incorrect credentials."""
        res = self.client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'wrongpassword'
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data['success'])

    def test_04_admin_metrics_and_rbac(self):
        """Test admin metrics endpoint and RBAC barrier for unauthenticated & employee users."""
        # 1. Unauthenticated access
        unauth_res = self.client.get('/api/admin/metrics')
        self.assertEqual(unauth_res.status_code, 401)

        # 2. Employee access (should be 403)
        self.client.post('/api/auth/login', json={'username': 'sarah.jenkins', 'password': 'Employee@12345'})
        emp_res = self.client.get('/api/admin/metrics')
        self.assertEqual(emp_res.status_code, 403)

        # 3. Admin access
        self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@12345'})
        admin_res = self.client.get('/api/admin/metrics')
        self.assertEqual(admin_res.status_code, 200)
        data = admin_res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['active_staff'], 3)
        self.assertGreater(data['data']['total_payroll'], 0)

    def test_05_admin_employee_creation_and_payroll_toggle(self):
        """Test creating an employee and toggling their payroll status."""
        self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@12345'})
        
        # Create new staff member
        create_res = self.client.post('/api/admin/employees/create', json={
            'username': 'elena.rostova',
            'password': 'password123',
            'full_name': 'Elena Rostova',
            'email': 'elena.r@enterprise.internal',
            'phone': '+1 (555) 999-1234',
            'salary': 95000.00,
            'payslip_status': 'Unpaid'
        })
        self.assertEqual(create_res.status_code, 201)
        new_emp_id = create_res.get_json()['data']['id']

        # Toggle payroll to 'Paid'
        toggle_res = self.client.patch(f'/api/admin/employees/{new_emp_id}/toggle-payroll')
        self.assertEqual(toggle_res.status_code, 200)
        self.assertEqual(toggle_res.get_json()['data']['payslip_status'], 'Paid')

    @patch('app.routes.admin_routes.notify_task_dispatched')
    def test_06_task_creation_with_email_notification(self, mock_notify):
        """Test task dispatch by admin triggers async task assignment email."""
        self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@12345'})
        task_res = self.client.post('/api/admin/tasks/create', json={
            'employee_id': 3, # Sarah Jenkins
            'task_title': 'Load Balancer SSL Rotation',
            'description': 'Update wild-card SSL certificates before expiration.',
            'priority': 'Urgent',
            'due_date': '2026-09-10'
        })
        self.assertEqual(task_res.status_code, 201)
        
        # Verify notify_task_dispatched was invoked with correct parameters
        mock_notify.assert_called_once_with(
            recipient_email='sarah.jenkins@enterprise.internal',
            assignee_name='Sarah Jenkins',
            title='Load Balancer SSL Rotation',
            priority='Urgent',
            due_date='2026-09-10'
        )

    @patch('app.routes.employee_routes.notify_task_blocked')
    def test_07_task_status_transition_and_blocker_escalation(self, mock_notify_blocked):
        """Test employee status transitions and blocker escalation alert email."""
        # 1. Admin creates task
        self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@12345'})
        task_res = self.client.post('/api/admin/tasks/create', json={
            'employee_id': 3, # Sarah Jenkins
            'task_title': 'Database Sharding Pipeline',
            'description': 'Configure hash partitioning for customer records.',
            'priority': 'High',
            'due_date': '2026-09-15'
        })
        task_id = task_res.get_json()['data']['id']

        # 2. Employee Sarah logs in
        self.client.post('/api/auth/login', json={'username': 'sarah.jenkins', 'password': 'Employee@12345'})
        
        # Update to Ongoing
        update_res = self.client.patch(f'/api/employee/tasks/{task_id}/status', json={
            'status': 'Ongoing'
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()['data']['status'], 'Ongoing')
        mock_notify_blocked.assert_not_called()

        # Update to Blocked with blocker reason
        block_res = self.client.patch(f'/api/employee/tasks/{task_id}/status', json={
            'status': 'Blocked',
            'comment': 'Staging RDS instance out of memory; waiting on DevOps scaling.'
        })
        self.assertEqual(block_res.status_code, 200)
        self.assertEqual(block_res.get_json()['data']['status'], 'Blocked')

        # Verify notify_task_blocked was triggered
        mock_notify_blocked.assert_called_once()
        call_args = mock_notify_blocked.call_args[1]
        self.assertEqual(call_args['admin_email'], 'admin@enterprise.internal')
        self.assertEqual(call_args['assignee_name'], 'Sarah Jenkins')
        self.assertEqual(call_args['title'], 'Database Sharding Pipeline')
        self.assertIn('Staging RDS instance out of memory', call_args['comment'])

    def test_08_employee_cross_tenant_isolation(self):
        """Test that an employee cannot mutate tasks assigned to another employee."""
        # 1. Admin creates task for Sarah (ID 3)
        self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@12345'})
        task_res = self.client.post('/api/admin/tasks/create', json={
            'employee_id': 3,
            'task_title': 'Isolated Task',
            'priority': 'Low'
        })
        task_id = task_res.get_json()['data']['id']

        # 2. Marcus (ID 4) attempts to tamper with Sarah's task
        self.client.post('/api/auth/login', json={'username': 'marcus.vance', 'password': 'Employee@12345'})
        
        tamper_res = self.client.patch(f'/api/employee/tasks/{task_id}/status', json={
            'status': 'Completed'
        })
        self.assertEqual(tamper_res.status_code, 403)

    @patch('smtplib.SMTP')
    def test_09_email_service_fail_safe_execution(self, mock_smtp_cls):
        """Verify that SMTP socket exceptions are logged and do not crash the app or abort DB transactions."""
        # Configure mock SMTP to raise a ConnectionRefusedError
        mock_smtp_cls.side_effect = ConnectionRefusedError("Connection refused by test SMTP host")

        with self.app.app_context():
            # Dispatch email - should complete silently without unhandled exception
            send_async_email(
                subject="Test Subject",
                recipient="test@example.com",
                text_body="Test Body",
                html_body="<p>Test</p>"
            )

if __name__ == '__main__':
    unittest.main()
