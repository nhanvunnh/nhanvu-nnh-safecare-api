#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT_DIR}/infra"
ENV_FILE="${INFRA_DIR}/.env.infra"
COMPOSE_FILE="${INFRA_DIR}/docker-compose.infra.yml"
PROJECT_NAME="servera_infra"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Create it before deploying." >&2
  exit 1
fi

ensure_network() {
  local network_name="$1"
  if ! docker network inspect "${network_name}" >/dev/null 2>&1; then
    docker network create "${network_name}"
  fi
}

ensure_network proxy-network
ensure_network infra-network

DOCKER_CONTEXT_ARGS=(--env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}")

echo "Applying infrastructure stack..."
docker compose "${DOCKER_CONTEXT_ARGS[@]}" pull
docker compose "${DOCKER_CONTEXT_ARGS[@]}" up -d

echo "Infrastructure stack is up."
