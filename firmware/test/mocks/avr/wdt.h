// Mock watchdog
#pragma once
#define WDTO_15MS 0
#define WDTO_2S 7
#define WDTO_8S 9
extern int g_mockWdtTimeout;
extern unsigned long g_mockWdtResets;
inline void wdt_enable(int t) { g_mockWdtTimeout = t; }
inline void wdt_disable() { g_mockWdtTimeout = -1; }
inline void wdt_reset() { g_mockWdtResets++; }
