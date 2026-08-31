import logging

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.breaker import CircuitBreaker, CircuitOpenError
from app.config import settings
from app.security import verify_table_signature

from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger("payments")
app = FastAPI(title="Tablr Payments Service")
Instrumentator().instrument(app).expose(app)  # izloži /metrics za Prometheus

# prekidač za sinhroni poziv ka orders servisu (obeležavanje stavki plaćenim)
orders_breaker = CircuitBreaker("orders", fail_max=3, reset_timeout=10)


class PayIn(BaseModel):
    cafe_id: str
    table_number: int = Field(ge=1, le=500)
    sig: str
    order_item_ids: list[int] = Field(min_length=1)
    amount: int = Field(gt=0)
    # tokenizovan payload iz Google Pay / Apple Pay — SIROVA KARTICA NIKAD NE STIŽE OVDE.
    # U TEST modu je lažan; u produkciji se prosleđuje pravom procesoru (PSP).
    token: str


@app.get("/health")
def health():
    return {"service": "payments", "status": "ok"}


@app.post("/pay")
async def pay(body: PayIn):
    """DEMO online naplata (Google Pay TEST). Gost šalje tokenizovan payload; ovaj servis
    dokazuje sto (potpis), 'naplati' (u TEST-u samo prihvati token), pa javi orders-u da
    obeleži stavke plaćenim. Karta nikad ne prolazi kroz orders/menu — samo kroz PSP granicu.
    U produkciji `token` ide pravom procesoru (Raiffeisen/Corvus/...) umesto ovog prihvatanja."""
    if not verify_table_signature(body.cafe_id, body.table_number, body.sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")
    if not body.token:
        raise HTTPException(status_code=400, detail="Missing payment token")

    # --- ovde bi u produkciji išao poziv PSP-u sa `token` i `amount` ---
    logger.info("DEMO naplata: sto %s, iznos %s RSD, stavke %s",
                body.table_number, body.amount, body.order_item_ids)

    # naplaćeno → orders obeležava stavke plaćenim (servis-servis, kroz Circuit Breaker)
    async def _settle() -> httpx.Response:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{settings.orders_url}/tables/{body.cafe_id}/{body.table_number}/bill/settle",
                json={"order_item_ids": body.order_item_ids, "payment_method": "card"},
            )
            resp.raise_for_status()
            return resp

    try:
        resp = await orders_breaker.call(_settle)
    except CircuitOpenError:
        raise HTTPException(status_code=503,
                            detail="Naplata privremeno nedostupna (prekidač otvoren)")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Orders service unavailable")

    return {"status": "paid", "amount": body.amount, "bill": resp.json()}
