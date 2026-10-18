// =====================================================================
// Movimento: X/Z1/Z2 con AccelStepper, R asservito a X (gearing
// elettronico, un passo per iterazione), homing non bloccante.
// Convenzioni:
//   X  : passi = mm * x_spm (0 = origine tavolo dopo homing)
//   Z  : passi = discesa dalla home (0 = finecorsa alto, + = verso il basso)
//        gap = z_home_gap - passi / z_spm
//   R  : passi = mm superficie * r_spm
// =====================================================================
#pragma once
#include <Arduino.h>
#include <AccelStepper.h>

enum HomingResult : uint8_t { HOMING_BUSY, HOMING_DONE, HOMING_FAIL };

void motionInit();
void motionApplyParams();          // inversione DIR, larghezza impulso
void motionRun();                  // da chiamare il piu' spesso possibile

// Abilitazione driver
void motionEnable(bool on);
bool motionEnabled();
unsigned long motionEnabledSince();
void motionDisableFromIsr();       // sicuro da ISR: solo scrittura pin ENA

// Arresti
void motionHardStop();             // immediato (emergenza / allarme driver)
void motionFastStop();             // decelerazione alta (barriera / extracorsa)
void motionStop();                 // decelerazione normale
void motionStopX();
void motionStopZ(uint8_t i);       // i = 0 (Z1) / 1 (Z2)

bool motionBusy();
bool xBusy();
bool zBusy();
bool rBusy();
int8_t xDir();                     // -1/0/+1 verso del moto X
int8_t zDir(uint8_t i);            // +1 = verso il basso

// Posizioni
float xPosMm();
float gapMm(uint8_t i);
float gapAvgMm();
float rPosMm();
long  rPosSteps();
float gapMaxEff();                 // min(g_max, z_home_gap)

// Comandi di movimento (nessun controllo limiti: li fa il chiamante)
void moveXTo(float mm, float speed, bool gear, float od);
void moveXRel(float mm, float speed, bool gear, float od);
void moveGapTo(float gap);
void moveGapRel(float dmm, float speedFactor);   // + = sale
void jogR(float mm);
void rCancel();
// Varianti a passi assoluti (ripresa di un movimento interrotto)
long xTargetSteps();
long zTargetSteps(uint8_t i);
long rTargetStepsJog();            // target del JOG R in corso (= posizione se nessun jog)
void moveXToSteps(long t, float speed, bool gear, float od);
void moveZToSteps(long t1, long t2, float speedFactor);
void jogRToSteps(long t);

// Homing
void homingStart();
HomingResult homingStep(unsigned long nowMs);
uint8_t homingFailAxis();          // 0 = Z1, 1 = Z2, 2 = X
void homingAbort();

// Accesso per i test host
AccelStepper &motX();
AccelStepper &motZ(uint8_t i);
