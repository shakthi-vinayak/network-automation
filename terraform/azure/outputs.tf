output "resource_group_name" {
  description = "Azure resource group name"
  value       = azurerm_resource_group.main.name
}

output "vnet_id" {
  description = "Virtual network resource ID"
  value       = azurerm_virtual_network.main.id
}

output "vnet_address_space" {
  description = "VNet address space"
  value       = azurerm_virtual_network.main.address_space
}

output "management_subnet_id" {
  description = "Management subnet resource ID"
  value       = azurerm_subnet.management.id
}

output "transit_subnet_id" {
  description = "Transit subnet resource ID"
  value       = azurerm_subnet.transit.id
}

output "workload_subnet_id" {
  description = "Workload subnet resource ID"
  value       = azurerm_subnet.workload.id
}

output "firewall_public_ip" {
  description = "Azure Firewall public IP address"
  value       = azurerm_public_ip.firewall.ip_address
}

output "firewall_id" {
  description = "Azure Firewall resource ID"
  value       = azurerm_firewall.main.id
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace resource ID"
  value       = azurerm_log_analytics_workspace.main.id
}
