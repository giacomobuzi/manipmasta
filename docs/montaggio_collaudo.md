# Montaggio, messa in servizio e uso

## 1. Ancoraggi
1. Tracciare i centri (±930, ±340) dal centro del piano (o i valori rigenerati da `cad/params.json`).
2. Forare il piano per le 4 viti M8 di ogni ancoraggio, contropiastra CTP-01 sotto. Non serrare a fondo.
3. Posare il portale (anche solo il telaio) con i perni negli ancoraggi, verificare che scenda senza forzare, poi serrare gli ancoraggi.
4. A1 è il riferimento (foro tondo), A2 ha l'asola, A3/A4 sono solo appoggio: è voluto, evita impuntamenti.

## 2. Meccanica del portale
1. Guide SBR20 sui longheroni: allineare la prima con riga/comparatore, la seconda parallela alla prima (0,1 mm su tutta la corsa).
2. Carrelli con pattini, traversa ponte PON-01: il ponte deve scorrere a mano senza punti duri.
3. Albero di sincronismo con pulegge, cinghie aperte bloccate ai carrelli: tensionare uguale sui due lati (stessa freccia).
4. Moduli Z: piastre Z, alberi Ø16 su SK16, slitte con SC16UU, viti TR16 con BK12/BF12, motori Z su distanziali.
5. Rullo nei supporti SUCF204, puleggia 40T, motore R e cinghia chiusa; tensionare con le asole della slitta Z1.
6. Raschietto in appoggio leggero sul rullo.

## 3. Elettrica
Secondo `wiring/README.md` (verifiche a vuoto prima di dare tensione, test ingressi uno a uno).
Impostare i DIP dei CL57T: X 1600 impulsi/giro, Z1/Z2/R 800 impulsi/giro.

## 4. Firmware e rete
1. Caricare il firmware (`firmware/README.md`), da seriale 115200: `SET ip …`, `SET mqtt_host …`, `SET mqtt_pass …`, `SAVE`, `REBOOT`.
2. Arduino su VLAN IoT; broker MQTT sulla VM (`server/README.md`).

## 5. Prima messa in servizio (motori a vuoto, senza impasto)
1. `ENABLE 1`, `JOG X 10` / `JOG X -10`: verificare il verso (se invertito: `SET dir_inv …`).
2. `JOG G -5`: il rullo deve **scendere**; Z1 e Z2 nello stesso verso.
3. `HOME`: Z sale ai finecorsa alti (si livella da solo), poi X va a X_MIN.
4. Calibrazione luce: portare il rullo a gap nominale 10 (`GAP 10`), misurare con spessimetro sotto il rullo ai due lati.
   Se si leggono 10,6 mm: `SET z_home_gap` = valore attuale + 0,6, `SAVE`, `HOME`. Se i due lati differiscono, regolare la camma/posizione del finecorsa del lato alto.
5. Verificare step/mm X: `MOVE X 0`, poi `MOVE X 500` e misurare (16 step/mm teorici).
6. Provare emergenza, barriera, STOP, sfilamento portale (SEAT): ogni ingresso deve fermare la macchina.

## 6. Primo ciclo con impasto
Ricetta prudente: `RUN cx=0 s0=150 s1=250 g0=40 g1=8 dg=3 f=40 n=2 od=2`.
Spolverare di farina piano e rullo. Aumentare velocità e ridurre `dg` solo dopo aver visto come lavora l'impasto.
Se l'impasto si attacca o "striscia": aumentare `od` (overdrive) di 1–2 % o ridurlo se tende a spingere avanti la sfoglia.

## 7. Pulizia
Macchina ferma e disabilitata (`ENABLE 0`), togliere i perni a sfere, sollevare il portale in due con le maniglie e appoggiarlo
sul suo cavalletto. Rullo e raschietto si puliscono con detergente alimentare; le guide si ingrassano con grasso H1.
