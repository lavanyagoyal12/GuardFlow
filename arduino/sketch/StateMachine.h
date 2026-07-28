#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <Arduino.h>
#include "Config.h"
#include "LEDManager.h"
#include "MatrixManager.h"
#include "ServoManager.h"
#include "NFCManager.h"
#include "BuzzerManager.h"

// Result of the most recent NFC check, polled by the Python side via Bridge
enum class NfcResult {
    NONE = 0,       // no card checked yet / no new result
    AUTHORIZED = 1,
    DENIED = 2
};

class StateMachine {
public:
    StateMachine();

    void begin();

    // Must be called every loop() iteration
    void update();

    // ---- Commands, called from Python via Bridge.provide() wrappers ----
    void cmdBoot();
    void cmdScan();
    void cmdLow();
    void cmdMedium();
    void cmdHigh();
    void cmdAuthorized();
    void cmdDenied();
    void cmdReset();

    // Python polls this after seeing WAITING_FOR_NFC to find out the
    // outcome of the most recent card tap. Calling it consumes (clears)
    // the pending result.
    int pollNfcResult();

    // Lets Python know which state we're in, useful for UI / logging
    const char* getStateName() const;

    // TEMPORARY: exposes the raw UID of the last card tapped, so it can
    // be read from Python during initial setup (to find your card's UID
    // for Config.h). Safe to leave in permanently - it's just a getter.
    String getLastNfcUid() const;

private:
    LEDManager    _leds;
    MatrixManager _matrix;
    ServoManager  _servo;
    NFCManager    _nfc;
    BuzzerManager _buzzer;

    SystemState _state;
    NfcResult   _pendingNfcResult;

    uint8_t _bootStep;
    unsigned long _bootStepStart;
    unsigned long _stateEnteredAt;
    bool _checkmarkShown;

    void setState(SystemState newState);

    void updateBooting();
    void updateIdle();
    void updateScanning();
    void updateLowRisk();
    void updateMediumRisk();
    void updateHighRisk();
    void updateWaitingForNfc();
    void updateAuthorized();
    void updateDenied();
};

#endif // STATE_MACHINE_H