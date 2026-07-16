#!/usr/bin/env bash
# --------------------------------------------------------------------------
# generate_configs.sh
# Generates device configurations from templates using the Python config generator.
# --------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${PROJECT_ROOT}/output/configs"

GREEN='\033[0;32m'
NC='\033[0m'

mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo " Configuration Generator"
echo "========================================"
echo ""

# Ensure dependencies
pip install -q jinja2 pyyaml 2>/dev/null || true

INVENTORY="${1:-${PROJECT_ROOT}/inventories/production/hosts.yml}"

echo "Inventory: ${INVENTORY}"
echo "Output:    ${OUTPUT_DIR}"
echo ""

python3 -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}')
from python.config_gen.config_generator import ConfigGenerator
from python.inventory.inventory_manager import InventoryManager
import yaml
import os

gen = ConfigGenerator(templates_dir='${PROJECT_ROOT}/templates')
inv = InventoryManager('${INVENTORY}')

vendor_template_map = {
    'cisco': 'cisco_ios/base_config.j2',
    'juniper': 'juniper_srx/base_config.j2',
    'arista': 'arista_eos/base_config.j2',
    'paloalto': 'paloalto/base_config.j2',
    'fortinet': 'fortinet/base_config.j2',
}

# Load global vars
group_vars = {}
gv_path = '${PROJECT_ROOT}/group_vars/all.yml'
if os.path.exists(gv_path):
    with open(gv_path) as f:
        group_vars = yaml.safe_load(f) or {}

for device in inv.devices:
    template = vendor_template_map.get(device.vendor)
    if not template:
        print(f'  SKIP: {device.name} — no template for vendor {device.vendor}')
        continue

    # Merge group vars with host vars
    vars_dict = {**group_vars}
    vars_dict['hostname'] = device.name
    vars_dict['ansible_host'] = device.ansible_host
    vars_dict['vendor'] = device.vendor
    vars_dict['platform'] = device.platform
    vars_dict['role'] = device.role
    vars_dict['region'] = device.region

    # Load host_vars if available
    hv_path = '${PROJECT_ROOT}/host_vars/' + device.name + '.yml'
    if os.path.exists(hv_path):
        with open(hv_path) as f:
            hv = yaml.safe_load(f) or {}
            vars_dict.update(hv)

    try:
        config = gen.render(template, vars_dict)
        out_file = '${OUTPUT_DIR}/' + device.name + '.cfg'
        with open(out_file, 'w') as f:
            f.write(config)
        print(f'  ${GREEN}OK${NC}: {device.name} -> {out_file}')
    except Exception as e:
        print(f'  ERROR: {device.name} — {e}')

print()
print('Configuration generation complete.')
"
