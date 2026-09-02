# tablr

Sistem za QR poručivanje u kafićima — gost skenira QR kod na stolu, naručuje sa
telefona, a porudžbina u realnom vremenu stiže osoblju na ekran.

Projekat iz predmeta **Razvoj naprednih aplikacija elektronskog poslovanja**
(FON, Katedra za elektronsko poslovanje). Dokumentacija arhitekture (Domaći I):
[`docs/domaci-1/`](docs/domaci-1/).

## Arhitektura

Mikroservisna arhitektura (Database-per-service) sa API Gateway-em kao jedinom
ulaznom tačkom:

| Komponenta | Putanja | Tehnologija | Baza |
|---|---|---|---|
| API Gateway | `gateway/` | FastAPI | — |
| Meni (Catalog) | `services/menu/` | FastAPI + Beanie | MongoDB |
| Porudžbine (Orders) | `services/orders/` | FastAPI + SQLAlchemy | PostgreSQL |
| Bar / KDS | `services/barkds/` | FastAPI + Beanie, WebSocket | MongoDB |
| Auth | `services/auth/` | FastAPI | PostgreSQL |
| Plaćanje (Payments) | `services/payments/` | FastAPI | — (bez baze, demo) |
| Izveštavanje (Reporting) | `services/reporting/` | FastAPI + Beanie (CQRS) | MongoDB |
| Gost aplikacija | `frontend/guest/` | React + Vite + TS | — |
| Bar dashboard | `frontend/bar/` | React + Vite + TS | — |
| Admin panel | `frontend/admin/` | React + Vite + TS | — |

**Asinhrona komunikacija:** Apache Kafka (KRaft) — `orders` objavljuje događaje o
životnom ciklusu porudžbine na topic `order-events`; `barkds` i `reporting` ih
konzumiraju nezavisno (decoupling, otpornost na prekid rada servisa).

**Monitoring:** Prometheus + Grafana — svi servisi izlažu `/metrics`, gotov
dashboard prati P95 latenciju i broj zahteva po servisu.

**Mikroservisni paterni:**
- **Circuit Breaker** (`app/breaker.py` u orders/barkds/payments) — sinhroni
  pozivi ka drugim servisima obmotani prekidačem (closed → open → half-open);
  posle 3 uzastopne greške prekidač se otvara i naredni pozivi odmah dobijaju
  grešku (fail-fast) umesto da čekaju timeout, dajući pozvanom servisu vremena
  da se oporavi.
- **Saga (orkestrirana)** — registracija kafića (`auth` orkestrira: prvo `menu`
  kreira kafić, pa tek onda `auth` upisuje vlasnički nalog); ako drugi korak
  padne, kompenzaciona akcija briše kafić da ne ostane osirotao zapis.
- **CQRS** — `reporting` servis je odvojen read model: sluša Kafka događaje i
  održava agregiranu statistiku (pazar, prosečna ocena) nezavisno od `orders`
  (write) baze, bez dodatnog opterećenja transakcione baze upitima za izveštaje.

## Preduslovi

- Docker + Docker Compose

## Pokretanje

```bash
docker compose up -d --build
```

Provera da sistem radi:

```bash
curl http://localhost:8000/health
```

Očekivan odgovor — gateway i svih 6 servisa `ok`:

```json
{"gateway": "ok", "services": {"menu": "ok", "orders": "ok", "barkds": "ok", "auth": "ok", "payments": "ok", "reporting": "ok"}}
```

Demo QR linkovi za stolove:

```bash
python scripts/qr_links.py
```

## Pristupne tačke

| Aplikacija | Adresa |
|---|---|
| Gost (skeniranjem QR koda ili direktno) | http://localhost:5173 |
| Bar dashboard | http://localhost:5174 |
| Admin panel | http://localhost:5175 |
| API Gateway | http://localhost:8000 |
| Grafana (monitoring) | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

Demo nalozi (bar/admin prijava): `konobar / konobar` (uloga konobar),
`admin / admin` (uloga vlasnik).

## E2E testovi

```bash
pip install -r tests/requirements.txt
python tests/e2e_test.py
```

Na Windows-u dodati `PYTHONIOENCODING=utf-8` zbog ćiriličnih/šumnika u ispisu.

## Struktura repozitorijuma

```
tablr/
├── gateway/            # API Gateway (jedina ulazna tačka)
├── services/           # mikroservisi (svaki sa sopstvenom bazom)
│   ├── menu/ orders/ barkds/ auth/ payments/ reporting/
├── frontend/            # klijentske aplikacije (guest / bar / admin)
├── monitoring/          # Prometheus + Grafana konfiguracija
├── docs/domaci-1/       # projektna dokumentacija (Domaći I)
├── tests/                # E2E testovi
├── .github/workflows/    # CI/CD (GitHub Actions)
└── docker-compose.yml    # podizanje celokupnog okruženja
```

## Bezbednost

- **HMAC-SHA256** potpis stola (`QR_SECRET`) — gostove rute su javne ali
  kriptografski dokazuju identitet stola; cene se nikad ne primaju od klijenta.
- **JWT** (HS256, TTL 12h) za osoblje/vlasnika, validacija na gateway-u; role
  `vlasnik`/`konobar` ograničavaju pristup administrativnim rutama.
- **Multi-tenant izolacija** — gateway proverava da `cafe_id` iz zahteva
  odgovara `cafe_id` iz tokena (zabrana pristupa tuđem kafiću).
- Lozinke isključivo kao **bcrypt** heš; parametrizovani upiti (SQLAlchemy ORM)
  protiv SQL injekcije; CORS ograničen na tri frontend origin-a.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) — na svaki push/PR ka
`develop`/`main`: build celog stack-a, provera `/health`, pokretanje E2E
testova.

## Radni tok (GitFlow)

- `main` — isključivo stabilne, tagovane verzije (v1.0.0, ...)
- `develop` — integraciona grana
- `feature/*` — razvoj funkcionalnosti, spajanje u `develop` isključivo putem
  pull request-ova sa pregledom koda

Repozitorijum: https://github.com/LazarTrifkovic/tablr_2022_0365
