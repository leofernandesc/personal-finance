#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

db_port=${E2E_DB_PORT:-15432}
api_port=${E2E_API_PORT:-18000}
web_port=${E2E_WEB_PORT:-13000}

validate_port() {
  local name=$1
  local value=$2
  if [[ ! "$value" =~ ^[0-9]{1,5}$ ]] || ((10#$value < 1024 || 10#$value > 65535)); then
    printf '%s deve ser uma porta entre 1024 e 65535 (recebido: %s)\n' "$name" "$value" >&2
    exit 2
  fi
}

validate_port E2E_DB_PORT "$db_port"
validate_port E2E_API_PORT "$api_port"
validate_port E2E_WEB_PORT "$web_port"
if [[ "$db_port" == "$api_port" || "$db_port" == "$web_port" || "$api_port" == "$web_port" ]]; then
  echo "E2E_DB_PORT, E2E_API_PORT e E2E_WEB_PORT devem ser diferentes" >&2
  exit 2
fi

command -v docker >/dev/null 2>&1 || { echo "Docker não foi encontrado no PATH" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl é necessário para aguardar os serviços" >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "O daemon Docker não está acessível" >&2; exit 1; }

if [[ ! -x "$repo_root/frontend/node_modules/.bin/playwright" ]]; then
  echo "Playwright não está instalado; execute 'cd frontend && npm ci'" >&2
  exit 1
fi
firefox_binary=$(cd "$repo_root/frontend" && node -e "process.stdout.write(require('@playwright/test').firefox.executablePath())")
if [[ ! -x "$firefox_binary" ]]; then
  echo "Firefox do Playwright não está instalado; execute 'cd frontend && npx playwright install firefox'" >&2
  exit 1
fi

project_suffix=$(date -u +%Y%m%d%H%M%S)-${BASHPID}-${RANDOM}
compose_project="personal-finance-e2e-${project_suffix}"

existing_containers=$(docker container ls --all --quiet --filter "label=com.docker.compose.project=${compose_project}")
existing_volumes=$(docker volume ls --quiet --filter "label=com.docker.compose.project=${compose_project}")
existing_images=$(docker image ls --quiet --filter "reference=${compose_project}-*")
if [[ -n "$existing_containers" || -n "$existing_volumes" || -n "$existing_images" ]]; then
  echo "O namespace temporário E2E já existe; recusando reutilizar ou remover recursos" >&2
  exit 1
fi

compose() {
  docker compose --project-name "$compose_project" \
    --file "$repo_root/docker-compose.yml" \
    --file "$repo_root/docker-compose.e2e.yml" "$@"
}

# Use a dedicated Compose namespace, database volume, credentials, and ports.
# Never pass the developer's root .env values into the temporary backend.
export BACKEND_ENV_FILE=/dev/null
export ENVIRONMENT=test
export DEBUG=false
export COOKIE_SECURE=false
export POSTGRES_USER=finance_e2e
export POSTGRES_PASSWORD=finance_e2e
export POSTGRES_DB=personal_finance_e2e
export POSTGRES_HOST_PORT="$db_port"
export BACKEND_HOST_PORT="$api_port"
export FRONTEND_HOST_PORT="$web_port"
export APP_BIND_HOST=127.0.0.1
export AGENT_SHARED_SECRET=local-e2e-only-secret-not-for-production
export CORS_ORIGINS="http://localhost:${web_port}"
export ALLOWED_HOSTS=localhost,127.0.0.1,backend,testserver
export NEXT_PUBLIC_API_URL="http://localhost:${api_port}/api/v1"
export PLAYWRIGHT_BASE_URL="http://localhost:${web_port}"

compose_started=0
cleanup() {
  local result=$?
  trap - EXIT
  if ((compose_started)); then
    if ! compose down --volumes --remove-orphans; then
      echo "Não foi possível remover a stack E2E temporária ${compose_project}" >&2
      if ((result == 0)); then result=1; fi
    else
      for service in backend frontend-e2e; do
        local image_ref="${compose_project}-${service}:latest"
        if docker image inspect "$image_ref" >/dev/null 2>&1; then
          if ! docker image rm "$image_ref" >/dev/null; then
            echo "Não foi possível remover a imagem E2E temporária ${image_ref}" >&2
            if ((result == 0)); then result=1; fi
          fi
        fi
      done
    fi
  fi
  exit "$result"
}
trap cleanup EXIT

echo "Iniciando stack E2E descartável ${compose_project} (web :${web_port}, API :${api_port}, PostgreSQL :${db_port})"
compose_started=1
compose up --detach --build db backend frontend-e2e

ready=0
for attempt in $(seq 1 90); do
  if curl --fail --silent "http://127.0.0.1:${api_port}/ready" >/dev/null \
    && curl --fail --silent "http://localhost:${web_port}/register" >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done

if (( ! ready )); then
  echo "A stack E2E não ficou pronta; status dos serviços:" >&2
  compose ps >&2
  compose logs --no-color backend frontend-e2e >&2 || true
  exit 1
fi

(cd "$repo_root/frontend" && npm run test:e2e)
