// =====================================================================
// Movimento assi + gearing R + homing (non bloccante)
// =====================================================================
#include "motion.h"
#include "config.h"
#include "params.h"
#include "inputs.h"
#include <math.h>

static void hStageReset();

static AccelStepper stX(AccelStepper::DRIVER, PIN_X_PUL, PIN_X_DIR);
static AccelStepper stZ1(AccelStepper::DRIVER, PIN_Z1_PUL, PIN_Z1_DIR);
static AccelStepper stZ2(AccelStepper::DRIVER, PIN_Z2_PUL, PIN_Z2_DIR);

AccelStepper &motX() { return stX; }
AccelStepper &motZ(uint8_t i) { return i ? stZ2 : stZ1; }

static volatile bool s_enabled = false;
static unsigned long s_enabledSince = 0;

// ---------------------------------------------------------------------
// Asse R: gearing elettronico su X
// ---------------------------------------------------------------------
enum RMode : uint8_t { R_NONE, R_GEAR, R_JOG };
static uint8_t rMode = R_NONE;
static long rPos = 0, rTarget = 0, rBase = 0, xBase = 0, lastXp = 0;
static float gearRatio = 0;
static bool rDirLevel = false, rInvert = false;
static unsigned long rLastStepUs = 0, rIntervalUs = 1000;

static void rPulse(int8_t dir) {
  bool lvl = (dir > 0) != rInvert;
  if (lvl != rDirLevel) {
    digitalWrite(PIN_R_DIR, lvl ? HIGH : LOW);
    rDirLevel = lvl;
    delayMicroseconds(R_DIR_SETUP_US);     // setup DIR prima del fronte PUL
  }
  digitalWrite(PIN_R_PUL, HIGH);
  delayMicroseconds(STEP_PULSE_US);        // impulso >= 5 us
  digitalWrite(PIN_R_PUL, LOW);
  rPos += dir;
}

static void rService() {
  if (!s_enabled) return;
  if (rMode == R_GEAR) {
    long xp = stX.currentPosition();
    if (xp != lastXp) {                    // ricalcolo solo se X e' cambiato
      lastXp = xp;
      rTarget = rBase + lround((float)(xp - xBase) * gearRatio);
    }
    if (rPos != rTarget) rPulse(rTarget > rPos ? 1 : -1);   // un passo per iterazione
  } else if (rMode == R_JOG) {
    if (rPos == rTarget) { rMode = R_NONE; return; }
    unsigned long now = micros();
    if (now - rLastStepUs >= rIntervalUs) {
      rLastStepUs = now;
      rPulse(rTarget > rPos ? 1 : -1);
    }
  }
}

void rCancel() { rTarget = rPos; rMode = R_NONE; }

// ---------------------------------------------------------------------
// Init / parametri
// ---------------------------------------------------------------------
static void writeEna(uint8_t lvl) {
  digitalWrite(PIN_X_ENA, lvl);
  digitalWrite(PIN_Z1_ENA, lvl);
  digitalWrite(PIN_Z2_ENA, lvl);
  digitalWrite(PIN_R_ENA, lvl);
}

void motionApplyParams() {
  stX.setPinsInverted(P.dir_inv & 1, false, false);
  stZ1.setPinsInverted(P.dir_inv & 2, false, false);
  stZ2.setPinsInverted(P.dir_inv & 4, false, false);
  rInvert = (P.dir_inv & 8) != 0;
  digitalWrite(PIN_R_DIR, rDirLevel != rInvert ? HIGH : LOW);
  stX.setMinPulseWidth(STEP_PULSE_US);
  stZ1.setMinPulseWidth(STEP_PULSE_US);
  stZ2.setMinPulseWidth(STEP_PULSE_US);
  stX.setMaxSpeed(P.x_vmax * P.x_spm);
  stX.setAcceleration(P.x_acc * P.x_spm);
  stZ1.setMaxSpeed(P.z_vmax * P.z_spm);
  stZ1.setAcceleration(P.z_acc * P.z_spm);
  stZ2.setMaxSpeed(P.z_vmax * P.z_spm);
  stZ2.setAcceleration(P.z_acc * P.z_spm);
}

void motionInit() {
  // ENA prima di tutto a "disabilitato"
  pinMode(PIN_X_ENA, OUTPUT); pinMode(PIN_Z1_ENA, OUTPUT);
  pinMode(PIN_Z2_ENA, OUTPUT); pinMode(PIN_R_ENA, OUTPUT);
  writeEna(ENA_INACTIVE_LEVEL);
  s_enabled = false;
  pinMode(PIN_R_PUL, OUTPUT); pinMode(PIN_R_DIR, OUTPUT);
  digitalWrite(PIN_R_PUL, LOW);
  rDirLevel = false;
  stX.setCurrentPosition(0);
  stZ1.setCurrentPosition(0);
  stZ2.setCurrentPosition(0);
  rPos = rTarget = rBase = xBase = lastXp = 0;
  rMode = R_NONE;
  hStageReset();
  motionApplyParams();
}

// ---------------------------------------------------------------------
// Abilitazione
// ---------------------------------------------------------------------
void motionEnable(bool on) {
  if (on) {
    writeEna(ENA_ACTIVE_LEVEL);
    if (!s_enabled) s_enabledSince = millis();
    s_enabled = true;
  } else {
    motionHardStop();
    writeEna(ENA_INACTIVE_LEVEL);
    s_enabled = false;
  }
}

bool motionEnabled() { return s_enabled; }
unsigned long motionEnabledSince() { return s_enabledSince; }

void motionDisableFromIsr() {
  writeEna(ENA_INACTIVE_LEVEL);
  s_enabled = false;
}

// ---------------------------------------------------------------------
// Arresti
// ---------------------------------------------------------------------
void motionHardStop() {
  // setCurrentPosition azzera velocita' e target: nessun altro impulso
  stX.setCurrentPosition(stX.currentPosition());
  stZ1.setCurrentPosition(stZ1.currentPosition());
  stZ2.setCurrentPosition(stZ2.currentPosition());
  rCancel();
}

void motionFastStop() {
  stX.setAcceleration(FAST_DECEL_X * P.x_spm);
  stZ1.setAcceleration(FAST_DECEL_Z * P.z_spm);
  stZ2.setAcceleration(FAST_DECEL_Z * P.z_spm);
  stX.stop(); stZ1.stop(); stZ2.stop();
  if (rMode == R_JOG) rCancel();           // in gearing R segue X in decelerazione
}

void motionStop() {
  stX.stop(); stZ1.stop(); stZ2.stop();
  if (rMode == R_JOG) rCancel();
}

void motionStopX() { stX.stop(); }
void motionStopZ(uint8_t i) { motZ(i).stop(); }

bool xBusy() { return stX.isRunning(); }
bool zBusy() { return stZ1.isRunning() || stZ2.isRunning(); }
bool rBusy() { return (rMode == R_GEAR && rPos != rTarget) || rMode == R_JOG; }
bool motionBusy() { return xBusy() || zBusy() || rBusy(); }

static int8_t dirOf(AccelStepper &s) {
  if (!s.isRunning()) return 0;
  long d = s.distanceToGo();
  if (d > 0) return 1;
  if (d < 0) return -1;
  return s.speed() > 0 ? 1 : (s.speed() < 0 ? -1 : 0);
}
int8_t xDir() { return dirOf(stX); }
int8_t zDir(uint8_t i) { return dirOf(motZ(i)); }

// ---------------------------------------------------------------------
// Posizioni
// ---------------------------------------------------------------------
float xPosMm() { return (float)stX.currentPosition() / P.x_spm; }
float gapMm(uint8_t i) { return P.z_home_gap - (float)motZ(i).currentPosition() / P.z_spm; }
float gapAvgMm() { return (gapMm(0) + gapMm(1)) * 0.5f; }
float rPosMm() { return (float)rPos / P.r_spm; }
long rPosSteps() { return rPos; }
float gapMaxEff() { return P.g_max < P.z_home_gap ? P.g_max : P.z_home_gap; }

// ---------------------------------------------------------------------
// Comandi di movimento
// ---------------------------------------------------------------------
static void engageGear(bool gear, float od) {
  if (gear) {
    rBase = (rMode == R_GEAR) ? rTarget : rPos;   // continuita' tra segmenti
    xBase = stX.currentPosition();
    lastXp = xBase;
    rTarget = rBase;
    gearRatio = P.r_spm / P.x_spm * (1.0f + od / 100.0f) * (float)R_GEAR_SIGN;
    rMode = R_GEAR;
  } else if (rMode == R_GEAR) {
    rCancel();
  }
}

void moveXToSteps(long t, float speed, bool gear, float od) {
  engageGear(gear, od);
  stX.setMaxSpeed(speed * P.x_spm);
  stX.setAcceleration(P.x_acc * P.x_spm);
  stX.moveTo(t);
}

void moveXTo(float mm, float speed, bool gear, float od) {
  moveXToSteps(lround(mm * P.x_spm), speed, gear, od);
}

long xTargetSteps() { return stX.targetPosition(); }
long zTargetSteps(uint8_t i) { return motZ(i).targetPosition(); }
long rTargetStepsJog() { return rMode == R_JOG ? rTarget : rPos; }

void moveXRel(float mm, float speed, bool gear, float od) {
  engageGear(gear, od);
  stX.setMaxSpeed(speed * P.x_spm);
  stX.setAcceleration(P.x_acc * P.x_spm);
  stX.moveTo(stX.currentPosition() + lround(mm * P.x_spm));
}

static void zSpeed(float factor) {
  for (uint8_t i = 0; i < 2; i++) {
    motZ(i).setMaxSpeed(P.z_vmax * factor * P.z_spm);
    motZ(i).setAcceleration(P.z_acc * P.z_spm);
  }
}

void moveGapTo(float gap) {
  zSpeed(1.0f);
  long t = lround((P.z_home_gap - gap) * P.z_spm);
  stZ1.moveTo(t);
  stZ2.moveTo(t);
}

void moveGapRel(float dmm, float speedFactor) {
  zSpeed(speedFactor);
  long d = lround(-dmm * P.z_spm);          // gap + = Z sale = passi -
  stZ1.moveTo(stZ1.currentPosition() + d);
  stZ2.moveTo(stZ2.currentPosition() + d);
}

void moveZToSteps(long t1, long t2, float speedFactor) {
  zSpeed(speedFactor);
  stZ1.moveTo(t1);
  stZ2.moveTo(t2);
}

void jogR(float mm) { jogRToSteps(rPos + lround(mm * P.r_spm)); }

void jogRToSteps(long t) {
  if (rMode == R_GEAR) rCancel();
  rTarget = t;
  float sps = R_JOG_SPEED * P.r_spm;
  rIntervalUs = (unsigned long)(1000000.0f / (sps > 1.0f ? sps : 1.0f));
  rLastStepUs = micros() - rIntervalUs;
  rMode = (rTarget != rPos) ? R_JOG : R_NONE;
}

void motionRun() {
  stX.run();
  stZ1.run();
  stZ2.run();
  rService();
}

// ---------------------------------------------------------------------
// Homing: Z1/Z2 indipendenti verso l'alto, poi X verso X_MIN.
// Ogni asse: veloce -> stop -> arretramento -> riavvicinamento lento.
// ---------------------------------------------------------------------
enum HPhase : uint8_t { HP_FAST, HP_STOPPING, HP_BACK, HP_WAIT_REL, HP_SLOW, HP_DONE };
enum HStage : uint8_t { HS_IDLE, HS_Z, HS_X, HS_X_POS, HS_DONE, HS_FAIL };

struct AxisHome {
  AccelStepper *st;
  InputId sw;
  int8_t towardSign;      // segno passi verso il finecorsa
  float spm, fast, slow, acc, searchMm;
  uint8_t ph;
  uint8_t retries;
  long trig;
  unsigned long t0;
};

static uint8_t hStage = HS_IDLE;
static uint8_t hFailAxis = 0;
static AxisHome hZ[2], hX;

static void axStart(AxisHome &a, AccelStepper *st, InputId sw, int8_t sign, float spm,
                    float fast, float slow, float acc, float searchMm, unsigned long now) {
  a.st = st; a.sw = sw; a.towardSign = sign; a.spm = spm;
  a.fast = fast; a.slow = slow; a.acc = acc; a.searchMm = searchMm;
  a.retries = 0;
  a.st->setCurrentPosition(0);
  a.st->setAcceleration(acc * spm);
  a.t0 = now;
  if (inActive(sw)) {                   // gia' sul finecorsa: salta la fase veloce
    a.trig = 0;
    a.ph = HP_STOPPING;
  } else {
    a.st->setMaxSpeed(fast * spm);
    a.st->moveTo(lround(sign * searchMm * spm));
    a.ph = HP_FAST;
  }
}

// Ritorna HOMING_BUSY / HOMING_DONE / HOMING_FAIL per il singolo asse
static uint8_t axStep(AxisHome &a, unsigned long now) {
  AccelStepper &s = *a.st;
  unsigned long el = now - a.t0;
  switch (a.ph) {
    case HP_FAST:
      if (inActive(a.sw)) { a.trig = s.currentPosition(); s.stop(); a.ph = HP_STOPPING; a.t0 = now; }
      else if (!s.isRunning() || el > (a.st == &stX ? HOME_X_FAST_TO_MS : HOME_Z_FAST_TO_MS)) return HOMING_FAIL;
      break;
    case HP_STOPPING:
      if (!s.isRunning()) {
        s.setMaxSpeed(a.fast * a.spm);
        s.moveTo(a.trig - lround(a.towardSign * HOME_BACKOFF_MM * a.spm));
        a.ph = HP_BACK; a.t0 = now;
      } else if (el > HOME_BACKOFF_TO_MS) return HOMING_FAIL;
      break;
    case HP_BACK:
      if (!s.isRunning()) { a.ph = HP_WAIT_REL; a.t0 = now; }
      else if (el > HOME_BACKOFF_TO_MS) return HOMING_FAIL;
      break;
    case HP_WAIT_REL:                     // attende il rilascio filtrato del finecorsa
      if (!inActive(a.sw)) {
        s.setMaxSpeed(a.slow * a.spm);
        s.moveTo(s.currentPosition() + lround(a.towardSign * (HOME_BACKOFF_MM * 3.0f) * a.spm));
        a.ph = HP_SLOW; a.t0 = now;
      } else if (el > 50) {
        // ancora impegnato (isteresi/oltrecorsa): arretra di nuovo, max 5 volte
        if (++a.retries > 5) return HOMING_FAIL;
        s.moveTo(s.currentPosition() - lround(a.towardSign * HOME_BACKOFF_MM * a.spm));
        a.ph = HP_BACK; a.t0 = now;
      }
      break;
    case HP_SLOW:
      if (inActive(a.sw)) { s.setCurrentPosition(0); a.ph = HP_DONE; return HOMING_DONE; }
      if (!s.isRunning() || el > HOME_SLOW_TO_MS) return HOMING_FAIL;
      break;
    case HP_DONE:
      return HOMING_DONE;
  }
  return HOMING_BUSY;
}

void homingStart() {
  unsigned long now = millis();
  rCancel();
  float zf = HOME_Z_FAST < P.z_vmax ? HOME_Z_FAST : P.z_vmax;
  float zs = HOME_Z_SLOW < zf ? HOME_Z_SLOW : zf;
  float zSearch = P.z_home_gap + HOME_Z_EXTRA_MM;
  axStart(hZ[0], &stZ1, IN_Z1_HOME, -1, P.z_spm, zf, zs, P.z_acc, zSearch, now);
  axStart(hZ[1], &stZ2, IN_Z2_HOME, -1, P.z_spm, zf, zs, P.z_acc, zSearch, now);
  hStage = HS_Z;
}

HomingResult homingStep(unsigned long now) {
  switch (hStage) {
    case HS_Z: {
      uint8_t r0 = axStep(hZ[0], now), r1 = axStep(hZ[1], now);
      if (r0 == HOMING_FAIL || r1 == HOMING_FAIL) {
        hFailAxis = (r0 == HOMING_FAIL) ? 0 : 1;
        motionHardStop(); hStage = HS_FAIL; return HOMING_FAIL;
      }
      if (r0 == HOMING_DONE && r1 == HOMING_DONE) {
        // Z in home: gap = z_home_gap (posizione 0)
        float xf = HOME_X_FAST < P.x_vmax ? HOME_X_FAST : P.x_vmax;
        float xs = HOME_X_SLOW < xf ? HOME_X_SLOW : xf;
        axStart(hX, &stX, IN_X_MIN, -1, P.x_spm, xf, xs, P.x_acc,
                (P.x_max - P.x_min) + P.x_home_off + HOME_X_EXTRA_MM, now);
        hStage = HS_X;
      }
      return HOMING_BUSY;
    }
    case HS_X: {
      uint8_t r = axStep(hX, now);
      if (r == HOMING_FAIL) { hFailAxis = 2; motionHardStop(); hStage = HS_FAIL; return HOMING_FAIL; }
      if (r == HOMING_DONE) {
        // finecorsa X_MIN = x_min - x_home_off, poi si porta a x_min
        stX.setCurrentPosition(lround((P.x_min - P.x_home_off) * P.x_spm));
        stX.setMaxSpeed(P.x_vmax * P.x_spm);
        stX.setAcceleration(P.x_acc * P.x_spm);
        stX.moveTo(lround(P.x_min * P.x_spm));
        hX.t0 = now;
        hStage = HS_X_POS;
      }
      return HOMING_BUSY;
    }
    case HS_X_POS:
      if (!stX.isRunning()) { hStage = HS_DONE; return HOMING_DONE; }
      if (now - hX.t0 > HOME_POS_TO_MS) { hFailAxis = 2; motionHardStop(); hStage = HS_FAIL; return HOMING_FAIL; }
      return HOMING_BUSY;
    case HS_DONE: return HOMING_DONE;
    default: return HOMING_FAIL;
  }
}

static void hStageReset() { hStage = HS_IDLE; hFailAxis = 0; }
uint8_t homingFailAxis() { return hFailAxis; }
void homingAbort() { hStage = HS_IDLE; }
