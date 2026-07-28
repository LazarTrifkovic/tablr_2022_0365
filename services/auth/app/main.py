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
logger = logging.getLogger("auth")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.app_env == "dev":
        await seed_if_empty()
    yield
    await engine.dispose()


from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Tablr Auth Service", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)  # izloži /metrics za Prometheus


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
    """SaaS registracija kafića kao ORKESTRIRANA SAGA (Faza 4).

    Dve lokalne transakcije u dva servisa (odvojene baze → nema zajedničkog rollback-a):
      Korak 1: menu kreira kafić
      Korak 2: auth kreira vlasnički nalog
    auth je 'dirigent': ako Korak 2 padne, pokreće KOMPENZACIJU — briše kafić iz Koraka 1
    (menu DELETE /internal/cafes/{id}), da ne ostane osirotan kafić bez vlasnika.
    """
    # pre-provera: ako je email zauzet, ne diramo menu uopšte (sagu i ne počinjemo)
    exists = await session.execute(select(User).where(User.email == body.email))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email već postoji")

    # ——— Korak 1: kreiraj kafić (menu servis) ———
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(f"{settings.menu_url}/internal/cafes", json={
                "name": body.cafe_name, "address": body.address})
            resp.raise_for_status()
            cafe = resp.json()
    except httpx.HTTPError:
        # Korak 1 pao → ništa nije ni nastalo, nema šta da se kompenzuje
        raise HTTPException(status_code=503, detail="Menu servis nedostupan")
    logger.info("SAGA onboard: Korak 1 OK — kafić %s kreiran", cafe["id"])

    # ——— Korak 2: kreiraj vlasnički nalog; ako padne → KOMPENZUJ Korak 1 ———
    try:
        # (dev) namerna injekcija greške za demonstraciju kompenzacije
        if settings.app_env == "dev" and body.email.split("@", 1)[0] == "saga-fail":
            raise RuntimeError("injektovana greška Koraka 2 (demo kompenzacije)")

        user = User(cafe_id=cafe["id"], email=body.email,
                    password_hash=hash_password(body.password), role="vlasnik",
                    name=body.name)
        session.add(user)
        await session.commit()
    except Exception as exc:  # noqa: BLE001 — bilo koja greška Koraka 2 pokreće kompenzaciju
        await session.rollback()
        logger.warning("SAGA onboard: Korak 2 pao (%s) → KOMPENZACIJA: brišem kafić %s",
                       exc, cafe["id"])
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                await client.delete(f"{settings.menu_url}/internal/cafes/{cafe['id']}")
            logger.info("SAGA onboard: kompenzacija OK — kafić %s poništen", cafe["id"])
        except httpx.HTTPError:
            # kompenzacija sama pala — kafić ostaje osirotan; treba retry/ručno (zabeleži)
            logger.error("SAGA onboard: KOMPENZACIJA NIJE USPELA za kafić %s — ručna intervencija",
                         cafe["id"])
        raise HTTPException(status_code=500, detail="Registracija nije uspela (poništena)")

    logger.info("SAGA onboard: Korak 2 OK — vlasnik %s; saga uspešna", user.email)
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
