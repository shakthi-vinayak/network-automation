# OPA Policy Tests
# =================
# Tests for network compliance Rego policies.
# Run with: opa test . -v

package network.compliance

import data.network.compliance as policy

# -------------------------------------------------------
# SSH-Only Policy Tests
# -------------------------------------------------------
test_deny_telnet_enabled if {
    count(policy.deny) > 0 with input as {
        "device_name": "test-rtr-01",
        "transport_methods": ["ssh", "telnet"],
        "ssh_enabled": true,
        "ssh_version": 2,
        "snmp_v3_enabled": true,
        "snmp_v1v2_communities": [],
        "ntp_servers": ["10.0.0.1", "10.0.0.2"],
        "aaa_enabled": true,
        "aaa_servers": ["10.0.0.20", "10.0.0.21"],
        "syslog_servers": [{"host": "10.0.0.10"}, {"host": "10.0.0.11"}],
        "login_banner": "Authorized",
        "motd_banner": "Lab",
        "ssh_ciphers": ["aes256-gcm"],
        "ssh_macs": ["hmac-sha2-256"],
    }
}

test_allow_ssh_only if {
    count(policy.deny) == 0 with input as {
        "device_name": "test-rtr-01",
        "transport_methods": ["ssh"],
        "ssh_enabled": true,
        "ssh_version": 2,
        "snmp_v3_enabled": true,
        "snmp_v3_auth_protocol": "sha",
        "snmp_v3_priv_protocol": "aes-256",
        "snmp_v1v2_communities": [],
        "ntp_servers": ["10.0.0.1", "10.0.0.2"],
        "aaa_enabled": true,
        "aaa_servers": ["10.0.0.20", "10.0.0.21"],
        "syslog_servers": [{"host": "10.0.0.10"}, {"host": "10.0.0.11"}],
        "login_banner": "Authorized Access Only",
        "motd_banner": "Network Lab",
        "ssh_ciphers": ["aes256-gcm", "aes128-gcm"],
        "ssh_macs": ["hmac-sha2-256", "hmac-sha2-512"],
        "default_credentials_active": false,
        "local_users": [],
    }
}

# -------------------------------------------------------
# SNMPv3 Policy Tests
# -------------------------------------------------------
test_deny_snmp_v2c_community if {
    count(policy.deny) > 0 with input as {
        "device_name": "test-fw-01",
        "transport_methods": ["ssh"],
        "ssh_enabled": true,
        "ssh_version": 2,
        "snmp_v3_enabled": true,
        "snmp_v3_auth_protocol": "sha",
        "snmp_v3_priv_protocol": "aes-128",
        "snmp_v1v2_communities": [{"name": "public", "version": "v2c"}],
        "ntp_servers": ["10.0.0.1", "10.0.0.2"],
        "aaa_enabled": true,
        "aaa_servers": ["10.0.0.20", "10.0.0.21"],
        "syslog_servers": [{"host": "10.0.0.10"}, {"host": "10.0.0.11"}],
        "login_banner": "Authorized",
        "motd_banner": "Lab",
        "ssh_ciphers": ["aes256-gcm"],
        "ssh_macs": ["hmac-sha2-256"],
    }
}

# -------------------------------------------------------
# NTP Redundancy Tests
# -------------------------------------------------------
test_deny_single_ntp if {
    count(policy.deny) > 0 with input as {
        "device_name": "test-sw-01",
        "transport_methods": ["ssh"],
        "ssh_enabled": true,
        "ssh_version": 2,
        "snmp_v3_enabled": true,
        "snmp_v1v2_communities": [],
        "ntp_servers": ["10.0.0.1"],
        "aaa_enabled": true,
        "aaa_servers": ["10.0.0.20", "10.0.0.21"],
        "syslog_servers": [{"host": "10.0.0.10"}, {"host": "10.0.0.11"}],
        "login_banner": "Authorized",
        "motd_banner": "Lab",
        "ssh_ciphers": ["aes256-gcm"],
        "ssh_macs": ["hmac-sha2-256"],
    }
}

# -------------------------------------------------------
# Approved Ciphers Tests
# -------------------------------------------------------
test_deny_weak_cipher if {
    count(policy.deny) > 0 with input as {
        "device_name": "test-rtr-02",
        "transport_methods": ["ssh"],
        "ssh_enabled": true,
        "ssh_version": 2,
        "snmp_v3_enabled": true,
        "snmp_v1v2_communities": [],
        "ntp_servers": ["10.0.0.1", "10.0.0.2"],
        "aaa_enabled": true,
        "aaa_servers": ["10.0.0.20", "10.0.0.21"],
        "syslog_servers": [{"host": "10.0.0.10"}, {"host": "10.0.0.11"}],
        "login_banner": "Authorized",
        "motd_banner": "Lab",
        "ssh_ciphers": ["aes256-gcm", "3des-cbc"],
        "ssh_macs": ["hmac-sha2-256"],
    }
}
