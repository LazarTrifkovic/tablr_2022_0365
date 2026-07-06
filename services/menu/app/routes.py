from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query

from app.models import Cafe, Category, MenuItem
from app.schemas import (
    CafeOut,
    CategoryOut,
    InternalItem,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    MenuOut,
)

router = APIRouter()


def _cafe_out(cafe: Cafe) -> CafeOut:
    return CafeOut(id=str(cafe.id), name=cafe.name, slug=cafe.slug,
                   address=cafe.address, currency=cafe.currency)


def _item_out(item: MenuItem) -> ItemOut:
    return ItemOut(id=str(item.id), name=item.name, description=item.description,
                   price=item.price, available=item.available,
                   allergens=item.allergens, image_url=item.image_url)


async def _get_cafe_or_404(cafe_id: str) -> Cafe:
    try:
        oid = PydanticObjectId(cafe_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Cafe not found")
    cafe = await Cafe.get(oid)
    if cafe is None:
        raise HTTPException(status_code=404, detail="Cafe not found")
    return cafe


@router.get("/cafes", response_model=list[CafeOut])
async def list_cafes():
    return [_cafe_out(c) for c in await Cafe.find_all().to_list()]


@router.get("/cafes/{cafe_id}/menu", response_model=MenuOut)
async def get_menu(cafe_id: str):
    cafe = await _get_cafe_or_404(cafe_id)
    categories = await Category.find(Category.cafe_id == cafe.id).sort("+sort").to_list()
    items = await MenuItem.find(MenuItem.cafe_id == cafe.id).to_list()

    by_category: dict[PydanticObjectId, list[ItemOut]] = {}
    for item in items:
        by_category.setdefault(item.category_id, []).append(_item_out(item))

    return MenuOut(
        cafe=_cafe_out(cafe),
        categories=[
            CategoryOut(id=str(c.id), name=c.name, items=by_category.get(c.id, []))
            for c in categories
        ],
    )


@router.post("/cafes/{cafe_id}/items", response_model=ItemOut, status_code=201)
async def create_item(cafe_id: str, body: ItemCreate):
    cafe = await _get_cafe_or_404(cafe_id)
    try:
        category_oid = PydanticObjectId(body.category_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category_id")
    category = await Category.get(category_oid)
    if category is None or category.cafe_id != cafe.id:
        raise HTTPException(status_code=400, detail="Category does not belong to this cafe")

    item = MenuItem(cafe_id=cafe.id, category_id=category_oid,
                    **body.model_dump(exclude={"category_id"}))
    await item.insert()
    return _item_out(item)


@router.patch("/cafes/{cafe_id}/items/{item_id}", response_model=ItemOut)
async def update_item(cafe_id: str, item_id: str, body: ItemUpdate):
    cafe = await _get_cafe_or_404(cafe_id)
    try:
        item = await MenuItem.get(PydanticObjectId(item_id))
    except Exception:
        item = None
    # provera vlasništva: stavka mora pripadati kafiću iz putanje (anti-IDOR)
    if item is None or item.cafe_id != cafe.id:
        raise HTTPException(status_code=404, detail="Item not found")

    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    await item.save()
    return _item_out(item)


@router.delete("/cafes/{cafe_id}/items/{item_id}", status_code=204)
async def delete_item(cafe_id: str, item_id: str):
    cafe = await _get_cafe_or_404(cafe_id)
    try:
        item = await MenuItem.get(PydanticObjectId(item_id))
    except Exception:
        item = None
    if item is None or item.cafe_id != cafe.id:
        raise HTTPException(status_code=404, detail="Item not found")
    await item.delete()


@router.get("/internal/items", response_model=list[InternalItem])
async def internal_items(ids: str = Query(..., description="Zarezom razdvojeni ID-jevi stavki")):
    """Interna ruta za orders servis — vraća podatke za validaciju porudžbine."""
    object_ids = []
    for raw in ids.split(","):
        try:
            object_ids.append(PydanticObjectId(raw.strip()))
        except Exception:
            continue
    items = await MenuItem.find({"_id": {"$in": object_ids}}).to_list()
    return [
        InternalItem(id=str(i.id), cafe_id=str(i.cafe_id), name=i.name,
                     price=i.price, available=i.available)
        for i in items
    ]
