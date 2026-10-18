// =====================================================================
// Ingressi: tabella pin, debounce a integratore, ISR di sicurezza
// =====================================================================
#include "inputs.h"
#include "config.h"
#include "motion.h"

volatile bool g_estopIsr = false;
volatile bool g_curtainIsr = false;

struct InDef { uint8_t pin; uint8_t activeHigh; };

// Ordine = enum InputId
static const InDef IN_DEFS[IN_COUNT] PROGMEM = {
  {PIN_X_ALM, 0}, {PIN_Z1_ALM, 0}, {PIN_Z2_ALM, 0}, {PIN_R_ALM, 0},
  {PIN_X_MIN, 0}, {PIN_X_MAX, 0}, {PIN_Z1_HOME, 0}, {PIN_Z2_HOME, 0},
  {PIN_Z1_LOW, 0}, {PIN_Z2_LOW, 0},
  {PIN_SEAT_A, 0}, {PIN_SEAT_B, 0},
  {PIN_BTN_START, 0},
  {PIN_BTN_STOP, 1},     // NC: ALTO = premuto
  {PIN_ESTOP_OK, 1},     // ALTO = emergenza
  {PIN_CURTAIN_OK, 1},   // ALTO = barriera interrotta
};

static uint8_t s_cnt[IN_COUNT];      // integratore debounce
static uint32_t s_state;             // bit = stato filtrato attivo
static uint32_t s_edges;             // bit = fronte di attivazione pendente
static unsigned long s_lastScan;

static inline uint8_t defPin(uint8_t i) { return pgm_read_byte(&IN_DEFS[i].pin); }
static inline uint8_t defHigh(uint8_t i) { return pgm_read_byte(&IN_DEFS[i].activeHigh); }

bool inRawActive(InputId id) {
  uint8_t v = digitalRead(defPin(id)) == HIGH ? 1 : 0;
  return v == defHigh(id);
}

// ISR emergenza: disabilita SUBITO i driver (opto ENA), poi il loop gestisce lo stato
static void isrEstop() {
  if (digitalRead(PIN_ESTOP_OK) == HIGH) {
    motionDisableFromIsr();
    g_estopIsr = true;
  }
}

static void isrCurtain() {
  if (digitalRead(PIN_CURTAIN_OK) == HIGH) g_curtainIsr = true;
}

void inputsInit() {
  for (uint8_t i = 0; i < IN_COUNT; i++) pinMode(defPin(i), INPUT_PULLUP);
  s_edges = 0;
  s_state = 0;
  for (uint8_t i = 0; i < IN_COUNT; i++) {
    bool a = inRawActive((InputId)i);
    s_cnt[i] = a ? INPUT_DEBOUNCE_MS : 0;
    if (a) s_state |= (1UL << i);
  }
  s_lastScan = millis();
  g_estopIsr = false;
  g_curtainIsr = false;
  attachInterrupt(digitalPinToInterrupt(PIN_ESTOP_OK), isrEstop, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_CURTAIN_OK), isrCurtain, CHANGE);
}

void inputsScan(unsigned long nowMs) {
  if (nowMs == s_lastScan) return;
  s_lastScan = nowMs;
  for (uint8_t i = 0; i < IN_COUNT; i++) {
    bool a = inRawActive((InputId)i);
    uint32_t bit = 1UL << i;
    if (a) {
      if (s_cnt[i] < INPUT_DEBOUNCE_MS) s_cnt[i]++;
      if (s_cnt[i] >= INPUT_DEBOUNCE_MS && !(s_state & bit)) { s_state |= bit; s_edges |= bit; }
    } else {
      if (s_cnt[i] > 0) s_cnt[i]--;
      if (s_cnt[i] == 0) s_state &= ~bit;
    }
  }
}

bool inActive(InputId id) { return (s_state >> id) & 1UL; }

bool inRoseEdge(InputId id) {
  uint32_t bit = 1UL << id;
  if (s_edges & bit) { s_edges &= ~bit; return true; }
  return false;
}
