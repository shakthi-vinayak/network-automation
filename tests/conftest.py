"""
Shared pytest fixtures and configuration for network automation test suite.
"""

import os
import sys
import pytest
import yaml
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def inventories_dir(project_root):
    return project_root / "inventories"


@pytest.fixture(scope="session")
def templates_dir(project_root):
    return project_root / "templates"


@pytest.fixture(scope="session")
def group_vars_dir(project_root):
    return project_root / "group_vars"


@pytest.fixture(scope="session")
def production_inventory(inventories_dir):
    inv_path = inventories_dir / "production" / "hosts.yml"
    if inv_path.exists():
        with open(inv_path) as f:
            return yaml.safe_load(f)
    return {}


@pytest.fixture
def sample_device_vars():
    """Standard device variables for template rendering tests."""
    return {
        "hostname": "test-device-01",
        "domain_name": "lab.example.com",
        "vendor": "cisco",
        "platform": "ios-xe",
        "role": "core_router",
        "region": "us-east",
        "ntp_servers": ["10.0.0.1", "10.0.0.2", "10.0.0.3"],
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "syslog_servers": [
            {"host": "10.0.0.10", "severity": "informational"},
            {"host": "10.0.0.11", "severity": "informational"},
        ],
        "aaa": {
            "enabled": True,
            "protocol": "tacacs+",
            "servers": ["10.0.0.20", "10.0.0.21", "10.0.0.22"],
            "key": "TEST_KEY_12345",
        },
        "snmp": {
            "v3_enabled": True,
            "username": "snmpv3user",
            "auth_protocol": "sha",
            "auth_key": "AUTH_KEY_12345",
            "priv_protocol": "aes-256",
            "priv_key": "PRIV_KEY_12345",
        },
        "ssh": {
            "version": 2,
            "ciphers": ["aes256-gcm", "aes128-gcm", "aes256-ctr"],
            "macs": ["hmac-sha2-256", "hmac-sha2-512"],
            "kex_algorithms": ["curve25519-sha256", "diffie-hellman-group16-sha512"],
        },
        "login_banner": "AUTHORIZED ACCESS ONLY — DISCONNECT IF NOT AUTHORIZED",
        "motd_banner": "Enterprise Network Automation Lab",
    }


@pytest.fixture
def sample_firewall_vars():
    """Firewall-specific variables for Palo Alto / Fortinet template tests."""
    return {
        "hostname": "fw-test-01",
        "vendor": "paloalto",
        "platform": "panos",
        "management_ip": "10.0.1.1/24",
        "management_gateway": "10.0.1.254",
        "zones": [
            {"name": "trust", "interfaces": ["ethernet1/1"]},
            {"name": "untrust", "interfaces": ["ethernet1/2"]},
            {"name": "dmz", "interfaces": ["ethernet1/3"]},
        ],
        "security_rules": [
            {
                "name": "allow-web",
                "source_zone": "untrust",
                "destination_zone": "dmz",
                "source_addresses": ["any"],
                "destination_addresses": ["web-servers"],
                "applications": ["web-browsing", "ssl"],
                "action": "allow",
                "logging": True,
            }
        ],
    }
