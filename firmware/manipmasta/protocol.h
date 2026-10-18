// =====================================================================
// Protocollo comandi testuale (SPEC §3), identico su seriale e MQTT
// =====================================================================
#pragma once
#include <Arduino.h>
#include "net.h"

void protocolInit();
// Legge la seriale (non bloccante) e la coda MQTT, esegue i comandi completi
void protocolPoll();
// Esegue una riga di comando (la stringa viene modificata: tokenizzazione in place)
void protocolExecute(char *line, CmdSrc src);
// Invia "ERR Exx testo" sul canale indicato
void protocolReplyErr(CmdSrc src, uint8_t code);
