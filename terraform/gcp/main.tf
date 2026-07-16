# -----------------------------------------------------------------------------
# GCP VPC Networking — Enterprise Network Automation Platform
# -----------------------------------------------------------------------------
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.10"
    }
  }

  backend "gcs" {
    bucket = "terraform-state-network-automation"
    prefix = "gcp-networking"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# -----------------------------------------------------------------------------
# VPC Network
# -----------------------------------------------------------------------------
resource "google_compute_network" "main" {
  name                    = "vpc-${var.project_name}-${var.environment}"
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
  description             = "Enterprise network automation VPC — ${var.environment}"
}

# -----------------------------------------------------------------------------
# Subnets
# -----------------------------------------------------------------------------
resource "google_compute_subnetwork" "management" {
  name          = "snet-management-${var.gcp_region}"
  ip_cidr_range = var.subnet_management_cidr
  region        = var.gcp_region
  network       = google_compute_network.main.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "transit" {
  name          = "snet-transit-${var.gcp_region}"
  ip_cidr_range = var.subnet_transit_cidr
  region        = var.gcp_region
  network       = google_compute_network.main.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 1.0
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "workload" {
  name          = "snet-workload-${var.gcp_region}"
  ip_cidr_range = var.subnet_workload_cidr
  region        = var.gcp_region
  network       = google_compute_network.main.id

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.secondary_pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.secondary_services_cidr
  }

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# -----------------------------------------------------------------------------
# Firewall Rules
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "allow_ssh_management" {
  name    = "fw-allow-ssh-management"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = [var.management_cidr]
  target_tags   = ["management"]
  direction     = "INGRESS"
  priority      = 100
  description   = "Allow SSH from management networks"
}

resource "google_compute_firewall" "allow_netconf" {
  name    = "fw-allow-netconf"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["830"]
  }

  source_ranges = [var.management_cidr]
  target_tags   = ["management"]
  direction     = "INGRESS"
  priority      = 110
  description   = "Allow NETCONF from management networks"
}

resource "google_compute_firewall" "allow_restconf" {
  name    = "fw-allow-restconf"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["443", "8443"]
  }

  source_ranges = [var.management_cidr]
  target_tags   = ["management"]
  direction     = "INGRESS"
  priority      = 120
  description   = "Allow RESTCONF from management networks"
}

resource "google_compute_firewall" "allow_icmp" {
  name    = "fw-allow-icmp-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_management_cidr, var.subnet_transit_cidr, var.subnet_workload_cidr]
  direction     = "INGRESS"
  priority      = 200
  description   = "Allow ICMP within VPC for monitoring"
}

resource "google_compute_firewall" "deny_all_ingress" {
  name    = "fw-deny-all-ingress"
  network = google_compute_network.main.name

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
  direction     = "INGRESS"
  priority      = 65534
  description   = "Default deny all ingress"
}

# -----------------------------------------------------------------------------
# Cloud Router and Cloud NAT
# -----------------------------------------------------------------------------
resource "google_compute_router" "main" {
  name    = "router-${var.project_name}-${var.environment}"
  network = google_compute_network.main.name
  region  = var.gcp_region

  bgp {
    asn = var.cloud_router_asn
  }
}

resource "google_compute_router_nat" "main" {
  name                               = "nat-${var.project_name}-${var.environment}"
  router                             = google_compute_router.main.name
  region                             = var.gcp_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.workload.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# -----------------------------------------------------------------------------
# Cloud VPN (optional site-to-site)
# -----------------------------------------------------------------------------
resource "google_compute_ha_vpn_gateway" "main" {
  count   = var.enable_vpn ? 1 : 0
  name    = "vpn-${var.project_name}-${var.environment}"
  network = google_compute_network.main.id
  region  = var.gcp_region
}

resource "google_compute_external_vpn_gateway" "peer" {
  count           = var.enable_vpn ? 1 : 0
  name            = "ext-vpn-peer-${var.environment}"
  redundancy_type = "SINGLE_IP_INTERNALLY_REDUNDANT"

  interface {
    id         = 0
    ip_address = var.vpn_peer_ip
  }
}

# -----------------------------------------------------------------------------
# Private Service Connect (optional)
# -----------------------------------------------------------------------------
resource "google_compute_global_address" "psc" {
  count        = var.enable_psc ? 1 : 0
  name         = "psc-${var.project_name}-${var.environment}"
  address_type = "INTERNAL"
  ip_version   = "IPV4"
}
