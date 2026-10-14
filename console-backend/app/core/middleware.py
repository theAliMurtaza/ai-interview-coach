"""Bound request sizes and apply shared request limits before route work."""

import uuid

from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.rate_limit import check_rate_limit


class RequestPolicyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid4())

        async def send_headers(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        path = scope["path"]
        try:
            if path not in {"/health", "/ready"} and scope["method"] != "OPTIONS":
                ip = (scope.get("client") or ("unknown",))[0]
                auth = path.startswith(settings.API_V1_PREFIX + "/auth/")
                webhook = path.startswith(settings.API_V1_PREFIX + "/webhooks/")
                bucket = "auth" if auth else "webhook" if webhook else "api"
                limit = (
                    settings.AUTH_RATE_LIMIT_PER_MINUTE
                    if auth
                    else (
                        settings.WEBHOOK_RATE_LIMIT_PER_MINUTE
                        if webhook
                        else settings.RATE_LIMIT_PER_MINUTE
                    )
                )
                await check_rate_limit(
                    f"{bucket}:{ip}",
                    limit,
                )
        except AppError as exc:
            response = JSONResponse(
                {"error": {"code": exc.error_code, "message": exc.message}},
                status_code=exc.status_code,
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send_headers)
            return
        # Enforce even on chunked bodies with no Content-Length header.
        limit = (
            settings.MAX_UPLOAD_BYTES + 65536 if path.endswith("/resumes/upload") else 1024 * 1024
        )
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                await JSONResponse(
                    {"error": {"code": "payload_too_large", "message": "Request body too large"}},
                    status_code=413,
                )(scope, receive, send_headers)
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def receive_body():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, receive_body, send_headers)
