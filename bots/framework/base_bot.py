"""
Base Bot Framework
===================
Abstract base class and shared types for all network automation bots.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Status & response types
# ---------------------------------------------------------------------------
class BotStatus(str, Enum):
    """Operational status for a bot."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BotResponse:
    """Standardised response returned by every bot action."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: BotStatus = BotStatus.IDLE
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "message": self.message,
            "data": self.data or {},
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------
class BotActionRequest(BaseModel):
    """Generic action request body."""
    action: str
    parameters: Dict[str, Any] = {}
    requester: str = "anonymous"
    ticket_id: Optional[str] = None


class BotActionResponse(BaseModel):
    """Generic action response body."""
    request_id: str
    status: str
    message: str
    data: Dict[str, Any] = {}
    timestamp: str


# ---------------------------------------------------------------------------
# BaseBot abstract class
# ---------------------------------------------------------------------------
class BaseBot:
    """
    Abstract base class for network automation bots.

    Subclasses must implement:
        - ``execute_action(action, parameters)`` — run the requested action.
        - ``list_actions()`` — return supported actions.

    Usage::

        class MyBot(BaseBot):
            name = "my-bot"

            async def execute_action(self, action, parameters):
                ...

        bot = MyBot()
        app = bot.create_app()
    """

    name: str = "base-bot"
    description: str = "Network Automation Bot"
    version: str = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.status: BotStatus = BotStatus.IDLE
        self._history: List[BotResponse] = []
        self._router = APIRouter(prefix=f"/api/v1/{self.name}", tags=[self.name])
        self._setup_routes()

    # -- abstract methods ---------------------------------------------------
    async def execute_action(
        self, action: str, parameters: Dict[str, Any]
    ) -> BotResponse:
        raise NotImplementedError("Subclasses must implement execute_action()")

    def list_actions(self) -> List[Dict[str, str]]:
        raise NotImplementedError("Subclasses must implement list_actions()")

    # -- FastAPI app --------------------------------------------------------
    def _setup_routes(self) -> None:
        @self._router.get("/health")
        async def health():
            return {"bot": self.name, "status": self.status.value, "version": self.version}

        @self._router.get("/actions")
        async def actions():
            return {"bot": self.name, "actions": self.list_actions()}

        @self._router.post("/execute", response_model=BotActionResponse)
        async def execute(request: BotActionRequest):
            self.status = BotStatus.RUNNING
            try:
                result = await self.execute_action(request.action, request.parameters)
                self._history.append(result)
                self.status = BotStatus.SUCCESS if result.status == BotStatus.SUCCESS else BotStatus.FAILED
                return BotActionResponse(**result.to_dict())
            except Exception as exc:
                self.status = BotStatus.FAILED
                logger.exception("Action '%s' failed", request.action)
                raise HTTPException(status_code=500, detail=str(exc))

        @self._router.get("/history")
        async def history(limit: int = 50):
            entries = self._history[-limit:]
            return {"bot": self.name, "count": len(entries), "entries": [e.to_dict() for e in entries]}

    def create_app(self) -> FastAPI:
        app = FastAPI(
            title=f"{self.name} — Network Automation Bot",
            description=self.description,
            version=self.version,
        )
        app.include_router(self._router)
        return app

    # -- helpers ------------------------------------------------------------
    def _ok(self, message: str, data: Optional[Dict] = None) -> BotResponse:
        return BotResponse(status=BotStatus.SUCCESS, message=message, data=data)

    def _fail(self, message: str, data: Optional[Dict] = None) -> BotResponse:
        return BotResponse(status=BotStatus.FAILED, message=message, data=data)
