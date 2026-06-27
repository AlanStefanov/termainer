#!/usr/bin/env bash
set -euo pipefail

IMAGE="${TERMAINER_TEST_IMAGE:-ubuntu:24.04}"
CONTAINER="termainer-test-pip-$$"

cleanup() {
  docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

command -v docker >/dev/null 2>&1
docker info >/dev/null 2>&1

docker run -dit --name "${CONTAINER}" "${IMAGE}" >/dev/null

docker exec "${CONTAINER}" bash -lc '
  set -euo pipefail
  export DEBIAN_FRONTEND=noninteractive
  apt-get update >/dev/null
  apt-get install -y python3 python3-pip python3-venv >/dev/null
  python3 -m venv /tmp/termainer-venv
  /tmp/termainer-venv/bin/pip install --upgrade pip >/dev/null
  /tmp/termainer-venv/bin/pip install termainer >/dev/null
  /tmp/termainer-venv/bin/termainer --version >/dev/null
  /tmp/termainer-venv/bin/termainer --help >/dev/null
  /tmp/termainer-venv/bin/termainer doctor >/dev/null
'
