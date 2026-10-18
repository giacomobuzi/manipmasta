# ManipMasta — documentazione di cablaggio

> **Avvertenza.** Questi schemi sono un progetto **indicativo**. Il quadro va realizzato, collaudato e
> dichiarato conforme da un **elettricista qualificato** secondo **CEI EN 60204-1** (equipaggiamento
> elettrico delle macchine), con valutazione dei rischi e del Performance Level della funzione di
> emergenza secondo EN ISO 13849-1. Riferimento unico per pin e componenti: `docs/SPEC.md` §2 e §2.1.

## Contenuto

| File | Descrizione |
|---|---|
| `generate_wiring.py` | genera tutte le tavole (solo matplotlib). `python3 generate_wiring.py` ; con `--md` stampa le tabelle di questo README |
| `out/E01.svg/.png` | **E01 Potenza** — 230 V, Q1, Q2, F1–F3, KM1, PSU1/2/3, fusibili driver F11–F14, distribuzione 48 V/24 V, barra PE |
| `out/E02.svg/.png` | **E02 Sicurezza** — fungo S0 2NC, reset S1, relè di sicurezza K1, KM1 con retroazione, barriera LC1 → K2/K3 → D3 |
| `out/E03.svg/.png` | **E03 Arduino e driver** — 4 × CL57T: PUL/DIR/ENA/ALM, alimentazione 48 V, fasi motore ed encoder via XP1 |
| `out/E04.svg/.png` | **E04 Ingressi/uscite** — sensori B1–B8 via XP2 → U6, pulsanti e sicurezze → U7, D5–D8 → U8 → colonna luminosa |
| `out/E05.svg/.png` | **E05 Disposizione quadro** — piastra, parete laterale, fondo con connettori Harting, porta, collegamento al portale |
| `out/schemi_elettrici.pdf` | le 5 tavole in un PDF A3 orizzontale |
| `out/elenco_fili.csv` | elenco fili (stesso contenuto della tabella sotto, separatore `;`) |

## Sigle principali

| Sigla | Componente |
|---|---|
| X0 | morsetti ingresso rete L, N, PE |
| Q1 | interruttore generale magnetotermico 2P C10, 6 kA |
| Q2 | differenziale 2P 25 A, Id 30 mA tipo A (facoltativo se già presente a quadro di laboratorio dedicato) |
| X1 | distribuzione 230 V (X1:1–3 L, X1:4–6 N) |
| F1 / F2 / F3 | fusibili 10×38 gG su L: PSU1 6,3 A, PSU2 2 A, PSU3 1 A (taratura da confermare con lo spunto delle PSU) |
| KM1 | contattore AC-3 ≥ 9 A, bobina 24 V DC con soppressore, contatto ausiliario NC 21-22 |
| PSU1 | Mean Well SDR-480-48 — 48 V 10 A, solo driver |
| PSU2 | Mean Well HDR-60-24 — 24 V 2,5 A (sicurezza, sensori, relè, colonna) |
| PSU3 | Mean Well HDR-15-12 — 12 V, Vin Arduino |
| F4 / F5 | fusibili 5×20 2 A T su +24 V: F4 circuito di sicurezza (X3:1–4), F5 I/O (X3:5–13) |
| F11–F14 | fusibili 5×20 **5 A T** sul +48 V, uno per driver |
| X2 | distribuzione 48 V (X2:1–4 +48 V, X2:5–9 0V48) |
| X3 / X4 | +24 V (X3:1–4 sicurezza, X3:5–13 I/O) / 0V24 (X4:1–12) |
| X6 / X7 | GND logica 5 V (X6:1–8) / +5 V logica da Arduino (X7:1–4) |
| K1 | modulo relè di sicurezza 2 canali, cat. 3 / PL d, reset manuale controllato (es. PNOZ X2.8P, SRB 301MC o equivalente) |
| K2, K3 | relè di interfaccia 24 V DC, 1 contatto NO (OSSD1, OSSD2 della barriera) |
| S0 | fungo di emergenza a ritenuta 2NC (porta) |
| S1 / S2 / S3 | RESET blu NO / START verde NO / STOP nero NC (porta) |
| LC1 | barriera fotoelettrica di sicurezza tipo 4 (TX emettitore, RX ricevitore con OSSD1/OSSD2) |
| A1 | Arduino Mega 2560 Rev3 + Ethernet Shield 2 (W5500), su supporto DIN con screw-shield |
| U6 | scheda optoisolata PC817 8 canali 24→5 V — sensori |
| U7 | scheda optoisolata PC817 8 canali 24→5 V — ESTOP_OK, CURTAIN_OK, START, STOP (4 canali di riserva) |
| U8 | modulo relè 4 canali 5 V, ingressi optoisolati, **trigger ALTO** |
| U9 | convertitore DC/DC 24→5 V 1 A su DIN (alimenta solo le bobine di U8 — vedi note) |
| U11–U14 | driver CL57T per M1 X, M2 Z1, M3 Z2, M4 R |
| M1–M4 | NEMA23 closed-loop con encoder 1000 linee |
| B1–B8 | sensori induttivi M12 PNP NO 24 V, 3 fili |
| H1–H4 | colonna luminosa 24 V: verde, gialla, rossa, buzzer |
| XP1 | Harting Han-Modular 24B: moduli a,b Han EE 8 poli (fasi), c,d Han DD 12 poli (encoder), PE sul telaio |
| XP2 | Harting Han 10 E + PE (sensori) |
| JB1 | scatola di derivazione sul portale (distributore M12) per i sensori |
| BPE | barra di terra principale del quadro |

## Pinout Arduino Mega 2560 (da SPEC §2.1 — DEFINITIVO)

Riservati Ethernet Shield 2: **D4** (SD CS, tenere ALTO), **D10** (W5500 CS), **D50–D53** (SPI). Non usati.

| Pin | Funzione | Dir | Collegato a | Logica |
|---|---|---|---|---|
| D22 / D23 / D24 | X PUL / DIR / ENA | OUT | U11 PUL+ / DIR+ / ENA+ | ENA ALTO = driver disabilitato |
| D25 | X ALM | IN_PULLUP | U11 ALM+ | BASSO = allarme |
| D26 / D27 / D28 | Z1 PUL / DIR / ENA | OUT | U12 PUL+ / DIR+ / ENA+ | |
| D29 | Z1 ALM | IN_PULLUP | U12 ALM+ | BASSO = allarme |
| D30 / D31 / D32 | Z2 PUL / DIR / ENA | OUT | U13 PUL+ / DIR+ / ENA+ | |
| D33 | Z2 ALM | IN_PULLUP | U13 ALM+ | BASSO = allarme |
| D34 / D35 / D36 | R PUL / DIR / ENA | OUT | U14 PUL+ / DIR+ / ENA+ | |
| D37 | R ALM | IN_PULLUP | U14 ALM+ | BASSO = allarme |
| D38 | X_MIN (home) | IN_PULLUP | U6 OUT1 ← B1 | BASSO = attivo |
| D39 | X_MAX (extracorsa) | IN_PULLUP | U6 OUT2 ← B2 | BASSO = attivo |
| D40 | Z1_HOME (alto) | IN_PULLUP | U6 OUT3 ← B3 | BASSO = attivo |
| D41 | Z2_HOME (alto) | IN_PULLUP | U6 OUT4 ← B4 | BASSO = attivo |
| D42 | Z1_LOW (extracorsa basso) | IN_PULLUP | U6 OUT5 ← B5 | BASSO = attivo |
| D43 | Z2_LOW (extracorsa basso) | IN_PULLUP | U6 OUT6 ← B6 | BASSO = attivo |
| D44 | SEAT_A (portale in sede A1) | IN_PULLUP | U6 OUT7 ← B7 | BASSO = in sede |
| D45 | SEAT_B (portale in sede A2) | IN_PULLUP | U6 OUT8 ← B8 | BASSO = in sede |
| D48 | BTN_START | IN_PULLUP | U7 OUT3 ← S2 (NO) | BASSO = premuto |
| D49 | BTN_STOP | IN_PULLUP | U7 OUT4 ← S3 (NC) | ALTO = premuto / filo rotto |
| D2 | ESTOP_OK (INT) | IN_PULLUP | U7 OUT1 ← K1 43-44 | BASSO = catena OK, ALTO = emergenza |
| D3 | CURTAIN_OK (INT) | IN_PULLUP | U7 OUT2 ← K2+K3 11-14 | BASSO = barriera libera |
| D5 | lampada verde | OUT | U8 IN1 → H1 | ALTO = accesa |
| D6 | lampada gialla | OUT | U8 IN2 → H2 | ALTO = accesa |
| D7 | lampada rossa | OUT | U8 IN3 → H3 | ALTO = accesa |
| D8 | buzzer | OUT | U8 IN4 → H4 | ALTO = attivo |
| Vin / GND | alimentazione | — | PSU3 +12 V / −V (fili 701/702) | |
| 5V / GND | logica | — | X7:1 / X6:1 (fili 400/401) | |

Cablaggio CL57T a **catodo comune 5 V**: PUL+/DIR+/ENA+ ← pin Arduino, PUL−/DIR−/ENA−/ALM− ponticellati sul
driver e collegati alla GND logica (X6). ALM+ → pin Arduino con INPUT_PULLUP.

## Sezioni e tipi di cavo

| Circuito | Sezione | Cavo / colore |
|---|---|---|
| 230 V AC (rete, Q1, Q2, F1–F3, KM1, PSU) | 1,5 mm² | H07V-K: L marrone (o nero), N blu chiaro |
| PE | 2,5 mm² (1,5 per PSU1 FG e ponti PELV, 6 mm² treccia porta) | giallo-verde |
| 48 V DC PSU1 → X2 | 2,5 mm² | + rosso, 0 V nero |
| 48 V DC X2 → F11–F14 → driver | 1,5 mm² | + rosso, 0 V nero |
| 24 V DC alimentazione PSU2 → F4/F5/X3/X4 | 1,0 mm² | + blu scuro, 0 V blu/bianco |
| 24 V DC comandi e sicurezza | 0,5–0,75 mm² | + blu scuro, 0 V blu/bianco |
| Segnali logici 5 V (Arduino, driver, opto, relè) | 0,5 mm² | uscite viola, ingressi grigio, +5 V rosso, GND nero |
| Motori (W1, W3, W5, W7) | **4 × 1,0 mm² schermato**, per posa mobile | tipo Igus chainflex CF886/CF27 |
| Encoder (W2, W4, W6, W8) | 3 × 2 × 0,25 mm² **schermato a coppie**, per posa mobile | tipo chainflex CF11; coppie EA+/EA−, EB+/EB−, VCC/EGND |
| Sensori portale (W10, XP2 → JB1) | 12G0,5 per posa mobile | tipo chainflex CF5 |
| Sensori (W11–W18, JB1 → B1–B8) | 3 × 0,34 PUR M12 precablato | BN +24, BU 0V, BK segnale |
| PE portale (W9) | 1 × 2,5 mm² | giallo-verde, capocorda ad occhio sul telaio |
| Ethernet (W23) | Cat.6 S/FTP | passaparete RJ45 IP67 |

Tutti i conduttori numerati alle due estremità (numero filo della tabella), capicorda a puntale
crimpati su tutti i conduttori flessibili.

### Cavi esterni

| Cavo | Tratta | Tipo | Note |
|---|---|---|---|
| W0 | rete -> X0 | H07RN-F 3G1,5 | spina CEE 16 A 2P+T |
| W1/W3/W5/W7 | XP1 -> motori M1..M4 (fasi) | 4x1,0 schermato per posa mobile (tipo Igus chainflex CF886/CF27) | schermo a PE solo lato quadro |
| W2/W4/W6/W8 | XP1 -> encoder M1..M4 | 3x2x0,25 schermato a coppie per posa mobile (tipo chainflex CF11) | coppie: EA+/EA-, EB+/EB-, VCC/EGND |
| W9 | XP1:PE -> telaio portale | 1x2,5 giallo-verde (H07V-K o chainflex) | capocorda ad occhio su perno saldato |
| W10 | XP2 -> JB1 (scatola di derivazione portale) | 12G0,5 per posa mobile (tipo chainflex CF5) | 10 conduttori + PE + 1 riserva |
| W11..W18 | JB1 -> sensori B1..B8 | 3x0,34 PUR M12 (precablato) | BN +24, BU 0V, BK segnale |
| W20 | X3/X4 -> LC1-TX | secondo costruttore barriera (M12 4/5 poli) |  |
| W21 | X3/X4/K2/K3 -> LC1-RX | secondo costruttore barriera (M12 5/8 poli) | OSSD1/OSSD2 |
| W22 | U8/X4 -> colonna luminosa H1..H4 | 7G0,5 | 2 conduttori di riserva |
| W23 | Ethernet Shield -> switch VLAN IoT | Cat.6 S/FTP + passaparete RJ45 IP67 | IP 192.168.50.60 |

## Connettori verso il portale

Il portale si stacca aprendo **XP1** (motori + encoder) e **XP2** (sensori), custodie Harting a parete
sul fondo del quadro; lato portale spine volanti cablate sui cavi. Inserti maschio lato quadro solo se
non in tensione a connettore aperto: preferire **inserti femmina sul lato che resta alimentato**
(quadro) per entrambi.

### XP1 — Han-Modular 24B

| Contatto | Asse | Segnale | Colore anima motore | Filo interno | Cavo |
|---|---|---|---|---|---|
| a1 | X | M1 A+ | nero | 801 | W1 |
| a2 | X | M1 A- | verde | 802 | W1 |
| a3 | X | M1 B+ | rosso | 803 | W1 |
| a4 | X | M1 B- | blu | 804 | W1 |
| c1 | X | M1 enc EA+ | nero | 821 | W2 |
| c2 | X | M1 enc EA- | blu | 822 | W2 |
| c3 | X | M1 enc EB+ | giallo | 823 | W2 |
| c4 | X | M1 enc EB- | verde | 824 | W2 |
| c5 | X | M1 enc VCC | rosso | 825 | W2 |
| c6 | X | M1 enc EGND | bianco | 826 | W2 |
| a5 | Z1 | M2 A+ | nero | 805 | W3 |
| a6 | Z1 | M2 A- | verde | 806 | W3 |
| a7 | Z1 | M2 B+ | rosso | 807 | W3 |
| a8 | Z1 | M2 B- | blu | 808 | W3 |
| c7 | Z1 | M2 enc EA+ | nero | 827 | W4 |
| c8 | Z1 | M2 enc EA- | blu | 828 | W4 |
| c9 | Z1 | M2 enc EB+ | giallo | 829 | W4 |
| c10 | Z1 | M2 enc EB- | verde | 830 | W4 |
| c11 | Z1 | M2 enc VCC | rosso | 831 | W4 |
| c12 | Z1 | M2 enc EGND | bianco | 832 | W4 |
| b1 | Z2 | M3 A+ | nero | 809 | W5 |
| b2 | Z2 | M3 A- | verde | 810 | W5 |
| b3 | Z2 | M3 B+ | rosso | 811 | W5 |
| b4 | Z2 | M3 B- | blu | 812 | W5 |
| d1 | Z2 | M3 enc EA+ | nero | 833 | W6 |
| d2 | Z2 | M3 enc EA- | blu | 834 | W6 |
| d3 | Z2 | M3 enc EB+ | giallo | 835 | W6 |
| d4 | Z2 | M3 enc EB- | verde | 836 | W6 |
| d5 | Z2 | M3 enc VCC | rosso | 837 | W6 |
| d6 | Z2 | M3 enc EGND | bianco | 838 | W6 |
| b5 | R | M4 A+ | nero | 813 | W7 |
| b6 | R | M4 A- | verde | 814 | W7 |
| b7 | R | M4 B+ | rosso | 815 | W7 |
| b8 | R | M4 B- | blu | 816 | W7 |
| d7 | R | M4 enc EA+ | nero | 839 | W8 |
| d8 | R | M4 enc EA- | blu | 840 | W8 |
| d9 | R | M4 enc EB+ | giallo | 841 | W8 |
| d10 | R | M4 enc EB- | verde | 842 | W8 |
| d11 | R | M4 enc VCC | rosso | 843 | W8 |
| d12 | R | M4 enc EGND | bianco | 844 | W8 |

PE: telaio Han-Modular (contatto PE dedicato) → W9 → telaio portale. Schermi W1–W8: sulla custodia
EMC/pressacavo lato quadro e quindi a PE; **non collegati lato motore**.

### XP2 — Han 10 E

| Contatto | Segnale | Lato quadro | Lato portale (JB1) |
|---|---|---|---|
| 1 | +24 V sensori | X3:11 (filo 350) | BN di tutti i sensori |
| 2 | 0V24 sensori | X4:9 (filo 351) | BU di tutti i sensori |
| 3 | X_MIN | U6:IN1 (filo 352) → D38 | BK di B1 (longherone Y-, lato X- (home)) |
| 4 | X_MAX | U6:IN2 (filo 353) → D39 | BK di B2 (longherone Y-, lato X+ (extracorsa)) |
| 5 | Z1_HOME | U6:IN3 (filo 354) → D40 | BK di B3 (piastra Z1, finecorsa alto) |
| 6 | Z2_HOME | U6:IN4 (filo 355) → D41 | BK di B4 (piastra Z2, finecorsa alto) |
| 7 | Z1_LOW | U6:IN5 (filo 356) → D42 | BK di B5 (piastra Z1, extracorsa basso) |
| 8 | Z2_LOW | U6:IN6 (filo 357) → D43 | BK di B6 (piastra Z2, extracorsa basso) |
| 9 | SEAT_A | U6:IN7 (filo 358) → D44 | BK di B7 (piede A1 (portale in sede)) |
| 10 | SEAT_B | U6:IN8 (filo 359) → D45 | BK di B8 (piede A2 (portale in sede)) |
| PE | PE | BPE (PE6) | telaio JB1 |

## Tabella morsetti / fili

Numerazione: 1–17 230 V · PEx terra · 2xx 48 V · 3xx 24 V e sicurezza · 4xx driver · 5xx ingressi ·
6xx uscite · 7xx alimentazione Arduino · 8xx motori/encoder (interno quadro, dal driver all'inserto XP1).

| N. filo | Da | A | Segnale | Sezione [mm²] | Colore | Note |
|---|---|---|---|---|---|---|
| 1 | X0:L | Q1:1 | L 230 V | 1,5 | marrone | ingresso rete da W0 |
| 2 | X0:N | Q1:3 | N | 1,5 | blu chiaro |  |
| 3 | Q1:2 | Q2:1 | L | 1,5 | marrone |  |
| 4 | Q1:4 | Q2:N | N | 1,5 | blu chiaro |  |
| 5 | Q2:2 | X1:1 | L | 1,5 | marrone | ponticello X1:1-3 |
| 6 | Q2:N | X1:4 | N | 1,5 | blu chiaro | ponticello X1:4-6 |
| 7 | X1:1 | F1:1 | L PSU1 | 1,5 | marrone |  |
| 8 | X1:2 | F2:1 | L PSU2 | 1,5 | marrone |  |
| 9 | X1:3 | F3:1 | L PSU3 | 1,5 | marrone |  |
| 10 | F1:2 | KM1:1 | L PSU1 | 1,5 | marrone |  |
| 11 | X1:4 | KM1:3 | N PSU1 | 1,5 | blu chiaro |  |
| 12 | KM1:2 | PSU1:L | L PSU1 sotto sicurezza | 1,5 | marrone |  |
| 13 | KM1:4 | PSU1:N | N PSU1 sotto sicurezza | 1,5 | blu chiaro |  |
| 14 | F2:2 | PSU2:L | L PSU2 | 1,5 | marrone |  |
| 15 | X1:5 | PSU2:N | N PSU2 | 1,5 | blu chiaro |  |
| 16 | F3:2 | PSU3:L | L PSU3 | 1,5 | marrone |  |
| 17 | X1:6 | PSU3:N | N PSU3 | 1,5 | blu chiaro |  |
| PE1 | X0:PE | BPE | PE rete | 2,5 | giallo-verde |  |
| PE2 | BPE | PSU1:FG | PE | 1,5 | giallo-verde | PSU2/PSU3 HDR in classe II: senza FG |
| PE3 | BPE | piastra di fondo | PE | 2,5 | giallo-verde |  |
| PE4 | BPE | porta quadro | PE | 6 (treccia) | giallo-verde / treccia Cu |  |
| PE5 | BPE | XP1:PE | PE portale | 2,5 | giallo-verde | prosegue con W9 al telaio portale |
| PE6 | BPE | XP2:PE | PE | 1,5 | giallo-verde |  |
| PE7 | X2:5 | BPE | ponte 0V48-PE | 1,5 | giallo-verde | PELV, un solo punto, rimovibile per prova isolamento |
| PE8 | X4:1 | BPE | ponte 0V24-PE | 1,5 | giallo-verde | PELV, un solo punto, rimovibile per prova isolamento |
| PE9 | BPE | staffa schermi | PE schermi | 2,5 | giallo-verde | schermi cavi a terra solo lato quadro |
| 201 | PSU1:+V | X2:1 | +48 V | 2,5 | rosso | ponticello X2:1-4 |
| 202 | PSU1:-V | X2:5 | 0V48 | 2,5 | nero | ponticello X2:5-9 |
| 203 | X2:1 | F11:1 | +48 V driver X | 1,5 | rosso |  |
| 204 | X2:2 | F12:1 | +48 V driver Z1 | 1,5 | rosso |  |
| 205 | X2:3 | F13:1 | +48 V driver Z2 | 1,5 | rosso |  |
| 206 | X2:4 | F14:1 | +48 V driver R | 1,5 | rosso |  |
| 207 | F11:2 | U11:+Vdc | +48 V driver X | 1,5 | rosso | F11 fusibile 5 A ritardato 5x20 |
| 208 | F12:2 | U12:+Vdc | +48 V driver Z1 | 1,5 | rosso | F12 fusibile 5 A ritardato 5x20 |
| 209 | F13:2 | U13:+Vdc | +48 V driver Z2 | 1,5 | rosso | F13 fusibile 5 A ritardato 5x20 |
| 210 | F14:2 | U14:+Vdc | +48 V driver R | 1,5 | rosso | F14 fusibile 5 A ritardato 5x20 |
| 211 | X2:6 | U11:GND | 0V48 driver X | 1,5 | nero |  |
| 212 | X2:7 | U12:GND | 0V48 driver Z1 | 1,5 | nero |  |
| 213 | X2:8 | U13:GND | 0V48 driver Z2 | 1,5 | nero |  |
| 214 | X2:9 | U14:GND | 0V48 driver R | 1,5 | nero |  |
| 301 | PSU2:+V | F4:1 | +24 V | 1,0 | blu scuro |  |
| 302 | PSU2:+V | F5:1 | +24 V | 1,0 | blu scuro |  |
| 303 | PSU2:-V | X4:1 | 0V24 | 1,0 | blu/bianco | ponticello X4:1-12 |
| 304 | F4:2 | X3:1 | +24 V S (sicurezza) | 1,0 | blu scuro | ponticello X3:1-4 |
| 305 | F5:2 | X3:5 | +24 V I/O | 1,0 | blu scuro | ponticello X3:5-13 |
| 310 | X3:2 | K1:A1 | +24 V S alim. K1 | 0,75 | blu scuro |  |
| 311 | X4:2 | K1:A2 | 0V24 K1 | 0,75 | blu/bianco |  |
| 312 | K1:S11 | S0:11 | emergenza canale 1 | 0,5 | blu scuro | verso porta |
| 313 | S0:12 | K1:S12 | emergenza canale 1 | 0,5 | blu scuro |  |
| 314 | K1:S21 | S0:21 | emergenza canale 2 | 0,5 | blu scuro |  |
| 315 | S0:22 | K1:S22 | emergenza canale 2 | 0,5 | blu scuro |  |
| 316 | K1:S33 | S1:13 | reset | 0,5 | blu scuro |  |
| 317 | S1:14 | KM1:21 | reset + retroazione | 0,5 | blu scuro |  |
| 318 | KM1:22 | K1:S34 | retroazione KM1 (NC) | 0,5 | blu scuro |  |
| 319 | X3:3 | K1:13 | +24 V S | 0,75 | blu scuro |  |
| 320 | K1:14 | K1:23 | serie contatti sicuri | 0,75 | blu scuro |  |
| 321 | K1:24 | KM1:A1 | comando bobina KM1 | 0,75 | blu scuro | soppressore su bobina |
| 322 | KM1:A2 | X4:3 | 0V24 | 0,75 | blu/bianco |  |
| 323 | X3:4 | K1:43 | +24 V S | 0,5 | blu scuro |  |
| 324 | K1:44 | U7:IN1 | ESTOP_OK (24 V = OK) | 0,5 | blu scuro | -> D2 |
| 330 | X3:6 | LC1-TX:+24 | +24 V emettitore | 0,5 | blu scuro | via W20 |
| 331 | X4:4 | LC1-TX:0V | 0V24 | 0,5 | blu/bianco | via W20 |
| 332 | X3:7 | LC1-RX:+24 | +24 V ricevitore | 0,5 | blu scuro | via W21 |
| 333 | X4:5 | LC1-RX:0V | 0V24 | 0,5 | blu/bianco | via W21 |
| 334 | LC1-RX:OSSD1 | K2:A1 | OSSD1 | 0,5 | blu scuro | via W21 |
| 335 | K2:A2 | X4:6 | 0V24 | 0,5 | blu/bianco |  |
| 336 | LC1-RX:OSSD2 | K3:A1 | OSSD2 | 0,5 | blu scuro | via W21 |
| 337 | K3:A2 | X4:7 | 0V24 | 0,5 | blu/bianco |  |
| 338 | X3:8 | K2:11 | +24 V I/O | 0,5 | blu scuro |  |
| 339 | K2:14 | K3:11 | serie K2-K3 | 0,5 | blu scuro |  |
| 340 | K3:14 | U7:IN2 | CURTAIN_OK (24 V = libera) | 0,5 | blu scuro | -> D3 |
| 341 | X3:9 | S2:13 | +24 V I/O | 0,5 | blu scuro |  |
| 342 | S2:14 | U7:IN3 | BTN_START | 0,5 | blu scuro | -> D48 |
| 343 | X3:10 | S3:11 | +24 V I/O | 0,5 | blu scuro |  |
| 344 | S3:12 | U7:IN4 | BTN_STOP (NC) | 0,5 | blu scuro | -> D49 |
| 345 | X4:8 | U7:COM | 0V24 ingressi U7 | 0,5 | blu/bianco |  |
| 350 | X3:11 | XP2:1 | +24 V sensori | 0,75 | blu scuro |  |
| 351 | X4:9 | XP2:2 | 0V24 sensori | 0,75 | blu/bianco |  |
| 352 | XP2:3 | U6:IN1 | X_MIN (B1) | 0,5 | blu scuro | -> D38 |
| 353 | XP2:4 | U6:IN2 | X_MAX (B2) | 0,5 | blu scuro | -> D39 |
| 354 | XP2:5 | U6:IN3 | Z1_HOME (B3) | 0,5 | blu scuro | -> D40 |
| 355 | XP2:6 | U6:IN4 | Z2_HOME (B4) | 0,5 | blu scuro | -> D41 |
| 356 | XP2:7 | U6:IN5 | Z1_LOW (B5) | 0,5 | blu scuro | -> D42 |
| 357 | XP2:8 | U6:IN6 | Z2_LOW (B6) | 0,5 | blu scuro | -> D43 |
| 358 | XP2:9 | U6:IN7 | SEAT_A (B7) | 0,5 | blu scuro | -> D44 |
| 359 | XP2:10 | U6:IN8 | SEAT_B (B8) | 0,5 | blu scuro | -> D45 |
| 360 | X4:10 | U6:COM | 0V24 ingressi U6 | 0,5 | blu/bianco |  |
| 370 | X3:12 | U8:COM1 | +24 V colonna | 0,5 | blu scuro | ponticelli COM1-COM4 |
| 371 | U8:NO1 | H1 | lampada VERDE | 0,5 | blu scuro | via W22 |
| 372 | U8:NO2 | H2 | lampada GIALLA | 0,5 | blu scuro | via W22 |
| 373 | U8:NO3 | H3 | lampada ROSSA | 0,5 | blu scuro | via W22 |
| 374 | U8:NO4 | H4 | BUZZER | 0,5 | blu scuro | via W22 |
| 375 | X4:11 | H comune | 0V colonna luminosa | 0,5 | blu/bianco | via W22 |
| 380 | X3:13 | U9:+Vin | +24 V DC/DC | 0,5 | blu scuro |  |
| 381 | X4:12 | U9:-Vin | 0V24 DC/DC | 0,5 | blu/bianco |  |
| 382 | U9:+Vout | U8:JD-VCC | +5 V bobine rele | 0,5 | rosso | togliere ponticello JD-VCC/VCC |
| 383 | U9:-Vout | U8:GND(JD) | 0 V bobine rele | 0,5 | nero |  |
| 400 | A1:5V | X7:1 | +5 V logica | 0,5 | rosso | ponticello X7:1-4 |
| 401 | A1:GND | X6:1 | GND logica | 0,5 | nero | ponticello X6:1-8 |
| 411 | A1:D22 | U11:PUL+ | X_PUL | 0,5 | viola |  |
| 412 | A1:D23 | U11:DIR+ | X_DIR | 0,5 | viola |  |
| 413 | A1:D24 | U11:ENA+ | X_ENA (ALTO=disabilitato) | 0,5 | viola |  |
| 414 | U11:ALM+ | A1:D25 | X_ALM (BASSO=allarme) | 0,5 | grigio | INPUT_PULLUP |
| 415 | X6:2 | U11:PUL- | GND logica X | 0,5 | nero | ponticelli PUL-/DIR-/ENA-/ALM- sul driver |
| 421 | A1:D26 | U12:PUL+ | Z1_PUL | 0,5 | viola |  |
| 422 | A1:D27 | U12:DIR+ | Z1_DIR | 0,5 | viola |  |
| 423 | A1:D28 | U12:ENA+ | Z1_ENA (ALTO=disabilitato) | 0,5 | viola |  |
| 424 | U12:ALM+ | A1:D29 | Z1_ALM (BASSO=allarme) | 0,5 | grigio | INPUT_PULLUP |
| 425 | X6:3 | U12:PUL- | GND logica Z1 | 0,5 | nero | ponticelli PUL-/DIR-/ENA-/ALM- sul driver |
| 431 | A1:D30 | U13:PUL+ | Z2_PUL | 0,5 | viola |  |
| 432 | A1:D31 | U13:DIR+ | Z2_DIR | 0,5 | viola |  |
| 433 | A1:D32 | U13:ENA+ | Z2_ENA (ALTO=disabilitato) | 0,5 | viola |  |
| 434 | U13:ALM+ | A1:D33 | Z2_ALM (BASSO=allarme) | 0,5 | grigio | INPUT_PULLUP |
| 435 | X6:4 | U13:PUL- | GND logica Z2 | 0,5 | nero | ponticelli PUL-/DIR-/ENA-/ALM- sul driver |
| 441 | A1:D34 | U14:PUL+ | R_PUL | 0,5 | viola |  |
| 442 | A1:D35 | U14:DIR+ | R_DIR | 0,5 | viola |  |
| 443 | A1:D36 | U14:ENA+ | R_ENA (ALTO=disabilitato) | 0,5 | viola |  |
| 444 | U14:ALM+ | A1:D37 | R_ALM (BASSO=allarme) | 0,5 | grigio | INPUT_PULLUP |
| 445 | X6:5 | U14:PUL- | GND logica R | 0,5 | nero | ponticelli PUL-/DIR-/ENA-/ALM- sul driver |
| 501 | U6:OUT1 | A1:D38 | X_MIN | 0,5 | grigio | BASSO = attivo |
| 502 | U6:OUT2 | A1:D39 | X_MAX | 0,5 | grigio | BASSO = attivo |
| 503 | U6:OUT3 | A1:D40 | Z1_HOME | 0,5 | grigio | BASSO = attivo |
| 504 | U6:OUT4 | A1:D41 | Z2_HOME | 0,5 | grigio | BASSO = attivo |
| 505 | U6:OUT5 | A1:D42 | Z1_LOW | 0,5 | grigio | BASSO = attivo |
| 506 | U6:OUT6 | A1:D43 | Z2_LOW | 0,5 | grigio | BASSO = attivo |
| 507 | U6:OUT7 | A1:D44 | SEAT_A | 0,5 | grigio | BASSO = attivo |
| 508 | U6:OUT8 | A1:D45 | SEAT_B | 0,5 | grigio | BASSO = attivo |
| 509 | X7:2 | U6:VCC | +5 V | 0,5 | rosso |  |
| 510 | X6:6 | U6:GND | GND logica | 0,5 | nero |  |
| 511 | U7:OUT1 | A1:D2 | ESTOP_OK | 0,5 | grigio |  |
| 512 | U7:OUT2 | A1:D3 | CURTAIN_OK | 0,5 | grigio |  |
| 513 | U7:OUT3 | A1:D48 | BTN_START | 0,5 | grigio |  |
| 514 | U7:OUT4 | A1:D49 | BTN_STOP | 0,5 | grigio |  |
| 515 | X7:3 | U7:VCC | +5 V | 0,5 | rosso |  |
| 516 | X6:7 | U7:GND | GND logica | 0,5 | nero |  |
| 601 | A1:D5 | U8:IN1 | H1 lampada VERDE | 0,5 | viola | attivo ALTO |
| 602 | A1:D6 | U8:IN2 | H2 lampada GIALLA | 0,5 | viola | attivo ALTO |
| 603 | A1:D7 | U8:IN3 | H3 lampada ROSSA | 0,5 | viola | attivo ALTO |
| 604 | A1:D8 | U8:IN4 | H4 BUZZER | 0,5 | viola | attivo ALTO |
| 605 | X7:4 | U8:VCC | +5 V ingressi rele | 0,5 | rosso |  |
| 606 | X6:8 | U8:GND | GND logica | 0,5 | nero |  |
| 701 | PSU3:+V | A1:Vin | +12 V | 0,75 | rosso | jack DC 5,5x2,1 o pin Vin |
| 702 | PSU3:-V | A1:GND | 0 V 12 V | 0,75 | nero |  |
| 801 | U11:A+ | XP1:a1 | M1 fase A+ | 1,0 | nero (num.) | prosegue W1 (nero) |
| 802 | U11:A- | XP1:a2 | M1 fase A- | 1,0 | nero (num.) | prosegue W1 (verde) |
| 803 | U11:B+ | XP1:a3 | M1 fase B+ | 1,0 | nero (num.) | prosegue W1 (rosso) |
| 804 | U11:B- | XP1:a4 | M1 fase B- | 1,0 | nero (num.) | prosegue W1 (blu) |
| 805 | U12:A+ | XP1:a5 | M2 fase A+ | 1,0 | nero (num.) | prosegue W3 (nero) |
| 806 | U12:A- | XP1:a6 | M2 fase A- | 1,0 | nero (num.) | prosegue W3 (verde) |
| 807 | U12:B+ | XP1:a7 | M2 fase B+ | 1,0 | nero (num.) | prosegue W3 (rosso) |
| 808 | U12:B- | XP1:a8 | M2 fase B- | 1,0 | nero (num.) | prosegue W3 (blu) |
| 809 | U13:A+ | XP1:b1 | M3 fase A+ | 1,0 | nero (num.) | prosegue W5 (nero) |
| 810 | U13:A- | XP1:b2 | M3 fase A- | 1,0 | nero (num.) | prosegue W5 (verde) |
| 811 | U13:B+ | XP1:b3 | M3 fase B+ | 1,0 | nero (num.) | prosegue W5 (rosso) |
| 812 | U13:B- | XP1:b4 | M3 fase B- | 1,0 | nero (num.) | prosegue W5 (blu) |
| 813 | U14:A+ | XP1:b5 | M4 fase A+ | 1,0 | nero (num.) | prosegue W7 (nero) |
| 814 | U14:A- | XP1:b6 | M4 fase A- | 1,0 | nero (num.) | prosegue W7 (verde) |
| 815 | U14:B+ | XP1:b7 | M4 fase B+ | 1,0 | nero (num.) | prosegue W7 (rosso) |
| 816 | U14:B- | XP1:b8 | M4 fase B- | 1,0 | nero (num.) | prosegue W7 (blu) |
| 821 | U11:EA+ | XP1:c1 | M1 encoder EA+ | 0,25 schermato | come cavo | prosegue W2 (nero) |
| 822 | U11:EA- | XP1:c2 | M1 encoder EA- | 0,25 schermato | come cavo | prosegue W2 (blu) |
| 823 | U11:EB+ | XP1:c3 | M1 encoder EB+ | 0,25 schermato | come cavo | prosegue W2 (giallo) |
| 824 | U11:EB- | XP1:c4 | M1 encoder EB- | 0,25 schermato | come cavo | prosegue W2 (verde) |
| 825 | U11:VCC | XP1:c5 | M1 encoder VCC | 0,25 schermato | come cavo | prosegue W2 (rosso) |
| 826 | U11:EGND | XP1:c6 | M1 encoder EGND | 0,25 schermato | come cavo | prosegue W2 (bianco) |
| 827 | U12:EA+ | XP1:c7 | M2 encoder EA+ | 0,25 schermato | come cavo | prosegue W4 (nero) |
| 828 | U12:EA- | XP1:c8 | M2 encoder EA- | 0,25 schermato | come cavo | prosegue W4 (blu) |
| 829 | U12:EB+ | XP1:c9 | M2 encoder EB+ | 0,25 schermato | come cavo | prosegue W4 (giallo) |
| 830 | U12:EB- | XP1:c10 | M2 encoder EB- | 0,25 schermato | come cavo | prosegue W4 (verde) |
| 831 | U12:VCC | XP1:c11 | M2 encoder VCC | 0,25 schermato | come cavo | prosegue W4 (rosso) |
| 832 | U12:EGND | XP1:c12 | M2 encoder EGND | 0,25 schermato | come cavo | prosegue W4 (bianco) |
| 833 | U13:EA+ | XP1:d1 | M3 encoder EA+ | 0,25 schermato | come cavo | prosegue W6 (nero) |
| 834 | U13:EA- | XP1:d2 | M3 encoder EA- | 0,25 schermato | come cavo | prosegue W6 (blu) |
| 835 | U13:EB+ | XP1:d3 | M3 encoder EB+ | 0,25 schermato | come cavo | prosegue W6 (giallo) |
| 836 | U13:EB- | XP1:d4 | M3 encoder EB- | 0,25 schermato | come cavo | prosegue W6 (verde) |
| 837 | U13:VCC | XP1:d5 | M3 encoder VCC | 0,25 schermato | come cavo | prosegue W6 (rosso) |
| 838 | U13:EGND | XP1:d6 | M3 encoder EGND | 0,25 schermato | come cavo | prosegue W6 (bianco) |
| 839 | U14:EA+ | XP1:d7 | M4 encoder EA+ | 0,25 schermato | come cavo | prosegue W8 (nero) |
| 840 | U14:EA- | XP1:d8 | M4 encoder EA- | 0,25 schermato | come cavo | prosegue W8 (blu) |
| 841 | U14:EB+ | XP1:d9 | M4 encoder EB+ | 0,25 schermato | come cavo | prosegue W8 (giallo) |
| 842 | U14:EB- | XP1:d10 | M4 encoder EB- | 0,25 schermato | come cavo | prosegue W8 (verde) |
| 843 | U14:VCC | XP1:d11 | M4 encoder VCC | 0,25 schermato | come cavo | prosegue W8 (rosso) |
| 844 | U14:EGND | XP1:d12 | M4 encoder EGND | 0,25 schermato | come cavo | prosegue W8 (bianco) |

## Regole di posa

1. **Separazione**: cavi motore (W1/W3/W5/W7) e 230 V in canalina separata da segnali 5 V, encoder,
   sensori ed Ethernet; distanza ≥ 100 mm nei percorsi paralleli, incroci a 90°. Nel quadro la canalina
   centrale separa la zona potenza (riga alta) dalla logica (parete laterale).
2. **Schermi a terra lato quadro**: schermo dei cavi motore ed encoder collegato a 360° (pressacavo EMC
   o custodia Han EMC / staffa con cavallotti) alla barra PE del quadro; lato motore schermo isolato e
   rifilato. Tratti non schermati il più corti possibile (< 50 mm).
3. **Catena portacavi**: solo cavi per **posa mobile** (tipo Igus chainflex), raggio di curvatura minimo
   secondo il costruttore (tipicamente ≥ 7,5–10 × diametro), riempimento ≤ 60–70 %, cavi affiancati non
   sovrapposti, separatori tra cavi motore e segnali, fissaggio con fascette solo ai terminali della
   catena (punto fisso e punto mobile), mai lungo il tratto in movimento.
4. **Contatto alimentare**: sul portale, scatole e pressacavi in inox o PA alimentare IP67/IP69K, cavi PUR
   resistenti ai detergenti; nessun cavo sopra la zona dell'impasto.
5. **Coppie intrecciate**: PUL+/PUL−, DIR+/DIR− verso i driver preferibilmente in coppia (o percorso
   affiancato), lunghezza minima.
6. **PE**: un solo punto di collegamento 0V48–PE (X2:5) e 0V24–PE (X4:1); ponti rimovibili per la prova
   di isolamento. GND logica Arduino non collegata a PE (separata dagli optoisolatori).
7. Bobina KM1 con soppressore (diodo o varistore); relè K2/K3 con LED/diodo integrato.

## Impostazioni driver CL57T (DIP / microstep)

| Driver | Asse | Impulsi/giro | Risultato meccanico (SPEC §1) |
|---|---|---|---|
| U11 | X (M1) | **1600** | 16 step/mm (puleggia 100 mm/giro) |
| U12 | Z1 (M2) | **800** | 200 step/mm (TR16×4) |
| U13 | Z2 (M3) | **800** | 200 step/mm (TR16×4) |
| U14 | R (M4) | **800** | 5,093 step/mm di superficie rullo |

**Verificare la tabella DIP sul manuale del driver specifico acquistato**: la posizione degli switch
SW1–SW4 (impulsi/giro), la direzione, il fronte attivo dell'impulso e la logica di ENA/ALM cambiano tra
versioni e cloni del CL57T. Corrente: i driver closed-loop la regolano in automatico; impostare se
previsto la corrente nominale del motore. Verificare anche che gli ingressi accettino **5 V** (alcune
versioni hanno un selettore 5/24 V) e che l'**uscita ALM** sia configurata "attiva = transistor ON"
(pin BASSO in allarme, come da SPEC). Logica ENA: la SPEC prevede pin ALTO = disabilitato
(`ENA_ACTIVE_LEVEL` in `firmware/manipmasta/config.h`).

## Procedura di verifica prima dell'accensione

Eseguire a quadro **scollegato dalla rete**, motori scollegati (XP1 aperto), con multimetro e
misuratore di isolamento. Annotare gli esiti.

1. **Ispezione visiva**: serraggio morsetti, puntali, numerazione fili, assenza di trefoli liberi,
   ponticelli X1, X2, X3, X4, X6, X7 come da tabella; fusibili del calibro corretto (F11–F14 = 5 A T).
2. **Continuità PE** (< 0,1 Ω tipico, metodo CEI EN 60204-1 §18.2): BPE ↔ X0:PE, piastra, porta, PSU1 FG,
   XP1 PE ↔ telaio portale (con XP1 chiuso), carcasse motori, XP2 PE.
3. **Isolamento** (CEI EN 60204-1 §18.3): 500 V DC tra L+N uniti e PE con Q1 chiuso, PSU **scollegate**
   (o morsetti di ingresso PSU aperti) e KM1 forzato chiuso solo per la misura → ≥ 1 MΩ. Circuiti PELV:
   aprire i ponti PE7 e PE8 e misurare a tensione ridotta (es. 250 V) solo se i componenti elettronici
   sono scollegati; poi **richiudere i ponti**.
4. **Assenza di corti**: tra +48 V e 0V48 a valle di ogni F1x, tra +24 V e 0V24, tra +5 V e GND logica.
5. **Prima alimentazione senza carichi**: driver, Arduino, U6/U7/U8 scollegati o fusibili F11–F14 e F4/F5
   tolti. Q1+Q2 ON: verificare 230 V a PSU2/PSU3, 24,0 V tra X3 e X4, 12 V al jack Arduino.
   **PSU1 deve restare spenta** (KM1 aperto).
6. **Polarità**: con multimetro su ogni alimentazione prima di collegare i carichi (+48 V sul +Vdc di
   ogni driver, +24 V su BN dei sensori, +12 V centrale positivo sul jack Arduino).
7. **Catena di sicurezza**: inserire F4. S0 rilasciato → premere S1 → KM1 si chiude, PSU1 accesa,
   48 V ai driver. Premere S0 → KM1 apre. Con KM1 forzato meccanicamente (o simulando il contatto
   21-22 aperto) il reset non deve essere possibile. Provare entrambi i canali (staccare un filo per
   volta: 312 e 314) → K1 non deve riarmarsi.
8. **Test ingressi uno a uno** con firmware caricato, collegati via USB-Serial 115200 o MQTT, comando
   **`STATUS`** dopo ogni azione:
   - avvicinare un target metallico a B1…B8 uno per volta → il campo corrispondente in `in` passa a 1
     e il LED della scheda U6 si accende; tutti gli altri restano invariati;
   - premere S0 → `estop` cambia e `st` = `ESTOP`; riarmare con S1;
   - interrompere la barriera → `curt` cambia; premere S2/S3 e verificare la reazione del firmware;
   - verificare i livelli sui pin con un tester (BASSO ≈ 0,2 V = attivo, ALTO ≈ 5 V = non attivo).
   Nota: il JSON di `STATUS` previsto in SPEC §3 non riporta tutti gli ingressi (vedi sotto): per Z1_LOW,
   Z2_LOW, SEAT_A/SEAT_B separati, START, STOP e ALM verificare con il LED della scheda opto e il tester
   sul pin, o tramite eventuale comando diagnostico del firmware.
9. **Uscite**: forzare le lampade (stato `READY`/`ALARM`) → H1/H2/H3/H4 secondo D5–D8.
10. **Driver**: `ENABLE 1` a motori scollegati (XP1 aperto) → nessun allarme; poi XP1 chiuso, verso di
    rotazione con `JOG` a bassa velocità, finecorsa X_MIN/Z_HOME attivati a mano prima di `HOME`.
11. Verifica finale e documentazione a cura dell'elettricista qualificato (prove CEI EN 60204-1 §18,
    dichiarazione di conformità dell'equipaggiamento).

## Note di progetto e punti aperti

- **Barriera LC1**: come da SPEC agisce solo tramite firmware (D3). Per una vera funzione di sicurezza le
  OSSD devono agire sul circuito di potenza (secondo modulo di sicurezza o K1 con ingressi OSSD → KM1).
- **Categoria 3 con un solo contattore**: per PL d serve ridondanza in uscita (KM1 + KM2 in serie, contatti
  a specchio in serie nel loop di retroazione S33–S34).
- **ENA all'accensione**: i pin Arduino sono in alta impedenza durante il reset/boot → ENA non pilotato →
  CL57T **abilitato** finché il firmware non porta ENA ALTO. Il rischio è limitato perché senza impulsi il
  motore non si muove e KM1 richiede comunque il reset manuale, ma valutare una resistenza di pull-up
  (es. 1 kΩ verso +5 V su ENA+) se si vuole il driver disabilitato a MCU ferma.
- **Corrente uscite Arduino**: 12 ingressi opto dei driver da ~7–15 mA; pin 22–33 (PORTA + PC4–PC7) nello
  stesso gruppo di alimentazione del Mega (limite 100 mA): non portare ENA ALTO e impulsi a corrente piena
  su tutti i canali contemporaneamente, o usare un buffer (es. 74HCT244/ULN) se i driver assorbono di più.
- **Modulo relè U8**: 4 bobine 5 V (~70 mA cad.) dal regolatore dell'Arduino alimentato a 12 V lo
  surriscaldano → bobine da U9 (DC/DC 24→5 V) con ponticello JD-VCC rimosso, oppure modulo relè con
  bobine a 24 V. Il modulo deve essere a **trigger ALTO** (molti moduli economici sono a trigger basso).
- **Cassetta 400×300×200**: occupazione stimata ~95 % e dissipazione interna 40–70 W (PSU1 + driver):
  valutare 500×400×250 o ventilazione filtrata IP54 compatibile con la pulizia del laboratorio.
