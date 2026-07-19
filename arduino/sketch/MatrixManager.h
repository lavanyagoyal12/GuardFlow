#ifndef MATRIX_MANAGER_H
#define MATRIX_MANAGER_H

#include <Arduino.h>
#include <Arduino_LED_Matrix.h>
#include "Config.h"

// Which looping animation (if any) is currently active on the matrix
enum class MatrixAnimation {
    NONE,
    HEARTBEAT,
    SCANNING,
    WARNING_BLINK,
    NFC_WAITING,
    DENIED_CROSS
};

class MatrixManager {
public:
    MatrixManager();

    void begin();

    // Static / one-shot frames
    void showHeart();
    void showShield();
    void showGF();
    void showLock();
    void showUnlock();
    void showCheckmark();
    void showCross();
    void showExclamation();
    void showWarningTriangle();
    void showSafe();
    void showWarningText();
    void showOpen();
    void showAccessDenied();
    void showScanCard();
    void clear();

    // Looping animations - call start once, then update() every loop()
    void startAnimation(MatrixAnimation anim);
    void stopAnimation();

    // Must be called every loop() iteration to advance active animation
    void update();

private:
    ArduinoLEDMatrix _matrix;
    MatrixAnimation _activeAnimation;
    unsigned long _lastFrameTime;
    uint8_t _frameIndex;

    void renderFrame(const uint8_t frame[8][12]);

    void updateHeartbeat();
    void updateScanning();
    void updateWarningBlink();
    void updateNfcWaiting();
    void updateDeniedCross();
};

#endif // MATRIX_MANAGER_H
