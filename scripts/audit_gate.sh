#!/usr/bin/env bash
# =============================================================================
# Audit Gate — CI/CD wrapper for the migration audit pipeline
#
# This script is used by the composite GitHub Action (action.yml) and can also
# be run standalone in any CI system.
#
# Environment variables (set by action.yml or manually):
#   INPUT_CONFIG_PATH       — Path to audit YAML config (default: config/audit.yaml)
#   INPUT_CLIENT_NAME       — Client name for report (default: CI_Run)
#   INPUT_MIGRATION_DESC    — Migration description (default: Source -> Target)
#   INPUT_FAIL_ON_WARNINGS  — "true" to block on GO WITH WARNINGS (default: false)
#
# Outputs (GitHub Actions):
#   verdict      — The audit verdict string
#   report_path  — Directory containing the audit report
#   results_json — Path to the JSON results file
# =============================================================================

set -euo pipefail

CONFIG_PATH="${INPUT_CONFIG_PATH:-config/audit.yaml}"
CLIENT_NAME="${INPUT_CLIENT_NAME:-CI_Run}"
MIGRATION_DESC="${INPUT_MIGRATION_DESC:-Source -> Target}"
FAIL_ON_WARNINGS="${INPUT_FAIL_ON_WARNINGS:-false}"

RESULTS_JSON="test_outputs/ci/audit_result.json"

echo ""
echo "============================================"
echo "  Migration Audit Gate"
echo "============================================"
echo "  Config  : ${CONFIG_PATH}"
echo "  Client  : ${CLIENT_NAME}"
echo "  Migration: ${MIGRATION_DESC}"
echo "  Fail on warnings: ${FAIL_ON_WARNINGS}"
echo "============================================"
echo ""

# Build the CLI command
CLI_ARGS=(
    run
    --config "${CONFIG_PATH}"
    --client "${CLIENT_NAME}"
    --migration "${MIGRATION_DESC}"
    --ci
)

if [[ "${FAIL_ON_WARNINGS}" == "true" ]]; then
    CLI_ARGS+=(--fail-on-warnings)
fi

# Run the audit and capture exit code
set +e
python3 cli.py "${CLI_ARGS[@]}"
EXIT_CODE=$?
set -e

# Extract verdict from JSON results
VERDICT="UNKNOWN"
REPORT_PATH="test_outputs"
if [[ -f "${RESULTS_JSON}" ]]; then
    VERDICT=$(python3 -c "import json; print(json.load(open('${RESULTS_JSON}'))['verdict'])" 2>/dev/null || echo "UNKNOWN")
fi

# Set GitHub Actions outputs (no-op if not in GitHub Actions)
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "verdict=${VERDICT}" >> "${GITHUB_OUTPUT}"
    echo "report_path=${REPORT_PATH}" >> "${GITHUB_OUTPUT}"
    echo "results_json=${RESULTS_JSON}" >> "${GITHUB_OUTPUT}"
fi

# Write job summary (GitHub Actions only)
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
        echo "## 🔍 Migration Audit Gate"
        echo ""

        if [[ "${EXIT_CODE}" -eq 0 ]]; then
            echo "### ✅ Verdict: ${VERDICT}"
            echo ""
            echo "Deployment is **approved**."
        else
            echo "### ❌ Verdict: ${VERDICT}"
            echo ""
            echo "Deployment is **blocked**. Review the audit report for details."
        fi

        echo ""

        if [[ -f "${RESULTS_JSON}" ]]; then
            echo "#### Summary"
            echo ""
            python3 -c "
import json
r = json.load(open('${RESULTS_JSON}'))
s = r['summary']
print(f'| Metric | Count |')
print(f'|--------|-------|')
print(f'| ✅ Pass | {s[\"pass\"]} |')
print(f'| ⚠️ Warn | {s[\"warn\"]} |')
print(f'| ❌ Fail | {s[\"fail\"]} |')
print(f'| 🔴 Error | {s[\"error\"]} |')
print(f'| **Total** | **{r[\"total_checks\"]}** |')
" 2>/dev/null || echo "_Could not parse results._"
        fi

        echo ""
        echo "📄 Full results: \`${RESULTS_JSON}\`"
    } >> "${GITHUB_STEP_SUMMARY}"
fi

exit "${EXIT_CODE}"
