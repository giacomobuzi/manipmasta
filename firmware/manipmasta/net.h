// =====================================================================
// Rete: Ethernet W5500 + MQTT (PubSubClient), stato JSON, eventi
// =====================================================================
#pragma once
#include <Arduino.h>

enum CmdSrc : uint8_t { SRC_SERIAL, SRC_MQTT, SRC_LOCAL };

void netInit();
// moving = macchina in movimento (throttling e niente riconnessioni)
void netLoop(unsigned long nowMs, bool moving);
bool netMqttConnected();

// Uscite verso l'esterno
void netReply(CmdSrc src, const char *txt);     // risposta OK/ERR
void netEvent(const char *txt);                 // evento (seriale + MQTT)
void netRequestState();                         // pubblica lo stato al prossimo giro
void netPrintStateSerial();                     // stampa JSON su seriale (STATUS)

// Costruisce il JSON di stato in buf; ritorna la lunghezza
uint16_t buildStateJson(char *buf, uint16_t cap);

// Comando MQTT ricevuto in attesa di esecuzione (copiato dal callback)
bool netTakeCommand(char *out, uint8_t cap);
