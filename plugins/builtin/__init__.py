"""
Built-in plugins for common operations.
"""

from plugins.builtin.script_plugin import ScriptPlugin
from plugins.builtin.command_plugin import CommandPlugin
from plugins.builtin.http_plugin import HTTPPlugin

__all__ = ["ScriptPlugin", "CommandPlugin", "HTTPPlugin"]
