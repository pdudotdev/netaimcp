#!/usr/bin/env bash
# aiNOC Agent Test Suite Runner
# Usage: ./run_tests.sh [unit|integration|all]
#
# unit        — no device connectivity, fast (~seconds)
# integration — read-only device queries (~1 min)
# all         — unit + integration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_DIR="${SCRIPT_DIR}"
MODE="${1:-all}"

echo "========================================"
echo " aiNOC Agent Test Suite"
echo " Mode: ${MODE}"
echo " Root: ${PROJECT_ROOT}"
echo "========================================"

# Run from project root so that all project modules are on the Python path.
# Test paths are prefixed with the relative path from the project root.
cd "${PROJECT_ROOT}"
TEST_PREFIX="testing/agent-testing"

# Use project venv python if available, otherwise fall back to system python3
VENV_PYTHON="${PROJECT_ROOT}/mcp/bin/python3"
if [[ -x "${VENV_PYTHON}" ]]; then
    PYTHON="${VENV_PYTHON}"
else
    PYTHON="python3"
fi

# Check dependencies
if ! "${PYTHON}" -c "import pytest" 2>/dev/null; then
    echo "ERROR: pytest not found. Run: pip install -r /home/mcp/aiNOC/requirements.txt"
    exit 1
fi

PASS=0
FAIL=0
ERRORS=()

run_pytest() {
    local label="$1"
    local path="$2"

    echo ""
    echo "── ${label} ────────────────────────────────"
    if "${PYTHON}" -m pytest "${path}" -v 2>&1; then
        PASS=$((PASS + 1))
        echo "  [PASS] ${label}"
    else
        FAIL=$((FAIL + 1))
        ERRORS+=("${label}")
        echo "  [FAIL] ${label}"
    fi
}

case "${MODE}" in
    unit)
        run_pytest "UT-001 SLA Patterns"        "${TEST_PREFIX}/unit/test_sla_patterns.py"
        run_pytest "UT-002 Platform Map"        "${TEST_PREFIX}/unit/test_platform_map.py"
        run_pytest "UT-003 Drain Mechanism"     "${TEST_PREFIX}/unit/test_drain_mechanism.py"
        run_pytest "UT-004 Input Validation"    "${TEST_PREFIX}/unit/test_input_validation.py"
        run_pytest "UT-006 Command Validation"  "${TEST_PREFIX}/unit/test_command_validation.py"
        run_pytest "UT-008 Risk Assessment"     "${TEST_PREFIX}/unit/test_risk_assessment.py"
        run_pytest "UT-009 Syslog Sanitize"     "${TEST_PREFIX}/unit/test_syslog_sanitize.py"
        run_pytest "UT-010 Transport Dispatch"  "${TEST_PREFIX}/unit/test_transport_dispatch.py"
        run_pytest "UT-011 RESTCONF Unit"       "${TEST_PREFIX}/unit/test_restconf_unit.py"
        run_pytest "UT-013 SSH Unit"            "${TEST_PREFIX}/unit/test_ssh_unit.py"
        run_pytest "UT-014 Config Push"         "${TEST_PREFIX}/unit/test_config_push.py"
        run_pytest "UT-015 Tool Layer"          "${TEST_PREFIX}/unit/test_tool_layer.py"
        run_pytest "UT-016 Jira Tools"          "${TEST_PREFIX}/unit/test_jira_tools.py"
        run_pytest "UT-017 Discord Approval"    "${TEST_PREFIX}/unit/test_approval.py"
        run_pytest "UT-018 Config Approval Gate" "${TEST_PREFIX}/unit/test_config_approval_gate.py"
        ;;

    integration)
        run_pytest "IT-001 MCP Connectivity"  "${TEST_PREFIX}/integration/test_mcp_connectivity.py"
        run_pytest "IT-002 Watcher Events"    "${TEST_PREFIX}/integration/test_watcher_events.py"
        run_pytest "IT-003 MCP Tools"         "${TEST_PREFIX}/integration/test_mcp_tools.py"
        run_pytest "IT-004 Transport Layer"   "${TEST_PREFIX}/integration/test_transport.py"
        run_pytest "IT-005 Platform Coverage" "${TEST_PREFIX}/platform_tests/test_platform_coverage.py"
        ;;

    all)
        run_pytest "UT-001 SLA Patterns"        "${TEST_PREFIX}/unit/test_sla_patterns.py"
        run_pytest "UT-002 Platform Map"        "${TEST_PREFIX}/unit/test_platform_map.py"
        run_pytest "UT-003 Drain Mechanism"     "${TEST_PREFIX}/unit/test_drain_mechanism.py"
        run_pytest "UT-004 Input Validation"    "${TEST_PREFIX}/unit/test_input_validation.py"
        run_pytest "UT-006 Command Validation"  "${TEST_PREFIX}/unit/test_command_validation.py"
        run_pytest "UT-008 Risk Assessment"     "${TEST_PREFIX}/unit/test_risk_assessment.py"
        run_pytest "UT-009 Syslog Sanitize"     "${TEST_PREFIX}/unit/test_syslog_sanitize.py"
        run_pytest "UT-010 Transport Dispatch"  "${TEST_PREFIX}/unit/test_transport_dispatch.py"
        run_pytest "UT-011 RESTCONF Unit"       "${TEST_PREFIX}/unit/test_restconf_unit.py"
        run_pytest "UT-013 SSH Unit"            "${TEST_PREFIX}/unit/test_ssh_unit.py"
        run_pytest "UT-014 Config Push"         "${TEST_PREFIX}/unit/test_config_push.py"
        run_pytest "UT-015 Tool Layer"          "${TEST_PREFIX}/unit/test_tool_layer.py"
        run_pytest "UT-016 Jira Tools"          "${TEST_PREFIX}/unit/test_jira_tools.py"
        run_pytest "UT-017 Discord Approval"    "${TEST_PREFIX}/unit/test_approval.py"
        run_pytest "UT-018 Config Approval Gate" "${TEST_PREFIX}/unit/test_config_approval_gate.py"
        run_pytest "IT-001 MCP Connectivity"    "${TEST_PREFIX}/integration/test_mcp_connectivity.py"
        run_pytest "IT-002 Watcher Events"      "${TEST_PREFIX}/integration/test_watcher_events.py"
        run_pytest "IT-003 MCP Tools"           "${TEST_PREFIX}/integration/test_mcp_tools.py"
        run_pytest "IT-004 Transport Layer"     "${TEST_PREFIX}/integration/test_transport.py"
        run_pytest "IT-005 Platform Coverage"   "${TEST_PREFIX}/platform_tests/test_platform_coverage.py"
        ;;

    *)
        echo "Usage: $0 [unit|integration|all]"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo " Results: ${PASS} passed, ${FAIL} failed"
if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo " Failed:"
    for e in "${ERRORS[@]}"; do
        echo "   - ${e}"
    done
fi
echo "========================================"

if [[ ${FAIL} -gt 0 ]]; then
    exit 1
fi
