import asyncio
import contextlib
import re

import httpx
import jwt
import websockets
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Zaštićene (osoblje) rute: (METOD, servis, regex putanje, potrebna_uloga|None).
# None = bilo koja prijavljena uloga; "vlasnik" = samo vlasnik. Sve što NIJE ovde je
# javno (gost preko QR potpisa). Gost i osoblje dele prefikse pa se gleda metod+putanja.
PROTECTED: list[tuple[str, str, str, str | None]] = [
    ("GET", "orders", r"^orders/history", "vlasnik"),                # arhiva/pazar → vlasnik
    ("POST", "auth", r"^register$", "vlasnik"),                      # dodavanje osoblja → vlasnik
    ("POST", "orders", r"^tables/[^/]+/[^/]+/bill/settle$", None),   # naplata na stolu
    ("GET", "bar", r"^tickets", None),                              # tabla porudžbina
    ("PATCH", "bar", r"^tickets/[^/]+/status$", None),              # promena statusa
    ("GET", "bar", r"^requests", None),                            # lista poziva konobara
    ("PATCH", "bar", r"^requests/[^/]+/resolve$", None),           # rešavanje poziva
    ("POST", "menu", r"", None),                                  # meni izmene → osoblje
    ("PATCH", "menu", r"", None),
    ("PUT", "menu", r"", None),
    ("DELETE", "menu", r"", None),
]


def _required_role(method: str, service: str, path: str):
    """Vraća (zaštićeno, potrebna_uloga|None). zaštićeno=False → javna ruta."""
    for m, svc, rx, role in PROTECTED:
        if m == method and svc == service and re.search(rx, path):
            return True, role
    return False, None


def _verify_jwt(request: Request) -> dict | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        return jwt.decode(auth[7:], settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None

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

    # autentikacija osoblja za zaštićene rute; javne (gost) rute prolaze slobodno
    protected, need_role = _required_role(request.method, service, path)
    extra_headers: dict[str, str] = {}
    if protected:
        claims = _verify_jwt(request)
        if claims is None:
            return Response(status_code=401, content=b'{"detail":"Prijava je obavezna"}',
                            media_type="application/json")
        if need_role is not None and claims.get("role") != need_role:
            return Response(status_code=403, content=b'{"detail":"Nedovoljna prava"}',
                            media_type="application/json")
        # prosleđujemo identitet servisu (servisi veruju gateway-u)
        extra_headers = {
            "X-User": str(claims.get("sub", "")),
            "X-Role": str(claims.get("role", "")),
            "X-Cafe": str(claims.get("cafe_id", "")),
        }

    upstream = await client.request(
        request.method,
        f"{base}/{path}",
        params=request.query_params,
        content=await request.body(),
        headers={**{k: v for k, v in request.headers.items()
                    if k.lower() not in ("host", "content-length")},
                 **extra_headers},
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
