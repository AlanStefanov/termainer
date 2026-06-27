#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

print_header() {
  echo "========================================="
  echo "        TERMAINER SMOKE TEST"
  echo "========================================="
  echo ""
}

pass() {
  printf "[${GREEN}✓${NC}] %s\n" "$1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  printf "[${RED}✗${NC}] %s\n" "$1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

run_check() {
  local label=$1
  shift

  if "$@"; then
    pass "$label"
  else
    fail "$label"
  fi
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

check_local_cli() {
  if [ -x "${ROOT_DIR}/venv/bin/termainer" ]; then
    CLI="${ROOT_DIR}/venv/bin/termainer"
  elif has_command termainer; then
    CLI="termainer"
  else
    return 1
  fi

  "${CLI}" --version >/dev/null
  "${CLI}" --help >/dev/null
  "${CLI}" doctor >/dev/null
}

print_header

run_check "Docker CLI" has_command docker
run_check "Docker Image" "${ROOT_DIR}/scripts/test-docker.sh"
run_check "Python" has_command python3
run_check "PyPI" "${ROOT_DIR}/scripts/test-pip.sh"
run_check "Homebrew" "${ROOT_DIR}/scripts/test-brew.sh"
run_check "Version" bash -c 'termainer --version >/dev/null 2>&1 || venv/bin/termainer --version >/dev/null 2>&1'
run_check "Help" bash -c 'termainer --help >/dev/null 2>&1 || venv/bin/termainer --help >/dev/null 2>&1'
run_check "Doctor" check_local_cli

echo ""
echo "========================================="
if [ "${FAIL_COUNT}" -eq 0 ]; then
  echo "All tests passed successfully."
else
  echo "${FAIL_COUNT} smoke test(s) failed."
fi
echo "========================================="

[ "${FAIL_COUNT}" -eq 0 ]
