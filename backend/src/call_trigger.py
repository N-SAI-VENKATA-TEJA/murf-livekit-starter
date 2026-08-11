"""
BoloBuddy Day 6 — Outbound Call Trigger
========================================
A minimal HTTP trigger server that makes Chinnu call a phone number.

Usage
-----
1.  Start the agent first:
        uv run python src/agent.py dev

2.  Start this trigger server:
        uv run python src/call_trigger.py

3.  Trigger a call (replace with your real phone number in E.164 format):
        curl -X POST http://localhost:8089/outbound-call \\
             -H "Content-Type: application/json" \\
             -d '{"phone_number": "+91XXXXXXXXXX"}'

    Optional — include child name so Chinnu greets by name:
        curl -X POST http://localhost:8089/outbound-call \\
             -H "Content-Type: application/json" \\
             -d '{"phone_number": "+91XXXXXXXXXX", "child_name": "Sateesh"}'

Environment variables required (in backend/.env.local)
-------------------------------------------------------
    LIVEKIT_URL                   — wss://your-project.livekit.cloud
    LIVEKIT_API_KEY               — APIxxxxx
    LIVEKIT_API_SECRET            — your secret
    LIVEKIT_SIP_OUTBOUND_TRUNK_ID — ST_xxxxxxxxxxxx  (from LiveKit Cloud → Telephony)

How it works
------------
    POST /outbound-call
         |
         +-- 1. Create a unique LiveKit room
         +-- 2. Dispatch "my-agent" to that room (with outbound metadata)
         +-- 3. Create SIP participant → Twilio dials the phone number
         +-- 4. wait_until_answered=True → call blocks until user picks up
         |
    Chinnu is already in the room when user answers → zero ringback delay.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from dotenv import load_dotenv
from livekit import api as lk_api

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("call-trigger")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(".env.local")

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
LIVEKIT_SIP_OUTBOUND_TRUNK_ID = os.environ.get("LIVEKIT_SIP_OUTBOUND_TRUNK_ID", "")

SERVER_PORT = int(os.environ.get("OUTBOUND_SERVER_PORT", "8089"))

# ---------------------------------------------------------------------------
# Core: outbound call logic
# ---------------------------------------------------------------------------


async def place_outbound_call(phone_number: str, child_name: str = "") -> dict:
    """
    1. Create a unique LiveKit room.
    2. Dispatch 'my-agent' to that room with outbound metadata.
    3. Dial phone_number via SIP (wait_until_answered=True).
    Returns a dict with room_name and status.
    """
    if not LIVEKIT_SIP_OUTBOUND_TRUNK_ID:
        raise RuntimeError(
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not set. "
            "Create an outbound SIP trunk in LiveKit Cloud → Telephony → SIP Trunks, "
            "then add LIVEKIT_SIP_OUTBOUND_TRUNK_ID=ST_xxx to backend/.env.local"
        )

    room_name = f"bolobuddy-call-{uuid.uuid4().hex[:8]}"
    metadata = json.dumps({
        "outbound": True,
        "phone_number": phone_number,
        "child_name": child_name,
    })

    logger.info(
        "[outbound] Starting call → phone=%r  room=%r  child=%r",
        phone_number,
        room_name,
        child_name or "(none)",
    )

    lk = lk_api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )

    try:
        # Step 1 — Create the room so the agent has somewhere to join
        await lk.room.create_room(lk_api.CreateRoomRequest(name=room_name))
        logger.info("[outbound] Room created: %s", room_name)

        # Step 2 — Dial the phone via the configured SIP outbound trunk.
        # wait_until_answered=True blocks until the user picks up (or fails).
        logger.info(
            "[outbound] Dialling %s via trunk %s …",
            phone_number,
            LIVEKIT_SIP_OUTBOUND_TRUNK_ID,
        )
        await lk.sip.create_sip_participant(
            lk_api.CreateSIPParticipantRequest(
                sip_trunk_id=LIVEKIT_SIP_OUTBOUND_TRUNK_ID,
                sip_call_to=phone_number,
                room_name=room_name,
                participant_identity="phone-user",
                participant_name="BoloBuddy Learner",
                wait_until_answered=True,
            )
        )
        logger.info("[outbound] Call answered by %s in room %s", phone_number, room_name)

        # Step 3 — Dispatch the existing Chinnu agent to that room.
        # Since the call is already answered, the agent can start its session and
        # greet immediately without losing the first few seconds of audio to latency.
        await lk.agent_dispatch.create_dispatch(
            lk_api.CreateAgentDispatchRequest(
                agent_name="my-agent",
                room=room_name,
                metadata=metadata,
            )
        )
        logger.info("[outbound] Agent 'my-agent' dispatched to room %s", room_name)

    finally:
        await lk.aclose()

    return {"status": "answered", "room": room_name, "phone_number": phone_number}


# ---------------------------------------------------------------------------
# HTTP server — stdlib only, no FastAPI / Flask needed
# ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    """Handle POST /outbound-call and GET /health."""

    def log_message(self, fmt: str, *args) -> None:  # silence default access logs
        logger.debug(fmt, *args)

    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "bolobuddy-call-trigger"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/outbound-call":
            self._send_json(404, {"error": "not found"})
            return

        # Parse request body
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return

        phone_number = (body.get("phone_number") or "").strip()
        child_name = (body.get("child_name") or "").strip()

        if not phone_number:
            self._send_json(
                400,
                {"error": "phone_number is required (E.164 format, e.g. +91XXXXXXXXXX)"},
            )
            return

        # Submit to the shared asyncio event loop and wait for the result
        loop = self.server._loop  # type: ignore[attr-defined]
        future = asyncio.run_coroutine_threadsafe(
            place_outbound_call(phone_number, child_name), loop
        )
        try:
            result = future.result(timeout=120)  # 2-minute timeout
            self._send_json(200, result)
        except RuntimeError as exc:
            logger.error("[outbound] Configuration error: %s", exc)
            self._send_json(500, {"error": str(exc)})
        except Exception as exc:
            logger.exception("[outbound] Call failed")
            self._send_json(500, {"error": f"Call failed: {exc}"})


class _Server(HTTPServer):
    """HTTPServer that carries a reference to the asyncio event loop."""

    def __init__(self, *args, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop = loop


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _validate_env() -> None:
    missing = []
    for var in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        raise SystemExit(
            f"ERROR: Missing required environment variables: {', '.join(missing)}\n"
            "Make sure backend/.env.local is present and loaded."
        )
    if not LIVEKIT_SIP_OUTBOUND_TRUNK_ID:
        logger.warning(
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not set — calls will fail. "
            "See the Day 6 setup instructions."
        )


def main() -> None:
    _validate_env()

    # Run the asyncio event loop on a background thread so the blocking
    # HTTPServer.serve_forever() and async LiveKit calls can coexist.
    loop = asyncio.new_event_loop()
    t = Thread(target=loop.run_forever, daemon=True)
    t.start()

    server = _Server(("", SERVER_PORT), _Handler, loop=loop)

    logger.info("=" * 60)
    logger.info("BoloBuddy Outbound Call Trigger — Day 6")
    logger.info("Listening on http://localhost:%d", SERVER_PORT)
    logger.info("")
    logger.info("To trigger a call:")
    logger.info(
        "  curl -X POST http://localhost:%d/outbound-call"
        ' -H "Content-Type: application/json"'
        " -d '{\"phone_number\": \"+91XXXXXXXXXX\"}'",
        SERVER_PORT,
    )
    logger.info("")
    logger.info("Make sure the agent is running first:")
    logger.info("  uv run python src/agent.py dev")
    logger.info("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        loop.call_soon_threadsafe(loop.stop)


if __name__ == "__main__":
    main()
