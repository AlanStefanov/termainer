#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${ROOT_DIR}/venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

RUN_LINT=true
RUN_TESTS=true
RUN_APP=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lint-only)  RUN_TESTS=false; RUN_APP=false; shift ;;
        --test-only)  RUN_LINT=false;  RUN_APP=false; shift ;;
        --run)        RUN_APP=true;                    shift ;;
        --help)
            echo "Usage: $0 [--lint-only | --test-only | --run]"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${YELLOW}[bootstrap] Creating venv...${NC}"
    python3 -m venv "$VENV_DIR"
fi

source "${VENV_DIR}/bin/activate"

if ! pip show textual &>/dev/null; then
    echo -e "${YELLOW}[bootstrap] Installing dependencies...${NC}"
    pip install -q -r requirements.txt
    pip install -q ruff pytest pytest-asyncio
fi

STATUS=0

if $RUN_LINT; then
    echo -e "${YELLOW}[lint] Running ruff...${NC}"
    if rtk ruff check src/ tests/; then
        echo -e "${GREEN}[lint] No issues found${NC}"
    else
        echo -e "${RED}[lint] Issues found${NC}"
        STATUS=1
    fi
fi

if $RUN_TESTS; then
    echo -e "${YELLOW}[test] Running pytest...${NC}"
    if rtk pytest tests/ -v; then
        echo -e "${GREEN}[test] All tests passed${NC}"
    else
        echo -e "${RED}[test] Some tests failed${NC}"
        STATUS=1
    fi
fi

if $RUN_APP; then
    echo -e "${YELLOW}[app] Checking runtime...${NC}"
    if command -v docker &>/dev/null && docker info &>/dev/null; then
        echo -e "${GREEN}[app] Docker detected, launching Termainer...${NC}"
        python -m termainer.app
    elif command -v podman &>/dev/null && podman info &>/dev/null; then
        echo -e "${GREEN}[app] Podman detected, launching Termainer...${NC}"
        python -m termainer.app
    elif command -v kubectl &>/dev/null && kubectl cluster-info &>/dev/null; then
        echo -e "${GREEN}[app] Kubernetes detected, launching Termainer...${NC}"
        python -m termainer.app
    else
        echo -e "${RED}[app] No container runtime detected${NC}"
        echo "  Start Docker/Podman or point kubectl to a cluster, then retry."
        STATUS=1
    fi
fi

exit $STATUS
