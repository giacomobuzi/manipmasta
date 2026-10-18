// =====================================================================
// Parametri EEPROM: default, load/save con CRC16, SET/GET per chiave
// =====================================================================
#include "params.h"
#include "config.h"
#include <EEPROM.h>
#include <string.h>
#include <stddef.h>
#include <stdlib.h>
#include <math.h>

Params P;

// ---------------------------------------------------------------------
// Default SPEC §2.2
// ---------------------------------------------------------------------
void paramsDefaults(Params &p) {
  memset(&p, 0, sizeof(p));
  p.magic = PARAMS_MAGIC;
  p.version = PARAMS_VERSION;
  p.x_spm = 16.0f;  p.z_spm = 200.0f;  p.r_spm = 5.093f;
  p.x_min = -700.0f; p.x_max = 700.0f;
  p.g_min = 0.5f;   p.g_max = 150.0f;
  p.z_home_gap = 150.0f;
  p.x_vmax = 150.0f; p.x_acc = 300.0f;
  p.z_vmax = 8.0f;   p.z_acc = 20.0f;
  p.x_home_off = 20.0f;
  p.od = 2.0f;
  p.dir_inv = 0;
  // MAC "locally administered" (lo shield 2 riporta il MAC su etichetta: impostarlo con SET mac)
  const uint8_t mac[6] = {0x02, 0x4D, 0x4D, 0x00, 0x00, 0x01};
  memcpy(p.mac, mac, 6);
  const uint8_t ip[4] = {192, 168, 50, 60};
  const uint8_t gw[4] = {192, 168, 50, 1};
  const uint8_t mk[4] = {255, 255, 255, 0};
  memcpy(p.ip, ip, 4); memcpy(p.gw, gw, 4); memcpy(p.mask, mk, 4); memcpy(p.dns, gw, 4);
  strcpy_P(p.mqtt_host, PSTR("192.168.50.10"));
  p.mqtt_port = 1883;
  strcpy_P(p.mqtt_user, PSTR("manipmasta"));
  p.mqtt_pass[0] = 0;          // "(impostare)" via SET mqtt_pass
  p.crc = paramsCrc(p);
}

// CRC16-CCITT su tutta la struttura escluso il campo crc
uint16_t paramsCrc(const Params &p) {
  const uint8_t *b = (const uint8_t *)&p;
  uint16_t n = (uint16_t)offsetof(Params, crc);
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < n; i++) {
    crc ^= (uint16_t)b[i] << 8;
    for (uint8_t k = 0; k < 8; k++)
      crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  }
  return crc;
}

bool paramsLoad() {
  Params tmp;
  EEPROM.get(PARAMS_EE_ADDR, tmp);
  if (tmp.magic == PARAMS_MAGIC && tmp.version == PARAMS_VERSION && tmp.crc == paramsCrc(tmp)) {
    // stringhe sempre terminate
    tmp.mqtt_host[sizeof(tmp.mqtt_host) - 1] = 0;
    tmp.mqtt_user[sizeof(tmp.mqtt_user) - 1] = 0;
    tmp.mqtt_pass[sizeof(tmp.mqtt_pass) - 1] = 0;
    P = tmp;
    return true;
  }
  paramsDefaults(P);
  return false;
}

void paramsSave() {
  P.magic = PARAMS_MAGIC;
  P.version = PARAMS_VERSION;
  P.crc = paramsCrc(P);
  EEPROM.put(PARAMS_EE_ADDR, P);   // put() usa update(): scrive solo i byte cambiati
}

// ---------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------
bool parseFloatStrict(const char *s, float *out) {
  if (!s || !*s) return false;
  char *end;
  double v = strtod(s, &end);
  if (end == s || *end != 0) return false;
  if (isnan(v) || isinf(v)) return false;
  *out = (float)v;
  return true;
}

bool parseLongStrict(const char *s, long *out) {
  if (!s || !*s) return false;
  char *end;
  long v = strtol(s, &end, 10);
  if (end == s || *end != 0) return false;
  *out = v;
  return true;
}

bool parseIp(const char *s, uint8_t ip[4]) {
  uint8_t tmp[4];
  for (uint8_t i = 0; i < 4; i++) {
    if (*s < '0' || *s > '9') return false;
    uint16_t v = 0; uint8_t nd = 0;
    while (*s >= '0' && *s <= '9') { v = v * 10 + (*s - '0'); s++; if (++nd > 3) return false; }
    if (v > 255) return false;
    tmp[i] = (uint8_t)v;
    if (i < 3) { if (*s != '.') return false; s++; }
  }
  if (*s != 0) return false;
  memcpy(ip, tmp, 4);
  return true;
}

static int8_t hexVal(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

bool parseMac(const char *s, uint8_t mac[6]) {
  uint8_t tmp[6];
  for (uint8_t i = 0; i < 6; i++) {
    int8_t h = hexVal(s[0]), l = hexVal(s[1]);
    if (h < 0 || l < 0) return false;
    tmp[i] = (uint8_t)((h << 4) | l);
    s += 2;
    if (i < 5) { if (*s != ':' && *s != '-') return false; s++; }
  }
  if (*s != 0) return false;
  memcpy(mac, tmp, 6);
  return true;
}

// Formattazione a virgola fissa senza printf("%f") (non supportato su AVR)
uint8_t fmtFixed(char *out, uint8_t outLen, float v, uint8_t dec) {
  long scale = 1;
  for (uint8_t i = 0; i < dec; i++) scale *= 10;
  bool neg = v < 0;
  if (neg) v = -v;
  if (v > 2.0e9f / scale) v = 2.0e9f / scale;   // saturazione anti-overflow
  long q = (long)(v * scale + 0.5f);
  if (q == 0) neg = false;                       // niente "-0.00"
  long ip = q / scale, fp = q % scale;
  char tmp[24];
  uint8_t n = 0;
  // parte frazionaria (al contrario)
  for (uint8_t i = 0; i < dec; i++) { tmp[n++] = (char)('0' + fp % 10); fp /= 10; }
  if (dec) tmp[n++] = '.';
  do { tmp[n++] = (char)('0' + ip % 10); ip /= 10; } while (ip && n < sizeof(tmp) - 2);
  if (neg) tmp[n++] = '-';
  uint8_t len = 0;
  while (n && len < outLen - 1) out[len++] = tmp[--n];
  out[len] = 0;
  return len;
}

// ---------------------------------------------------------------------
// Tabella chiavi (PROGMEM)
// ---------------------------------------------------------------------
enum PType : uint8_t { PT_FLOAT, PT_U8, PT_U16, PT_IP, PT_MAC, PT_STR };
enum PFlag : uint8_t { PF_NONE = 0, PF_HOMING = 1, PF_SECRET = 2 };

struct PDesc {
  char     name[12];
  uint8_t  type;
  uint8_t  flags;
  uint8_t  offset;
  uint8_t  size;   // per stringhe
  float    vmin, vmax;
};

#define PD_F(n, f, lo, hi, fl) { n, PT_FLOAT, fl, (uint8_t)offsetof(Params, f), 4, lo, hi }

static const PDesc PDESC[] PROGMEM = {
  PD_F("x_spm", x_spm, 0.1f, 10000.0f, PF_HOMING),
  PD_F("z_spm", z_spm, 0.1f, 10000.0f, PF_HOMING),
  PD_F("r_spm", r_spm, 0.01f, 10000.0f, PF_NONE),
  PD_F("x_min", x_min, -2000.0f, 2000.0f, PF_NONE),
  PD_F("x_max", x_max, -2000.0f, 2000.0f, PF_NONE),
  PD_F("g_min", g_min, 0.0f, 400.0f, PF_NONE),
  PD_F("g_max", g_max, 0.0f, 400.0f, PF_NONE),
  PD_F("z_home_gap", z_home_gap, 1.0f, 400.0f, PF_HOMING),
  PD_F("x_vmax", x_vmax, 1.0f, 1000.0f, PF_NONE),
  PD_F("x_acc", x_acc, 1.0f, 10000.0f, PF_NONE),
  PD_F("z_vmax", z_vmax, 0.1f, 50.0f, PF_NONE),
  PD_F("z_acc", z_acc, 0.1f, 1000.0f, PF_NONE),
  PD_F("x_home_off", x_home_off, 0.0f, 200.0f, PF_HOMING),
  PD_F("od", od, -10.0f, 20.0f, PF_NONE),
  { "dir_inv", PT_U8, PF_HOMING, (uint8_t)offsetof(Params, dir_inv), 1, 0, 15 },
  { "mac", PT_MAC, PF_NONE, (uint8_t)offsetof(Params, mac), 6, 0, 0 },
  { "ip", PT_IP, PF_NONE, (uint8_t)offsetof(Params, ip), 4, 0, 0 },
  { "gw", PT_IP, PF_NONE, (uint8_t)offsetof(Params, gw), 4, 0, 0 },
  { "mask", PT_IP, PF_NONE, (uint8_t)offsetof(Params, mask), 4, 0, 0 },
  { "dns", PT_IP, PF_NONE, (uint8_t)offsetof(Params, dns), 4, 0, 0 },
  { "mqtt_host", PT_STR, PF_NONE, (uint8_t)offsetof(Params, mqtt_host), sizeof(((Params *)0)->mqtt_host), 0, 0 },
  { "mqtt_port", PT_U16, PF_NONE, (uint8_t)offsetof(Params, mqtt_port), 2, 1, 65535 },
  { "mqtt_user", PT_STR, PF_NONE, (uint8_t)offsetof(Params, mqtt_user), sizeof(((Params *)0)->mqtt_user), 0, 0 },
  { "mqtt_pass", PT_STR, PF_SECRET, (uint8_t)offsetof(Params, mqtt_pass), sizeof(((Params *)0)->mqtt_pass), 0, 0 },
};
#define PDESC_COUNT (sizeof(PDESC) / sizeof(PDESC[0]))

static bool findDesc(const char *key, PDesc *d) {
  for (uint8_t i = 0; i < PDESC_COUNT; i++) {
    memcpy_P(d, &PDESC[i], sizeof(PDesc));
    if (strcasecmp(key, d->name) == 0) return true;
  }
  return false;
}

// Coerenza incrociata dopo un SET
static bool crossCheck(const Params &p) {
  if (!(p.x_min < p.x_max)) return false;
  if (!(p.g_min < p.g_max)) return false;
  if (p.g_min > p.z_home_gap) return false;
  if (p.mqtt_port == 0) return false;
  return true;
}

uint8_t paramsSet(const char *key, const char *val, bool *homingLost) {
  PDesc d;
  if (!key || !val || !findDesc(key, &d)) return 2;
  Params tmp = P;
  uint8_t *base = (uint8_t *)&tmp + d.offset;
  switch (d.type) {
    case PT_FLOAT: {
      float f;
      if (!parseFloatStrict(val, &f) || f < d.vmin || f > d.vmax) return 2;
      memcpy(base, &f, 4);
      break;
    }
    case PT_U8:
    case PT_U16: {
      long l;
      if (!parseLongStrict(val, &l) || l < (long)d.vmin || l > (long)d.vmax) return 2;
      if (d.type == PT_U8) *base = (uint8_t)l;
      else { uint16_t u = (uint16_t)l; memcpy(base, &u, 2); }
      break;
    }
    case PT_IP:
      if (!parseIp(val, base)) return 2;
      break;
    case PT_MAC:
      if (!parseMac(val, base)) return 2;
      break;
    case PT_STR: {
      size_t n = strlen(val);
      if (n >= d.size) return 2;
      // "-" = stringa vuota (es. mqtt_user anonimo)
      if (n == 1 && val[0] == '-') n = 0;
      memset(base, 0, d.size);
      memcpy(base, val, n);
      break;
    }
  }
  if (!crossCheck(tmp)) return 2;
  bool changed = memcmp(&tmp, &P, sizeof(Params)) != 0;
  if (homingLost) *homingLost = changed && (d.flags & PF_HOMING);
  P = tmp;
  return 0;
}

uint8_t paramsGet(const char *key, char *out, uint8_t outLen) {
  PDesc d;
  if (!key || !findDesc(key, &d) || outLen < 20) return 2;
  const uint8_t *base = (const uint8_t *)&P + d.offset;
  switch (d.type) {
    case PT_FLOAT: { float f; memcpy(&f, base, 4); fmtFixed(out, outLen, f, 3); break; }
    case PT_U8: snprintf_P(out, outLen, PSTR("%u"), (unsigned)*base); break;
    case PT_U16: { uint16_t u; memcpy(&u, base, 2); snprintf_P(out, outLen, PSTR("%u"), (unsigned)u); break; }
    case PT_IP: snprintf_P(out, outLen, PSTR("%u.%u.%u.%u"), base[0], base[1], base[2], base[3]); break;
    case PT_MAC:
      snprintf_P(out, outLen, PSTR("%02X:%02X:%02X:%02X:%02X:%02X"),
                 base[0], base[1], base[2], base[3], base[4], base[5]);
      break;
    case PT_STR:
      if (d.flags & PF_SECRET) strcpy_P(out, ((const char *)base)[0] ? PSTR("***") : PSTR("(vuota)"));
      else { strncpy(out, (const char *)base, outLen - 1); out[outLen - 1] = 0; }
      break;
  }
  return 0;
}
