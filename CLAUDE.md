# tablr — QR poručivanje za kafiće

Mikroservisni sistem: gost skenira QR kod na stolu → naruči sa telefona → porudžbina
u realnom vremenu stiže baru. Projekat iz predmeta RNAEP (tri faze: dokumentacija,
implementacija, seminarski) + ambicija da bude prodajan SaaS. Radi se solo uz AI agente.

## Arhitektura

| Komponenta | Putanja | Stek | Baza |
|---|---|---|---|
| API Gateway (port 8000) | `gateway/` | FastAPI proxy + WS relay | — |
| Meni | `services/menu/` | FastAPI + Beanie | MongoDB `menu-db` |
| Porudžbine | `services/orders/` | FastAPI + SQLAlchemy async | PostgreSQL `orders-db` |
| Bar/KDS | `services/barkds/` | FastAPI + Beanie + WS push | MongoDB `barkds-db` |
| Auth (skelet, Faza 3) | `services/auth/` | FastAPI | PostgreSQL |
| Payments (skelet, Faza 3) | `services/payments/` | FastAPI | PostgreSQL |
| Gost app (port 5173) | `frontend/guest/` | React + Vite + TS | — |
| Bar dashboard (port 5174) | `frontend/bar/` | React + Vite + TS | — |

Nepromenljiva pravila:
- Klijenti komuniciraju ISKLJUČIVO kroz gateway: `/api/{servis}/...` i `/ws/bar/{cafe_id}`.
- Rute `/internal` i `/dev` su blokirane na gateway-u — samo za servis↔servis saobraćaj.
- Multi-tenant: `cafe_id` na svakom entitetu. Cene: int, celi RSD.
- QR nosi HMAC potpis stola (`QR_SECRET`); cene se NIKAD ne primaju od klijenta.
- Status tok: CREATED→ACCEPTED→READY→DELIVERED (+CANCELLED). Orders servis je vlasnik
  tranzicija i beleži timestampove (accepted_at, ready_at...) za statistiku pripreme.

## Pokretanje i provera
- Ceo sistem: `docker compose up -d --build` → provera `curl http://localhost:8000/health`
- Demo QR linkovi za stolove: `python scripts/qr_links.py`
- E2E testovi (27 provera): `python tests/e2e_test.py` — traži pokrenut sistem;
  na Windows-u dodaj `PYTHONIOENCODING=utf-8`; host treba `pip install httpx websockets`

## Pinovi i zamke
- `beanie<2` + eksplicitan `motor` u requirements (beanie 2.0 je izbacio motor!)
- SQLAlchemy `create_all` NE dodaje kolone u postojeću tabelu — nova kolona u dev-u
  znači reset `tablr_orders-data` volume-a
- Docker Desktop na ovoj mašini ume da se sruši na zombi socket fajlove —
  rešenje je skripta `../popravi-docker.cmd`

## Git pravila (OCENJUJE SE na ispitu — strogo poštovati)
- GitFlow: `feature/*` → `develop` → `main` (tagovi vX.Y.Z). NIKAD direktan commit
  na develop/main; merge isključivo `--no-ff`.
- Agentske uloge koriste svoje prefikse grana: `docs/*` (dokumentacija), `tests/*` (testiranje).
- Commit poruke: conventional prefiks (feat/fix/docs/test/chore), tekst na srpskom.

## Rad sa agentima
- Uloge i uputstva po ulozi: `../agenti/<uloga>/CLAUDE.md`
- Zajednička tabla napretka: `../NAPREDAK.md` — OBAVEZNO je pročitaj na početku sesije
  i upiši jedan red u svoju sekciju posle svakog završenog zadatka.
- Piši fajlove samo unutar opsega koji tvoja uloga dozvoljava (u tvom CLAUDE.md).

## Status faza
- ✓ Faza 0 (skelet) · ✓ Faza 2 (jezgro + frontendi + product runde 1 i 2)
- → Sledeće: Faza 3 (Auth JWT, Payments, eksterni API-ji OpenFoodFacts + Frankfurter,
  admin panel + QR generisanje) → Faza 1 (dokumentacija Domaći I — može paralelno)
  → Faza 4 seminarski (Kafka, Saga/CQRS/Circuit Breaker, bezbednost, monitoring, CI/CD)
- Jezički togl SR/EN/RU: na samom kraju projekta.
