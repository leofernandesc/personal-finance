from app.api.v1 import (
    accounts,
    agent,
    auth,
    budgets,
    categories,
    dashboard,
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
    agent.router,
    whatsapp.router,
]
