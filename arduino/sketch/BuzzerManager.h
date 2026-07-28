#ifndef BUZZER_MANAGER_H
#define BUZZER_MANAGER_H

#include <Arduino.h>
#include "Config.h"

// Controls a single active buzzer on PIN_BUZZER. Used as an audible
// alarm during HIGH_RISK / WAITING_FOR_NFC, so the person is prompted
// to tap their card - not just relying on the red LED.
class BuzzerManager {
public:
    BuzzerManager();

    void begin();

    // Starts the intermittent on/off beeping pattern (non-blocking).
    void startAlarm();

    // Immediately silences the buzzer and stops the alarm pattern.
    void stopAlarm();

    bool isAlarming() const;

    // Must be called every loop() iteration to advance the beep pattern.
    void update();

private:
    bool _alarming;
    bool _buzzerOn;
    unsigned long _lastToggleTime;

    void setPin(bool on);
};

#endif // BUZZER_MANAGER_H