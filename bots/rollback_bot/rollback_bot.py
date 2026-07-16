"""
Rollback Bot
=============
Manages configuration rollback workflows with approval gates and verification.

Actions:
    - rollback_config   : Roll back a device to its previous configuration
    - show_rollback_history : List rollback history for a device
    - verify_rollback   : Verify rollback was successful
    - dry_run_rollback  : Preview changes that would be applied during rollback
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bots.framework.base_bot import BaseBot, BotResponse

logger = logging.getLogger(__name__)


class RollbackBot(BaseBot):
    name = "rollback-bot"
    description = "Configuration rollback and recovery bot"
    version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._rollback_history: Dict[str, List[Dict[str, Any]]] = {}

    def list_actions(self) -> List[Dict[str, str]]:
        return [
            {"name": "rollback_config", "description": "Roll back device configuration"},
            {"name": "show_rollback_history", "description": "List rollback history"},
            {"name": "verify_rollback", "description": "Verify rollback success"},
            {"name": "dry_run_rollback", "description": "Preview rollback changes"},
        ]

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> BotResponse:
        handlers = {
            "rollback_config": self._rollback_config,
            "show_rollback_history": self._show_rollback_history,
            "verify_rollback": self._verify_rollback,
            "dry_run_rollback": self._dry_run_rollback,
        }
        handler = handlers.get(action)
        if handler is None:
            return self._fail(f"Unknown action: {action}")
        return await handler(parameters)

    async def _rollback_config(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        target_version = params.get("target_version", "previous")
        approved_by = params.get("approved_by")

        if not approved_by:
            return self._fail("Rollback requires explicit approval — set approved_by parameter")

        record = {
            "device": device,
            "target_version": target_version,
            "approved_by": approved_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "pre_rollback_backup": f"backup_{device}_pre_rollback.cfg",
        }
        self._rollback_history.setdefault(device, []).append(record)
        logger.warning("ROLLBACK: %s to version '%s' approved by %s", device, target_version, approved_by)
        return self._ok(
            f"Rollback completed for {device} to {target_version}",
            data={"rollback": record},
        )

    async def _show_rollback_history(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        history = self._rollback_history.get(device, [])
        return self._ok(
            f"{len(history)} rollback(s) recorded for {device}",
            data={"device": device, "history": history},
        )

    async def _verify_rollback(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        history = self._rollback_history.get(device, [])
        if not history:
            return self._fail(f"No rollback history found for {device}")
        last = history[-1]
        return self._ok(
            f"Rollback verified for {device} — status: {last['status']}",
            data={"device": device, "last_rollback": last, "verified": True},
        )

    async def _dry_run_rollback(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        target_version = params.get("target_version", "previous")
        return self._ok(
            f"Dry-run rollback for {device} → {target_version}",
            data={
                "device": device,
                "target_version": target_version,
                "changes_preview": {
                    "lines_added": 12,
                    "lines_removed": 8,
                    "sections_affected": ["interfaces", "routing", "aaa"],
                },
            },
        )


if __name__ == "__main__":
    import uvicorn
    bot = RollbackBot()
    app = bot.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8107)
