# 2. Prikupljanje korisničkih zahteva

## 2.1 User story analiza

### Identifikacija aktera

| Akter | Opis | Kako se identifikuje |
|---|---|---|
| **Gost** | Osoba za stolom koja poručuje, prati porudžbinu, plaća i ocenjuje. | Anoniman — bez naloga; sesija je vezana za sto preko QR koda sa HMAC potpisom (`cafe_id`, broj stola, `sig`). |
| **Konobar / bar** | Osoblje koje prima i priprema porudžbine, reaguje na zahteve gostiju i naplaćuje. | Koristi bar dashboard aplikaciju (`frontend/bar`); trenutno bez prijave — sistem još ne razlikuje konobara od menadžera (Auth servis je skelet, planiran za Fazu 3). |
| **Menadžer / vlasnik** | Odgovoran za meni kafića i uvid u učinak smene (pazar, ocene). | Deli isti bar dashboard sa konobarom (uređivanje menija, arhiva smene); razdvajanje pristupnih prava čeka Auth servis. |

Sistem je multi-tenant: sva tri aktera uvek deluju u okviru tačno jednog
kafića (`cafe_id`), bez uvida u podatke drugih kafića.

### User story-ji

> **US-1 (domen: Meni + Porudžbine — servisi `menu`, `orders`):**
> Kao gost za stolom, želim da skeniram QR kod i naručim sa menija direktno sa
> telefona, kako bih poručio bez čekanja da mi priđe konobar.

> **US-2 (domen: Porudžbine — servis `orders`):**
> Kao gost za stolom, želim da vidim status svoje porudžbine uživo (poslato →
> prihvaćeno → spremno → isporučeno), kako bih znao kada stiže bez zaustavljanja
> konobara da pitam.

> **US-3 (domen: Bar/KDS — servis `barkds`):**
> Kao gost za stolom, želim da jednim dodirom pozovem konobara ili zatražim
> račun, kako bih dobio pažnju osoblja bez ustajanja i mahanja rukom.

> **US-4 (domen: Porudžbine — servis `orders`):**
> Kao gost za stolom, želim da otkažem porudžbinu dok još nije prihvaćena,
> kako bih ispravio grešku u poručivanju bez čekanja da neko dođe do stola.

> **US-5 (domen: Porudžbine + Bar/KDS + Payments — servisi `orders`, `barkds`,
> `payments`):**
> Kao gost za stolom, želim da vidim zbirni račun stola i platim ceo račun ili
> samo svoje stavke (podela računa) — gotovinom/karticom preko konobara ili
> online karticom — kako bih platio na način koji meni odgovara, bez da čekam
> da se ceo sto oko toga dogovori.

> **US-6 (domen: Porudžbine — servis `orders`):**
> Kao gost za stolom, želim da ocenim porudžbinu posle isporuke (1–5 zvezdica
> + komentar), kako bih dao brzu povratnu informaciju kafiću.

> **US-7 (domen: Bar/KDS + Porudžbine — servisi `barkds`, `orders`):**
> Kao konobar, želim da na bar dashboard-u uživo vidim nove porudžbine i
> zahteve gostiju i da menjam status porudžbine (prihvaćeno/spremno/isporučeno),
> kako bih opsluživao više stolova odjednom bez papira i dovikivanja.

> **US-8 (domen: Meni — servis `menu`):**
> Kao konobar/menadžer, želim da u toku smene promenim dostupnost, cenu ili
> napomenu stavke menija, kako bih odmah sakrio ono čega nema, bez čekanja na
> IT podršku.

> **US-9 (domen: Porudžbine — servis `orders`):**
> Kao menadžer/vlasnik, želim uvid u arhivu završenih porudžbina sa pazarom,
> prosečnim vremenom pripreme i prosečnom ocenom, kako bih pratio učinak smene.

---

## 2.2 Specifikacija funkcionalnih zahteva

### FZ-1 — poručivanje sa menija (US-1)
- **FZ-1.1** Sistem mora prikazati gostu meni kafića grupisan po kategorijama,
  sa nazivom, cenom, opisom, alergenima, napomenom i dostupnošću stavke
  (`GET /api/menu/cafes/{cafe_id}/menu`).
- **FZ-1.2** Sistem mora omogućiti pristup meniju isključivo skeniranjem QR
  koda stola (kodira `cafe_id`, broj stola i HMAC potpis `sig`) — bez
  registracije ili prijave gosta.
- **FZ-1.3** Sistem ne sme dozvoliti dodavanje u korpu stavki koje su označene
  kao nedostupne (`available = false`).
- **FZ-1.4** Sistem mora, pri slanju porudžbine (`POST /api/orders/orders`),
  validirati potpis stola i svaku naručenu stavku preko menu servisa (interna
  ruta `/internal/items`) — cena porudžbine se u celosti izračunava na serveru
  iz kataloga, nikad se ne prihvata od klijenta.
- **FZ-1.5** Ako je stavka u međuvremenu postala nedostupna, sistem mora
  odbiti kreiranje porudžbine (HTTP 409) uz naziv sporne stavke.
- **FZ-1.6** Sistem mora, po uspešnom kreiranju porudžbine (status `CREATED`),
  odmah obavestiti Bar/KDS servis (interna ruta `/internal/tickets`) radi
  generisanja tiketa za pripremu.

### FZ-2 — status porudžbine uživo (US-2)
- **FZ-2.1** Sistem mora omogućiti gostu uvid u status svojih aktivnih
  porudžbina za dati sto (`GET /api/orders/tables/{cafe_id}/{table_number}/orders`,
  uz potpis stola).
- **FZ-2.2** Status porudžbine mora pratiti tok
  `CREATED → ACCEPTED → READY → DELIVERED` (sa mogućim ranim izlazom u
  `CANCELLED`); svaku tranziciju validira isključivo orders servis prema
  definisanoj mašini stanja.
- **FZ-2.3** Promena statusa mora biti vidljiva gostu najkasnije 5 sekundi od
  akcije konobara (klijent osvežava prikaz na svakih 5 s).
- **FZ-2.4** Isporučena porudžbina ostaje vidljiva gostu još najviše 3 sata
  posle isporuke (radi naknadnog ocenjivanja); otkazane porudžbine se odmah
  uklanjaju iz gostovog prikaza.

### FZ-3 — poziv konobara i zahtev za račun (US-3)
- **FZ-3.1** Sistem mora omogućiti gostu slanje zahteva „pozovi konobara" ili
  „traži račun" jednim dodirom (`POST /api/bar/requests`, uz potpis stola).
- **FZ-3.2** Sistem ne sme dupliranje otvorenih zahteva istog tipa za isti sto
  — ako već postoji otvoren (`OPEN`) zahtev tog tipa, vraća se postojeći
  umesto kreiranja novog; klijent dodatno primenjuje 60-sekundni kulaun po
  tipu zahteva kao zaštitu od spamovanja konobara.
- **FZ-3.3** Novi zahtev mora biti odmah prikazan na bar dashboard-u putem
  WebSocket-a (`request.created`); konobar ga označava rešenim
  (`PATCH /api/bar/requests/{id}/resolve`, event `request.resolved`).

### FZ-4 — otkazivanje porudžbine (US-4)
- **FZ-4.1** Sistem mora dozvoliti gostu da otkaže sopstvenu porudžbinu
  isključivo dok je u statusu `CREATED`
  (`POST /api/orders/orders/{order_id}/cancel`, uz potpis stola).
- **FZ-4.2** Otkazivanje mora biti atomska operacija (uslovni UPDATE nad
  `status = 'CREATED'`) koja korektno razrešava trku sa istovremenim
  prihvatanjem od strane konobara — ako je porudžbina u međuvremenu već
  prihvaćena ili otkazana, sistem vraća grešku (HTTP 409).
- **FZ-4.3** Uspešno otkazivanje mora ukloniti odgovarajući tiket sa bar
  dashboard-a uživo (orders obaveštava barkds internom rutom, koja emituje
  isti `ticket.updated` event kao i redovna promena statusa).

### FZ-5 — račun i plaćanje (US-5)
- **FZ-5.1** Sistem mora prikazati gostu zbirni račun stola — sve stavke svih
  neotkazanih porudžbina, sa oznakom plaćeno/neplaćeno
  (`GET /api/orders/tables/{cafe_id}/{table_number}/bill`).
- **FZ-5.2** Sistem mora omogućiti gostu da izabere podskup stavki i pošalje
  konobaru zahtev da naplati samo izabrano (`POST /api/bar/requests`,
  `kind = bill_split`, sa spiskom stavki i iznosom).
- **FZ-5.3** Sistem mora omogućiti konobaru da naplati (keš/kartica na licu
  mesta) izabrane stavke, koje se time obeležavaju kao plaćene i otpadaju sa
  preostalog dela računa (`POST /api/orders/tables/{cafe_id}/{table_number}/bill/settle`).
- **FZ-5.4** Sistem mora omogućiti online plaćanje izabranih stavki karticom
  (demo tok, Google Pay TEST okruženje) preko Payments servisa
  (`POST /api/payments/pay`) — servis dokazuje sto potpisom pa servis-servis
  pozivom nalaže orders servisu da obeleži stavke plaćenim; sirovi podaci
  kartice nikada ne prolaze kroz orders/menu servise.
- **FZ-5.5** Kada su sve stavke računa plaćene, sistem mora gostu prikazati
  potvrdu da je račun izmiren.

### FZ-6 — ocenjivanje porudžbine (US-6)
- **FZ-6.1** Sistem mora dozvoliti gostu da oceni porudžbinu (1–5 zvezdica +
  opcioni komentar) isključivo pošto je porudžbina u statusu `DELIVERED`
  (`POST /api/orders/orders/{order_id}/rating`, uz potpis stola).
- **FZ-6.2** Sistem mora odbiti ocenjivanje porudžbine koja nije isporučena
  (HTTP 409).
- **FZ-6.3** Data ocena mora ostati trajno vezana za porudžbinu i biti
  prikazana gostu kao potvrda.

### FZ-7 — upravljanje porudžbinama na baru (US-7)
- **FZ-7.1** Sistem mora prikazati konobaru nove porudžbine u realnom vremenu
  putem WebSocket konekcije kroz gateway (`/ws/bar/{cafe_id}`, event
  `ticket.created`).
- **FZ-7.2** Sistem mora omogućiti konobaru promenu statusa tiketa
  (`PATCH /api/bar/tickets/{order_id}/status`); barkds servis prosleđuje
  promenu ka orders servisu (vlasniku mašine stanja), koji je validira pre
  potvrde.
- **FZ-7.3** Pri isporuci porudžbine, sistem mora omogućiti konobaru da izabere
  način plaćanja (keš/kartica), koji se beleži uz porudžbinu radi kasnijeg
  bilansa smene.
- **FZ-7.4** Aktivni tiketi (`CREATED`/`ACCEPTED`/`READY`) moraju biti
  prikazani grupisano po statusu, sa najstarijim tiketom kao prioritetom u
  koloni novih porudžbina.

### FZ-8 — uređivanje menija (US-8)
- **FZ-8.1** Sistem mora omogućiti konobaru/menadžeru izmenu dostupnosti,
  cene, opisa i napomene stavke menija u toku smene
  (`PATCH /api/menu/cafes/{cafe_id}/items/{item_id}`).
- **FZ-8.2** Promena dostupnosti mora biti vidljiva gostu u meniju najkasnije
  30 sekundi (gostov klijent periodično osvežava meni).

### FZ-9 — arhiva i bilans smene (US-9)
- **FZ-9.1** Sistem mora omogućiti uvid u istoriju završenih (`DELIVERED` ili
  `CANCELLED`) porudžbina kafića (`GET /api/orders/orders/history?cafe_id=...`).
- **FZ-9.2** Sistem mora prikazati sažetak smene: ukupan pazar, prosečno
  vreme pripreme, prosečnu ocenu gostiju i podelu naplate po načinu plaćanja.
- **FZ-9.3** Napomena za implementaciju: ruta trenutno nije ograničena
  autentifikacijom (Auth servis je skelet, Faza 3) — u produkciji mora biti
  dostupna isključivo ulozi menadžer/vlasnik.

---

## 2.3 Specifikacija nefunkcionalnih zahteva

> Vrednosti obeležene sa **(PREDLOG — potvrditi)** su projekcije za solo kafić
> (jedna lokacija, do ~30 stolova) koje student brani usmeno na odbrani; nisu
> izmerene na produkcionom saobraćaju.

### Dostupnost
- **NFZ-1:** Sistem mora biti dostupan **99,5% vremena mesečno** (dozvoljen
  prekid do ~3,6 h/mesec) tokom radnog vremena kafića. **(PREDLOG — potvrditi)**
  *Obrazloženje:* jedna lokacija bez 24/7 obaveze; kratki planirani prekidi za
  update (van radnog vremena) su prihvatljivi, ali gost tokom rada mora moći
  da poruči.
- **NFZ-2:** Kvar Bar/KDS servisa ne sme onemogućiti kreiranje porudžbine —
  porudžbina se trajno čuva u orders bazi i mora se pojaviti na baru u roku
  od **60 sekundi** od oporavka servisa (osveženje dashboard-a). **(PREDLOG — potvrditi)**
  *Obrazloženje:* obaveštavanje bar servisa je već implementirano kao
  best-effort HTTP poziv (ne blokira kreiranje porudžbine); potrebna je gornja
  granica koliko dugo porudžbina sme ostati nevidljiva baru pri padu servisa.

### Skaliranje
- **NFZ-3:** Sistem mora podržati najmanje **100 istovremenih gostiju po
  kafiću** (aktivne HTTP/WebSocket sesije) bez degradacije. **(PREDLOG — potvrditi)**
  *Obrazloženje:* realan gornji limit za kafić od 20–30 stolova uz više gostiju
  po stolu i preklapanje smena.
- **NFZ-4:** Sistem mora podržati najmanje **20 istovremenih aktivnih
  porudžbina** u obradi (statusi `CREATED`/`ACCEPTED`/`READY`) po kafiću, bez
  merljivog usporavanja bar dashboard-a. **(PREDLOG — potvrditi)**
  *Obrazloženje:* špic rada — svi stolovi naruče u kratkom vremenskom prozoru.
- **NFZ-5:** Arhitektura (nezavisni mikroservisi iza gateway-a,
  `cafe_id` na svakom entitetu) mora dozvoliti horizontalno skaliranje broja
  kafića bez izmene koda — dodavanje novog kafića je isključivo upis podataka.
  *(ovo je projektni princip, ne kapacitetski broj — potvrđeno postojećim
  multi-tenant modelom u kodu.)*

### Konzistentnost podataka
- **NFZ-6:** Status porudžbine u Bar/KDS servisu (kopija stanja tiketa) mora
  biti usklađen sa statusom u orders servisu (izvor istine) u roku od
  **3 sekunde** od promene (eventualna konzistentnost, best-effort HTTP
  notifikacija). **(PREDLOG — potvrditi)**
  *Obrazloženje:* orders i barkds su odvojene baze (PostgreSQL / MongoDB) bez
  distribuirane transakcije; usklađivanje ide preko interne HTTP notifikacije,
  pa kratak vremenski prozor neusklađenosti je neizbežan i mora imati gornju
  granicu.
- **NFZ-7:** Promena statusa porudžbine mora biti **atomska u odnosu na
  konkurentne promene** (npr. gost otkazuje dok konobar prihvata) — sistem
  garantuje da tačno jedna od dve konkurentne tranzicije uspe (uslovni UPDATE
  u bazi), a druga dobija eksplicitnu grešku (HTTP 409) umesto tihog
  nadpisivanja. Ovo je već implementirano i proverljivo u kodu, nije predlog.
- **NFZ-8:** Cena porudžbine mora u svakom trenutku odgovarati ceni u meniju u
  trenutku poručivanja — server ponovo izračunava ukupan iznos iz kataloga pri
  svakom kreiranju porudžbine (nema keširane/klijentske cene). Već
  implementirano, nije predlog.

### Dodatno (performanse i bezbednost)
- **NFZ-9:** P95 latencija kreiranja porudžbine
  (`POST /api/orders/orders`, uključujući validaciju kod menu servisa) mora
  biti **< 500 ms**. **(PREDLOG — potvrditi)**
  *Obrazloženje:* gost ne sme osetiti čekanje nakon klika na „Poruči" — kritičan
  trenutak za percepciju brzine aplikacije.
- **NFZ-10:** Identitet stola mora biti kriptografski dokaziv — HMAC-SHA256
  potpis (256-bitni ključ `QR_SECRET`, heksadecimalni potpis dužine 64
  karaktera) se proverava na svakoj ruti koja menja ili čita podatke vezane
  za konkretan sto. Već implementirano, nije predlog.

