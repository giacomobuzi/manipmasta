// =====================================================================
// Ingressi: debounce, fronti pulsanti, interrupt ESTOP / barriera
// =====================================================================
#pragma once
#include <Arduino.h>

enum InputId : uint8_t {
  IN_X_ALM, IN_Z1_ALM, IN_Z2_ALM, IN_R_ALM,
  IN_X_MIN, IN_X_MAX, IN_Z1_HOME, IN_Z2_HOME, IN_Z1_LOW, IN_Z2_LOW,
  IN_SEAT_A, IN_SEAT_B, IN_BTN_START, IN_BTN_STOP,
  IN_ESTOP, IN_CURTAIN,
  IN_COUNT
};

// Flag impostati dalle ISR (consumati dal supervisore nel loop)
extern volatile bool g_estopIsr;
extern volatile bool g_curtainIsr;

void inputsInit();
// Campiona gli ingressi (debounce a 1 ms). Chiamare ad ogni loop.
void inputsScan(unsigned long nowMs);
// Stato filtrato "attivo" (allarme / finecorsa impegnato / in sede /
// pulsante premuto / emergenza / barriera interrotta)
bool inActive(InputId id);
// Lettura istantanea non filtrata (sicurezza / homing)
bool inRawActive(InputId id);
// Fronte di attivazione (consumato alla lettura)
bool inRoseEdge(InputId id);

inline bool estopActiveRaw() { return inRawActive(IN_ESTOP); }
inline bool curtainActiveRaw() { return inRawActive(IN_CURTAIN); }
inline bool seatOk() { return inActive(IN_SEAT_A) && inActive(IN_SEAT_B); }
