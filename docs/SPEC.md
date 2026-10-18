# ManipMasta — Specifica tecnica di riferimento

Documento unico di riferimento per meccanica, elettronica, firmware, server e app.
Ogni modulo del repository DEVE restare coerente con questo file. Unità: mm, s, N.

## 0. Ipotesi di progetto (da confermare con le misure reali)

| Parametro | Valore ipotizzato | Note |
|---|---|---|
| Tavolo | 2000 (X, lunghezza) × 800 (Y, profondità) × 900 (h) | piano inox AISI 304 sp. 40 (lamiera su pannello) |
| Origine | centro del piano del tavolo, Z=0 sul piano, Z verso l'alto | |
| Impasto | palla 1–3 kg al centro (X=0, Y=0) | sfoglia finale 2–15 mm |
| Uso | laboratorio pasticceria, contatto alimentare | parti a contatto: AISI 304/316 o POM-C/PE-HD alimentare |

Tutte le quote sono parametriche (`cad/params.json`): con le misure reali si rigenera tutto.

## 1. Architettura meccanica

- **4 ancoraggi fissi** (parallelepipedi AISI 304, 100×100×50) imbullonati agli angoli del tavolo,
  centri a (±930, ±340). Restano sempre sul tavolo.
  - A1 (X−, Y−): foro di riferimento Ø20 H7 (centraggio).
  - A2 (X+, Y−): asola 20 H7 × 26 lungo X (elimina l'iperstaticità, assorbe tolleranze/dilatazioni).
  - A3 (X−, Y+) e A4 (X+, Y+): foro Ø26 di solo appoggio (gioco).
  - A1 e A2 hanno foro trasversale Ø8 H8 per perno di bloccaggio a sfere (ball-lock pin).
  - Fissaggio al tavolo: 4 fori M8 ciechi sul fondo + contropiastra sotto il piano (passante), oppure staffa a C sul bordo.
- **Struttura mobile (portale)** che si appoggia e si toglie dagli ancoraggi:
  - 4 montanti tubo quadro AISI 304 60×60×3, con piastra piede 120×120×10 e perno di centraggio Ø20 g6 (punta conica) che entra negli ancoraggi.
  - 2 longheroni X tubo rettangolare 80×40×3 (80 in verticale) a Y=±340, piano superiore a Z=470.
  - 2 traversi Y tubo 60×40×3 alle estremità X=±930.
  - Peso stimato portale completo: ~45–55 kg → 2 maniglie per lato, sollevamento in 2 persone.
  - Sensore induttivo M12 in 2 piedi (A1, A2) per conferma "portale in sede".
- **Asse X (traslazione rullo)**: guide supportate SBR20 (L=1800) sui longheroni, 2 pattini SBR20UU per lato.
  Trazione a cinghia HTD‑5M larghezza 15, un motore su traverso X−, albero di sincronismo Ø16 su Y
  con pulegge 20 denti ai due lati (nessun disallineamento del ponte). Corsa utile del rullo ±700 (limitata dall'albero di sincronismo a X=−870).
  - passo: 1 giro puleggia = 100 mm; driver 1600 impulsi/giro → **16 step/mm**.
- **Asse Z (altezza rullo = spessore sfoglia)**: su ogni carrello X una piastra verticale con 2 guide
  tonde Ø16 h6 inox (L≈370) su supporti SK16 con pattini SC16UU e vite trapezia TR16×4 comandata da un motore dedicato (Z1 lato Y−, Z2 lato Y+).
  Vite autobloccante: il rullo non scende a motori spenti.
  - driver 800 impulsi/giro, passo 4 mm → **200 step/mm**.
  - Homing in ALTO (sicuro), ognuno sul proprio finecorsa → auto-livellamento del rullo.
  - Quota Z espressa come **gap = luce tra rullo e piano** (0…150 mm). Calibrazione: `z_home_gap` in EEPROM.
- **Rullo (cilindro)**: tubo AISI 304 Ø100×3, tavola utile 370 mm (con tavolo da 900 mm di profondità si arriva a ~470), testate saldate e perni Ø20,
  rettificato e lucidato Ra ≤ 0,8 µm (alternativa: POM‑C alimentare pieno Ø100). Supporti: 2 unità flangiate quadre inox SUCF204 (4 fori, interasse 64).
  Raschietto in POM‑C a molla sul lato superiore.
- **Asse R (rotazione rullo motorizzata)**: motore su piastra Z1, cinghia HTD‑5M 15, pulegge 20T (motore) → 40T (rullo), rapporto 2:1.
  Sviluppo superficie per giro motore = π·100/2 = 157,08 mm; driver 800 impulsi/giro → **5,093 step/mm di superficie**.
  R è **asservito elettronicamente a X** (velocità periferica = velocità di traslazione × (1 + overdrive%)) per evitare strisciamento.
- Ponte: traversa tubo 40×40×2 tra i due carrelli X (squadratura + passaggio cavi). Catena portacavi lungo il longherone Y−.

## 2. Elettronica

| Rif | Componente |
|---|---|
| MCU | **Arduino Mega 2560 Rev3** + **Arduino Ethernet Shield 2 (W5500)** — cablato, niente Wi‑Fi in laboratorio |
| M1 X | NEMA23 closed-loop ~2 Nm + driver CL57T (o equivalente step/dir con encoder) |
| M2 Z1, M3 Z2 | NEMA23 closed-loop ~2 Nm + driver CL57T |
| M4 R | NEMA23 closed-loop ~1,2–2 Nm + driver CL57T |
| PSU1 | 48 V DC 480 W (Mean Well SDR-480-48) → driver |
| PSU2 | 24 V DC 60 W (Mean Well HDR-60-24) → sensori, relè, colonna luminosa |
| PSU3 | 12 V DC 15 W (Mean Well HDR-15-12) → Vin Arduino |
| Ingressi 24 V | 2 schede optoisolate 24→5 V (PC817, 8 canali: U6 sensori, U7 emergenza/barriera/pulsanti) — logica **attiva BASSA** lato Arduino (INPUT_PULLUP) |
| Relè uscite | modulo 4 relè 5 V **attivo ALTO** (verificare jumper) con bobine alimentate da DC/DC 24→5 V dedicato (U9), non dal 5 V dell'Arduino |
| Sicurezza | fungo emergenza 2NC + modulo relè di sicurezza cat. 3 → contattori **KM1 + KM2 in serie** (ridondanza, retroazione NC in serie al reset) su alimentazione AC di PSU1; contatto ausiliario all'Arduino |
| Barriera | barriera fotoelettrica di sicurezza tipo 2/4 sui lati lunghi: per essere funzione di sicurezza le OSSD devono agire su KM1/KM2 tramite un secondo modulo di sicurezza; in più segnale all'Arduino (D3) per la pausa controllata |
| Quadro | cassetta inox IP65 **500×400×250** (la 400×300 è satura), ventilazione filtrata IP54 |

### 2.1 Pinout Arduino Mega 2560 (DEFINITIVO)

Riservati shield Ethernet: D4 (SD CS, tenere ALTO), D10 (W5500 CS), D50–D53 (SPI). Non usarli.

| Funzione | Pin | Dir | Note |
|---|---|---|---|
| X PUL / DIR / ENA | 22 / 23 / 24 | OUT | |
| X ALM | 25 | IN_PULLUP | basso = allarme driver |
| Z1 PUL / DIR / ENA | 26 / 27 / 28 | OUT | |
| Z1 ALM | 29 | IN_PULLUP | |
| Z2 PUL / DIR / ENA | 30 / 31 / 32 | OUT | |
| Z2 ALM | 33 | IN_PULLUP | |
| R PUL / DIR / ENA | 34 / 35 / 36 | OUT | |
| R ALM | 37 | IN_PULLUP | |
| X_MIN (home) | 38 | IN_PULLUP | finecorsa induttivo, basso = attivo |
| X_MAX (extracorsa) | 39 | IN_PULLUP | |
| Z1_HOME (alto) | 40 | IN_PULLUP | |
| Z2_HOME (alto) | 41 | IN_PULLUP | |
| Z1_LOW (extracorsa basso) | 42 | IN_PULLUP | |
| Z2_LOW (extracorsa basso) | 43 | IN_PULLUP | |
| SEAT_A (portale in sede A1) | 44 | IN_PULLUP | basso = in sede |
| SEAT_B (portale in sede A2) | 45 | IN_PULLUP | |
| BTN_START (pannello) | 48 | IN_PULLUP | |
| BTN_STOP (pannello, NC) | 49 | IN_PULLUP | ALTO = premuto/filo rotto |
| ESTOP_OK | 2 | IN_PULLUP + INT | BASSO = catena sicurezza OK; ALTO = emergenza |
| CURTAIN_OK | 3 | IN_PULLUP + INT | BASSO = barriera libera; ALTO = interrotta |
| Lampada verde | 5 | OUT | modulo relè, attivo ALTO |
| Lampada gialla | 6 | OUT | |
| Lampada rossa | 7 | OUT | |
| Buzzer | 8 | OUT | |

Driver CL57T: ingressi optoisolati 5 V a catodo comune: PUL+ ← pin, PUL− → GND (idem DIR, ENA).
ENA: pin ALTO = driver **disabilitato** (logica CL57T: opto attivo = disable). Il firmware definisce `ENA_ACTIVE_LEVEL` in `config.h`.
All'accensione/reset i pin sono flottanti: resistenza di pull-up 4,7 kΩ verso 5 V su ogni ENA+ così i driver partono disabilitati.
I pin 22–37 condividono un gruppo di porte del Mega (limite 100 mA): con driver ad alto assorbimento d'ingresso usare un buffer 74HCT245/ULN.
ALM+: → pin Arduino (pull-up), ALM− → GND.

### 2.2 Parametri motore (default, modificabili via `SET`, salvati in EEPROM)

| Chiave | Default | Significato |
|---|---|---|
| x_spm | 16.0 | step/mm X |
| z_spm | 200.0 | step/mm Z |
| r_spm | 5.093 | step/mm superficie rullo |
| x_min / x_max | -700 / 700 | limiti software X (mm) |
| g_min / g_max | 0.5 / 150 | limiti software gap (mm) |
| z_home_gap | 150.0 | gap reale quando Z è sul finecorsa alto (calibrazione) |
| x_vmax / x_acc | 150 / 300 | mm/s, mm/s² |
| z_vmax / z_acc | 8 / 20 | |
| x_home_off | 20 | dopo homing X si porta a x_min+… |
| od | 2.0 | overdrive rullo % |
| ip / gw / mask / dns | 192.168.50.60 / .1 / 255.255.255.0 / .1 | rete (VLAN IoT) |
| mqtt_host / mqtt_port | 192.168.50.10 / 1883 | broker sulla VM |
| mqtt_user / mqtt_pass | manipmasta / (impostare) | |

## 3. Protocollo di comando (identico su USB‑Serial 115200 e MQTT)

Testo ASCII, una riga per comando, case-insensitive per la parola chiave. Risposte: `OK <cmd>` oppure `ERR <codice> <testo>`.

MQTT (QoS 0/1):
- `manipmasta/cmd` → comandi verso Arduino (server pubblica)
- `manipmasta/resp` → risposte `OK…`/`ERR…`
- `manipmasta/state` → JSON stato (ogni 200 ms in movimento, ogni 2 s a riposo), retained
- `manipmasta/event` → eventi testuali (`HOMED`, `CYCLE_START`, `PASS 3/12`, `CYCLE_DONE`, `ALARM X_ALM`, `ESTOP`…)
- `manipmasta/online` → `1`/`0` retained (LWT `0`)

Comandi:

| Comando | Effetto |
|---|---|
| `PING` | → `OK PING` |
| `STATUS` | pubblica subito lo stato |
| `HOME` | homing Z (alto, Z1/Z2 indipendenti) poi X (verso X_MIN) |
| `ENABLE 1` / `ENABLE 0` | abilita/disabilita driver (0 solo se fermo) |
| `JOG X <mm>` / `JOG G <mm>` / `JOG R <mm>` | movimento relativo (G = gap) |
| `MOVE X <mm> [F <mm/s>]` | assoluto X |
| `GAP <mm>` | assoluto gap (Z1 e Z2 insieme) |
| `RUN cx=0 s0=150 s1=300 g0=40 g1=5 dg=3 f=60 n=2 od=2` | ciclo sfogliatura (vedi §4); parametri mancanti = default |
| `PAUSE` / `RESUME` | pausa a fine movimento corrente (rullo resta in quota) / ripresa |
| `STOP` | arresto con decelerazione, ciclo annullato, Z sale a gap sicuro |
| `RESET` | reset allarmi (solo se cause rimosse) |
| `SET <chiave> <valore>` / `GET <chiave>` / `SAVE` / `DEFAULTS` | parametri EEPROM |

Stato JSON (`manipmasta/state`):

```json
{"st":"READY","hm":1,"en":1,"x":0.00,"g":40.00,"z1":40.00,"z2":40.00,"r":0.0,
 "cyc":{"pass":3,"np":12,"gap":31.0},"in":{"xmin":0,"xmax":0,"z1h":0,"z2h":0,"seat":1,"estop":0,"curt":0},
 "alm":"","fw":"1.0.0","up":123456}
```

Stati `st`: `BOOT`, `IDLE` (non homed), `HOMING`, `READY`, `MOVING`, `RUNNING`, `PAUSED`, `ALARM`, `ESTOP`.
Codici errore: `E01` comando sconosciuto, `E02` parametro non valido, `E03` non homed, `E04` stato non consente, `E05` fuori limiti, `E06` portale non in sede, `E07` emergenza attiva, `E08` allarme driver.

## 4. Ciclo di sfogliatura `RUN`

Parametri: `cx` centro impasto (mm, X), `s0`→`s1` semicorsa iniziale→finale (mm, l'impasto si allarga),
`g0`→`g1` gap iniziale→finale, `dg` riduzione gap per ogni passata doppia, `f` velocità di lavoro mm/s,
`n` passate extra al gap finale, `od` overdrive rullo %.

1. Precondizioni: homed, portale in sede, emergenza e barriera OK, nessun allarme.
2. Z a gap sicuro `g0 + 20`, X a `cx − s0 − 60` (fuori dall'impasto), Z a `g0`.
3. Passata avanti fino a `cx + s + 60` con R asservito; a fine corsa (fuori impasto) si applica il nuovo gap; passata indietro.
4. Ogni passata doppia: `gap = max(g1, gap − dg)`, `s` interpolata linearmente tra s0 e s1 sul numero di passate.
5. Al gap finale: `n` passate doppie extra. Poi Z a `g1 + 30`, X a `cx` (rullo sollevato al centro), evento `CYCLE_DONE`.
Numero passate doppie: `np = ceil((g0 − g1)/dg) + n`.

## 5. Software lato VM

- VM Linux (Debian 12/13 o Ubuntu 24.04) su Proxmox, Docker Compose: `mosquitto` (1883 solo VLAN IoT, user/pass, ACL) + `manipmasta-server` (FastAPI, porta 8080).
- API REST (header `Authorization: Bearer <API_TOKEN>`):
  - `GET /api/state` · `POST /api/cmd {"cmd":"HOME"}` · `GET/POST/PUT/DELETE /api/recipes[/{id}]` · `POST /api/recipes/{id}/run` · `GET /api/history` · `GET /api/health` (senza auth)
  - `WS /ws?token=…` → push stato/eventi/risposte in JSON `{"type":"state|event|resp|online","data":…}`
- UI web mobile-first servita da `/` (stessa base per l'app Android).
- Esposizione: Nginx Proxy Manager → `https://manipmasta.<dominio>` → `vm:8080`, Websockets ON, certificato Let's Encrypt.
- Simulatore (`server/simulator.py`) che si comporta come l'Arduino su MQTT, per provare UI e app senza hardware.

## 6. App Android

App nativa Kotlin (package `it.mybuzi.manipmasta`, minSdk 26) — WebView sulla UI del server con: configurazione URL e token,
schermo sempre acceso durante il ciclo, pulsante STOP nativo sempre visibile (chiama `POST /api/cmd STOP`), notifiche di fine ciclo
via polling WebSocket in foreground. Build APK automatica su GitHub Actions.

## 7. Integrazioni allineate tra firmware, server e simulatore

- Risposte con valore: `OK GET <chiave> <valore>` e `OK SET <chiave> <valore>`.
- Eventi emessi: `BOOT`, `HOMING`, `HOMED`, `CYCLE_START`, `PASS k/np` (inizio passata k), `PAUSED`, `RESUME`, `CYCLE_DONE`,
  `STOP`/`STOPPED`, `ALARM <causa>`, `ESTOP`, `CURTAIN`, `SEAT_LOST`, `BTN_STOP`, `RESET`.
- Comando aggiuntivo `REBOOT` (applica i parametri di rete dopo `SAVE`); parametri aggiuntivi `mac` (client id MQTT) e `dir_inv` (bitmask inversione verso: bit0 X, bit1 Z1, bit2 Z2, bit3 R).
- Ciclo RUN: la passata doppia k va avanti al gap G_k; fuori dall'impasto si applica `max(g1, G_k − dg)` e si torna indietro.
- I gap di sicurezza (`g0+20`, `g1+30`) sono limitati a `min(g_max, z_home_gap)`.
- PubSubClient pubblica a QoS 0; con broker irraggiungibile durante un movimento una publish può bloccare il loop fino a ~150 ms (documentato in firmware/README.md).
