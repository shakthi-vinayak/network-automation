output "vpc_id" {
  description = "AWS VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_public_ips" {
  description = "Elastic IPs used by NAT gateways"
  value       = aws_eip.nat[*].public_ip
}

output "transit_gateway_id" {
  description = "Transit Gateway ID (if enabled)"
  value       = var.enable_transit_gateway ? aws_ec2_transit_gateway.main[0].id : null
}

output "management_sg_id" {
  description = "Management security group ID"
  value       = aws_security_group.management.id
}
