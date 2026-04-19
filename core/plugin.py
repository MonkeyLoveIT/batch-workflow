"""
Plugin system for the workflow framework.
All tools (scripts, notifications, alerts) are abstracted as Plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class Plugin(ABC):
    """Base class for all plugins."""

    name: str
    version: str = "0.1.0"

    def __init__(self):
        self._initialized = False

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plugin with the given context.

        Args:
            context: Execution context containing configuration and shared state

        Returns:
            Dict containing execution result and any output values
        """
        pass

    def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate the plugin configuration.

        Args:
            config: Plugin configuration to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def on_start(self, context: Dict[str, Any]) -> None:
        """Called before execution starts."""
        pass

    def on_success(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Called after successful execution."""
        pass

    def on_failure(self, context: Dict[str, Any], error: Exception) -> None:
        """Called after failed execution."""
        pass

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the plugin with configuration.
        Called once before first execution.
        """
        self._initialized = True

    def cleanup(self) -> None:
        """Cleanup resources after all executions."""
        pass


class PluginRegistry:
    """Registry for managing plugins."""

    _plugins: ClassVar[Dict[str, "type"]] = {}

    @classmethod
    def register(cls, name: str, plugin_class: type) -> None:
        """Register a plugin class with a name."""
        if not issubclass(plugin_class, Plugin):
            raise TypeError(f"Plugin class must inherit from Plugin, got {plugin_class}")
        cls._plugins[name] = plugin_class
        logger.debug(f"Registered plugin: {name}")

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """Get a plugin class by name."""
        return cls._plugins.get(name)

    @classmethod
    def create(cls, name: str, **kwargs) -> Optional[Plugin]:
        """Create an instance of a plugin by name."""
        plugin_class = cls.get(name)
        if plugin_class is None:
            logger.error(f"Plugin not found: {name}")
            return None
        return plugin_class(**kwargs)

    @classmethod
    def list_plugins(cls) -> list:
        """List all registered plugin names."""
        return list(cls._plugins.keys())


def register_plugin(name: str) -> Callable:
    """
    Decorator to register a plugin class.

    Usage:
        @register_plugin("my_plugin")
        class MyPlugin(Plugin):
            ...
    """
    def decorator(cls: type) -> type:
        PluginRegistry.register(name, cls)
        return cls
    return decorator


def get_plugin(name: str) -> Optional[Plugin]:
    """Create and return a plugin instance by name."""
    return PluginRegistry.create(name)
