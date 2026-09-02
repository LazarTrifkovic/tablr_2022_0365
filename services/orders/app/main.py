import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.consumer import start_consumer, stop_consumer
from app.db import Base, engine
from app.events import start_producer, stop_producer
from app.routes import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_producer()  # Kafka producer: order-created / order-status-changed / order-rated
    await start_consumer()  # Kafka consumer: ticket-status-requests (hibridni modul)
    yield
    await stop_consumer()
    await stop_producer()
    await engine.dispose()


from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Tablr Orders Service", lifespan=lifespan)
app.include_router(router)
Instrumentator().instrument(app).expose(app)  # izloži /metrics za Prometheus


@app.get("/health")
def health():
    return {"service": "orders", "status": "ok"}
