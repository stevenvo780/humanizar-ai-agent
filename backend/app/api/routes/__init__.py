"""HTTP routers grouped by resource; app.main includes them in this order."""

from app.api.routes import (
    chat,
    conversations,
    customers,
    knowledge,
    requests,
    system,
    tools,
)

ROUTERS = (
    system.router,
    knowledge.router,
    tools.router,
    requests.router,
    customers.router,
    conversations.router,
    chat.router,
)
