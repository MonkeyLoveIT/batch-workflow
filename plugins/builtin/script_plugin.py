"""
Script execution plugin.
Executes shell scripts (Bash, Python, etc.) as tasks.
"""

import os
import subprocess
from typing import Any, Dict
import logging

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("script")
class ScriptPlugin(Plugin):
    """
    Plugin for executing scripts.

    Configuration:
        - script: Path to the script file (required)
        - interpreter: Interpreter to use (default: auto-detect from extension)
        - args: List of arguments to pass to the script
        - env: Dict of environment variables to set
        - cwd: Working directory for script execution
    """

    name = "script"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        if "script" not in config:
            logger.error("Script path is required")
            return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        script_path = context.get("script")
        if not script_path:
            return {"success": False, "error": "No script specified"}

        # Resolve path
        if not os.path.isabs(script_path):
            workflow_cwd = context.get("workflow_cwd", os.getcwd())
            script_path = os.path.join(workflow_cwd, script_path)

        if not os.path.exists(script_path):
            return {"success": False, "error": f"Script not found: {script_path}"}

        # Determine interpreter
        interpreter = context.get("interpreter")
        if not interpreter:
            ext = os.path.splitext(script_path)[1].lower()
            interpreter_map = {
                ".py": "python",
                ".sh": "bash",
                ".bash": "bash",
                ".zsh": "zsh",
            }
            interpreter = interpreter_map.get(ext, "bash")

        # Build command
        args = context.get("args", [])
        cmd = [interpreter, script_path] + args

        # Environment
        env = os.environ.copy()
        extra_env = context.get("env", {})
        env.update(extra_env)

        # Working directory
        cwd = context.get("cwd")

        logger.info(f"Executing script: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
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
            return {"success": False, "error": "Script timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
