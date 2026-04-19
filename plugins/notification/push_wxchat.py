"""
Push WeChat Plugin

Wraps the existing push_msg tool from /path/to/tools/push_msg.py

Configuration:
    - content: Message content
    - group: Group to send to (either group or user required)
    - user: User to send to (either group or user required)
    - dclear: Whether to clear previous messages (default: True)
    - service_name: Service name prefix
    - at_list: List of users to @mention
"""

import sys
import os
from typing import Any, Dict

# Add tools directory to path if needed
TOOLS_DIR = os.environ.get("TOOLS_DIR", "/Users/eddy/tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from core.plugin import Plugin, register_plugin

logger = __import__('logging').getLogger(__name__)


@register_plugin("push_wxchat")
class PushWxchatPlugin(Plugin):
    """
    Plugin for sending WeChat messages via the existing push_msg system.
    """

    name = "push_wxchat"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        if not config.get("group") and not config.get("user"):
            logger.error("Either 'group' or 'user' is required")
            return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from push_msg import push_wxchat

        # Build message from template
        content_template = context.get("content", "{workflow_name}: {task_id} - {status}")
        content = content_template.format(
            workflow_name=context.get("workflow_name", "workflow"),
            task_id=context.get("task_id", ""),
            status=context.get("status", ""),
            error=context.get("error", ""),
            duration=context.get("duration", 0),
        )

        group = context.get("group")
        user = context.get("user")
        dclear = context.get("dclear", True)
        service_name = context.get("service_name", context.get("workflow_name", "workflow"))
        at_list = context.get("at_list", "")

        logger.info(f"Pushing WeChat message to {group or user}: {content[:50]}...")

        try:
            push_wxchat(
                content=content,
                group=group,
                user=user,
                dclear=dclear,
                service_name=service_name,
                at_list=at_list
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
