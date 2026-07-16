#!/usr/bin/env bash
# --------------------------------------------------------------------------
# validate_inventory.sh
# Validates the Ansible inventory against JSON schemas using check-jsonschema.
# --------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCHEMAS_DIR="${PROJECT_ROOT}/schemas"
INVENTORIES_DIR="${PROJECT_ROOT}/inventories"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo " Network Automation Inventory Validator"
echo "========================================"
echo ""

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 is required but not installed.${NC}"
    exit 1
fi

# Install check-jsonschema if not present
pip install -q check-jsonschema 2>/dev/null || true

SCHEMA_FILE="${SCHEMAS_DIR}/inventory.json"
if [[ ! -f "$SCHEMA_FILE" ]]; then
    echo -e "${RED}ERROR: Schema file not found: ${SCHEMA_FILE}${NC}"
    exit 1
fi

ERRORS=0
TOTAL=0

for env_dir in "${INVENTORIES_DIR}"/*/; do
    env_name=$(basename "$env_dir")
    for inv_file in "${env_dir}"*.yml "${env_dir}"*.yaml; do
        [[ -f "$inv_file" ]] || continue
        TOTAL=$((TOTAL + 1))
        echo -n "Validating ${env_name}/$(basename "$inv_file")... "
        if check-jsonschema --schemafile "$SCHEMA_FILE" "$inv_file" 2>/dev/null; then
            echo -e "${GREEN}PASS${NC}"
        else
            echo -e "${RED}FAIL${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    done
done

echo ""
echo "========================================"
echo " Results: ${TOTAL} validated, ${ERRORS} failed"
echo "========================================"

if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}Validation FAILED — ${ERRORS} inventory file(s) have errors.${NC}"
    exit 1
else
    echo -e "${GREEN}All inventory files passed validation.${NC}"
    exit 0
fi
