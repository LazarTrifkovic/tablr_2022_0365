import asyncio

import httpx
from fastapi import FastAPI

SERVICES = {
    "menu": "http://menu:8000/health",
    "orders": "http://orders:8000/health",
    "barkds": "http://barkds:8000/health",
    "auth": "http://auth:8000/health",
    "payments": "http://payments:8000/health",
}

app = FastAPI(title="Tablr API Gateway")


async def check(client: httpx.AsyncClient, name: str, url: str) -> tuple[str, str]:
    try:
        response = await client.get(url)
        return name, response.json().get("status", "unknown")
    except httpx.HTTPError:
        return name, "down"


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=2) as client:
        results = await asyncio.gather(
            *(check(client, name, url) for name, url in SERVICES.items())
        )
    return {"gateway": "ok", "services": dict(results)}
