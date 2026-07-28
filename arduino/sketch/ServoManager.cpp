#include "ServoManager.h"

ServoManager::ServoManager()
    : _currentAngle(SERVO_UNLOCK_ANGLE),
      _targetAngle(SERVO_UNLOCK_ANGLE),
      _lastStepTime(0) {}

void ServoManager::begin() {
    _servo.attach(PIN_SERVO);
    _currentAngle = SERVO_UNLOCK_ANGLE;
    _targetAngle = SERVO_UNLOCK_ANGLE;
    _servo.write(_currentAngle);
}

void ServoManager::moveTo(int targetAngle) {
    _targetAngle = constrain(targetAngle, 0, 180);
}

void ServoManager::lock() {
    moveTo(SERVO_LOCK_ANGLE);
}

void ServoManager::unlock() {
    moveTo(SERVO_UNLOCK_ANGLE);
}

bool ServoManager::isLocked() const {
    return _currentAngle == SERVO_LOCK_ANGLE;
}

bool ServoManager::isMoving() const {
    return _currentAngle != _targetAngle;
}

void ServoManager::update() {
    if (_currentAngle == _targetAngle) {
        return;
    }

    unsigned long now = millis();
    if (now - _lastStepTime < SERVO_STEP_DELAY_MS) {
        return;
    }
    _lastStepTime = now;

    if (_currentAngle < _targetAngle) {
        _currentAngle++;
    } else {
        _currentAngle--;
    }

    _servo.write(_currentAngle);
}
