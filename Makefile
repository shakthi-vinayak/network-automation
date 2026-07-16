# ===========================================================================
# Network Automation Platform — Makefile
# ===========================================================================
# Usage:
#   make help            Show all available targets
#   make setup           Install dependencies and pre-commit hooks
#   make validate        Run all validation checks
#   make test            Run unit tests with coverage
#   make compliance      Run OPA compliance scan
#   make configs         Generate device configurations
#   make lint            Run all linters
#   make clean           Clean generated files and caches
# ===========================================================================

.PHONY: help setup validate test compliance configs lint clean

PYTHON := python3
PIP := pip3
PROJECT_ROOT := $(shell pwd)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install Python deps, Ansible collections, and pre-commit hooks
	$(PIP) install -r requirements.txt
	ansible-galaxy collection install -r requirements.yml
	pre-commit install
	@echo "Setup complete."

validate: ## Validate inventories, schemas, and templates
	bash scripts/validate_inventory.sh
	$(PYTHON) -m schemas.validate_all

test: ## Run unit tests with coverage
	$(PYTHON) -m pytest tests/unit -v --cov=python --cov=bots --cov-report=term-missing --cov-report=html:reports/coverage

test-integration: ## Run integration tests (requires lab devices)
	$(PYTHON) -m pytest tests/integration -v --tb=short

compliance: ## Run OPA compliance scan against example input
	bash scripts/run_compliance_scan.sh examples/device_compliance_input.json

compliance-test: ## Run OPA policy unit tests
	opa test policies/opa/ -v

configs: ## Generate device configurations from templates
	bash scripts/generate_configs.sh

lint: ## Run all linters (ansible-lint, yamllint, flake8, black, isort)
	ansible-lint
	yamllint .
	$(PYTHON) -m flake8 python/ bots/ tests/
	$(PYTHON) -m black --check python/ bots/ tests/
	$(PYTHON) -m isort --check-only python/ bots/ tests/

format: ## Auto-format Python code (black + isort)
	$(PYTHON) -m black python/ bots/ tests/
	$(PYTHON) -m isort python/ bots/ tests/

molecule: ## Run Molecule tests for Ansible roles
	molecule test -s default --base-config tests/molecule/common/default/molecule.yml

terraform-plan: ## Run Terraform plan for all cloud providers
	cd terraform/aws && terraform init && terraform plan
	cd terraform/azure && terraform init && terraform plan
	cd terraform/gcp && terraform init && terraform plan

bots: ## Start all automation bots
	$(PYTHON) -m bots.firewall_bot.firewall_bot &
	$(PYTHON) -m bots.vlan_bot.vlan_bot &
	$(PYTHON) -m bots.port_bot.port_bot &
	$(PYTHON) -m bots.backup_bot.backup_bot &
	$(PYTHON) -m bots.health_bot.health_bot &
	$(PYTHON) -m bots.compliance_bot.compliance_bot &
	$(PYTHON) -m bots.rollback_bot.rollback_bot &
	@echo "All bots started on ports 8101-8107."

clean: ## Remove generated files, caches, and build artifacts
	rm -rf output/ reports/ .pytest_cache/ htmlcov/
	rm -rf **/__pycache__ **/*.pyc
	rm -rf .molecule/
	find . -name "*.retry" -delete
	@echo "Clean complete."
