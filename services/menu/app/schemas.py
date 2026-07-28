from typing import Literal

from pydantic import BaseModel, Field


class ItemOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    price: int
    available: bool
    note: str | None = None
    allergens: list[str] = []
    image_url: str | None = None


class CategoryOut(BaseModel):
    id: str
    name: str
    items: list[ItemOut]


class TableSpotOut(BaseModel):
    number: int
    zone: str | None = None
    label: str | None = None
    shape: str = "square"
    seats: int | None = None
    x: float | None = None
    y: float | None = None
    w: float = 12
    h: float = 12


class TableSpotIn(BaseModel):
    """Jedan sto kad vlasnik snima raspored (editor mape)."""
    number: int = Field(ge=1, le=500)
    zone: str | None = Field(default=None, max_length=40)
    label: str | None = Field(default=None, max_length=60)
    shape: Literal["square", "round"] = "square"
    seats: int | None = Field(default=None, ge=1, le=50)
    x: float | None = Field(default=None, ge=0, le=100)
    y: float | None = Field(default=None, ge=0, le=100)
    w: float = Field(default=12, ge=3, le=40)
    h: float = Field(default=12, ge=3, le=40)


class TablesUpdate(BaseModel):
    tables: list[TableSpotIn] = Field(max_length=200)


class CafeOut(BaseModel):
    id: str
    name: str
    slug: str
    address: str | None = None
    currency: str
    tables: list[TableSpotOut] = []
    tables_count: int = 0  # izvedeno = len(tables), radi kompatibilnosti potrošača


class MenuOut(BaseModel):
    cafe: CafeOut
    categories: list[CategoryOut]


class ItemCreate(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    price: int = Field(gt=0)
    available: bool = True
    allergens: list[str] = []
    image_url: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    price: int | None = Field(default=None, gt=0)
    available: bool | None = None
    note: str | None = Field(default=None, max_length=200)
    allergens: list[str] | None = None
    image_url: str | None = None


class InternalItem(BaseModel):
    """Podaci o stavci za validaciju porudžbine u orders servisu."""
    id: str
    cafe_id: str
    name: str
    price: int
    available: bool
