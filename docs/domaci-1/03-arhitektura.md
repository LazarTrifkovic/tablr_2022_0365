# 3. Projektovanje arhitekture aplikacije

## 3.1 Software Architecture Canvas

**Softverski sistem:** tablr — QR poručivanje za kafiće
**Projektantski tim:** 1 član (samostalna izrada, RNAEP; ime/prezime i broj
indeksa iz tabele na naslovnoj strani) — implementacija uz pomoć AI agenata
u ulogama (implementacija, recenzija, testiranje, istraživanje, dokumentacija)
**Datum:** 28.7.2026.
**Iteracija:** Iteracija 1 (Domaći I) — stanje posle Faze 2 (jezgro: meni,
porudžbine, bar/KDS + product runde 1–2) i Faze 3 (Auth, Payments demo,
eksterni API-ji, admin panel, editor mape stolova)

| Polje canvasa | Sadržaj |
|---|---|
| **Poslovni problem (Business Case)** | U manjim ugostiteljskim objektima (kafići, barovi, splavovi) tokom špica, malobrojno osoblje gubi vreme na komunikaciju sa gostima umesto na uslugu: gost fizički doziva konobara da poruči, pita za dostupnost, traži račun i dogovara podelu plaćanja. tablr uklanja to usko grlo — gost sam poručuje i prati porudžbinu sa telefona (QR kod, bez naloga), a konobar dobija sve uživo na dashboard. Cilj: manje trčanja po konobaru, brža rotacija stolova, merljiv uvid vlasnika u učinak smene. Sistem je zamišljen i kao prodajan multi-tenant SaaS (jedna instalacija opslužuje više nezavisnih kafića), ne samo kao školski projekat jednog lokala. |
| **Pregled funkcionalnih zahteva** | Gost (FZ-1 do FZ-6, FZ-14): poručivanje sa menija, status uživo, poziv konobara/račun, otkazivanje, pregled i podela računa, online i gotovinsko/kartično plaćanje preko konobara, ocenjivanje, prikaz cene u stranoj valuti. Osoblje/konobar (FZ-7, FZ-8): bar dashboard uživo, promena statusa tiketa, ograničena izmena dostupnosti stavki. Vlasnik/administracija (FZ-9, FZ-10 do FZ-13, FZ-15, FZ-16): arhiva i pazar smene, onboarding kafića, pun CRUD menija, predlog alergena, generisanje QR kodova, upravljanje osobljem, uređivanje mape stolova. Puna specifikacija: `02-korisnicki-zahtevi.md`. |
| **Kontekst** | Tri ljudska aktera: **Gost** (anoniman, identifikovan HMAC potpisom stola), **Konobar** i **Vlasnik** (autentifikovani JWT-om, različita prava). Tri eksterna sistema: **Frankfurter** (kursevi valuta), **OpenFoodFacts** (predlog alergena), **Google Pay TEST** (demo tokenizacija kartice; u produkciji bi ga zamenio pravi domaći PSP). Sistem se sastoji od tri korisnička frontenda (gost, bar, admin) i šest backend mikroservisa iza jednog API gateway-a. |
| **Organizaciona ograničenja** | Projekat radi jedan student solo (uz AI agente u jasno razdvojenim ulogama, GitFlow disciplina — `feature/*` → `develop` → `main`, isključivo `--no-ff` merge). Rok je ispitni (tri faze predmeta: dokumentacija, implementacija, seminarski). Budžet je 0 — svi eksterni API-ji koji se koriste su besplatni (Frankfurter, OpenFoodFacts, Google Pay TEST environment); nema registrovane firme niti PSP ugovora, pa je online plaćanje isključivo demo. GitHub Classroom repo (remote, Issues/PR tok) još nije registrovan. |
| **Tehnička ograničenja** | Ceo stek: Python/FastAPI (backend), React+Vite+TypeScript (tri frontenda), Docker Compose orkestracija (bez Kubernetes-a) na jednoj razvojnoj mašini (Windows). Poliglot perzistencija: PostgreSQL (orders, auth — ACID i relacije bitne) i MongoDB (menu, barkds — polustrukturirani/brzo-menjajući podaci). Sinhrona REST komunikacija servis↔servis (nema message broker-a u ovoj iteraciji — Kafka je planirana za Fazu 4/seminarski). Svi servisi dele dva tajna ključa preko env promenljivih: `QR_SECRET` (HMAC potpis stola) i `JWT_SECRET` (HS256, deljen između auth servisa koji izdaje token i gateway-a koji ga validira). Gateway je jedina spoljna ulazna tačka — `/internal/*` i `/dev/*` rute su na njemu tvrdo blokirane. |
| **Atributi kvaliteta** | Dostupnost (NFZ-1, NFZ-2), skaliranje (NFZ-3 do NFZ-5), konzistentnost podataka (NFZ-6 do NFZ-8), performanse (NFZ-9), bezbednost (NFZ-10 do NFZ-12: HMAC identitet stola, JWT+uloge na gateway-u, bcrypt lozinke). Detaljne projektovane vrednosti: `02-korisnicki-zahtevi.md`, poglavlje 2.3. |
| **Hipoteze arhitekture softvera** | (1) Dekompozicija po poslovnom domenu (meni, porudžbine, bar/KDS, auth, payments) drži servise nezavisno razvojnim i deployable — potvrđeno kroz 7+ feature grana rađenih bez međusobnog blokiranja. (2) Poliglot perzistencija: relaciona baza tamo gde su tranzakcije/CAS kritični (orders — status mašina, naplata; auth — nalozi), dokumentna baza tamo gde je šema fleksibilna i čita se pretežno cela agregacija odjednom (menu — katalog i mapa stolova; barkds — tiketi/zahtevi). (3) Gateway kao jedina ulazna tačka + deljeni JWT secret omogućava stateless autentifikaciju bez posebnog session-store-a i bez servisa koji ponovo pozivaju auth servis da provere token. (4) Eventualna konzistentnost je prihvatljiva između orders (izvor istine za status) i barkds (kopija za prikaz) jer je vremenski prozor neusklađenosti u praksi ispod sekunde (best-effort HTTP notifikacija), a CAS na orders strani sprečava da neusklađenost ikad postane netačna (samo kratkotrajno zakasnela). (5) Servisi koji zahtevaju cross-service podatak (npr. orders treba cenu iz menu, payments treba da naloži orders naplatu) to rade sinhronim internim REST pozivom zaštićenim na gateway nivou, umesto deljene baze — svaki servis ostaje jedini vlasnik svoje šeme. |
| **Tehnički izazovi i rizici** | (1) *Nema distribuirane transakcije preko servisa* — npr. onboarding (auth→menu `/internal/cafes` pa lokalni upis User-a) ili orders→menu validacija pri kreiranju porudžbine: delimičan neuspeh može ostaviti osiroteo zapis (kafić bez vlasnika ako auth padne posle uspešnog poziva menu-u); danas nema kompenzacione (Saga) logike — planirano razmatranje u Fazi 4. (2) *In-memory WebSocket menadžer u barkds* (`ConnectionManager`, `dict[cafe_id] -> set[WebSocket]` u memoriji procesa) ne bi radio ispravno sa više replika servisa bez deljenog pub/sub sloja (npr. Redis) — trenutno OK jer se pokreće tačno jedna instanca po servisu. (3) *Zavisnost od dostupnosti eksternih API-ja* (Frankfurter, OpenFoodFacts) ublažena kešom (1h) i rezervnim vrednostima, ali oba su javna besplatna dobra bez SLA garancije. (4) *Deljeni tajni ključevi kroz env promenljive* (`QR_SECRET`, `JWT_SECRET`) nemaju rotacionu strategiju — kompromitovan ključ zahteva restart svih servisa sa novim ključem i nevaženje svih postojećih QR nalepnica/tokena. (5) *Payments servis je demo* (Google Pay TEST, bez pravog PSP-a) — prelazak na produkciju (npr. Raiffeisen RaiAccept/CorvusPay) i fiskalizacija nisu deo trenutne arhitekture, samo su istraženi i dokumentovani zasebno. (6) *Nema circuit breaker/retry standarda* između servisa — orders→menu i orders→barkds pozivi danas ili blokiraju zahtev (menu validacija — mora uspeti) ili su best-effort bez ponavljanja (barkds notifikacija) — nedosledno, kandidat za ujednačavanje u Fazi 4. |

---

## 3.2 Arhitektura aplikacije — C4, nivoi 1–3

> Sledeći opisi su tekstualna specifikacija za crtanje u draw.io (link ka
> crtežima ide na naslovnu stranu u Wordu). Legenda: strelica "→" = smer
> zavisnosti/poziva; u zagradi je protokol/tip veze.

### Nivo 1 — Kontekst (System Context)

**Elementi:**
- `Gost` (Person/akter) — anoniman gost za stolom
- `Konobar` (Person/akter) — osoblje, prijavljeno
- `Vlasnik` (Person/akter) — administrator kafića, prijavljen
- `tablr` (Software System, centralni pravougaonik) — ceo sistem iz perspektive konteksta
- `Frankfurter API` (External System) — javni ECB kursevi valuta
- `OpenFoodFacts API` (External System) — javna baza prehrambenih proizvoda/alergena
- `Google Pay (TEST)` (External System) — demo tokenizacija plaćanja karticom (produkcioni PSP bi zauzeo ovo mesto)

**Veze (od → ka, tip):**
- `Gost` → `tablr` : skenira QR, pregleda meni, poručuje, prati status, poziva konobara, plaća, ocenjuje (HTTPS)
- `Konobar` → `tablr` : prijavljuje se, prati tikete uživo, menja status, naplaćuje (HTTPS + WSS)
- `Vlasnik` → `tablr` : sve što i konobar + registruje kafić, uređuje meni/mapu/QR/osoblje, uvid u pazar (HTTPS)
- `tablr` → `Frankfurter API` : dobavlja tekuće kurseve valuta (HTTPS, REST)
- `tablr` → `OpenFoodFacts API` : pretražuje predlog alergena po nazivu proizvoda (HTTPS, REST)
- `Gost` → `Google Pay (TEST)` : unosi/potvrđuje karticu, sistem dobija tokenizovan payload (HTTPS, JS SDK u browseru gosta) — `tablr` nikad ne vidi sirovu karticu

### Nivo 2 — Kontejneri (Containers)

**Elementi (kontejneri unutar granice `tablr`):**

*Frontend kontejneri:*
- `Guest Web App` — React + Vite + TypeScript, port 5173 (`frontend/guest`)
- `Bar Dashboard` — React + Vite + TypeScript, port 5174 (`frontend/bar`) — koriste ga i konobar i vlasnik
- `Admin Panel` — React + Vite + TypeScript, port 5175 (`frontend/admin`) — isključivo vlasnik

*Ulazna tačka:*
- `API Gateway` — FastAPI, port 8000 (`gateway/`) — reverse-proxy prema svim servisima na putanji `/api/{servis}/...`, WebSocket relay `/ws/bar/{cafe_id}`, lokalna JWT (HS256) validacija i provera uloge za zaštićene rute, blokada `/internal/*` i `/dev/*` spolja

*Backend mikroservisi (svaki sopstvena baza — Database per Service):*
- `Auth Service` — FastAPI (`services/auth`) — registracija/prijava, izdavanje JWT, uloge
- `Auth DB` — PostgreSQL (`auth-db`, baza `auth`, tabela `users`)
- `Menu Service` — FastAPI + Beanie (`services/menu`) — katalog, mapa stolova, eksterne integracije (fx, alergeni)
- `Menu DB` — MongoDB (`menu-db`, baza `menu`, kolekcije `cafes`, `categories`, `items`)
- `Orders Service` — FastAPI + SQLAlchemy async (`services/orders`) — porudžbine, status mašina, račun, ocene
- `Orders DB` — PostgreSQL (`orders-db`, baza `orders`, tabele `orders`, `order_items`)
- `BarKDS Service` — FastAPI + Beanie + WebSocket (`services/barkds`) — tiketi i zahtevi gostiju uživo
- `BarKDS DB` — MongoDB (`barkds-db`, baza `barkds`, kolekcije `tickets`, `requests`)
- `Payments Service` — FastAPI, bez sopstvene baze (`services/payments`) — demo naplata karticom

*Eksterni sistemi:* `Frankfurter API`, `OpenFoodFacts API`, `Google Pay (TEST)` (isto kao L1)

**Veze (od → ka, tip):**
- `Gost` → `Guest Web App` (koristi, browser)
- `Konobar`, `Vlasnik` → `Bar Dashboard` (koristi, browser)
- `Vlasnik` → `Admin Panel` (koristi, browser)
- `Guest Web App` → `API Gateway` : `GET/POST /api/menu/*`, `/api/orders/*`, `/api/bar/requests` — javne rute, HMAC potpis stola u query/body (REST/JSON, HTTPS)
- `Bar Dashboard` → `API Gateway` : `/api/auth/login`, `/api/bar/*`, `/api/orders/*` — sa `Authorization: Bearer <JWT>` (REST/JSON, HTTPS) + `wss://.../ws/bar/{cafe_id}` (WebSocket)
- `Admin Panel` → `API Gateway` : `/api/auth/*`, `/api/menu/*` (kategorije/stavke/QR/mapa) — sa JWT (REST/JSON, HTTPS)
- `API Gateway` → `Auth Service` : proxy `/api/auth/{login,onboard,register,cafes/{id}/staff}` (REST/JSON); JWT validacija za ostale servise je **lokalna** na gateway-u (deljeni `JWT_SECRET`), ne poziva Auth Service
- `API Gateway` → `Menu Service` : proxy `/api/menu/*` (REST/JSON)
- `API Gateway` → `Orders Service` : proxy `/api/orders/*` (REST/JSON)
- `API Gateway` → `BarKDS Service` : proxy `/api/bar/*` (REST/JSON) + WS relay `/ws/bar/{cafe_id}` → `ws://barkds/ws/{cafe_id}`
- `API Gateway` → `Payments Service` : proxy `/api/payments/pay` (REST/JSON)
- `Auth Service` → `Auth DB` (SQL, asyncpg)
- `Auth Service` → `Menu Service` : `POST /internal/cafes` pri onboardingu — kreira kafić pre upisa vlasničkog naloga (REST/JSON, servis-servis, interna ruta)
- `Menu Service` → `Menu DB` (MongoDB driver, Beanie/motor)
- `Menu Service` → `Frankfurter API` : `GET /latest?base=EUR&symbols=...` (REST/JSON, HTTPS)
- `Menu Service` → `OpenFoodFacts API` : `GET /cgi/search.pl?...` (REST/JSON, HTTPS)
- `Orders Service` → `Orders DB` (SQL, asyncpg)
- `Orders Service` → `Menu Service` : `GET /internal/items?ids=...` — validacija stavki/cena pri kreiranju porudžbine (REST/JSON, sinhrono, blokira kreiranje)
- `Orders Service` → `BarKDS Service` : `POST /internal/tickets`, `PATCH /internal/tickets/{order_id}/status` — obaveštavanje o novoj porudžbini/promeni (REST/JSON, best-effort, ne blokira)
- `BarKDS Service` → `BarKDS DB` (MongoDB driver, Beanie/motor)
- `BarKDS Service` → `Orders Service` : `PATCH /internal/orders/{order_id}/status` — kad konobar menja status sa dashboard-a, barkds prvo traži potvrdu od orders (vlasnika mašine stanja) (REST/JSON, sinhrono)
- `Payments Service` → `Orders Service` : `POST /tables/{cafe_id}/{table_number}/bill/settle` — posle demo naplate, nalaže obeležavanje stavki plaćenim (REST/JSON, servis-servis)
- `Guest Web App` → `Google Pay (TEST)` : tokenizacija kartice u browseru (JS SDK), token zatim ide ka `Payments Service` preko gateway-a

*Napomena o mapiranju naziva:* gateway prefiks za BarKDS je `bar` (`/api/bar/...`), ne `barkds` — svuda gore korišćen naziv kontejnera `BarKDS Service`, a putanja `/api/bar/...` je tačan naziv iz koda.

### Nivo 3 — Komponente (preporučeni kontejner: `Orders Service`)

**Elementi (komponente unutar `Orders Service`):**
- `OrderRoutes` (`app/routes.py`) — HTTP rute: kreiranje porudžbine, uvid, otkazivanje, ocena, račun/naplata, arhiva, interna promena statusa
- `StatusStateMachine` (`STATUS_FLOW` u `app/models.py`) — definicija dozvoljenih tranzicija `CREATED→{ACCEPTED,CANCELLED}`, `ACCEPTED→{READY,CANCELLED}`, `READY→{DELIVERED}`, terminalna `DELIVERED`/`CANCELLED`
- `AtomicStatusUpdater` (logika uslovnog UPDATE-a u `OrderRoutes`) — izvršava CAS (`UPDATE ... WHERE id=:id AND status=:trenutni`), koristi ga i `cancel_order` i `update_status`; vraća HTTP 409 kad `rowcount == 0` (konkurentna promena)
- `TableSignatureVerifier` (`app/security.py`) — HMAC-SHA256 dokaz identiteta stola (`table_signature`, `verify_table_signature`)
- `MenuServiceClient` (HTTP klijent unutar `OrderRoutes`) — poziva menu servis (`GET /internal/items`) radi validacije stavki i cena pri kreiranju porudžbine
- `BarKdsNotifier` (HTTP klijent unutar `OrderRoutes`) — best-effort poziv barkds servisu (`POST /internal/tickets`, `PATCH /internal/tickets/{id}/status`) posle kreiranja/otkazivanja porudžbine
- `OrderRepository` (`app/models.py`, SQLAlchemy ORM klase `Order`, `OrderItem`) — mapiranje objekat↔red, veza 1:N sa kaskadnim brisanjem
- `DbSession` (`app/db.py`) — async SQLAlchemy engine/sesija ka Orders DB

**Veze (od → ka, tip):**
- `OrderRoutes` → `TableSignatureVerifier` : verifikuje potpis pre svake gostove akcije (poziv unutar procesa)
- `OrderRoutes` → `MenuServiceClient` : pri kreiranju porudžbine, traži cene/dostupnost (sinhroni REST poziv)
- `OrderRoutes` → `StatusStateMachine` : proverava da li je tražena tranzicija statusa dozvoljena (poziv unutar procesa, pre pisanja u bazu)
- `OrderRoutes` → `AtomicStatusUpdater` : izvršava CAS upis za `cancel`/`update_status` (poziv unutar procesa)
- `AtomicStatusUpdater` → `DbSession` : izvršava uslovni `UPDATE` (SQL)
- `OrderRoutes` → `OrderRepository` : čitanje/pisanje porudžbina i stavki (poziv unutar procesa → SQLAlchemy)
- `OrderRepository` → `DbSession` → `Orders DB` : SQL (asyncpg)
- `OrderRoutes` → `BarKdsNotifier` : posle uspešnog kreiranja/CAS upisa statusa, šalje obaveštenje (asinhroni/best-effort REST poziv, greška se guta i loguje)
- *(spoljna zavisnost, iz L2)* `API Gateway` → `OrderRoutes` : prosleđuje HTTP zahtev + zaglavlja `X-User`/`X-Role`/`X-Cafe` za zaštićene rute (Orders Service veruje ovim zaglavljima jer je validacija već izvršena na gateway-u)

---

## 3.3 EventStorming metodologija

> Legenda boja (obavezno u draw.io crtežu): **akter = žuto**, **komanda =
> plavo**, **događaj = narandžasto**, **polisa = ljubičasto**; agregat se
> grupiše kao okvir/lane oko pripadajućih komandi+događaja, artefakt
> (generisan dokument, npr. račun) se crta kao poseban element pored toka.

### Tok 1 — Poručivanje (US-1, servisi `menu`+`orders`+`barkds`)

`Gost` (akter) → **Pošalji porudžbinu** (komanda, `POST /api/orders/orders`)
→ ⟨polisa: *"Odbij ako potpis stola nije važeći ili je bilo koja stavka
nedostupna/nepoznata"*⟩ → **Porudžbina kreirana** (događaj, `OrderCreated`)
→ ⟨polisa: *"Kad je porudžbina kreirana, odmah generiši tiket za bar"*⟩ →
**Kreiraj tiket** (sistemska komanda, `POST /internal/tickets`) → **Tiket
kreiran** (događaj, `TicketCreated`)

Agregati: `Order` (orders servis, vlasnik cene/statusa) i `Ticket` (barkds
servis, kopija za prikaz). Artefakt: **Porudžbenica** — generisani zapis sa
poljima `order_id`, stavke (`name`, `qty`, `unit_price`), `total`, `table_number`.

### Tok 2 — Promena statusa (US-7, servisi `barkds`+`orders`)

`Konobar` (akter) → **Promeni status tiketa** (komanda,
`PATCH /api/bar/tickets/{order_id}/status`) → ⟨polisa: *"Dozvoli promenu
samo ako je tranzicija u skladu sa STATUS_FLOW i status nije u međuvremenu
konkurentno promenjen (CAS), inače odbij sa 409"*⟩ → **Status porudžbine
promenjen** (događaj, `OrderStatusChanged` — konkretizovano kao
`OrderAccepted` / `OrderReady` / `OrderDelivered`) → ⟨polisa: *"Kad se
status promeni, ažuriraj prikaz na bar dashboard-u uživo"*⟩ → **Tiket
ažuriran** (događaj, `TicketUpdated`, WebSocket broadcast)

Agregati: `Order` (vlasnik tranzicije), `Ticket` (kopija).

### Tok 3 — Otkazivanje (US-4, servisi `orders`+`barkds`)

`Gost` (akter) → **Otkaži porudžbinu** (komanda,
`POST /api/orders/orders/{id}/cancel`) → ⟨polisa: *"Otkaži isključivo ako je
trenutni status CREATED (uslovni UPDATE); ako je konobar u međuvremenu već
prihvatio, odbij sa 409"*⟩ → **Porudžbina otkazana** (događaj,
`OrderCancelled`) → ⟨polisa: *"Kad je porudžbina otkazana, ukloni njen tiket
sa bar dashboard-a"*⟩ → **Tiket ažuriran** (događaj, `TicketUpdated` —
uklanjanje sa aktivne table)

Agregati: `Order`, `Ticket`. Ovaj tok deli istu polisu/CAS mehanizam kao Tok 2
— oba pišu u isti `Order` agregat pod istim uslovnim UPDATE-om, čime je
race-condition gost-otkazuje/konobar-prihvata rešena na nivou baze.

### Tok 4 — Podela i naplata računa (US-5, servisi `orders`+`barkds`+`payments`)

**4a — podela (offline naplata kod konobara):**
`Gost` (akter) → **Zatraži naplatu izabranih stavki** (komanda,
`POST /api/bar/requests`, `kind=bill_split`) → **Zahtev za podelu računa
kreiran** (događaj, `BillSplitRequested`) → ⟨polisa: *"Prikaži zahtev na bar
dashboard-u dok se ne reši"*⟩ → `Konobar` (akter) → **Naplati izabrane
stavke** (komanda, `POST /api/orders/tables/{cafe}/{table}/bill/settle`) →
**Stavke naplaćene** (događaj, `BillItemsSettled`) — svaka `OrderItem`
prelazi u `paid = true`.

**4b — online naplata karticom (demo):**
`Gost` (akter) → **Plati karticom (Google Pay)** (komanda,
`POST /api/payments/pay`, tokenizovan payload) → ⟨polisa: *"Dokaži identitet
stola HMAC potpisom pre bilo kakve naplate"*⟩ → **Plaćanje izvršeno (demo)**
(događaj, `PaymentProcessed`) → ⟨polisa: *"Kad je plaćanje izvršeno, naloži
orders servisu da odmah obeleži iste stavke plaćenim"*⟩ → **Stavke
naplaćene** (događaj, `BillItemsSettled`, isti agregat kao 4a)

Agregat: `Order`/`OrderItem` (naplata), `ServiceRequest` (zahtev za podelu).
Artefakt: **Račun** — `table_number`, spisak `OrderItem` (naziv, cena,
`paid`), `subtotal`, `paid_total`, `remaining`, `payment_method`.

### Tok 5 — Onboarding kafića (US-10, servisi `auth`+`menu`)

`Budući vlasnik` (akter) → **Registruj kafić** (komanda,
`POST /api/auth/onboard`) → ⟨polisa: *"Generiši jedinstven slug kafića pre
upisa"*⟩ → **Kafić kreiran** (događaj, `CafeCreated`, u menu servisu preko
`POST /internal/cafes`) → ⟨polisa: *"Tek pošto je kafić uspešno kreiran,
napravi vlasnički nalog vezan za njega"*⟩ → **Vlasnički nalog kreiran**
(događaj, `OwnerAccountCreated`, u auth servisu) → sistem odmah vraća JWT
(implicitna komanda **Izdaj token** → događaj **Token izdat**)

Agregati: `Cafe` (menu servis), `User` (auth servis) — povezani logičkom
referencom `cafe_id`, bez zajedničke baze ni DB-transakcije preko servisa
(rizik naveden u 3.1, tabela "Tehnički izazovi i rizici").

---

## 3.4 Definicija modela podataka

### Relacioni model — `Orders Service` (PostgreSQL, baza `orders`)

**UML/PMOV konceptualne klase (tekstualna specifikacija za draw.io):**

**Klasa `Order`** (tabela `orders`)
| Atribut | Tip | Napomena |
|---|---|---|
| `id` | UUID (PK) | |
| `cafe_id` | String(32) | logička referenca na `Cafe` u menu servisu (bez FK — druga baza) |
| `table_number` | Integer | |
| `status` | String(16) | `CREATED\|ACCEPTED\|READY\|DELIVERED\|CANCELLED`, default `CREATED` |
| `note` | Text (nullable) | napomena gosta |
| `total` | Integer | zbir u RSD (celi dinari) |
| `taken_by` | String(64) (nullable) | konobar koji je preuzeo |
| `payment_method` | String(16) (nullable) | `cash\|card` |
| `rating` | Integer (nullable) | 1–5 |
| `rating_comment` | Text (nullable) | |
| `created_at` | DateTime(tz) | default `utcnow` |
| `accepted_at` | DateTime(tz) (nullable) | |
| `ready_at` | DateTime(tz) (nullable) | |
| `delivered_at` | DateTime(tz) (nullable) | |
| `cancelled_at` | DateTime(tz) (nullable) | |

**Klasa `OrderItem`** (tabela `order_items`)
| Atribut | Tip | Napomena |
|---|---|---|
| `id` | Integer (PK, autoincrement) | |
| `order_id` | UUID (FK → `Order.id`) | indeksirano |
| `item_id` | String(32) | logička referenca na `MenuItem._id` (MongoDB, menu servis — bez FK) |
| `name` | String(120) | snapshot naziva u trenutku porudžbine |
| `unit_price` | Integer | snapshot cene u trenutku porudžbine (RSD) |
| `qty` | Integer | |
| `paid` | Boolean | default `false`, za podelu računa po stavci |

**Veza:** `Order` **1 --- \*** `OrderItem` (kompozicija — `cascade="all,
delete-orphan"`: brisanje porudžbine briše sve njene stavke; stavka ne može
postojati bez porudžbine).

### Relacioni model — `Auth Service` (PostgreSQL, baza `auth`)

**Klasa `User`** (tabela `users`)
| Atribut | Tip | Napomena |
|---|---|---|
| `id` | UUID (PK) | default `uuid4` |
| `cafe_id` | String(32), indeksirano | logička referenca na `Cafe` (menu servis, bez FK) |
| `email` | String(160), unique, indeksirano | |
| `password_hash` | String(128) | bcrypt heš |
| `role` | String(16) | `vlasnik\|konobar`, default `konobar` |
| `name` | String(80) | |
| `created_at` | DateTime(tz) | default `utcnow` |

**Veza:** `User.cafe_id` je logička (cross-service) referenca na `Cafe` iz
Menu servisa — nema DB-FK jer su to dve odvojene baze/servisa; integritet
garantuje aplikativna logika (`/internal/cafes` mora uspeti pre upisa User-a).

*Napomena o izboru relacione baze:* Orders i Auth koriste PostgreSQL jer im
je prioritet ACID (novčani iznosi, status mašina sa konkurentnim pristupom,
jedinstvenost email-a) i jednostavne, stabilne šeme — tačno kriterijum iz
template-a ("relacione tamo gde su ACID + kompleksne veze prioritet").

---

### Nerelacioni model — `Menu Service` (MongoDB, baza `menu`)

**Kolekcija `cafes`:**
```json
{
  "_id": "ObjectId",
  "name": "string",
  "slug": "string (unique index)",
  "address": "string | null",
  "currency": "string (default: RSD)",
  "tables": [
    {
      "number": "int (1-500)",
      "zone": "string | null (max 40)",
      "label": "string | null (max 60)",
      "shape": "square | round (default: square)",
      "seats": "int | null (1-50)",
      "x": "float | null (0-100, % pozicije na platnu)",
      "y": "float | null (0-100)",
      "w": "float (3-40, default: 12)",
      "h": "float (3-40, default: 12)"
    }
  ]
}
```
`tables` je embedded lista (ne posebna kolekcija) — cela mapa stolova kafića
čita/piše se kao jedan dokument (`PATCH /cafes/{id}/tables` zamenjuje celu
listu odjednom, max 200 stolova, brojevi stolova moraju biti jedinstveni).

**Kolekcija `categories`:**
```json
{
  "_id": "ObjectId",
  "cafe_id": "ObjectId (ref: cafes._id, indeksirano)",
  "name": "string",
  "sort": "int (default: 0)"
}
```

**Kolekcija `items`:**
```json
{
  "_id": "ObjectId",
  "cafe_id": "ObjectId (ref: cafes._id, indeksirano)",
  "category_id": "ObjectId (ref: categories._id, indeksirano)",
  "name": "string",
  "description": "string | null",
  "price": "int (RSD, celi dinari)",
  "available": "bool (default: true)",
  "note": "string | null",
  "allergens": ["string"],
  "image_url": "string | null"
}
```

### Nerelacioni model — `BarKDS Service` (MongoDB, baza `barkds`)

**Kolekcija `tickets`:**
```json
{
  "_id": "ObjectId",
  "order_id": "string (unique index, ref: orders.orders.id)",
  "cafe_id": "string (indeksirano)",
  "table_number": "int",
  "status": "string (default: CREATED)",
  "note": "string | null",
  "items": [
    { "name": "string", "qty": "int" }
  ],
  "created_at": "datetime"
}
```

**Kolekcija `requests`:**
```json
{
  "_id": "ObjectId",
  "cafe_id": "string (indeksirano)",
  "table_number": "int",
  "kind": "waiter | bill | bill_split",
  "status": "OPEN | RESOLVED (default: OPEN)",
  "created_at": "datetime",
  "detail": "string | null",
  "item_ids": "[int] | null (OrderItem.id spisak, samo za bill_split)",
  "amount": "int | null"
}
```

*Napomena o izboru nerelacione baze:* Menu (katalog + mapa stolova) i BarKDS
(tiketi/zahtevi) koriste MongoDB jer je šema polustrukturirana i menja se
često (alergeni kao lista, mapa stolova kao slobodna geometrija), a tipičan
pristup je čitanje cele agregacije odjednom (ceo meni kafića, ceo aktivni
tiket) bez potrebe za relacionim spajanjima — tačno kriterijum iz template-a
("nerelacione za polustrukturirane/brzo-skalirajuće" podatke — katalog,
tabla uživo).
