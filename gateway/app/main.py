import asyncio
import contextlib

import httpx
import websockets
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# mapa javnih prefiksa na interne adrese servisa
ROUTES = {
    "menu": settings.menu_url,
    "orders": settings.orders_url,
    "bar": settings.barkds_url,
    "auth": settings.auth_url,
    "payments": settings.payments_url,
}

# zaglavlja koja se ne prosleđuju nazad klijentu
HOP_BY_HOP = {
    "content-length", "transfer-encoding", "connection", "keep-alive",
    "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade",
}

app = FastAPI(title="Tablr API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = httpx.AsyncClient(timeout=15)


@app.on_event("shutdown")
async def shutdown() -> None:
    await client.aclose()


@app.get("/health")
async def health():
    async def check(name: str, base: str) -> tuple[str, str]:
        try:
            r = await client.get(f"{base}/health", timeout=2)
            return name, r.json().get("status", "unknown")
        except httpx.HTTPError:
            return name, "down"

    results = await asyncio.gather(*(check(n, b) for n, b in ROUTES.items()))
    return {"gateway": "ok", "services": dict(results)}


@app.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(service: str, path: str, request: Request) -> Response:
    base = ROUTES.get(service)
    if base is None:
        return Response(status_code=404, content=b'{"detail":"Unknown service"}',
                        media_type="application/json")
    # interne rute servisa nikada nisu dostupne spolja
    if path.startswith("internal") or path.startswith("dev"):
        return Response(status_code=403, content=b'{"detail":"Forbidden"}',
                        media_type="application/json")

    upstream = await client.request(
        request.method,
        f"{base}/{path}",
        params=request.query_params,
        content=await request.body(),
        headers={k: v for k, v in request.headers.items()
                 if k.lower() not in ("host", "content-length")},
    )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers={k: v for k, v in upstream.headers.items()
                 if k.lower() not in HOP_BY_HOP},
    )


@app.websocket("/ws/bar/{cafe_id}")
async def ws_bar(ws: WebSocket, cafe_id: str) -> None:
    """Prosleđuje WebSocket konekciju bar dashboard-a ka Bar/KDS servisu."""
    await ws.accept()
    upstream_url = settings.barkds_url.replace("http://", "ws://") + f"/ws/{cafe_id}"
    try:
        async with websockets.connect(upstream_url) as upstream:

            async def client_to_upstream() -> None:
                while True:
                    await upstream.send(await ws.receive_text())

            async def upstream_to_client() -> None:
                async for message in upstream:
                    await ws.send_text(message)

            done, pending = await asyncio.wait(
                [asyncio.create_task(client_to_upstream()),
                 asyncio.create_task(upstream_to_client())],
                return_when=asyncio.FIRST_EXCEPTION,
            )
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
    except (WebSocketDisconnect, websockets.WebSocketException, OSError):
        pass
    finally:
        with contextlib.suppress(RuntimeError):
            await ws.close()
