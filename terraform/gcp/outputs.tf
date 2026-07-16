output "vpc_id" {
  description = "GCP VPC network ID"
  value       = google_compute_network.main.id
}

output "vpc_name" {
  description = "GCP VPC network name"
  value       = google_compute_network.main.name
}

output "management_subnet_id" {
  description = "Management subnet ID"
  value       = google_compute_subnetwork.management.id
}

output "transit_subnet_id" {
  description = "Transit subnet ID"
  value       = google_compute_subnetwork.transit.id
}

output "workload_subnet_id" {
  description = "Workload subnet ID"
  value       = google_compute_subnetwork.workload.id
}

output "cloud_router_name" {
  description = "Cloud Router name"
  value       = google_compute_router.main.name
}

output "nat_gateway_ip" {
  description = "Cloud NAT gateway public IP (auto-assigned)"
  value       = "Auto-assigned — query via gcloud"
}

output "vpn_gateway_id" {
  description = "HA VPN gateway ID (if enabled)"
  value       = var.enable_vpn ? google_compute_ha_vpn_gateway.main[0].id : null
}
