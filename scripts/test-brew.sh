#!/usr/bin/env bash
set -euo pipefail

IMAGE="${TERMAINER_TEST_IMAGE:-ubuntu:24.04}"
CONTAINER="termainer-test-brew-$$"

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
  apt-get install -y build-essential curl file git procps >/dev/null
  NONINTERACTIVE=1 bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" >/dev/null
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  brew tap AlanStefanov/termainer >/dev/null
  brew install termainer >/dev/null
  termainer --version >/dev/null
  termainer --help >/dev/null
  termainer doctor >/dev/null
'
