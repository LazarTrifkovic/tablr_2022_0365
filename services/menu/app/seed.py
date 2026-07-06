from app.models import Cafe, Category, MenuItem

DEMO_MENU: dict[str, list[tuple[str, int, str | None]]] = {
    "Topli napici": [
        ("Espresso", 160, None),
        ("Espresso dupli", 220, None),
        ("Kapućino", 220, "mleko"),
        ("Late makijato", 250, "mleko"),
        ("Topla čokolada", 280, "mleko,gluten"),
        ("Čaj (nana/kamilica/voćni)", 180, None),
    ],
    "Hladni napici": [
        ("Ledena kafa", 290, "mleko"),
        ("Limunada", 220, None),
        ("Ceđena pomorandža", 320, None),
        ("Koka-kola 0.25", 220, None),
        ("Kisela voda 0.25", 160, None),
        ("Negazirana voda 0.25", 160, None),
    ],
    "Pivo": [
        ("Lav točeno 0.3", 240, "gluten"),
        ("Zaječarsko 0.33", 260, "gluten"),
        ("Tuborg 0.33", 280, "gluten"),
        ("Erdinger pšenično 0.5", 420, "gluten"),
    ],
    "Vino i kokteli": [
        ("Vranac čaša", 320, "sulfiti"),
        ("Chardonnay čaša", 340, "sulfiti"),
        ("Aperol Spritz", 520, "sulfiti"),
        ("Mojito", 490, None),
    ],
}


async def seed_if_empty() -> None:
    """Ubacuje demo kafić sa menijem ako je baza prazna."""
    if await Cafe.count() > 0:
        return

    cafe = Cafe(name="Kafić Panorama", slug="panorama", address="Beška bb")
    await cafe.insert()

    for sort, (category_name, items) in enumerate(DEMO_MENU.items()):
        category = Category(cafe_id=cafe.id, name=category_name, sort=sort)
        await category.insert()
        for name, price, allergens in items:
            await MenuItem(
                cafe_id=cafe.id,
                category_id=category.id,
                name=name,
                price=price,
                allergens=allergens.split(",") if allergens else [],
            ).insert()
