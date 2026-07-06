from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models import Ticket
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_url)
    await init_beanie(database=client.get_default_database(),
                      document_models=[Ticket])
    yield
    client.close()


app = FastAPI(title="Tablr Bar/KDS Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"service": "barkds", "status": "ok"}
