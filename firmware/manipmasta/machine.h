// =====================================================================
// Macchina a stati principale, supervisore di sicurezza, lampade/buzzer
// =====================================================================
#pragma once
#include <Arduino.h>
#include "cycle.h"

enum MachState : uint8_t {
  ST_BOOT, ST_IDLE, ST_HOMING, ST_READY, ST_MOVING, ST_RUNNING, ST_PAUSED, ST_ALARM, ST_ESTOP
};

// Codici errore protocollo (E01..E08)
enum ErrCode : uint8_t {
  E_OK = 0, E_UNKNOWN = 1, E_PARAM = 2, E_NOT_HOMED = 3, E_STATE = 4,
  E_LIMITS = 5, E_SEAT = 6, E_ESTOP = 7, E_DRIVER = 8
};

void mmSetup();
void mmLoop();

MachState machState();
void machStateName(MachState s, char *out, uint8_t cap);
bool machHomed();
const char *machAlarm();
bool machMoving();                 // stato con assi in movimento

// Azioni (ritornano ErrCode)
uint8_t machHome();
uint8_t machEnable(bool on);
uint8_t machJog(char axis, float mm);
uint8_t machMoveX(float mm, float f);
uint8_t machGap(float g);
uint8_t machRun(const RunParams &p, uint16_t *npOut);
uint8_t machRunLast(uint16_t *npOut);
uint8_t machPause();
uint8_t machResume();
uint8_t machStop();
uint8_t machReset();
uint8_t machParamsEditable();      // E_OK se si possono cambiare i parametri
void machInvalidateHoming();
void machRequestReboot();
bool machRebootRequested();
