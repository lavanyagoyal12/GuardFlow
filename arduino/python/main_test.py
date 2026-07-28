# #!/usr/bin/env python3
# """
# GuardFlow - TEST MODE (no backend needed)

# This is a drop-in replacement for python/main.py that lets you test the
# whole state machine (LEDs, servo, matrix, NFC) by typing commands
# directly into the App Lab console, instead of waiting for a real AI
# backend to be wired up over Serial.

# Type any of: BOOT, SCAN, LOW, MEDIUM, HIGH, AUTHORIZED, DENIED, RESET
# then press Enter. Type EXIT or QUIT to stop.

# Once your backend is ready, swap this file back for the real
# python/main.py (the Serial-based one) - nothing on the sketch side
# needs to change, since both talk to the MCU through the same Bridge
# functions.
# """

# import sys
# import time
# import threading

# from arduino.app_utils import Bridge

# VALID_COMMANDS = {
#     "BOOT": "cmd_boot",
#     "SCAN": "cmd_scan",
#     "LOW": "cmd_low",
#     "MEDIUM": "cmd_medium",
#     "HIGH": "cmd_high",
#     "AUTHORIZED": "cmd_authorized",
#     "DENIED": "cmd_denied",
#     "RESET": "cmd_reset",
# }

# NFC_POLL_INTERVAL_S = 0.2

# NFC_NONE = 0
# NFC_AUTHORIZED = 1
# NFC_DENIED = 2

# _stop_flag = False


# def dispatch_to_mcu(command: str):
#     bridge_function = VALID_COMMANDS.get(command)
#     if bridge_function is None:
#         print(f"[GuardFlow-TEST] Unknown command: {command!r} "
#               f"(valid: {', '.join(VALID_COMMANDS.keys())})")
#         return
#     try:
#         Bridge.call(bridge_function)
#         print(f"[GuardFlow-TEST] -> MCU: {bridge_function}()")
#     except Exception as exc:
#         print(f"[GuardFlow-TEST] Bridge call failed for {bridge_function}: {exc}")


# def nfc_poll_loop():
#     """Background thread: watches for NFC results and prints them."""
#     while not _stop_flag:
#         try:
#             result = int(Bridge.call("poll_nfc_result"))
#             if result == NFC_AUTHORIZED:
#                 print("\n[GuardFlow-TEST] *** NFC RESULT: AUTHORIZED ***")
#             elif result == NFC_DENIED:
#                 print("\n[GuardFlow-TEST] *** NFC RESULT: DENIED ***")
#         except Exception as exc:
#             print(f"[GuardFlow-TEST] Bridge poll_nfc_result failed: {exc}")
#         time.sleep(NFC_POLL_INTERVAL_S)


# def keyboard_loop():
#     global _stop_flag
#     print("GuardFlow TEST MODE - no backend required.")
#     print("Type a command and press Enter:")
#     print("  BOOT SCAN LOW MEDIUM HIGH AUTHORIZED DENIED RESET  |  EXIT to quit\n")

#     while True:
#         try:
#             line = input("> ").strip().upper()
#         except (EOFError, KeyboardInterrupt):
#             break

#         if not line:
#             continue
#         if line in ("EXIT", "QUIT"):
#             break

#         dispatch_to_mcu(line)

#     _stop_flag = True


# def main():
#     poller = threading.Thread(target=nfc_poll_loop, daemon=True)
#     poller.start()
#     keyboard_loop()
#     print("\n[GuardFlow-TEST] Stopped.")


# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         sys.exit(0)
