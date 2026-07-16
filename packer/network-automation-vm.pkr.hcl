# -----------------------------------------------------------------------------
# Packer — Network Automation Tooling VM Image
# -----------------------------------------------------------------------------
# Builds a pre-configured VM image with all network automation tools installed.
# Use: packer build packer/network-automation-vm.pkr.hcl
# -----------------------------------------------------------------------------

packer {
  required_plugins {
    amazon = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t3.medium"
}

variable "ami_name_prefix" {
  type    = string
  default = "network-automation"
}

locals {
  ami_name = "${var.ami_name_prefix}-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  tags = {
    Name        = local.ami_name
    Project     = "network-automation"
    ManagedBy   = "packer"
    Environment = "shared"
  }
}

source "amazon-ebs" "netauto" {
  ami_name      = local.ami_name
  instance_type = var.instance_type
  region        = var.aws_region

  source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["099720109477"]  # Canonical
  }

  ssh_username = "ubuntu"

  launch_block_device_mappings {
    device_name           = "/dev/sda1"
    volume_size           = 50
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = local.tags
}

build {
  sources = ["source.amazon-ebs.netauto"]

  # -- System updates -------------------------------------------------------
  provisioner "shell" {
    inline = [
      "sudo apt-get update -y",
      "sudo apt-get upgrade -y",
      "sudo apt-get install -y python3 python3-pip python3-venv git curl wget unzip jq",
    ]
  }

  # -- Ansible --------------------------------------------------------------
  provisioner "shell" {
    inline = [
      "sudo apt-get install -y software-properties-common",
      "sudo apt-add-repository --yes --update ppa:ansible/ansible",
      "sudo apt-get install -y ansible",
    ]
  }

  # -- Python dependencies ---------------------------------------------------
  provisioner "shell" {
    inline = [
      "pip3 install --user --upgrade pip",
      "pip3 install --user ansible-core netmiko napalm nornir jinja2 pyyaml",
      "pip3 install --user paramiko textfsm genie pyats",
      "pip3 install --user fastapi uvicorn httpx",
      "pip3 install --user pytest pytest-cov flake8 black isort mypy",
    ]
  }

  # -- Terraform ------------------------------------------------------------
  provisioner "shell" {
    inline = [
      "curl -fsSL https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip -o /tmp/terraform.zip",
      "unzip /tmp/terraform.zip -d /tmp",
      "sudo mv /tmp/terraform /usr/local/bin/",
      "terraform version",
    ]
  }

  # -- Open Policy Agent -----------------------------------------------------
  provisioner "shell" {
    inline = [
      "curl -L -o /tmp/opa https://openpolicyagent.org/downloads/v0.60.0/opa_linux_amd64_static",
      "chmod +x /tmp/opa",
      "sudo mv /tmp/opa /usr/local/bin/",
      "opa version",
    ]
  }

  # -- Batfish ---------------------------------------------------------------
  provisioner "shell" {
    inline = [
      "pip3 install --user pybatfish",
    ]
  }

  # -- Clone project repo (optional) ----------------------------------------
  provisioner "shell" {
    inline = [
      "mkdir -p /home/ubuntu/network-automation",
      "echo 'Clone your network-automation repo here after boot.'",
    ]
  }

  # -- Cleanup ---------------------------------------------------------------
  provisioner "shell" {
    inline = [
      "sudo apt-get autoremove -y",
      "sudo apt-get clean",
      "rm -rf /tmp/*",
    ]
  }
}
