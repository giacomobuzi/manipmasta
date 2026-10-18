# ManipMasta — software lato VM

Broker MQTT (Mosquitto) + server FastAPI con interfaccia web per comandare la sfogliatrice
ManipMasta (Arduino Mega 2560 + Ethernet). Riferimento vincolante: [`docs/SPEC.md`](../docs/SPEC.md) §3–§5.

```
 Telefono / app Android ──HTTPS──► Nginx Proxy Manager ──HTTP──► VM :8080  manipmasta-server (FastAPI)
                                                                     │  MQTT (utente manipmasta-server)
 Arduino Mega (VLAN IoT 192.168.50.60) ──MQTT 1883──────────────► VM :1883  mosquitto
```

| Percorso | Contenuto |
|---|---|
| `app/` | server FastAPI: `main.py` (API, WebSocket, UI), `bridge.py` (MQTT paho v2, stato, storico), `protocol.py` (validazione comandi, riga RUN, stime), `db.py` (SQLite) |
| `app/static/` | UI web mobile-first (HTML/CSS/JS senza dipendenze esterne), PWA |
| `simulator.py` | simulatore dell'Arduino su MQTT |
| `mosquitto/config/` | `mosquitto.conf`, `acl` (il file `passwd` lo crea lo script) |
| `scripts/create_mqtt_users.sh` | crea gli utenti MQTT da `.env` |
| `tests/` | pytest: protocollo, API con MQTT finto, prova end-to-end con Mosquitto reale + simulatore |

## 1. VM su Proxmox

Consigliato: **Debian 12** (va bene anche Debian 13 o Ubuntu 24.04).

| Voce | Valore |
|---|---|
| vCPU | 2 (tipo `host`) |
| RAM | 2 GB |
| Disco | 16 GB (VirtIO SCSI, `discard=on`) |
| Rete | 2 NIC VirtIO: `net0` sulla LAN servizi (dove sta Nginx Proxy Manager), `net1` sulla **VLAN IoT** (tag VLAN, es. 50) |
| Opzioni | QEMU guest agent attivo, avvio automatico |

Indirizzi suggeriti, coerenti con i default dell'Arduino (SPEC §2.2): VM sulla VLAN IoT `192.168.50.10`
(= `mqtt_host`), Arduino `192.168.50.60`.

In alternativa a due NIC: una sola NIC sulla LAN e regole firewall (OPNsense) che permettano
**solo** `192.168.50.60 → VM:1883/tcp` dalla VLAN IoT; nessun altro traffico IoT → LAN.

Creazione rapida da shell del nodo (adattare ID, storage e bridge):

```bash
qm create 160 --name manipmasta --memory 2048 --cores 2 --cpu host \
  --net0 virtio,bridge=vmbr0 --net1 virtio,bridge=vmbr0,tag=50 \
  --scsihw virtio-scsi-single --scsi0 local-zfs:16,discard=on \
  --ide2 local:iso/debian-12-netinst.iso,media=cdrom --boot order='scsi0;ide2' \
  --agent enabled=1 --onboot 1 --ostype l26
```

Durante l'installazione Debian: solo "SSH server" e "utilità di sistema standard".
Poi IP statici in `/etc/network/interfaces` (la NIC IoT **senza gateway**):

```
auto ens19
iface ens19 inet static
    address 192.168.50.10/24
```

## 2. Docker

```bash
sudo apt update && sudo apt install -y ca-certificates curl git qemu-guest-agent
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
 | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER   # poi rientrare
```

## 3. Configurazione e avvio

```bash
git clone <repo> manipmasta && cd manipmasta/server
cp .env.example .env
sed -i "s/^API_TOKEN=.*/API_TOKEN=$(openssl rand -hex 32)/" .env
nano .env                       # MQTT_BIND = IP della VM sulla VLAN IoT, eventuale HTTP_BIND
sudo ./scripts/create_mqtt_users.sh
docker compose up -d --build
docker compose logs -f app
```

Lo script legge `.env`, genera le password mancanti (`MQTT_PASS` per il server, `MQTT_DEVICE_PASS`
per l'Arduino), crea `mosquitto/config/passwd` e imposta i permessi per l'utente del container
(uid 1883). Va rieseguito, seguito da `docker compose restart mosquitto`, ogni volta che si cambia
una password.

Utenti MQTT e permessi (`mosquitto/config/acl`):

| Utente | Uso | Scrive | Legge |
|---|---|---|---|
| `manipmasta-server` | server FastAPI | `cmd` | `state`, `event`, `resp`, `online` |
| `manipmasta` | Arduino (e simulatore) | `resp`, `state`, `event`, `online` | `cmd`, `sim` |
| `manipmasta-tools` | diagnostica (facoltativo, `MQTT_TOOLS_PASS`) | `sim` | tutto |

Sull'Arduino, da seriale USB (115200): `SET mqtt_host 192.168.50.10`, `SET mqtt_user manipmasta`,
`SET mqtt_pass <MQTT_DEVICE_PASS>`, `SAVE`.

Verifica: `curl http://<vm>:8080/api/health` → `{"status":"ok","mqtt":true,"online":...}`.

### Simulatore (senza hardware)

```bash
docker compose --profile sim up -d       # avvia anche il simulatore (SIM_SPEED in .env)
docker compose stop simulator            # prima di collegare l'Arduino vero!
```

Il simulatore usa le credenziali dell'Arduino: **non tenerlo acceso insieme alla macchina reale**.
Guasti simulati (utente `manipmasta-tools`):

```bash
mosquitto_pub -h 192.168.50.10 -u manipmasta-tools -P <pw> -t manipmasta/sim -m "ESTOP 1"   # poi "ESTOP 0" e RESET
#   CURTAIN 1|0 · SEAT 0|1 · ALM X|Z1|Z2|R
```

Fuori da Docker: `python simulator.py --host 192.168.50.10 --user manipmasta --password <pw> --speed 10 -v`.

## 4. Nginx Proxy Manager

*Hosts → Proxy Hosts → Add Proxy Host*

| Scheda | Impostazione |
|---|---|
| Details | Domain `manipmasta.<dominio>` · Scheme `http` · Forward `IP VM LAN` · Port `8080` |
| Details | **Websockets Support: ON** (obbligatorio: la UI riceve lo stato su `/ws`) · Block Common Exploits ON · Cache Assets OFF |
| SSL | Request a new certificate (Let's Encrypt) · **Force SSL ON** · HTTP/2 ON · HSTS a scelta |
| Access List | facoltativa: es. solo reti interne/VPN (NetBird) |

Advanced (consigliato, mantiene aperto il WebSocket):

```nginx
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

**authentik / forward-auth.** Se il proxy host è protetto con authentik (forward auth), l'app Android e
le chiamate API non passano: la WebView non completa il login OIDC sulle chiamate `fetch`/WebSocket e
riceverebbe redirect HTML. Due possibilità:

1. escludere dal forward-auth i percorsi `/api/` e `/ws` (in authentik: *Provider → Advanced protocol
   settings → Unauthenticated Paths*: `^/api/.*`, `^/ws.*`) — restano comunque protetti dal token;
2. non usare authentik su questo host e affidarsi al solo `API_TOKEN` (+ eventuale Access List).

## 5. Interfaccia e API

UI: `https://manipmasta.<dominio>/` — al primo accesso chiede il token (salvato nel browser).
L'app Android può passarlo nell'URL: `https://manipmasta.<dominio>/#token=<API_TOKEN>` (viene
salvato e tolto dalla barra). Installabile come PWA ("Aggiungi a schermata Home").

Tutte le API (tranne `/api/health`) richiedono `Authorization: Bearer <API_TOKEN>`.
Documentazione interattiva: `/api/docs`.

| Metodo | Percorso | Note |
|---|---|---|
| GET | `/api/health` | senza auth |
| GET | `/api/state` | `{online, mqtt, state, age}` (state = JSON SPEC §3) |
| POST | `/api/cmd` | `{"cmd":"HOME"}` → `{sent, cmd, resp, ok, timeout}`; whitelist e sintassi verificate; attesa risposta 2 s |
| GET/POST | `/api/recipes` | lista / crea (con `np`, `t_est` stimato in s, `run_line`) |
| GET/PUT/DELETE | `/api/recipes/{id}` | |
| POST | `/api/recipes/{id}/run` | invia la riga `RUN …` della ricetta |
| GET | `/api/history?limit=50` | storico cicli (esito: completato, interrotto, allarme, emergenza) |
| GET | `/api/events?limit=100` | ultimi eventi (in memoria) |
| WS | `/ws?token=…` | messaggi `{"type":"state|event|resp|online|mqtt|cmd|history","data":…}`; il client può inviare `ping` |

```bash
T=<API_TOKEN>; U=https://manipmasta.<dominio>
curl -H "Authorization: Bearer $T" -H 'Content-Type: application/json' -d '{"cmd":"HOME"}' $U/api/cmd
curl -H "Authorization: Bearer $T" -X POST $U/api/recipes/1/run
```

## 6. Sicurezza

- Il broker MQTT **non** va esposto su Internet né in LAN: `MQTT_BIND` = IP della VM sulla VLAN IoT;
  firewall che consente solo Arduino → VM:1883. Niente port-forward sul router.
- `allow_anonymous false` + password + ACL per utente: il server non può falsificare lo stato,
  l'Arduino non può inviarsi comandi.
- `API_TOKEN` lungo e casuale (`openssl rand -hex 32`); va cambiato se un telefono viene perso
  (modifica `.env`, `docker compose up -d`, nuovo login sui client).
- Accesso esterno solo via HTTPS (NPM, Force SSL); meglio ancora solo da VPN o con Access List.
- Il pulsante STOP software **non sostituisce** il fungo di emergenza e la catena di sicurezza hardware.
- Aggiornamenti: `apt upgrade` periodico, `docker compose pull && docker compose up -d --build`.

### Backup

Dati da salvare: `server/.env`, `server/data/manipmasta.db` (ricette e storico), `server/mosquitto/config/`.
Backup consistente del DB anche a server acceso:

```bash
sqlite3 data/manipmasta.db ".backup 'data/backup-$(date +%F).db'"
```

oppure backup della VM intera con Proxmox Backup Server (pianificazione giornaliera).

## 7. Sviluppo e test

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests          # la prova end-to-end richiede il binario mosquitto (apt install mosquitto)
MQTT_HOST=localhost API_TOKEN=dev DB_PATH=./data/dev.db \
  uvicorn app.main:create_app --factory --reload --port 8080
```

## Note di interpretazione della SPEC

- Ciclo RUN (§4): la passata doppia *k* va avanti al gap corrente; fuori impasto si applica
  `gap = max(g1, gap − dg)` e si torna indietro. Dopo `ceil((g0−g1)/dg)` passate doppie il gap è `g1`,
  poi `n` passate extra. `s` è interpolata linearmente fra `s0` (prima passata) e `s1` (ultima).
- Risposte: per `GET`/`SET` il simulatore risponde `OK GET <chiave> <valore>` / `OK SET <chiave> <valore>`
  (la SPEC indica solo `OK <cmd>`); la UI legge il valore da lì. Il firmware dovrebbe fare lo stesso.
- Eventi usati per lo storico: `CYCLE_START`, `PASS k/np` (inizio passata k), `CYCLE_DONE`, `STOP`,
  `ALARM <causa>`, `ESTOP`. Il simulatore emette anche `HOMED`, `PAUSED`, `RESUMED`, `RESET`, `BOOT`.
- `ENABLE`: il simulatore si avvia con driver abilitati; dopo un'emergenza `en=0` e `hm=0`
  (serve `RESET`, `ENABLE 1`, `HOME`). I movimenti con driver disabilitati rispondono `E04`.
- Topic `manipmasta/sim` e utente `manipmasta-tools`: aggiunte solo per il simulatore/diagnostica.
