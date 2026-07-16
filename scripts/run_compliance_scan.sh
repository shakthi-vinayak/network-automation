#!/usr/bin/env bash
# --------------------------------------------------------------------------
# run_compliance_scan.sh
# Runs OPA compliance policies against device configurations.
# --------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
POLICIES_DIR="${PROJECT_ROOT}/policies/opa"
OUTPUT_DIR="${PROJECT_ROOT}/reports/compliance"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo " Network Compliance Scan (OPA)"
echo "========================================"
echo ""

# Check OPA is installed
if ! command -v opa &> /dev/null; then
    echo -e "${RED}ERROR: Open Policy Agent (opa) is required but not installed.${NC}"
    echo "Install from: https://www.openpolicyagent.org/docs/latest/#running-opa"
    exit 1
fi

# Validate input
INPUT_FILE="${1:-}"
if [[ -z "$INPUT_FILE" ]]; then
    echo "Usage: $0 <input.json>"
    echo ""
    echo "  input.json — JSON file containing device configuration data"
    echo "               to evaluate against compliance policies."
    echo ""
    echo "Example:"
    echo "  $0 examples/device_compliance_input.json"
    exit 1
fi

if [[ ! -f "$INPUT_FILE" ]]; then
    echo -e "${RED}ERROR: Input file not found: ${INPUT_FILE}${NC}"
    exit 1
fi

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
REPORT_FILE="${OUTPUT_DIR}/compliance_report_${TIMESTAMP}.json"

echo "Policies: ${POLICIES_DIR}"
echo "Input:    ${INPUT_FILE}"
echo "Report:   ${REPORT_FILE}"
echo ""

# Run OPA evaluation
echo "Running compliance evaluation..."
opa eval \
    --data "${POLICIES_DIR}/network_compliance.rego" \
    --data "${POLICIES_DIR}/firewall_rules.rego" \
    --input "$INPUT_FILE" \
    --format json \
    "data.network.compliance.deny" \
    > "$REPORT_FILE"

# Parse results
DENY_COUNT=$(python3 -c "
import json, sys
with open('${REPORT_FILE}') as f:
    data = json.load(f)
results = data.get('result', [{}])[0].get('expressions', [{}])[0].get('value', [])
print(len(results) if isinstance(results, list) else 0)
")

echo ""
echo "========================================"
if [[ "$DENY_COUNT" -gt 0 ]]; then
    echo -e " Result: ${RED}${DENY_COUNT} violation(s) found${NC}"
    echo ""
    echo "Violations:"
    python3 -c "
import json
with open('${REPORT_FILE}') as f:
    data = json.load(f)
results = data.get('result', [{}])[0].get('expressions', [{}])[0].get('value', [])
for v in results:
    print(f'  - {v}')
"
    exit 1
else
    echo -e " Result: ${GREEN}COMPLIANT — no violations${NC}"
    exit 0
fi
