# Firewall Rules Compliance Policies
# =====================================
# OPA policies specifically for firewall rule validation and compliance.

package network.firewall

import future.keywords.if
import future.keywords.contains

# -------------------------------------------------------
# No "any-any-allow" rules without explicit approval
# -------------------------------------------------------
deny contains msg if {
    rule := input.firewall_rules[_]
    rule.source_addresses[_] == "any"
    rule.destination_addresses[_] == "any"
    rule.action == "allow"
    not rule.exception_approved
    msg := sprintf("CRITICAL: Rule '%s' is any-to-any allow without approval", [rule.name])
}

# -------------------------------------------------------
# Allow rules from untrusted zones must have logging
# -------------------------------------------------------
deny contains msg if {
    rule := input.firewall_rules[_]
    rule.action == "allow"
    rule.source_zone in {"untrust", "outside", "internet", "dmz"}
    not rule.logging
    msg := sprintf("HIGH: Rule '%s' allows traffic from %s without logging", [rule.name, rule.source_zone])
}

# -------------------------------------------------------
# Deny rules should not use "any" port
# -------------------------------------------------------
deny contains msg if {
    rule := input.firewall_rules[_]
    rule.action == "deny"
    rule.ports[_] == "any"
    msg := sprintf("MEDIUM: Deny rule '%s' uses 'any' port — specify explicit ports", [rule.name])
}

# -------------------------------------------------------
# No rules using deprecated protocols
# -------------------------------------------------------
DENIED_PROTOCOLS := {"telnet", "ftp", "tftp", "rsh", "rlogin"}

deny contains msg if {
    rule := input.firewall_rules[_]
    proto := rule.applications[_]
    lower(proto) in DENIED_PROTOCOLS
    rule.action == "allow"
    msg := sprintf("HIGH: Rule '%s' allows deprecated protocol '%s'", [rule.name, proto])
}

# -------------------------------------------------------
# Shadow rule detection (basic)
# -------------------------------------------------------
warnings contains msg if {
    rule_a := input.firewall_rules[i]
    rule_b := input.firewall_rules[j]
    i < j
    rule_a.action != rule_b.action
    rule_a.source_addresses[_] == rule_b.source_addresses[_]
    rule_a.destination_addresses[_] == rule_b.destination_addresses[_]
    msg := sprintf("WARNING: Rule '%s' may shadow or conflict with '%s'", [rule_b.name, rule_a.name])
}

# -------------------------------------------------------
# Maximum rule count per firewall
# -------------------------------------------------------
MAX_RULES := 500

warnings contains msg if {
    count(input.firewall_rules) > MAX_RULES
    msg := sprintf("WARNING: %s has %d rules — exceeds recommended maximum of %d", [input.device_name, count(input.firewall_rules), MAX_RULES])
}
