#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
VENV_DIR="${HOME}/.local/share/termainer/venv"

echo "▣  Installing Termainer..."
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

# Create virtual environment
echo "  Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Upgrade pip and install dependencies
echo "  Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r "$REPO_DIR/requirements.txt" --quiet
pip install -e "$REPO_DIR" --quiet

# Create symlink
mkdir -p "$INSTALL_DIR"
ln -sf "$VENV_DIR/bin/termainer" "$INSTALL_DIR/termainer"

echo ""
echo "  ✅ Termainer installed!"
echo ""
echo "  Make sure ${INSTALL_DIR} is in your PATH:"
echo "    export PATH=\"\$PATH:${INSTALL_DIR}\""
echo ""
echo "  Then run:"
echo "    termainer"
echo ""
echo "  For remote hosts, copy .env.example to .env and configure:"
echo "    cp ${REPO_DIR}/.env.example ${REPO_DIR}/.env"
