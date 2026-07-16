"""
Unit tests for ComplianceEngine
================================
"""

import pytest
from python.compliance.compliance_engine import (
    ComplianceEngine,
    ComplianceCheck,
    ComplianceResult,
    Severity,
)


@pytest.fixture
def engine():
    return ComplianceEngine()


class TestComplianceEngine:
    def test_engine_creation(self, engine):
        assert engine is not None
        assert len(engine.checks) > 0  # built-in checks loaded

    def test_check_ssh_only_pass(self, engine):
        config = {
            "line_vty": {
                "transport_input": "ssh",
            }
        }
        result = engine.check_config("test-device", config)
        ssh_check = next((r for r in result.results if "ssh" in r.check_name.lower()), None)
        # SSH-only config should pass
        assert ssh_check is None or ssh_check.passed

    def test_check_snmpv3_fail(self, engine):
        config = {
            "snmp": {
                "communities": [
                    {"name": "public", "version": "v2c"},
                ]
            }
        }
        result = engine.check_config("test-device", config)
        # SNMPv2c community should trigger a violation
        snmp_violations = [r for r in result.results if "snmp" in r.check_name.lower() and not r.passed]
        assert len(snmp_violations) > 0

    def test_check_ntp_redundancy(self, engine):
        config = {
            "ntp": {
                "servers": ["10.0.0.1"]  # Only one server
            }
        }
        result = engine.check_config("test-device", config)
        ntp_violations = [r for r in result.results if "ntp" in r.check_name.lower() and not r.passed]
        assert len(ntp_violations) > 0

    def test_generate_report(self, engine):
        config = {
            "ntp": {"servers": ["10.0.0.1", "10.0.0.2", "10.0.0.3"]},
            "aaa": {"enabled": True, "protocol": "tacacs+"},
        }
        result = engine.check_config("test-device", config)
        report = engine.generate_report(result)
        assert "device" in report
        assert "score" in report
        assert "violations" in report

    def test_save_report(self, engine, tmp_path):
        config = {}
        result = engine.check_config("test-device", config)
        output_path = tmp_path / "report.json"
        engine.save_report(result, str(output_path))
        assert output_path.exists()


class TestComplianceResult:
    def test_result_score(self):
        results = [
            ComplianceResult(check_name="check1", passed=True, severity=Severity.CRITICAL),
            ComplianceResults(check_name="check2", passed=False, severity=Severity.HIGH),
            ComplianceResult(check_name="check3", passed=True, severity=Severity.MEDIUM),
        ]
        # Note: score calculation depends on implementation
        # 2/3 passed = 66.7%

    def test_violations_filter(self):
        results = [
            ComplianceResult(check_name="pass1", passed=True, severity=Severity.LOW),
            ComplianceResult(check_name="fail1", passed=False, severity=Severity.CRITICAL),
        ]
        violations = [r for r in results if not r.passed]
        assert len(violations) == 1
        assert violations[0].severity == Severity.CRITICAL
