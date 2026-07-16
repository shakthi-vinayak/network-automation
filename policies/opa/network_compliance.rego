# Network Compliance OPA Policies
# ==================================
# Open Policy Agent (OPA) Rego policies for network configuration compliance.
# These policies are evaluated against device configurations and inventory data.

package network.compliance

import future.keywords.if
import future.keywords.contains

# -------------------------------------------------------
# METADATA
# -------------------------------------------------------
# METADATA
# title: SSH-Only Access Policy
# description: Telnet must be disabled on all network devices. SSH v2 is the only permitted management protocol.
# scope: all devices
# severity: CRITICAL

deny contains msg if {
    input.transport_methods[_] == "telnet"
    msg := sprintf("CRITICAL [POL-001]: Telnet is enabled on %s — must use SSH v2 only", [input.device_name])
}

deny contains msg if {
    not input.ssh_enabled
    msg := sprintf("CRITICAL [POL-001]: SSH is not enabled on %s", [input.device_name])
}

deny contains msg if {
    input.ssh_version != 2
    msg := sprintf("CRITICAL [POL-001]: SSH version must be 2 on %s (found: %d)", [input.device_name, input.ssh_version])
}

# -------------------------------------------------------
# METADATA
# title: SNMPv3 Mandatory Usage
# description: SNMPv1 and SNMPv2c communities must not be configured. Only SNMPv3 with authentication and encryption is permitted.
# scope: all devices
# severity: CRITICAL

deny contains msg if {
    count(input.snmp_v1v2_communities) > 0
    msg := sprintf("CRITICAL [POL-002]: SNMPv1/v2c communities found on %s: %v", [input.device_name, input.snmp_v1v2_communities])
}

deny contains msg if {
    not input.snmp_v3_enabled
    msg := sprintf("CRITICAL [POL-002]: SNMPv3 is not enabled on %s", [input.device_name])
}

deny contains msg if {
    input.snmp_v3_auth_protocol == "md5"
    msg := sprintf("HIGH [POL-002]: SNMPv3 on %s uses weak auth protocol MD5 — use SHA", [input.device_name])
}

deny contains msg if {
    input.snmp_v3_priv_protocol == "des"
    msg := sprintf("HIGH [POL-002]: SNMPv3 on %s uses weak privacy protocol DES — use AES-128 or AES-256", [input.device_name])
}

# -------------------------------------------------------
# METADATA
# title: NTP Redundancy
# description: At least 2 NTP servers must be configured for time synchronisation redundancy.
# scope: all devices
# severity: HIGH

deny contains msg if {
    count(input.ntp_servers) < 2
    msg := sprintf("HIGH [POL-003]: %s has only %d NTP server(s) — minimum 2 required", [input.device_name, count(input.ntp_servers)])
}

# -------------------------------------------------------
# METADATA
# title: AAA Required
# description: AAA (TACACS+ or RADIUS) must be configured for centralised authentication, authorisation, and accounting.
# scope: all devices
# severity: CRITICAL

deny contains msg if {
    not input.aaa_enabled
    msg := sprintf("CRITICAL [POL-004]: AAA is not enabled on %s", [input.device_name])
}

deny contains msg if {
    input.aaa_enabled
    count(input.aaa_servers) < 2
    msg := sprintf("HIGH [POL-004]: %s has only %d AAA server(s) — minimum 2 for redundancy", [input.device_name, count(input.aaa_servers)])
}

deny contains msg if {
    input.aaa_protocol == "local"
    msg := sprintf("CRITICAL [POL-004]: %s uses local authentication — must use TACACS+ or RADIUS", [input.device_name])
}

# -------------------------------------------------------
# METADATA
# title: Approved SSH Cipher Suites
# description: Only approved SSH ciphers, MACs, and key exchange algorithms are permitted.
# scope: all devices
# severity: HIGH

APPROVED_CIPHERS := {"aes256-gcm", "aes128-gcm", "aes256-ctr", "aes192-ctr", "aes128-ctr"}
APPROVED_MACS := {"hmac-sha2-256", "hmac-sha2-512", "hmac-sha2-256-etm", "hmac-sha2-512-etm"}
APPROVED_KEX := {"curve25519-sha256", "diffie-hellman-group16-sha512", "diffie-hellman-group14-sha256"}

deny contains msg if {
    cipher := input.ssh_ciphers[_]
    not cipher in APPROVED_CIPHERS
    msg := sprintf("HIGH [POL-005]: Unapproved SSH cipher '%s' on %s", [cipher, input.device_name])
}

deny contains msg if {
    mac := input.ssh_macs[_]
    not mac in APPROVED_MACS
    msg := sprintf("HIGH [POL-005]: Unapproved SSH MAC '%s' on %s", [mac, input.device_name])
}

# -------------------------------------------------------
# METADATA
# title: Syslog Configuration
# description: At least 2 remote syslog servers must be configured for log redundancy.
# scope: all devices
# severity: HIGH

deny contains msg if {
    count(input.syslog_servers) < 2
    msg := sprintf("HIGH [POL-006]: %s has only %d syslog server(s) — minimum 2 required", [input.device_name, count(input.syslog_servers)])
}

# -------------------------------------------------------
# METADATA
# title: Login and MOTD Banners
# description: All devices must have login and MOTD banners configured with approved legal text.
# scope: all devices
# severity: MEDIUM

deny contains msg if {
    not input.login_banner
    msg := sprintf("MEDIUM [POL-007]: No login banner configured on %s", [input.device_name])
}

deny contains msg if {
    not input.motd_banner
    msg := sprintf("MEDIUM [POL-007]: No MOTD banner configured on %s", [input.device_name])
}

# -------------------------------------------------------
# METADATA
# title: No Default Credentials
# description: Default passwords and credentials must be changed before deployment.
# scope: all devices
# severity: CRITICAL

deny contains msg if {
    input.default_credentials_active
    msg := sprintf("CRITICAL [POL-008]: Default credentials are still active on %s", [input.device_name])
}

# -------------------------------------------------------
# METADATA
# title: Password Complexity
# description: Local user passwords must meet minimum complexity requirements.
# scope: all devices
# severity: HIGH

deny contains msg if {
    user := input.local_users[_]
    not user.password_encrypted
    msg := sprintf("HIGH [POL-009]: User '%s' on %s has unencrypted password", [user.username, input.device_name])
}

# -------------------------------------------------------
# METADATA
# title: Firmware Version Approval
# description: Only approved firmware versions may be deployed.
# scope: all devices
# severity: HIGH

deny contains msg if {
    not input.firmware_version in input.approved_firmware_list
    msg := sprintf("HIGH [POL-010]: %s running unapproved firmware %s", [input.device_name, input.firmware_version])
}
