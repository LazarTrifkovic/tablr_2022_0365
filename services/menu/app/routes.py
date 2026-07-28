from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query

import re

from app.config import settings
from app.external import currency_rates, suggest_allergens
from app.models import Cafe, Category, MenuItem, TableSpot
from app.schemas import (
    CafeCreate,
    CafeOut,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    InternalItem,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    MenuOut,
    QrLink,
    TablesUpdate,
    TableSpotOut,
)
from app.security import table_signature

router = APIRouter()


def _cafe_out(cafe: Cafe) -> CafeOut:
    return CafeOut(id=str(cafe.id), name=cafe.name, slug=cafe.slug,
                   address=cafe.address, currency=cafe.currency,
                   tables=[TableSpotOut(**t.model_dump()) for t in cafe.tables],
                   tables_count=len(cafe.tables))


def _item_out(item: MenuItem) -> ItemOut:
    return ItemOut(id=str(item.id), name=item.name, description=item.description,
                   price=item.price, available=item.available, note=item.note,
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


@router.get("/fx")
async def fx():
    """Kursevi za prikaz cena gostu u stranoj valuti (Frankfurter + RSD sidro).
    Vraća koliko RSD vredi 1 jedinica svake valute — gost deli cenu tim brojem.
    Uvek uspeva: ako je Frankfurter nedostupan, vraća rezervne kurseve (fresh=false)."""
    return await currency_rates()


@router.get("/allergens/search")
async def allergens_search(q: str = Query(..., min_length=2, max_length=80)):
    """Predlog alergena za naziv proizvoda (OpenFoodFacts) — pomoć osoblju pri uređivanju.
    Uvek uspeva: ako je OFF nedostupan, vraća praznu listu (available=false)."""
    return await suggest_allergens(q)


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "kafic"
    return base[:40]


@router.post("/internal/cafes", response_model=CafeOut, status_code=201)
async def create_cafe(body: CafeCreate):
    """Kreiranje kafića — interna ruta (poziva auth pri onboardingu). Blokirana na gateway-u."""
    slug = _slugify(body.name)
    # slug mora biti jedinstven (unique index) — dodaj sufiks ako je zauzet
    if await Cafe.find_one(Cafe.slug == slug) is not None:
        i = 2
        while await Cafe.find_one(Cafe.slug == f"{slug}-{i}") is not None:
            i += 1
        slug = f"{slug}-{i}"
    cafe = Cafe(name=body.name, slug=slug, address=body.address, currency=body.currency)
    await cafe.insert()
    return _cafe_out(cafe)


@router.delete("/internal/cafes/{cafe_id}", status_code=204)
async def delete_cafe(cafe_id: str):
    """KOMPENZACIONA akcija za onboarding-sagu (Faza 4): poništava kreiranje kafića
    ako naredni korak (kreiranje vlasnika) padne. Briše kafić + kategorije + stavke.
    Interna (blokirana na gateway-u), idempotentna (nepostojeći kafić = već poništen)."""
    try:
        oid = PydanticObjectId(cafe_id)
    except Exception:
        return  # nevalidan id → tretiraj kao već obrisan
    cafe = await Cafe.get(oid)
    if cafe is None:
        return
    await MenuItem.find(MenuItem.cafe_id == cafe.id).delete()
    await Category.find(Category.cafe_id == cafe.id).delete()
    await cafe.delete()


@router.post("/cafes/{cafe_id}/categories", response_model=CategoryOut, status_code=201)
async def create_category(cafe_id: str, body: CategoryCreate):
    cafe = await _get_cafe_or_404(cafe_id)
    count = await Category.find(Category.cafe_id == cafe.id).count()
    category = Category(cafe_id=cafe.id, name=body.name, sort=count)
    await category.insert()
    return CategoryOut(id=str(category.id), name=category.name, items=[])


@router.patch("/cafes/{cafe_id}/categories/{category_id}", response_model=CategoryOut)
async def update_category(cafe_id: str, category_id: str, body: CategoryUpdate):
    cafe = await _get_cafe_or_404(cafe_id)
    try:
        category = await Category.get(PydanticObjectId(category_id))
    except Exception:
        category = None
    if category is None or category.cafe_id != cafe.id:
        raise HTTPException(status_code=404, detail="Category not found")
    category.name = body.name
    await category.save()
    return CategoryOut(id=str(category.id), name=category.name, items=[])


@router.delete("/cafes/{cafe_id}/categories/{category_id}", status_code=204)
async def delete_category(cafe_id: str, category_id: str):
    cafe = await _get_cafe_or_404(cafe_id)
    try:
        category = await Category.get(PydanticObjectId(category_id))
    except Exception:
        category = None
    if category is None or category.cafe_id != cafe.id:
        raise HTTPException(status_code=404, detail="Category not found")
    # briše i sve stavke kategorije
    await MenuItem.find(MenuItem.category_id == category.id).delete()
    await category.delete()


@router.get("/cafes/{cafe_id}/qr-links", response_model=list[QrLink])
async def qr_links(cafe_id: str):
    """Potpisani QR linkovi po stolu — vlasnik ih generiše i štampa. Zaštićeno na gateway-u."""
    cafe = await _get_cafe_or_404(cafe_id)
    links = []
    for t in sorted(cafe.tables, key=lambda s: s.number):
        sig = table_signature(cafe_id, t.number)
        url = f"{settings.guest_base_url}/?cafe={cafe_id}&table={t.number}&sig={sig}"
        links.append(QrLink(table_number=t.number, url=url))
    return links


@router.patch("/cafes/{cafe_id}/tables", response_model=CafeOut)
async def update_tables(cafe_id: str, body: TablesUpdate):
    """Vlasnik snima raspored stolova (editor mape). Zamenjuje celu listu stolova.
    Zaštićeno na gateway-u (samo vlasnik). Brojevi stolova moraju biti jedinstveni."""
    cafe = await _get_cafe_or_404(cafe_id)
    numbers = [t.number for t in body.tables]
    if len(numbers) != len(set(numbers)):
        raise HTTPException(status_code=400, detail="Brojevi stolova moraju biti jedinstveni")
    cafe.tables = [TableSpot(**t.model_dump()) for t in body.tables]
    await cafe.save()
    return _cafe_out(cafe)


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
