# GuardFlow (Arduino App Lab App)

AI-powered fraud detection peripheral controller for the Arduino UNO Q.

## Architecture

```
AI Backend (FastAPI, on a separate PC)
        │  USB Serial (one-word commands)
        ▼
python/main.py            <-- runs on UNO Q Linux/MPU side (QRB2210)
        │  Arduino Bridge (Bridge.call / Bridge.provide)
        ▼
sketch/GuardFlow.ino       <-- runs on UNO Q microcontroller (STM32)
        │
        ├─ LEDManager    -> Green / Yellow / Red status LEDs
        ├─ ServoManager   -> SG90 lock servo
        ├─ MatrixManager  -> built-in 12x8 LED matrix
        └─ NFCManager     -> RC522 NFC reader
```

The MCU sketch does **no** fraud-detection logic. It only reacts to
commands relayed from Python and reports NFC tap results back.

## Folder layout

```
GuardFlow/
├── app.yaml              # App Lab project config
├── README.md
├── python/
│   └── main.py            # Backend Serial <-> Bridge relay
└── sketch/
    ├── GuardFlow.ino       # setup()/loop(), Bridge.provide() registrations
    ├── Config.h            # pins, timing constants, state enum
    ├── LEDManager.h/.cpp
    ├── ServoManager.h/.cpp
    ├── MatrixManager.h/.cpp
    ├── NFCManager.h/.cpp
    └── StateMachine.h/.cpp
```

## Setup

1. In Arduino App Lab, create a new empty App and replace its generated
   `python/` and `sketch/` folders with the ones in this project (or
   import this project directly if your App Lab version supports
   zip import).
2. Wire the hardware per the pin map in `sketch/Config.h`:
   - Green LED = D2, Yellow LED = D3, Red LED = D4
   - Servo = D5
   - RC522: SDA=D10, SCK=D13, MOSI=D11, MISO=D12, RST=D9
3. In App Lab's Library Manager (for the sketch side), install
   `MFRC522` (by miguelbalboa / GithubCommunity). `Servo` and
   `Arduino_LED_Matrix` ship with the UNO Q core.
4. Edit `BACKEND_SERIAL_PORT` in `python/main.py` to match how your AI
   backend PC is physically connected to the UNO Q's Linux side (e.g.
   a USB-serial adapter port such as `/dev/ttyUSB0`, or `/dev/ttyACM0`).
5. Update `AUTHORIZED_UID` in `sketch/Config.h` with your real NFC
   card's UID if it differs from the placeholder `73 A2 91 C4`.
6. Click **Run** in App Lab. This builds/flashes the sketch to the
   STM32 and starts `python/main.py` on the Linux side.

## Protocol (backend -> UNO Q, over Serial, one word per line)

`BOOT`, `SCAN`, `LOW`, `MEDIUM`, `HIGH`, `AUTHORIZED`, `DENIED`, `RESET`

## Protocol (UNO Q -> backend, over Serial)

`AUTHORIZED` or `DENIED`, sent once after a card is tapped while the
board is in `WAITING_FOR_NFC`.
