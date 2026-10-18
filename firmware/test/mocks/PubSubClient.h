// Mock PubSubClient: registra connect/publish/subscribe
#pragma once
#include <stdint.h>
#include <string>
#include <vector>
#include "Ethernet.h"

struct MockPub { std::string topic, payload; bool retained; };

class PubSubClient {
 public:
  typedef void (*Cb)(char *, uint8_t *, unsigned int);
  static PubSubClient *instance;
  explicit PubSubClient(EthernetClient &) { instance = this; }
  PubSubClient &setServer(IPAddress ip, uint16_t port) { serverIp = ip; host.clear(); this->port = port; return *this; }
  PubSubClient &setServer(const char *h, uint16_t port) { host = h; this->port = port; return *this; }
  PubSubClient &setCallback(Cb c) { cb = c; return *this; }
  bool setBufferSize(uint16_t s) { bufSize = s; return true; }
  PubSubClient &setKeepAlive(uint16_t k) { keepAlive = k; return *this; }
  PubSubClient &setSocketTimeout(uint16_t t) { (void)t; return *this; }
  bool connect(const char *id, const char *user, const char *pass, const char *willTopic,
               uint8_t willQos, bool willRetain, const char *willMsg) {
    connectCalls++;
    clientId = id ? id : "";
    this->user = user ? user : "";
    this->pass = pass ? pass : "";
    this->willTopic = willTopic ? willTopic : "";
    this->willMsg = willMsg ? willMsg : "";
    this->willRetain = willRetain; this->willQos = willQos;
    conn = acceptConnect;
    return conn;
  }
  bool connected() { return conn; }
  bool loop() { loopCalls++; return conn; }
  bool publish(const char *t, const char *p, bool r = false) {
    if (!conn) return false;
    pubs.push_back({t, p, r});
    return true;
  }
  bool subscribe(const char *t, uint8_t q = 0) { subs.push_back(t); (void)q; return conn; }
  void disconnect() { conn = false; }
  // --- controllo test ---
  void inject(const char *payload) { if (cb) cb((char *)"manipmasta/cmd", (uint8_t *)payload, (unsigned)strlen(payload)); }
  bool acceptConnect = true;
  bool conn = false;
  int connectCalls = 0;
  unsigned long loopCalls = 0;
  Cb cb = nullptr;
  IPAddress serverIp; std::string host; uint16_t port = 0, bufSize = 0, keepAlive = 0;
  std::string clientId, user, pass, willTopic, willMsg; bool willRetain = false; uint8_t willQos = 0;
  std::vector<MockPub> pubs;
  std::vector<std::string> subs;
};
