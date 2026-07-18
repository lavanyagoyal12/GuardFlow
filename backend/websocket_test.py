import asyncio
import json
import websockets
import uuid
from datetime import datetime, timezone


async def test():

    uri = "ws://127.0.0.1:8000/ws"

    try:

        async with websockets.connect(uri) as websocket:

            print("✅ Connected to server")

            sample = {
                "event_id": str(uuid.uuid4()),
                "session_id": "ABC123",
                "event_type": "WEBSITE_OPENED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_app": "chrome_extension",
                "payload": {
                    "url": "https://fake-scholarship.xyz",
                    "title": "Scholarship Portal",
                    "text": "Pay ₹500 registration fee"
                }
            }

            await websocket.send(json.dumps(sample))

            print("✅ JSON Sent")

            response = await websocket.recv()

            print("Server Response:", response)

    except Exception as e:

        print(type(e).__name__)
        print(e)


asyncio.run(test())