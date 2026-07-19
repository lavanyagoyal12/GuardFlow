## GuardFlow

> **An AI-powered multi-device fraud prevention system that protects users from phishing attacks, fake payment portals, scholarship scams, QR frauds, and other online financial threats before money is lost.**

GuardFlow combines an **Android application**, **Browser Extension**, **AI PC Backend**, and **Arduino-based hardware authentication** into a single intelligent security ecosystem. By correlating events across multiple devices, GuardFlow can detect suspicious activities in real time and warn users before they complete a risky transaction.

---

# Project Description 

### Android App

The Android application acts as the central dashboard.

Responsibilities:
- Show AI explanations
- Receive backend responses
- Receive NFC verification
- User interaction

### Browser Extension


Purpose : Stop phishing before users submit information.

How it works:
- Detects current webpage
- Extracts URL
- Sends URL to backend
- Waits for AI analysis
- Displays warning popup

### AI PC Backend

The backend is the brain of GuardFlow.

Responsibilities:
- Receive requests
- Analyze websites
- Calculate risk
- Generate explanations
- Return recommendations


### Arduino Device

Purpose:
Provide secure, contactless identity verification using NFC technology.

Responsibilities:
- Read NFC card UID
- Send UID to Android App
- Verify authorized users
- Trigger access decision
- Enable real-time authentication


# Features
- Detects phishing and scam websites
- Live webpage analysis through Browser Extension
- AI-generated fraud explanations
- Deterministic risk scoring (0–100)
- Multilingual voice alerts
- Real-time Android notifications
- NFC-based physical verification for high-risk payments
- FastAPI backend with WebSocket communication
- Local event storage and session tracking
---

# Tech Stack

| Component | Technologies |
|-----------|--------------|
| Android App | Kotlin, Jetpack Compose, CameraX(YOLO) |
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| Browser Extension | JavaScript, Chrome Extension (Manifest V3) |
| AI | Qualcomm GenieX, Qwen, Sarvam AI, Bulbul v3 |
| Hardware | Arduino UNO R4 WiFi, RC522 NFC, Servo, LEDs, Buzzer |
| Communication | REST APIs, WebSockets, JSON |

---

# Complete System Setup

## Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/GuardFlow.git

cd GuardFlow
```

---

## Step 2 — AI PC Backend

1. Navigate to the backend folder.

```bash
cd AI_PC_Backend
```

2. Create a virtual environment.

```bash
python -m venv .venv
```

3. Activate the virtual environment.

### Windows

```powershell
.\.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

4. Install the required dependencies.

```bash
pip install -r requirements.txt
```

5. Create a configuration file.

```bash
cp .env.example .env
```

Open `.env` and update the required values:

```env
SARVAM_API_KEY=your_api_key
LLM_MODEL=Qwen/Qwen2.5-3B-Instruct
HOST=0.0.0.0
PORT=8000
```

6. Start the backend server.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify that the backend is running:

```
http://localhost:8000/docs
```

---

## Step 3 — Browser Extension

1. Open Chrome and navigate to:

```
chrome://extensions
```

2. Enable **Developer Mode**.

3. Click **Load unpacked**.

4. Select the `Browser_Extension` folder.

5. Update the backend WebSocket URL if required.

Example:

```javascript
const WS_URL = "ws://<AI_PC_IP>:8000/ws";
```

6. Reload the extension.

7. Open the extension popup and verify it shows:

```
Connected
```

---

## Step 4 — Android App

1. Open the project in Android Studio.

```
File
    → Open
        → Android_App/
```

2. Allow **Gradle Sync** to complete.

3. Update the backend API URL.

Example:

```kotlin
const val BASE_URL = "http://<AI_PC_IP>:8000/api/v1/"
```

4. Build the project.

```
Build
    → Make Project
```

or

```
Ctrl + F9
```

5. Run the application.

```
Run
    → Run 'app'
```

or

```
Shift + F10
```

6. Grant all required permissions:

- Accessibility Service
- Camera
- Notifications
- Internet

7. Verify that the app opens successfully and connects to the backend.

---

## Step 5 — Arduino Device

1. Open the Arduino project in **Arduino App Lab**.

```
File
    → Open
        → Arduino/
```

2. Install the required libraries.

Open:

```
Tools
    → Manage Libraries
```

Install:

- Servo
- MFRC522

3. Connect the hardware.

| Component | Pin |
|-----------|-----|
| Green LED | D2 |
| Yellow LED | D3 |
| Red LED | D4 |
| Servo | D5 |
| Buzzer | D6 |
| RC522 | SPI |

4. Configure the backend IP address.

Example:

```python
BACKEND_BASE_URL = "http://<AI_PC_IP>:8000"
```

5. Upload the firmware.

```
Sketch
    → Upload
```

or click the **Upload (→)** button.

6. Register the authorized NFC card using its UID.

Run the discovery sketch.

Open the Serial Monitor.

```
Tools
    → Serial Monitor
```

Tap the NFC card.

Example output:

```
Detected UID:
73 A2 91 C4
```

Copy the UID into:

```cpp
Config.h

AUTHORIZED_UID = {0x73, 0xA2, 0x91, 0xC4};
```

Upload the final firmware again.

7. Verify the device.

- LEDs turn on correctly.
- Servo locks and unlocks.
- NFC card is detected.
- Device communicates with the backend.

# Start the Complete System

Start each component in the following order:

1. Start GenieX (Local AI)
2. Start the AI PC Backend
3. Load the Browser Extension
4. Launch the Android App
5. Power the Arduino Device
6. Perform the demo

Following this sequence ensures that every component can communicate correctly with the others.

---
# Complete Workflow

```text
User Opens Website
        │
        ▼
Android detects event
        │
        ▼
Backend receives event
        │
        ▼
Browser Extension analyzes webpage
        │
        ▼
Signals stored in Database
        │
        ▼
Risk Engine calculates score
        │
        ▼
AI generates explanation
        │
        ▼
Translation + Voice Generation
        │
        ▼
Android displays warning
        │
        ▼
High Risk?
   │              │
  No             Yes
   │              │
Continue     Arduino requests
             NFC Verification
```

---

# Future Scope

- Cloud-based threat intelligence
- Machine Learning-based behavioral analysis
- Support for multiple browsers
- Banking API integration
- Smartwatch notifications
- Enterprise dashboard
- Additional language support
- Federated learning for improved privacy

---

# License

This project is developed for educational, research, and hackathon purposes.

Feel free to use, modify, and extend the project with proper attribution to the contributors.

#

**Team**
| Name | Email |
|------|-------|
| Ashika  | ashikajain2401@gmail.com |
| Chhavi  | goelchhavi090@gmail.com |
| Lavanya | lavanyagoyal1212@gmail.com |
| Piyush  | piyushkumarb2510@gmail.com |
| Uday    | udayverma112006@gmail.com |

