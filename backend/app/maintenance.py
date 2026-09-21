from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.maintenance import cleanup_expired_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove sessões, desafios e logs técnicos expirados com segurança."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="confirma a remoção; sem esta opção executa somente uma simulação",
    )
    parser.add_argument(
        "--agent-log-retention-days",
        type=int,
        default=None,
        help="retenção dos logs técnicos sem vínculo financeiro (padrão: configuração)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    retention_days = (
        args.agent_log_retention_days
        if args.agent_log_retention_days is not None
        else settings.agent_log_retention_days
    )

    with SessionLocal() as db:
        result = cleanup_expired_data(
            db,
            agent_log_retention_days=retention_days,
            dry_run=not args.apply,
        )

    output = {"mode": "apply" if args.apply else "dry-run", **asdict(result)}
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
