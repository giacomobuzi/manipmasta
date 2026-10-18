// Mock Ethernet (W5500)
#pragma once
#include <stdint.h>
#include <string.h>
class IPAddress {
 public:
  uint8_t b[4] = {0, 0, 0, 0};
  IPAddress() {}
  IPAddress(uint8_t a, uint8_t c, uint8_t d, uint8_t e) { b[0] = a; b[1] = c; b[2] = d; b[3] = e; }
  uint8_t operator[](int i) const { return b[i]; }
};
enum EthernetHardwareStatus { EthernetNoHardware, EthernetW5100, EthernetW5200, EthernetW5500 };
enum EthernetLinkStatus { Unknown, LinkON, LinkOFF };
class EthernetClass {
 public:
  EthernetHardwareStatus hw = EthernetW5500;
  EthernetLinkStatus link = LinkON;
  uint8_t mac[6];
  IPAddress ip;
  unsigned long maintainCalls = 0;
  void init(uint8_t) {}
  void begin(uint8_t *m, IPAddress i, IPAddress, IPAddress, IPAddress) { memcpy(mac, m, 6); ip = i; }
  int maintain() { maintainCalls++; return 0; }
  EthernetHardwareStatus hardwareStatus() { return hw; }
  EthernetLinkStatus linkStatus() { return link; }
  void setRetransmissionTimeout(uint16_t) {}
  void setRetransmissionCount(uint8_t) {}
};
extern EthernetClass Ethernet;
class EthernetClient {
 public:
  uint16_t connTimeout = 0;
  void setConnectionTimeout(uint16_t t) { connTimeout = t; }
};
