"""
Batch Workflow Framework
A lightweight workflow execution framework with plugin support.
"""

from core.plugin import Plugin, register_plugin, get_plugin
from core.scheduler import DAGScheduler
from core.engine import WorkflowEngine
from core.context import WorkflowContext

__all__ = [
    "Plugin",
    "register_plugin",
    "get_plugin",
    "DAGScheduler",
    "WorkflowEngine",
    "WorkflowContext",
]

__version__ = "0.1.0"
