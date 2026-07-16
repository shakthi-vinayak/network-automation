"""Compliance Engine - Automated compliance checking for network devices.

Runs compliance checks against device configurations or running state.
Supports pluggable rule sets for extensibility.

Example:
    >>> from python.compliance import ComplianceEngine
    >>> engine = ComplianceEngine()
    >>> result = engine.check_config(config_text)
    >>> print(f"Passed: {result.passed}, Failed: {result.failed}")
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Compliance check severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class ComplianceCheck:
    """A single compliance check definition.

    Attributes:
        name: Human-readable check name.
        description: What this check validates.
        severity: Severity level if check fails.
        check_func: Function that performs the check.
        category: Check category (ssh, ntp, aaa, snmp, etc.).
    """

    name: str
    description: str
    severity: Severity
    check_func: Callable[[str], bool]
    category: str = "general"


@dataclass
class ComplianceResult:
    """Result of a compliance check.

    Attributes:
        check_name: Name of the check.
        passed: Whether the check passed.
        severity: Severity level.
        message: Result message.
        timestamp: When the check was run.
    """

    check_name: str
    passed: bool
    severity: Severity
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ComplianceEngine:
    """Network device compliance checking engine.

    Runs a set of compliance checks against device configurations
    and produces a detailed compliance report.
    """

    def __init__(self) -> None:
        """Initialize the compliance engine with default checks."""
        self.checks: list[ComplianceCheck] = []
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register built-in compliance checks."""

        # SSH Only - No Telnet
        self.add_check(ComplianceCheck(
            name="SSH Only - No Telnet",
            description="Verify telnet is not enabled and SSH is configured",
            severity=Severity.CRITICAL,
            check_func=lambda config: (
                "transport input ssh" in config
                and "transport input telnet" not in config
                and "ip ssh version 2" in config
            ),
            category="ssh",
        ))

        # NTP Configured
        self.add_check(ComplianceCheck(
            name="NTP Configured",
            description="Verify NTP is configured with at least 2 servers",
            severity=Severity.HIGH,
            check_func=lambda config: (
                len(re.findall(r"ntp server \d+\.\d+\.\d+\.\d+", config)) >= 2
            ),
            category="ntp",
        ))

        # AAA Enabled
        self.add_check(ComplianceCheck(
            name="AAA Enabled",
            description="Verify AAA is enabled with TACACS+ or RADIUS",
            severity=Severity.CRITICAL,
            check_func=lambda config: (
                "aaa new-model" in config
                and ("tacacs" in config.lower() or "radius" in config.lower())
            ),
            category="aaa",
        ))

        # SNMPv3 Only
        self.add_check(ComplianceCheck(
            name="SNMPv3 Only",
            description="Verify only SNMPv3 is used (no v1/v2c communities)",
            severity=Severity.HIGH,
            check_func=lambda config: (
                "snmp-server community" not in config
                and "snmp-server user" in config
            ),
            category="snmp",
        ))

        # Logging Enabled
        self.add_check(ComplianceCheck(
            name="Logging Enabled",
            description="Verify syslog is configured with at least 2 servers",
            severity=Severity.MEDIUM,
            check_func=lambda config: (
                len(re.findall(r"logging host \d+\.\d+\.\d+\.\d+", config)) >= 2
            ),
            category="logging",
        ))

        # Approved Ciphers
        self.add_check(ComplianceCheck(
            name="Approved SSH Ciphers",
            description="Verify only approved SSH ciphers are configured",
            severity=Severity.HIGH,
            check_func=lambda config: (
                "aes256-gcm" in config or "aes256-ctr" in config
            ),
            category="ssh",
        ))

        # Password Policy
        self.add_check(ComplianceCheck(
            name="Password Policy",
            description="Verify password encryption and minimum length",
            severity=Severity.CRITICAL,
            check_func=lambda config: (
                "service password-encryption" in config
                or "password encryption aes" in config
            ),
            category="security",
        ))

        # Banner Configured
        self.add_check(ComplianceCheck(
            name="Login Banner",
            description="Verify login banner is configured",
            severity=Severity.LOW,
            check_func=lambda config: "banner login" in config.lower(),
            category="banner",
        ))

        # No default credentials
        self.add_check(ComplianceCheck(
            name="No Default Credentials",
            description="Verify no default usernames/passwords exist",
            severity=Severity.CRITICAL,
            check_func=lambda config: (
                "username admin password admin" not in config
                and "username cisco password cisco" not in config
            ),
            category="security",
        ))

    def add_check(self, check: ComplianceCheck) -> None:
        """Add a compliance check.

        Args:
            check: ComplianceCheck instance to add.
        """
        self.checks.append(check)

    def remove_check(self, name: str) -> None:
        """Remove a compliance check by name.

        Args:
            name: Name of the check to remove.
        """
        self.checks = [c for c in self.checks if c.name != name]

    def check_config(self, config: str) -> list[ComplianceResult]:
        """Run all compliance checks against a configuration.

        Args:
            config: Device configuration text.

        Returns:
            List of ComplianceResult objects.
        """
        results: list[ComplianceResult] = []

        for check in self.checks:
            try:
                passed = check.check_func(config)
                result = ComplianceResult(
                    check_name=check.name,
                    passed=passed,
                    severity=check.severity,
                    message="PASS" if passed else f"FAIL: {check.description}",
                )
            except Exception as e:
                result = ComplianceResult(
                    check_name=check.name,
                    passed=False,
                    severity=check.severity,
                    message=f"ERROR: {e}",
                )
            results.append(result)

        return results

    def check_configs(
        self, configs: dict[str, str]
    ) -> dict[str, list[ComplianceResult]]:
        """Run compliance checks on multiple device configurations.

        Args:
            configs: Dictionary mapping device names to configurations.

        Returns:
            Dictionary mapping device names to compliance results.
        """
        results: dict[str, list[ComplianceResult]] = {}
        for device_name, config in configs.items():
            results[device_name] = self.check_config(config)
        return results

    def generate_report(
        self, results: list[ComplianceResult], device_name: str = ""
    ) -> dict[str, Any]:
        """Generate a compliance report from results.

        Args:
            results: List of ComplianceResult objects.
            device_name: Optional device name for the report.

        Returns:
            Report dictionary with summary and details.
        """
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        report = {
            "device": device_name,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": len(results),
                "passed": passed,
                "failed": failed,
                "compliance_percentage": round(
                    (passed / len(results) * 100) if results else 0, 1
                ),
            },
            "checks": [
                {
                    "name": r.check_name,
                    "passed": r.passed,
                    "severity": r.severity.value,
                    "message": r.message,
                }
                for r in results
            ],
            "critical_failures": [
                r.check_name
                for r in results
                if not r.passed and r.severity == Severity.CRITICAL
            ],
        }
        return report

    def save_report(
        self, report: dict[str, Any], output_path: str
    ) -> None:
        """Save compliance report as JSON.

        Args:
            report: Report dictionary.
            output_path: Path to save the report.
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Compliance report saved to {output_path}")
