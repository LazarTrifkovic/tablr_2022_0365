from pydantic import BaseModel, Field


class ItemOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    price: int
    available: bool
    allergens: list[str] = []
    image_url: str | None = None


class CategoryOut(BaseModel):
    id: str
    name: str
    items: list[ItemOut]


class CafeOut(BaseModel):
    id: str
    name: str
    slug: str
    address: str | None = None
    currency: str


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
    allergens: list[str] | None = None
    image_url: str | None = None


class InternalItem(BaseModel):
    """Podaci o stavci za validaciju porudžbine u orders servisu."""
    id: str
    cafe_id: str
    name: str
    price: int
    available: bool
