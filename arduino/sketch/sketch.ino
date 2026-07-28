/*
 * GuardFlow - AI-Powered Fraud Detection System
 * MCU Sketch for Arduino UNO Q (Arduino App Lab)
 *
 * This file runs on the STM32 real-time microcontroller side of the
 * UNO Q. It owns all the time-critical hardware: the 3 status LEDs,
 * the SG90 lock servo, the 12x8 LED matrix, and the RC522 NFC reader.
 *
 * It performs NO fraud-detection logic itself and does NOT talk to the
 * AI backend directly. Instead, it exposes a small set of functions
 * over the Arduino Bridge that the companion Python app
 * (python/main.py, running on the Linux/MPU side) calls after it has
 * received a command from the AI backend over USB Serial / network.
 *
 * Bridge functions exposed to Python:
 *   cmd_boot()          - replay boot animation
 *   cmd_scan()           - play ~3s scanning animation
 *   cmd_low()             - LOW risk verdict
 *   cmd_medium()          - MEDIUM risk verdict
 *   cmd_high()            - HIGH risk verdict (locks + waits for NFC)
 *   cmd_authorized()      - force-authorize (backend override)
 *   cmd_denied()          - force-deny (backend override)
 *   cmd_reset()           - back to IDLE
 *   poll_nfc_result()     - int: 0=none, 1=authorized, 2=denied (clears on read)
 *   get_state_name()      - String: current state, for logging/UI
 */

#include <Arduino_RouterBridge.h>
#include "Config.h"
#include "StateMachine.h"

StateMachine guardFlow;

// ---- Bridge-exposed wrapper functions -------------------------------
// Bridge.provide() needs plain functions (or captureless lambdas), so
// these thin wrappers forward to the StateMachine instance.

void cmd_boot()       { guardFlow.cmdBoot(); }
void cmd_scan()        { guardFlow.cmdScan(); }
void cmd_low()          { guardFlow.cmdLow(); }
void cmd_medium()       { guardFlow.cmdMedium(); }
void cmd_high()         { guardFlow.cmdHigh(); }
void cmd_authorized()   { guardFlow.cmdAuthorized(); }
void cmd_denied()       { guardFlow.cmdDenied(); }
void cmd_reset()        { guardFlow.cmdReset(); }

int poll_nfc_result() {
    return guardFlow.pollNfcResult();
}

String get_state_name() {
    return String(guardFlow.getStateName());
}

void setup() {
    guardFlow.begin();

    // Bring up the Bridge and register every function Python needs.
    Bridge.begin();

    Bridge.provide("cmd_boot", cmd_boot);
    Bridge.provide("cmd_scan", cmd_scan);
    Bridge.provide("cmd_low", cmd_low);
    Bridge.provide("cmd_medium", cmd_medium);
    Bridge.provide("cmd_high", cmd_high);
    Bridge.provide("cmd_authorized", cmd_authorized);
    Bridge.provide("cmd_denied", cmd_denied);
    Bridge.provide("cmd_reset", cmd_reset);
    Bridge.provide("poll_nfc_result", poll_nfc_result);
    Bridge.provide("get_state_name", get_state_name);
}

void loop() {
    // Keep the Bridge responsive to incoming calls from Python.
    Bridge.update();

    // Advance LEDs / servo / matrix animation / NFC polling / state
    // transitions. Fully non-blocking (millis()-based).
    guardFlow.update();
}
