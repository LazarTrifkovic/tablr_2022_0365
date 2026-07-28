import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.events import start_producer, stop_producer
from app.routes import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_producer()  # Kafka producer za događaje o porudžbini
    yield
    await stop_producer()
    await engine.dispose()


app = FastAPI(title="Tablr Orders Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"service": "orders", "status": "ok"}
