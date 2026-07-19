#include "MatrixManager.h"

// The Arduino UNO R4 matrix is 12 columns x 8 rows.
// Frames are declared as [8 rows][12 cols], 1 = pixel on.

static const uint8_t FRAME_HEART[8][12] = {
    {0,0,1,1,0,0,0,0,1,1,0,0},
    {0,1,1,1,1,0,1,1,1,1,0,0},
    {1,1,1,1,1,1,1,1,1,1,1,0},
    {1,1,1,1,1,1,1,1,1,1,1,0},
    {0,1,1,1,1,1,1,1,1,1,0,0},
    {0,0,1,1,1,1,1,1,1,0,0,0},
    {0,0,0,1,1,1,1,1,0,0,0,0},
    {0,0,0,0,1,1,1,0,0,0,0,0}
};

static const uint8_t FRAME_SHIELD[8][12] = {
    {0,0,0,1,1,1,1,1,0,0,0,0},
    {0,0,1,1,0,0,0,1,1,0,0,0},
    {0,1,1,0,0,0,0,0,1,1,0,0},
    {0,1,1,0,1,0,1,0,1,1,0,0},
    {0,1,1,0,0,1,0,0,1,1,0,0},
    {0,0,1,1,0,0,0,1,1,0,0,0},
    {0,0,0,1,1,0,1,1,0,0,0,0},
    {0,0,0,0,1,1,1,0,0,0,0,0}
};

static const uint8_t FRAME_GF[8][12] = {
    {0,1,1,1,0,0,1,1,1,1,0,0},
    {1,1,0,0,0,0,1,1,0,0,0,0},
    {1,1,0,0,0,0,1,1,0,0,0,0},
    {1,1,0,1,1,0,1,1,1,1,0,0},
    {1,1,0,0,1,0,1,1,0,0,0,0},
    {1,1,0,0,1,0,1,1,0,0,0,0},
    {0,1,1,1,1,0,1,1,0,0,0,0},
    {0,0,0,0,0,0,1,1,0,0,0,0}
};

static const uint8_t FRAME_LOCK[8][12] = {
    {0,0,0,1,1,1,1,0,0,0,0,0},
    {0,0,1,1,0,0,1,1,0,0,0,0},
    {0,0,1,1,0,0,1,1,0,0,0,0},
    {0,1,1,1,1,1,1,1,1,0,0,0},
    {0,1,1,1,1,1,1,1,1,0,0,0},
    {0,1,1,0,1,1,0,1,1,0,0,0},
    {0,1,1,0,1,1,0,1,1,0,0,0},
    {0,1,1,1,1,1,1,1,1,0,0,0}
};

static const uint8_t FRAME_UNLOCK[8][12] = {
    {0,0,0,1,1,1,1,0,0,0,0,0},
    {0,0,1,1,0,0,1,1,0,0,0,0},
    {0,0,1,1,0,0,0,0,0,0,0,0},
    {0,1,1,1,1,1,1,1,1,0,0,0},
    {0,1,1,1,1,1,1,1,1,0,0,0},
    {0,1,1,0,1,1,0,1,1,0,0,0},
    {0,1,1,0,1,1,0,1,1,0,0,0},
    {0,1,1,1,1,1,1,1,1,0,0,0}
};

static const uint8_t FRAME_CHECK[8][12] = {
    {0,0,0,0,0,0,0,0,1,1,0,0},
    {0,0,0,0,0,0,0,1,1,0,0,0},
    {0,0,0,0,0,0,1,1,0,0,0,0},
    {1,1,0,0,0,1,1,0,0,0,0,0},
    {1,1,1,0,1,1,0,0,0,0,0,0},
    {0,1,1,1,1,0,0,0,0,0,0,0},
    {0,0,1,1,0,0,0,0,0,0,0,0},
    {0,0,0,1,0,0,0,0,0,0,0,0}
};

static const uint8_t FRAME_CROSS[8][12] = {
    {1,1,0,0,0,0,0,0,0,1,1,0},
    {0,1,1,0,0,0,0,0,1,1,0,0},
    {0,0,1,1,0,0,0,1,1,0,0,0},
    {0,0,0,1,1,0,1,1,0,0,0,0},
    {0,0,0,0,1,1,1,0,0,0,0,0},
    {0,0,0,1,1,0,1,1,0,0,0,0},
    {0,0,1,1,0,0,0,1,1,0,0,0},
    {0,1,1,0,0,0,0,0,1,1,0,0}
};

static const uint8_t FRAME_EXCLAIM[8][12] = {
    {0,0,0,0,0,1,1,0,0,0,0,0},
    {0,0,0,0,0,1,1,0,0,0,0,0},
    {0,0,0,0,0,1,1,0,0,0,0,0},
    {0,0,0,0,0,1,1,0,0,0,0,0},
    {0,0,0,0,0,1,1,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,1,1,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0}
};

static const uint8_t FRAME_TRIANGLE[8][12] = {
    {0,0,0,0,0,1,1,0,0,0,0,0},
    {0,0,0,0,1,1,1,1,0,0,0,0},
    {0,0,0,1,1,0,0,1,1,0,0,0},
    {0,0,1,1,0,1,1,0,1,1,0,0},
    {0,1,1,0,1,1,1,1,0,1,1,0},
    {0,1,1,0,0,1,1,0,0,1,1,0},
    {1,1,0,0,1,1,1,1,0,0,1,1},
    {1,1,1,1,1,1,1,1,1,1,1,1}
};

static const uint8_t FRAME_BLANK[8][12] = {
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0}
};

// Spinner frames (4-phase rotating dot on a ring), used for SCAN animation
static const uint8_t FRAME_SPIN0[8][12] = {
    {0,0,0,0,1,1,1,1,0,0,0,0},
    {0,0,1,1,0,0,0,0,1,1,0,0},
    {0,1,0,0,0,0,0,0,0,0,1,0},
    {1,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,1},
    {0,1,0,0,0,0,0,0,0,0,1,0},
    {0,0,1,1,0,0,0,0,1,1,0,0},
    {0,0,0,0,1,1,1,1,0,0,0,0}
};
static const uint8_t FRAME_SPIN1[8][12] = {
    {0,0,0,0,1,1,1,1,0,0,0,0},
    {0,0,1,1,0,0,0,0,1,1,0,0},
    {0,1,0,0,0,0,0,0,0,1,1,0},
    {1,0,0,0,0,0,0,0,0,0,1,0},
    {1,0,0,0,0,0,0,0,0,0,0,0},
    {0,1,0,0,0,0,0,0,0,0,0,0},
    {0,0,1,1,0,0,0,0,0,0,0,0},
    {0,0,0,0,1,1,0,0,0,0,0,0}
};
static const uint8_t FRAME_SPIN2[8][12] = {
    {0,0,0,0,1,1,0,0,0,0,0,0},
    {0,0,1,1,0,0,0,0,0,0,0,0},
    {0,1,0,0,0,0,0,0,0,0,0,0},
    {1,0,0,0,0,0,0,0,0,0,0,0},
    {1,0,0,0,0,0,0,0,0,0,0,1},
    {0,1,0,0,0,0,0,0,0,0,1,0},
    {0,0,1,1,0,0,0,0,1,1,0,0},
    {0,0,0,0,1,1,1,1,0,0,0,0}
};
static const uint8_t FRAME_SPIN3[8][12] = {
    {0,0,0,0,0,0,1,1,0,0,0,0},
    {0,0,0,0,0,0,0,1,1,0,0,0},
    {0,0,0,0,0,0,0,0,1,0,1,0},
    {0,0,0,0,0,0,0,0,0,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,1},
    {0,1,0,0,0,0,0,0,0,0,1,0},
    {0,0,1,1,0,0,0,0,1,1,0,0},
    {0,0,0,0,1,1,1,1,0,0,0,0}
};

MatrixManager::MatrixManager()
    : _activeAnimation(MatrixAnimation::NONE), _lastFrameTime(0), _frameIndex(0) {}

void MatrixManager::begin() {
    _matrix.begin();
    clear();
}

void MatrixManager::renderFrame(const uint8_t frame[8][12]) {
    // ArduinoLEDMatrix expects a non-const uint8_t[8][12] buffer
    uint8_t buf[8][12];
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 12; c++) {
            buf[r][c] = frame[r][c];
        }
    }
    _matrix.renderBitmap(buf, 8, 12);
}

void MatrixManager::clear() {
    _activeAnimation = MatrixAnimation::NONE;
    renderFrame(FRAME_BLANK);
}

void MatrixManager::showHeart()          { renderFrame(FRAME_HEART); }
void MatrixManager::showShield()         { renderFrame(FRAME_SHIELD); }
void MatrixManager::showGF()             { renderFrame(FRAME_GF); }
void MatrixManager::showLock()           { renderFrame(FRAME_LOCK); }
void MatrixManager::showUnlock()         { renderFrame(FRAME_UNLOCK); }
void MatrixManager::showCheckmark()      { renderFrame(FRAME_CHECK); }
void MatrixManager::showCross()          { renderFrame(FRAME_CROSS); }
void MatrixManager::showExclamation()    { renderFrame(FRAME_EXCLAIM); }
void MatrixManager::showWarningTriangle(){ renderFrame(FRAME_TRIANGLE); }

// This board's Arduino_LED_Matrix build does not expose the
// beginDraw/stroke/textFont/println-style text API (that belongs to a
// different matrix library variant), so these "text" frames are
// implemented as plain bitmap icons instead - which also matches the
// original requirement to favor real bitmap graphics over scrolling text.
void MatrixManager::showSafe()          { renderFrame(FRAME_CHECK); }
void MatrixManager::showWarningText()   { renderFrame(FRAME_EXCLAIM); }
void MatrixManager::showOpen()          { renderFrame(FRAME_UNLOCK); }
void MatrixManager::showAccessDenied()  { renderFrame(FRAME_CROSS); }
void MatrixManager::showScanCard()      { renderFrame(FRAME_SPIN0); }

void MatrixManager::startAnimation(MatrixAnimation anim) {
    _activeAnimation = anim;
    _frameIndex = 0;
    _lastFrameTime = millis();
}

void MatrixManager::stopAnimation() {
    _activeAnimation = MatrixAnimation::NONE;
}

void MatrixManager::update() {
    switch (_activeAnimation) {
        case MatrixAnimation::HEARTBEAT:     updateHeartbeat();   break;
        case MatrixAnimation::SCANNING:      updateScanning();    break;
        case MatrixAnimation::WARNING_BLINK: updateWarningBlink();break;
        case MatrixAnimation::NFC_WAITING:   updateNfcWaiting();  break;
        case MatrixAnimation::DENIED_CROSS:  updateDeniedCross(); break;
        case MatrixAnimation::NONE:
        default:
            break;
    }
}

void MatrixManager::updateHeartbeat() {
    // Slow pulse: alternate between shield and blank-outline "beat"
    unsigned long now = millis();
    if (now - _lastFrameTime < HEARTBEAT_INTERVAL_MS) {
        return;
    }
    _lastFrameTime = now;
    _frameIndex = (_frameIndex + 1) % 2;
    if (_frameIndex == 0) {
        showShield();
    } else {
        showHeart();
    }
}

void MatrixManager::updateScanning() {
    unsigned long now = millis();
    if (now - _lastFrameTime < 200) {
        return;
    }
    _lastFrameTime = now;
    _frameIndex = (_frameIndex + 1) % 4;
    switch (_frameIndex) {
        case 0: renderFrame(FRAME_SPIN0); break;
        case 1: renderFrame(FRAME_SPIN1); break;
        case 2: renderFrame(FRAME_SPIN2); break;
        case 3: renderFrame(FRAME_SPIN3); break;
    }
}

void MatrixManager::updateWarningBlink() {
    unsigned long now = millis();
    if (now - _lastFrameTime < WARNING_ANIM_INTERVAL_MS) {
        return;
    }
    _lastFrameTime = now;
    _frameIndex = (_frameIndex + 1) % 2;
    if (_frameIndex == 0) {
        showExclamation();
    } else {
        renderFrame(FRAME_BLANK);
    }
}

void MatrixManager::updateNfcWaiting() {
    unsigned long now = millis();
    if (now - _lastFrameTime < 600) {
        return;
    }
    _lastFrameTime = now;
    _frameIndex = (_frameIndex + 1) % 2;
    if (_frameIndex == 0) {
        showScanCard();
    } else {
        renderFrame(FRAME_BLANK);
    }
}

void MatrixManager::updateDeniedCross() {
    unsigned long now = millis();
    if (now - _lastFrameTime < WARNING_ANIM_INTERVAL_MS) {
        return;
    }
    _lastFrameTime = now;
    _frameIndex = (_frameIndex + 1) % 2;
    if (_frameIndex == 0) {
        showCross();
    } else {
        renderFrame(FRAME_BLANK);
    }
}
