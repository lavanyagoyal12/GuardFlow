#ifndef LED_MANAGER_H
#define LED_MANAGER_H

#include <Arduino.h>
#include "Config.h"

// Simple non-blocking blink mode for a single LED
enum class LedMode {
    OFF,
    ON,
    BLINK
};

class LEDManager {
public:
    LEDManager();

    void begin();

    // Direct state setters
    void setGreen(LedMode mode);
    void setYellow(LedMode mode);
    void setRed(LedMode mode);

    // Convenience: turn everything off
    void allOff();

    // Must be called every loop() iteration - handles blinking without delay()
    void update();

private:
    LedMode _greenMode;
    LedMode _yellowMode;
    LedMode _redMode;

    bool _blinkPhase;
    unsigned long _lastBlinkToggle;

    void applyPin(int pin, LedMode mode);
};

#endif // LED_MANAGER_H
