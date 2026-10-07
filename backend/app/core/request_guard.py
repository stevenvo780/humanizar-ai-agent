from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestTooLarge(Exception):
    pass


class RequestGuard:
    """Bound bodies before parsing; keep raw unexpected tracebacks out of HTTP logs."""

    def __init__(self, app: ASGIApp, upload_limit: int) -> None:
        self.app, self.upload_limit = app, upload_limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        upload = scope.get("path") == "/api/documents" and scope.get("method") == "POST"
        bounded = upload or scope.get("method") in {"POST", "PUT", "PATCH", "DELETE"}
        # 512 KiB also accommodates maximum chat history encoded as escaped UTF-16 JSON.
        limit = self.upload_limit + 65536 if upload else 512 * 1024
        size_error = (
            "El archivo excede el tamaño permitido."
            if upload
            else "La solicitud excede el tamaño permitido."
        )
        if bounded:
            headers = dict(scope.get("headers", []))
            declared = headers.get(b"content-length", b"0")
            if declared.isdigit() and (len(declared) > 20 or int(declared) > limit):
                await JSONResponse({"detail": size_error}, 413)(scope, receive, send)
                return
        consumed = 0
        started = False
        exceeded = False
        rejected = False

        async def bounded_receive() -> Message:
            nonlocal consumed, exceeded
            message = await receive()
            if bounded and message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > limit:
                    exceeded = True
                    raise RequestTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal started, rejected
            if message["type"] == "http.response.start":
                started = True
                if exceeded:
                    # Framework parsing may turn receive errors into a generic 400 response.
                    rejected = True
                    await JSONResponse({"detail": size_error}, 413)(scope, receive, send)
            if not rejected:
                await send(message)

        try:
            await self.app(scope, bounded_receive, tracked_send)
        except Exception as exc:
            if not started:
                status = 413 if exceeded or isinstance(exc, RequestTooLarge) else 500
                message = size_error if status == 413 else "No se pudo completar la operación."
                await JSONResponse({"detail": message}, status)(scope, receive, send)
