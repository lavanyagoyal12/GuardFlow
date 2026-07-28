#include "LEDManager.h"

LEDManager::LEDManager()
    : _greenMode(LedMode::OFF),
      _yellowMode(LedMode::OFF),
      _redMode(LedMode::OFF),
      _blinkPhase(false),
      _lastBlinkToggle(0) {}

void LEDManager::begin() {
    pinMode(PIN_LED_GREEN, OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_RED, OUTPUT);
    allOff();
}

void LEDManager::setGreen(LedMode mode) {
    _greenMode = mode;
}

void LEDManager::setYellow(LedMode mode) {
    _yellowMode = mode;
}

void LEDManager::setRed(LedMode mode) {
    _redMode = mode;
}

void LEDManager::allOff() {
    _greenMode = LedMode::OFF;
    _yellowMode = LedMode::OFF;
    _redMode = LedMode::OFF;
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_RED, LOW);
}

void LEDManager::applyPin(int pin, LedMode mode) {
    switch (mode) {
        case LedMode::OFF:
            digitalWrite(pin, LOW);
            break;
        case LedMode::ON:
            digitalWrite(pin, HIGH);
            break;
        case LedMode::BLINK:
            digitalWrite(pin, _blinkPhase ? HIGH : LOW);
            break;
    }
}

void LEDManager::update() {
    unsigned long now = millis();
    if (now - _lastBlinkToggle >= BLINK_INTERVAL_MS) {
        _lastBlinkToggle = now;
        _blinkPhase = !_blinkPhase;
    }

    applyPin(PIN_LED_GREEN, _greenMode);
    applyPin(PIN_LED_YELLOW, _yellowMode);
    applyPin(PIN_LED_RED, _redMode);
}
