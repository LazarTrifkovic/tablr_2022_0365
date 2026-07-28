import logging
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import Base, engine, get_session
from app.models import ROLES, User
from app.schemas import LoginIn, OnboardIn, RegisterIn, TokenOut, UserOut
from app.security import create_token, hash_password, verify_password
from app.seed import seed_if_empty

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.app_env == "dev":
        await seed_if_empty()
    yield
    await engine.dispose()


app = FastAPI(title="Tablr Auth Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"service": "auth", "status": "ok"}


def _user_out(u: User) -> UserOut:
    return UserOut(id=str(u.id), cafe_id=u.cafe_id, email=u.email,
                   role=u.role, name=u.name)


@app.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Pogrešan email ili lozinka")
    token = create_token(user_id=str(user.id), email=user.email, role=user.role,
                         cafe_id=user.cafe_id, name=user.name)
    return TokenOut(access_token=token, user=_user_out(user))


@app.post("/onboard", response_model=TokenOut, status_code=201)
async def onboard(body: OnboardIn, session: AsyncSession = Depends(get_session)):
    """SaaS registracija kafića: kreira kafić (menu servis) + vlasnički nalog, vraća token.
    Javna ruta — ovako novi vlasnik dobija svoj kafić i nalog u jednom koraku."""
    exists = await session.execute(select(User).where(User.email == body.email))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email već postoji")
    # 1) kreiraj kafić u menu servisu (interna ruta)
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(f"{settings.menu_url}/internal/cafes", json={
                "name": body.cafe_name, "address": body.address})
            resp.raise_for_status()
            cafe = resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Menu servis nedostupan")
    # 2) kreiraj vlasnički nalog vezan za taj kafić
    user = User(cafe_id=cafe["id"], email=body.email,
                password_hash=hash_password(body.password), role="vlasnik",
                name=body.name)
    session.add(user)
    await session.commit()
    token = create_token(user_id=str(user.id), email=user.email, role=user.role,
                         cafe_id=user.cafe_id, name=user.name)
    return TokenOut(access_token=token, user=_user_out(user))


@app.get("/cafes/{cafe_id}/staff", response_model=list[UserOut])
async def staff(cafe_id: str, session: AsyncSession = Depends(get_session)):
    """Osoblje kafića — vlasnik vidi/uređuje naloge. Zaštićeno na gateway-u (vlasnik)."""
    result = await session.execute(
        select(User).where(User.cafe_id == cafe_id).order_by(User.created_at))
    return [_user_out(u) for u in result.scalars().all()]


@app.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    """Kreiranje naloga osoblja. (Kasnije: samo vlasnik sme da dodaje naloge svog kafića.)"""
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Nepoznata uloga")
    exists = await session.execute(select(User).where(User.email == body.email))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email već postoji")
    user = User(cafe_id=body.cafe_id, email=body.email,
                password_hash=hash_password(body.password), role=body.role,
                name=body.name)
    session.add(user)
    await session.commit()
    return _user_out(user)


@app.get("/internal/me", response_model=UserOut)
async def me(user_id: str, session: AsyncSession = Depends(get_session)):
    """Interna provera naloga (servis-servis). Klijent identitet dobija iz JWT-a."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad id")
    user = await session.get(User, uid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(user)
