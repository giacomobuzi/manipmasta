// Mock minimale di Arduino.h per i test host (g++). NON usato su AVR.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <strings.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <ctype.h>
#include "avr/pgmspace.h"

typedef uint8_t byte;
typedef bool boolean;

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define CHANGE 1
#define FALLING 2
#define RISING 3

#define F(s) (s)
#define digitalPinToInterrupt(p) ((p) == 2 ? 0 : ((p) == 3 ? 1 : -1))

void pinMode(uint8_t pin, uint8_t mode);
void digitalWrite(uint8_t pin, uint8_t val);
int digitalRead(uint8_t pin);
unsigned long millis();
unsigned long micros();
void delayMicroseconds(unsigned int us);
void delay(unsigned long ms);
void attachInterrupt(int irq, void (*isr)(), int mode);

class SerialMock {
 public:
  void begin(unsigned long) {}
  int available();
  int read();
  size_t print(const char *s);
  size_t print(long v);
  size_t println(const char *s);
  size_t println();
  void flush() {}
};
extern SerialMock Serial;
