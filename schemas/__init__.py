"""Schema validation utility for inventory, group_vars, and host_vars files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator, ValidationError


class SchemaValidator:
    """Validates YAML files against JSON schemas.

    This class provides methods to validate Ansible inventory,
    group_vars, and host_vars files against their respective schemas.

    Attributes:
        schemas_dir: Path to the directory containing JSON schema files.
    """

    def __init__(self, schemas_dir: str | Path | None = None) -> None:
        """Initialize the SchemaValidator.

        Args:
            schemas_dir: Path to the schemas directory. Defaults to ./schemas/.
        """
        if schemas_dir is None:
            schemas_dir = Path(__file__).parent.parent / "schemas"
        self.schemas_dir = Path(schemas_dir)
        self._schemas: dict[str, dict[str, Any]] = {}

    def _load_schema(self, schema_name: str) -> dict[str, Any]:
        """Load a JSON schema file.

        Args:
            schema_name: Name of the schema file (without extension).

        Returns:
            The loaded schema as a dictionary.

        Raises:
            FileNotFoundError: If the schema file does not exist.
        """
        if schema_name not in self._schemas:
            schema_path = self.schemas_dir / f"{schema_name}.json"
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
            with open(schema_path, "r", encoding="utf-8") as f:
                self._schemas[schema_name] = json.load(f)
        return self._schemas[schema_name]

    def _load_yaml(self, yaml_path: str | Path) -> Any:
        """Load a YAML file.

        Args:
            yaml_path: Path to the YAML file.

        Returns:
            The parsed YAML content.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            yaml.YAMLError: If the YAML is malformed.
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate(
        self, yaml_path: str | Path, schema_name: str
    ) -> tuple[bool, list[str]]:
        """Validate a YAML file against a schema.

        Args:
            yaml_path: Path to the YAML file to validate.
            schema_name: Name of the schema to validate against.

        Returns:
            A tuple of (is_valid, list_of_errors).
        """
        schema = self._load_schema(schema_name)
        data = self._load_yaml(yaml_path)
        validator = Draft7Validator(schema)
        errors = []

        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in error.absolute_path)
            error_msg = f"[{path}] {error.message}" if path else error.message
            errors.append(error_msg)

        return len(errors) == 0, errors

    def validate_inventory(self, yaml_path: str | Path) -> tuple[bool, list[str]]:
        """Validate an inventory file.

        Args:
            yaml_path: Path to the inventory YAML file.

        Returns:
            A tuple of (is_valid, list_of_errors).
        """
        return self.validate(yaml_path, "inventory")

    def validate_group_vars(self, yaml_path: str | Path) -> tuple[bool, list[str]]:
        """Validate a group_vars file.

        Args:
            yaml_path: Path to the group_vars YAML file.

        Returns:
            A tuple of (is_valid, list_of_errors).
        """
        return self.validate(yaml_path, "group_vars")

    def validate_host_vars(self, yaml_path: str | Path) -> tuple[bool, list[str]]:
        """Validate a host_vars file.

        Args:
            yaml_path: Path to the host_vars YAML file.

        Returns:
            A tuple of (is_valid, list_of_errors).
        """
        return self.validate(yaml_path, "host_vars")

    def validate_all(
        self, base_path: str | Path | None = None
    ) -> dict[str, tuple[bool, list[str]]]:
        """Validate all inventory, group_vars, and host_vars files.

        Args:
            base_path: Base path to search for YAML files. Defaults to project root.

        Returns:
            A dictionary mapping file paths to their validation results.
        """
        if base_path is None:
            base_path = Path(__file__).parent.parent
        base_path = Path(base_path)

        results: dict[str, tuple[bool, list[str]]] = {}

        # Validate inventories
        for inv_file in base_path.glob("inventories/**/hosts.yml"):
            results[str(inv_file)] = self.validate_inventory(inv_file)

        # Validate group_vars
        for gv_file in base_path.glob("group_vars/**/*.yml"):
            results[str(gv_file)] = self.validate_group_vars(gv_file)

        # Validate host_vars
        for hv_file in base_path.glob("host_vars/**/*.yml"):
            results[str(hv_file)] = self.validate_host_vars(hv_file)

        return results


def main() -> int:
    """Run schema validation from the command line.

    Returns:
        Exit code: 0 for success, 1 for validation errors.
    """
    validator = SchemaValidator()
    results = validator.validate_all()

    has_errors = False
    for filepath, (is_valid, errors) in results.items():
        if is_valid:
            print(f"PASS: {filepath}")
        else:
            has_errors = True
            print(f"FAIL: {filepath}")
            for error in errors:
                print(f"  - {error}")

    total = len(results)
    passed = sum(1 for v, _ in results.values() if v)
    failed = total - passed

    print(f"\nValidation complete: {passed}/{total} passed, {failed} failed")

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
