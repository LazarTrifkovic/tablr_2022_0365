from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models import Cafe, Category, MenuItem
from app.routes import router
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_url)
    await init_beanie(
        database=client.get_default_database(),
        document_models=[Cafe, Category, MenuItem],
    )
    await seed_if_empty()
    yield
    client.close()


app = FastAPI(title="Tablr Menu Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"service": "menu", "status": "ok"}
