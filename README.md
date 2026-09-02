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

**Asinhrona komunikacija:** Apache Kafka (KRaft), 4 teme:

| Topic | Producer | Consumer(i) |
|---|---|---|
| `order-created` | orders | barkds |
| `order-status-changed` | orders | barkds, reporting |
| `order-rated` | orders | reporting |
| `ticket-status-requests` | barkds | **orders** |

`orders` je **hibridni modul** (Consumer + Producer): konzumira zahteve za
promenu statusa sa `ticket-status-requests` (šalje ih barkds kad konobar
klikne dugme na dashboard-u), validira tranziciju kao vlasnik status mašine
(CAS `WHERE status=`), i publikuje rezultat na `order-status-changed` — čime je
i poslednja preostala sinhrona veza (barkds→orders) prešla na asinhronu, bez
gubitka validacije (barkds dodatno radi brzu lokalnu proveru da odmah odbije
očigledno nevalidnu tranziciju, bez čekanja na Kafka povratni krug).

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

## Bezbednost i zaštita od ranjivosti

### IDOR (Insecure Direct Object Reference)

Najozbiljnija klasa napada za ovaj domen — identifikatori (`cafe_id`,
`order_id`, broj stola) stoje direktno u URL-u. Tri sloja odbrane:

1. **Multi-tenant guard na gateway-u** (`gateway/app/main.py`) — za svaku
   zaštićenu rutu izvlači SVE `cafe_id` vrednosti iz zahteva (putanja, query,
   JSON telo) i poredi ih sa `cafe_id` iz JWT-a; svako neslaganje → **403**.
   Osoblje jednog kafića fizički ne može da dohvati podatke drugog.
2. **HMAC potpis stola** — gost ne može da izmisli broj stola: potpis nad
   `cafe_id:table_number` proverava se na svakoj gostovoj ruti (sto 5 ne
   otvara račun stola 3).
3. **Provera vlasništva nad resursom** — npr. naplata stavki proverava da
   `OrderItem` zaista pripada tom kafiću i stolu pre izmene.

### Autorizacija po ulozi

**JWT** (HS256, TTL 12h) validira gateway pre nego što zahtev stigne do
servisa: bez tokena → **401**, pogrešna uloga → **403**. Uloge `vlasnik` /
`konobar` razdvajaju prava — konobar u smeni menja samo dostupnost/napomenu/
alergene stavke, dok cenu i naziv može samo vlasnik (menu servis to dodatno
proverava na osnovu `X-Role` zaglavlja, ne veruje samo frontendu).

### SQL Injection

Nema konkatenacije SQL stringova nigde u kodu. Svi upiti idu kroz
**SQLAlchemy ORM** (`select()`, `update()`), koji parametrizuje vrednosti —
korisnički unos nikad ne postaje deo SQL sintakse. MongoDB servisi koriste
**Beanie ODM** sa tipiziranim upitima (nema `$where` ni evaluacije stringova).

### XSS (Cross-Site Scripting)

- **Izlaz:** React automatski enkodira sav tekst umetnut u DOM; nigde u
  kodu se ne koristi `dangerouslySetInnerHTML`, pa unos gosta (npr. napomena
  uz porudžbinu) ne može da se izvrši kao skripta na bar dashboard-u.
- **Ulaz:** Pydantic modeli validiraju tip i dužinu svakog polja pre nego što
  podatak uđe u bazu (npr. `table_number: int` sa opsegom, `note: str` sa
  ograničenom dužinom).

### CORS

Gateway (`CORSMiddleware`) dozvoljava isključivo tri poznata frontend
origin-a (`localhost:5173/5174/5175`) — **nije** `*`. Zahtev sa bilo kog
drugog domena browser odbija pre slanja.

### CSRF (Cross-Site Request Forgery)

Sistem je **po dizajnu imun** na CSRF: JWT se šalje u `Authorization: Bearer`
zaglavlju koje JavaScript eksplicitno postavlja, a **ne u kolačiću**. Browser
ne dodaje takvo zaglavlje automatski na zahteve sa tuđeg sajta, pa napadačeva
stranica ne može da izvrši akciju u ime prijavljenog konobara — nema šta da
se „ukrade" jer se ništa ne šalje automatski. (Anti-CSRF token je neophodan
kod cookie-based sesija; ovde bi bio suvišan sloj. Ako bi se autentifikacija
ikad prebacila na kolačiće, tada bi token — ili `SameSite=Strict` — postao
obavezan.)

### Ostalo

- Lozinke isključivo kao **bcrypt** heš — nikad u čitljivom obliku, ni u logu.
- **Interne rute** (`/internal/*`, `/dev/*`) tvrdo blokirane na gateway-u →
  dostupne samo servis-servis saobraćaju unutar Docker mreže.
- **Cene se nikad ne primaju od klijenta** — server ih ponovo računa iz
  kataloga pri svakom kreiranju porudžbine.

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
