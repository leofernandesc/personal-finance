from app.api.v1 import (
    accounts,
    agent,
    auth,
    budgets,
    categories,
    dashboard,
    diagnostic,
    goals,
    transactions,
    whatsapp,
)

API_PREFIX = "/api/v1"
API_ROUTERS = [
    auth.router,
    accounts.router,
    categories.router,
    transactions.router,
    budgets.router,
    goals.router,
    dashboard.router,
    diagnostic.router,
    agent.router,
    whatsapp.router,
]
