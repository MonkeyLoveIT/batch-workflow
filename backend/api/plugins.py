"""
Plugin API endpoints.
"""

from fastapi import APIRouter
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import plugins
from core.plugin import PluginRegistry

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# Plugin categories
TASK_PLUGINS = ['command', 'script', 'http', 'exec_flow']
NOTIFICATION_PLUGINS = ['wechat_work', 'dingtalk', 'email', 'push_wxchat', 'custom_notify']
ALERT_PLUGINS = ['alert', 'alert_ims']


@router.get("/types", response_model=dict)
def get_plugin_types():
    """Get all available plugin types grouped by category."""
    all_plugins = PluginRegistry.list_plugins()

    return {
        "task": [
            {"value": p, "label": _get_plugin_label(p)}
            for p in all_plugins if p in TASK_PLUGINS
        ],
        "notification": [
            {"value": p, "label": _get_plugin_label(p)}
            for p in all_plugins if p in NOTIFICATION_PLUGINS
        ],
        "alert": [
            {"value": p, "label": _get_plugin_label(p)}
            for p in all_plugins if p in ALERT_PLUGINS
        ],
        "all": [
            {"value": p, "label": _get_plugin_label(p)}
            for p in all_plugins
        ]
    }


@router.get("/list", response_model=list)
def list_all_plugins():
    """Get list of all available plugin names."""
    return PluginRegistry.list_plugins()


def _get_plugin_label(name: str) -> str:
    """Convert plugin name to display label."""
    labels = {
        "command": "命令行",
        "script": "脚本",
        "http": "HTTP请求",
        "exec_flow": "执行任务",
        "wechat_work": "企业微信",
        "dingtalk": "钉钉",
        "email": "邮件",
        "push_wxchat": "微信推送",
        "custom_notify": "自定义通知",
        "alert": "告警",
        "alert_ims": "IMS告警",
    }
    return labels.get(name, name)
