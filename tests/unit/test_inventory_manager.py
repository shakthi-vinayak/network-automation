"""
Unit tests for InventoryManager
================================
"""

import os
import tempfile
import pytest
import yaml

from python.inventory.inventory_manager import InventoryManager, Device, DeviceGroup


SAMPLE_INVENTORY = {
    "all": {
        "children": {
            "core_routers": {
                "hosts": {
                    "core-rtr-01": {
                        "ansible_host": "10.0.0.1",
                        "vendor": "cisco",
                        "platform": "ios-xe",
                        "role": "core_router",
                        "region": "us-east",
                    },
                    "core-rtr-02": {
                        "ansible_host": "10.0.0.2",
                        "vendor": "cisco",
                        "platform": "ios-xe",
                        "role": "core_router",
                        "region": "us-east",
                    },
                }
            },
            "firewalls": {
                "hosts": {
                    "fw-01": {
                        "ansible_host": "10.0.1.1",
                        "vendor": "paloalto",
                        "platform": "panos",
                        "role": "firewall",
                        "region": "us-east",
                    }
                }
            },
        }
    }
}


@pytest.fixture
def inventory_file(tmp_path):
    inv_path = tmp_path / "hosts.yml"
    inv_path.write_text(yaml.dump(SAMPLE_INVENTORY))
    return str(inv_path)


@pytest.fixture
def manager(inventory_file):
    return InventoryManager(inventory_file)


class TestInventoryManager:
    def test_load_inventory(self, manager):
        assert manager is not None
        devices = manager.devices
        assert len(devices) >= 3

    def test_get_devices_by_role(self, manager):
        core_routers = manager.get_devices_by_role("core_router")
        assert len(core_routers) == 2
        for d in core_routers:
            assert d.role == "core_router"

    def test_get_devices_by_vendor(self, manager):
        cisco = manager.get_devices_by_vendor("cisco")
        assert len(cisco) == 2
        paloalto = manager.get_devices_by_vendor("paloalto")
        assert len(paloalto) == 1

    def test_get_devices_by_region(self, manager):
        us_east = manager.get_devices_by_region("us-east")
        assert len(us_east) == 3

    def test_nonexistent_role_returns_empty(self, manager):
        result = manager.get_devices_by_role("nonexistent_role")
        assert result == []

    def test_device_attributes(self, manager):
        devices = manager.get_devices_by_role("firewall")
        assert len(devices) == 1
        fw = devices[0]
        assert fw.vendor == "paloalto"
        assert fw.platform == "panos"
        assert fw.ansible_host == "10.0.1.1"

    def test_summary(self, manager):
        summary = manager.summary()
        assert "total_devices" in summary
        assert summary["total_devices"] == 3


class TestDevice:
    def test_device_creation(self):
        d = Device(
            name="test-rtr-01",
            ansible_host="192.168.1.1",
            vendor="cisco",
            platform="ios-xe",
            role="router",
            region="us-east",
        )
        assert d.name == "test-rtr-01"
        assert d.vendor == "cisco"

    def test_device_repr(self):
        d = Device(
            name="test-rtr-01",
            ansible_host="192.168.1.1",
            vendor="cisco",
            platform="ios-xe",
            role="router",
            region="us-east",
        )
        assert "test-rtr-01" in repr(d)
