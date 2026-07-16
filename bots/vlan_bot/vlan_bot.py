"""
VLAN Bot
=========
Automates VLAN provisioning, modification, and decommissioning across multi-vendor switches.

Actions:
    - create_vlan       : Provision a new VLAN on target switches
    - modify_vlan       : Update VLAN name or description
    - delete_vlan       : Decommission a VLAN (with safety checks)
    - list_vlans        : List VLANs on a device
    - assign_port       : Assign a switchport to a VLAN
    - audit_vlans       : Audit VLAN consistency across the fabric
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from bots.framework.base_bot import BaseBot, BotResponse, BotStatus

logger = logging.getLogger(__name__)

# Reserved VLAN ranges
RESERVED_VLANS = list(range(1, 10)) + list(range(1002, 1006))
VLAN_RANGE_MIN = 10
VLAN_RANGE_MAX = 4094


class VlanBot(BaseBot):
    name = "vlan-bot"
    description = "VLAN lifecycle management bot"
    version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # In-memory VLAN DB: {device: {vlan_id: {...}}}
        self._vlan_db: Dict[str, Dict[int, Dict[str, Any]]] = {}

    def list_actions(self) -> List[Dict[str, str]]:
        return [
            {"name": "create_vlan", "description": "Create a new VLAN on a device"},
            {"name": "modify_vlan", "description": "Modify VLAN name/description"},
            {"name": "delete_vlan", "description": "Decommission a VLAN"},
            {"name": "list_vlans", "description": "List all VLANs on a device"},
            {"name": "assign_port", "description": "Assign a port to a VLAN"},
            {"name": "audit_vlans", "description": "Audit VLAN consistency across devices"},
        ]

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> BotResponse:
        handlers = {
            "create_vlan": self._create_vlan,
            "modify_vlan": self._modify_vlan,
            "delete_vlan": self._delete_vlan,
            "list_vlans": self._list_vlans,
            "assign_port": self._assign_port,
            "audit_vlans": self._audit_vlans,
        }
        handler = handlers.get(action)
        if handler is None:
            return self._fail(f"Unknown action: {action}")
        return await handler(parameters)

    async def _create_vlan(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        vlan_id = params.get("vlan_id")
        name = params.get("name", f"VLAN{vlan_id}")
        description = params.get("description", "")

        if vlan_id in RESERVED_VLANS:
            return self._fail(f"VLAN {vlan_id} is reserved and cannot be provisioned")
        if not (VLAN_RANGE_MIN <= vlan_id <= VLAN_RANGE_MAX):
            return self._fail(f"VLAN ID must be between {VLAN_RANGE_MIN} and {VLAN_RANGE_MAX}")

        device_vlans = self._vlan_db.setdefault(device, {})
        if vlan_id in device_vlans:
            return self._fail(f"VLAN {vlan_id} already exists on {device}")

        vlan = {
            "vlan_id": vlan_id,
            "name": name,
            "description": description,
            "state": "active",
            "shutdown": False,
        }
        device_vlans[vlan_id] = vlan
        logger.info("Created VLAN %d (%s) on %s", vlan_id, name, device)
        return self._ok(f"VLAN {vlan_id} ({name}) created on {device}", data={"vlan": vlan})

    async def _modify_vlan(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        vlan_id = params.get("vlan_id")
        vlan = self._vlan_db.get(device, {}).get(vlan_id)
        if vlan is None:
            return self._fail(f"VLAN {vlan_id} not found on {device}")
        if "name" in params:
            vlan["name"] = params["name"]
        if "description" in params:
            vlan["description"] = params["description"]
        return self._ok(f"VLAN {vlan_id} updated on {device}", data={"vlan": vlan})

    async def _delete_vlan(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        vlan_id = params.get("vlan_id")
        force = params.get("force", False)

        device_vlans = self._vlan_db.get(device, {})
        if vlan_id not in device_vlans:
            return self._fail(f"VLAN {vlan_id} not found on {device}")
        if vlan_id in RESERVED_VLANS and not force:
            return self._fail(f"VLAN {vlan_id} is reserved — use force=true to override")

        # Check for active ports (simulated)
        if not force:
            active_ports = params.get("active_ports", 0)
            if active_ports > 0:
                return self._fail(
                    f"VLAN {vlan_id} has {active_ports} active port(s). Use force=true to decommission."
                )

        del device_vlans[vlan_id]
        logger.info("Deleted VLAN %d from %s", vlan_id, device)
        return self._ok(f"VLAN {vlan_id} removed from {device}")

    async def _list_vlans(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        vlans = list(self._vlan_db.get(device, {}).values())
        return self._ok(
            f"Found {len(vlans)} VLANs on {device}",
            data={"device": device, "vlans": vlans, "count": len(vlans)},
        )

    async def _assign_port(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        port = params.get("port")
        vlan_id = params.get("vlan_id")
        mode = params.get("mode", "access")  # access | trunk

        if vlan_id not in self._vlan_db.get(device, {}):
            return self._fail(f"VLAN {vlan_id} does not exist on {device}")

        return self._ok(
            f"Port {port} on {device} assigned to VLAN {vlan_id} ({mode})",
            data={"device": device, "port": port, "vlan_id": vlan_id, "mode": mode},
        )

    async def _audit_vlans(self, params: Dict[str, Any]) -> BotResponse:
        devices = params.get("devices", list(self._vlan_db.keys()))
        # Build VLAN-to-device matrix
        matrix: Dict[int, List[str]] = {}
        for device in devices:
            for vlan_id in self._vlan_db.get(device, {}):
                matrix.setdefault(vlan_id, []).append(device)

        # Find inconsistencies
        inconsistencies = []
        for vlan_id, present_on in matrix.items():
            if len(present_on) < len(devices):
                missing_on = [d for d in devices if d not in present_on]
                inconsistencies.append({
                    "vlan_id": vlan_id,
                    "present_on": present_on,
                    "missing_on": missing_on,
                })

        return self._ok(
            f"Audit complete — {len(inconsistencies)} inconsistencies found",
            data={"inconsistencies": inconsistencies, "devices_audited": len(devices)},
        )


if __name__ == "__main__":
    import uvicorn
    bot = VlanBot()
    app = bot.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8102)
