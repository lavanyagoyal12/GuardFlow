#ifndef NFC_MANAGER_H
#define NFC_MANAGER_H

#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include "Config.h"

class NFCManager {
public:
    NFCManager();

    void begin();

    // Non-blocking poll. Returns true if a NEW card was read this call.
    bool poll();

    // Compares the last-read UID against the authorized UID stored in Config.h
    bool isLastCardAuthorized() const;

    // Human readable UID string of the last card read (e.g. "73 A2 91 C4")
    String getLastUidString() const;

private:
    MFRC522 _mfrc522;
    byte _lastUid[10];
    byte _lastUidSize;

    bool matchesAuthorized(const byte* uid, byte size) const;
};

#endif // NFC_MANAGER_H
