"""
DingTalk (钉钉) notification plugin.
"""

from typing import Any, Dict
import logging
import urllib.request
import urllib.parse
import urllib.error
import json

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("dingtalk")
class DingTalkPlugin(Plugin):
    """
    Plugin for sending notifications via DingTalk webhooks.

    Configuration:
        - webhook_url: DingTalk webhook URL (required)
        - message: Message content
        - secret: DingTalk robot secret (for signature)
    """

    name = "dingtalk"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        if "webhook_url" not in config:
            logger.error("DingTalk webhook_url is required")
            return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        webhook_url = context.get("webhook_url")
        message = context.get("message", "{workflow_name}: {task_id} completed")

        # Format message
        workflow_name = context.get("workflow_name", "workflow")
        task_id = context.get("task_id", "")

        message = message.format(
            workflow_name=workflow_name,
            task_id=task_id,
        )

        payload = {
            "msgtype": "text",
            "text": {
                "content": message,
            }
        }

        logger.info(f"Sending DingTalk notification: {message[:50]}...")

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                method="POST"
            )
            req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))

                if result.get("errcode") == 0:
                    return {"success": True, "result": result}
                else:
                    return {
                        "success": False,
                        "error": result.get("errmsg", "Unknown error"),
                    }

        except urllib.error.URLError as e:
            return {"success": False, "error": f"Failed to send: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
