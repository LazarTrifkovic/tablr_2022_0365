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

        # 1b. prijava osoblja — vlasnik token postaje default (staff pozivi ga koriste,
        # gost rute ga ignorišu jer koriste HMAC potpis)
        r = await c.post("/api/auth/login", json={
            "email": "vlasnik@panorama.rs", "password": "vlasnik123"})
        check("auth: prijava vlasnika vraća JWT",
              r.status_code == 200 and "access_token" in r.json())
        vlasnik_token = r.json()["access_token"]
        r = await c.post("/api/auth/login", json={
            "email": "konobar@panorama.rs", "password": "konobar123"})
        konobar_token = r.json()["access_token"]
        r = await c.post("/api/auth/login", json={
            "email": "vlasnik@panorama.rs", "password": "pogresna"})
        check("auth: pogrešna lozinka -> 401", r.status_code == 401)
        c.headers["Authorization"] = f"Bearer {vlasnik_token}"

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

            # 8. gost vidi aktivne porudzbine svog stola (otporno na nagomilane porudzbine:
            # tvoja porudzbina je vidljiva i NIJEDNA nije sa tudjeg stola)
            r = await c.get(f"/api/orders/tables/{cafe_id}/5/orders",
                            params={"sig": sign(cafe_id, 5)})
            mine = r.json()
            check("orders: gost vidi porudzbine svog stola",
                  r.status_code == 200 and any(o["id"] == order["id"] for o in mine)
                  and all(o["table_number"] == 5 for o in mine),
                  f"n={len(mine)}")
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

        # 12. ceo životni ciklus + arhiva smene (plaćanje + ocena gosta)
        r = await c.get(f"/api/menu/cafes/{cafe_id}/menu")
        espresso = r.json()["categories"][0]["items"][0]
        r = await c.post("/api/orders/orders", json={
            "cafe_id": cafe_id, "table_number": 7, "sig": sign(cafe_id, 7),
            "items": [{"item_id": espresso["id"], "qty": 2}]})
        arch_order = r.json()
        oid = arch_order["id"]
        await c.patch(f"/api/bar/tickets/{oid}/status", json={"status": "ACCEPTED"})
        await c.patch(f"/api/bar/tickets/{oid}/status", json={"status": "READY"})
        r = await c.patch(f"/api/bar/tickets/{oid}/status",
                          json={"status": "DELIVERED", "payment_method": "card"})
        check("orders: isporuka belezi nacin placanja",
              r.status_code == 200)
        r = await c.get(f"/api/orders/orders/{oid}")
        check("orders: payment_method sacuvan (evidencija smene)",
              r.json().get("payment_method") == "card",
              str(r.json().get("payment_method")))

        # gost ocenjuje isporucenu porudzbinu (potpis stola stiti od tudje ocene)
        r = await c.post(f"/api/orders/orders/{oid}/rating",
                         json={"sig": "laz", "rating": 5})
        check("rating: falsifikovan potpis odbijen (403)", r.status_code == 403)
        r = await c.post(f"/api/orders/orders/{oid}/rating",
                         json={"sig": sign(cafe_id, 7), "rating": 5,
                               "comment": "Odlicno!"})
        check("rating: gost ocenio isporucenu porudzbinu",
              r.status_code == 200 and r.json().get("rating") == 5)

        # arhiva je samo za vlasnika — konobar dobija 403, bez tokena 401
        r = await c.get("/api/orders/orders/history", params={"cafe_id": cafe_id},
                        headers={"Authorization": f"Bearer {konobar_token}"})
        check("auth: konobar ne sme arhivu (403)", r.status_code == 403)
        r = await c.get("/api/orders/orders/history", params={"cafe_id": cafe_id},
                        headers={"Authorization": ""})
        check("auth: arhiva bez tokena (401)", r.status_code == 401)

        # arhiva sadrzi zavrsenu porudzbinu sa svim podacima za bilans smene (vlasnik token je default)
        r = await c.get("/api/orders/orders/history", params={"cafe_id": cafe_id})
        hist = r.json()
        mine = next((h for h in hist if h["id"] == oid), None)
        check("arhiva: zavrsena porudzbina vidljiva sa placanjem i ocenom",
              r.status_code == 200 and mine is not None
              and mine["payment_method"] == "card" and mine["rating"] == 5,
              f"nadjeno={mine is not None}")

        # 13. zbirni racun stola + podela (konobar naplacuje izabrane stavke)
        r = await c.get(f"/api/menu/cafes/{cafe_id}/menu")
        cats = r.json()["categories"]
        it_a, it_b = cats[0]["items"][0], cats[0]["items"][1]
        # dva "gosta" za stolom 8
        await c.post("/api/orders/orders", json={
            "cafe_id": cafe_id, "table_number": 8, "sig": sign(cafe_id, 8),
            "items": [{"item_id": it_a["id"], "qty": 1}]})
        await c.post("/api/orders/orders", json={
            "cafe_id": cafe_id, "table_number": 8, "sig": sign(cafe_id, 8),
            "items": [{"item_id": it_b["id"], "qty": 1}]})

        r = await c.get(f"/api/orders/tables/{cafe_id}/8/bill",
                        params={"sig": sign(cafe_id, 8)})
        bill = r.json()
        names = [bi["name"] for bi in bill["items"]]
        check("racun: zbirni racun stola (sve stavke + ukupno)",
              r.status_code == 200 and it_a["name"] in names and it_b["name"] in names
              and bill["subtotal"] == sum(bi["line_total"] for bi in bill["items"])
              and bill["remaining"] >= it_a["price"] + it_b["price"],
              f"remaining={bill.get('remaining')}")

        r = await c.get(f"/api/orders/tables/{cafe_id}/8/bill", params={"sig": "laz"})
        check("racun: falsifikovan potpis -> 403", r.status_code == 403)

        # gost trazi da konobar naplati jednu (neplacenu) stavku (bill_split zahtev)
        pick = next(bi for bi in bill["items"] if not bi["paid"])
        r = await c.post("/api/bar/requests", json={
            "cafe_id": cafe_id, "table_number": 8, "sig": sign(cafe_id, 8),
            "kind": "bill_split", "detail": f'{pick["qty"]}x {pick["name"]}',
            "item_ids": [pick["order_item_id"]], "amount": pick["line_total"]})
        check("podela: zahtev za naplatu izabranih stavki kreiran",
              r.status_code == 201 and r.json().get("item_ids") == [pick["order_item_id"]])

        # konobar naplacuje te stavke -> otpadaju sa racuna
        r = await c.post(f"/api/orders/tables/{cafe_id}/8/bill/settle",
                         json={"order_item_ids": [pick["order_item_id"]],
                               "payment_method": "cash"})
        b2 = r.json()
        check("podela: naplacena stavka obelezena placenom i skinuta sa preostalog",
              r.status_code == 200 and b2["remaining"] == bill["remaining"] - pick["line_total"]
              and any(i["paid"] for i in b2["items"]),
              f"remaining={b2.get('remaining')}")

        # 14. gost otkazuje porudžbinu dok je CREATED (+ CAS zaštita)
        r = await c.get(f"/api/menu/cafes/{cafe_id}/menu")
        one = r.json()["categories"][0]["items"][0]

        async def make_order(tn: int) -> str:
            rr = await c.post("/api/orders/orders", json={
                "cafe_id": cafe_id, "table_number": tn, "sig": sign(cafe_id, tn),
                "items": [{"item_id": one["id"], "qty": 1}]})
            return rr.json()["id"]

        oid = await make_order(9)
        r = await c.post(f"/api/orders/orders/{oid}/cancel",
                         json={"sig": sign(cafe_id, 9)})
        check("otkazivanje: gost otkazao CREATED porudzbinu",
              r.status_code == 200 and r.json().get("status") == "CANCELLED",
              f"status={r.status_code}")

        r = await c.get(f"/api/orders/tables/{cafe_id}/9/orders",
                        params={"sig": sign(cafe_id, 9)})
        check("otkazivanje: otkazana nestala iz gostove liste",
              all(o["id"] != oid for o in r.json()))

        r = await c.post(f"/api/orders/orders/{oid}/cancel",
                         json={"sig": sign(cafe_id, 9)})
        check("otkazivanje: ponovno otkazivanje -> 409", r.status_code == 409)

        r = await c.post(f"/api/orders/orders/{oid}/cancel", json={"sig": "laz"})
        check("otkazivanje: falsifikovan potpis -> 403", r.status_code == 403)

        oid2 = await make_order(9)
        await c.patch(f"/api/bar/tickets/{oid2}/status", json={"status": "ACCEPTED"})
        r = await c.post(f"/api/orders/orders/{oid2}/cancel",
                         json={"sig": sign(cafe_id, 9)})
        check("otkazivanje: posle prihvatanja -> 409 (CAS trka)", r.status_code == 409)

        # 15. online plaćanje kroz Payments servis (Google Pay TEST tok)
        r = await c.get(f"/api/menu/cafes/{cafe_id}/menu")
        gp_item = r.json()["categories"][0]["items"][0]
        await c.post("/api/orders/orders", json={
            "cafe_id": cafe_id, "table_number": 6, "sig": sign(cafe_id, 6),
            "items": [{"item_id": gp_item["id"], "qty": 1}]})
        r = await c.get(f"/api/orders/tables/{cafe_id}/6/bill",
                        params={"sig": sign(cafe_id, 6)})
        gp_bill = r.json()
        gp_ids = [i["order_item_id"] for i in gp_bill["items"] if not i["paid"]]

        r = await c.post("/api/payments/pay", json={
            "cafe_id": cafe_id, "table_number": 6, "sig": "laz",
            "order_item_ids": gp_ids, "amount": gp_bill["remaining"], "token": "t"})
        check("payments: falsifikovan potpis -> 403", r.status_code == 403)

        r = await c.post("/api/payments/pay", json={
            "cafe_id": cafe_id, "table_number": 6, "sig": sign(cafe_id, 6),
            "order_item_ids": gp_ids, "amount": gp_bill["remaining"],
            "token": '{"fake":"gpay-test-token"}'})
        check("payments: online placanje obelezava stavke placenim",
              r.status_code == 200 and r.json().get("status") == "paid")

        r = await c.get(f"/api/orders/tables/{cafe_id}/6/bill",
                        params={"sig": sign(cafe_id, 6)})
        check("payments: racun stola posle online placanja = 0",
              r.json()["remaining"] == 0, f"remaining={r.json()['remaining']}")

        # 16. eksterni API-ji (Frankfurter kursevi + OpenFoodFacts alergeni)
        r = await c.get("/api/menu/fx")
        fx = r.json()
        curs = {x["currency"] for x in fx.get("rates", [])}
        check("eksterni: Frankfurter kursevi (EUR/USD, RSD baza)",
              r.status_code == 200 and fx.get("base") == "RSD"
              and "EUR" in curs and "USD" in curs
              and all(x["rsd_per_unit"] > 0 for x in fx["rates"]),
              f"valute={sorted(curs)} fresh={fx.get('fresh')}")

        r = await c.get("/api/menu/allergens/search", params={"q": "cappuccino"})
        al = r.json()
        check("eksterni: OpenFoodFacts predlog alergena",
              r.status_code == 200 and "allergens" in al
              and isinstance(al["allergens"], list),
              f"matched={al.get('matched_product')} → {al.get('allergens')}")

        # 17. editor mape — vlasnik snima raspored (PATCH tables), zaštita + validacija
        r = await c.get("/api/menu/cafes")
        before = r.json()[0]["tables"]  # trenutni raspored (da ga vratimo na kraju)

        new_layout = {"tables": [
            {"number": 1, "zone": "Test", "shape": "round", "seats": 4,
             "x": 10, "y": 10, "w": 14, "h": 14},
            {"number": 2, "shape": "square", "x": 40, "y": 40, "w": 12, "h": 12},
        ]}
        r = await c.patch(f"/api/menu/cafes/{cafe_id}/tables", json=new_layout,
                          headers={"Authorization": ""})
        check("editor mape: bez tokena -> 401", r.status_code == 401)
        r = await c.patch(f"/api/menu/cafes/{cafe_id}/tables", json=new_layout,
                          headers={"Authorization": f"Bearer {konobar_token}"})
        check("editor mape: konobar ne sme -> 403", r.status_code == 403)
        r = await c.patch(f"/api/menu/cafes/{cafe_id}/tables",
                          json={"tables": [{"number": 1}, {"number": 1}]})
        check("editor mape: duplirani broj stola -> 400", r.status_code == 400)
        r = await c.patch(f"/api/menu/cafes/{cafe_id}/tables",
                          json={"tables": [{"number": 1, "x": 150, "y": 10}]})
        check("editor mape: pozicija van opsega -> 422", r.status_code == 422)

        r = await c.patch(f"/api/menu/cafes/{cafe_id}/tables", json=new_layout)
        saved = r.json()
        check("editor mape: vlasnik snimio raspored",
              r.status_code == 200 and saved["tables_count"] == 2
              and saved["tables"][0]["shape"] == "round"
              and saved["tables"][0]["seats"] == 4,
              f"count={saved.get('tables_count')}")

        # vrati originalni raspord (idempotentan test)
        restore = {"tables": [{k: t[k] for k in
                   ("number", "zone", "label", "shape", "seats", "x", "y", "w", "h")}
                   for t in before]}
        r = await c.patch(f"/api/menu/cafes/{cafe_id}/tables", json=restore)
        check("editor mape: originalni raspored vraćen",
              r.status_code == 200 and r.json()["tables_count"] == len(before))

    failed = [r for r in results if not r[1]]
    print(f"\n{'='*50}\nUKUPNO: {len(results)} testova, "
          f"{len(results)-len(failed)} proslo, {len(failed)} palo")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
