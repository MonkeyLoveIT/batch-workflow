"""
Command execution plugin.
Executes command-line tools as tasks.
"""

import subprocess
from typing import Any, Dict, List
import logging
import shlex

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("command")
class CommandPlugin(Plugin):
    """
    Plugin for executing command-line tools.

    Configuration:
        - cmd: Command to execute (string or list)
        - args: List of arguments (appended to cmd)
        - env: Dict of environment variables
        - cwd: Working directory
        - timeout: Execution timeout in seconds
    """

    name = "command"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        if "cmd" not in config:
            logger.error("Command is required")
            return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        cmd = context.get("cmd")
        if isinstance(cmd, str):
            cmd_list = shlex.split(cmd)
        else:
            cmd_list = list(cmd)

        args = context.get("args", [])
        cmd_list.extend(args)

        if not cmd_list:
            return {"success": False, "error": "Empty command"}

        # Environment
        env = None
        extra_env = context.get("env")
        if extra_env:
            import os
            env = os.environ.copy()
            env.update(extra_env)

        # Working directory
        cwd = context.get("cwd")

        logger.info(f"Executing command: {' '.join(cmd_list)}")

        try:
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                env=env,
                cwd=cwd,
                timeout=context.get("timeout", 3600)
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
