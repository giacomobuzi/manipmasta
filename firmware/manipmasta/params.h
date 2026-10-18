// =====================================================================
// Parametri runtime (SPEC §2.2) salvati in EEPROM con magic/versione/CRC
// =====================================================================
#pragma once
#include <Arduino.h>

#define PARAMS_MAGIC    0x4D4DU   // "MM"
#define PARAMS_VERSION  1
#define PARAMS_EE_ADDR  0

struct Params {
  uint16_t magic;
  uint8_t  version;
  // --- meccanica / movimento ---
  float x_spm, z_spm, r_spm;
  float x_min, x_max;
  float g_min, g_max;
  float z_home_gap;
  float x_vmax, x_acc;
  float z_vmax, z_acc;
  float x_home_off;
  float od;
  uint8_t dir_inv;           // bit0=X bit1=Z1 bit2=Z2 bit3=R (inverte DIR)
  // --- rete ---
  uint8_t mac[6];
  uint8_t ip[4], gw[4], mask[4], dns[4];
  char     mqtt_host[40];
  uint16_t mqtt_port;
  char     mqtt_user[24];
  char     mqtt_pass[32];
  uint16_t crc;
};

extern Params P;

void paramsDefaults(Params &p);
// Carica da EEPROM; ritorna false (e carica i default) se magic/versione/CRC non validi
bool paramsLoad();
void paramsSave();
uint16_t paramsCrc(const Params &p);

// SET/GET per chiave. Ritorna 0 se OK, altrimenti codice errore (2=E02).
// *motionChanged = true se e' cambiato un parametro che invalida l'homing.
uint8_t paramsSet(const char *key, const char *val, bool *homingLost);
// Scrive il valore in out (stringa). Ritorna 0 se OK, 2 se chiave sconosciuta.
uint8_t paramsGet(const char *key, char *out, uint8_t outLen);

// Utility di parsing/formattazione condivise
bool parseFloatStrict(const char *s, float *out);
bool parseLongStrict(const char *s, long *out);
bool parseIp(const char *s, uint8_t ip[4]);
bool parseMac(const char *s, uint8_t mac[6]);
// Formatta un float con 'dec' decimali senza %f (AVR). Ritorna lunghezza.
uint8_t fmtFixed(char *out, uint8_t outLen, float v, uint8_t dec);
