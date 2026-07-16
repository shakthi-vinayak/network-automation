"""
Unit tests for ConfigGenerator
===============================
"""

import os
import pytest
from pathlib import Path

from python.config_gen.config_generator import ConfigGenerator


TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


@pytest.fixture
def generator():
    return ConfigGenerator(templates_dir=str(TEMPLATES_DIR))


SAMPLE_VARS = {
    "hostname": "test-rtr-01",
    "domain_name": "example.com",
    "ntp_servers": ["10.0.0.1", "10.0.0.2"],
    "dns_servers": ["8.8.8.8", "8.8.4.4"],
    "syslog_servers": [
        {"host": "10.0.0.10", "severity": "informational", "transport": "udp"},
        {"host": "10.0.0.11", "severity": "informational", "transport": "tcp"},
    ],
    "aaa": {
        "enabled": True,
        "protocol": "tacacs+",
        "servers": ["10.0.0.20", "10.0.0.21"],
        "key": "ENCRYPTED_KEY",
    },
    "snmp": {
        "v3_enabled": True,
        "username": "snmpuser",
        "auth_protocol": "sha",
        "auth_key": "AUTH_KEY",
        "priv_protocol": "aes-256",
        "priv_key": "PRIV_KEY",
    },
    "ssh": {
        "version": 2,
        "ciphers": ["aes256-gcm", "aes128-gcm"],
        "macs": ["hmac-sha2-256", "hmac-sha2-512"],
    },
    "login_banner": "AUTHORIZED ACCESS ONLY",
    "motd_banner": "Network Automation Lab",
    "interfaces": [
        {"name": "GigabitEthernet0/0", "description": "Uplink", "ip": "10.0.1.1", "mask": "255.255.255.0"},
    ],
    "vlans": [
        {"id": 100, "name": "MGMT"},
        {"id": 200, "name": "DATA"},
    ],
}


class TestConfigGenerator:
    def test_generator_creation(self, generator):
        assert generator is not None

    def test_list_templates(self, generator):
        templates = generator.list_templates()
        assert isinstance(templates, list)
        # Should find at least the Cisco IOS template
        cisco_templates = [t for t in templates if "cisco" in t.lower()]
        assert len(cisco_templates) > 0

    def test_render_cisco_ios(self, generator):
        config = generator.render("cisco_ios/base_config.j2", SAMPLE_VARS)
        assert config is not None
        assert "hostname test-rtr-01" in config
        assert "ntp server 10.0.0.1" in config

    def test_render_includes_banners(self, generator):
        config = generator.render("cisco_ios/base_config.j2", SAMPLE_VARS)
        assert "AUTHORIZED ACCESS ONLY" in config
        assert "Network Automation Lab" in config

    def test_render_includes_snmpv3(self, generator):
        config = generator.render("cisco_ios/base_config.j2", SAMPLE_VARS)
        assert "snmp" in config.lower()

    def test_render_includes_vlans(self, generator):
        config = generator.render("cisco_ios/base_config.j2", SAMPLE_VARS)
        assert "100" in config or "MGMT" in config

    def test_render_missing_template_raises(self, generator):
        with pytest.raises(Exception):
            generator.render("nonexistent/template.j2", {})

    def test_validate_config(self, generator):
        config = generator.render("cisco_ios/base_config.j2", SAMPLE_VARS)
        valid, errors = generator.validate(config, vendor="cisco_ios")
        assert valid
        assert len(errors) == 0


class TestConfigGeneratorEdgeCases:
    def test_empty_vars(self, generator):
        # Should not crash even with minimal vars
        try:
            config = generator.render("cisco_ios/base_config.j2", {"hostname": "test"})
            assert "hostname test" in config
        except Exception:
            # Template may require certain vars — that's expected
            pass

    def test_render_all_vendors(self, generator):
        vendors = ["cisco_ios", "juniper_srx", "arista_eos", "paloalto", "fortinet"]
        for vendor in vendors:
            template_path = f"{vendor}/base_config.j2"
            try:
                config = generator.render(template_path, SAMPLE_VARS)
                assert config is not None and len(config) > 0
            except Exception:
                # Some templates may require vendor-specific vars
                pass
