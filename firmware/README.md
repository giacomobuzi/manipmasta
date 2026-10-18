# ManipMasta — firmware Arduino

Firmware per **Arduino Mega 2560 Rev3 + Ethernet Shield 2 (W5500)** della sfogliatrice a portale ManipMasta.
La specifica vincolante è [`../docs/SPEC.md`](../docs/SPEC.md): pinout, parametri, protocollo, stati e ciclo RUN
sono implementati come descritti lì. Le scelte su punti non definiti dalla SPEC sono elencate in fondo.

## Struttura

```
firmware/
├── platformio.ini            build PlatformIO (src_dir = manipmasta)
├── manipmasta/               sketch Arduino IDE
│   ├── manipmasta.ino        setup()/loop() → mmSetup()/mmLoop()
│   ├── config.h              pinout DEFINITIVO, ENA_ACTIVE_LEVEL, costanti homing/rete/ciclo
│   ├── params.h/.cpp         parametri EEPROM (magic, versione, CRC16), SET/GET/SAVE/DEFAULTS
│   ├── inputs.h/.cpp         ingressi con debounce, fronti pulsanti, ISR ESTOP/barriera
│   ├── motion.h/.cpp         X/Z1/Z2 (AccelStepper), R asservito a X, homing non bloccante
│   ├── cycle.h/.cpp          ciclo RUN (SPEC §4) come macchina a stati
│   ├── machine.h/.cpp        stati, supervisore sicurezza, lampade/buzzer, watchdog
│   ├── protocol.h/.cpp       parser comandi (seriale + MQTT)
│   └── net.h/.cpp            Ethernet, MQTT (LWT, backoff), JSON di stato
└── test/                     test host in C++ con mock di Arduino/AccelStepper/EEPROM/Ethernet/PubSubClient
```

## Librerie

| Libreria | Versione | Note |
|---|---|---|
| AccelStepper (waspinator / Mike McCauley) | ≥ 1.64 | assi X, Z1, Z2 |
| PubSubClient (knolleary) | ≥ 2.8 | serve `setBufferSize()` (il JSON di stato è circa 250 byte) |
| Ethernet (arduino-libraries) | ≥ 2.0.0 | W5500, `setConnectionTimeout()` |

Non serve ArduinoJson: il JSON viene costruito a mano.

## Compilazione e caricamento

### Arduino IDE 2
1. *Gestore librerie*: installare **AccelStepper**, **PubSubClient** e **Ethernet** (Arduino).
2. Aprire `firmware/manipmasta/manipmasta.ino` (il nome della cartella coincide con quello dello sketch).
3. *Scheda*: **Arduino Mega or Mega 2560**, *Processore*: ATmega2560, selezionare la porta.
4. *Verifica*, poi *Carica*. Monitor seriale a **115200**, fine riga **Newline** (oppure NL+CR).

### PlatformIO
```sh
cd firmware
pio run                      # compila (scarica da solo le lib_deps)
pio run -t upload            # carica
pio device monitor           # monitor seriale a 115200
```

### Test host (senza hardware)
```sh
cd firmware/test
./run_tests.sh               # oppure: make test
```
Compila la logica del firmware con g++ e dei mock minimali, poi esegue i test: parser, calcolo delle passate,
limiti software, homing, transizioni ESTOP/RESET, barriera, PAUSE/STOP, allarmi, asservimento R, JSON e MQTT.

> Watchdog: il firmware usa il watchdog AVR (2 s). Con il bootloader stk500v2 attuale della Mega non ci sono problemi.
> Le schede con il bootloader vecchio (precedente al 2014) restano bloccate dopo un reset da watchdog: in quel caso
> aggiornare il bootloader.

## Configurazione rete e MQTT (da seriale)

Al primo avvio la EEPROM non è valida e vengono caricati i default della SPEC §2.2 (sulla seriale compare un avviso).
Configurazione tipica:

```
SET mac A8:61:0A:AE:12:34        (MAC stampato sull'etichetta dello shield)
SET ip 192.168.50.60
SET gw 192.168.50.1
SET mask 255.255.255.0
SET dns 192.168.50.1
SET mqtt_host 192.168.50.10      (meglio un IP: la risoluzione DNS blocca il loop)
SET mqtt_port 1883
SET mqtt_user manipmasta
SET mqtt_pass <password>         (senza spazi; "-" = vuota)
SAVE
REBOOT
```

- Rete e MAC si applicano al riavvio (`REBOOT` o spegnimento). Le credenziali MQTT si applicano alla connessione successiva.
- `GET mqtt_pass` non mostra la password: risponde `***`.
- Client id MQTT: `manipmasta-<mac in esadecimale>`. LWT `manipmasta/online` = `0` (retained); quando si connette
  pubblica `1` (retained) e si sottoscrive a `manipmasta/cmd`.
- La riconnessione al broker si tenta **solo a macchina ferma**, con backoff da 2 s a 30 s, perché il `connect()`
  del W5500 è bloccante (timeout 0,8 s).

## Prima messa in servizio

> Prima di tutto controllare la catena di sicurezza: fungo, relè di sicurezza, KM1 e barriera.
> Lo stato `estop` e `curt` si legge con `STATUS`.

1. **Ingressi.** Con `STATUS` controllare `in`: `seat:1` con il portale in sede, `estop:0`, `curt:0`, i finecorsa a 0.
   Azionare a mano ogni finecorsa e verificare che il bit corrispondente passi a 1.
   I comandi di movimento richiedono il portale in sede (E06): per le prove al banco ponticellare SEAT_A e SEAT_B.
2. **Driver.** Al termine del BOOT (100 ms) i driver vengono abilitati (`en:1`). Dopo un'emergenza o un allarme serve `RESET`.
3. **Verso dei motori**, a macchina non homed, con velocità ridotta al 25 %:
   - `JOG X 10`: X deve andare verso X+ (lontano da X_MIN);
   - `JOG G 2`: **entrambi** i lati Z devono SALIRE (il gap aumenta);
   - `JOG R 50`: guardando dal lato in cui X avanza, il rullo deve girare nel verso del rotolamento.
   Se un asse va al contrario, invertirlo con `SET dir_inv <maschera>`, dove bit0 = X, bit1 = Z1, bit2 = Z2, bit3 = R.
   Esempio: `SET dir_inv 6` inverte Z1 e Z2. Poi `SAVE`.
   Senza homing, il JOG verso un finecorsa già impegnato viene rifiutato e il moto si ferma quando il finecorsa home interviene.
4. **Step/mm.**
   - X: con un metro, `JOG X 500`, misurare lo spostamento reale e calcolare `x_spm_nuovo = x_spm × 500 / misura`. Poi `SET x_spm …`.
   - Z: con un comparatore, `JOG G 20` e la stessa formula per `z_spm`.
   - R: segnare il rullo, `JOG R 314.16`, che corrisponde a 1 giro su un diametro di 100 mm, e correggere `r_spm`.
   Un cambio di `x_spm`, `z_spm`, `z_home_gap`, `x_home_off` o `dir_inv` annulla l'homing.
5. **Homing.** `HOME`: Z1 e Z2 salgono ognuno sul proprio finecorsa (veloce, arretramento di 2 mm, riavvicinamento lento),
   e questo livella il rullo. Poi X va verso X_MIN: il punto del finecorsa vale `x_min − x_home_off` e alla fine X si porta a `x_min`.
   Se una fase non si chiude entro il suo timeout, la macchina va in ALARM `HOME_Z1`, `HOME_Z2` o `HOME_X`.
6. **Calibrazione `z_home_gap` con lo spessimetro.**
   1. Fare `HOME`, poi `GAP 10`.
   2. Misurare con lo spessimetro (o con blocchetti) la luce reale tra rullo e piano, **ai due lati** del rullo.
   3. Calcolare `z_home_gap_nuovo = z_home_gap + (misura − 10)` e impostarlo con `SET z_home_gap …`. Poi `SAVE` e di nuovo `HOME`.
   4. Ripetere a `GAP 2` per la verifica fine.
   Se i due lati misurano luci diverse, i finecorsa home non sono alla stessa quota: regolarli meccanicamente.
   Tenere `g_max ≤ z_home_gap`: il firmware usa comunque come limite superiore `min(g_max, z_home_gap)`.
7. **Overdrive.** Fare una passata di prova su un impasto e regolare `od` (in %, da −10 a 20) finché la sfoglia non striscia né si arriccia.

## Comandi

Protocollo identico su USB seriale (115200) e MQTT (`manipmasta/cmd` → `manipmasta/resp`). Una riga per comando;
la parola chiave non distingue maiuscole e minuscole. Risposte: `OK <CMD> [info]` oppure `ERR Exx testo`.

| Comando | Effetto | Condizioni |
|---|---|---|
| `PING` | `OK PING` | — |
| `STATUS` | pubblica subito lo stato (sulla seriale stampa anche il JSON) | — |
| `HOME` | homing di Z (in alto, Z1 e Z2 indipendenti), poi di X (verso X_MIN) | IDLE o READY, in sede, barriera libera |
| `ENABLE 1` / `ENABLE 0` | abilita / disabilita i driver (con `0` l'homing si perde) | `0` solo a macchina ferma |
| `JOG X <mm>` / `JOG G <mm>` / `JOG R <mm>` | movimento relativo; `G` è il gap (positivo = sale) | se homed, entro i limiti software |
| `MOVE X <mm> [F <mm/s>]` | X in assoluto, con R asservito | homed, `0 < F ≤ x_vmax` |
| `GAP <mm>` | gap in assoluto (Z1 e Z2 insieme) | homed, `g_min ≤ gap ≤ min(g_max, z_home_gap)` |
| `RUN cx= s0= s1= g0= g1= dg= f= n= od=` | ciclo di sfogliatura; risponde `OK RUN np=N` | homed, in sede, nessun allarme |
| `PAUSE` | pausa alla fine del segmento corrente | RUNNING |
| `RESUME` | ripresa | PAUSED, barriera libera, assi fermi |
| `STOP` | decelera, annulla il ciclo, Z sale di 20 mm (fino al limite) | sempre |
| `RESET` | uscita da ALARM o ESTOP verso IDLE (driver riabilitati) | emergenza rilasciata |
| `SET <k> <v>` / `GET <k>` | lettura e scrittura dei parametri in RAM | SET solo a macchina ferma |
| `SAVE` / `DEFAULTS` | salva in EEPROM / ricarica i default (poi serve `SAVE`) | a macchina ferma |
| `REBOOT` | riavvio tramite watchdog (serve per applicare la rete) | a macchina ferma |

Chiavi per `SET`/`GET`: `x_spm z_spm r_spm x_min x_max g_min g_max z_home_gap x_vmax x_acc z_vmax z_acc x_home_off od
dir_inv mac ip gw mask dns mqtt_host mqtt_port mqtt_user mqtt_pass`.

Codici di errore: `E01` comando sconosciuto · `E02` parametro non valido · `E03` non homed · `E04` stato non consente ·
`E05` fuori limiti · `E06` portale non in sede · `E07` emergenza attiva · `E08` allarme driver.

Eventi (`manipmasta/event` e seriale `EVT …`): `BOOT`, `HOMING`, `HOMED`, `CYCLE_START`, `PASS k/np`, `PAUSED`, `RESUME`,
`CURTAIN`, `STOP`, `STOPPED`, `CYCLE_DONE`, `ALARM <causa>`, `ESTOP`, `RESET`, `SEAT_LOST`, `BTN_STOP`, `ERR …` (dai pulsanti).
Le cause di allarme sono `X_ALM`, `Z1_ALM`, `Z2_ALM`, `R_ALM`, `X_MAX`, `X_MIN`, `Z1_LOW`, `Z2_LOW`, `SEAT`, `HOME_Z1`, `HOME_Z2` e `HOME_X`.

### Ciclo RUN

`np = ceil((g0 − g1)/dg) + n` passate doppie. Per la passata doppia k (con k da 0 a np−1):
1. andata fino a `cx + s_k + 60` al gap `G_k`;
2. fuori impasto, Z passa a `G_{k+1} = max(g1, G_k − dg)`;
3. ritorno fino a `cx − s_k − 60`.

`G_0 = g0` e `s_k` è interpolata linearmente da s0 a s1. Prima del ciclo: Z a `g0+20`, X a `cx−s0−60`, Z a `g0`.
Alla fine: Z a `g1+30`, X a `cx`, evento `CYCLE_DONE` e 3 bip. I gap di sicurezza vengono limitati a `min(g_max, z_home_gap)`.
I parametri mancanti prendono i default dell'esempio della SPEC (`cx=0 s0=150 s1=300 g0=40 g1=5 dg=3 f=60 n=2`) e `od` dalla EEPROM.
Il pulsante START, da READY, rilancia il RUN con gli ultimi parametri; da PAUSED esegue RESUME.

### Lampade
| Stato | Verde | Giallo | Rosso |
|---|---|---|---|
| READY | fisso | | |
| RUNNING / MOVING / HOMING | lampeggiante | | |
| IDLE / PAUSED / BOOT | | fisso | |
| ALARM / ESTOP | | | fisso |

## Sicurezza (riassunto del comportamento)

- **ESTOP_OK (pin 2, interrupt).** L'ISR disabilita subito i driver (ENA). Il loop poi ferma gli assi senza rampa,
  passa in `ESTOP` e azzera l'homing. Si esce solo con `RESET`, a catena ripristinata.
- **CURTAIN_OK (pin 3, interrupt).** Barriera interrotta durante RUNNING o MOVING: arresto rapido (3000 mm/s² su X)
  e stato `PAUSED` con evento `CURTAIN`. Si riparte solo con `RESUME` (o START) a barriera libera; il segmento interrotto viene rifatto.
  Durante HOMING la barriera interrompe l'homing e la macchina torna in IDLE.
- **ALM dei driver** (basso, controllato solo a driver abilitati e 300 ms dopo l'abilitazione): `ALARM`, driver disabilitati.
- **Extracorsa** (`X_MAX`, `Z1_LOW`, `Z2_LOW`) quando l'asse si muove verso il finecorsa: `ALARM` con arresto rapido. Con homing valido anche `X_MIN` è un'extracorsa.
- **BTN_STOP** (NC, alto = premuto o filo rotto): equivale a `STOP`. Finché resta alto, START e i comandi di movimento sono rifiutati.
- **Portale tolto**: durante un movimento va in `ALARM SEAT`; a riposo annulla l'homing.
- **Watchdog** a 2 s. Viene allargato a 8 s solo durante la risoluzione DNS del broker, che avviene a macchina ferma.

Il firmware **non sostituisce** la catena di sicurezza hardware (fungo, relè di sicurezza, KM1).

## Limiti noti

- Le `publish` MQTT durante il moto passano per lo stack TCP del W5500. Se il broker sparisce durante un movimento,
  un invio può bloccarsi fino a circa 150 ms (timeout di ritrasmissione impostato a 50 ms × 3). La rete viene servita
  al massimo ogni 5 ms e lo stato ogni 200 ms.
- PubSubClient pubblica solo con QoS 0. La sottoscrizione a `manipmasta/cmd` è con QoS 1.
- AccelStepper scrive DIR e PUL a pochi µs di distanza. I cambi di verso avvengono a velocità quasi nulla e con il CL57T
  non ci sono problemi, ma se il driver perde passi all'inversione conviene aggiungere un ritardo.
- Il valore di `up` nel JSON è l'uptime in **secondi**.
