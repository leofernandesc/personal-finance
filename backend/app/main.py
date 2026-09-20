from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import API_PREFIX, API_ROUTERS
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name, version="0.1.0", description="API multiusuário de finanças pessoais"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
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


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "personal-finance-api"}
