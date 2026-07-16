"""
Compliance Bot
===============
Automated compliance scanning, reporting, and remediation workflow bot.

Actions:
    - scan_device       : Run compliance scan on a single device
    - scan_group        : Run compliance scan on a device group
    - get_report        : Retrieve latest compliance report
    - remediate         : Auto-remediate a specific compliance violation
    - add_policy        : Register a new compliance policy
    - list_policies     : List all active compliance policies
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bots.framework.base_bot import BaseBot, BotResponse

logger = logging.getLogger(__name__)

# Default built-in policies
BUILTIN_POLICIES: List[Dict[str, Any]] = [
    {"id": "POL-001", "name": "SSH-Only Access", "severity": "CRITICAL",
     "check": "no_telnet", "description": "Telnet must be disabled; SSH v2 only"},
    {"id": "POL-002", "name": "SNMPv3 Required", "severity": "CRITICAL",
     "check": "snmpv3_only", "description": "SNMPv1/v2c communities must not be configured"},
    {"id": "POL-003", "name": "NTP Redundancy", "severity": "HIGH",
     "check": "ntp_servers", "description": "Minimum 2 NTP servers configured"},
    {"id": "POL-004", "name": "AAA Required", "severity": "CRITICAL",
     "check": "aaa_enabled", "description": "AAA with TACACS+ or RADIUS required"},
    {"id": "POL-005", "name": "Approved Ciphers", "severity": "HIGH",
     "check": "ssh_ciphers", "description": "Only approved SSH cipher suites"},
    {"id": "POL-006", "name": "Logging Enabled", "severity": "HIGH",
     "check": "syslog_configured", "description": "Minimum 2 syslog servers"},
    {"id": "POL-007", "name": "Banner Configured", "severity": "MEDIUM",
     "check": "login_banner", "description": "Login and MOTD banners required"},
    {"id": "POL-008", "name": "No Default Credentials", "severity": "CRITICAL",
     "check": "no_default_creds", "description": "Default passwords must be changed"},
]


class ComplianceBot(BaseBot):
    name = "compliance-bot"
    description = "Network compliance scanning and policy enforcement bot"
    version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._policies: List[Dict[str, Any]] = list(BUILTIN_POLICIES)
        self._reports: Dict[str, List[Dict[str, Any]]] = {}

    def list_actions(self) -> List[Dict[str, str]]:
        return [
            {"name": "scan_device", "description": "Run compliance scan on a device"},
            {"name": "scan_group", "description": "Scan a device group for compliance"},
            {"name": "get_report", "description": "Get latest compliance report"},
            {"name": "remediate", "description": "Auto-remediate a violation"},
            {"name": "add_policy", "description": "Add a new compliance policy"},
            {"name": "list_policies", "description": "List active policies"},
        ]

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> BotResponse:
        handlers = {
            "scan_device": self._scan_device,
            "scan_group": self._scan_group,
            "get_report": self._get_report,
            "remediate": self._remediate,
            "add_policy": self._add_policy,
            "list_policies": self._list_policies,
        }
        handler = handlers.get(action)
        if handler is None:
            return self._fail(f"Unknown action: {action}")
        return await handler(parameters)

    async def _scan_device(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        device_config = params.get("running_config", {})
        violations = []
        passed = []
        for policy in self._policies:
            result = self._run_check(policy["check"], device_config)
            entry = {
                "policy_id": policy["id"],
                "policy_name": policy["name"],
                "severity": policy["severity"],
                "passed": result,
            }
            if result:
                passed.append(entry)
            else:
                violations.append(entry)

        report = {
            "device": device,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_policies": len(self._policies),
            "passed": len(passed),
            "violations": len(violations),
            "compliance_score": round(len(passed) / len(self._policies) * 100, 1),
            "violation_details": violations,
        }
        self._reports.setdefault(device, []).append(report)
        logger.info(
            "Compliance scan: %s — score %.1f%% (%d violations)",
            device, report["compliance_score"], report["violations"],
        )
        return self._ok(
            f"Compliance scan: {device} — {report['compliance_score']}% compliant",
            data=report,
        )

    async def _scan_group(self, params: Dict[str, Any]) -> BotResponse:
        devices = params.get("devices", [])
        results = []
        for device in devices:
            result = await self._scan_device({"device": device, "running_config": params.get("configs", {}).get(device, {})})
            results.append(result.to_dict())
        return self._ok(
            f"Group scan complete — {len(results)} devices scanned",
            data={"devices_scanned": len(results), "results": results},
        )

    async def _get_report(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        reports = self._reports.get(device, [])
        if not reports:
            return self._fail(f"No compliance reports found for {device}")
        return self._ok(f"Latest report for {device}", data={"report": reports[-1]})

    async def _remediate(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        policy_id = params.get("policy_id")
        policy = next((p for p in self._policies if p["id"] == policy_id), None)
        if not policy:
            return self._fail(f"Policy {policy_id} not found")
        return self._ok(
            f"Remediation queued for {device} — policy {policy_id} ({policy['name']})",
            data={"device": device, "policy": policy, "status": "pending"},
        )

    async def _add_policy(self, params: Dict[str, Any]) -> BotResponse:
        policy = {
            "id": params.get("policy_id", f"POL-{len(self._policies) + 1:03d}"),
            "name": params.get("name"),
            "severity": params.get("severity", "MEDIUM"),
            "check": params.get("check"),
            "description": params.get("description", ""),
        }
        self._policies.append(policy)
        return self._ok(f"Policy {policy['id']} added", data={"policy": policy})

    async def _list_policies(self, params: Dict[str, Any]) -> BotResponse:
        return self._ok(
            f"{len(self._policies)} active policies",
            data={"policies": self._policies, "count": len(self._policies)},
        )

    # -- compliance checks --------------------------------------------------
    def _run_check(self, check_name: str, config: Dict[str, Any]) -> bool:
        checks = {
            "no_telnet": lambda c: not c.get("telnet_enabled", False),
            "snmpv3_only": lambda c: not c.get("snmp_v1v2_communities", []),
            "ntp_servers": lambda c: len(c.get("ntp_servers", [])) >= 2,
            "aaa_enabled": lambda c: c.get("aaa_enabled", False),
            "ssh_ciphers": lambda c: all(
                cip in ["aes256-gcm", "aes128-gcm", "aes256-ctr"]
                for cip in c.get("ssh_ciphers", ["aes256-gcm"])
            ),
            "syslog_configured": lambda c: len(c.get("syslog_servers", [])) >= 2,
            "login_banner": lambda c: bool(c.get("login_banner", "")),
            "no_default_creds": lambda c: not c.get("default_credentials_active", False),
        }
        fn = checks.get(check_name)
        return fn(config) if fn else True


if __name__ == "__main__":
    import uvicorn
    bot = ComplianceBot()
    app = bot.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8106)
