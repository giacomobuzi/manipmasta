// =====================================================================
// Ciclo RUN (SPEC §4)
//
// Interpretazione adottata (coerente con np = ceil((g0-g1)/dg) + n):
//   G_0 = g0, G_{k+1} = max(g1, G_k - dg)
//   passata doppia k (k = 0..np-1):
//     avanti  fino a cx + s_k + 60 al gap G_k (R asservito)
//     a fine corsa (fuori impasto) Z va a G_{k+1}
//     indietro fino a cx - s_k - 60 al gap G_{k+1} (R asservito)
//   s_k = s0 + (s1 - s0) * k / (np - 1)
// Il gap raggiunge g1 dopo ceil((g0-g1)/dg) passate doppie; le ultime n
// passate doppie sono interamente al gap finale.
// =====================================================================
#include "cycle.h"
#include "config.h"
#include "params.h"
#include "motion.h"
#include "net.h"
#include <math.h>

enum CPhase : uint8_t {
  CP_NONE, CP_SAFE_UP, CP_TO_START, CP_GAP_G0, CP_FWD, CP_GAP_NEXT, CP_BACK,
  CP_END_UP, CP_END_CENTER
};

static RunParams cp;
static uint8_t phase = CP_NONE;
static bool segIssued = false;
static bool pauseReq = false;
static uint16_t passK = 0, np = 0;
static float curGap = 0;
static uint16_t passAnnounced = 0xFFFF;

void runDefaults(RunParams &p) {
  p.cx = RUN_DEF_CX; p.s0 = RUN_DEF_S0; p.s1 = RUN_DEF_S1;
  p.g0 = RUN_DEF_G0; p.g1 = RUN_DEF_G1; p.dg = RUN_DEF_DG;
  p.f = RUN_DEF_F; p.n = RUN_DEF_N; p.od = P.od;
}

// Numero di riduzioni necessarie per arrivare da g0 a g1
static uint16_t reductions(const RunParams &p) {
  float d = p.g0 - p.g1;
  if (d <= 0.0f) return 0;
  // tolleranza per errori di rappresentazione float (es. 0.9/0.3)
  float q = d / p.dg - 1e-4f;
  return (uint16_t)ceilf(q < 0 ? 0 : q);
}

uint16_t cyclePassCount(const RunParams &p) {
  return reductions(p) + (uint16_t)(p.n > 0 ? p.n : 0);
}

float cycleGapForPass(const RunParams &p, uint16_t k) {
  float g = p.g0 - p.dg * (float)k;
  return g < p.g1 ? p.g1 : g;
}

float cycleSForPass(const RunParams &p, uint16_t k, uint16_t n) {
  if (n <= 1) return p.s0;
  return p.s0 + (p.s1 - p.s0) * (float)k / (float)(n - 1);
}

static float safeGap(float g) { float m = gapMaxEff(); return g > m ? m : g; }

uint8_t cycleValidate(const RunParams &p, uint16_t *npOut) {
  if (p.n < 0 || p.s0 < 0 || p.s1 < 0) return 2;
  if (!(p.f > 0) || p.f > P.x_vmax) return 2;
  if (p.od < -10.0f || p.od > 20.0f) return 2;
  if (p.g0 < p.g1) return 2;
  if (p.g0 > p.g1 && !(p.dg > 0)) return 2;
  if (p.dg < 0) return 2;
  uint16_t n = cyclePassCount(p);
  if (n == 0 || n > RUN_MAX_PASSES) return 2;
  // limiti software
  if (p.g1 < P.g_min || p.g0 > gapMaxEff()) return 5;
  float smax = p.s0 > p.s1 ? p.s0 : p.s1;
  if (p.cx - smax - RUN_MARGIN_MM < P.x_min || p.cx + smax + RUN_MARGIN_MM > P.x_max) return 5;
  if (npOut) *npOut = n;
  return 0;
}

void cycleStart(const RunParams &p) {
  cp = p;
  np = cyclePassCount(p);
  passK = 0;
  curGap = p.g0;
  phase = CP_SAFE_UP;
  segIssued = false;
  pauseReq = false;
  passAnnounced = 0xFFFF;
}

static void issue() {
  float s = cycleSForPass(cp, passK, np);
  switch (phase) {
    case CP_SAFE_UP:    moveGapTo(safeGap(cp.g0 + RUN_SAFE_ABOVE)); break;
    case CP_TO_START:   moveXTo(cp.cx - cp.s0 - RUN_MARGIN_MM, P.x_vmax, false, 0); break;
    case CP_GAP_G0:     moveGapTo(cp.g0); curGap = cp.g0; break;
    case CP_FWD:
      if (passAnnounced != passK) {
        passAnnounced = passK;
        char b[20];
        snprintf_P(b, sizeof(b), PSTR("PASS %u/%u"), (unsigned)(passK + 1), (unsigned)np);
        netEvent(b);
      }
      moveXTo(cp.cx + s + RUN_MARGIN_MM, cp.f, true, cp.od);
      break;
    case CP_GAP_NEXT:   // nuovo gap applicato fuori impasto
      curGap = cycleGapForPass(cp, passK + 1);
      moveGapTo(curGap);
      break;
    case CP_BACK:       moveXTo(cp.cx - s - RUN_MARGIN_MM, cp.f, true, cp.od); break;
    case CP_END_UP:     moveGapTo(safeGap(cp.g1 + RUN_END_ABOVE)); break;
    case CP_END_CENTER: moveXTo(cp.cx, P.x_vmax, false, 0); break;
    default: break;
  }
  segIssued = true;
}

static void advance() {
  switch (phase) {
    case CP_SAFE_UP:  phase = CP_TO_START; break;
    case CP_TO_START: phase = CP_GAP_G0; break;
    case CP_GAP_G0:   phase = CP_FWD; break;
    case CP_FWD:      phase = CP_GAP_NEXT; break;
    case CP_GAP_NEXT: phase = CP_BACK; break;
    case CP_BACK:
      passK++;
      phase = (passK < np) ? CP_FWD : CP_END_UP;
      break;
    case CP_END_UP:     phase = CP_END_CENTER; break;
    case CP_END_CENTER: phase = CP_NONE; break;
    default: phase = CP_NONE; break;
  }
  segIssued = false;
}

CycleResult cycleStep() {
  if (phase == CP_NONE) return CY_DONE;
  if (!segIssued) { issue(); return CY_BUSY; }
  if (motionBusy()) return CY_BUSY;
  // segmento terminato
  advance();
  if (phase == CP_NONE) return CY_DONE;
  if (pauseReq) { pauseReq = false; return CY_PAUSED; }
  return CY_BUSY;
}

void cycleInit() { cycleCancel(); np = 0; passK = 0; curGap = 0; passAnnounced = 0xFFFF; }

void cycleRequestPause() { pauseReq = true; }
void cycleInterrupt() { segIssued = false; pauseReq = false; }
void cycleCancel() { phase = CP_NONE; segIssued = false; pauseReq = false; }
bool cycleActive() { return phase != CP_NONE; }

uint16_t cyclePass() {
  if (np == 0) return 0;
  uint16_t k = passK + 1;
  return k > np ? np : k;
}
uint16_t cycleNp() { return np; }
float cycleGap() { return curGap; }
