# 2. Prikupljanje korisničkih zahteva

## 2.1 User story analiza

### Identifikacija aktera

| Akter | Opis | Kako se identifikuje |
|---|---|---|
| **Gost** | Osoba za stolom koja poručuje, prati porudžbinu, plaća i ocenjuje. | Anoniman — bez naloga; sesija je vezana za sto preko QR koda sa HMAC potpisom (`cafe_id`, broj stola, `sig`). |
| **Konobar** | Osoblje koje prima i priprema porudžbine, reaguje na zahteve gostiju i naplaćuje. | Prijavljen korisnik bar dashboard aplikacije (`frontend/bar`, port 5174) preko Auth servisa — JWT (HS256, TTL 12h) sa ulogom `konobar`. Ima pristup tabli/statusima tiketa, naplati računa i izmeni dostupnosti/napomene/alergena stavki menija u toku smene; **nema** pristup punom CRUD-u menija (naziv/cena/opis stavke — menu servis vraća 403), arhivi/pazaru, uređivanju mape stolova ni administrativnim rutama. |
| **Vlasnik** | Odgovoran za administraciju kafića: kompletan meni, mapu stolova, QR kodove, osoblje i uvid u učinak (pazar, ocene). | Prijavljen korisnik sa JWT ulogom `vlasnik` — ima sva prava konobara PLUS arhivu/pazar (`orders/history`), pun CRUD menija, editor mape stolova, generisanje QR kodova i upravljanje nalozima osoblja (`POST /api/auth/register`). Vlasnički nalog nastaje samostalnom registracijom kafića (`POST /api/auth/onboard`) ili ga kreira postojeći vlasnik. |

Konobar i vlasnik dele isti bar dashboard (`frontend/bar`) za svakodnevnu
opslugu (tabla, statusi, naplata); dodatno, vlasnik ima pristup posebnoj
**admin aplikaciji** (`frontend/admin`, port 5175) za administrativne
zadatke koji se ne rade u toku opsluživanja gostiju (pun CRUD menija, QR
generisanje, osoblje) — frontend blokira pristup admin panelu ako uloga nije
`vlasnik`, a gateway to dodatno garantuje na serverskoj strani nezavisno od
frontenda. Sistem je multi-tenant: svaki entitet nosi `cafe_id` i svaki upit
filtrira po njemu. Osoblje/vlasnik deluju u okviru kafića iz svog JWT tokena, a
gost u okviru kafića iz HMAC potpisa QR-a; gateway za svaku zaštićenu rutu
proverava da se `cafe_id` iz zahteva (putanja/query/telo) poklapa sa `cafe_id`
iz tokena i odbija pristup tuđem kafiću (HTTP 403), tako da nijedan akter nema
uvid u podatke drugih kafića.

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
> Kao konobar/menadžer, želim da u toku smene promenim dostupnost, napomenu ili
> alergene stavke menija, kako bih odmah sakrio ono čega nema ili ispravio
> napomenu, bez čekanja na IT podršku.

> **US-9 (domen: Porudžbine — servis `orders`):**
> Kao menadžer/vlasnik, želim uvid u arhivu završenih porudžbina sa pazarom,
> prosečnim vremenom pripreme i prosečnom ocenom, kako bih pratio učinak smene.

> **US-10 (domen: Auth + Meni — servisi `auth`, `menu`):**
> Kao budući vlasnik kafića, želim da samostalno registrujem svoj kafić i
> vlasnički nalog kroz jednu formu, kako bih odmah počeo da koristim tablr
> bez ručne intervencije administratora sistema.

> **US-11 (domen: Meni — servis `menu`, admin panel):**
> Kao vlasnik, želim da iz admin panela u potpunosti uređujem meni (dodajem,
> menjam i brišem kategorije i stavke — ne samo dostupnost u toku smene),
> kako bih meni ažurirao van gužve, bez ograničenja koja važe za konobara.

> **US-12 (domen: Meni — servis `menu`, admin panel):**
> Kao vlasnik, želim da generišem i odštampam QR kodove za sve stolove
> kafića, kako bih ih nalepio na stolove i pustio gostima da poručuju.

> **US-13 (domen: Auth — servis `auth`, admin panel):**
> Kao vlasnik, želim da dodam naloge za novo osoblje (konobare) i da vidim
> spisak postojećeg osoblja, kako bih upravljao pristupom sistemu bez
> deljenja sopstvenih kredencijala.

> **US-14 (domen: Meni — servis `menu`, eksterni API Frankfurter):**
> Kao gost za stolom, želim da vidim približnu cenu stavki menija u valuti
> koju ja razumem (EUR/USD/GBP/CHF), kako bih lakše procenio koliko trošim
> ako nisam navikao na dinare.

> **US-15 (domen: Meni — servis `menu`, eksterni API OpenFoodFacts):**
> Kao vlasnik/konobar koji unosi novu stavku menija, želim predlog mogućih
> alergena na osnovu naziva stavke, kako ne bih morao ručno da pretražujem i
> ne bih propustio bitan alergen zbog žurbe.

> **US-16 (domen: Meni — servis `menu`, bar dashboard):**
> Kao vlasnik, želim da prevlačenjem uredim raspored stolova na vizuelnoj
> mapi (dodam, uklonim, pomerim, promenim broj/zonu/oblik stola), kako bi
> mapa na bar dashboard-u i generisani QR kodovi odgovarali stvarnom
> rasporedu sale.

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
  umesto kreiranja novog (pravilo važi za tipove „pozovi konobara" i „traži
  račun"; zahtevi za podelu računa `bill_split` se ne spajaju jer svaki nosi
  različit skup stavki); klijent dodatno primenjuje 60-sekundni kulaun po
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
  napomene i liste alergena stavke menija u toku smene
  (`PATCH /api/menu/cafes/{cafe_id}/items/{item_id}`); izmena naziva, cene i
  opisa je deo punog CRUD-a menija i rezervisana je za vlasnika (FZ-11) — menu
  servis odbija (403) ako konobarski token pokuša da promeni ta polja.
- **FZ-8.2** Promena dostupnosti mora biti vidljiva gostu u meniju najkasnije
  30 sekundi (gostov klijent periodično osvežava meni).

### FZ-9 — arhiva i bilans smene (US-9)
- **FZ-9.1** Sistem mora omogućiti uvid u istoriju završenih (`DELIVERED` ili
  `CANCELLED`) porudžbina kafića (`GET /api/orders/orders/history?cafe_id=...`).
- **FZ-9.2** Sistem mora prikazati sažetak smene: ukupan pazar, prosečno
  vreme pripreme, prosečnu ocenu gostiju i podelu naplate po načinu plaćanja.
- **FZ-9.3** Ruta mora biti zaštićena JWT autentifikacijom i dostupna
  isključivo ulozi vlasnik (`GET /api/orders/orders/history`) — gateway
  odbija zahtev bez važećeg tokena (HTTP 401) ili sa ulogom `konobar`
  (HTTP 403), pre nego što zahtev uopšte stigne do orders servisa. Već
  implementirano, nije predlog.

### FZ-10 — registracija kafića i vlasničkog naloga (US-10)
- **FZ-10.1** Sistem mora omogućiti javnu registraciju novog kafića i
  pripadajućeg vlasničkog naloga u jednom koraku
  (`POST /api/auth/onboard`) — bez potrebe za prijavom ili odobrenjem
  administratora.
- **FZ-10.2** Registracija mora slediti redosled koji garantuje da nalog ne
  nastaje bez kafića: prvo se kafić kreira u menu servisu (interna ruta
  `/internal/cafes`), pa tek onda korisnički nalog sa ulogom `vlasnik` vezan
  za taj kafić u auth servisu; ako kreiranje kafića ne uspe, nalog se ne sme
  kreirati. Obrnut delimičan neuspeh (kafić kreiran, ali kreiranje naloga
  padne) u sinhronoj verziji nije kompenzovan — v. rizik (1) u 3.1;
  orkestrirana saga sa kompenzacionim brisanjem kafića predmet je Faze 4.
- **FZ-10.3** Sistem mora automatski generisati jedinstven identifikator
  (slug) kafića, tako da vlasnik ne mora ručno da bira slobodan naziv.
- **FZ-10.4** Po uspešnoj registraciji sistem mora odmah vratiti važeći JWT
  token, tako da je vlasnik prijavljen bez dodatnog koraka.

### FZ-11 — CRUD menija u admin panelu (US-11)
- **FZ-11.1** Sistem mora omogućiti vlasniku kreiranje, izmenu naziva
  i brisanje kategorija menija
  (`POST/PATCH/DELETE /api/menu/cafes/{cafe_id}/categories[/{category_id}]`).
- **FZ-11.2** Sistem mora omogućiti vlasniku kreiranje, potpunu izmenu
  (naziv, opis, cena, dostupnost, napomena, alergeni, slika) i brisanje
  stavki menija
  (`POST/PATCH/DELETE /api/menu/cafes/{cafe_id}/items[/{item_id}]`).
- **FZ-11.3** Brisanje kategorije mora obrisati i sve stavke koje joj
  pripadaju (kaskadno brisanje unutar menu servisa).
- **FZ-11.4** Kreiranje i brisanje kategorija/stavki, izmena kategorija i puna
  izmena stavke (naziv, opis, cena, slika) dostupni su isključivo ulozi vlasnik:
  gateway vraća 403 za konobara na kreiranje/brisanje, a menu servis dodatno
  odbija (403) ako konobarski token pri izmeni stavke dira bilo koje polje van
  dostupnosti/napomene/alergena. Konobar u toku smene menja isključivo
  dostupnost, napomenu i alergene stavke (FZ-8).

### FZ-12 — generisanje i štampa QR kodova (US-12)
- **FZ-12.1** Sistem mora vlasniku generisati potpisan link za svaki sto
  kafića (`GET /api/menu/cafes/{cafe_id}/qr-links`), sa istim HMAC potpisom
  koji gost koristi za pristup meniju (`table_signature`).
- **FZ-12.2** Sistem mora u admin panelu prikazati generisane linkove kao QR
  slike (klijentsko generisanje) i omogućiti njihovu štampu.
- **FZ-12.3** Ruta mora biti dostupna isključivo ulozi vlasnik.

### FZ-13 — upravljanje osobljem (US-13)
- **FZ-13.1** Sistem mora vlasniku prikazati spisak osoblja kafića
  (`GET /api/auth/cafes/{cafe_id}/staff`).
- **FZ-13.2** Sistem mora omogućiti vlasniku kreiranje novog naloga osoblja
  (uloga `konobar` ili `vlasnik`, email, lozinka, ime) preko
  `POST /api/auth/register`; sistem mora odbiti nepoznatu ulogu (HTTP 400).
- **FZ-13.3** Lozinke se moraju čuvati isključivo kao bcrypt heš — sistem ne
  sme ni u jednom trenutku sačuvati ili logovati lozinku u čitljivom obliku.
- **FZ-13.4** Rute uvida i kreiranja osoblja moraju biti dostupne isključivo
  ulozi vlasnik.

### FZ-14 — prikaz cene u stranoj valuti (US-14)
- **FZ-14.1** Sistem mora gostu ponuditi približnu cenu stavki menija u
  valuti EUR, USD, GBP ili CHF pored osnovne cene u RSD
  (`GET /api/menu/fx`).
- **FZ-14.2** Kursevi moraju biti keširani najviše 1 h; ako eksterni servis
  (Frankfurter) nije dostupan, sistem mora vratiti rezervne kurseve uz
  oznaku `fresh=false`, umesto da vrati grešku gostu.
- **FZ-14.3** Prikazana vrednost u stranoj valuti je isključivo informativna
  („≈ cena") — jedina merodavna cena za naplatu ostaje cena u RSD iz menu
  kataloga (FZ-1.4).

### FZ-15 — predlog alergena iz eksterne baze (US-15)
- **FZ-15.1** Sistem mora, na zahtev vlasnika/konobara koji unosi ili menja
  stavku menija, ponuditi predlog alergena pretragom eksterne baze
  OpenFoodFacts na osnovu naziva stavke (`GET /api/menu/allergens/search?q=`).
- **FZ-15.2** Predložene alergene sistem mora mapirati na fiksan skup
  srpskih naziva (npr. mleko, gluten, jaja, orašasti plodovi, kikiriki,
  soja, riba, rakovi, mekušci, susam, celer, slačica, sulfiti, lupina).
- **FZ-15.3** Predlog je isključivo informativan — vlasnik/konobar ručno
  potvrđuje konačnu listu alergena pre čuvanja stavke; ako eksterni servis
  ne odgovori, sistem mora vratiti praznu listu predloga bez greške
  (`available: false`), a ne prekinuti unos stavke.

### FZ-16 — uređivanje mape stolova (US-16)
- **FZ-16.1** Sistem mora omogućiti vlasniku uređivanje rasporeda stolova
  (dodavanje, uklanjanje, pomeranje, promena broja/zone/oblika/kapaciteta)
  na vizuelnom platnu (`PATCH /api/menu/cafes/{cafe_id}/tables`).
- **FZ-16.2** Sistem ne sme sačuvati raspored ako brojevi stolova nisu
  jedinstveni u okviru kafića (HTTP 400).
- **FZ-16.3** Ruta zamenjuje kompletnu listu stolova kafića odjednom
  (najviše 200 stolova) — nema parcijalnog ažuriranja pojedinačnog stola.
- **FZ-16.4** Ruta mora biti dostupna isključivo ulozi vlasnik.

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
  U sinhronoj verziji propušteni tiket (bar servis bio nedostupan) zapravo
  ostaje nevidljiv baru — best-effort poziv nema retry ni ponovno usklađivanje —
  pa je ovaj NFZ cilj koji tek treba u potpunosti ispuniti: ili da barkds pri
  startu povuče aktivne porudžbine iz orders-a, ili preko asinhronog toka
  (Kafka, Faza 4) gde bar konzument pročita propuštene događaje sa sačuvanog
  offset-a.

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
  potpis nad `cafe_id:table_number` sa deljenim tajnim ključem iz env
  promenljive `QR_SECRET` (heksadecimalni potpis dužine 64 karaktera) proverava
  se na svakoj **gostovoj** ruti (kreiranje porudžbine, pregled porudžbina
  stola, račun, otkazivanje, ocena, poziv konobara, online plaćanje);
  osobljanske rute se umesto potpisa štite JWT-om (NFZ-11). Već implementirano,
  nije predlog.
- **NFZ-11:** Pristup svakoj administrativnoj i osobljanskoj ruti (izmena
  menija, mapa stolova, QR generisanje, upravljanje osobljem, arhiva/pazar,
  naplata) mora zahtevati važeći JWT (HS256, TTL 12 h) — gateway odbija
  zahtev bez tokena ili sa isteklim/nevažećim tokenom sa HTTP 401 pre nego
  što stigne do servisa. Rute koje traže konkretnu ulogu (`vlasnik`) moraju
  vratiti HTTP 403 ako je token važeći ali uloga ne odgovara. Već
  implementirano na nivou gateway-a (`PROTECTED` lista ruta), nije predlog.
- **NFZ-12:** Lozinke naloga osoblja/vlasnika moraju se čuvati isključivo u
  vidu bcrypt heša — sistem nikad ne sme sačuvati, logovati ili vratiti
  lozinku u čitljivom obliku, ni internim rutama. Već implementirano, nije
  predlog.

