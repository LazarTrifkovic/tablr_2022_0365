"""End-to-end test tablr demo toka: meni -> porudzbina -> WS tiket -> status."""
import asyncio
import hashlib
import hmac
import json
import sys

import httpx
import websockets

BASE = "http://localhost:8000"
QR_SECRET = "dev-secret-change-in-prod"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} | {name} {('- ' + detail) if detail else ''}")


def sign(cafe_id: str, table: int) -> str:
    return hmac.new(QR_SECRET.encode(), f"{cafe_id}:{table}".encode(),
                    hashlib.sha256).hexdigest()


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE, timeout=10) as c:
        # 1. zdravlje sistema
        r = await c.get("/health")
        services = r.json().get("services", {})
        check("health: svi servisi ok", all(v == "ok" for v in services.values()),
              str(services))

        # 2. meni
        r = await c.get("/api/menu/cafes")
        cafes = r.json()
        check("menu: lista kafica", r.status_code == 200 and len(cafes) == 1,
              cafes[0]["name"] if cafes else "prazno")
        cafe_id = cafes[0]["id"]

        r = await c.get(f"/api/menu/cafes/{cafe_id}/menu")
        menu = r.json()
        n_items = sum(len(cat["items"]) for cat in menu["categories"])
        check("menu: kategorije i stavke", len(menu["categories"]) == 4 and n_items == 20,
              f"{len(menu['categories'])} kategorija, {n_items} stavki")
        espresso = menu["categories"][0]["items"][0]
        limunada = next(i for cat in menu["categories"] for i in cat["items"]
                        if i["name"] == "Limunada")

        # 3. bezbednost: interne rute blokirane na gateway-u
        r = await c.get("/api/menu/internal/items", params={"ids": "x"})
        check("gateway: /internal blokiran spolja", r.status_code == 403)
        r = await c.get("/api/orders/dev/sign",
                        params={"cafe_id": "x", "table_number": 1})
        check("gateway: /dev blokiran spolja", r.status_code == 403)

        # 4. bezbednost: pogresan QR potpis odbijen
        r = await c.post("/api/orders/orders", json={
            "cafe_id": cafe_id, "table_number": 5, "sig": "falsifikat",
            "items": [{"item_id": espresso["id"], "qty": 1}],
        })
        check("orders: falsifikovan potpis -> 403", r.status_code == 403)

        # 5. WS slusalac (glumi bar dashboard) + prava porudzbina
        received: list[dict] = []
        async with websockets.connect(
                f"ws://localhost:8000/ws/bar/{cafe_id}") as ws:

            async def listener() -> None:
                async for msg in ws:
                    received.append(json.loads(msg))

            listen_task = asyncio.create_task(listener())

            r = await c.post("/api/orders/orders", json={
                "cafe_id": cafe_id, "table_number": 5,
                "sig": sign(cafe_id, 5), "note": "bez leda",
                "items": [{"item_id": espresso["id"], "qty": 2},
                          {"item_id": limunada["id"], "qty": 1}],
            })
            order = r.json()
            expected_total = espresso["price"] * 2 + limunada["price"]
            check("orders: porudzbina kreirana", r.status_code == 201,
                  f"status={r.status_code}")
            check("orders: total ispravan (cene sa servera)",
                  order.get("total") == expected_total,
                  f"{order.get('total')} == {expected_total}")

            await asyncio.sleep(1.5)
            created = [e for e in received if e.get("type") == "ticket.created"]
            check("WS: tiket stigao na bar dashboard u realnom vremenu",
                  len(created) == 1 and created[0]["ticket"]["order_id"] == order["id"],
                  f"primljeno {len(received)} poruka")

            # 6. barmen prihvata porudzbinu -> status se vraca u orders + WS event
            r = await c.patch(f"/api/bar/tickets/{order['id']}/status",
                              json={"status": "ACCEPTED"})
            check("barkds: barmen menja status", r.status_code == 200)

            await asyncio.sleep(1.5)
            updated = [e for e in received if e.get("type") == "ticket.updated"]
            check("WS: promena statusa emitovana", len(updated) == 1)

            r = await c.get(f"/api/orders/orders/{order['id']}")
            check("orders: status sinhronizovan (ACCEPTED)",
                  r.json().get("status") == "ACCEPTED", r.json().get("status", "?"))
            check("orders: accepted_at timestamp zabelezen (statistika)",
                  r.json().get("accepted_at") is not None,
                  str(r.json().get("accepted_at")))

            # 7. nevalidna tranzicija odbijena (CREATED<-... vec je ACCEPTED)
            r = await c.patch(f"/api/bar/tickets/{order['id']}/status",
                              json={"status": "DELIVERED"})
            check("orders: nevalidna tranzicija ACCEPTED->DELIVERED odbijena",
                  r.status_code == 409, f"status={r.status_code}")

            # 8. gost vidi aktivne porudzbine svog stola
            r = await c.get(f"/api/orders/tables/{cafe_id}/5/orders",
                            params={"sig": sign(cafe_id, 5)})
            check("orders: gost vidi porudzbine svog stola",
                  r.status_code == 200 and len(r.json()) == 1)
            r = await c.get(f"/api/orders/tables/{cafe_id}/3/orders",
                            params={"sig": sign(cafe_id, 5)})
            check("orders: potpis stola 5 ne otvara sto 3 (anti-IDOR)",
                  r.status_code == 403)

            # 9. pozovi konobara: pogresan potpis, kreiranje, WS, anti-spam, resolve
            r = await c.post("/api/bar/requests", json={
                "cafe_id": cafe_id, "table_number": 5, "sig": "laz", "kind": "waiter"})
            check("requests: falsifikovan potpis -> 403", r.status_code == 403)

            r = await c.post("/api/bar/requests", json={
                "cafe_id": cafe_id, "table_number": 5,
                "sig": sign(cafe_id, 5), "kind": "waiter"})
            req = r.json()
            check("requests: poziv konobara kreiran", r.status_code == 201)

            await asyncio.sleep(1.5)
            req_created = [e for e in received if e.get("type") == "request.created"]
            check("WS: zahtev stigao na bar (crno/beli alert)",
                  len(req_created) == 1 and
                  req_created[0]["request"]["table_number"] == 5)

            r = await c.post("/api/bar/requests", json={
                "cafe_id": cafe_id, "table_number": 5,
                "sig": sign(cafe_id, 5), "kind": "waiter"})
            check("requests: anti-spam (isti sto+vrsta -> isti zahtev)",
                  r.json().get("id") == req["id"])

            r = await c.patch(f"/api/bar/requests/{req['id']}/resolve")
            check("requests: konobar resio zahtev", r.status_code == 200)
            await asyncio.sleep(1.5)
            req_resolved = [e for e in received if e.get("type") == "request.resolved"]
            check("WS: resolve emitovan (alert nestaje)", len(req_resolved) == 1)

            listen_task.cancel()

        # 10. dostupnost i napomena stavke (bar tab Meni)
        r = await c.patch(f"/api/menu/cafes/{cafe_id}/items/{limunada['id']}",
                          json={"available": False, "note": "danas bez limuna"})
        check("menu: stavka oznacena kao nedostupna + napomena",
              r.status_code == 200 and r.json()["available"] is False
              and r.json()["note"] == "danas bez limuna")

        r = await c.post("/api/orders/orders", json={
            "cafe_id": cafe_id, "table_number": 5, "sig": sign(cafe_id, 5),
            "items": [{"item_id": limunada["id"], "qty": 1}]})
        check("orders: porudzbina nedostupne stavke odbijena (409)",
              r.status_code == 409, f"status={r.status_code}")

        r = await c.get(f"/api/menu/cafes/{cafe_id}/menu")
        lim = next(i for cat in r.json()["categories"] for i in cat["items"]
                   if i["id"] == limunada["id"])
        check("menu: gost vidi napomenu u meniju",
              lim["note"] == "danas bez limuna" and lim["available"] is False)

        r = await c.patch(f"/api/menu/cafes/{cafe_id}/items/{limunada['id']}",
                          json={"available": True, "note": None})
        check("menu: stavka vracena u ponudu", r.status_code == 200
              and r.json()["available"] is True and r.json()["note"] is None)

        # 11. mapa stolova: lista stolova + izracunat tables_count
        r = await c.get("/api/menu/cafes")
        cafe0 = r.json()[0]
        tables = cafe0.get("tables")
        check("menu: stolovi za mapu (tables + tables_count)",
              isinstance(tables, list) and len(tables) > 0
              and cafe0.get("tables_count") == len(tables),
              f"tables_count={cafe0.get('tables_count')}, len(tables)="
              f"{len(tables) if isinstance(tables, list) else 'n/a'}")

    failed = [r for r in results if not r[1]]
    print(f"\n{'='*50}\nUKUPNO: {len(results)} testova, "
          f"{len(results)-len(failed)} proslo, {len(failed)} palo")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
