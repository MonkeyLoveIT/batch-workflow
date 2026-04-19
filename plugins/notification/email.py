"""
Email notification plugin.
"""

from typing import Any, Dict, List, Optional
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("email")
class EmailPlugin(Plugin):
    """
    Plugin for sending email notifications.

    Configuration:
        - smtp_host: SMTP server hostname (required)
        - smtp_port: SMTP server port (default: 587)
        - smtp_user: SMTP username (required)
        - smtp_password: SMTP password (required)
        - from_addr: Sender email address (required)
        - to_addrs: Recipient email addresses (required, list or string)
        - subject: Email subject template
        - use_tls: Whether to use TLS (default: True)
    """

    name = "email"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        required = ["smtp_host", "smtp_user", "smtp_password", "from_addr", "to_addrs"]
        for field in required:
            if field not in config:
                logger.error(f"Email config field '{field}' is required")
                return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        smtp_host = context.get("smtp_host")
        smtp_port = context.get("smtp_port", 587)
        smtp_user = context.get("smtp_user")
        smtp_password = context.get("smtp_password")
        from_addr = context.get("from_addr")
        to_addrs = context.get("to_addrs")

        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]

        subject_template = context.get("subject", "[{workflow_name}] {task_id} notification")
        body_template = context.get(
            "body",
            "Workflow: {workflow_name}\nTask: {task_id}\nStatus: {status}\nDuration: {duration}s"
        )

        workflow_name = context.get("workflow_name", "workflow")
        task_id = context.get("task_id", "")
        status = context.get("status", "unknown")
        duration = context.get("duration", 0)

        subject = subject_template.format(
            workflow_name=workflow_name,
            task_id=task_id,
            status=status,
        )

        body = body_template.format(
            workflow_name=workflow_name,
            task_id=task_id,
            status=status,
            duration=duration,
        )

        logger.info(f"Sending email to {to_addrs}: {subject}")

        try:
            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = ", ".join(to_addrs)
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                if context.get("use_tls", True):
                    server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}
