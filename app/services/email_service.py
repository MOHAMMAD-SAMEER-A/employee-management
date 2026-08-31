import logging
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from flask import current_app

logger = logging.getLogger(__name__)

# Dedicated background worker pool for zero-infrastructure async email delivery
_executor = ThreadPoolExecutor(max_workers=4)

def _dispatch_email_worker(app, subject, recipient, text_body, html_body):
    """Background worker executing SMTP dispatch within an application context."""
    with app.app_context():
        try:
            smtp_server = app.config.get('SMTP_SERVER', 'localhost')
            smtp_port = int(app.config.get('SMTP_PORT', 587))
            smtp_use_tls = app.config.get('SMTP_USE_TLS', True)
            smtp_username = app.config.get('SMTP_USERNAME', '')
            smtp_password = app.config.get('SMTP_PASSWORD', '')
            default_sender = app.config.get('MAIL_DEFAULT_SENDER', 'TaskCorp Alerts <notifications@enterprise.internal>')

            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = default_sender
            msg['To'] = recipient
            msg.set_content(text_body)

            if html_body:
                msg.add_alternative(html_body, subtype='html')

            # Connect to SMTP server
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            
            # Identify client
            server.ehlo()

            # Upgrade to secure TLS if requested and supported
            if smtp_use_tls and smtp_port != 1025:  # Skip TLS if local debug server doesn't support it
                try:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                except Exception as tls_err:
                    logger.warning("SMTP STARTTLS skipped or not supported: %s", tls_err)

            # Authenticate if credentials are provided
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            server.send_message(msg)
            server.quit()
            logger.info("Asynchronous email dispatched successfully to: %s [Subject: %s]", recipient, subject)

        except Exception as exc:
            # Fail-safe: Log error without disrupting primary transaction
            logger.error("Failed to deliver asynchronous email to %s: %s", recipient, exc, exc_info=True)

def send_async_email(subject, recipient, text_body, html_body=None):
    """Dispatch email delivery asynchronously to the ThreadPoolExecutor."""
    try:
        # Capture raw Flask application object for thread safety
        app = current_app._get_current_object()
        _executor.submit(_dispatch_email_worker, app, subject, recipient, text_body, html_body)
    except Exception as exc:
        logger.error("Failed to submit async email job to executor: %s", exc)

def notify_task_dispatched(recipient_email, assignee_name, title, priority, due_date=None):
    """Send an asynchronous notification to an employee upon new task allocation."""
    subject = f"📋 New Task Assigned: {title} [{priority} Priority]"
    formatted_due = due_date if due_date else "Flexible / None specified"

    # Plain text version fallback
    text_body = f"""Hello {assignee_name},

A new operational task has been dispatched to your queue:

Title: {title}
Priority: {priority}
Due Date: {formatted_due}

Please sign in to the Enterprise Portal to review the scope and update your progress status.

--
Enterprise Core Management System
"""

    # Priority badge styling
    priority_colors = {
        'Urgent': {'bg': '#f43f5e', 'text': '#ffffff', 'badge': '#ffe4e6', 'label': '#be123c'},
        'High': {'bg': '#f59e0b', 'text': '#ffffff', 'badge': '#fef3c7', 'label': '#b45309'},
        'Medium': {'bg': '#6366f1', 'text': '#ffffff', 'badge': '#e0e7ff', 'label': '#4338ca'},
        'Low': {'bg': '#64748b', 'text': '#ffffff', 'badge': '#f1f5f9', 'label': '#334155'}
    }
    p_style = priority_colors.get(priority, priority_colors['Medium'])

    # Modern Dark Slate HTML Template
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>New Task Assignment</title>
</head>
<body style="margin: 0; padding: 0; background-color: #020617; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #020617; padding: 32px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" max-width="580px" cellspacing="0" cellpadding="0" border="0" style="max-width: 580px; background-color: #0f172a; border-radius: 16px; border: 1px solid #334155; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 24px 32px; border-bottom: 1px solid #3730a3;">
                            <table width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td>
                                        <span style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: #818cf8;">Task Dispatch Alert</span>
                                        <h1 style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #ffffff;">New Task Assigned</h1>
                                    </td>
                                    <td align="right">
                                        <span style="display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; background-color: {p_style['bg']}; color: {p_style['text']}; text-transform: uppercase;">
                                            {priority} Priority
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 32px;">
                            <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.6; color: #cbd5e1;">
                                Hello <strong style="color: #ffffff;">{assignee_name}</strong>,
                            </p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #94a3b8;">
                                An administrator has allocated a new work order to your active queue.
                            </p>

                            <!-- Task Card -->
                            <table width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #94a3b8; margin-bottom: 4px;">Task Title</div>
                                        <div style="font-size: 16px; font-weight: 700; color: #f8fafc; margin-bottom: 16px;">{title}</div>

                                        <table width="100%" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td width="50%">
                                                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #94a3b8;">Priority</div>
                                                    <div style="font-size: 13px; font-weight: 600; color: #cbd5e1; margin-top: 2px;">{priority}</div>
                                                </td>
                                                <td width="50%">
                                                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #94a3b8;">Target Due Date</div>
                                                    <div style="font-size: 13px; font-weight: 600; color: #cbd5e1; margin-top: 2px; font-family: monospace;">{formatted_due}</div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 24px 0; font-size: 13px; line-height: 1.6; color: #94a3b8;">
                                Please sign in to your workspace to examine instructions, update progress status, or report roadblocks.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #020617; padding: 20px 32px; border-top: 1px solid #1e293b; text-align: center;">
                            <p style="margin: 0; font-size: 11px; color: #64748b;">
                                Enterprise Core Management System &bull; Automated Task Allocation Dispatcher
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    send_async_email(subject, recipient_email, text_body, html_body)

def notify_task_blocked(admin_email, admin_username, assignee_name, title, comment=None):
    """Send an immediate blocker escalation alert to the task creator / administrator."""
    subject = f"🚨 URGENT BLOCKER: {title} marked as Blocked by {assignee_name}"
    comment_text = comment if comment else "No additional commentary provided."

    # Plain text version fallback
    text_body = f"""Attention Administrator (@{admin_username}),

Task Escalation Alert:
An assigned employee has flagged a roadblock and marked the following task as BLOCKED:

Task: {title}
Assignee: {assignee_name}
Blocker Details: {comment_text}

Immediate intervention or resource reallocation may be required.

--
Enterprise Core Management System
"""

    # High-contrast Dark Slate Blocker HTML Template
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Urgent Blocker Escalation</title>
</head>
<body style="margin: 0; padding: 0; background-color: #020617; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #020617; padding: 32px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" max-width="580px" cellspacing="0" cellpadding="0" border="0" style="max-width: 580px; background-color: #0f172a; border-radius: 16px; border: 1px solid #881337; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(244, 63, 94, 0.2);">
                    
                    <!-- Header with Glowing Rose Alert -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #881337 0%, #4c0519 100%); padding: 24px 32px; border-bottom: 1px solid #f43f5e;">
                            <table width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; background-color: #ffe4e6; color: #9f1239; margin-bottom: 6px;">
                                            🚨 Blocker Escalation
                                        </span>
                                        <h1 style="margin: 0; font-size: 19px; font-weight: 700; color: #ffffff;">Operational Roadblock Reported</h1>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 32px;">
                            <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                                Attention <strong style="color: #ffffff;">@{admin_username}</strong>,
                            </p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #fda4af;">
                                <strong style="color: #ffffff;">{assignee_name}</strong> has encountered a critical impediment and transitioned a work order to <span style="background-color: #4c0519; color: #f43f5e; padding: 2px 6px; border-radius: 4px; font-weight: 700;">BLOCKED</span> status.
                            </p>

                            <!-- Roadblock Details Card -->
                            <table width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #1e293b; border-radius: 12px; border: 1px solid #475569; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #94a3b8; margin-bottom: 4px;">Impacted Task</div>
                                        <div style="font-size: 16px; font-weight: 700; color: #f8fafc; margin-bottom: 16px;">{title}</div>

                                        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #94a3b8; margin-bottom: 4px;">Assignee</div>
                                        <div style="font-size: 13px; font-weight: 600; color: #cbd5e1; margin-bottom: 16px;">{assignee_name}</div>

                                        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #f43f5e; margin-bottom: 6px;">Reported Impediment / Comment</div>
                                        <div style="background-color: #020617; border-left: 3px solid #f43f5e; padding: 12px 16px; border-radius: 0 8px 8px 0; font-size: 13px; color: #e2e8f0; line-height: 1.5; font-style: italic;">
                                            "{comment_text}"
                                        </div>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 8px 0; font-size: 13px; line-height: 1.6; color: #94a3b8;">
                                Please review the task in the Admin Operations Dashboard to resolve dependency issues or reassign workflow items.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #020617; padding: 20px 32px; border-top: 1px solid #1e293b; text-align: center;">
                            <p style="margin: 0; font-size: 11px; color: #64748b;">
                                Enterprise Core Management System &bull; Executive Incident Notification
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    send_async_email(subject, admin_email, text_body, html_body)
