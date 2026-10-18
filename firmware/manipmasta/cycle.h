// =====================================================================
// Ciclo di sfogliatura RUN (SPEC §4) come macchina a stati non bloccante
// =====================================================================
#pragma once
#include <Arduino.h>

struct RunParams {
  float cx, s0, s1, g0, g1, dg, f, od;
  int16_t n;
};

enum CycleResult : uint8_t { CY_BUSY, CY_DONE, CY_PAUSED };

// --- Funzioni pure (testabili) ---
void runDefaults(RunParams &p);           // default SPEC + od da EEPROM
uint16_t cyclePassCount(const RunParams &p);          // np = ceil((g0-g1)/dg) + n
float cycleGapForPass(const RunParams &p, uint16_t k); // gap della passata avanti k (0-based)
float cycleSForPass(const RunParams &p, uint16_t k, uint16_t np);  // semicorsa s_k
// Validazione: 0 = OK, 2 = E02 parametro non valido, 5 = E05 fuori limiti
uint8_t cycleValidate(const RunParams &p, uint16_t *npOut);

// --- Macchina a stati ---
void cycleInit();
void cycleStart(const RunParams &p);
CycleResult cycleStep();                  // chiamare in stato RUNNING
void cycleRequestPause();
void cycleInterrupt();                    // arresto rapido: il segmento verra' riemesso
void cycleCancel();
bool cycleActive();

// Stato per JSON (pass 1-based, np, gap corrente del ciclo)
uint16_t cyclePass();
uint16_t cycleNp();
float cycleGap();
