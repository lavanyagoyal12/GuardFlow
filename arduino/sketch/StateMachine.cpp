#include "StateMachine.h"

StateMachine::StateMachine()
    : _state(SystemState::BOOTING),
      _pendingNfcResult(NfcResult::NONE),
      _bootStep(0),
      _bootStepStart(0),
      _stateEnteredAt(0) {}

void StateMachine::begin() {
    _leds.begin();
    _matrix.begin();
    _servo.begin();
    _nfc.begin();

    setState(SystemState::BOOTING);
}

void StateMachine::setState(SystemState newState) {
    _state = newState;
    _stateEnteredAt = millis();

    switch (_state) {
        case SystemState::BOOTING:
            _bootStep = 0;
            _bootStepStart = millis();
            break;

        case SystemState::IDLE:
            _leds.allOff();
            _servo.unlock();
            _matrix.startAnimation(MatrixAnimation::HEARTBEAT);
            break;

        case SystemState::SCANNING:
            _leds.allOff();
            _matrix.startAnimation(MatrixAnimation::SCANNING);
            break;

        case SystemState::LOW_RISK:
            _matrix.stopAnimation();
            _leds.setGreen(LedMode::ON);
            _leds.setYellow(LedMode::OFF);
            _leds.setRed(LedMode::OFF);
            _servo.unlock();
            _matrix.showSafe();
            break;

        case SystemState::MEDIUM_RISK:
            _matrix.stopAnimation();
            _leds.setGreen(LedMode::OFF);
            _leds.setYellow(LedMode::ON);
            _leds.setRed(LedMode::OFF);
            _servo.unlock();
            _matrix.showWarningText();
            _matrix.startAnimation(MatrixAnimation::WARNING_BLINK);
            break;

        case SystemState::HIGH_RISK:
            _leds.setGreen(LedMode::OFF);
            _leds.setYellow(LedMode::OFF);
            _leds.setRed(LedMode::ON);
            _servo.lock();
            _matrix.stopAnimation();
            _matrix.showWarningTriangle();
            break;

        case SystemState::WAITING_FOR_NFC:
            _matrix.startAnimation(MatrixAnimation::NFC_WAITING);
            break;

        case SystemState::AUTHORIZED:
            _matrix.stopAnimation();
            _leds.setRed(LedMode::OFF);
            _leds.setYellow(LedMode::OFF);
            _leds.setGreen(LedMode::ON);
            _servo.unlock();
            _matrix.showOpen();
            _pendingNfcResult = NfcResult::AUTHORIZED;
            break;

        case SystemState::DENIED:
            _matrix.stopAnimation();
            _leds.setGreen(LedMode::OFF);
            _leds.setYellow(LedMode::OFF);
            _leds.setRed(LedMode::BLINK);
            _servo.lock();
            _matrix.startAnimation(MatrixAnimation::DENIED_CROSS);
            _pendingNfcResult = NfcResult::DENIED;
            break;
    }
}

// ---------------------------------------------------------------------
// Commands (called from Python via Bridge)
// ---------------------------------------------------------------------

void StateMachine::cmdBoot()       { setState(SystemState::BOOTING); }
void StateMachine::cmdScan()       { setState(SystemState::SCANNING); }
void StateMachine::cmdLow()        { setState(SystemState::LOW_RISK); }
void StateMachine::cmdMedium()     { setState(SystemState::MEDIUM_RISK); }
void StateMachine::cmdHigh()       { setState(SystemState::HIGH_RISK); }
void StateMachine::cmdAuthorized() { setState(SystemState::AUTHORIZED); }
void StateMachine::cmdDenied()     { setState(SystemState::DENIED); }
void StateMachine::cmdReset()      { setState(SystemState::IDLE); }

int StateMachine::pollNfcResult() {
    int result = static_cast<int>(_pendingNfcResult);
    _pendingNfcResult = NfcResult::NONE; // consume
    return result;
}

const char* StateMachine::getStateName() const {
    switch (_state) {
        case SystemState::BOOTING:         return "BOOTING";
        case SystemState::IDLE:            return "IDLE";
        case SystemState::SCANNING:        return "SCANNING";
        case SystemState::LOW_RISK:        return "LOW_RISK";
        case SystemState::MEDIUM_RISK:     return "MEDIUM_RISK";
        case SystemState::HIGH_RISK:       return "HIGH_RISK";
        case SystemState::WAITING_FOR_NFC: return "WAITING_FOR_NFC";
        case SystemState::AUTHORIZED:      return "AUTHORIZED";
        case SystemState::DENIED:          return "DENIED";
        default:                           return "UNKNOWN";
    }
}

void StateMachine::update() {
    _leds.update();
    _servo.update();
    _matrix.update();

    switch (_state) {
        case SystemState::BOOTING:        updateBooting();       break;
        case SystemState::IDLE:           updateIdle();          break;
        case SystemState::SCANNING:       updateScanning();      break;
        case SystemState::LOW_RISK:       updateLowRisk();       break;
        case SystemState::MEDIUM_RISK:    updateMediumRisk();    break;
        case SystemState::HIGH_RISK:      updateHighRisk();      break;
        case SystemState::WAITING_FOR_NFC:updateWaitingForNfc(); break;
        case SystemState::AUTHORIZED:     updateAuthorized();    break;
        case SystemState::DENIED:         updateDenied();        break;
    }
}

// ---------------------------------------------------------------------
// Per-state update handlers
// ---------------------------------------------------------------------

void StateMachine::updateBooting() {
    unsigned long elapsed = millis() - _bootStepStart;

    switch (_bootStep) {
        case 0:
            _matrix.showHeart();
            if (elapsed >= BOOT_STEP_DURATION_MS) {
                _bootStep = 1;
                _bootStepStart = millis();
            }
            break;
        case 1:
            _matrix.showGF();
            if (elapsed >= BOOT_STEP_DURATION_MS) {
                _bootStep = 2;
                _bootStepStart = millis();
            }
            break;
        case 2:
            _matrix.showShield();
            if (elapsed >= BOOT_STEP_DURATION_MS) {
                _bootStep = 3;
                _bootStepStart = millis();
            }
            break;
        case 3:
        default:
            setState(SystemState::IDLE);
            break;
    }
}

void StateMachine::updateIdle() {
    // Heartbeat animation is handled by MatrixManager::update().
}

void StateMachine::updateScanning() {
    unsigned long elapsed = millis() - _stateEnteredAt;
    if (elapsed >= SCAN_ANIMATION_DURATION_MS) {
        setState(SystemState::IDLE);
    }
}

void StateMachine::updateLowRisk() {
    // Static display, waits for next command from Python.
}

void StateMachine::updateMediumRisk() {
    // Blinking exclamation handled by MatrixManager::update().
}

void StateMachine::updateHighRisk() {
    unsigned long elapsed = millis() - _stateEnteredAt;
    if (elapsed >= 1500) {
        _matrix.showLock();
    }
    if (elapsed >= 2500) {
        setState(SystemState::WAITING_FOR_NFC);
    }
}

void StateMachine::updateWaitingForNfc() {
    unsigned long elapsed = millis() - _stateEnteredAt;

    if (elapsed >= NFC_TIMEOUT_MS) {
        setState(SystemState::IDLE);
        return;
    }

    if (_nfc.poll()) {
        if (_nfc.isLastCardAuthorized()) {
            setState(SystemState::AUTHORIZED);
        } else {
            setState(SystemState::DENIED);
        }
    }
}

void StateMachine::updateAuthorized() {
    unsigned long elapsed = millis() - _stateEnteredAt;
    if (elapsed >= 1200 && elapsed < 1220) {
        _matrix.showCheckmark();
    }
    if (elapsed >= 4000) {
        setState(SystemState::IDLE);
    }
}

void StateMachine::updateDenied() {
    unsigned long elapsed = millis() - _stateEnteredAt;
    if (elapsed >= DENIED_FLASH_DURATION_MS) {
        setState(SystemState::WAITING_FOR_NFC);
    }
}
