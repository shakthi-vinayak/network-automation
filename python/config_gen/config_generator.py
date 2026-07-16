"""Configuration Generator - Generate device configs from Jinja2 templates.

Generates network device configurations from Jinja2 templates and structured
YAML data (inventory, group_vars, host_vars).

Example:
    >>> from python.config_gen import ConfigGenerator
    >>> gen = ConfigGenerator(templates_dir="./templates", data_dir="./group_vars")
    >>> config = gen.generate("core-rtr-01-us-east", "cisco_ios/base_config.j2")
    >>> gen.save(config, "./output/core-rtr-01-us-east.cfg")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

logger = logging.getLogger(__name__)


class ConfigGenerator:
    """Generate network device configurations from Jinja2 templates.

    Attributes:
        templates_dir: Path to Jinja2 templates directory.
        data_dir: Path to variable data directory.
        output_dir: Path for generated configuration output.
    """

    def __init__(
        self,
        templates_dir: str | Path = "./templates",
        data_dir: str | Path = ".",
        output_dir: str | Path = "./output",
    ) -> None:
        """Initialize ConfigGenerator.

        Args:
            templates_dir: Path to templates directory.
            data_dir: Path to base data directory containing group_vars/host_vars.
            output_dir: Path for output configurations.
        """
        self.templates_dir = Path(templates_dir)
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Register custom filters
        self._register_filters()

    def _register_filters(self) -> None:
        """Register custom Jinja2 filters."""

        def ip_network(address: str, prefix: int = 24) -> str:
            """Extract network address from IP/prefix."""
            parts = address.split(".")
            if prefix >= 24:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
            elif prefix >= 16:
                return f"{parts[0]}.{parts[1]}.0.0"
            elif prefix >= 8:
                return f"{parts[0]}.0.0.0"
            return "0.0.0.0"

        def wildcard_mask(mask: str) -> str:
            """Convert subnet mask to wildcard."""
            octets = [255 - int(x) for x in mask.split(".")]
            return ".".join(str(x) for x in octets)

        def prefix_to_mask(prefix: int) -> str:
            """Convert prefix length to subnet mask."""
            bits = "1" * prefix + "0" * (32 - prefix)
            return ".".join(
                str(int(bits[i : i + 8], 2)) for i in range(0, 32, 8)
            )

        self.env.filters["ip_network"] = ip_network
        self.env.filters["wildcard_mask"] = wildcard_mask
        self.env.filters["prefix_to_mask"] = prefix_to_mask

    def load_variables(self, device_name: str) -> dict[str, Any]:
        """Load merged variables for a device.

        Merges group_vars/all.yml, group_vars/<group>.yml, and
        host_vars/<device>.yml in that order.

        Args:
            device_name: Device hostname.

        Returns:
            Merged variable dictionary.
        """
        variables: dict[str, Any] = {}

        # Load all.yml (global defaults)
        all_vars_path = self.data_dir / "group_vars" / "all.yml"
        if all_vars_path.exists():
            with open(all_vars_path, "r", encoding="utf-8") as f:
                all_vars = yaml.safe_load(f) or {}
                variables.update(all_vars)

        # Load host-specific vars (override globals)
        host_vars_path = self.data_dir / "host_vars" / f"{device_name}.yml"
        if host_vars_path.exists():
            with open(host_vars_path, "r", encoding="utf-8") as f:
                host_vars = yaml.safe_load(f) or {}
                variables.update(host_vars)

        return variables

    def generate(
        self,
        device_name: str,
        template_name: str,
        extra_vars: dict[str, Any] | None = None,
    ) -> str:
        """Generate configuration for a device.

        Args:
            device_name: Device hostname.
            template_name: Jinja2 template path relative to templates_dir.
            extra_vars: Additional variables to pass to the template.

        Returns:
            Generated configuration string.

        Raises:
            TemplateNotFound: If the template doesn't exist.
            Exception: If template rendering fails.
        """
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise

        variables = self.load_variables(device_name)
        if extra_vars:
            variables.update(extra_vars)

        # Ensure hostname is set
        if "hostname" not in variables:
            variables["hostname"] = device_name

        logger.info(f"Generating config for {device_name} using {template_name}")
        config = template.render(**variables)
        return config

    def generate_batch(
        self,
        devices: list[str],
        template_name: str,
    ) -> dict[str, str]:
        """Generate configurations for multiple devices.

        Args:
            devices: List of device hostnames.
            template_name: Jinja2 template path.

        Returns:
            Dictionary mapping device names to generated configs.
        """
        results: dict[str, str] = {}
        for device in devices:
            try:
                config = self.generate(device, template_name)
                results[device] = config
                logger.info(f"Generated config for {device}")
            except Exception as e:
                logger.error(f"Failed to generate config for {device}: {e}")
                results[device] = ""
        return results

    def save(self, config: str, output_path: str | Path) -> Path:
        """Save generated configuration to a file.

        Args:
            config: Configuration string to save.
            output_path: Output file path.

        Returns:
            Path to the saved file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(config)

        logger.info(f"Configuration saved to {output_path}")
        return output_path

    def diff(
        self,
        current_config: str,
        new_config: str,
        context_lines: int = 3,
    ) -> str:
        """Generate a unified diff between two configurations.

        Args:
            current_config: Current running configuration.
            new_config: New generated configuration.
            context_lines: Number of context lines around changes.

        Returns:
            Unified diff string.
        """
        import difflib

        current_lines = current_config.splitlines(keepends=True)
        new_lines = new_config.splitlines(keepends=True)

        diff = difflib.unified_diff(
            current_lines,
            new_lines,
            fromfile="current",
            tofile="generated",
            n=context_lines,
        )
        return "".join(diff)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate network configurations")
    parser.add_argument("--device", required=True, help="Device hostname")
    parser.add_argument("--template", required=True, help="Template path")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--templates-dir", default="./templates", help="Templates dir")
    args = parser.parse_args()

    gen = ConfigGenerator(templates_dir=args.templates_dir)
    config = gen.generate(args.device, args.template)
    output_file = Path(args.output) / f"{args.device}.cfg"
    gen.save(config, output_file)
    print(f"Configuration saved to {output_file}")
