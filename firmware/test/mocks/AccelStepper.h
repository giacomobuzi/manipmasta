// Mock AccelStepper: un passo (o stepsPerRun passi) per chiamata a run(),
// senza profilo di velocita'. Sufficiente per la logica.
#pragma once
#include <stdint.h>
unsigned long micros();
class AccelStepper {
 public:
  enum MotorInterfaceType { FUNCTION = 0, DRIVER = 1, FULL2WIRE = 2 };
  static int stepsPerRun;      // passi per run()
  static int stopOvershoot;    // passi residui dopo stop() (decelerazione)
  AccelStepper(uint8_t = 4, uint8_t = 2, uint8_t = 3, uint8_t = 4, uint8_t = 5, bool = true) {}
  void moveTo(long t) { _target = t; }
  void move(long d) { _target = _pos + d; }
  bool run() {
    if (_pos == _target) { _speed = 0; return false; }
    int dir = _target > _pos ? 1 : -1;
    // un passo alla volta, cadenzato dalla velocita' massima (senza rampa)
    unsigned long iv = (unsigned long)(1000000.0f / (_max > 1.0f ? _max : 1.0f));
    if (stepsPerRun > 0 && micros() - _last >= iv) {
      _last = micros();
      for (int i = 0; i < stepsPerRun && _pos != _target; i++) { _pos += dir; _phys += dir; }
    }
    _speed = dir * _max;
    return _pos != _target;
  }
  bool runSpeed() { return run(); }
  long distanceToGo() { return _target - _pos; }
  long targetPosition() { return _target; }
  long currentPosition() { return _pos; }
  void setCurrentPosition(long p) { _pos = _target = p; _speed = 0; }
  void setMaxSpeed(float s) { _max = s; }
  float maxSpeed() { return _max; }
  void setAcceleration(float a) { _acc = a; }
  float acceleration() { return _acc; }
  void setSpeed(float s) { _speed = s; }
  float speed() { return _speed; }
  void stop() {
    long d = _target - _pos;
    if (d == 0) return;
    long o = stopOvershoot;
    if (d > 0) _target = _pos + (d < o ? d : o);
    else _target = _pos - (-d < o ? -d : o);
    stopCalls++;
  }
  bool isRunning() { return _pos != _target; }
  void setPinsInverted(bool d = false, bool s = false, bool e = false) { _dirInv = d; (void)s; (void)e; }
  void setMinPulseWidth(unsigned int w) { _minPulse = w; }
  // ispezione test
  long _pos = 0, _target = 0;
  long _phys = 0;
  unsigned long _last = 0;              // posizione fisica (non toccata da setCurrentPosition)
  float _max = 1, _acc = 1, _speed = 0;
  bool _dirInv = false;
  unsigned _minPulse = 0;
  int stopCalls = 0;
};
