#include "BuzzerManager.h"

BuzzerManager::BuzzerManager()
    : _alarming(false), _buzzerOn(false), _lastToggleTime(0) {}

void BuzzerManager::begin() {
    pinMode(PIN_BUZZER, OUTPUT);
    setPin(false);
}

void BuzzerManager::setPin(bool on) {
    _buzzerOn = on;
    digitalWrite(PIN_BUZZER, on ? HIGH : LOW);
}

void BuzzerManager::startAlarm() {
    _alarming = true;
    _lastToggleTime = millis();
    setPin(true); // start audible immediately, not after the first interval
}

void BuzzerManager::stopAlarm() {
    _alarming = false;
    setPin(false);
}

bool BuzzerManager::isAlarming() const {
    return _alarming;
}

void BuzzerManager::update() {
    if (!_alarming) {
        return;
    }

    unsigned long now = millis();
    if (now - _lastToggleTime >= BUZZER_BEEP_INTERVAL_MS) {
        _lastToggleTime = now;
        setPin(!_buzzerOn);
    }
}