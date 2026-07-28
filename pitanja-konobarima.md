# Pitanja za konobare / barmene — validacija tablr funkcija

> Svrha: pre nego što gradimo neke funkcije, čuti ljude iz struke. Nije anketa —
> vodi to kao opušten razgovor uz kafu. Cilj je da razdvojimo "meni to zvuči kul"
> od "ovo bi mi stvarno pomoglo/smetalo u špicu".
>
> Kako koristiti: ne moraš sve odjednom. Izaberi 1–2 teme po osobi. Najvrednije su
> priče iz prakse ("kad je gužva, ja radim ovako..."), ne da/ne odgovori.
> Zabeleži KO je odgovorio (koliko iskustva, kakav lokal) — bitno za težinu odgovora.

---

## 0. Baza — kako stvarno teče špic (pusti ih da pričaju)
- Kad ti padne 5–6 porudžbina odjednom, kako biraš šta praviš prvo?
- Ideš li redom kako su stigle, ili grupišeš slične stvari?
- Šta te najviše uspori u naletu?

## 1. Grupisanje pića (batching) — SRŽ pitanja
- Kad ti dođu 3 kapućina odjednom, praviš li ih zajedno ili jedan po jedan?
- Koliko ti otprilike treba za 1 kapućino, a koliko za 3 zaredom? (tražimo da čuješ
  da 3 NIJE 3× jedan)
- Postoji li grupa pića koja ti je "usput" da radiš paralelno (dok radi aparat,
  točiš pivo...)? Koje kombinacije se lepo poklapaju, a koje se "biju"?
- Da li bi ti softver koji sabira "ova tura ≈ X min" uopšte značio, ili ti to
  ionako držiš u glavi?

## 2. Vreme po piću (za osećaj koliko da stavimo kao default)
- Koje piće je najbrže, koje najsporije za pripremu?
- Grubo: espreso ~? min, kapućino ~?, ceđena ~?, koktel ~?
- Šta menja vreme — gužva, spremljene sirovine, ko je za šankom?

## 3. Kokteli i procesi (ceđenje, muljanje, šejk...)
- Koji kokteli imaju "proces" koji traje (ceđenje limuna, muljanje nane, šejk, led)?
- Da li se koktel radi "u komadu" ili se neki delovi pripremaju unapred (npr.
  isečen limun, sirup)?
- Ima li smisla da sistem zna da koktel ima duži "proces" pa ga računa drugačije
  od kafe, ili je to preterivanje?

## 4. Procena vremena GOSTU (ETA)
- Da li bi bilo dobro da gostu na telefonu piše "otprilike ~5–10 min" kad poruči?
- Šta misliš da je gore: da mu pokažemo tačan broj (pa se naljuti ako kasni) ili
  grubi opseg? Ili da mu uopšte ne pišemo vreme?
- Da li bi ti to smanjilo pitanja tipa "gde mi je kafa" ili bi napravilo pritisak?

## 5. Živi tajmer na ekranu bara (VEĆ NAPRAVLJENO — validacija)
- Kad bi ti na ekranu svaka porudžbina imala tajmer "čeka 3:20" koji kuca, da li
  bi ti to pomoglo ili bi bio dodatni stres?
- Od koliko minuta bi porudžbina trebalo da "pocrveni" da kasni? (mi sad imamo 8)

## 6. Prioritet porudžbina (VEĆ NAPRAVLJENO — validacija)
- Mi sad ističemo NAJSTARIJU kao "prva na redu". Je li to pravo pravilo?
- Ima li stvari koje logično preskaču red (npr. pivo/sok ide odmah, a kuvano čeka)?
- Da li bi voleo da ti sistem sam predloži redosled, ili ti to radiš bolje od glave?

## 7. Detaljan račun gostu (KRUG 1 — pred gradnju)
- Da li gosti traže da vide račun na telefonu pre nego što plate?
- Šta očekuju da vide — samo svoje ili sve sa stola? Sa cenama po stavci?
- Da li bi njima to skratilo vreme ili napravilo zabunu?

## 8. Podela računa (KRUG 2 — DA LI UOPŠTE DA GRADIMO)
- Koliko često gosti u kafiću traže da razdvoje račun i plate posebno?
- Kako to sad rešavaš — na kalkulatoru, "ovo je moje", odokativno?
- Da li bi funkcija "svako skenira i plati svoje sa stola" bila korisna, ili u
  kafiću (za razliku od restorana) to skoro niko ne traži?
- Šta je najveći problem kad se deli račun (neko ode, neko ne plati svoje...)?

## 9. Naplata: keš vs kartica (VEĆ NAPRAVLJENO payment_method — validacija)
- Ko obično naplaćuje — ti dođeš do stola, ili gost dolazi do šanka/kase?
- Odnos keš/kartica kod vas otprilike?
- Da li bi ti značilo da na kraju smene vidiš koliko je išlo keš, koliko kartica?

## 10. Ocena gosta (VEĆ NAPRAVLJENO — validacija)
- Da li misliš da bi gosti stvarno ostavljali ocenu posle pića?
- Da li tebi kao konobaru ocena nešto znači, ili je to samo za gazdu?
- Šta bi bilo korisnije — ocena (zvezdice) ili slobodan komentar/žalba?

## 11. Statistika pripreme po konobaru (KRUG 2 prep — ideja)
- Kako bi ti bilo da sistem meri koliko ti u proseku treba da spremiš porudžbinu?
- Da li bi to doživeo kao korisnu povratnu informaciju ili kao nadzor/pritisak?
  (bitno — ako smeta ljudima, ne radimo)
- Da li bi voleo da vidiš svoj prosek na kraju smene?

## 12. Otvoreno (najvredniji deo)
- Šta te u toku smene NAJVIŠE nervira, a softver bi mogao da reši?
- Da imaš čarobni ekran na baru koji ti pokazuje bilo šta — šta bi hteo da vidiš?
- Šta od svega ovoga zvuči kao "e to bi mi stvarno pomoglo", a šta kao "bezveze,
  samo smeta"?

---

### Beleške posle razgovora (popuniti)
- Ko / kakav lokal / koliko iskustva:
- Najjači uvid:
- Šta menja naš plan:
