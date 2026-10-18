// Implementazione dei mock Arduino per i test host
#include "Arduino.h"
#include "mockctl.h"
#include "AccelStepper.h"
#include "EEPROM.h"
#include "Ethernet.h"
#include "PubSubClient.h"
#include "avr/wdt.h"

SerialMock Serial;
EEPROMClass EEPROM;
EthernetClass Ethernet;
PubSubClient *PubSubClient::instance = nullptr;
int AccelStepper::stepsPerRun = 1;
int AccelStepper::stopOvershoot = 3;
int g_mockWdtTimeout = -1;
unsigned long g_mockWdtResets = 0;

namespace mock {
uint8_t pinModes[80];
uint8_t outVal[80];
uint8_t inVal[80];
unsigned long long nowUs = 0;
std::string serialIn, serialOut;
size_t serialPos = 0;
long rPulses = 0, rPulsesNeg = 0, rPulsesPos = 0;
std::function<int(uint8_t, int)> inputHook;
static void (*isrs[2])() = {nullptr, nullptr};

void reset() {
  memset(pinModes, 0, sizeof(pinModes));
  memset(outVal, 0, sizeof(outVal));
  memset(inVal, 1, sizeof(inVal));
  nowUs = 1000000ULL;
  serialIn.clear(); serialOut.clear(); serialPos = 0;
  rPulses = rPulsesNeg = rPulsesPos = 0;
  inputHook = nullptr;
  isrs[0] = isrs[1] = nullptr;
  AccelStepper::stepsPerRun = 1;
  AccelStepper::stopOvershoot = 3;
}

void setPin(uint8_t pin, int v) {
  bool changed = inVal[pin] != (uint8_t)v;
  inVal[pin] = (uint8_t)v;
  int irq = digitalPinToInterrupt(pin);
  if (changed && irq >= 0 && isrs[irq]) isrs[irq]();
}
void advanceUs(unsigned long us) { nowUs += us; }
}  // namespace mock

void pinMode(uint8_t pin, uint8_t mode) { mock::pinModes[pin] = mode; }
void digitalWrite(uint8_t pin, uint8_t val) {
  if (pin == 34 && val == HIGH && mock::outVal[34] == LOW) {   // fronte PUL asse R
    if (mock::outVal[35]) { mock::rPulses++; mock::rPulsesPos++; }
    else { mock::rPulses--; mock::rPulsesNeg++; }
  }
  mock::outVal[pin] = val;
}
int digitalRead(uint8_t pin) {
  if (mock::pinModes[pin] == OUTPUT) return mock::outVal[pin];
  int v = mock::inVal[pin];
  if (mock::inputHook) v = mock::inputHook(pin, v);
  return v;
}
unsigned long millis() { return (unsigned long)(mock::nowUs / 1000ULL); }
unsigned long micros() { return (unsigned long)mock::nowUs; }
void delayMicroseconds(unsigned int us) { mock::nowUs += us; }
void delay(unsigned long ms) { mock::nowUs += ms * 1000ULL; }
void attachInterrupt(int irq, void (*isr)(), int) { if (irq >= 0 && irq < 2) mock::isrs[irq] = isr; }

int SerialMock::available() { return (int)(mock::serialIn.size() - mock::serialPos); }
int SerialMock::read() { return mock::serialPos < mock::serialIn.size() ? (unsigned char)mock::serialIn[mock::serialPos++] : -1; }
size_t SerialMock::print(const char *s) { mock::serialOut += s; return strlen(s); }
size_t SerialMock::print(long v) { mock::serialOut += std::to_string(v); return 1; }
size_t SerialMock::println(const char *s) { mock::serialOut += s; mock::serialOut += "\r\n"; return strlen(s) + 2; }
size_t SerialMock::println() { mock::serialOut += "\r\n"; return 2; }
