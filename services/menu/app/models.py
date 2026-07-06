from beanie import Document, PydanticObjectId
from pymongo import IndexModel


class Cafe(Document):
    name: str
    slug: str
    address: str | None = None
    currency: str = "RSD"

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
    allergens: list[str] = []
    image_url: str | None = None

    class Settings:
        name = "items"
        indexes = ["cafe_id", "category_id"]
