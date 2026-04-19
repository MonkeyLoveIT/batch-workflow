"""
Custom Notification Plugin

Calls a custom notification API to send alerts/messages.
Supports internal notification systems like WeChat Work, DingTalk, etc.

Configuration:
    - api_url: The notification API endpoint (required)
    - method: HTTP method (default: POST)
    - headers: HTTP headers (e.g., Authorization)
    - body_template: Template for request body (supports {task_id}, {workflow_name}, etc.)
    - targets: List of targets to notify (user IDs, phone numbers, etc.)
    - target_field: Field name for targets in the request body (default: "user_ids")
"""

import logging
import urllib.request
import urllib.parse
import urllib.error
import json

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("custom_notify")
class CustomNotifyPlugin(Plugin):
    """
    Generic notification plugin for custom APIs.

    Supports any notification service that has an HTTP API.
    """

    name = "custom_notify"
    version = "0.1.0"

    def validate(self, config):
        if "api_url" not in config:
            logger.error("api_url is required for custom_notify plugin")
            return False
        return True

    def execute(self, context):
        api_url = context.get("api_url")
        method = context.get("method", "POST").upper()
        headers = context.get("headers", {})
        body_template = context.get("body_template", "{workflow_name}: {task_id} - {status}")
        targets = context.get("targets", [])
        target_field = context.get("target_field", "user_ids")

        # Build message from template
        workflow_name = context.get("workflow_name", "workflow")
        task_id = context.get("task_id", "")
        status = context.get("status", "unknown")
        error = context.get("error", "")
        duration = context.get("duration", 0)

        message = body_template.format(
            workflow_name=workflow_name,
            task_id=task_id,
            status=status,
            error=error,
            duration=duration,
        )

        # Build request body
        body = {
            "message": message,
            target_field: targets,
            "extra": {
                "workflow_name": workflow_name,
                "task_id": task_id,
                "status": status,
                "duration": duration,
            }
        }

        # Add any additional context fields
        for key, value in context.items():
            if key not in body and key not in ("api_url", "method", "headers", "body_template", "targets", "target_field"):
                body["extra"][key] = value

        logger.info(f"Sending notification via {api_url}: {message[:50]}...")

        try:
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(api_url, data=data, method=method)

            for key, value in headers.items():
                req.add_header(key, value)

            if "Content-Type" not in headers:
                req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=context.get("timeout", 30)) as response:
                response_body = response.read().decode("utf-8")
                return {
                    "success": True,
                    "status_code": response.status,
                    "response": response_body,
                }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else None
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "status_code": e.code,
                "response": error_body,
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"URL error: {e.reason}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
