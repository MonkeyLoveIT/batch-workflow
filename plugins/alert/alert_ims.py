"""
Alert IMS Plugin

Wraps the existing alert_ims tool from /path/to/tools/alert_ims.py

Configuration:
    - subsys_id: Subsystem ID
    - title: Alert title
    - content: Alert content
    - level: Alert level (info, warning, error, critical)
    - receiver: Receiver user ID
    - alert_way: Alert way (e.g., wechat, sms, email)
"""

import sys
import os
from typing import Any, Dict

# Add tools directory to path if needed
TOOLS_DIR = os.environ.get("TOOLS_DIR", "/Users/eddy/tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from core.plugin import Plugin, register_plugin

logger = logger = __import__('logging').getLogger(__name__)


@register_plugin("alert_ims")
class AlertImsPlugin(Plugin):
    """
    Plugin for sending alerts via the existing alert_ims system.
    """

    name = "alert_ims"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        required = ["subsys_id", "title", "content", "level", "receiver"]
        for field in required:
            if field not in config:
                logger.error(f"Missing required field: {field}")
                return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from alert_ims import send_ims

        subsys_id = context.get("subsys_id")
        title = context.get("title", "").format(
            workflow_name=context.get("workflow_name", ""),
            task_id=context.get("task_id", ""),
        )
        content = context.get("content", "").format(
            workflow_name=context.get("workflow_name", ""),
            task_id=context.get("task_id", ""),
            error=context.get("error", ""),
        )
        level = context.get("level", "info")
        receiver = context.get("receiver")
        alert_way = context.get("alert_way", "wechat")

        logger.info(f"Sending IMS alert: [{level}] {title}")

        try:
            send_ims(
                subsys_id=subsys_id,
                title=title,
                content=content,
                level=level,
                reciver=receiver,
                alert_way=alert_way
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
