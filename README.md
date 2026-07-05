# tablr

Sistem za QR poručivanje u kafićima — gost skenira QR kod na stolu, naručuje sa
telefona, a porudžbina u realnom vremenu stiže osoblju na ekran.

Projekat iz predmeta **Razvoj naprednih aplikacija elektronskog poslovanja**.

## Arhitektura

Mikroservisna arhitektura (Database-per-service) sa API Gateway-em kao jedinom
ulaznom tačkom:

| Komponenta | Putanja | Tehnologija | Baza |
|---|---|---|---|
| API Gateway | `gateway/` | FastAPI | — |
| Meni (Catalog) | `services/menu/` | FastAPI | MongoDB |
| Porudžbine (Orders) | `services/orders/` | FastAPI | PostgreSQL |
| Bar / KDS | `services/barkds/` | FastAPI | MongoDB |
| Auth | `services/auth/` | FastAPI | PostgreSQL |
| Plaćanje (Payments) | `services/payments/` | FastAPI | PostgreSQL |
| Gost aplikacija | `frontend/guest/` | React + Vite + TS | — |
| Bar dashboard | `frontend/bar/` | React + Vite + TS | — |
| Admin panel | `frontend/admin/` | React + Vite + TS | — |

Asinhrona komunikacija između servisa: Apache Kafka (u kasnijoj fazi).
Monitoring: Prometheus + Grafana (u kasnijoj fazi).

## Preduslovi

- Docker + Docker Compose

## Pokretanje

```bash
docker compose up --build
```

Provera da sistem radi:

```bash
curl http://localhost:8000/health
```

Očekivan odgovor — gateway i svih 5 servisa `ok`:

```json
{"gateway": "ok", "services": {"menu": "ok", "orders": "ok", "barkds": "ok", "auth": "ok", "payments": "ok"}}
```

## Struktura repozitorijuma

```
tablr/
├── gateway/            # API Gateway (jedina ulazna tačka)
├── services/           # mikroservisi (svaki sa sopstvenom bazom)
├── frontend/           # klijentske aplikacije (guest / bar / admin)
├── infra/              # infrastruktura (Kafka, Prometheus, Grafana...)
├── docs/               # projektna dokumentacija
└── docker-compose.yml  # podizanje celokupnog okruženja
```

## Radni tok (GitFlow)

- `main` — isključivo stabilne, tagovane verzije (v1.0.0, ...)
- `develop` — integraciona grana
- `feature/*` — razvoj funkcionalnosti, spajanje u `develop` putem pull request-ova
