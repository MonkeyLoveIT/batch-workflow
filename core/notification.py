"""
Notification manager for workflow events.
"""

from typing import Any, Dict, List, Optional
from enum import Enum
import logging

from core.plugin import Plugin, get_plugin

logger = logging.getLogger(__name__)


class NotificationEvent(Enum):
    """Events that can trigger notifications."""
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAILED = "workflow_failed"
    TASK_START = "task_start"
    TASK_SUCCESS = "task_success"
    TASK_FAILURE = "task_failure"
    TASK_RETRY = "task_retry"


class NotificationManager:
    """
    Manages notifications for workflow events.
    Supports multiple notification channels (plugins).
    """

    def __init__(self):
        self._handlers: Dict[NotificationEvent, List[Dict[str, Any]]] = {
            event: [] for event in NotificationEvent
        }

    def register_handler(
        self,
        event: NotificationEvent,
        plugin_name: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Register a notification handler for an event.

        Args:
            event: The event to handle
            plugin_name: Name of the notification plugin to use
            config: Configuration for the plugin
        """
        handler = {"plugin_name": plugin_name, "config": config}
        self._handlers[event].append(handler)
        logger.debug(f"Registered handler for {event}: {plugin_name}")

    def notify(
        self,
        event: NotificationEvent,
        context: Dict[str, Any]
    ) -> None:
        """
        Send notifications for an event.

        Args:
            event: The event that occurred
            context: Context containing event details
        """
        handlers = self._handlers.get(event, [])

        for handler in handlers:
            plugin_name = handler["plugin_name"]
            config = handler["config"]

            try:
                plugin = get_plugin(plugin_name)
                if plugin:
                    plugin.execute({**config, **context})
                else:
                    logger.warning(f"Notification plugin not found: {plugin_name}")
            except Exception as e:
                logger.error(f"Failed to send notification via {plugin_name}: {e}")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "NotificationManager":
        """
        Create a NotificationManager from configuration.

        Configuration format:
            notifications:
              - event: task_failure
                plugin: wechat_work
                config:
                  webhook_url: "https://..."
                  message: "Task {task_id} failed"
        """
        manager = cls()

        notifications = config.get("notifications", [])
        for notif_config in notifications:
            event_str = notif_config.get("event")
            plugin_name = notif_config.get("plugin")
            plugin_config = notif_config.get("config", {})

            if event_str and plugin_name:
                try:
                    event = NotificationEvent(event_str)
                    manager.register_handler(event, plugin_name, plugin_config)
                except ValueError:
                    logger.warning(f"Unknown notification event: {event_str}")

        return manager
