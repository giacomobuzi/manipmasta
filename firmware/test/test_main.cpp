// =====================================================================
// Test host della logica firmware ManipMasta (g++ + mock Arduino)
// =====================================================================
#include <cstdio>
#include <string>
#include <vector>
#include <cmath>
#include "mockctl.h"
#include "Arduino.h"
#include "AccelStepper.h"
#include "EEPROM.h"
#include "Ethernet.h"
#include "PubSubClient.h"
#include "avr/wdt.h"
#include "config.h"
#include "params.h"
#include "inputs.h"
#include "motion.h"
#include "cycle.h"
#include "machine.h"
#include "protocol.h"
#include "net.h"

static int g_pass = 0, g_fail = 0;
static const char *g_test = "";

#define CHECK(c) do { if (c) g_pass++; else { g_fail++; \
  printf("  FAIL [%s] %s:%d: %s\n", g_test, __FILE__, __LINE__, #c); } } while (0)
#define CHECK_STR(a, b) do { std::string _a = (a), _b = (b); if (_a == _b) g_pass++; else { g_fail++; \
  printf("  FAIL [%s] %s:%d: \"%s\" != \"%s\"\n", g_test, __FILE__, __LINE__, _a.c_str(), _b.c_str()); } } while (0)
#define CHECK_NEAR(a, b, tol) do { double _a = (a), _b = (b); if (fabs(_a - _b) <= (tol)) g_pass++; else { g_fail++; \
  printf("  FAIL [%s] %s:%d: %s = %.4f, atteso %.4f\n", g_test, __FILE__, __LINE__, #a, _a, _b); } } while (0)

// ---------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------
static bool g_physX = true;     // finecorsa X_MIN simulato dalla posizione fisica
static const long Z1_HOME_PHYS = -3000, Z2_HOME_PHYS = -3100, X_MIN_PHYS = -4000;

static PubSubClient &mq() { return *PubSubClient::instance; }

static void healthyInputs() {
  const uint8_t highs[] = {PIN_X_ALM, PIN_Z1_ALM, PIN_Z2_ALM, PIN_R_ALM, PIN_X_MIN, PIN_X_MAX,
                           PIN_Z1_HOME, PIN_Z2_HOME, PIN_Z1_LOW, PIN_Z2_LOW, PIN_BTN_START};
  for (uint8_t p : highs) mock::inVal[p] = HIGH;
  mock::inVal[PIN_SEAT_A] = LOW;
  mock::inVal[PIN_SEAT_B] = LOW;
  mock::inVal[PIN_BTN_STOP] = LOW;     // NC chiuso = non premuto
  mock::inVal[PIN_ESTOP_OK] = LOW;     // catena OK
  mock::inVal[PIN_CURTAIN_OK] = LOW;   // barriera libera
}

static void installPhysics() {
  mock::inputHook = [](uint8_t pin, int v) -> int {
    if (pin == PIN_Z1_HOME) return motZ(0)._phys <= Z1_HOME_PHYS ? LOW : HIGH;
    if (pin == PIN_Z2_HOME) return motZ(1)._phys <= Z2_HOME_PHYS ? LOW : HIGH;
    if (pin == PIN_X_MIN && g_physX) return motX()._phys <= X_MIN_PHYS ? LOW : HIGH;
    return v;
  };
}

static void tick(long n = 1) {
  for (long i = 0; i < n; i++) { mock::advanceUs(200); mmLoop(); }
}

template <typename F>
static bool runUntil(F pred, long maxLoops = 2000000) {
  for (long i = 0; i < maxLoops; i++) { if (pred()) return true; tick(); }
  return pred();
}

static void boot() {
  mock::reset();
  memset(EEPROM.data, 0xFF, sizeof(EEPROM.data));
  healthyInputs();
  g_physX = true;
  installPhysics();
  if (PubSubClient::instance) {
    PubSubClient &m = mq();
    m.conn = false; m.acceptConnect = true; m.connectCalls = 0; m.pubs.clear(); m.subs.clear();
  }
  motX()._phys = 0; motZ(0)._phys = 0; motZ(1)._phys = 0;
  mmSetup();
  tick(1000);   // 200 ms: fine BOOT
}

static std::vector<std::string> lines(const std::string &s) {
  std::vector<std::string> v;
  size_t a = 0;
  while (a < s.size()) {
    size_t b = s.find("\r\n", a);
    if (b == std::string::npos) b = s.size();
    v.push_back(s.substr(a, b - a));
    a = b + 2;
  }
  return v;
}

// Invia un comando su seriale e ritorna la risposta OK/ERR
static std::string cmd(const std::string &c) {
  mock::serialOut.clear();
  mock::serialIn = c + "\n";
  mock::serialPos = 0;
  tick(1);
  for (int i = 0; i < 10 && mock::serialPos < mock::serialIn.size(); i++) tick(1);
  for (auto &l : lines(mock::serialOut))
    if (l.rfind("OK", 0) == 0 || l.rfind("ERR", 0) == 0) return l;
  return "";
}

static std::string g_events;   // log eventi accumulato
static void collect() {
  for (auto &l : lines(mock::serialOut))
    if (l.rfind("EVT ", 0) == 0) g_events += l.substr(4) + "|";
  mock::serialOut.clear();
}
static void tickCollect(long n = 1) { for (long i = 0; i < n; i++) { tick(); collect(); } }
template <typename F>
static bool runUntilCollect(F pred, long maxLoops = 3000000) {
  for (long i = 0; i < maxLoops; i++) { if (pred()) return true; tick(); collect(); }
  return pred();
}

static bool doHome() {
  if (cmd("HOME") != "OK HOME") return false;
  return runUntil([] { return machState() == ST_READY || machState() == ST_ALARM; }) && machState() == ST_READY;
}

static std::string stName() { char b[12]; machStateName(machState(), b, sizeof(b)); return b; }

// ---------------------------------------------------------------------
// Test
// ---------------------------------------------------------------------
static void testFmt() {
  g_test = "fmtFixed/parse";
  char b[24];
  fmtFixed(b, sizeof(b), -0.5f, 2); CHECK_STR(b, "-0.50");
  fmtFixed(b, sizeof(b), 0.004f, 2); CHECK_STR(b, "0.00");
  fmtFixed(b, sizeof(b), -0.004f, 2); CHECK_STR(b, "0.00");
  fmtFixed(b, sizeof(b), 123.456f, 3); CHECK_STR(b, "123.456");
  fmtFixed(b, sizeof(b), -700.0f, 2); CHECK_STR(b, "-700.00");
  fmtFixed(b, sizeof(b), 5.093f, 3); CHECK_STR(b, "5.093");
  uint8_t ip[4];
  CHECK(parseIp("192.168.50.60", ip) && ip[3] == 60);
  CHECK(!parseIp("192.168.50", ip));
  CHECK(!parseIp("1.2.3.256", ip));
  uint8_t mac[6];
  CHECK(parseMac("02:4d:4D:00:00:0a", mac) && mac[1] == 0x4D && mac[5] == 0x0A);
  CHECK(!parseMac("02:4d:4D:00:00", mac));
  float f;
  CHECK(parseFloatStrict("-12.5", &f) && f == -12.5f);
  CHECK(!parseFloatStrict("12x", &f));
  CHECK(!parseFloatStrict("", &f));
}

static void testParser() {
  g_test = "parser";
  boot();
  CHECK_STR(stName(), "IDLE");
  CHECK_STR(cmd("PING"), "OK PING");
  CHECK_STR(cmd("ping"), "OK PING");
  CHECK_STR(cmd("  Ping  "), "OK PING");
  CHECK_STR(cmd("FOO"), "ERR E01 comando sconosciuto");
  CHECK_STR(cmd("PING 1"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("JOG Q 5"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("JOG X"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("MOVE X abc"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("MOVE Y 10"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("MOVE X 10"), "ERR E03 non homed");
  CHECK_STR(cmd("move x 10 f 50"), "ERR E03 non homed");
  CHECK_STR(cmd("GAP 10"), "ERR E03 non homed");
  CHECK_STR(cmd("RUN"), "ERR E03 non homed");
  CHECK_STR(cmd("RUN g0=abc"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("RUN zz=1"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("RUN n=1.5"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("ENABLE 2"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("RESUME"), "ERR E04 stato non consente");
  CHECK_STR(cmd("PAUSE"), "ERR E04 stato non consente");
  CHECK_STR(cmd("STATUS"), "OK STATUS");
  CHECK(mock::serialOut.find("{\"st\":\"IDLE\"") != std::string::npos);
  CHECK_STR(cmd(""), "");
  CHECK_STR(cmd("A B C D E F G H I J K L M N"), "ERR E02 parametro non valido");
  // riga troppo lunga
  CHECK_STR(cmd(std::string(150, 'X')), "ERR E02 parametro non valido");
  CHECK_STR(cmd("PING"), "OK PING");
}

static void testParams() {
  g_test = "params SET/GET/SAVE";
  boot();
  CHECK_STR(cmd("GET x_spm"), "OK GET x_spm 16.000");
  CHECK_STR(cmd("GET r_spm"), "OK GET r_spm 5.093");
  CHECK_STR(cmd("GET z_home_gap"), "OK GET z_home_gap 150.000");
  CHECK_STR(cmd("GET ip"), "OK GET ip 192.168.50.60");
  CHECK_STR(cmd("GET mqtt_host"), "OK GET mqtt_host 192.168.50.10");
  CHECK_STR(cmd("GET mqtt_port"), "OK GET mqtt_port 1883");
  CHECK_STR(cmd("GET mqtt_user"), "OK GET mqtt_user manipmasta");
  CHECK_STR(cmd("GET mqtt_pass"), "OK GET mqtt_pass (vuota)");
  CHECK_STR(cmd("SET x_spm 0"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("SET x_spm abc"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("SET X_SPM 20"), "OK SET");
  CHECK_STR(cmd("GET x_spm"), "OK GET x_spm 20.000");
  CHECK_STR(cmd("SET x_min 900"), "ERR E02 parametro non valido");   // x_min >= x_max
  CHECK_STR(cmd("SET g_min 200"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("SET ip 10.0.0.5"), "OK SET");
  CHECK_STR(cmd("GET ip"), "OK GET ip 10.0.0.5");
  CHECK_STR(cmd("SET ip 300.1.1.1"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("SET mac 02:aa:bb:cc:dd:ee"), "OK SET");
  CHECK_STR(cmd("GET mac"), "OK GET mac 02:AA:BB:CC:DD:EE");
  CHECK_STR(cmd("SET mqtt_pass segreto"), "OK SET");
  CHECK_STR(cmd("GET mqtt_pass"), "OK GET mqtt_pass ***");
  CHECK_STR(cmd("SET mqtt_port 0"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("SET dir_inv 16"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("SET dir_inv 3"), "OK SET");
  CHECK(motX()._dirInv && motZ(0)._dirInv && !motZ(1)._dirInv);
  CHECK_STR(cmd("SET pippo 1"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("GET pippo"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("SAVE"), "OK SAVE");
  // ricarica da EEPROM
  CHECK(paramsLoad());
  CHECK(P.x_spm == 20.0f && P.ip[0] == 10 && strcmp(P.mqtt_pass, "segreto") == 0);
  // EEPROM corrotta -> default
  EEPROM.data[10] ^= 0x55;
  CHECK(!paramsLoad());
  CHECK(P.x_spm == 16.0f && P.ip[0] == 192);
  // DEFAULTS
  CHECK_STR(cmd("SET od 5"), "OK SET");
  CHECK_STR(cmd("DEFAULTS"), "OK DEFAULTS");
  CHECK_STR(cmd("GET od"), "OK GET od 2.000");
  // SAVE non riscrive byte invariati
  cmd("SAVE");
  unsigned long w = EEPROM.writes;
  cmd("SAVE");
  CHECK(EEPROM.writes == w);
  // EEPROM vergine al boot -> default
  boot();
  CHECK(P.x_spm == 16.0f && P.mqtt_port == 1883);
}

static void testCycleMath() {
  g_test = "calcolo passate RUN";
  boot();
  RunParams p;
  runDefaults(p);
  CHECK(p.cx == 0 && p.s0 == 150 && p.s1 == 300 && p.g0 == 40 && p.g1 == 5 && p.dg == 3 && p.f == 60 && p.n == 2);
  CHECK_NEAR(p.od, 2.0, 1e-6);
  CHECK(cyclePassCount(p) == 14);           // ceil(35/3)=12 + 2
  const float expG[14] = {40, 37, 34, 31, 28, 25, 22, 19, 16, 13, 10, 7, 5, 5};
  for (int k = 0; k < 14; k++) CHECK_NEAR(cycleGapForPass(p, k), expG[k], 1e-4);
  CHECK_NEAR(cycleSForPass(p, 0, 14), 150, 1e-4);
  CHECK_NEAR(cycleSForPass(p, 13, 14), 300, 1e-4);
  CHECK_NEAR(cycleSForPass(p, 1, 14), 150 + 150.0 / 13, 1e-3);
  RunParams q = p;
  q.g0 = 5; q.g1 = 5; q.n = 2;              CHECK(cyclePassCount(q) == 2);
  q = p; q.g0 = 40; q.g1 = 10; q.n = 0;     CHECK(cyclePassCount(q) == 10);   // divisione esatta
  q = p; q.g0 = 1.0f; q.g1 = 0.1f; q.dg = 0.3f; q.n = 0; CHECK(cyclePassCount(q) == 3);  // 0.9/0.3 float
  q = p; q.dg = 4; q.n = 2;                 CHECK(cyclePassCount(q) == 11);   // ceil(8.75)=9 + 2
  q = p; q.dg = 50; q.n = 0;                CHECK(cyclePassCount(q) == 1);
  uint16_t np = 0;
  CHECK(cycleValidate(p, &np) == 0 && np == 14);
  q = p; q.f = 0;      CHECK(cycleValidate(q, &np) == 2);
  q = p; q.f = 200;    CHECK(cycleValidate(q, &np) == 2);    // > x_vmax
  q = p; q.g1 = 0.2f;  CHECK(cycleValidate(q, &np) == 5);    // < g_min
  q = p; q.g0 = 151;   CHECK(cycleValidate(q, &np) == 5);    // > g_max
  q = p; q.g0 = 4;     CHECK(cycleValidate(q, &np) == 2);    // g0 < g1
  q = p; q.dg = 0;     CHECK(cycleValidate(q, &np) == 2);
  q = p; q.cx = 500;   CHECK(cycleValidate(q, &np) == 5);    // 500+300+60 > 700
  q = p; q.cx = -341;  CHECK(cycleValidate(q, &np) == 5);
  q = p; q.cx = 340;   CHECK(cycleValidate(q, &np) == 0);
  q = p; q.g0 = 5; q.n = 0; CHECK(cycleValidate(q, &np) == 2);  // np = 0
  q = p; q.od = 30;    CHECK(cycleValidate(q, &np) == 2);
}

static void testHoming() {
  g_test = "homing";
  boot();
  // portale non in sede
  mock::inVal[PIN_SEAT_B] = HIGH;
  tick(20);
  CHECK_STR(cmd("HOME"), "ERR E06 portale non in sede");
  mock::inVal[PIN_SEAT_B] = LOW;
  tick(20);
  mock::serialOut.clear();
  g_events.clear();
  CHECK_STR(cmd("HOME"), "OK HOME");
  collect();
  CHECK_STR(stName(), "HOMING");
  CHECK(runUntilCollect([] { return machState() != ST_HOMING; }));
  CHECK_STR(stName(), "READY");
  CHECK(machHomed());
  CHECK(g_events.find("HOMED|") != std::string::npos);
  CHECK_NEAR(xPosMm(), -700.0, 1e-3);
  CHECK_NEAR(gapMm(0), 150.0, 1e-3);
  CHECK_NEAR(gapMm(1), 150.0, 1e-3);
  // Z1 e Z2 indipendenti: ognuno fermo sul proprio finecorsa (fisico diverso)
  CHECK(llabs(motZ(0)._phys - Z1_HOME_PHYS) <= 3);
  CHECK(llabs(motZ(1)._phys - Z2_HOME_PHYS) <= 3);
  // X: finecorsa = x_min - x_home_off, poi a x_min (+20 mm = 320 passi)
  CHECK(llabs(motX()._phys - (X_MIN_PHYS + 320)) <= 3);

  // Homing fallito: X_MIN mai trovato -> ALARM
  boot();
  g_physX = false;
  CHECK_STR(cmd("HOME"), "OK HOME");
  CHECK(runUntil([] { return machState() != ST_HOMING; }, 5000000));
  CHECK_STR(stName(), "ALARM");
  CHECK_STR(machAlarm(), "HOME_X");
  CHECK(!machHomed());
  CHECK_STR(cmd("RESET"), "OK RESET");
  CHECK_STR(stName(), "IDLE");

  // Timeout: Z1 bloccato (nessun passo fisico) -> ALARM HOME_Z1 entro il timeout
  boot();
  mock::inputHook = [](uint8_t pin, int v) -> int {
    if (pin == PIN_Z2_HOME) return motZ(1)._phys <= Z2_HOME_PHYS ? LOW : HIGH;
    return v;   // Z1_HOME mai attivo
  };
  AccelStepper::stepsPerRun = 0;            // motori "bloccati": nessun avanzamento
  unsigned long t0 = millis();
  CHECK_STR(cmd("HOME"), "OK HOME");
  CHECK(runUntil([] { return machState() != ST_HOMING; }, 2000000));
  CHECK_STR(stName(), "ALARM");
  CHECK_STR(machAlarm(), "HOME_Z1");
  CHECK(millis() - t0 >= HOME_Z_FAST_TO_MS);
  AccelStepper::stepsPerRun = 1;
}

static void testLimits() {
  g_test = "limiti software";
  boot();
  CHECK(doHome());
  CHECK_STR(cmd("MOVE X 800"), "ERR E05 fuori limiti");
  CHECK_STR(cmd("MOVE X -781"), "ERR E05 fuori limiti");
  CHECK_STR(cmd("MOVE X 100 F 200"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("MOVE X 100 F 0"), "ERR E02 parametro non valido");
  CHECK_STR(cmd("GAP 0.2"), "ERR E05 fuori limiti");
  CHECK_STR(cmd("GAP 151"), "ERR E05 fuori limiti");
  CHECK_STR(cmd("JOG X -10"), "ERR E05 fuori limiti");    // gia' a x_min
  CHECK_STR(cmd("JOG G 10"), "ERR E05 fuori limiti");     // gia' a g_max
  CHECK_STR(cmd("RUN cx=500"), "ERR E05 fuori limiti");
  CHECK_STR(cmd("RUN g1=0.1"), "ERR E05 fuori limiti");
  CHECK_STR(cmd("GAP 40"), "OK GAP");
  CHECK_STR(stName(), "MOVING");
  CHECK_STR(cmd("GAP 30"), "ERR E04 stato non consente");
  CHECK_STR(cmd("SET x_spm 10"), "ERR E04 stato non consente");
  CHECK(runUntil([] { return machState() == ST_READY; }));
  CHECK_NEAR(gapMm(0), 40.0, 1e-3);
  CHECK_NEAR(gapMm(1), 40.0, 1e-3);
  CHECK_STR(cmd("JOG G -39.5"), "OK JOG");                // a g_min esatto
  CHECK(runUntil([] { return machState() == ST_READY; }));
  CHECK_NEAR(gapAvgMm(), 0.5, 1e-3);
  CHECK_STR(cmd("JOG G -0.1"), "ERR E05 fuori limiti");
  CHECK_STR(cmd("MOVE X 700 F 150"), "OK MOVE");
  CHECK(runUntil([] { return machState() == ST_READY; }));
  CHECK_NEAR(xPosMm(), 700.0, 1e-3);
  CHECK_STR(cmd("JOG X 0.5"), "ERR E05 fuori limiti");
  // cambio step/mm -> homing perso
  CHECK_STR(cmd("SET x_spm 16.5"), "OK SET");
  CHECK(!machHomed());
  CHECK_STR(stName(), "IDLE");
  CHECK_STR(cmd("SET od 3"), "OK SET");               // non invalida l'homing (gia' perso)
}

static void testGearing() {
  g_test = "asservimento R";
  boot();
  CHECK(doHome());
  mock::rPulses = mock::rPulsesPos = mock::rPulsesNeg = 0;
  // od = 2 % : 100 mm di X -> 100 * 5.093 * 1.02 = 519.486 -> 519 passi R
  CHECK_STR(cmd("MOVE X -600"), "OK MOVE");
  long maxLag = 0;
  runUntil([&] {
    long expect = lround((motX().currentPosition() - (-700 * 16)) * 5.093 / 16.0 * 1.02);
    long lag = labs(expect - mock::rPulses);
    if (lag > maxLag) maxLag = lag;
    return machState() == ST_READY;
  });
  CHECK(maxLag <= 1);                       // un passo per iterazione: R insegue X
  CHECK(mock::rPulses == 519);
  CHECK(mock::rPulsesNeg == 0);             // verso coerente con X+
  CHECK(rPosSteps() == 519);
  CHECK_NEAR(rPosMm(), 519 / 5.093, 1e-3);
  // ritorno: R ruota al contrario (rotolamento senza strisciamento)
  CHECK_STR(cmd("MOVE X -700"), "OK MOVE");
  CHECK(runUntil([] { return machState() == ST_READY; }));
  CHECK(mock::rPulses == 0);
  CHECK(mock::rPulsesNeg == 519);
  // od = 0
  CHECK_STR(cmd("SET od 0"), "OK SET");
  mock::rPulses = mock::rPulsesPos = mock::rPulsesNeg = 0;
  CHECK_STR(cmd("MOVE X -600"), "OK MOVE");
  CHECK(runUntil([] { return machState() == ST_READY; }));
  CHECK(mock::rPulses == 509);              // 509.3
  // dir_inv bit3: inverte il livello DIR di R ma non il conteggio logico
  CHECK_STR(cmd("SET dir_inv 8"), "OK SET");
  CHECK(!machHomed());
  // JOG R indipendente
  long before = rPosSteps();
  CHECK_STR(cmd("JOG R 10"), "OK JOG");
  CHECK(runUntil([] { return machState() == ST_IDLE; }));
  CHECK(rPosSteps() - before == lround(10 * 5.093));
}

static void testEstop() {
  g_test = "ESTOP/RESET";
  boot();
  CHECK(doHome());
  CHECK_STR(cmd("MOVE X 0"), "OK MOVE");
  tick(200);
  CHECK(xBusy());
  mock::setPin(PIN_ESTOP_OK, HIGH);         // ISR
  // driver disabilitati subito dall'ISR, prima del loop
  CHECK(mock::outVal[PIN_X_ENA] == ENA_INACTIVE_LEVEL);
  CHECK(mock::outVal[PIN_Z1_ENA] == ENA_INACTIVE_LEVEL);
  CHECK(mock::outVal[PIN_Z2_ENA] == ENA_INACTIVE_LEVEL);
  CHECK(mock::outVal[PIN_R_ENA] == ENA_INACTIVE_LEVEL);
  mock::serialOut.clear();
  g_events.clear();
  tickCollect(1);
  CHECK_STR(stName(), "ESTOP");
  CHECK(g_events.find("ESTOP|") != std::string::npos);
  CHECK(!machHomed());
  CHECK(!motionEnabled());
  long x = motX().currentPosition();
  tick(100);
  CHECK(motX().currentPosition() == x);     // fermo immediato
  CHECK(!motionBusy());
  CHECK(mock::outVal[PIN_LAMP_RED] == HIGH);
  CHECK_STR(cmd("RESET"), "ERR E07 emergenza attiva");
  CHECK_STR(cmd("MOVE X 0"), "ERR E07 emergenza attiva");
  CHECK_STR(cmd("ENABLE 1"), "ERR E07 emergenza attiva");
  CHECK_STR(cmd("HOME"), "ERR E07 emergenza attiva");
  mock::setPin(PIN_ESTOP_OK, LOW);
  tick(10);
  CHECK_STR(stName(), "ESTOP");             // resta in ESTOP fino a RESET
  CHECK_STR(cmd("RESET"), "OK RESET");
  CHECK_STR(stName(), "IDLE");
  CHECK(motionEnabled());
  CHECK(mock::outVal[PIN_X_ENA] == ENA_ACTIVE_LEVEL);
  CHECK_STR(cmd("MOVE X 0"), "ERR E03 non homed");
  CHECK(doHome());
  // ESTOP anche senza fronte ISR (solo livello)
  mock::inVal[PIN_ESTOP_OK] = HIGH;
  tick(1);
  CHECK_STR(stName(), "ESTOP");
  mock::inVal[PIN_ESTOP_OK] = LOW;
  // ENABLE 0 solo da fermo
  tick(5);
  CHECK_STR(cmd("RESET"), "OK RESET");
  CHECK_STR(cmd("ENABLE 0"), "OK ENABLE");
  CHECK(!motionEnabled());
  CHECK_STR(cmd("HOME"), "ERR E04 stato non consente");
  CHECK_STR(cmd("ENABLE 1"), "OK ENABLE");
}

struct CycleLog {
  std::vector<double> gaps;       // target gap ad ogni nuovo comando Z
  std::vector<double> xTargets;   // target X ad ogni nuovo comando X
  long lastZT = 0x7fffffff, lastXT = 0x7fffffff;
  void sample() {
    long zt = zTargetSteps(0), xt = xTargetSteps();
    if (zt != lastZT) { lastZT = zt; gaps.push_back(150.0 - zt / 200.0); }
    if (xt != lastXT) { lastXT = xt; xTargets.push_back(xt / 16.0); }
  }
};

static void testFullCycle() {
  g_test = "ciclo RUN completo";
  boot();
  CHECK(doHome());
  mock::serialOut.clear();
  g_events.clear();
  CycleLog lg;
  lg.lastZT = zTargetSteps(0);
  lg.lastXT = xTargetSteps();
  CHECK_STR(cmd("RUN"), "OK RUN np=14");
  collect();
  CHECK_STR(stName(), "RUNNING");
  int beeps = 0;
  uint8_t lastBz = 0;
  bool ok = runUntilCollect([&] {
    lg.sample();
    return machState() != ST_RUNNING;
  });
  CHECK(ok);
  CHECK_STR(stName(), "READY");
  // eventi
  std::string exp = "CYCLE_START|";
  for (int i = 1; i <= 14; i++) exp += "PASS " + std::to_string(i) + "/14|";
  exp += "CYCLE_DONE|";
  CHECK_STR(g_events, exp);
  // sequenza gap: sicuro 60, g0 40, poi G1..G14, fine g1+30
  const double expG[] = {60, 40, 37, 34, 31, 28, 25, 22, 19, 16, 13, 10, 7, 5, 35};
  // (le passate extra a 5 mm non cambiano il target Z)
  CHECK(lg.gaps.size() == sizeof(expG) / sizeof(expG[0]));
  for (size_t i = 0; i < lg.gaps.size() && i < 15; i++) CHECK_NEAR(lg.gaps[i], expG[i], 1e-3);
  // target X: start, poi 14 x (avanti, indietro), poi centro
  CHECK(lg.xTargets.size() == 1 + 28 + 1);
  if (lg.xTargets.size() == 30) {
    CHECK_NEAR(lg.xTargets[0], -210, 1e-3);          // cx - s0 - 60
    CHECK_NEAR(lg.xTargets[1], 210, 1e-3);           // cx + s0 + 60
    CHECK_NEAR(lg.xTargets[2], -210, 1e-3);
    CHECK_NEAR(lg.xTargets[27], 360, 1e-3);          // ultima passata s1 = 300
    CHECK_NEAR(lg.xTargets[28], -360, 1e-3);
    CHECK_NEAR(lg.xTargets[29], 0, 1e-3);            // rullo al centro
  }
  CHECK_NEAR(xPosMm(), 0.0, 1e-3);
  CHECK_NEAR(gapAvgMm(), 35.0, 1e-3);
  CHECK(cycleNp() == 14 && cyclePass() == 14);
  // buzzer: 3 bip
  for (int i = 0; i < 10000; i++) {
    tick();
    uint8_t b = mock::outVal[PIN_BUZZER];
    if (b && !lastBz) beeps++;
    lastBz = b;
  }
  CHECK(beeps == 3);
  // lampada verde fissa a READY
  CHECK(mock::outVal[PIN_LAMP_GREEN] == HIGH && mock::outVal[PIN_LAMP_YELLOW] == LOW);
  // START da pannello: RUN con gli ultimi parametri
  g_events.clear();
  mock::setPin(PIN_BTN_START, LOW);
  tickCollect(20);
  mock::setPin(PIN_BTN_START, HIGH);
  tickCollect(5);
  CHECK(g_events.find("CYCLE_START|") != std::string::npos);
  CHECK_STR(stName(), "RUNNING");
  CHECK(cycleNp() == 14);
}

static void testPause() {
  g_test = "PAUSE/RESUME";
  boot();
  CHECK(doHome());
  g_events.clear();
  mock::serialOut.clear();
  CHECK_STR(cmd("RUN g0=20 g1=10 dg=5 n=1 s0=100 s1=100"), "OK RUN np=3");
  collect();
  CHECK(runUntilCollect([] { return g_events.find("PASS 1/3") != std::string::npos; }));
  tickCollect(100);
  CHECK(xBusy());
  CHECK_STR(cmd("PAUSE"), "OK PAUSE");
  collect();
  CHECK_STR(stName(), "RUNNING");          // finisce il segmento corrente
  double target = xTargetSteps() / 16.0;
  CHECK(runUntilCollect([] { return machState() == ST_PAUSED; }));
  CHECK_NEAR(xPosMm(), target, 1e-3);       // fermo a fine segmento
  CHECK(g_events.find("PAUSED|") != std::string::npos);
  tick(1000);
  CHECK(!motionBusy());
  CHECK(mock::outVal[PIN_LAMP_YELLOW] == HIGH);
  CHECK_STR(cmd("RESUME"), "OK RESUME");
  CHECK_STR(stName(), "RUNNING");
  CHECK(runUntilCollect([] { return machState() != ST_RUNNING; }));
  CHECK_STR(stName(), "READY");
  CHECK(g_events.find("CYCLE_DONE|") != std::string::npos);
}

static void testCurtain() {
  g_test = "barriera";
  boot();
  CHECK(doHome());
  g_events.clear();
  mock::serialOut.clear();
  CHECK_STR(cmd("RUN g0=20 g1=10 dg=5 n=1 s0=100 s1=100"), "OK RUN np=3");
  collect();
  CHECK(runUntilCollect([] { return g_events.find("PASS 2/3") != std::string::npos; }));
  tickCollect(300);
  CHECK(xBusy());
  int stopsBefore = motX().stopCalls;
  mock::setPin(PIN_CURTAIN_OK, HIGH);
  tickCollect(1);
  CHECK_STR(stName(), "PAUSED");
  CHECK(motX().stopCalls == stopsBefore + 1);    // arresto rapido
  CHECK(g_events.find("CURTAIN|") != std::string::npos);
  tickCollect(50);
  CHECK(!motionBusy());
  long xStop = motX().currentPosition();
  CHECK_STR(cmd("RESUME"), "ERR E04 stato non consente");   // barriera ancora interrotta
  mock::setPin(PIN_CURTAIN_OK, LOW);
  tickCollect(20);
  CHECK(motX().currentPosition() == xStop);
  CHECK_STR(cmd("RESUME"), "OK RESUME");
  CHECK(runUntilCollect([] { return machState() != ST_RUNNING; }));
  CHECK_STR(stName(), "READY");
  CHECK(g_events.find("PASS 3/3|CYCLE_DONE|") != std::string::npos);
  CHECK_NEAR(xPosMm(), 0, 1e-3);
  CHECK_NEAR(gapAvgMm(), 40, 1e-3);
  // barriera durante MOVING manuale -> PAUSED, RESUME completa il movimento
  CHECK_STR(cmd("MOVE X 300"), "OK MOVE");
  tick(500);
  mock::setPin(PIN_CURTAIN_OK, HIGH);
  tick(50);
  CHECK_STR(stName(), "PAUSED");
  CHECK_STR(cmd("MOVE X 0"), "ERR E04 stato non consente");
  mock::setPin(PIN_CURTAIN_OK, LOW);
  tick(5);
  CHECK_STR(cmd("RESUME"), "OK RESUME");
  CHECK(runUntil([] { return machState() == ST_READY; }));
  CHECK_NEAR(xPosMm(), 300, 1e-3);
  // barriera interrotta a riposo: movimento rifiutato
  mock::setPin(PIN_CURTAIN_OK, HIGH);
  tick(5);
  CHECK_STR(cmd("RUN"), "ERR E04 stato non consente");
  mock::setPin(PIN_CURTAIN_OK, LOW);
}

static void testStop() {
  g_test = "STOP";
  boot();
  CHECK(doHome());
  g_events.clear();
  mock::serialOut.clear();
  CHECK_STR(cmd("RUN"), "OK RUN np=14");
  collect();
  CHECK(runUntilCollect([] { return g_events.find("PASS 2/14") != std::string::npos; }));
  tickCollect(200);
  double g = gapAvgMm();
  CHECK_STR(cmd("STOP"), "OK STOP");
  collect();
  CHECK(!cycleActive());
  CHECK(runUntilCollect([] { return machState() == ST_READY; }));
  CHECK(g_events.find("STOP|") != std::string::npos && g_events.find("STOPPED|") != std::string::npos);
  CHECK_NEAR(gapAvgMm(), g + SAFE_LIFT_MM, 1e-3);   // Z a gap sicuro
  CHECK(g_events.find("PASS 3/14") == std::string::npos);
  // BTN_STOP (NC: alto = premuto) durante il ciclo
  g_events.clear();
  CHECK_STR(cmd("RUN"), "OK RUN np=14");
  tickCollect(500);
  mock::setPin(PIN_BTN_STOP, HIGH);
  tickCollect(30);
  CHECK(g_events.find("BTN_STOP|STOP|") != std::string::npos);
  CHECK(runUntilCollect([] { return machState() == ST_READY; }));
  // con STOP premuto/filo rotto START e comandi di moto rifiutati
  CHECK_STR(cmd("RUN"), "ERR E04 stato non consente");
  mock::setPin(PIN_BTN_START, LOW);
  tickCollect(30);
  mock::setPin(PIN_BTN_START, HIGH);
  tickCollect(30);
  CHECK(g_events.find("ERR E04") != std::string::npos);
  CHECK_STR(stName(), "READY");
  mock::setPin(PIN_BTN_STOP, LOW);
  tick(30);
  CHECK_STR(cmd("GAP 100"), "OK GAP");
}

static void testAlarms() {
  g_test = "allarmi";
  boot();
  CHECK(doHome());
  g_events.clear();
  mock::serialOut.clear();
  mock::setPin(PIN_X_ALM, LOW);
  tickCollect(30);
  CHECK_STR(stName(), "ALARM");
  CHECK_STR(machAlarm(), "X_ALM");
  CHECK(g_events.find("ALARM X_ALM|") != std::string::npos);
  CHECK(!motionEnabled());
  CHECK(!machHomed());
  CHECK(mock::outVal[PIN_LAMP_RED] == HIGH);
  CHECK_STR(cmd("MOVE X 0"), "ERR E08 allarme driver");
  CHECK_STR(cmd("HOME"), "ERR E08 allarme driver");
  // RESET con allarme ancora presente -> di nuovo ALARM dopo il mascheramento
  CHECK_STR(cmd("RESET"), "OK RESET");
  CHECK_STR(stName(), "IDLE");
  tick(3000);
  CHECK_STR(stName(), "ALARM");
  mock::setPin(PIN_X_ALM, HIGH);
  tick(20);
  CHECK_STR(cmd("RESET"), "OK RESET");
  tick(3000);
  CHECK_STR(stName(), "IDLE");
  CHECK(doHome());

  // Extracorsa X_MAX in movimento verso +
  CHECK_STR(cmd("MOVE X 700"), "OK MOVE");
  tick(2000);
  mock::setPin(PIN_X_MAX, LOW);
  tick(20);
  CHECK_STR(stName(), "ALARM");
  CHECK_STR(machAlarm(), "X_MAX");
  CHECK(motionEnabled());
  CHECK_STR(cmd("MOVE X 0"), "ERR E04 stato non consente");
  CHECK_STR(cmd("RESET"), "OK RESET");
  CHECK_STR(stName(), "IDLE");
  CHECK_STR(cmd("JOG X 5"), "ERR E05 fuori limiti");     // verso il finecorsa: no
  CHECK_STR(cmd("JOG X -5"), "OK JOG");                   // allontanamento: si'
  CHECK(runUntil([] { return machState() == ST_IDLE; }));
  mock::setPin(PIN_X_MAX, HIGH);

  // Extracorsa Z1_LOW in discesa
  tick(20);
  CHECK(doHome());
  CHECK_STR(cmd("GAP 10"), "OK GAP");
  tick(3000);
  mock::setPin(PIN_Z1_LOW, LOW);
  tick(20);
  CHECK_STR(stName(), "ALARM");
  CHECK_STR(machAlarm(), "Z1_LOW");
  mock::setPin(PIN_Z1_LOW, HIGH);
  tick(10);
  CHECK_STR(cmd("RESET"), "OK RESET");

  // Portale tolto durante il movimento
  tick(20);
  CHECK(doHome());
  CHECK_STR(cmd("MOVE X 0"), "OK MOVE");
  tick(200);
  mock::setPin(PIN_SEAT_A, HIGH);
  tick(20);
  CHECK_STR(stName(), "ALARM");
  CHECK_STR(machAlarm(), "SEAT");
  mock::setPin(PIN_SEAT_A, LOW);
  tick(20);
  CHECK_STR(cmd("RESET"), "OK RESET");
  CHECK_STR(cmd("RESET"), "OK RESET");      // RESET senza allarmi: nessun effetto
  CHECK_STR(stName(), "IDLE");
}

static void testJson() {
  g_test = "JSON stato";
  boot();
  CHECK(doHome());
  char buf[400];
  uint16_t n = buildStateJson(buf, sizeof(buf));
  std::string s(buf);
  CHECK(n == s.size());
  std::string pre = "{\"st\":\"READY\",\"hm\":1,\"en\":1,\"x\":-700.00,\"g\":150.00,\"z1\":150.00,\"z2\":150.00,"
                    "\"r\":0.0,\"cyc\":{\"pass\":0,\"np\":0,\"gap\":0.0},\"in\":{\"xmin\":0,\"xmax\":0,\"z1h\":1,"
                    "\"z2h\":1,\"seat\":1,\"estop\":0,\"curt\":0},\"alm\":\"\",\"fw\":\"1.0.0\",\"up\":";
  CHECK_STR(s.substr(0, pre.size()), pre);
  CHECK(s.back() == '}');
  std::string up = s.substr(pre.size(), s.size() - pre.size() - 1);
  CHECK(!up.empty() && up.find_first_not_of("0123456789") == std::string::npos);
  CHECK(n < 300);   // entra nel buffer statico (320) e nel buffer MQTT (400)
  // in ESTOP
  mock::setPin(PIN_ESTOP_OK, HIGH);
  tick(30);
  buildStateJson(buf, sizeof(buf));
  s = buf;
  CHECK(s.find("\"st\":\"ESTOP\",\"hm\":0,\"en\":0") != std::string::npos);
  CHECK(s.find("\"estop\":1") != std::string::npos);
  CHECK(s.find("\"alm\":\"ESTOP\"") != std::string::npos);
}

static void testMqtt() {
  g_test = "MQTT";
  boot();
  PubSubClient &m = mq();
  CHECK(m.connectCalls >= 1);
  CHECK(m.connected());
  CHECK_STR(m.clientId, "manipmasta-024d4d000001");
  CHECK_STR(m.willTopic, "manipmasta/online");
  CHECK_STR(m.willMsg, "0");
  CHECK(m.willRetain);
  CHECK_STR(m.user, "manipmasta");
  CHECK(m.bufSize >= 300);
  bool online = false, state = false;
  for (auto &p : m.pubs) {
    if (p.topic == "manipmasta/online" && p.payload == "1" && p.retained) online = true;
    if (p.topic == "manipmasta/state" && p.retained && p.payload.rfind("{\"st\":", 0) == 0) state = true;
  }
  CHECK(online && state);
  CHECK(m.subs.size() == 1 && m.subs[0] == "manipmasta/cmd");
  // comando via MQTT -> risposta su manipmasta/resp
  m.pubs.clear();
  m.inject("ping");
  tick(5);
  bool resp = false;
  for (auto &p : m.pubs) if (p.topic == "manipmasta/resp" && p.payload == "OK PING") resp = true;
  CHECK(resp);
  m.pubs.clear();
  m.inject("HOME");
  m.inject("BOGUS");
  tick(5);
  int nresp = 0;
  bool evHoming = false;
  for (auto &p : m.pubs) {
    if (p.topic == "manipmasta/resp") nresp++;
    if (p.topic == "manipmasta/event" && p.payload == "HOMING") evHoming = true;
  }
  CHECK(nresp == 2 && evHoming);
  CHECK(runUntil([] { return machState() == ST_READY; }));
  // stato a riposo: ogni 2 s
  m.pubs.clear();
  tick(5 * 10000 / 2);                      // 5 s
  int ns = 0;
  for (auto &p : m.pubs) if (p.topic == "manipmasta/state") ns++;
  CHECK(ns >= 2 && ns <= 4);
  // in movimento: ogni 200 ms, rete servita con throttling 5 ms
  CHECK_STR(cmd("MOVE X 700 F 150"), "OK MOVE");
  m.pubs.clear();
  unsigned long mc = Ethernet.maintainCalls;
  unsigned long lc = m.loopCalls;
  tick(5000);                               // 1 s
  CHECK(machState() == ST_MOVING);
  ns = 0;
  for (auto &p : m.pubs) if (p.topic == "manipmasta/state") ns++;
  CHECK(ns >= 4 && ns <= 7);
  CHECK(Ethernet.maintainCalls - mc >= 150 && Ethernet.maintainCalls - mc <= 210);
  CHECK(m.loopCalls - lc <= 210);
  // broker perso durante il movimento: nessun tentativo finche' la macchina si muove
  m.conn = false;
  m.acceptConnect = false;
  int cc = m.connectCalls;
  tick(5000);
  CHECK(machState() == ST_MOVING);
  CHECK(m.connectCalls == cc);
  CHECK(runUntil([] { return machState() == ST_READY; }));
  // a riposo: tentativi con backoff (2, 4, 8, 16 s ...)
  cc = m.connectCalls;
  tick(5 * 1000 * 15);                      // 15 s
  int attempts = m.connectCalls - cc;
  CHECK(attempts >= 3 && attempts <= 4);
  m.acceptConnect = true;
  tick(5 * 1000 * 20);
  CHECK(m.connected());
  // link Ethernet giu': nessun connect
  m.conn = false;
  Ethernet.link = LinkOFF;
  cc = m.connectCalls;
  tick(5 * 1000 * 40);
  CHECK(m.connectCalls == cc);
  Ethernet.link = LinkON;
}

static void testWatchdogAndLamps() {
  g_test = "watchdog/lampade";
  boot();
  CHECK(g_mockWdtTimeout == WDTO_2S);
  unsigned long r = g_mockWdtResets;
  tick(10);
  CHECK(g_mockWdtResets - r >= 10);
  CHECK(mock::outVal[PIN_LAMP_YELLOW] == HIGH);     // IDLE
  CHECK(mock::outVal[PIN_LAMP_GREEN] == LOW);
  CHECK(mock::outVal[PIN_SD_CS] == HIGH);           // SD dello shield deselezionata
  CHECK(doHome());
  CHECK_STR(cmd("RUN"), "OK RUN np=14");
  int greenEdges = 0;
  uint8_t last = mock::outVal[PIN_LAMP_GREEN];
  for (int i = 0; i < 5 * 3000; i++) {             // 3 s
    tick();
    if (mock::outVal[PIN_LAMP_GREEN] != last) { greenEdges++; last = mock::outVal[PIN_LAMP_GREEN]; }
  }
  CHECK(greenEdges >= 4);                           // lampeggio verde in RUNNING
  CHECK(mock::outVal[PIN_LAMP_RED] == LOW);
}

int main() {
  testFmt();
  testParser();
  testParams();
  testCycleMath();
  testHoming();
  testLimits();
  testGearing();
  testEstop();
  testFullCycle();
  testPause();
  testCurtain();
  testStop();
  testAlarms();
  testJson();
  testMqtt();
  testWatchdogAndLamps();
  printf("\n%d controlli superati, %d falliti\n", g_pass, g_fail);
  return g_fail ? 1 : 0;
}
