#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${ROOT_DIR}/venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${YELLOW}[bootstrap] Creating venv...${NC}"
    python3 -m venv "$VENV_DIR"
fi

source "${VENV_DIR}/bin/activate"

if ! pip show textual &>/dev/null; then
    echo -e "${YELLOW}[bootstrap] Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi

echo -e "${YELLOW}[app] Checking runtime...${NC}"
if command -v docker &>/dev/null && docker info &>/dev/null; then
    echo -e "${GREEN}[app] Docker detected, launching Termainer...${NC}"
elif command -v podman &>/dev/null && podman info &>/dev/null; then
    echo -e "${GREEN}[app] Podman detected, launching Termainer...${NC}"
elif command -v kubectl &>/dev/null && kubectl cluster-info &>/dev/null; then
    echo -e "${GREEN}[app] Kubernetes detected, launching Termainer...${NC}"
else
    echo -e "${YELLOW}[app] No container runtime detected, launching anyway...${NC}"
fi

python -m termainer.app
