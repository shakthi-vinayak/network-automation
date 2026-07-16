"""
Firewall Bot
=============
Manages firewall rules across multi-vendor firewalls (Palo Alto, Fortinet, Cisco ASA, Juniper SRX).

Actions:
    - list_rules        : List active firewall rules on a device
    - add_rule          : Create a new firewall rule
    - remove_rule       : Delete an existing firewall rule
    - validate_rule     : Validate a rule against compliance policy
    - search_rule       : Search rules by source, destination, or port
    - bulk_import       : Import rules from a CSV/JSON file
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from bots.framework.base_bot import BaseBot, BotResponse, BotStatus

logger = logging.getLogger(__name__)


class FirewallBot(BaseBot):
    name = "firewall-bot"
    description = "Firewall rule management bot for multi-vendor environments"
    version = "1.0.0"

    SUPPORTED_VENDORS = ["paloalto", "fortinet", "cisco_asa", "juniper_srx"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._rule_store: Dict[str, List[Dict[str, Any]]] = {}

    def list_actions(self) -> List[Dict[str, str]]:
        return [
            {"name": "list_rules", "description": "List all firewall rules on a device"},
            {"name": "add_rule", "description": "Create a new firewall rule"},
            {"name": "remove_rule", "description": "Delete a firewall rule by ID"},
            {"name": "validate_rule", "description": "Validate a rule against compliance policy"},
            {"name": "search_rule", "description": "Search rules by criteria"},
            {"name": "bulk_import", "description": "Import rules from JSON payload"},
        ]

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> BotResponse:
        handlers = {
            "list_rules": self._list_rules,
            "add_rule": self._add_rule,
            "remove_rule": self._remove_rule,
            "validate_rule": self._validate_rule,
            "search_rule": self._search_rule,
            "bulk_import": self._bulk_import,
        }
        handler = handlers.get(action)
        if handler is None:
            return self._fail(f"Unknown action: {action}")
        return await handler(parameters)

    # -- action handlers ----------------------------------------------------
    async def _list_rules(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device", "unknown")
        rules = self._rule_store.get(device, [])
        return self._ok(
            f"Found {len(rules)} rules on {device}",
            data={"device": device, "rules": rules, "count": len(rules)},
        )

    async def _add_rule(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        rule = {
            "id": params.get("rule_id", f"rule-{len(self._rule_store.get(device, [])) + 1}"),
            "name": params.get("name", ""),
            "source": params.get("source_zone", "any"),
            "destination": params.get("destination_zone", "any"),
            "source_addresses": params.get("source_addresses", []),
            "destination_addresses": params.get("destination_addresses", []),
            "ports": params.get("ports", []),
            "protocol": params.get("protocol", "tcp"),
            "action": params.get("rule_action", "allow"),
            "logging": params.get("logging", True),
            "vendor": params.get("vendor", "generic"),
        }
        # Validate before creating
        validation = self._validate_rule_sync(rule)
        if not validation["valid"]:
            return self._fail(
                f"Rule failed compliance validation: {validation['violations']}",
                data={"rule": rule, "validation": validation},
            )
        self._rule_store.setdefault(device, []).append(rule)
        logger.info("Added rule %s on %s", rule["id"], device)
        return self._ok(f"Rule {rule['id']} created on {device}", data={"rule": rule})

    async def _remove_rule(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        rule_id = params.get("rule_id")
        rules = self._rule_store.get(device, [])
        self._rule_store[device] = [r for r in rules if r.get("id") != rule_id]
        return self._ok(f"Rule {rule_id} removed from {device}")

    async def _validate_rule(self, params: Dict[str, Any]) -> BotResponse:
        rule = params.get("rule", {})
        result = self._validate_rule_sync(rule)
        status = BotStatus.SUCCESS if result["valid"] else BotStatus.FAILED
        return BotResponse(
            status=status,
            message="Rule is compliant" if result["valid"] else "Rule is non-compliant",
            data=result,
        )

    async def _search_rule(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        rules = self._rule_store.get(device, [])
        criteria = {k: v for k, v in params.items() if k not in ("device",)}
        matched = [r for r in rules if all(r.get(k) == v for k, v in criteria.items() if v)]
        return self._ok(
            f"Found {len(matched)} matching rules on {device}",
            data={"matches": matched, "count": len(matched)},
        )

    async def _bulk_import(self, params: Dict[str, Any]) -> BotResponse:
        device = params.get("device")
        rules = params.get("rules", [])
        imported = 0
        errors = []
        for rule in rules:
            validation = self._validate_rule_sync(rule)
            if validation["valid"]:
                self._rule_store.setdefault(device, []).append(rule)
                imported += 1
            else:
                errors.append({"rule": rule.get("id"), "violations": validation["violations"]})
        return self._ok(
            f"Imported {imported}/{len(rules)} rules",
            data={"imported": imported, "errors": errors},
        )

    # -- helpers ------------------------------------------------------------
    def _validate_rule_sync(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        violations = []
        # Policy: no "any" action=allow from untrusted to trusted without logging
        if (
            rule.get("action") == "allow"
            and rule.get("source") in ("untrusted", "outside", "any")
            and not rule.get("logging", True)
        ):
            violations.append("Allow rule from untrusted zone must have logging enabled")
        # Policy: deny rules should not use "any" port
        if rule.get("action") == "deny" and rule.get("ports") == ["any"]:
            violations.append("Deny rules should specify explicit ports")
        # Policy: approved ports check
        approved_ports = self.config.get("approved_ports", [])
        if approved_ports and rule.get("ports"):
            unapproved = [p for p in rule["ports"] if p not in approved_ports and p != "any"]
            if unapproved:
                violations.append(f"Unapproved ports: {unapproved}")
        return {"valid": len(violations) == 0, "violations": violations}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    bot = FirewallBot()
    app = bot.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8101)
