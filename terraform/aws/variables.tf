variable "project_name" {
  description = "Project name used in resource naming and tagging"
  type        = string
  default     = "netauto"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "management_cidr" {
  description = "Allowed source CIDR for management access"
  type        = string
  default     = "10.0.0.0/8"
}

variable "availability_zones" {
  description = "AWS availability zones for subnet distribution"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "enable_transit_gateway" {
  description = "Enable AWS Transit Gateway for multi-VPC routing"
  type        = bool
  default     = true
}

variable "transit_gateway_asn" {
  description = "ASN for Transit Gateway"
  type        = number
  default     = 64512
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}
