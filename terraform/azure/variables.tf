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

variable "azure_region" {
  description = "Azure region for resource deployment"
  type        = string
  default     = "eastus"
}

variable "vnet_address_space" {
  description = "CIDR blocks for the virtual network"
  type        = list(string)
  default     = ["10.100.0.0/16"]
}

variable "subnet_management_cidr" {
  description = "CIDR block for the management subnet"
  type        = string
  default     = "10.100.1.0/24"
}

variable "subnet_transit_cidr" {
  description = "CIDR block for the transit subnet"
  type        = string
  default     = "10.100.2.0/24"
}

variable "subnet_workload_cidr" {
  description = "CIDR block for the workload subnet"
  type        = string
  default     = "10.100.10.0/24"
}

variable "subnet_firewall_cidr" {
  description = "CIDR block for the Azure Firewall subnet (must be /26 or larger)"
  type        = string
  default     = "10.100.3.0/26"
}

variable "management_cidr" {
  description = "Allowed source CIDR for management access"
  type        = string
  default     = "10.0.0.0/8"
}

variable "firewall_private_ip" {
  description = "Private IP address of the firewall/NVA for default route"
  type        = string
  default     = "10.100.3.4"
}

variable "enable_virtual_wan" {
  description = "Enable Azure Virtual WAN hub-and-spoke topology"
  type        = bool
  default     = false
}

variable "hub_address_prefix" {
  description = "Address prefix for Virtual WAN hub"
  type        = string
  default     = "10.200.0.0/23"
}
