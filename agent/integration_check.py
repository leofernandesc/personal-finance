"""Read-only readiness checks for the local Hermes integration.

The command intentionally reports warnings for manual prerequisites such as
WhatsApp pairing and a Hermes-sized model. It only fails in ``--strict`` mode,
which is useful in a real Cycle 3 acceptance run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MIN_HERMES_CONTEXT_LENGTH = 64_000
E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _get_json(url: str, *, timeout: float = 3.0) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, Any], *, timeout: float = 3.0) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _model_context(model_info: dict[str, Any]) -> int | None:
    info = model_info.get("model_info")
    if not isinstance(info, dict):
        return None
    for key, value in info.items():
        if key.endswith(".context_length"):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def check_backend(base_url: str) -> Check:
    try:
        data = _get_json(f"{base_url.rstrip('/')}/ready")
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return Check("backend", "fail", f"indisponível ({exc})")
    if data.get("status") != "ready":
        return Check("backend", "fail", f"resposta inesperada: {data.get('status')!r}")
    return Check("backend", "ok", "API pronta")


def check_ollama(base_url: str, model: str) -> Check:
    try:
        tags = _get_json(f"{base_url.rstrip('/')}/api/tags")
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return Check("ollama", "fail", f"indisponível ({exc})")
    models = {
        str(item.get("name"))
        for item in tags.get("models", [])
        if isinstance(item, dict) and item.get("name")
    }
    if model not in models:
        available = ", ".join(sorted(models)) or "nenhum modelo"
        return Check(
            "ollama", "warn", f"modelo {model!r} ausente; disponíveis: {available}"
        )
    try:
        info = _post_json(
            f"{base_url.rstrip('/')}/api/show",
            {"name": model},
            timeout=5.0,
        )
        context = _model_context(info)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return Check(
            "ollama",
            "warn",
            f"modelo presente, mas não foi possível ler a janela ({exc})",
        )
    if context is None:
        return Check("ollama", "warn", f"modelo {model} presente; janela não informada")
    if context < MIN_HERMES_CONTEXT_LENGTH:
        return Check(
            "ollama",
            "warn",
            f"{model} tem {context:,} tokens; Hermes exige pelo menos "
            f"{MIN_HERMES_CONTEXT_LENGTH:,}",
        )
    return Check("ollama", "ok", f"{model} disponível com janela de {context:,} tokens")


def check_hermes(repo_root: Path) -> Check:
    hermes = shutil.which("hermes")
    if not hermes:
        return Check("hermes", "fail", "comando não encontrado no PATH")
    result = subprocess.run(
        [hermes, "plugins", "doctor", "./agent", "--ci"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout or result.stderr).strip().splitlines()[-1:]
        return Check("hermes", "fail", detail[0] if detail else "plugin doctor falhou")
    return Check("hermes", "ok", "plugin doctor confirmou manifesto, import e registro")


def check_whatsapp(
    session_dir: Path,
    bridge_url: str,
    allowed_users: str | None,
    mode: str | None = None,
) -> Check:
    creds = session_dir / "creds.json"
    if not creds.exists():
        return Check("whatsapp", "warn", f"não pareado; falta {creds}")
    try:
        health = _get_json(f"{bridge_url.rstrip('/')}/health")
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return Check(
            "whatsapp", "warn", f"sessão existe, mas bridge não responde ({exc})"
        )
    if health.get("status") != "connected":
        return Check("whatsapp", "warn", f"bridge em estado {health.get('status')!r}")
    entries = {
        entry.strip() for entry in (allowed_users or "").split(",") if entry.strip()
    }
    if not entries:
        return Check(
            "whatsapp",
            "warn",
            "bridge conectado, mas WHATSAPP_ALLOWED_USERS não está definido",
        )
    if "*" in entries:
        return Check(
            "whatsapp",
            "warn",
            "WHATSAPP_ALLOWED_USERS não pode usar wildcard no aceite do Ciclo 3",
        )
    invalid_entries = sum(not E164_RE.fullmatch(entry) for entry in entries)
    if invalid_entries:
        return Check(
            "whatsapp",
            "warn",
            f"allowlist contém {invalid_entries} entrada(s) fora do formato E.164",
        )
    normalized_mode = (mode or "").strip().lower()
    if normalized_mode != "bot":
        return Check(
            "whatsapp",
            "warn",
            "bridge conectado, mas WHATSAPP_MODE=bot não está configurado",
        )
    return Check("whatsapp", "ok", "sessão Baileys conectada")


def run_checks(repo_root: Path) -> list[Check]:
    backend_url = os.getenv("PERSONAL_FINANCE_BACKEND_URL", "http://127.0.0.1:8000")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    # Keep the gateway model independent from the smaller smoke-runner model.
    model = os.getenv("HERMES_OLLAMA_MODEL", "llama3.2:3b")
    configured_session = os.getenv("HERMES_WHATSAPP_SESSION")
    if configured_session:
        session_dir = Path(configured_session).expanduser()
    else:
        # Hermes keeps the legacy path when it already contains credentials;
        # otherwise the current layout is used. Do not inspect credential data.
        legacy_session = Path("~/.hermes/whatsapp/session").expanduser()
        current_session = Path("~/.hermes/platforms/whatsapp/session").expanduser()
        session_dir = (
            legacy_session
            if (legacy_session / "creds.json").exists()
            else current_session
        )
    return [
        check_backend(backend_url),
        check_ollama(ollama_url, model),
        check_hermes(repo_root),
        check_whatsapp(
            session_dir,
            os.getenv("HERMES_WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3300"),
            os.getenv("WHATSAPP_ALLOWED_USERS")
            or os.getenv("HERMES_WHATSAPP_ALLOWED_USERS"),
            os.getenv("WHATSAPP_MODE"),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifica a prontidão do Ciclo 3 local"
    )
    parser.add_argument("--json", action="store_true", help="imprime somente JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="retorna erro enquanto houver qualquer check diferente de ok",
    )
    args = parser.parse_args()
    checks = run_checks(Path(__file__).resolve().parents[1])
    if args.json:
        print(
            json.dumps(
                [asdict(check) for check in checks], ensure_ascii=False, indent=2
            )
        )
    else:
        for check in checks:
            print(f"[{check.status.upper():5}] {check.name}: {check.detail}")
    return 1 if args.strict and any(check.status != "ok" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
