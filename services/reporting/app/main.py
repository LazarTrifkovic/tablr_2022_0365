import logging
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.consumer import start_consumer, stop_consumer
from app.models import CafeStats, ProcessedEvent

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_url)
    await init_beanie(database=client.get_default_database(),
                      document_models=[CafeStats, ProcessedEvent])
    await start_consumer()  # projektor gradi read model iz Kafke
    yield
    await stop_consumer()
    client.close()


from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Tablr Reporting Service", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)  # izloži /metrics za Prometheus


@app.get("/health")
def health():
    return {"service": "reporting", "status": "ok"}


@app.get("/analytics/{cafe_id}")
async def analytics(cafe_id: str):
    """UPIT (CQRS read strana): vraća VEĆ-SRAČUNAT bilans smene iz read modela —
    bez skeniranja porudžbina i bez ikakvog računanja nad write bazom."""
    s = await CafeStats.find_one(CafeStats.cafe_id == cafe_id)
    if s is None:
        # još nema isporučenih porudžbina za ovaj kafić
        return {"cafe_id": cafe_id, "orders_count": 0, "revenue": 0,
                "avg_prep_seconds": None, "avg_rating": None,
                "rated_count": 0, "cash_count": 0, "card_count": 0}
    return {
        "cafe_id": s.cafe_id,
        "orders_count": s.orders_count,
        "revenue": s.revenue,
        "avg_prep_seconds": round(s.prep_seconds_sum / s.prep_seconds_count, 1)
        if s.prep_seconds_count else None,
        "avg_rating": round(s.rating_sum / s.rating_count, 2)
        if s.rating_count else None,
        "rated_count": s.rating_count,
        "cash_count": s.cash_count,
        "card_count": s.card_count,
    }
