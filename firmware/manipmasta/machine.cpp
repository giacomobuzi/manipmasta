// =====================================================================
// Macchina a stati principale + supervisore sicurezza + segnalazioni
// =====================================================================
#include "machine.h"
#include "config.h"
#include "params.h"
#include "inputs.h"
#include "motion.h"
#include "cycle.h"
#include "net.h"
#include "protocol.h"
#include <avr/wdt.h>
#include <string.h>

static MachState st = ST_BOOT;
static bool homed = false;
static char alm[16] = "";
static bool almDriver = false;
static MachState pausedFrom = ST_RUNNING;
static unsigned long bootT = 0;
static RunParams lastRun;
static bool rebootReq = false;

// Movimento manuale (per la ripresa dopo barriera) e sequenza di STOP
static bool manual = false;
static long mvX, mvZ1, mvZ2, mvR;
static float mvSpeedX = 0, mvSpeedZ = 1.0f;
static uint8_t stopPhase = 0;            // 0 = no, 1 = decel. poi risalita, 2 = risalita Z, 3 = decel. senza risalita

// Segnalazioni
static uint8_t beepsLeft = 0;
static bool beepOn = false;
static unsigned long beepT = 0;
static unsigned long lampT = 0;

static const char ST_NAMES[] PROGMEM =
  "BOOT\0IDLE\0HOMING\0READY\0MOVING\0RUNNING\0PAUSED\0ALARM\0ESTOP\0";

void machStateName(MachState s, char *out, uint8_t cap) {
  PGM_P p = ST_NAMES;
  for (uint8_t i = 0; i < (uint8_t)s; i++) while (pgm_read_byte(p++)) {}
  strncpy_P(out, p, cap - 1);
  out[cap - 1] = 0;
}

MachState machState() { return st; }
bool machHomed() { return homed; }
const char *machAlarm() { return alm; }
bool machMoving() {
  return st == ST_HOMING || st == ST_MOVING || st == ST_RUNNING || motionBusy();
}
void machInvalidateHoming() {
  homed = false;
  if (st == ST_READY) st = ST_IDLE;
  netRequestState();
}
void machRequestReboot() { rebootReq = true; }
bool machRebootRequested() { return rebootReq; }

static void setState(MachState s) {
  if (st != s) { st = s; netRequestState(); }
}

static void eventP(PGM_P p) {
  char b[32];
  strncpy_P(b, p, sizeof(b) - 1);
  b[sizeof(b) - 1] = 0;
  netEvent(b);
}

// ---------------------------------------------------------------------
// Ingresso negli stati di sicurezza
// ---------------------------------------------------------------------
static void enterEstop() {
  motionDisableFromIsr();          // driver disabilitati (idempotente con la ISR)
  motionHardStop();                // stop immediato: nessun impulso residuo
  cycleCancel();
  homingAbort();
  manual = false; stopPhase = 0;
  homed = false;
  strcpy_P(alm, PSTR("ESTOP"));
  almDriver = false;
  setState(ST_ESTOP);
  eventP(PSTR("ESTOP"));
}

static void enterAlarm(PGM_P code, bool driver, bool hard) {
  if (st == ST_ESTOP || st == ST_ALARM) return;
  if (hard) motionHardStop(); else motionFastStop();
  if (driver) motionEnable(false);
  cycleCancel();
  homingAbort();
  manual = false; stopPhase = 0;
  homed = false;
  strncpy_P(alm, code, sizeof(alm) - 1);
  alm[sizeof(alm) - 1] = 0;
  almDriver = driver;
  setState(ST_ALARM);
  char b[24];
  snprintf_P(b, sizeof(b), PSTR("ALARM %s"), alm);
  netEvent(b);
}

static void finishMove() {
  bool wasStop = stopPhase != 0;
  stopPhase = 0;
  manual = false;
  setState(homed ? ST_READY : ST_IDLE);
  if (wasStop) eventP(PSTR("STOPPED"));
}

// ---------------------------------------------------------------------
// Supervisore: emergenza, allarmi, extracorsa, barriera, sede, pulsanti
// ---------------------------------------------------------------------
static void supervise(unsigned long now) {
  // 1) Emergenza (ISR + livello)
  bool estop = g_estopIsr || estopActiveRaw();
  g_estopIsr = false;
  if (estop) {
    if (st != ST_ESTOP) enterEstop();
    else if (motionEnabled()) motionDisableFromIsr();
  }
  if (st == ST_ESTOP) { g_curtainIsr = false; return; }

  // 2) Allarme driver (solo con driver abilitati, dopo il mascheramento)
  if (motionEnabled() && (now - motionEnabledSince()) > ALM_MASK_MS) {
    if (inActive(IN_X_ALM)) enterAlarm(PSTR("X_ALM"), true, true);
    else if (inActive(IN_Z1_ALM)) enterAlarm(PSTR("Z1_ALM"), true, true);
    else if (inActive(IN_Z2_ALM)) enterAlarm(PSTR("Z2_ALM"), true, true);
    else if (inActive(IN_R_ALM)) enterAlarm(PSTR("R_ALM"), true, true);
  }

  // 3) Extracorsa (solo se ci si muove verso il finecorsa)
  if (inActive(IN_X_MAX) && xDir() > 0) enterAlarm(PSTR("X_MAX"), false, false);
  if (inActive(IN_Z1_LOW) && zDir(0) > 0) enterAlarm(PSTR("Z1_LOW"), false, false);
  if (inActive(IN_Z2_LOW) && zDir(1) > 0) enterAlarm(PSTR("Z2_LOW"), false, false);
  if (st != ST_HOMING) {
    // X_MIN: con homing valido e' un'extracorsa (x_min e' x_home_off oltre),
    // senza homing (JOG di messa in servizio) ferma solo l'asse
    if (inActive(IN_X_MIN) && xDir() < 0) {
      if (homed) enterAlarm(PSTR("X_MIN"), false, false);
      else motionStopX();
    }
    // HOME Z: senza homing ferma il motore (con homing i limiti software
    // impediscono di superare la home)
    if (!homed) {
      if (inActive(IN_Z1_HOME) && zDir(0) < 0) motionStopZ(0);
      if (inActive(IN_Z2_HOME) && zDir(1) < 0) motionStopZ(1);
    }
  }

  // 4) Portale in sede
  if (!seatOk()) {
    if (st == ST_HOMING || st == ST_MOVING || st == ST_RUNNING) {
      enterAlarm(PSTR("SEAT"), false, false);
    } else if (homed) {
      homed = false;                 // portale tolto: quote non piu' garantite
      if (st == ST_READY) setState(ST_IDLE);
      eventP(PSTR("SEAT_LOST"));
    }
  }

  // 5) Barriera fotoelettrica
  bool curt = g_curtainIsr || curtainActiveRaw();
  g_curtainIsr = false;
  if (curt) {
    if (st == ST_RUNNING) {
      motionFastStop();
      cycleInterrupt();
      pausedFrom = ST_RUNNING;
      setState(ST_PAUSED);
      eventP(PSTR("CURTAIN"));
    } else if (st == ST_MOVING) {
      motionFastStop();
      if (stopPhase) {
        stopPhase = 3;               // arresto senza risalita (barriera)
      } else {
        pausedFrom = ST_MOVING;
        setState(ST_PAUSED);
      }
      eventP(PSTR("CURTAIN"));
    } else if (st == ST_HOMING) {
      motionFastStop();
      homingAbort();
      homed = false;
      manual = false;
      stopPhase = 3;
      setState(ST_MOVING);
      eventP(PSTR("CURTAIN"));
    }
  }

  // 6) Pulsanti pannello
  if (inRoseEdge(IN_BTN_STOP)) {
    eventP(PSTR("BTN_STOP"));
    machStop();
  }
  if (inRoseEdge(IN_BTN_START)) {
    uint8_t e;
    uint16_t np;
    if (st == ST_PAUSED) e = machResume();
    else if (st == ST_READY) e = machRunLast(&np);
    else e = E_STATE;
    if (e) protocolReplyErr(SRC_LOCAL, e);
  }
}

// ---------------------------------------------------------------------
// Avanzamento stati
// ---------------------------------------------------------------------
static void stepState(unsigned long now) {
  switch (st) {
    case ST_BOOT:
      if (now - bootT >= BOOT_SETTLE_MS) {
        motionEnable(true);
        setState(ST_IDLE);
        eventP(PSTR("BOOT"));
      }
      break;
    case ST_HOMING: {
      HomingResult r = homingStep(now);
      if (r == HOMING_DONE) {
        homed = true;
        setState(ST_READY);
        eventP(PSTR("HOMED"));
      } else if (r == HOMING_FAIL) {
        uint8_t a = homingFailAxis();
        enterAlarm(a == 2 ? PSTR("HOME_X") : (a == 1 ? PSTR("HOME_Z2") : PSTR("HOME_Z1")), false, true);
      }
      break;
    }
    case ST_RUNNING: {
      CycleResult r = cycleStep();
      if (r == CY_DONE) {
        setState(ST_READY);
        eventP(PSTR("CYCLE_DONE"));
        beepsLeft = 3; beepOn = false; beepT = now - BEEP_OFF_MS;
      } else if (r == CY_PAUSED) {
        pausedFrom = ST_RUNNING;
        setState(ST_PAUSED);
        eventP(PSTR("PAUSED"));
      }
      break;
    }
    case ST_MOVING:
      if (motionBusy()) break;
      if (stopPhase == 1) {
        if (homed && motionEnabled() && !curtainActiveRaw()) {
          float g = gapAvgMm() + SAFE_LIFT_MM;
          if (g > gapMaxEff()) g = gapMaxEff();
          moveGapTo(g);
          stopPhase = 2;
        } else {
          finishMove();
        }
      } else {
        finishMove();
      }
      break;
    default:
      break;
  }
}

// ---------------------------------------------------------------------
// Lampade e buzzer
// ---------------------------------------------------------------------
static void signals(unsigned long now) {
  if (now - lampT >= 20) {
    lampT = now;
    bool blink = ((now / BLINK_MS) & 1) != 0;
    bool g = (st == ST_READY) || ((st == ST_RUNNING || st == ST_MOVING || st == ST_HOMING) && blink);
    bool y = (st == ST_PAUSED || st == ST_IDLE || st == ST_BOOT);
    bool r = (st == ST_ALARM || st == ST_ESTOP);
    digitalWrite(PIN_LAMP_GREEN, g ? HIGH : LOW);
    digitalWrite(PIN_LAMP_YELLOW, y ? HIGH : LOW);
    digitalWrite(PIN_LAMP_RED, r ? HIGH : LOW);
  }
  if (beepsLeft) {
    if (beepOn && now - beepT >= BEEP_ON_MS) {
      beepOn = false; beepT = now; beepsLeft--;
      digitalWrite(PIN_BUZZER, LOW);
    } else if (!beepOn && now - beepT >= BEEP_OFF_MS) {
      beepOn = true; beepT = now;
      digitalWrite(PIN_BUZZER, HIGH);
    }
  } else if (beepOn) {
    beepOn = false;
    digitalWrite(PIN_BUZZER, LOW);
  }
}

// ---------------------------------------------------------------------
// Azioni
// ---------------------------------------------------------------------
static uint8_t canMove(bool needHomed) {
  if (st == ST_ESTOP || estopActiveRaw()) return E_ESTOP;
  if (st == ST_ALARM) return almDriver ? E_DRIVER : E_STATE;
  if (st != ST_IDLE && st != ST_READY) return E_STATE;
  if (!motionEnabled()) return E_STATE;
  if (!seatOk()) return E_SEAT;
  if (curtainActiveRaw() || inActive(IN_BTN_STOP)) return E_STATE;
  if (needHomed && !homed) return E_NOT_HOMED;
  return E_OK;
}

static void startManual() {
  manual = true;
  stopPhase = 0;
  mvX = xTargetSteps();
  mvZ1 = zTargetSteps(0);
  mvZ2 = zTargetSteps(1);
  mvR = rTargetStepsJog();
  setState(ST_MOVING);
}

uint8_t machHome() {
  uint8_t e = canMove(false);
  if (e) return e;
  homed = false;
  homingStart();
  setState(ST_HOMING);
  eventP(PSTR("HOMING"));
  return E_OK;
}

uint8_t machEnable(bool on) {
  if (on) {
    if (st == ST_ESTOP || estopActiveRaw()) return E_ESTOP;
    if (st == ST_ALARM) return almDriver ? E_DRIVER : E_STATE;
    if (st != ST_IDLE && st != ST_READY) return E_STATE;
    motionEnable(true);
  } else {
    if (motionBusy() || (st != ST_IDLE && st != ST_READY && st != ST_ALARM)) return E_STATE;
    motionEnable(false);
    // motori liberi: le quote non sono piu' garantite
    homed = false;
    if (st == ST_READY) setState(ST_IDLE);
  }
  netRequestState();
  return E_OK;
}

uint8_t machJog(char axis, float mm) {
  if (axis != 'X' && axis != 'G' && axis != 'R') return E_PARAM;
  if (mm < -5000.0f || mm > 5000.0f) return E_PARAM;
  uint8_t e = canMove(false);
  if (e) return e;
  float f = homed ? 1.0f : JOG_UNHOMED_FACTOR;
  if (axis == 'X') {
    if (mm > 0 && inActive(IN_X_MAX)) return E_LIMITS;
    if (mm < 0 && inActive(IN_X_MIN)) return E_LIMITS;
    if (homed) {
      float t = xPosMm() + mm;
      if (t < P.x_min - 0.001f || t > P.x_max + 0.001f) return E_LIMITS;
      moveXTo(t, P.x_vmax, true, P.od);
    } else {
      moveXRel(mm, P.x_vmax * f, true, P.od);
    }
    mvSpeedX = homed ? P.x_vmax : P.x_vmax * f;
  } else if (axis == 'G') {
    if (mm < 0 && (inActive(IN_Z1_LOW) || inActive(IN_Z2_LOW))) return E_LIMITS;
    if (homed) {
      float t = gapAvgMm() + mm;
      if (t < P.g_min - 0.001f || t > gapMaxEff() + 0.001f) return E_LIMITS;
      moveGapTo(t);
    } else {
      if (mm > 0 && (inActive(IN_Z1_HOME) || inActive(IN_Z2_HOME))) return E_LIMITS;
      moveGapRel(mm, f);
    }
    mvSpeedZ = f;
  } else {
    jogR(mm);
  }
  startManual();
  return E_OK;
}

uint8_t machMoveX(float mm, float f) {
  uint8_t e = canMove(true);
  if (e) return e;
  if (!(f > 0) || f > P.x_vmax) return E_PARAM;
  if (mm < P.x_min - 0.001f || mm > P.x_max + 0.001f) return E_LIMITS;
  moveXTo(mm, f, true, P.od);
  mvSpeedX = f;
  startManual();
  return E_OK;
}

uint8_t machGap(float g) {
  uint8_t e = canMove(true);
  if (e) return e;
  if (g < P.g_min - 0.001f || g > gapMaxEff() + 0.001f) return E_LIMITS;
  moveGapTo(g);
  mvSpeedZ = 1.0f;
  startManual();
  return E_OK;
}

uint8_t machRun(const RunParams &p, uint16_t *npOut) {
  uint8_t e = canMove(true);
  if (e) return e;
  e = cycleValidate(p, npOut);
  if (e) return e;
  lastRun = p;
  cycleStart(p);
  manual = false; stopPhase = 0;
  setState(ST_RUNNING);
  eventP(PSTR("CYCLE_START"));
  return E_OK;
}

uint8_t machRunLast(uint16_t *npOut) { return machRun(lastRun, npOut); }

uint8_t machPause() {
  if (st == ST_RUNNING) { cycleRequestPause(); return E_OK; }
  if (st == ST_PAUSED) return E_OK;
  return E_STATE;
}

uint8_t machResume() {
  if (st != ST_PAUSED) return E_STATE;
  if (estopActiveRaw()) return E_ESTOP;
  if (curtainActiveRaw() || inActive(IN_BTN_STOP) || motionBusy() || !motionEnabled()) return E_STATE;
  if (!seatOk()) return E_SEAT;
  if (pausedFrom == ST_RUNNING) {
    setState(ST_RUNNING);            // cycleStep riemette il segmento corrente
  } else {
    // ripresa del movimento manuale interrotto
    if (motX().currentPosition() != mvX) moveXToSteps(mvX, mvSpeedX, true, P.od);
    moveZToSteps(mvZ1, mvZ2, mvSpeedZ);
    if (mvR != rPosSteps()) jogRToSteps(mvR);
    setState(ST_MOVING);
  }
  eventP(PSTR("RESUME"));
  return E_OK;
}

uint8_t machStop() {
  switch (st) {
    case ST_RUNNING: case ST_PAUSED: case ST_MOVING: case ST_HOMING:
      if (st == ST_HOMING) { homingAbort(); homed = false; }
      cycleCancel();
      motionStop();
      manual = false;
      stopPhase = 1;
      setState(ST_MOVING);
      eventP(PSTR("STOP"));
      return E_OK;
    default:
      motionStop();                  // es. JOG R residuo
      return E_OK;
  }
}

uint8_t machReset() {
  if (st == ST_ESTOP || st == ST_ALARM) {
    if (estopActiveRaw()) return E_ESTOP;
    alm[0] = 0;
    almDriver = false;
    motionEnable(true);              // ENA ciclato: azzera l'allarme CL57T
    setState(ST_IDLE);
    eventP(PSTR("RESET"));
  }
  return E_OK;
}

uint8_t machParamsEditable() {
  if (machMoving() || st == ST_PAUSED) return E_STATE;
  return E_OK;
}

// ---------------------------------------------------------------------
// setup / loop
// ---------------------------------------------------------------------
void mmSetup() {
#ifndef MM_HOST_TEST
  MCUSR = 0;
  wdt_disable();
#endif
  pinMode(PIN_LAMP_GREEN, OUTPUT);  digitalWrite(PIN_LAMP_GREEN, LOW);
  pinMode(PIN_LAMP_YELLOW, OUTPUT); digitalWrite(PIN_LAMP_YELLOW, HIGH);
  pinMode(PIN_LAMP_RED, OUTPUT);    digitalWrite(PIN_LAMP_RED, LOW);
  pinMode(PIN_BUZZER, OUTPUT);      digitalWrite(PIN_BUZZER, LOW);

  Serial.begin(SERIAL_BAUD);
  Serial.println(F("ManipMasta fw " FW_VERSION));
  if (!paramsLoad()) Serial.println(F("EEPROM non valida: caricati i default (usare SAVE)"));

  st = ST_BOOT;
  homed = false;
  alm[0] = 0;
  almDriver = false;
  manual = false;
  stopPhase = 0;
  beepsLeft = 0; beepOn = false;
  rebootReq = false;

  motionInit();
  inputsInit();
  cycleInit();
  runDefaults(lastRun);
  protocolInit();
  netInit();
  bootT = millis();
  wdt_enable(WDTO_2S);
}

void mmLoop() {
  wdt_reset();
  unsigned long now = millis();
  motionRun();
  inputsScan(now);
  supervise(now);
  motionRun();
  stepState(now);
  motionRun();
  protocolPoll();
  motionRun();
  netLoop(now, machMoving());
  signals(now);
  if (rebootReq && !machMoving()) {
#ifndef MM_HOST_TEST
    Serial.flush();
    wdt_enable(WDTO_15MS);
    for (;;) {}
#endif
  }
}
