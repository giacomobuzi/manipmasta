// =====================================================================
// Rete: Ethernet W5500 (IP statico) + MQTT con LWT, riconnessione non
// bloccante con backoff SOLO a macchina ferma. JSON senza ArduinoJson.
// =====================================================================
#include "net.h"
#include "config.h"
#include "params.h"
#include "machine.h"
#include "motion.h"
#include "inputs.h"
#include "cycle.h"
#include <SPI.h>
#include <Ethernet.h>
#include <PubSubClient.h>
#include <avr/wdt.h>
#include <string.h>

static EthernetClient ethClient;
static PubSubClient mqtt(ethClient);

static bool s_hwOk = false;
static unsigned long s_lastService = 0;
static unsigned long s_nextAttempt = 0;
static unsigned long s_backoff = MQTT_BACKOFF_MIN_MS;
static unsigned long s_lastStatePub = 0;
static bool s_stateReq = true;
static char s_clientId[24];
static uint8_t s_serverIp[4];

// Coda comandi MQTT (copiati dal callback: il buffer di PubSubClient
// viene riutilizzato dalle publish, quindi non si esegue nel callback)
#define MQ_SLOTS 2
static char s_mq[MQ_SLOTS][CMD_MAX_LEN];
static uint8_t s_mqHead = 0, s_mqCount = 0;
static bool s_mqDropped = false;

static char s_json[320];

// ---------------------------------------------------------------------
// JSON di stato (SPEC §3) - campi esatti
// ---------------------------------------------------------------------
struct JB {
  char *b; uint16_t cap, len;
  void raw(const char *s) { while (*s && len < cap - 1) b[len++] = *s++; b[len] = 0; }
  void rawP(PGM_P s) {
    char c;
    while ((c = (char)pgm_read_byte(s++)) && len < cap - 1) b[len++] = c;
    b[len] = 0;
  }
  void num(long v) { char t[24]; snprintf_P(t, sizeof(t), PSTR("%ld"), v); raw(t); }
  void fix(float v, uint8_t d) { char t[16]; fmtFixed(t, sizeof(t), v, d); raw(t); }
  void flag(bool v) { raw(v ? "1" : "0"); }
};

uint16_t buildStateJson(char *buf, uint16_t cap) {
  JB j = {buf, cap, 0};
  buf[0] = 0;
  char st[10];
  machStateName(machState(), st, sizeof(st));
  j.rawP(PSTR("{\"st\":\"")); j.raw(st);
  j.rawP(PSTR("\",\"hm\":")); j.flag(machHomed());
  j.rawP(PSTR(",\"en\":")); j.flag(motionEnabled());
  j.rawP(PSTR(",\"x\":")); j.fix(xPosMm(), 2);
  j.rawP(PSTR(",\"g\":")); j.fix(gapAvgMm(), 2);
  j.rawP(PSTR(",\"z1\":")); j.fix(gapMm(0), 2);
  j.rawP(PSTR(",\"z2\":")); j.fix(gapMm(1), 2);
  j.rawP(PSTR(",\"r\":")); j.fix(rPosMm(), 1);
  j.rawP(PSTR(",\"cyc\":{\"pass\":")); j.num(cyclePass());
  j.rawP(PSTR(",\"np\":")); j.num(cycleNp());
  j.rawP(PSTR(",\"gap\":")); j.fix(cycleGap(), 1);
  j.rawP(PSTR("},\"in\":{\"xmin\":")); j.flag(inActive(IN_X_MIN));
  j.rawP(PSTR(",\"xmax\":")); j.flag(inActive(IN_X_MAX));
  j.rawP(PSTR(",\"z1h\":")); j.flag(inActive(IN_Z1_HOME));
  j.rawP(PSTR(",\"z2h\":")); j.flag(inActive(IN_Z2_HOME));
  j.rawP(PSTR(",\"seat\":")); j.flag(seatOk());
  j.rawP(PSTR(",\"estop\":")); j.flag(inActive(IN_ESTOP));
  j.rawP(PSTR(",\"curt\":")); j.flag(inActive(IN_CURTAIN));
  j.rawP(PSTR("},\"alm\":\"")); j.raw(machAlarm());
  j.rawP(PSTR("\",\"fw\":\"" FW_VERSION "\",\"up\":")); j.num((long)(millis() / 1000UL));
  j.raw("}");
  return j.len;
}

// ---------------------------------------------------------------------
// MQTT
// ---------------------------------------------------------------------
static void mqttCallback(char *topic, byte *payload, unsigned int len) {
  (void)topic;
  if (s_mqCount >= MQ_SLOTS) { s_mqDropped = true; return; }
  uint8_t slot = (uint8_t)((s_mqHead + s_mqCount) % MQ_SLOTS);
  if (len >= CMD_MAX_LEN) len = CMD_MAX_LEN - 1;
  memcpy(s_mq[slot], payload, len);
  s_mq[slot][len] = 0;
  s_mqCount++;
}

bool netTakeCommand(char *out, uint8_t cap) {
  if (s_mqDropped) {
    s_mqDropped = false;
    netReply(SRC_MQTT, "ERR E04 coda comandi piena");
  }
  if (!s_mqCount) return false;
  strncpy(out, s_mq[s_mqHead], cap - 1);
  out[cap - 1] = 0;
  s_mqHead = (uint8_t)((s_mqHead + 1) % MQ_SLOTS);
  s_mqCount--;
  return true;
}

static void mqttAttempt(unsigned long now) {
  wdt_reset();
  bool isIp = parseIp(P.mqtt_host, s_serverIp);
  if (isIp) {
    mqtt.setServer(IPAddress(s_serverIp[0], s_serverIp[1], s_serverIp[2], s_serverIp[3]), P.mqtt_port);
  } else {
    // risoluzione DNS potenzialmente lunga: watchdog allargato solo qui (macchina ferma)
    mqtt.setServer(P.mqtt_host, P.mqtt_port);
    wdt_enable(WDTO_8S);
  }
  const char *user = P.mqtt_user[0] ? P.mqtt_user : NULL;
  const char *pass = (user && P.mqtt_pass[0]) ? P.mqtt_pass : NULL;
  bool ok = mqtt.connect(s_clientId, user, pass, TOPIC_ONLINE, 1, true, "0");
  if (!isIp) wdt_enable(WDTO_2S);
  wdt_reset();
  if (ok) {
    mqtt.publish(TOPIC_ONLINE, "1", true);
    mqtt.subscribe(TOPIC_CMD, 1);
    s_backoff = MQTT_BACKOFF_MIN_MS;
    s_stateReq = true;
    Serial.println(F("NET MQTT connesso"));
  } else {
    s_nextAttempt = now + s_backoff;
    s_backoff = s_backoff * 2 > MQTT_BACKOFF_MAX_MS ? MQTT_BACKOFF_MAX_MS : s_backoff * 2;
  }
}

void netInit() {
  // SD dello shield deselezionata
  pinMode(PIN_SD_CS, OUTPUT);
  digitalWrite(PIN_SD_CS, HIGH);
  s_mqHead = s_mqCount = 0;
  s_mqDropped = false;
  s_backoff = MQTT_BACKOFF_MIN_MS;
  s_nextAttempt = 0;
  s_stateReq = true;
  s_lastStatePub = 0;
  snprintf_P(s_clientId, sizeof(s_clientId), PSTR("manipmasta-%02x%02x%02x%02x%02x%02x"),
             P.mac[0], P.mac[1], P.mac[2], P.mac[3], P.mac[4], P.mac[5]);

  Ethernet.init(PIN_W5500_CS);
  Ethernet.begin(P.mac, IPAddress(P.ip[0], P.ip[1], P.ip[2], P.ip[3]),
                 IPAddress(P.dns[0], P.dns[1], P.dns[2], P.dns[3]),
                 IPAddress(P.gw[0], P.gw[1], P.gw[2], P.gw[3]),
                 IPAddress(P.mask[0], P.mask[1], P.mask[2], P.mask[3]));
  s_hwOk = Ethernet.hardwareStatus() != EthernetNoHardware;
  if (!s_hwOk) { Serial.println(F("NET W5500 non trovato: solo seriale")); return; }
  // limita i blocchi del W5500 (connect/send) ben sotto il watchdog
  Ethernet.setRetransmissionTimeout(50);
  Ethernet.setRetransmissionCount(3);
  ethClient.setConnectionTimeout(MQTT_CONN_TIMEOUT_MS);
  mqtt.setBufferSize(MQTT_BUFFER_SIZE);
  mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
  mqtt.setSocketTimeout(1);
  mqtt.setCallback(mqttCallback);
}

bool netMqttConnected() { return s_hwOk && mqtt.connected(); }

void netLoop(unsigned long now, bool moving) {
  if (!s_hwOk) return;
  // throttling: in movimento al massimo ogni NET_SERVICE_MOVING_MS
  if (moving && (now - s_lastService) < NET_SERVICE_MOVING_MS) return;
  s_lastService = now;
  Ethernet.maintain();
  if (mqtt.connected()) {
    mqtt.loop();
  } else if (!moving && (long)(now - s_nextAttempt) >= 0) {
    // connect() del W5500 puo' bloccare: SOLO a macchina ferma
    if (Ethernet.linkStatus() == LinkOFF) {
      s_nextAttempt = now + MQTT_BACKOFF_MIN_MS;
    } else {
      mqttAttempt(now);
    }
  }
  if (!mqtt.connected()) return;
  unsigned long interval = moving ? STATE_PUB_MOVING_MS : STATE_PUB_REST_MS;
  if (s_stateReq || (now - s_lastStatePub) >= interval) {
    s_stateReq = false;
    s_lastStatePub = now;
    buildStateJson(s_json, sizeof(s_json));
    mqtt.publish(TOPIC_STATE, s_json, true);
  }
}

void netRequestState() { s_stateReq = true; }

void netPrintStateSerial() {
  buildStateJson(s_json, sizeof(s_json));
  Serial.println(s_json);
}

void netReply(CmdSrc src, const char *txt) {
  if (src == SRC_MQTT) {
    if (netMqttConnected()) mqtt.publish(TOPIC_RESP, txt);
  } else if (src == SRC_LOCAL) {
    if (strncmp_P(txt, PSTR("ERR"), 3) == 0) netEvent(txt);   // errori da pulsanti -> evento
  } else {
    Serial.println(txt);
  }
}

void netEvent(const char *txt) {
  Serial.print(F("EVT "));
  Serial.println(txt);
  if (netMqttConnected()) mqtt.publish(TOPIC_EVENT, txt);
  s_stateReq = true;
}
