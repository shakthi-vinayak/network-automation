"""
Port Bot
=========
Automates switchport provisioning, modification, and shutdown across network devices.

Actions:
    - configure_port    : Configure a switchport (access/trunk/L3)
    - shutdown_port     : Administratively shut down a port
    - no_shutdown_port  : Bring a port up
    - show_port         : Display port configuration
    - port_security     : Configure port security (MAC limiting, sticky MAC)
    - find_mac          : Find a MAC address across the fabric
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from bots.framework.base_bot import BaseBot, BotResponse

logger = logging.getLogger(__name__)


class PortBot(BaseBot):
    name = "port-bot"
    description = "Switchport lifecycle management bot"
    version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Port DB: {(device, port): config}
        self._port_db: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def list_actions(self) -> List[Dict[str, str]]:
        return [
            {"name": "configure_port", "description": "Configure a switchport"},
            {"name": "shutdown_port", "description": "Shut down a port"},
            {"name": "no_shutdown_port", "description": "Bring a port up"},
            {"name": "show_port", "description": "Show port configuration"},
            {"name": "port_security", "description": "Configure port security"},
            {"name": "find_mac", "description": "Locate a MAC address"},
        ]

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> BotResponse:
        handlers = {
            "configure_port": self._configure_port,
            "shutdown_port": self._shutdown_port,
            "no_shutdown_port": self._no_shutdown_port,
            "show_port": self._show_port,
            "port_security": self._port_security,
            "find_mac": self._find_mac,
        }
        handler = handlers.get(action)
        if handler is None:
            return self._fail(f"Unknown action: {action}")
        return await handler(parameters)

    async def _configure_port(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        port = params.get("port")
        mode = params.get("mode", "access")
        vlan_id = params.get("vlan_id")
        description = params.get("description", "")

        config = {
            "port": port,
            "mode": mode,
            "vlan_id": vlan_id,
            "description": description,
            "state": "enabled",
            "speed": params.get("speed", "auto"),
            "duplex": params.get("duplex", "auto"),
            "mtu": params.get("mtu", 1500),
            "port_security": params.get("port_security", False),
        }
        self._port_db.setdefault(device, {})[port] = config
        logger.info("Configured port %s on %s — mode=%s vlan=%s", port, device, mode, vlan_id)
        return self._ok(
            f"Port {port} configured on {device} (mode={mode}, vlan={vlan_id})",
            data={"device": device, "config": config},
        )

    async def _shutdown_port(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        port = params.get("port")
        port_cfg = self._port_db.get(device, {}).get(port)
        if port_cfg is None:
            return self._fail(f"Port {port} not found on {device}")
        port_cfg["state"] = "shutdown"
        return self._ok(f"Port {port} on {device} shut down", data={"config": port_cfg})

    async def _no_shutdown_port(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        port = params.get("port")
        port_cfg = self._port_db.get(device, {}).get(port)
        if port_cfg is None:
            return self._fail(f"Port {port} not found on {device}")
        port_cfg["state"] = "enabled"
        return self._ok(f"Port {port} on {device} enabled", data={"config": port_cfg})

    async def _show_port(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        port = params.get("port")
        port_cfg = self._port_db.get(device, {}).get(port)
        if port_cfg is None:
            return self._fail(f"Port {port} not configured on {device}")
        return self._ok(f"Port {port} on {device}", data={"config": port_cfg})

    async def _port_security(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        port = params.get("port")
        max_macs = params.get("max_macs", 1)
        violation = params.get("violation_action", "restrict")  # restrict | protect | shutdown

        port_cfg = self._port_db.get(device, {}).get(port)
        if port_cfg is None:
            return self._fail(f"Port {port} not configured on {device}")

        port_cfg["port_security"] = True
        port_cfg["max_macs"] = max_macs
        port_cfg["violation_action"] = violation
        return self._ok(
            f"Port security enabled on {port} ({device}): max_macs={max_macs}, action={violation}",
            data={"config": port_cfg},
        )

    async def _find_mac(self, params: Dict[str, Any]) -> BotResponse:
        mac = params.get("mac_address", "").lower()
        # Simulated lookup
        results = []
        for device, ports in self._port_db.items():
            for port, cfg in ports.items():
                if cfg.get("mac_address", "").lower() == mac:
                    results.append({"device": device, "port": port, "config": cfg})
        if not results:
            return self._fail(f"MAC address {mac} not found in port database")
        return self._ok(
            f"MAC {mac} found on {len(results)} port(s)",
            data={"results": results},
        )


if __name__ == "__main__":
    import uvicorn
    bot = PortBot()
    app = bot.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8103)
