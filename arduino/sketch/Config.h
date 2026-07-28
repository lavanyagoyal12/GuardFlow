#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ================== SERIAL ==================
#define SERIAL_BAUD 115200

// ================== PINS =====================
#define PIN_LED_GREEN   2
#define PIN_LED_YELLOW  3
#define PIN_LED_RED     4
#define PIN_SERVO       5
#define PIN_BUZZER      6

#define PIN_RFID_SDA    10
#define PIN_RFID_SCK    13
#define PIN_RFID_MOSI   11
#define PIN_RFID_MISO   12
#define PIN_RFID_RST    9

// ================== SERVO ANGLES =============
#define SERVO_LOCK_ANGLE    0
#define SERVO_UNLOCK_ANGLE  90
#define SERVO_STEP_DELAY_MS 15   // ms between 1-degree steps for smooth movement

// ================== TIMING ====================
#define SCAN_ANIMATION_DURATION_MS   3000
#define NFC_TIMEOUT_MS               20000
#define HEARTBEAT_INTERVAL_MS        1500
#define BLINK_INTERVAL_MS            400
#define BOOT_STEP_DURATION_MS        900
#define WARNING_ANIM_INTERVAL_MS     500
#define BUZZER_BEEP_INTERVAL_MS      300   // on/off toggle period while alarming
#define DENIED_FLASH_DURATION_MS     2000

// ================== AUTHORIZED CARD ===========
// Example authorized UID: 73 A2 91 C4
#define AUTHORIZED_UID_LEN 4
static const byte AUTHORIZED_UID[AUTHORIZED_UID_LEN] = {0x8D, 0x1E, 0x03, 0x07};

// ================== SYSTEM STATES =============
enum class SystemState {
    BOOTING,
    IDLE,
    SCANNING,
    LOW_RISK,
    MEDIUM_RISK,
    HIGH_RISK,
    WAITING_FOR_NFC,
    AUTHORIZED,
    DENIED
};

#endif // CONFIG_H