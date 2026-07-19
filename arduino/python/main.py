#!/usr/bin/env python3
"""
GuardFlow - Production Backend <-> Arduino Integration
Python App (Linux/MPU side) for Arduino UNO Q - Arduino App Lab

Flow:
    FastAPI backend (POST /api/v1/score/{session_id}) creates a
    RiskAssessment row whenever the risk engine finishes scoring a
    session.
        |
        v (this script polls)
    GET  {BACKEND_BASE_URL}/api/v1/risk/latest
        |
        v  new assessment (unseen id) with level LOW/MEDIUM/HIGH/CRITICAL
    Bridge.call("cmd_low" | "cmd_medium" | "cmd_high")   [HIGH sent ONCE]
        |
        v  sketch StateMachine drives LEDs/servo/matrix, and for HIGH
        |  auto-enters WAITING_FOR_NFC after ~2.5s
        v
    Bridge.call("poll_nfc_result")  -> 0 none / 1 AUTHORIZED / 2 DENIED
        |
        v
    POST {BACKEND_BASE_URL}/api/v1/risk/{assessment_id}/nfc-result
         body: {"result": "AUTHORIZED" | "DENIED"}

Two independent worker threads:
    - backend_worker: polls for new assessments, dispatches to the MCU
    - nfc_worker:      polls the MCU for NFC results, reports them back

They only interact through a small set of lock-protected shared
variables (see SharedState below) - never blocking each other.

Requires the `requests` package on the board's Python environment:
    pip3 install requests --break-system-packages
"""

import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests
from arduino.app_utils import Bridge

# ======================================================================
# CONFIGURATION
# ======================================================================

# Base URL of the FastAPI backend. Override by editing this constant or
# (preferably) via the BACKEND_BASE_URL environment variable so the same
# code works whether the backend runs on your laptop's LAN IP, localhost
# (if colocated), or anything else - no code change needed per demo.
import os
print("MAIN.PY HAS STARTED", flush=True)

BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://172.20.10.2:8000")

LATEST_RISK_ENDPOINT = "/api/v1/risk/latest"
NFC_RESULT_ENDPOINT_TEMPLATE = "/api/v1/risk/{assessment_id}/nfc-result"
HEALTH_ENDPOINT = "/health"

BACKEND_POLL_INTERVAL_S = 2.0
NFC_POLL_INTERVAL_S = 0.5
HTTP_TIMEOUT_S = 5.0

# How long to wait after a failed backend request before retrying, and
# the cap on exponential backoff so a long outage doesn't turn into an
# hours-long wait between retries.
RETRY_BASE_DELAY_S = 2.0
RETRY_MAX_DELAY_S = 30.0

# Risk levels returned by the backend (schemas/risk_schema.py) map to
# these Bridge functions. CRITICAL has no dedicated Arduino command, so
# it is treated the same as HIGH (lock + wait for NFC) - the sketch
# only understands LOW/MEDIUM/HIGH.
LEVEL_TO_BRIDGE_FUNCTION = {
    "LOW": "cmd_low",
    "MEDIUM": "cmd_medium",
    "HIGH": "cmd_high",
    "CRITICAL": "cmd_high",
}

NFC_NONE = 0
NFC_AUTHORIZED = 1
NFC_DENIED = 2
NFC_RESULT_NAMES = {NFC_AUTHORIZED: "AUTHORIZED", NFC_DENIED: "DENIED"}

# ======================================================================
# LOGGING
# ======================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GuardFlow] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("guardflow")


# ======================================================================
# SHARED STATE (thread-safe)
# ======================================================================

@dataclass
class ActiveHighRiskAssessment:
    """Tracks the assessment currently waiting on an NFC confirmation,
    so the NFC worker knows which backend row to report the result
    against once a card is tapped.
    """
    assessment_id: str
    session_id: str


class SharedState:
    def __init__(self):
        self._lock = threading.Lock()
        self._last_processed_assessment_id: Optional[str] = None
        self._active_high_risk: Optional[ActiveHighRiskAssessment] = None

    def already_processed(self, assessment_id: str) -> bool:
        with self._lock:
            return self._last_processed_assessment_id == assessment_id

    def mark_processed(self, assessment_id: str) -> None:
        with self._lock:
            self._last_processed_assessment_id = assessment_id

    def set_active_high_risk(self, assessment_id: str, session_id: str) -> None:
        with self._lock:
            self._active_high_risk = ActiveHighRiskAssessment(assessment_id, session_id)

    def pop_active_high_risk(self) -> Optional[ActiveHighRiskAssessment]:
        """Consume (and clear) the assessment currently awaiting an NFC result."""
        with self._lock:
            active = self._active_high_risk
            self._active_high_risk = None
            return active

    def has_active_high_risk(self) -> bool:
        with self._lock:
            return self._active_high_risk is not None


state = SharedState()


# ======================================================================
# BACKEND HTTP CLIENT
# ======================================================================

def backend_url(path: str) -> str:
    return f"{BACKEND_BASE_URL.rstrip('/')}{path}"


def check_backend_health() -> bool:
    try:
        resp = requests.get(backend_url(HEALTH_ENDPOINT), timeout=HTTP_TIMEOUT_S)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def fetch_latest_assessment() -> Optional[dict]:
    """GET /api/v1/risk/latest. Returns the parsed JSON dict, or None if
    unavailable (no assessments yet, or the request failed)."""
    try:
        resp = requests.get(backend_url(LATEST_RISK_ENDPOINT), timeout=HTTP_TIMEOUT_S)
    except requests.RequestException as exc:
        log.warning(f"Backend unreachable while fetching latest assessment: {exc}")
        return None

    if resp.status_code == 404:
        return None  # no assessments exist yet - not an error
    if resp.status_code != 200:
        log.warning(f"Unexpected status {resp.status_code} from {LATEST_RISK_ENDPOINT}")
        return None

    try:
        return resp.json()
    except ValueError as exc:
        log.warning(f"Malformed JSON from {LATEST_RISK_ENDPOINT}: {exc}")
        return None


def report_nfc_result(assessment_id: str, result_name: str) -> bool:
    """POST the NFC outcome back to the backend. Returns True on success."""
    url = backend_url(NFC_RESULT_ENDPOINT_TEMPLATE.format(assessment_id=assessment_id))
    try:
        resp = requests.post(url, json={"result": result_name}, timeout=HTTP_TIMEOUT_S)
    except requests.RequestException as exc:
        log.error(f"Failed to report NFC result to backend: {exc}")
        return False

    if resp.status_code == 200:
        log.info("NFC result reported successfully")
        return True

    log.error(f"Backend rejected NFC result report: {resp.status_code} {resp.text}")
    return False


# ======================================================================
# ARDUINO BRIDGE HELPERS
# ======================================================================

def bridge_call_safe(function_name: str) -> bool:
    """Call a Bridge-exposed MCU function, logging (not raising) on failure."""
    try:
        Bridge.call(function_name)
        return True
    except Exception as exc:
        log.error(f"Bridge call failed for {function_name}: {exc}")
        return False


def poll_nfc_result() -> int:
    try:
        return int(Bridge.call("poll_nfc_result"))
    except Exception as exc:
        log.error(f"Bridge poll_nfc_result failed: {exc}")
        return NFC_NONE


def get_mcu_state_name() -> str:
    try:
        return str(Bridge.call("get_state_name"))
    except Exception:
        return "UNKNOWN"


# ======================================================================
# WORKER: backend polling -> dispatch risk verdicts to the MCU
# ======================================================================

def backend_worker():
    log.info(f"Backend worker starting (polling {BACKEND_BASE_URL} every "
              f"{BACKEND_POLL_INTERVAL_S}s)")

    retry_delay = RETRY_BASE_DELAY_S
    backend_was_up = None  # tri-state: None = unknown yet

    while True:
        assessment = fetch_latest_assessment()

        if assessment is None:
            if backend_was_up is not False:
                log.warning("Backend unavailable or has no assessments yet - retrying")
                backend_was_up = False
            time.sleep(min(retry_delay, RETRY_MAX_DELAY_S))
            retry_delay = min(retry_delay * 2, RETRY_MAX_DELAY_S)
            continue

        if backend_was_up is not True:
            log.info("Backend connected")
            backend_was_up = True
        retry_delay = RETRY_BASE_DELAY_S  # reset backoff after a success

        assessment_id = assessment.get("id")
        session_id = assessment.get("session_id")
        level = str(assessment.get("level", "")).upper()
        score = assessment.get("score")

        if assessment_id and not state.already_processed(assessment_id):
            log.info(
                f"New assessment: session={session_id}, score={score}, level={level}"
            )

            bridge_function = LEVEL_TO_BRIDGE_FUNCTION.get(level)
            if bridge_function is None:
                log.warning(f"Unrecognized risk level {level!r} - ignoring")
            else:
                # Mark processed BEFORE dispatching so a slow/failed Bridge
                # call can't cause this same assessment to be picked up
                # again by the next poll and re-fired (this is what makes
                # cmd_high fire exactly once per assessment, unlike the
                # test script's 18s re-arm loop).
                state.mark_processed(assessment_id)

                log.info(f"-> MCU: {bridge_function}()")
                bridge_call_safe(bridge_function)

                if level in ("HIGH", "CRITICAL"):
                    state.set_active_high_risk(assessment_id, session_id)
                    log.info(f"MCU state: {get_mcu_state_name()}")

        time.sleep(BACKEND_POLL_INTERVAL_S)


# ======================================================================
# WORKER: NFC polling -> report results back to the backend
# ======================================================================

def nfc_worker():
    log.info(f"NFC worker starting (polling every {NFC_POLL_INTERVAL_S}s)")

    while True:
        result = poll_nfc_result()

        if result in (NFC_AUTHORIZED, NFC_DENIED):
            result_name = NFC_RESULT_NAMES[result]
            log.info(f"NFC: {result_name}")

            active = state.pop_active_high_risk()
            if active is None:
                # The MCU resolved a card tap but we have no assessment on
                # file waiting for one (e.g. board was manually put into
                # WAITING_FOR_NFC, or this is a stale/duplicate read).
                # Hardware state is already handled by the sketch either
                # way - just skip the backend report since there's no
                # assessment_id to attach it to.
                log.warning(
                    "NFC result resolved but no active HIGH-risk assessment "
                    "was on file - not reporting to backend"
                )
            else:
                report_nfc_result(active.assessment_id, result_name)

        time.sleep(NFC_POLL_INTERVAL_S)


# ======================================================================
# MAIN
# ======================================================================

def main():
    log.info("GuardFlow starting...")

    log.info("-> MCU: cmd_boot()")
    bridge_call_safe("cmd_boot")
    time.sleep(4)  # let the boot animation (heart -> GF -> shield) finish

    if check_backend_health():
        log.info("Backend connected")
    else:
        log.warning(
            f"Backend not reachable yet at {BACKEND_BASE_URL} - will keep "
            "retrying in the background"
        )

    backend_thread = threading.Thread(target=backend_worker, daemon=True)
    nfc_thread = threading.Thread(target=nfc_worker, daemon=True)

    backend_thread.start()
    nfc_thread.start()

    log.info("GuardFlow running. Backend and NFC workers active.")

    # Keep the main thread alive (App Lab stops the app if main.py exits).
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()


# #!/usr/bin/env python3
# """
# GuardFlow - NFC-FOCUSED TEST MODE

# Skips straight to the HIGH risk state (locks the servo, puts the board
# into WAITING_FOR_NFC) and then continuously polls for NFC results so
# you can tap your card as many times as you want without re-running
# the whole BOOT/SCAN/LOW/MEDIUM sequence each time.

# Note: sketch/StateMachine.cpp auto-returns to IDLE after
# NFC_TIMEOUT_MS (20s, see Config.h) if no card is tapped. This script
# re-sends cmd_high every 18s so the board never falls out of
# WAITING_FOR_NFC while you're testing.
# """

# import time
# from arduino.app_utils import Bridge

# NFC_NONE = 0
# NFC_AUTHORIZED = 1
# NFC_DENIED = 2

# RE_ARM_INTERVAL_S = 18  # must be < NFC_TIMEOUT_MS (20s) in Config.h


# def call(bridge_function: str):
#     print(f"[GuardFlow-NFC] -> MCU: {bridge_function}()")
#     try:
#         Bridge.call(bridge_function)
#     except Exception as exc:
#         print(f"[GuardFlow-NFC] Bridge call failed for {bridge_function}: {exc}")


# def check_nfc_once():
#     try:
#         result = int(Bridge.call("poll_nfc_result"))
#         if result == NFC_AUTHORIZED:
#             print("[GuardFlow-NFC] *** RESULT: AUTHORIZED *** (card UID matched)")
#         elif result == NFC_DENIED:
#             print("[GuardFlow-NFC] *** RESULT: DENIED *** (card UID did not match)")
#         # NFC_NONE -> stay quiet, don't spam the console every second
#     except Exception as exc:
#         print(f"[GuardFlow-NFC] Bridge poll_nfc_result failed: {exc}")


# def main():
#     print("GuardFlow NFC TEST starting.\n")
#     print("Boot + arm the lock so the board enters WAITING_FOR_NFC...\n")

#     call("cmd_boot")
#     time.sleep(4)  # let the boot animation finish

#     call("cmd_high")
#     print("\nBoard should now be RED / locked / matrix showing lock+wait animation.")
#     print("Tap your card on the RC522 any time. Re-arming every "
#           f"{RE_ARM_INTERVAL_S}s so it never times out.\n")

#     last_rearm = time.monotonic()

#     while True:
#         check_nfc_once()

#         if time.monotonic() - last_rearm >= RE_ARM_INTERVAL_S:
#             call("cmd_high")  # re-send HIGH to keep it armed / waiting for NFC
#             last_rearm = time.monotonic()

#         time.sleep(1)


# if __name__ == "__main__":
#     main()

# # #!/usr/bin/env python3
# # """
# # GuardFlow - AUTO TEST MODE (no backend, no keyboard input needed)

# # App Lab's console does not support interactive stdin, so input()-based
# # testing hangs/exits immediately. This script instead runs a fixed,
# # timed sequence of commands automatically so you can watch the LEDs,
# # servo, and matrix react without typing anything.

# # Just hit Run in App Lab and watch the console + hardware.

# # Once your backend is ready, swap this file's content back for the real
# # Serial-based main.py - nothing on the sketch side changes.
# # """

# # import time
# # from arduino.app_utils import Bridge

# # NFC_NONE = 0
# # NFC_AUTHORIZED = 1
# # NFC_DENIED = 2


# # def call(bridge_function: str, wait_after_s: float = 3.0):
# #     print(f"[GuardFlow-AUTO] -> MCU: {bridge_function}()")
# #     try:
# #         Bridge.call(bridge_function)
# #     except Exception as exc:
# #         print(f"[GuardFlow-AUTO] Bridge call failed for {bridge_function}: {exc}")
# #     time.sleep(wait_after_s)


# # def check_nfc_once():
# #     try:
# #         result = int(Bridge.call("poll_nfc_result"))
# #         if result == NFC_AUTHORIZED:
# #             print("[GuardFlow-AUTO] *** NFC RESULT: AUTHORIZED ***")
# #         elif result == NFC_DENIED:
# #             print("[GuardFlow-AUTO] *** NFC RESULT: DENIED ***")
# #         else:
# #             print("[GuardFlow-AUTO] NFC result: none yet")
# #     except Exception as exc:
# #         print(f"[GuardFlow-AUTO] Bridge poll_nfc_result failed: {exc}")


# # def main():
# #     print("GuardFlow AUTO TEST starting - watch the LEDs / matrix / servo.\n")

# #     print("=== Step 1: BOOT ===")
# #     call("cmd_boot", wait_after_s=4)

# #     print("=== Step 2: SCAN ===")
# #     call("cmd_scan", wait_after_s=4)

# #     print("=== Step 3: LOW (green, unlocked) ===")
# #     call("cmd_low", wait_after_s=4)

# #     print("=== Step 4: MEDIUM (yellow, unlocked) ===")
# #     call("cmd_medium", wait_after_s=4)

# #     print("=== Step 5: HIGH (red, locks, then waits for NFC) ===")
# #     call("cmd_high", wait_after_s=4)

# #     print("=== Step 6: tap your card now - checking result for 15s ===")
# #     for _ in range(15):
# #         check_nfc_once()
# #         time.sleep(1)

# #     print("=== Step 7: RESET ===")
# #     call("cmd_reset", wait_after_s=2)

# #     print("\n[GuardFlow-AUTO] Sequence complete. Sketch is now idle.")
# #     print("[GuardFlow-AUTO] Script will now idle-loop so the app keeps running.")

# #     # Keep the app alive (App Lab stops the app if main.py exits),
# #     # while continuously watching for NFC taps in the background.
# #     while True:
# #         check_nfc_once()
# #         time.sleep(1)


# # if __name__ == "__main__":
# #     main()