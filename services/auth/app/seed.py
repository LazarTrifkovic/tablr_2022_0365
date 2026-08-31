import logging

import httpx
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.security import hash_password

logger = logging.getLogger("auth")

# demo nalozi za razvoj/ispit — proste kratke prijave (dev only, ne za produkciju).
# Prvi element je "korisničko ime" kojim se prijavljuješ (login prima username, ne samo email).
DEMO = [
    ("admin", "admin", "vlasnik", "Milan (vlasnik)"),
    ("konobar", "konobar", "konobar", "Ana (konobar)"),
]


async def _demo_cafe_id() -> str | None:
    """Veže demo naloge na demo kafić — dovlači njegov id iz menu servisa."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.menu_url}/cafes")
            r.raise_for_status()
            cafes = r.json()
            return cafes[0]["id"] if cafes else None
    except (httpx.HTTPError, KeyError, IndexError):
        return None


async def seed_if_empty() -> None:
    """Ubacuje demo naloge ako tabela nema korisnika (samo dev)."""
    async with SessionLocal() as session:
        existing = await session.execute(select(User).limit(1))
        if existing.scalar_one_or_none() is not None:
            return
        cafe_id = await _demo_cafe_id()
        if cafe_id is None:
            logger.warning("Nema demo kafića iz menu servisa — preskačem seed naloga")
            return
        for email, password, role, name in DEMO:
            session.add(User(cafe_id=cafe_id, email=email,
                             password_hash=hash_password(password),
                             role=role, name=name))
        await session.commit()
        logger.info("Seedovana %d demo naloga za kafić %s", len(DEMO), cafe_id)
