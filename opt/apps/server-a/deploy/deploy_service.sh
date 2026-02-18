#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $(basename "$0") <auth|sms|shop|laydi|core>" >&2
  exit 1
fi

SERVICE_NAME="$1"
shift || true

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="${ROOT_DIR}/services/${SERVICE_NAME}"
COMPOSE_FILE="${SERVICE_DIR}/docker-compose.prod.yml"
PROJECT_NAME="servera_${SERVICE_NAME}"

case "${SERVICE_NAME}" in
  auth|sms|shop|laydi|core)
    ;;
  *)
    echo "Unknown service '${SERVICE_NAME}'." >&2
    exit 1
    ;;
 esac

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Missing compose file for ${SERVICE_NAME}: ${COMPOSE_FILE}" >&2
  exit 1
fi

if [[ ! -f "${SERVICE_DIR}/.env" ]]; then
  echo "Missing ${SERVICE_DIR}/.env (container environment variables)." >&2
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

DOCKER_ARGS=(-f "${COMPOSE_FILE}" -p "${PROJECT_NAME}")

echo "Deploying service ${SERVICE_NAME}..."
if ! docker compose "${DOCKER_ARGS[@]}" pull "$@"; then
  echo "(pull step skipped or failed – continuing, build contexts may be used instead)"
fi
docker compose "${DOCKER_ARGS[@]}" up -d --remove-orphans "$@"

echo "Service ${SERVICE_NAME} is up."
