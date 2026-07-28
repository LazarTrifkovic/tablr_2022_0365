import logging
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.consumer import start_consumer, stop_consumer
from app.models import ServiceRequest, Ticket
from app.routes import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_url)
    await init_beanie(database=client.get_default_database(),
                      document_models=[Ticket, ServiceRequest])
    await start_consumer()  # Kafka consumer petlja (order-events)
    yield
    await stop_consumer()
    client.close()


app = FastAPI(title="Tablr Bar/KDS Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"service": "barkds", "status": "ok"}
