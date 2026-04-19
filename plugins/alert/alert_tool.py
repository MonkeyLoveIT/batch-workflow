"""
Alert tool plugin.
Integrates with existing alert/monitoring systems.
"""

from typing import Any, Dict, Optional
import logging

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("alert")
class AlertPlugin(Plugin):
    """
    Plugin for sending alerts to monitoring/alerting systems.

    This is a generic plugin that can be customized for specific alert backends:
    - Prometheus Alertmanager
    - Grafana OnCall
    - PagerDuty
    - Custom alert APIs

    Configuration:
        - type: Alert backend type (alertmanager, grafana, pagerduty, custom)
        - url: Alert API endpoint
        - level: Alert severity (info, warning, error, critical)
        - title: Alert title template
        - message: Alert message template
        - labels: Additional labels for the alert
        - headers: Custom HTTP headers
    """

    name = "alert"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        if "url" not in config:
            logger.error("Alert URL is required")
            return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        alert_url = context.get("url")
        alert_type = context.get("type", "custom")
        level = context.get("level", "info")
        title_template = context.get("title", "[{level}] {workflow_name}: {task_id}")
        message_template = context.get(
            "message",
            "Task {task_id} in workflow {workflow_name} requires attention.\nLevel: {level}\nDuration: {duration}s"
        )

        workflow_name = context.get("workflow_name", "workflow")
        task_id = context.get("task_id", "")
        duration = context.get("duration", 0)

        title = title_template.format(
            workflow_name=workflow_name,
            task_id=task_id,
            level=level.upper(),
        )

        message = message_template.format(
            workflow_name=workflow_name,
            task_id=task_id,
            level=level.upper(),
            duration=duration,
        )

        logger.info(f"Sending {level} alert: {title}")

        try:
            payload = self._build_payload(
                alert_type, title, message, level, context
            )
            return self._send_alert(alert_url, payload, context)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_payload(
        self,
        alert_type: str,
        title: str,
        message: str,
        level: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build alert payload based on alert type."""
        labels = context.get("labels", {})

        if alert_type == "alertmanager":
            return {
                "alerts": [{
                    "status": "firing" if level in ("error", "critical") else "resolved",
                    "labels": {
                        "alertname": title,
                        "severity": level,
                        **labels
                    },
                    "annotations": {
                        "summary": title,
                        "description": message,
                    }
                }]
            }

        elif alert_type == "grafana":
            return {
                "title": title,
                "message": message,
                "tags": [level],
            }

        elif alert_type == "pagerduty":
            return {
                "routing_key": context.get("routing_key"),
                "event_action": "trigger",
                "payload": {
                    "summary": message,
                    "severity": level,
                    "source": context.get("workflow_name", "workflow"),
                }
            }

        else:  # custom
            return {
                "title": title,
                "message": message,
                "level": level,
                "labels": labels,
            }

    def _send_alert(
        self,
        url: str,
        payload: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send alert to the specified URL."""
        import urllib.request
        import json

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        # Add custom headers
        headers = context.get("headers", {})
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                return {"success": True, "result": result}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"Failed to send alert: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
