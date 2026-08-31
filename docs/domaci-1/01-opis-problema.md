# 1. Opis problema

## Uvod u problem

U manjim ugostiteljskim objektima (kafići, barovi, splavovi) tokom špica rada —
kada je sala puna, a osoblje malobrojno — najveće usko grlo nije priprema pića
ili hrane, već **komunikacija između gosta i osoblja**: gost mora fizički da
dozove konobara da poruči, da pita da li je stavka na meniju uopšte dostupna,
da sazna da li je porudžbina uopšte stigla do šanka, da ponovo dozove konobara
kada želi račun, i na kraju da se sa ostatkom društva za stolom dogovori ko
šta plaća. Svaki od ovih koraka troši vreme konobara koje bi moglo da ide na
opsluživanje drugih stolova, i produžava vreme koje gost provede za stolom bez
da je za to plaćeno (sporija rotacija stolova).

**tablr** rešava ovaj problem tako što gost sam poručuje i prati porudžbinu sa
sopstvenog telefona, skeniranjem QR koda nalepljenog na sto — bez instalacije
aplikacije, bez pravljenja naloga. Konobar dobija porudžbine i zahteve gostiju
uživo na bar dashboard-u, umesto da ih zapisuje na papir ili pamti napamet.
Cilj je da jedan konobar sa manje trčanja opsluži više stolova, a da gost ima
osećaj kontrole (vidi status porudžbine, može da otkaže dok nije prihvaćena,
može sam da plati) bez potrebe da nekog zaustavlja.

## Opis domena

tablr je **multi-tenant** sistem — jedna instalacija istovremeno opslužuje više
kafića, svaki identifikovan sa `cafe_id`; svi entiteti (meni, sto, porudžbina,
tiket) nose taj identifikator, tako da su podaci različitih kafića potpuno
razdvojeni — gateway pri svakoj zaštićenoj ruti proverava da prijavljeno
osoblje pristupa isključivo svom kafiću.

Tok kroz domen izgleda ovako:

1. **Identitet stola bez naloga.** Svaki sto u kafiću ima QR kod koji kodira
   `cafe_id`, broj stola i **HMAC-SHA256 potpis** (izveden iz tajnog ključa
   `QR_SECRET` koji drži samo server). Gost otvaranjem QR linka dobija sesiju
   vezanu za taj sto — nema registracije, lozinke ni ličnih podataka. Potpis
   sprečava da gost izmisli broj stola koji nije njegov.
2. **Meni.** Kafić održava katalog kategorija i stavki (naziv, cena, opis,
   alergeni, dostupnost, napomena) — pun CRUD radi vlasnik u admin panelu, dok
   konobar u toku smene menja samo dostupnost, napomenu i alergene. Gost vidi
   samo ono što je trenutno dostupno.
3. **Porudžbina.** Gost sastavi korpu i pošalje porudžbinu. Server ponovo
   validira svaku stavku i cenu direktno iz kataloga (cena se **nikad** ne
   prihvata od klijenta) i potpis stola. Porudžbina zatim prolazi kroz jasno
   definisan životni ciklus statusa: `CREATED → ACCEPTED → READY → DELIVERED`,
   sa mogućim ranim izlazom u `CANCELLED`. Vlasnik ove tranzicije je isključivo
   servis za porudžbine — bar samo predlaže promenu, koja se validira na
   serverskoj strani.
4. **Bar / kuhinja.** Nova porudžbina se odmah prosleđuje bar servisu kao
   "tiket" koji se pojavljuje na dashboard-u konobara uživo (WebSocket), grupisan
   po statusu, tako da osoblje vidi šta treba da pripremi i šta treba da
   isporuči — bez papira i bez glasnog dovikivanja porudžbina.
5. **Interakcija bez prekidanja osoblja.** Gost sa istog ekrana može da pozove
   konobara, zatraži račun, otkaže porudžbinu dok još nije prihvaćena, i posle
   isporuke oceni porudžbinu — sve to stiže konobaru kao zahtev na dashboard-u,
   umesto da gost ustaje ili viče.
6. **Račun i plaćanje.** Gost može da vidi zbirni račun celog stola, da izabere
   samo svoje stavke i zatraži da se one naplate posebno (podela računa), i da
   plati gotovinom/karticom preko konobara ili online (demo Google Pay tok) —
   bez potrebe da se čitav sto slaže oko jednog zajedničkog računa.
7. **Administracija kafića.** Vlasnik samostalno registruje svoj kafić kroz
   javnu proceduru onboardinga (bez ručne intervencije), zatim iz posebne
   admin aplikacije uređuje ceo meni (kategorije i stavke, ne samo dostupnost
   u toku smene), generiše i štampa QR kodove za stolove i dodaje naloge
   osoblja. Konobar i vlasnik su od uvođenja autentifikacije razdvojeni
   pristupnim pravima — konobar radi svakodnevnu opsluge (tabla, statusi,
   naplata), dok su administrativne radnje (pun CRUD menija, QR kodovi, osoblje,
   pazar kafića) rezervisane isključivo za vlasnika.

Sistem je organizovan kao skup nezavisnih mikroservisa iza jednog API gateway-a:
**menu** (katalog i mapa stolova, MongoDB), **orders** (porudžbine i status
tok, PostgreSQL), **barkds** (bar/kuhinjski ekran uživo, MongoDB, WebSocket),
**payments** (demo online naplata) i **auth** (JWT autentifikacija i uloge
vlasnik/konobar, PostgreSQL). Gateway validira JWT token za sve zaštićene
(osobljanske i administrativne) rute i propušta gostove rute koje umesto
prijave koriste HMAC potpis stola — gost tako ostaje potpuno anoniman, dok
je pristup osoblja i vlasnika sistemu autentifikovan i ograničen po ulozi.
Gost, bar dashboard i admin panel komuniciraju isključivo kroz gateway
(`/api/{servis}/...` i `/ws/bar/{cafe_id}`) — direktan pristup internim
rutama servisa spolja je blokiran.
