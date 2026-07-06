from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Tablr Orders Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"service": "orders", "status": "ok"}
