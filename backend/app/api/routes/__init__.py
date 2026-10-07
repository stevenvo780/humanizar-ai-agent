"""HTTP routers grouped by resource; app.main includes them in this order."""

from app.api.routes import (
    ask,
    chat,
    conversations,
    customers,
    knowledge,
    preguntar,
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
    ask.router,
    preguntar.router,
)
