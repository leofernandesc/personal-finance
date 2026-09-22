#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
profile_home=${HERMES_PROFILE_HOME:-"${HOME}/.hermes/profiles/personal-finance"}
smoke_sender=${HERMES_SMOKE_SENDER:-"+5592999999999"}
smoke_message_id=${HERMES_SMOKE_MESSAGE_ID:-"hermes-local-smoke-$(date -u +%Y%m%dT%H%M%SZ)"}
smoke_text=${HERMES_SMOKE_TEXT:-"Use a ferramenta get_balance e responda apenas com os valores retornados. Quanto dinheiro tenho atualmente?"}

command -v hermes >/dev/null 2>&1 || {
  echo "hermes não foi encontrado no PATH" >&2
  exit 1
}

if [[ ! -d "${profile_home}/plugins/personal-finance" ]]; then
  echo "plugin personal-finance não instalado em ${profile_home}" >&2
  echo "instale-o com: HERMES_HOME=${profile_home} hermes plugins install file://${repo_root}#agent --enable" >&2
  exit 1
fi

if [[ -z "${AGENT_SHARED_SECRET:-}" ]]; then
  env_file=${PERSONAL_FINANCE_ENV_FILE:-"${repo_root}/.env"}
  if [[ -f "$env_file" ]]; then
    AGENT_SHARED_SECRET=$(sed -n 's/^AGENT_SHARED_SECRET=//p' "$env_file" | head -n 1)
    AGENT_SHARED_SECRET=${AGENT_SHARED_SECRET#\"}
    AGENT_SHARED_SECRET=${AGENT_SHARED_SECRET%\"}
  fi
fi

if [[ -z "${AGENT_SHARED_SECRET:-}" ]]; then
  echo "AGENT_SHARED_SECRET não foi definido" >&2
  exit 1
fi

export AGENT_SHARED_SECRET
export HERMES_HOME="$profile_home"
export HERMES_PROFILE=personal-finance
export HERMES_SESSION_PLATFORM=whatsapp
export HERMES_SESSION_USER_ID="$smoke_sender"
export HERMES_SESSION_MESSAGE_ID="$smoke_message_id"
export PERSONAL_FINANCE_API_URL="${PERSONAL_FINANCE_API_URL:-http://127.0.0.1:8000/api/v1/integrations/agent}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"

exec hermes -z "$smoke_text" \
  --reasoning none \
  --in "$repo_root" \
  --no-restore-cwd
