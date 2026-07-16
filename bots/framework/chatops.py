"""
ChatOps Integration Layer
==========================
Adapters for Slack, Microsoft Teams, and generic webhook ChatOps integrations.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ChatOps command model
# ---------------------------------------------------------------------------
@dataclass
class ChatOpsCommand:
    """Parsed command from a ChatOps platform."""
    platform: str          # "slack" | "teams" | "webhook"
    channel: str
    user: str
    command: str           # e.g. "/firewall add-rule"
    args: List[str]
    raw_payload: Dict[str, Any]


# ---------------------------------------------------------------------------
# Abstract handler
# ---------------------------------------------------------------------------
class ChatOpsHandler(ABC):
    """Base class for platform-specific ChatOps handlers."""

    def __init__(self, signing_secret: str = ""):
        self.signing_secret = signing_secret
        self._commands: Dict[str, Callable] = {}

    def register_command(self, name: str, callback: Callable) -> None:
        self._commands[name] = callback

    @abstractmethod
    def parse_request(self, payload: Dict[str, Any]) -> ChatOpsCommand:
        ...

    @abstractmethod
    async def send_message(self, channel: str, text: str, **kwargs) -> None:
        ...

    def get_router(self) -> APIRouter:
        router = APIRouter()

        @router.post(f"/chatops/{self.__class__.__name__.lower()}")
        async def receive(request: Request):
            body = await request.json()
            if self.signing_secret and not self._verify_signature(body):
                raise HTTPException(status_code=403, detail="Invalid signature")
            cmd = self.parse_request(body)
            handler = self._commands.get(cmd.command)
            if handler is None:
                await self.send_message(cmd.channel, f"Unknown command: {cmd.command}")
                return {"status": "ignored"}
            result = await handler(cmd)
            await self.send_message(cmd.channel, str(result))
            return {"status": "ok"}

        return router

    def _verify_signature(self, body: Dict[str, Any]) -> bool:
        return True  # Override in subclass


# ---------------------------------------------------------------------------
# Slack handler
# ---------------------------------------------------------------------------
class SlackHandler(ChatOpsHandler):
    """Slack Events / Slash-command adapter."""

    def __init__(self, signing_secret: str = "", bot_token: str = ""):
        super().__init__(signing_secret)
        self.bot_token = bot_token
        self.api_url = "https://slack.com/api/chat.postMessage"

    def parse_request(self, payload: Dict[str, Any]) -> ChatOpsCommand:
        text = payload.get("text", "")
        parts = text.split()
        command = parts[0] if parts else ""
        return ChatOpsCommand(
            platform="slack",
            channel=payload.get("channel_id", ""),
            user=payload.get("user_id", ""),
            command=command,
            args=parts[1:],
            raw_payload=payload,
        )

    async def send_message(self, channel: str, text: str, **kwargs) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json={"channel": channel, "text": text},
            )

    def _verify_signature(self, body: Dict[str, Any]) -> bool:
        raw = str(body).encode()
        sig = hmac.new(self.signing_secret.encode(), raw, hashlib.sha256).hexdigest()
        return body.get("signature", "") == sig


# ---------------------------------------------------------------------------
# Teams handler
# ---------------------------------------------------------------------------
class TeamsHandler(ChatOpsHandler):
    """Microsoft Teams Bot Framework adapter."""

    def __init__(self, app_id: str = "", app_password: str = ""):
        super().__init__()
        self.app_id = app_id
        self.app_password = app_password

    def parse_request(self, payload: Dict[str, Any]) -> ChatOpsCommand:
        text = payload.get("text", "")
        parts = text.split()
        command = parts[0] if parts else ""
        return ChatOpsCommand(
            platform="teams",
            channel=payload.get("conversation", {}).get("id", ""),
            user=payload.get("from", {}).get("id", ""),
            command=command,
            args=parts[1:],
            raw_payload=payload,
        )

    async def send_message(self, channel: str, text: str, **kwargs) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://smba.trafficmanager.net/amer/v3/conversations/{channel}/activities",
                headers={"Authorization": f"Bearer {self.app_password}"},
                json={"type": "message", "text": text},
            )


# ---------------------------------------------------------------------------
# Router aggregator
# ---------------------------------------------------------------------------
class ChatOpsRouter:
    """Aggregates multiple ChatOps handlers into a single APIRouter."""

    def __init__(self):
        self._handlers: List[ChatOpsHandler] = []

    def add_handler(self, handler: ChatOpsHandler) -> None:
        self._handlers.append(handler)

    def get_router(self) -> APIRouter:
        router = APIRouter(tags=["chatops"])
        for handler in self._handlers:
            router.include_router(handler.get_router())
        return router
