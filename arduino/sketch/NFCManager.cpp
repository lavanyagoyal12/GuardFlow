#include "NFCManager.h"

NFCManager::NFCManager()
    : _mfrc522(PIN_RFID_SDA, PIN_RFID_RST), _lastUidSize(0) {
    memset(_lastUid, 0, sizeof(_lastUid));
}

void NFCManager::begin() {
    SPI.begin();
    _mfrc522.PCD_Init();
    // Slightly boost antenna gain for more reliable reads
    _mfrc522.PCD_SetAntennaGain(_mfrc522.RxGain_max);
}

bool NFCManager::poll() {
    // PICC_IsNewCardPresent() + PICC_ReadCardSerial() are both fast,
    // non-blocking-ish calls that return quickly if no card is present.
    if (!_mfrc522.PICC_IsNewCardPresent()) {
        return false;
    }
    if (!_mfrc522.PICC_ReadCardSerial()) {
        // PICC_IsNewCardPresent() succeeded but the anticollision/select
        // sequence failed partway through (common with the MFRC522 lib -
        // timing/collision hiccup). Without this, the chip is left in a
        // half-selected state and won't reliably see the NEXT tap either.
        // Halting here resets it to a known idle state so the next
        // poll() starts clean instead of the reader appearing "stuck".
        _mfrc522.PICC_HaltA();
        return false;
    }

    _lastUidSize = _mfrc522.uid.size;
    for (byte i = 0; i < _lastUidSize && i < sizeof(_lastUid); i++) {
        _lastUid[i] = _mfrc522.uid.uidByte[i];
    }

    _mfrc522.PICC_HaltA();
    _mfrc522.PCD_StopCrypto1();

    return true;
}

bool NFCManager::matchesAuthorized(const byte* uid, byte size) const {
    if (size != AUTHORIZED_UID_LEN) {
        return false;
    }
    for (byte i = 0; i < size; i++) {
        if (uid[i] != AUTHORIZED_UID[i]) {
            return false;
        }
    }
    return true;
}

bool NFCManager::isLastCardAuthorized() const {
    return matchesAuthorized(_lastUid, _lastUidSize);
}

String NFCManager::getLastUidString() const {
    String result = "";
    for (byte i = 0; i < _lastUidSize; i++) {
        if (_lastUid[i] < 0x10) {
            result += "0";
        }
        result += String(_lastUid[i], HEX);
        if (i < _lastUidSize - 1) {
            result += " ";
        }
    }
    result.toUpperCase();
    return result;
}