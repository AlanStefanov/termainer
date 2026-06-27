#!/usr/bin/env bash
set -euo pipefail

IMAGE="${TERMAINER_DOCKER_IMAGE:-alanstefanov/termainer:latest}"

command -v docker >/dev/null 2>&1
docker info >/dev/null 2>&1
docker pull "${IMAGE}" >/dev/null
docker run --rm "${IMAGE}" --version >/dev/null
docker run --rm "${IMAGE}" --help >/dev/null
docker run --rm "${IMAGE}" doctor >/dev/null
