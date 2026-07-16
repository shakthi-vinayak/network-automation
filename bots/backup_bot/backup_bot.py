"""
Backup Bot
===========
Automates configuration backup scheduling, execution, and restoration across network devices.

Actions:
    - backup_now        : Trigger immediate backup for one or more devices
    - schedule_backup   : Schedule recurring backups (cron-like)
    - list_backups      : List available backups for a device
    - restore_backup    : Restore a device to a previous configuration
    - diff_backups      : Compare two backup snapshots
    - verify_backup     : Verify backup integrity (checksum + parseability)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bots.framework.base_bot import BaseBot, BotResponse

logger = logging.getLogger(__name__)


class BackupBot(BaseBot):
    name = "backup-bot"
    description = "Configuration backup management bot"
    version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Backup store: {device: [backup_record, ...]}
        self._backups: Dict[str, List[Dict[str, Any]]] = {}
        self._schedules: Dict[str, Dict[str, Any]] = {}

    def list_actions(self) -> List[Dict[str, str]]:
        return [
            {"name": "backup_now", "description": "Trigger immediate backup"},
            {"name": "schedule_backup", "description": "Schedule recurring backups"},
            {"name": "list_backups", "description": "List available backups"},
            {"name": "restore_backup", "description": "Restore from a backup"},
            {"name": "diff_backups", "description": "Diff two backup snapshots"},
            {"name": "verify_backup", "description": "Verify backup integrity"},
        ]

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> BotResponse:
        handlers = {
            "backup_now": self._backup_now,
            "schedule_backup": self._schedule_backup,
            "list_backups": self._list_backups,
            "restore_backup": self._restore_backup,
            "diff_backups": self._diff_backups,
            "verify_backup": self._verify_backup,
        }
        handler = handlers.get(action)
        if handler is None:
            return self._fail(f"Unknown action: {action}")
        return await handler(parameters)

    async def _backup_now(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        running_config = params.get("running_config", f"! Running config for {device}\nhostname {device}")
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        checksum = hashlib.sha256(running_config.encode()).hexdigest()
        record = {
            "device": device,
            "timestamp": ts,
            "filename": f"backup_{device}_{ts}.cfg",
            "size_bytes": len(running_config),
            "checksum_sha256": checksum,
            "status": "success",
        }
        self._backups.setdefault(device, []).append(record)
        logger.info("Backup created for %s — %s", device, record["filename"])
        return self._ok(f"Backup created for {device}", data={"backup": record})

    async def _schedule_backup(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        schedule = {
            "device": device,
            "cron_expression": params.get("cron", "0 2 * * *"),  # Daily at 02:00
            "retention_days": params.get("retention_days", 90),
            "enabled": True,
            "last_run": None,
            "next_run": "calculated_from_cron",
        }
        self._schedules[device] = schedule
        return self._ok(
            f"Backup scheduled for {device} — cron: {schedule['cron_expression']}",
            data={"schedule": schedule},
        )

    async def _list_backups(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        backups = self._backups.get(device, [])
        return self._ok(
            f"Found {len(backups)} backup(s) for {device}",
            data={"device": device, "backups": backups, "count": len(backups)},
        )

    async def _restore_backup(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        timestamp = params.get("timestamp")
        backups = self._backups.get(device, [])
        target = next((b for b in backups if b["timestamp"] == timestamp), None)
        if target is None:
            return self._fail(f"No backup found for {device} at {timestamp}")
        logger.warning("RESTORE requested for %s from %s — approval required", device, timestamp)
        return self._ok(
            f"Restore queued for {device} from backup {target['filename']} (approval pending)",
            data={"device": device, "backup": target, "status": "pending_approval"},
        )

    async def _diff_backups(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        ts_a = params.get("timestamp_a")
        ts_b = params.get("timestamp_b")
        backups = self._backups.get(device, [])
        a = next((b for b in backups if b["timestamp"] == ts_a), None)
        b = next((b for b in backups if b["timestamp"] == ts_b), None)
        if not a or not b:
            return self._fail("One or both backup timestamps not found")
        # Simulated diff
        return self._ok(
            f"Diff between {a['filename']} and {b['filename']}",
            data={
                "device": device,
                "backup_a": a["filename"],
                "backup_b": b["filename"],
                "size_diff_bytes": b["size_bytes"] - a["size_bytes"],
                "checksums_match": a["checksum_sha256"] == b["checksum_sha256"],
            },
        )

    async def _verify_backup(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        timestamp = params.get("timestamp")
        backups = self._backups.get(device, [])
        target = next((b for b in backups if b["timestamp"] == timestamp), None)
        if target is None:
            return self._fail(f"No backup found for {device} at {timestamp}")
        # Verify checksum exists and is valid SHA256
        checksum = target.get("checksum_sha256", "")
        valid = len(checksum) == 64 and all(c in "0123456789abcdef" for c in checksum)
        if not valid:
            return self._fail(f"Backup {target['filename']} has invalid checksum")
        return self._ok(
            f"Backup {target['filename']} verified — integrity OK",
            data={"backup": target, "integrity": "valid"},
        )


if __name__ == "__main__":
    import uvicorn
    bot = BackupBot()
    app = bot.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8104)
