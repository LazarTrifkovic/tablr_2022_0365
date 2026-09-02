# BACKLOG — odloženo za kasnije

> Centralno mesto za sve što smo svesno ostavili za kasnije, da ne zaboravimo.
> Format: **[oblast]** stavka — *zašto odloženo / čeka šta*.
> Kad se nešto uradi, briše se odavde.

## Plaćanje računa (podela)
- **[Krug 3 — DEMO URAĐEN]** Online plaćanje kroz **Google Pay TEST** (Payments servis
  `/pay` → orders settle; dugme na „Račun"). Radi kao demo bez firme/PSP-a. Ostaje: pravi
  procesor za produkciju (v. dole) i interaktivni test lista u pravom Chrome-u sa test karticom.
- **[Krug 3 — PRODUKCIJA]** Pravi PSP za srpsko tržište (karta ne dira naš server, PCI SAQ A).
  Kandidati: **Raiffeisen RaiAccept** (prvi u RS sa Apple+Google Pay prihvatom, dec. 2025) i
  **CorvusPay** (regionalni, nije vezan za jednu banku); Monri/WSPay (Google Pay potvrđen,
  Apple Pay proveriti). **Stripe ISKLJUČEN** — Srbija nije podržana zemlja (Stripe TEST može
  samo kao demo). *Traži registrovanu firmu + ugovor sa PSP-om — odluka posle firme/pilota.*
  Detalji: `2026-07-28-online-placanje-apple-pay.md` + **veliki produkcijski referentni
  izveštaj `2026-07-28-placanje-produkcija-srbija-detaljno.md`** (svi PSP-ovi u RS, cene,
  IPS, pravni/administrativni checklist korak-po-korak, fiskalizacija — čitati pred pilot).
- **[Krug 3]** **Apple Pay** — preskočeno: traži plaćen Apple Developer (99 USD/god) + Apple
  uređaj čak i za web sandbox; za ispit nepotrebno, za produkciju stiže preko PSP-a (RaiAccept).
- **[Krug 3]** Baksiš (napojnica) uz online karticu — *ide zajedno sa pravim online plaćanjem;
  keš baksiš ionako ide u ruku konobaru, mimo sistema.*
- **[fiskalizacija]** Spoj online plaćanja sa OBAVEZNIM fiskalnim računom (ESIR/LPFR) za
  ugostiteljstvo u Srbiji — *ključno za produkciju; obrađeno u velikom izveštaju.*
- **[podela]** `claimed_until` kratkoročno zaključavanje stavke — *treba tek za online
  instant-plaćanje (trka pri istovremenom tapkanju); offline putanju serijalizuje konobar.*
- **[podela]** Deljenje unutar količine (platiti 1 od „3× kafa") — *MVP plaća po celoj
  liniji; finije deljenje je komplikacija, pitati konobare da li se traži.*
- **[podela]** `paid_by_label` (slobodan tekst „Marko" po stavci) — *pitati konobare
  da li im to uopšte treba.*
- **[arhiva]** Kad plaćanje postane po stavci, arhiva mora da sabira način plaćanja
  po stavkama umesto po celoj porudžbini (`Order.payment_method` → po `OrderItem`).

## Procena vremena pripreme (ETA)
- **[istraživanje]** Pokrenuti istraživača na temu vreme pripreme/ETA (prompt već
  sastavljen u chatu) — *pre gradnje.*
- **[Krug 1 ETA]** Statičko `prep_seconds` po stavci + gostu grub opseg + konobaru
  procena ture „po stanici" (grupiši po kategoriji, max+inkrement) — *čeka razgovor sa
  konobarima (pitanja 1–4 u `pitanja-konobarima.md`) i istraživanje.*
- **[Krug 2 ETA]** Naučena statistika (prosečno stvarno vreme po piću/turi/konobaru) —
  *konfaund: `accepted→ready` je po celoj porudžbini i preklapa se kad konobar radi
  paralelno; možda traži per-stavka merenje = dodatno trenje. Odlučiti posle istraživanja.*

## Validacija sa konobarima
- **[discovery]** Proći `pitanja-konobarima.md` sa par ljudi iz struke pre nego što
  gradimo podelu računa (obim M) i ETA — *da ne uložimo trud u nešto što se retko koristi.*

## Mapa stolova
- ✅ **[Blok 2 — URAĐENO]** Editor rasporeda (vlasnik): PATCH `/cafes/{id}/tables`
  (vlasnik-only), custom drag/resize platno, panel za broj/zonu/opis/mesta/oblik,
  dodaj/ukloni sto. Kozmetika okruglih stolova (elipsa→krug) rešena. Field ograničenja
  na TableSpot dodata (recenzentov nalaz).
- **[recenzija — ostaje]** Nema migracije starih Cafe dokumenata (prazna mapa na
  perzistentnom volumenu) i prazan `tables` renderuje prazan ekran — *manje bitno sad jer
  seed daje stolove; pravo rešenje ide sa Alembic migracijama (v. "Pred kraj").*

## Bezbednost / Auth (Faza 3)
- ✅ **[Auth — URAĐENO]** JWT + uloge (vlasnik/konobar); gateway validira token, štiti
  tablu/status/settle (osoblje) + arhivu/register (vlasnik); bar dashboard ima login.
- **[Auth — ostaje]** `taken_by` statistika (ko je preuzeo porudžbinu) — X-User se sad
  prosleđuje kroz gateway; orders to još ne beleži na tranziciji. *Uz statistiku smene.*
- **[Auth — ostaje]** `/register` je zaštićen (samo vlasnik), ali UI za dodavanje osoblja
  dolazi tek sa admin panelom. *Sad se nalozi dodaju samo seed-om/API-jem.*
- **[Auth — produkcija]** `JWT_SECRET` hardkodovan u compose (kao QR_SECRET) — v. sekcija
  "Pred kraj". Admin/editor mape rute treba zaštititi kad se naprave.

## 🏁 Pred kraj projekta / pre produkcije (obavezne izmene — dev-prečice koje se moraju srediti)
> Ovo su svesne prečice iz razvoja koje su OK za ispit/demo ali NE smeju u pravi kafić.
> Kad dođe vreme za pilot/produkciju, proći celu ovu listu.
- **[bezbednost — KRITIČNO]** `QR_SECRET = "dev-secret-change-in-prod"` je hardkodovan u
  `docker-compose.yml` (menu/barkds/orders/payments) — *mora postati pravi tajni ključ iz
  env/secret menadžera; sa ovim ključem bilo ko može da falsifikuje QR potpis stola.*
- **[migracije — KRITIČNO]** Šema baze se u dev-u menja preko **reset volume-a** (SQLAlchemy
  `create_all` ne dodaje kolone) — *produkcija ne sme da gubi podatke; uvesti prave migracije
  (Alembic) pre nego što u bazi bude stvarnih porudžbina.*
- **[bezbednost]** Rute bez zaštite: `bill/settle` (naplata), arhiva (pazar), `payments/pay`,
  admin rute — *zaključati iza Auth JWT (već i u sekciji Auth). Sad su otvorene kao ceo dashboard.*
- **[plaćanje]** Google Pay je **TEST env** + `payments/pay` samo prihvata token — *za produkciju
  pravi PSP (RaiAccept/CorvusPay/PaySpot) + fiskalizacija (v. sekcija Plaćanje + veliki izveštaj).*
- **[demo podaci]** Seed „Kafić Panorama" + demo meni se ubacuje u praznu bazu; `/dev/sign`
  ruta postoji u orders (blokirana na gateway-u) — *za produkciju: ukloniti/ograditi seed i sve
  `/dev` rute, ne isporučivati demo kafić.*
- **[kozmetika]** Okrugli stolovi se renderuju kao elipse (v. Mapa stolova) — *sitna CSS ispravka.*
- **[i18n]** Jezički togl SR/EN/RU — *tek na samom kraju (održavanje prevoda tokom razvoja = stalni posao).*

## Ostalo (ranije odluke)
- ✅ **[Faza 3 — URAĐENO]** Admin panel (`frontend/admin` :5175): onboarding „Registruj
  kafić", meni CRUD (kategorije+stavke), QR generisanje+štampa, upravljanje osobljem.
  Statistika smene je već u bar Arhivi. Ostaje za produkciju: GUEST_BASE_URL hardkodovan
  (localhost:5173) — za pravi kafić postaviti pravi domen; nema „obriši kafić" rute.
- ✅ **[Faza 3 — URAĐENO]** Eksterni API-ji: OpenFoodFacts (predlog alergena u bar Meni tabu)
  + Frankfurter (birač valute kod gosta, ≈ cena). RSD sidro (Frankfurter nema RSD).
  Ostaje za produkciju: RSD sidro je hardkodovano (117.5) — povezati na pravi izvor kursa;
  keš je in-memory (nestane na restart).
- **[Faza 5]** Pun inventar sastojaka (koktel bez limuna…) — *sad samo toggle + napomena.*
- **[kraj projekta]** Jezički togl SR/EN/RU — *održavanje prevoda tokom razvoja = stalni posao.*
- **[blokada]** GitHub Classroom repo nije registrovan → nema remote-a/PR-ova/Issues.
  *Kad se registruje: push svega, prelazak na prave PR-ove sa review komentarima, i time se
  AKTIVIRA `.github/workflows/ci.yml` (CI/CD je napisan i lokalno validiran, čeka samo remote).*
- **[fiskalizacija]** PDV/fiskalni račun po zakonu — *zasebna pravna tema, ne otvarati bez potrebe.*
