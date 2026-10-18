// Mock di avr/pgmspace.h: su host la "flash" e' normale RAM
#pragma once
#include <string.h>
#include <strings.h>
#include <stdio.h>
#include <stdint.h>
#define PROGMEM
#define PSTR(s) (s)
typedef const char *PGM_P;
#define pgm_read_byte(p) (*(const uint8_t *)(p))
#define memcpy_P memcpy
#define strcpy_P strcpy
#define strncpy_P strncpy
#define strcmp_P strcmp
#define strncmp_P strncmp
#define strcasecmp_P strcasecmp
#define snprintf_P snprintf
