# BACKLOG — odloženo za kasnije

> Centralno mesto za sve što smo svesno ostavili za kasnije, da ne zaboravimo.
> Format: **[oblast]** stavka — *zašto odloženo / čeka šta*.
> Kad se nešto uradi, briše se odavde i upisuje red u `../NAPREDAK.md`.
> (Velike faze i plan su u `CLAUDE.md` — ovde su konkretne odložene stavke.)

## Plaćanje računa (podela)
- **[Krug 3 — DEMO URAĐEN]** Online plaćanje kroz **Google Pay TEST** (Payments servis
  `/pay` → orders settle; dugme na „Račun"). Radi kao demo bez firme/PSP-a. Ostaje: pravi
  procesor za produkciju (v. dole) i interaktivni test lista u pravom Chrome-u sa test karticom.
- **[Krug 3 — PRODUKCIJA]** Pravi PSP za srpsko tržište (karta ne dira naš server, PCI SAQ A).
  Kandidati: **Raiffeisen RaiAccept** (prvi u RS sa Apple+Google Pay prihvatom, dec. 2025) i
  **CorvusPay** (regionalni, nije vezan za jednu banku); Monri/WSPay (Google Pay potvrđen,
  Apple Pay proveriti). **Stripe ISKLJUČEN** — Srbija nije podržana zemlja (Stripe TEST može
  samo kao demo). *Traži registrovanu firmu + ugovor sa PSP-om — odluka posle firme/pilota.*
  Detalji: `2026-07-28-online-placanje-apple-pay.md` (+ veliki produkcijski izveštaj
  `2026-07-28-placanje-produkcija-srbija-detaljno.md`, u izradi).
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
- **[Blok 2]** PATCH ruta `/cafes/{id}/tables` + react-rnd editor (prevlačenje/resize) —
  *čeka Auth JWT (ruta mora biti zaštićena).*
- **[kozmetika]** Okrugli stolovi se renderuju kao elipse (platno 16:10, w=h=12% ≠ isti
  broj px) — *sitna CSS ispravka, može uz Blok 2.*
- **[recenzija]** 3 VAŽNA nalaza za table-spots: nema migracije starih Cafe dokumenata →
  prazna mapa na perzistentnom volumenu; prazan `tables` renderuje prazan ekran; neki
  `fetch` bez `.catch`. + Field ograničenja na `TableSpot` — *pre Bloka 2.*

## Bezbednost / Auth (Faza 3)
- **[Auth]** JWT + uloge (vlasnik/konobar) — *otključava editor mape, admin panel,
  `taken_by` statistiku.*
- **[Auth]** Zaključati iza Auth-a: arhiva (pokazuje pazar), settle ruta (naplata),
  admin rute — *sad su otvorene kao i ceo dashboard.*

## Ostalo (iz CLAUDE.md / ranijih odluka)
- **[Faza 3]** Admin panel (kreiranje kafića, meni CRUD, QR generisanje, statistika).
- **[Faza 3]** Eksterni API-ji: OpenFoodFacts (alergeni), Frankfurter (valute).
- **[Faza 5]** Pun inventar sastojaka (koktel bez limuna…) — *sad samo toggle + napomena.*
- **[kraj projekta]** Jezički togl SR/EN/RU — *održavanje prevoda tokom razvoja = stalni posao.*
- **[blokada]** GitHub Classroom repo nije registrovan → nema remote-a/PR-ova/Issues.
- **[fiskalizacija]** PDV/fiskalni račun po zakonu — *zasebna pravna tema, ne otvarati bez potrebe.*
