"""
Notification plugins.
"""

from plugins.notification.wechat_work import WeChatWorkPlugin
from plugins.notification.dingtalk import DingTalkPlugin
from plugins.notification.email import EmailPlugin
from plugins.notification.push_wxchat import PushWxchatPlugin

__all__ = ["WeChatWorkPlugin", "DingTalkPlugin", "EmailPlugin", "PushWxchatPlugin"]
