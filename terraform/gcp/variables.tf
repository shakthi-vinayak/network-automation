variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "netauto"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for resource deployment"
  type        = string
  default     = "us-east1"
}

variable "subnet_management_cidr" {
  description = "CIDR block for management subnet"
  type        = string
  default     = "10.200.1.0/24"
}

variable "subnet_transit_cidr" {
  description = "CIDR block for transit subnet"
  type        = string
  default     = "10.200.2.0/24"
}

variable "subnet_workload_cidr" {
  description = "CIDR block for workload subnet"
  type        = string
  default     = "10.200.10.0/24"
}

variable "secondary_pods_cidr" {
  description = "Secondary CIDR for GKE pods"
  type        = string
  default     = "172.16.0.0/16"
}

variable "secondary_services_cidr" {
  description = "Secondary CIDR for GKE services"
  type        = string
  default     = "172.17.0.0/20"
}

variable "management_cidr" {
  description = "Allowed source CIDR for management access"
  type        = string
  default     = "10.0.0.0/8"
}

variable "cloud_router_asn" {
  description = "BGP ASN for Cloud Router"
  type        = number
  default     = 65001
}

variable "enable_vpn" {
  description = "Enable Cloud VPN gateway"
  type        = bool
  default     = false
}

variable "vpn_peer_ip" {
  description = "Peer VPN gateway public IP"
  type        = string
  default     = "0.0.0.0"
}

variable "enable_psc" {
  description = "Enable Private Service Connect"
  type        = bool
  default     = false
}
