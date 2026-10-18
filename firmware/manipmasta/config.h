// =====================================================================
// ManipMasta - configurazione hardware e costanti firmware
// Pinout DEFINITIVO secondo docs/SPEC.md §2.1 (non modificare senza
// aggiornare la SPEC). Parametri runtime (EEPROM) in params.h.
// =====================================================================
#pragma once
#include <Arduino.h>

#define FW_VERSION "1.0.0"

// ---------------------------------------------------------------------
// Pin riservati shield Ethernet 2 (W5500): D4 SD CS (tenere ALTO),
// D10 W5500 CS, D50-D53 SPI. NON usarli.
// ---------------------------------------------------------------------
#define PIN_SD_CS        4
#define PIN_W5500_CS     10

// ---------------------------------------------------------------------
// Driver CL57T (step/dir)
// ---------------------------------------------------------------------
#define PIN_X_PUL   22
#define PIN_X_DIR   23
#define PIN_X_ENA   24
#define PIN_X_ALM   25

#define PIN_Z1_PUL  26
#define PIN_Z1_DIR  27
#define PIN_Z1_ENA  28
#define PIN_Z1_ALM  29

#define PIN_Z2_PUL  30
#define PIN_Z2_DIR  31
#define PIN_Z2_ENA  32
#define PIN_Z2_ALM  33

#define PIN_R_PUL   34
#define PIN_R_DIR   35
#define PIN_R_ENA   36
#define PIN_R_ALM   37

// ---------------------------------------------------------------------
// Ingressi (schede opto 24->5 V, INPUT_PULLUP)
// ---------------------------------------------------------------------
#define PIN_X_MIN      38   // home X, basso = attivo
#define PIN_X_MAX      39   // extracorsa X+, basso = attivo
#define PIN_Z1_HOME    40   // home Z1 (alto), basso = attivo
#define PIN_Z2_HOME    41
#define PIN_Z1_LOW     42   // extracorsa basso Z1, basso = attivo
#define PIN_Z2_LOW     43
#define PIN_SEAT_A     44   // portale in sede A1, basso = in sede
#define PIN_SEAT_B     45   // portale in sede A2, basso = in sede
#define PIN_BTN_START  48   // pulsante START, basso = premuto
#define PIN_BTN_STOP   49   // pulsante STOP NC: ALTO = premuto / filo rotto
#define PIN_ESTOP_OK    2   // INT: BASSO = catena OK, ALTO = emergenza
#define PIN_CURTAIN_OK  3   // INT: BASSO = barriera libera, ALTO = interrotta

// ---------------------------------------------------------------------
// Uscite colonna luminosa / buzzer (modulo rele', attivo ALTO)
// ---------------------------------------------------------------------
#define PIN_LAMP_GREEN  5
#define PIN_LAMP_YELLOW 6
#define PIN_LAMP_RED    7
#define PIN_BUZZER      8

// ---------------------------------------------------------------------
// ENA dei CL57T: opto attivo (pin ALTO) = driver DISABILITATO.
// ENA_ACTIVE_LEVEL = livello del pin che ABILITA il driver.
// ---------------------------------------------------------------------
#define ENA_ACTIVE_LEVEL    LOW
#define ENA_INACTIVE_LEVEL  ((ENA_ACTIVE_LEVEL) == LOW ? HIGH : LOW)

// Larghezza minima impulso step (us) per CL57T (min. 2,5 us)
#define STEP_PULSE_US       5
// Tempo di setup DIR prima dell'impulso (solo asse R gestito a mano)
#define R_DIR_SETUP_US      5

// Segno meccanico dell'asservimento R->X (+1/-1): scelto in modo che il
// rullo ROTOLI senza strisciare quando X avanza. Il verso fisico del
// motore R si corregge anche con il bit 3 di dir_inv (EEPROM).
#define R_GEAR_SIGN         1

// Velocita' JOG R (mm/s di superficie)
#define R_JOG_SPEED         40.0f

// ---------------------------------------------------------------------
// Homing
// ---------------------------------------------------------------------
#define HOME_BACKOFF_MM      2.0f    // arretramento dopo il primo contatto
#define HOME_Z_FAST          5.0f    // mm/s
#define HOME_Z_SLOW          0.5f    // mm/s
#define HOME_X_FAST         40.0f    // mm/s
#define HOME_X_SLOW          4.0f    // mm/s
#define HOME_Z_EXTRA_MM     50.0f    // corsa di ricerca oltre z_home_gap
#define HOME_X_EXTRA_MM    100.0f    // corsa di ricerca oltre (x_max-x_min)
#define HOME_Z_FAST_TO_MS   60000UL  // timeout fase veloce Z
#define HOME_X_FAST_TO_MS   60000UL  // timeout fase veloce X
#define HOME_BACKOFF_TO_MS   8000UL  // timeout arretramento
#define HOME_SLOW_TO_MS     15000UL  // timeout riavvicinamento lento
#define HOME_POS_TO_MS      30000UL  // timeout posizionamento finale X

// ---------------------------------------------------------------------
// Arresti
// ---------------------------------------------------------------------
#define FAST_DECEL_X      3000.0f   // mm/s^2 arresto rapido (barriera/allarme)
#define FAST_DECEL_Z       400.0f   // mm/s^2
#define SAFE_LIFT_MM        20.0f   // risalita su STOP
#define JOG_UNHOMED_FACTOR   0.25f  // velocita' JOG ridotta se non homed

// ---------------------------------------------------------------------
// Ciclo RUN: default dei parametri mancanti (SPEC §3, esempio RUN)
// ---------------------------------------------------------------------
#define RUN_DEF_CX     0.0f
#define RUN_DEF_S0   150.0f
#define RUN_DEF_S1   300.0f
#define RUN_DEF_G0    40.0f
#define RUN_DEF_G1     5.0f
#define RUN_DEF_DG     3.0f
#define RUN_DEF_F     60.0f
#define RUN_DEF_N      2
// od mancante = parametro EEPROM "od"
#define RUN_MARGIN_MM     60.0f   // fuori impasto (SPEC §4)
#define RUN_SAFE_ABOVE    20.0f   // Z a g0 + 20
#define RUN_END_ABOVE     30.0f   // Z a g1 + 30
#define RUN_MAX_PASSES   999

// ---------------------------------------------------------------------
// Rete / MQTT
// ---------------------------------------------------------------------
#define NET_SERVICE_MOVING_MS   5UL     // servizio rete in movimento
#define STATE_PUB_MOVING_MS   200UL
#define STATE_PUB_REST_MS    2000UL
#define MQTT_BACKOFF_MIN_MS  2000UL
#define MQTT_BACKOFF_MAX_MS 30000UL
#define MQTT_CONN_TIMEOUT_MS  800       // timeout connect() W5500 (< watchdog)
#define MQTT_BUFFER_SIZE      400
#define MQTT_KEEPALIVE_S       15

#define TOPIC_CMD    "manipmasta/cmd"
#define TOPIC_RESP   "manipmasta/resp"
#define TOPIC_STATE  "manipmasta/state"
#define TOPIC_EVENT  "manipmasta/event"
#define TOPIC_ONLINE "manipmasta/online"

// ---------------------------------------------------------------------
// Varie
// ---------------------------------------------------------------------
#define SERIAL_BAUD        115200
#define CMD_MAX_LEN            96
#define INPUT_DEBOUNCE_MS       3     // campioni stabili (1 ms ciascuno)
#define ALM_MASK_MS           300UL   // ignora ALM driver dopo l'abilitazione
#define BOOT_SETTLE_MS        100UL
#define BLINK_MS              500UL
#define BEEP_ON_MS            150UL
#define BEEP_OFF_MS           150UL
