"""
WeChat Work (企业微信) notification plugin.
"""

from typing import Any, Dict
import logging
import urllib.request
import urllib.parse
import urllib.error
import json

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("wechat_work")
class WeChatWorkPlugin(Plugin):
    """
    Plugin for sending notifications via WeChat Work webhooks.

    Configuration:
        - webhook_url: WeChat Work webhook URL (required)
        - message: Message content (supports {task_id}, {workflow_name} placeholders)
        - mention_list: List of user IDs to mention
        - mention_phone_list: List of phone numbers to mention
    """

    name = "wechat_work"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        if "webhook_url" not in config:
            logger.error("WeChat Work webhook_url is required")
            return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        webhook_url = context.get("webhook_url")
        message_template = context.get("message", "{workflow_name}: {task_id} completed")

        # Format message with context
        workflow_name = context.get("workflow_name", "workflow")
        task_id = context.get("task_id", "")

        message = message_template.format(
            workflow_name=workflow_name,
            task_id=task_id,
        )

        # Build payload
        payload = {
            "msgtype": "text",
            "text": {
                "content": message,
                "mentioned_list": context.get("mention_list", []),
                "mentioned_phone_list": context.get("mention_phone_list", []),
            }
        }

        logger.info(f"Sending WeChat Work notification: {message[:50]}...")

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
