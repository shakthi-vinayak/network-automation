"""
Network Automation Bot Framework
=================================
Base framework for building network automation bots with FastAPI and ChatOps support.
"""

from bots.framework.base_bot import BaseBot, BotStatus, BotResponse
from bots.framework.chatops import ChatOpsRouter, SlackHandler, TeamsHandler

__all__ = [
    "BaseBot",
    "BotStatus",
    "BotResponse",
    "ChatOpsRouter",
    "SlackHandler",
    "TeamsHandler",
]
