# ManipMasta – app Android

App nativa Kotlin (`it.mybuzi.manipmasta`, Android 8.0+ / minSdk 26) che mostra a tutto schermo la UI web del
server ManipMasta (SPEC §5–6) e aggiunge:

- **pulsante STOP nativo** rosso, sempre visibile in basso, anche se la pagina non si carica:
  invia `POST {url}/api/cmd {"cmd":"STOP"}` con `Authorization: Bearer <token>`, conferma con Snackbar e vibrazione
  (vibrazione lunga + pulsante "Riprova" se l'invio fallisce);
- **schermata "Server non raggiungibile"** con *Riprova* e *Impostazioni*; pull-to-refresh; tasto indietro = indietro nella WebView;
- **impostazioni**: URL server, token API (salvato cifrato con EncryptedSharedPreferences), schermo sempre acceso,
  notifiche fine ciclo, *Test connessione* (`GET /api/health` e verifica token su `GET /api/state`);
- **notifiche** di fine ciclo (`CYCLE_DONE`), allarme (`ALARM …`) ed emergenza (`ESTOP`) tramite un servizio in primo piano
  che tiene aperta la WebSocket `/ws?token=…`.

> Lo STOP dell'app è un comando software via rete. **Non sostituisce il fungo di emergenza** cablato (SPEC §2).

## 1. Ottenere l'APK

L'APK viene compilato automaticamente da GitHub Actions (`.github/workflows/android.yml`) a ogni push su `main`
che tocca `android/**`, oppure a mano.

- **Da Actions**: repository → tab **Actions** → workflow *Android APK* → ultima esecuzione verde →
  sezione **Artifacts** → `manipmasta-apk` (zip). Dentro:
  - `ManipMasta-<versione>-debug.apk` → **questo è quello da installare** (firmato con chiave di debug);
  - `ManipMasta-<versione>-release-unsigned.apk` → release non firmata, non installabile finché non si configura la firma (§5).
- **Avvio manuale**: tab Actions → *Android APK* → **Run workflow**.
- **Da Releases**: creando e pushando un tag `v*` il workflow pubblica una Release con gli APK allegati:
  ```bash
  git tag v1.0.0 && git push origin v1.0.0
  ```
  La versione dell'app (`versionName`) diventa `1.0.0`; `versionCode` = numero di esecuzione del workflow.

## 2. Installazione (sorgenti sconosciute)

1. Copia l'APK sul telefono (download dal browser, Drive, cavo USB…).
2. Aprilo dal file manager / dai download. Android chiederà di consentire l'installazione da quell'app
   (*Impostazioni → App → accesso speciale → Installa app sconosciute* → abilita per Chrome/Files).
3. Conferma l'installazione. Play Protect può avvisare che l'app non è nota: *Installa comunque*.
4. Aggiornamenti: installa il nuovo APK sopra il precedente. Funziona solo se è firmato con la **stessa chiave**:
   passare da debug a release firmata (o cambiare keystore) richiede di disinstallare prima l'app.
   Gli APK debug compilati su runner diversi possono avere chiavi debug diverse: se l'aggiornamento
   viene rifiutato, disinstalla e reinstalla (le impostazioni vanno reinserite) oppure configura la firma release.

## 3. Configurazione

Al primo avvio si apre **Impostazioni**:

| Voce | Valore |
|---|---|
| URL server | `https://manipmasta.<tuo-dominio>` (Nginx Proxy Manager, SPEC §5). Senza schema viene aggiunto `https://`. |
| Token API | lo stesso `API_TOKEN` del server. Salvato cifrato (Android Keystore). |
| Mantieni schermo acceso | attivo di default: lo schermo non si spegne finché l'app è in primo piano (utile durante il ciclo). |
| Notifiche fine ciclo | avvia il servizio di monitoraggio (vedi §4). Su Android 13+ viene chiesto il permesso notifiche. |
| Test connessione | prova `GET /api/health` (senza auth) e poi `GET /api/state` col token: indica se il token è valido. |

### Come arriva il token alla UI web (scelta implementativa)

La UI web legge il token da `localStorage["mm_token"]`. L'app:

1. carica `{url}/` passando anche l'header `Authorization: Bearer <token>` (vale solo per la richiesta iniziale
   della pagina: utile se un proxy protegge già `/`);
2. al **primo `onPageFinished`** sulla stessa origine del server esegue `evaluateJavascript` che scrive il token in
   `localStorage["mm_token"]`; **se il valore era diverso ricarica la pagina una volta**, così la UI parte già autenticata.

Le chiamate `fetch`/WebSocket della UI usano quindi il token dal localStorage come in un browser normale.
Cambiando URL o token nelle impostazioni la pagina viene ricaricata. Lo user agent della WebView termina con
`ManipMastaApp/<versione>`: la UI può riconoscere l'app (es. per nascondere il proprio pulsante STOP).
I link verso altri domini si aprono nel browser di sistema.

### HTTP in rete locale (network_security_config)

Di default l'app accetta **solo HTTPS** (`app/src/main/res/xml/network_security_config.xml`).
HTTP in chiaro è consentito solo verso:

- `localhost`, `127.0.0.1`, `10.0.2.2` (emulatore);
- `192.168.50.10` (VM ManipMasta nella VLAN IoT, SPEC §2.2) → es. `http://192.168.50.10:8080`;
- nomi host `*.local`, `*.lan`, `*.home.arpa`, `*.internal`, `*.localdomain`.

Android non permette di indicare intervalli (es. tutto `192.168.0.0/16`): per un altro IP LAN aggiungi una riga
`<domain includeSubdomains="false">192.168.x.y</domain>` nel `domain-config` e ricompila, oppure usa un nome host `.lan`.
In aggiunta, le Impostazioni rifiutano un URL `http://` verso host non privati. Per gli host LAN sono accettate anche
CA installate dall'utente (certificati interni del homelab); per tutti gli altri solo le CA di sistema
(Let's Encrypt va bene). Uso consigliato: HTTPS tramite Nginx Proxy Manager.

## 4. Notifiche e servizio in background

Con *Notifiche fine ciclo* attivo l'app avvia un **foreground service** (`foregroundServiceType="dataSync"`) che
mantiene una WebSocket OkHttp su `wss://…/ws?token=…` (ping ogni 20 s, riconnessione con backoff 2→60 s) e mostra:

- **Ciclo completato** su `CYCLE_DONE`;
- **ALLARME macchina** su eventi `ALARM …` (testo dell'evento nel corpo);
- **EMERGENZA attiva** su `ESTOP`.

È presente una notifica fissa ("monitoraggio attivo") con il pulsante **Disattiva**. Il servizio viene avviato quando
apri l'app (Android non consente di avviarlo da background). Limiti noti: Android 15 limita i servizi `dataSync`
a ~6 ore ogni 24 h, poi il servizio si ferma (riaprire l'app lo riavvia); alcune ROM con risparmio energetico
aggressivo possono chiuderlo: escludi ManipMasta dall'ottimizzazione batteria.

## 5. Compilare in locale (Android Studio)

Requisiti: Android Studio Ladybug (2024.2) o successivo, JDK 17, Android SDK 35.

Nel repository **non è incluso il Gradle wrapper** (il jar binario non è versionato). Due opzioni:

- **Android Studio**: *File → Open* sulla cartella `android/`. Se chiede il wrapper, genera prima il wrapper da terminale
  (sotto) oppure in *Settings → Build Tools → Gradle* scegli una distribuzione Gradle locale 8.10.2+.
- **Terminale** (con Gradle 8.10.2 installato, es. `sdk install gradle 8.10.2`):
  ```bash
  cd android
  gradle wrapper --gradle-version 8.10.2   # una volta: crea gradlew + gradle-wrapper.jar
  ./gradlew assembleDebug
  # APK: app/build/outputs/apk/debug/app-debug.apk
  adb install -r app/build/outputs/apk/debug/app-debug.apk
  ```
  Serve `local.properties` con `sdk.dir=/percorso/Android/Sdk` oppure la variabile `ANDROID_HOME`.

Stack: AGP 8.7.3, Kotlin 2.0.21, compileSdk/targetSdk 35, view system + Material Components 3 (niente Compose),
OkHttp 4.12, AndroidX Preference, security-crypto.

## 6. Firma release (keystore come secret)

1. Crea un keystore (una volta, conservalo con cura: serve per tutti gli aggiornamenti futuri):
   ```bash
   keytool -genkeypair -v -keystore manipmasta-release.jks -alias manipmasta \
     -keyalg RSA -keysize 4096 -validity 10000
   base64 -w0 manipmasta-release.jks > keystore.b64
   ```
2. Su GitHub: *Settings → Secrets and variables → Actions → New repository secret*:
   - `MM_KEYSTORE_BASE64` = contenuto di `keystore.b64`
   - `MM_KEYSTORE_PASSWORD` = password del keystore
   - `MM_KEY_ALIAS` = `manipmasta`
   - `MM_KEY_PASSWORD` = password della chiave
3. Al build successivo il workflow decodifica il keystore, imposta `MM_KEYSTORE_FILE` e `assembleRelease`
   produce `ManipMasta-<versione>-release.apk` firmato (installabile). Senza secret resta `release-unsigned`.

In locale la stessa firma si ottiene esportando le variabili:
```bash
export MM_KEYSTORE_FILE=$PWD/manipmasta-release.jks MM_KEYSTORE_PASSWORD=… MM_KEY_ALIAS=manipmasta MM_KEY_PASSWORD=…
./gradlew assembleRelease
```
Non committare mai il `.jks` (è in `.gitignore`).

## 7. Struttura

```
android/
├── build.gradle.kts, settings.gradle.kts, gradle.properties
└── app/
    ├── build.gradle.kts
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/it/mybuzi/manipmasta/
        │   ├── MainActivity.kt       WebView, errore rete, pull-to-refresh, STOP
        │   ├── SettingsActivity.kt   contenitore + toolbar
        │   ├── SettingsFragment.kt   preferenze, test connessione, permesso notifiche
        │   ├── MonitorService.kt     foreground service WebSocket + notifiche eventi
        │   ├── Prefs.kt              EncryptedSharedPreferences + PreferenceDataStore
        │   ├── Net.kt                client OkHttp, messaggi di errore
        │   ├── UrlUtils.kt           normalizzazione URL, host LAN, URL WebSocket
        │   ├── Notifications.kt      canali notifiche
        │   └── ManipMastaApp.kt
        └── res/ (layout, xml/preferences + network_security_config, icona adattiva vettoriale, stringhe IT)
```
