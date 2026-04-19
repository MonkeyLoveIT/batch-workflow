"""
Exec Flow Plugin

Wraps the existing exec_flow tool from /path/to/tools/exec_flow.py

Configuration:
    - params: Parameters to pass to exec()
    - Any other fields will be passed as keyword arguments
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


@register_plugin("exec_flow")
class ExecFlowPlugin(Plugin):
    """
    Plugin for executing tasks via the existing exec_flow system.
    """

    name = "exec_flow"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        # params is optional, can pass any config fields
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from exec_flow import exec

        params = context.get("params", {})

        # Also pass workflow context info
        exec_params = {
            **params,
            "workflow_name": context.get("workflow_name"),
            "task_id": context.get("task_id"),
        }

        logger.info(f"Executing flow: {exec_params}")

        try:
            result = exec(exec_params)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
