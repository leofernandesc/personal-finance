from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.router import API_PREFIX, API_ROUTERS
from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="API multiusuário de finanças pessoais",
    debug=settings.debug,
    docs_url="/docs" if settings.environment in {"development", "test"} else None,
    redoc_url="/redoc" if settings.environment in {"development", "test"} else None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    expose_headers=["X-Next-Cursor"],
    allow_headers=[
        "Content-Type",
        "X-Agent-Token",
        "X-Agent-Provider",
        "X-Agent-Sender-Id",
        "X-Agent-Message-Id",
    ],
)
for api_router in API_ROUTERS:
    app.include_router(api_router, prefix=API_PREFIX)


REQUIRED_SCHEMA_TABLES = (
    "users",
    "auth_sessions",
    "accounts",
    "categories",
    "transactions",
    "transfers",
    "budgets",
    "goals",
    "whatsapp_identities",
    "agent_messages",
    "agent_tool_calls",
    "pending_agent_actions",
    "financial_diagnostics",
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "personal-finance-api"}


@app.get("/ready", tags=["system"])
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        inspector = inspect(db.bind)
        missing_tables = [
            table_name
            for table_name in REQUIRED_SCHEMA_TABLES
            if not inspector.has_table(table_name)
        ]
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Banco de dados indisponível",
        ) from exc
    if missing_tables:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Schema do banco incompleto",
                "missing_tables": missing_tables,
            },
        )
    return {"status": "ready", "service": "personal-finance-api"}
