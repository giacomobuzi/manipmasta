// Mock EEPROM (4 KB come ATmega2560)
#pragma once
#include <stdint.h>
#include <string.h>
struct EEPROMClass {
  uint8_t data[4096];
  unsigned long writes = 0;
  uint8_t read(int a) { return data[a]; }
  void write(int a, uint8_t v) { data[a] = v; writes++; }
  void update(int a, uint8_t v) { if (data[a] != v) write(a, v); }
  int length() { return 4096; }
  template <typename T> T &get(int a, T &t) { memcpy(&t, data + a, sizeof(T)); return t; }
  template <typename T> const T &put(int a, const T &t) {
    const uint8_t *p = (const uint8_t *)&t;
    for (size_t i = 0; i < sizeof(T); i++) update(a + (int)i, p[i]);
    return t;
  }
};
extern EEPROMClass EEPROM;
