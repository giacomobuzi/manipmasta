// =====================================================================
// ManipMasta - firmware Arduino Mega 2560 + Ethernet Shield 2 (W5500)
// Sfogliatrice/impastatrice a portale: X (traslazione), Z1/Z2 (gap),
// R (rotazione rullo asservita a X).
// Specifica vincolante: docs/SPEC.md
//
// Librerie: AccelStepper (waspinator), PubSubClient (knolleary),
//           Ethernet (arduino-libraries, >= 2.0.0)
//
// Tutta la logica e' nei moduli .cpp della cartella dello sketch:
//   config.h    pinout e costanti
//   params.*    parametri EEPROM (SET/GET/SAVE/DEFAULTS)
//   inputs.*    ingressi, debounce, interrupt ESTOP/barriera
//   motion.*    assi, gearing R, homing
//   cycle.*     ciclo RUN
//   machine.*   macchina a stati, sicurezza, lampade, setup/loop
//   protocol.*  parser comandi
//   net.*       Ethernet, MQTT, JSON di stato
// =====================================================================
#include <AccelStepper.h>
#include <SPI.h>
#include <Ethernet.h>
#include <PubSubClient.h>
#include <EEPROM.h>
#include "machine.h"

void setup() {
  mmSetup();
}

void loop() {
  mmLoop();     // non bloccante: i motori vengono serviti piu' volte per giro
}
