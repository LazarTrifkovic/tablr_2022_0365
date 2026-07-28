"""Integracije sa besplatnim eksternim API-jima (pozivi idu server-side, ne iz browsera).

- Frankfurter (https://frankfurter.dev) — devizni kursevi ECB. NEMA RSD, pa RSD→EUR ide
  preko fiksnog sidra (config), a EUR→ostale valute preko Frankfurter-a. Konverzija je
  SAMO za prikaz gostu; cene se i dalje čuvaju i naplaćuju u celim RSD.
- OpenFoodFacts (https://openfoodfacts.org) — otvorena baza proizvoda; koristimo za
  predlog alergena po nazivu stavke (pomoć osoblju pri uređivanju menija).
"""
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger("menu")

FRANKFURTER = "https://api.frankfurter.app"
OFF_SEARCH = "https://world.openfoodfacts.org/cgi/search.pl"

# valute koje nudimo gostu (RSD je bazna); EUR ide preko sidra, ostale preko Frankfurter-a.
# RUB izostavljen — ECB/Frankfurter ga ne objavljuje od 2022.
TARGET_CURRENCIES = ["EUR", "USD", "GBP", "CHF"]

# rezervni EUR kursevi ako je Frankfurter nedostupan (gost i dalje vidi ≈ cenu, "nije sveže")
FALLBACK_EUR_RATES = {"EUR": 1.0, "USD": 1.08, "GBP": 0.85, "CHF": 0.95}

# OpenFoodFacts alergen tagovi (en:*) → naši srpski nazivi
ALLERGEN_MAP = {
    "milk": "mleko", "gluten": "gluten", "eggs": "jaja", "nuts": "orašasti plodovi",
    "peanuts": "kikiriki", "soybeans": "soja", "soy": "soja", "fish": "riba",
    "crustaceans": "rakovi", "molluscs": "mekušci", "sesame-seeds": "susam",
    "sesame": "susam", "celery": "celer", "mustard": "slačica", "sulphur-dioxide-and-sulphites": "sulfiti",
    "sulphites": "sulfiti", "lupin": "lupina",
}

# prosti in-memory keš (kursevi se menjaju dnevno; nema potrebe za bazom)
_fx_cache: dict | None = None
_fx_at: float = 0.0
_FX_TTL = 3600  # 1h


async def _frankfurter_eur_rates() -> tuple[dict[str, float], bool]:
    """EUR→{USD,GBP,...} sa Frankfurter-a (keširano, sa retry-jem). Vraća (kursevi, sveže).
    Ako Frankfurter padne → rezervni kursevi (sveže=False). EUR je uvek 1.0."""
    global _fx_cache, _fx_at
    if _fx_cache is not None and time.time() - _fx_at < _FX_TTL:
        return _fx_cache, True
    symbols = ",".join(c for c in TARGET_CURRENCIES if c != "EUR")
    for attempt in range(2):  # hladni start ume da tajmautuje — jedan retry
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                r = await client.get(f"{FRANKFURTER}/latest",
                                     params={"base": "EUR", "symbols": symbols})
                r.raise_for_status()
                rates = r.json().get("rates", {})
            rates["EUR"] = 1.0
            _fx_cache, _fx_at = rates, time.time()
            return rates, True
        except httpx.HTTPError:
            if attempt == 0:
                continue
            logger.warning("Frankfurter nedostupan — koristim rezervne kurseve")
    return dict(FALLBACK_EUR_RATES), False


async def currency_rates() -> dict:
    """Za svaku ponuđenu valutu vrati koliko RSD vredi 1 jedinica te valute.
    Gost deli cenu (RSD) sa tim brojem: cena_valuta = cena_rsd / rsd_per_unit."""
    eur_rates, fresh = await _frankfurter_eur_rates()
    anchor = settings.rsd_per_eur  # koliko RSD je 1 EUR (fiksno sidro)
    out = []
    for cur in TARGET_CURRENCIES:
        # 1 EUR = anchor RSD; 1 EUR = eur_rates[cur] jedinica valute cur
        # → 1 jedinica cur = anchor / eur_rates[cur] RSD
        rate = eur_rates.get(cur)
        if not rate:
            continue
        out.append({"currency": cur, "rsd_per_unit": round(anchor / rate, 4)})
    return {"base": "RSD", "anchor_rsd_per_eur": anchor, "fresh": fresh, "rates": out}


async def suggest_allergens(query: str) -> dict:
    """Predlog alergena za dati naziv proizvoda sa OpenFoodFacts-a. Degradira mekano:
    ako je OFF nedostupan/spor, vraća praznu listu (available=False) umesto greške —
    predlog alergena je pomoćna funkcija, ne sme da obori uređivanje menija."""
    products = None
    for attempt in range(2):  # OFF ume da tajmautuje na uzastopne pozive
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                r = await client.get(OFF_SEARCH, params={
                    "search_terms": query, "search_simple": 1, "json": 1, "page_size": 3,
                    "fields": "product_name,allergens_tags",
                })
                r.raise_for_status()
                products = r.json().get("products", [])
            break
        except httpx.HTTPError:
            if attempt == 0:
                continue
            logger.warning("OpenFoodFacts nedostupan za '%s'", query)
    if products is None:
        return {"query": query, "matched_product": None, "allergens": [], "available": False}
    tags: list[str] = []
    for p in products:
        for tag in p.get("allergens_tags", []):
            key = tag.split(":", 1)[-1]  # "en:milk" → "milk"
            label = ALLERGEN_MAP.get(key)
            if label and label not in tags:
                tags.append(label)
    match = products[0].get("product_name") if products else None
    return {"query": query, "matched_product": match, "allergens": tags, "available": True}
