// API di controllo dei mock (solo test)
#pragma once
#include <stdint.h>
#include <string>
#include <functional>
namespace mock {
extern uint8_t pinModes[80];
extern uint8_t outVal[80];
extern uint8_t inVal[80];
extern unsigned long long nowUs;
extern std::string serialIn, serialOut;
extern size_t serialPos;
extern long rPulses, rPulsesNeg, rPulsesPos;
extern std::function<int(uint8_t, int)> inputHook;
void reset();
void setPin(uint8_t pin, int v);   // imposta un ingresso (scatena l'ISR se presente)
void advanceUs(unsigned long us);
}
