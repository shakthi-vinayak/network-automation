"""
Health Bot
===========
Continuous health monitoring, diagnostics, and alerting for network devices.

Actions:
    - check_health      : Run a comprehensive health check on a device
    - check_reachability: Ping / TCP reachability test
    - check_interfaces  : Interface status and utilisation summary
    - check_cpu_memory  : CPU and memory utilisation
    - check_bgp         : BGP session status
    - run_diagnostics   : Full diagnostic bundle (traceroute, logs, counters)
"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

from bots.framework.base_bot import BaseBot, BotResponse

logger = logging.getLogger(__name__)


class HealthBot(BaseBot):
    name = "health-bot"
    description = "Network device health monitoring and diagnostics bot"
    version = "1.0.0"

    # Thresholds (overridable via config)
    DEFAULT_THRESHOLDS = {
        "cpu_warning": 70,
        "cpu_critical": 90,
        "memory_warning": 75,
        "memory_critical": 95,
        "interface_util_warning": 80,
        "interface_util_critical": 95,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(config or {}).get("thresholds", {})}

    def list_actions(self) -> List[Dict[str, str]]:
        return [
            {"name": "check_health", "description": "Comprehensive device health check"},
            {"name": "check_reachability", "description": "Device reachability test"},
            {"name": "check_interfaces", "description": "Interface status and utilisation"},
            {"name": "check_cpu_memory", "description": "CPU and memory utilisation"},
            {"name": "check_bgp", "description": "BGP session status"},
            {"name": "run_diagnostics", "description": "Full diagnostic bundle"},
        ]

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> BotResponse:
        handlers = {
            "check_health": self._check_health,
            "check_reachability": self._check_reachability,
            "check_interfaces": self._check_interfaces,
            "check_cpu_memory": self._check_cpu_memory,
            "check_bgp": self._check_bgp,
            "run_diagnostics": self._run_diagnostics,
        }
        handler = handlers.get(action)
        if handler is None:
            return self._fail(f"Unknown action: {action}")
        return await handler(parameters)

    async def _check_health(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        # Simulated health data
        cpu = random.randint(10, 95)
        memory = random.randint(20, 90)
        interfaces_up = random.randint(20, 48)
        interfaces_down = random.randint(0, 4)
        bgp_sessions_up = random.randint(5, 20)
        bgp_sessions_down = random.randint(0, 2)

        issues = []
        if cpu >= self.thresholds["cpu_critical"]:
            issues.append(f"CRITICAL: CPU at {cpu}%")
        elif cpu >= self.thresholds["cpu_warning"]:
            issues.append(f"WARNING: CPU at {cpu}%")
        if memory >= self.thresholds["memory_critical"]:
            issues.append(f"CRITICAL: Memory at {memory}%")
        elif memory >= self.thresholds["memory_warning"]:
            issues.append(f"WARNING: Memory at {memory}%")
        if bgp_sessions_down > 0:
            issues.append(f"WARNING: {bgp_sessions_down} BGP session(s) down")

        health_score = max(0, 100 - len(issues) * 15 - (cpu // 10) - (memory // 10))
        status = "healthy" if not issues else ("degraded" if all("WARNING" in i for i in issues) else "critical")

        return self._ok(
            f"Health check: {device} — score {health_score}/100 ({status})",
            data={
                "device": device,
                "health_score": health_score,
                "status": status,
                "cpu_percent": cpu,
                "memory_percent": memory,
                "interfaces": {"up": interfaces_up, "down": interfaces_down},
                "bgp_sessions": {"up": bgp_sessions_up, "down": bgp_sessions_down},
                "issues": issues,
            },
        )

    async def _check_reachability(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        # Simulated ping
        reachable = random.random() > 0.1
        latency_ms = round(random.uniform(1, 50), 2) if reachable else None
        return self._ok(
            f"{device} is {'reachable' if reachable else 'UNREACHABLE'}",
            data={
                "device": device,
                "reachable": reachable,
                "latency_ms": latency_ms,
                "packet_loss_percent": 0 if reachable else 100,
            },
        )

    async def _check_interfaces(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        interfaces = []
        for i in range(1, random.randint(5, 12)):
            state = random.choice(["up", "up", "up", "down"])
            interfaces.append({
                "name": f"GigabitEthernet0/0/{i}",
                "state": state,
                "speed": "1Gbps",
                "input_util_percent": round(random.uniform(0, 85), 1) if state == "up" else 0,
                "output_util_percent": round(random.uniform(0, 75), 1) if state == "up" else 0,
                "errors": random.randint(0, 5),
            })
        down_count = sum(1 for i in interfaces if i["state"] == "down")
        return self._ok(
            f"Interface summary for {device}: {len(interfaces) - down_count}/{len(interfaces)} up",
            data={"device": device, "interfaces": interfaces},
        )

    async def _check_cpu_memory(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        cpu = random.randint(5, 95)
        memory = random.randint(15, 90)
        cpu_5min = random.randint(5, 90)
        cpu_15min = random.randint(5, 85)
        return self._ok(
            f"CPU/Memory for {device}: CPU={cpu}% Memory={memory}%",
            data={
                "device": device,
                "cpu_percent": cpu,
                "cpu_5min_avg": cpu_5min,
                "cpu_15min_avg": cpu_15min,
                "memory_percent": memory,
                "memory_used_mb": random.randint(500, 4000),
                "memory_total_mb": 8192,
            },
        )

    async def _check_bgp(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        sessions = []
        for asn in [65001, 65002, 65100, 65200]:
            state = random.choice(["established", "established", "established", "idle", "active"])
            sessions.append({
                "neighbor": f"10.{random.randint(0,255)}.{random.randint(0,255)}.1",
                "remote_as": asn,
                "state": state,
                "prefixes_received": random.randint(50, 500) if state == "established" else 0,
                "uptime_seconds": random.randint(3600, 864000) if state == "established" else 0,
            })
        down = [s for s in sessions if s["state"] != "established"]
        return self._ok(
            f"BGP on {device}: {len(sessions) - len(down)}/{len(sessions)} sessions up",
            data={"device": device, "sessions": sessions, "down_count": len(down)},
        )

    async def _run_diagnostics(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        return self._ok(
            f"Diagnostic bundle collected for {device}",
            data={
                "device": device,
                "checks_performed": [
                    "reachability", "cpu_memory", "interfaces",
                    "bgp", "routing_table", "log_buffer", "arp_table"
                ],
                "log_entries_collected": random.randint(50, 200),
                "route_count": random.randint(500, 5000),
                "arp_entries": random.randint(20, 200),
            },
        )


if __name__ == "__main__":
    import uvicorn
    bot = HealthBot()
    app = bot.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8105)
