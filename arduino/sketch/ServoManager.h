#ifndef SERVO_MANAGER_H
#define SERVO_MANAGER_H

#include <Arduino.h>
#include <Servo.h>
#include "Config.h"

class ServoManager {
public:
    ServoManager();

    void begin();

    // Request a target angle; movement is smooth and non-blocking
    void moveTo(int targetAngle);

    void lock();
    void unlock();

    bool isLocked() const;
    bool isMoving() const;

    // Must be called every loop() iteration
    void update();

private:
    Servo _servo;
    int _currentAngle;
    int _targetAngle;
    unsigned long _lastStepTime;
};

#endif // SERVO_MANAGER_H
