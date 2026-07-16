"""Inventory Manager - Parse, enrich, and manage network device inventory.

This module provides classes for loading Ansible inventories, enriching device
data from CMDB sources, and querying device information.

Example:
    >>> from python.inventory import InventoryManager
    >>> inv = InventoryManager("inventories/production/hosts.yml")
    >>> devices = inv.get_devices_by_role("core_router")
    >>> for device in devices:
    ...     print(device.hostname, device.ip)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Device:
    """Represents a single network device.

    Attributes:
        hostname: Device hostname.
        ip: Management IP address.
        vendor: Device vendor (cisco, juniper, arista, etc.).
        platform: Device platform (ios-xe, nx-os, eos, etc.).
        role: Device role (core_router, firewall, etc.).
        region: Geographic region.
        site: Site/datacenter identifier.
        model: Hardware model.
        ha_role: High-availability role (primary, secondary, standalone).
        environment: Environment name (production, staging, lab, dr).
        tags: Additional tags for filtering.
        metadata: Additional device metadata.
    """

    hostname: str
    ip: str
    vendor: str
    platform: str
    role: str
    region: str
    site: str = ""
    model: str = ""
    ha_role: str = "standalone"
    environment: str = "production"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_primary(self) -> bool:
        """Check if device is primary in HA pair."""
        return self.ha_role in ("primary", "active")

    @property
    def fqdn(self) -> str:
        """Return fully qualified domain name."""
        return f"{self.hostname}.{self.site}.corp.example.com"

    def to_dict(self) -> dict[str, Any]:
        """Convert device to dictionary."""
        return {
            "hostname": self.hostname,
            "ip": self.ip,
            "vendor": self.vendor,
            "platform": self.platform,
            "role": self.role,
            "region": self.region,
            "site": self.site,
            "model": self.model,
            "ha_role": self.ha_role,
            "environment": self.environment,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class DeviceGroup:
    """Represents a group of network devices.

    Attributes:
        name: Group name (e.g., core_routers, firewalls).
        devices: List of devices in the group.
        variables: Group-level variables.
    """

    name: str
    devices: list[Device] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)

    def add_device(self, device: Device) -> None:
        """Add a device to the group."""
        self.devices.append(device)

    def get_devices_by_region(self, region: str) -> list[Device]:
        """Get devices in a specific region."""
        return [d for d in self.devices if d.region == region]


class InventoryManager:
    """Manages network device inventory.

    Loads Ansible inventory files, parses them, and provides methods
    for querying and filtering devices.

    Attributes:
        inventory_path: Path to the inventory file.
        groups: Dictionary of device groups.
        devices: List of all devices.
    """

    def __init__(self, inventory_path: str | Path) -> None:
        """Initialize InventoryManager.

        Args:
            inventory_path: Path to Ansible inventory YAML file.
        """
        self.inventory_path = Path(inventory_path)
        self.groups: dict[str, DeviceGroup] = {}
        self.devices: list[Device] = []
        self._raw_inventory: dict[str, Any] = {}
        self._load_inventory()

    def _load_inventory(self) -> None:
        """Load and parse the inventory file."""
        with open(self.inventory_path, "r", encoding="utf-8") as f:
            self._raw_inventory = yaml.safe_load(f)

        if not self._raw_inventory:
            return

        # Parse global variables
        global_vars = self._raw_inventory.get("all", {}).get("vars", {})
        environment = global_vars.get("environment", "production")

        # Parse device groups
        children = self._raw_inventory.get("all", {}).get("children", {})
        for group_name, group_data in children.items():
            group = DeviceGroup(name=group_name)
            group.variables = group_data.get("vars", {})

            hosts = group_data.get("hosts", {})
            for hostname, host_vars in hosts.items():
                device = Device(
                    hostname=hostname,
                    ip=host_vars.get("ansible_host", ""),
                    vendor=host_vars.get("vendor", ""),
                    platform=host_vars.get("platform", ""),
                    role=host_vars.get("role", group_name),
                    region=host_vars.get("region", ""),
                    site=host_vars.get("site", ""),
                    model=host_vars.get("model", ""),
                    ha_role=host_vars.get("ha_role", "standalone"),
                    environment=environment,
                    tags=host_vars.get("tags", []),
                )
                group.add_device(device)
                self.devices.append(device)

            self.groups[group_name] = group

    def get_devices_by_role(self, role: str) -> list[Device]:
        """Get all devices with a specific role.

        Args:
            role: Device role to filter by.

        Returns:
            List of devices matching the role.
        """
        return [d for d in self.devices if d.role == role]

    def get_devices_by_vendor(self, vendor: str) -> list[Device]:
        """Get all devices from a specific vendor.

        Args:
            vendor: Vendor name to filter by.

        Returns:
            List of devices matching the vendor.
        """
        return [d for d in self.devices if d.vendor == vendor]

    def get_devices_by_region(self, region: str) -> list[Device]:
        """Get all devices in a specific region.

        Args:
            region: Region to filter by.

        Returns:
            List of devices in the region.
        """
        return [d for d in self.devices if d.region == region]

    def get_devices_by_site(self, site: str) -> list[Device]:
        """Get all devices at a specific site.

        Args:
            site: Site identifier to filter by.

        Returns:
            List of devices at the site.
        """
        return [d for d in self.devices if d.site == site]

    def get_group(self, group_name: str) -> DeviceGroup | None:
        """Get a device group by name.

        Args:
            group_name: Name of the group.

        Returns:
            DeviceGroup or None if not found.
        """
        return self.groups.get(group_name)

    def get_device(self, hostname: str) -> Device | None:
        """Get a specific device by hostname.

        Args:
            hostname: Device hostname.

        Returns:
            Device or None if not found.
        """
        for device in self.devices:
            if device.hostname == hostname:
                return device
        return None

    def get_primary_devices(self) -> list[Device]:
        """Get all primary/active devices in HA pairs.

        Returns:
            List of primary devices.
        """
        return [d for d in self.devices if d.is_primary]

    def to_json(self) -> str:
        """Export inventory as JSON.

        Returns:
            JSON string representation of the inventory.
        """
        return json.dumps(
            {
                "groups": {
                    name: {
                        "devices": [d.to_dict() for d in group.devices],
                        "variables": group.variables,
                    }
                    for name, group in self.groups.items()
                },
                "total_devices": len(self.devices),
            },
            indent=2,
        )

    def summary(self) -> dict[str, int]:
        """Get inventory summary statistics.

        Returns:
            Dictionary with counts by vendor, role, and region.
        """
        vendors: dict[str, int] = {}
        roles: dict[str, int] = {}
        regions: dict[str, int] = {}

        for device in self.devices:
            vendors[device.vendor] = vendors.get(device.vendor, 0) + 1
            roles[device.role] = roles.get(device.role, 0) + 1
            regions[device.region] = regions.get(device.region, 0) + 1

        return {
            "total_devices": len(self.devices),
            "total_groups": len(self.groups),
            "vendors": vendors,
            "roles": roles,
            "regions": regions,
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python inventory_manager.py <inventory_path>")
        sys.exit(1)

    manager = InventoryManager(sys.argv[1])
    print(json.dumps(manager.summary(), indent=2))
