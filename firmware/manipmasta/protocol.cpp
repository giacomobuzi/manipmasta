// =====================================================================
// Parser ed esecuzione comandi. Nessuna String dinamica: buffer statici,
// testi costanti in PROGMEM.
// =====================================================================
#include "protocol.h"
#include "config.h"
#include "params.h"
#include "machine.h"
#include "motion.h"
#include "cycle.h"
#include <string.h>
#include <ctype.h>

#define MAX_TOK 12

static char s_line[CMD_MAX_LEN];
static uint8_t s_len = 0;
static bool s_overflow = false;
static char s_mqLine[CMD_MAX_LEN];
static char s_out[80];

static const char ERR_TXT[] PROGMEM =
  "\0"
  "comando sconosciuto\0"
  "parametro non valido\0"
  "non homed\0"
  "stato non consente\0"
  "fuori limiti\0"
  "portale non in sede\0"
  "emergenza attiva\0"
  "allarme driver\0";

void protocolInit() {
  s_len = 0;
  s_overflow = false;
}

void protocolReplyErr(CmdSrc src, uint8_t code) {
  if (code < 1 || code > 8) code = 2;
  PGM_P p = ERR_TXT;
  for (uint8_t i = 0; i < code; i++) while (pgm_read_byte(p++)) {}
  char t[24];
  strncpy_P(t, p, sizeof(t) - 1);
  t[sizeof(t) - 1] = 0;
  snprintf_P(s_out, sizeof(s_out), PSTR("ERR E%02u %s"), (unsigned)code, t);
  netReply(src, s_out);
}

static void replyOk(CmdSrc src, const char *cmd, const char *extra) {
  if (extra && *extra) snprintf_P(s_out, sizeof(s_out), PSTR("OK %s %s"), cmd, extra);
  else snprintf_P(s_out, sizeof(s_out), PSTR("OK %s"), cmd);
  netReply(src, s_out);
}

static void upcase(char *s) { for (; *s; s++) *s = (char)toupper((unsigned char)*s); }

static uint8_t tokenize(char *line, char *tok[], uint8_t maxTok) {
  uint8_t n = 0;
  char *p = line;
  while (*p && n < maxTok) {
    while (*p == ' ' || *p == '\t') *p++ = 0;
    if (!*p) break;
    tok[n++] = p;
    while (*p && *p != ' ' && *p != '\t') p++;
  }
  // token in eccesso -> segnalato come parametro non valido
  while (*p == ' ' || *p == '\t') p++;
  if (*p) return 0xFF;
  return n;
}

// Parsing argomenti RUN "k=v": parametri mancanti = default
static uint8_t parseRun(char *tok[], uint8_t n, RunParams &rp) {
  runDefaults(rp);
  for (uint8_t i = 1; i < n; i++) {
    char *eq = strchr(tok[i], '=');
    if (!eq) return E_PARAM;
    *eq = 0;
    const char *k = tok[i];
    float v;
    if (!parseFloatStrict(eq + 1, &v)) return E_PARAM;
    if (!strcasecmp_P(k, PSTR("cx"))) rp.cx = v;
    else if (!strcasecmp_P(k, PSTR("s0"))) rp.s0 = v;
    else if (!strcasecmp_P(k, PSTR("s1"))) rp.s1 = v;
    else if (!strcasecmp_P(k, PSTR("g0"))) rp.g0 = v;
    else if (!strcasecmp_P(k, PSTR("g1"))) rp.g1 = v;
    else if (!strcasecmp_P(k, PSTR("dg"))) rp.dg = v;
    else if (!strcasecmp_P(k, PSTR("f"))) rp.f = v;
    else if (!strcasecmp_P(k, PSTR("od"))) rp.od = v;
    else if (!strcasecmp_P(k, PSTR("n"))) {
      long l;
      if (!parseLongStrict(eq + 1, &l) || l < 0 || l > RUN_MAX_PASSES) return E_PARAM;
      rp.n = (int16_t)l;
    } else return E_PARAM;
  }
  return E_OK;
}

void protocolExecute(char *line, CmdSrc src) {
  // rimuove CR/LF finali
  size_t L = strlen(line);
  while (L && (line[L - 1] == '\r' || line[L - 1] == '\n')) line[--L] = 0;
  char *tok[MAX_TOK];
  uint8_t n = tokenize(line, tok, MAX_TOK);
  if (n == 0) return;                          // riga vuota
  if (n == 0xFF) { protocolReplyErr(src, E_PARAM); return; }
  upcase(tok[0]);
  const char *cmd = tok[0];
  uint8_t e = E_OK;
  char extra[64];
  extra[0] = 0;

  if (!strcmp_P(cmd, PSTR("PING"))) {
    if (n != 1) e = E_PARAM;
  } else if (!strcmp_P(cmd, PSTR("STATUS"))) {
    netRequestState();
    if (src == SRC_SERIAL) netPrintStateSerial();
  } else if (!strcmp_P(cmd, PSTR("HOME"))) {
    e = (n == 1) ? machHome() : (uint8_t)E_PARAM;
  } else if (!strcmp_P(cmd, PSTR("ENABLE"))) {
    if (n != 2 || (strcmp(tok[1], "0") && strcmp(tok[1], "1"))) e = E_PARAM;
    else e = machEnable(tok[1][0] == '1');
  } else if (!strcmp_P(cmd, PSTR("JOG"))) {
    float v;
    if (n != 3 || strlen(tok[1]) != 1 || !parseFloatStrict(tok[2], &v)) e = E_PARAM;
    else e = machJog((char)toupper((unsigned char)tok[1][0]), v);
  } else if (!strcmp_P(cmd, PSTR("MOVE"))) {
    float v, f = P.x_vmax;
    if ((n != 3 && n != 5) || strcasecmp_P(tok[1], PSTR("X")) || !parseFloatStrict(tok[2], &v)) e = E_PARAM;
    else if (n == 5 && (strcasecmp_P(tok[3], PSTR("F")) || !parseFloatStrict(tok[4], &f))) e = E_PARAM;
    else e = machMoveX(v, f);
  } else if (!strcmp_P(cmd, PSTR("GAP"))) {
    float v;
    if (n != 2 || !parseFloatStrict(tok[1], &v)) e = E_PARAM;
    else e = machGap(v);
  } else if (!strcmp_P(cmd, PSTR("RUN"))) {
    RunParams rp;
    uint16_t np = 0;
    e = parseRun(tok, n, rp);
    if (!e) e = machRun(rp, &np);
    if (!e) snprintf_P(extra, sizeof(extra), PSTR("np=%u"), (unsigned)np);
  } else if (!strcmp_P(cmd, PSTR("PAUSE"))) {
    e = (n == 1) ? machPause() : (uint8_t)E_PARAM;
  } else if (!strcmp_P(cmd, PSTR("RESUME"))) {
    e = (n == 1) ? machResume() : (uint8_t)E_PARAM;
  } else if (!strcmp_P(cmd, PSTR("STOP"))) {
    e = machStop();
  } else if (!strcmp_P(cmd, PSTR("RESET"))) {
    e = (n == 1) ? machReset() : (uint8_t)E_PARAM;
  } else if (!strcmp_P(cmd, PSTR("SET"))) {
    if (n != 3) e = E_PARAM;
    else if ((e = machParamsEditable()) == E_OK) {
      bool lost = false;
      e = paramsSet(tok[1], tok[2], &lost);
      if (!e) {
        motionApplyParams();
        if (lost) machInvalidateHoming();
      }
    }
  } else if (!strcmp_P(cmd, PSTR("GET"))) {
    char v[40];
    if (n != 2) e = E_PARAM;
    else if ((e = paramsGet(tok[1], v, sizeof(v))) == E_OK) {
      snprintf_P(extra, sizeof(extra), PSTR("%s %s"), tok[1], v);
    }
  } else if (!strcmp_P(cmd, PSTR("SAVE"))) {
    if ((e = machParamsEditable()) == E_OK) paramsSave();
  } else if (!strcmp_P(cmd, PSTR("DEFAULTS"))) {
    if ((e = machParamsEditable()) == E_OK) {
      paramsDefaults(P);
      motionApplyParams();
      machInvalidateHoming();
    }
  } else if (!strcmp_P(cmd, PSTR("REBOOT"))) {
    if ((e = machParamsEditable()) == E_OK) machRequestReboot();
  } else {
    e = E_UNKNOWN;
  }

  if (e) protocolReplyErr(src, e);
  else replyOk(src, cmd, extra);
}

void protocolPoll() {
  // Seriale: al massimo 64 caratteri per giro per non affamare i motori
  uint8_t budget = 64;
  while (budget-- && Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (s_overflow) {
        s_overflow = false;
        s_len = 0;
        protocolReplyErr(SRC_SERIAL, E_PARAM);
      } else if (s_len) {
        s_line[s_len] = 0;
        s_len = 0;
        protocolExecute(s_line, SRC_SERIAL);
      }
    } else if (s_len < CMD_MAX_LEN - 1) {
      s_line[s_len++] = c;
    } else {
      s_overflow = true;
    }
  }
  // MQTT: un comando per giro
  if (netTakeCommand(s_mqLine, sizeof(s_mqLine))) protocolExecute(s_mqLine, SRC_MQTT);
}
