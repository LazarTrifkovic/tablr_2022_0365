from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel
from pymongo import IndexModel


class TableSpot(BaseModel):
    """Jedan sto na mapi kafića (embedded u Cafe — 10-30 po kafiću, nema kolekcije)."""
    number: int
    zone: str | None = None            # "Unutra" / "Bašta" / "Šank" — grupisanje na mapi
    label: str | None = None           # kratak opis ("do prozora")
    shape: Literal["square", "round"] = "square"
    seats: int | None = None
    # slobodna pozicija na platnu u procentima (0-100); None = koristi grid fallback
    x: float | None = None
    y: float | None = None
    w: float = 12
    h: float = 12


class Cafe(Document):
    name: str
    slug: str
    address: str | None = None
    currency: str = "RSD"
    tables: list[TableSpot] = []  # mapa stolova — osnova za prikaz baru i QR generisanje

    class Settings:
        name = "cafes"
        indexes = [IndexModel("slug", unique=True)]


class Category(Document):
    cafe_id: PydanticObjectId
    name: str
    sort: int = 0

    class Settings:
        name = "categories"
        indexes = ["cafe_id"]


class MenuItem(Document):
    cafe_id: PydanticObjectId
    category_id: PydanticObjectId
    name: str
    description: str | None = None
    price: int  # cena u RSD (celi dinari)
    available: bool = True
    # javna napomena osoblja koju gost vidi u meniju (npr. "danas bez limuna")
    note: str | None = None
    allergens: list[str] = []
    image_url: str | None = None

    class Settings:
        name = "items"
        indexes = ["cafe_id", "category_id"]
