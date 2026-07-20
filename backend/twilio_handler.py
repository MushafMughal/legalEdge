"""Twilio Media Streams <-> Gemini Live bridge for one inbound intake call.

Audio in:  Twilio mu-law 8kHz -> PCM16 16kHz -> Gemini (send_realtime_input)
Audio out: Gemini PCM16 24kHz -> mu-law 8kHz -> Twilio (160-byte frames)
Both directions and the Gemini receive loop run as concurrent asyncio tasks.

Structurally identical to the screening twilio_handler; the only LegalEdge
differences are (a) the two intake tools, (b) the intake prompt, and (c)
_end_call_handler persisting to SQLite + calling the CRM stub.
"""
import asyncio
import base64
import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

import pytz

import config
import legaledge_client
import store
from audio import GeminiToTwilioResampler, TwilioToGeminiResampler
from gemini_live import GeminiLivePhone
from intake_tools import (
    submit_case_details_tool,
    submit_contact_details_tool,
    submit_injury_details_tool,
)
from prompts import build_intake_prompt

logger = logging.getLogger(__name__)

MULAW_FRAME_SIZE = 160  # 20ms @ 8kHz mu-law
CALL_TIMEOUT_SECONDS = 600  # 10 min hard cap


def _now_epoch() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


def _local_date_str():
    tzname = config.settings.INTAKE_TIMEZONE or "UTC"
    try:
        tz = pytz.timezone(tzname)
    except Exception:  # noqa: BLE001
        tz, tzname = pytz.utc, "UTC"
    return datetime.now(tz).strftime("%A, %d %B %Y"), tzname


class TwilioPhoneHandler:
    def __init__(self, session_id, intake_sessions):
        self.session_id = session_id
        self.intake_sessions = intake_sessions
        session = intake_sessions[session_id]

        self.stream_sid = None
        self.call_sid = None
        self.websocket: WebSocket | None = None
        self.output_buffer = bytearray()
        self._cur = None  # in-progress utterance {speaker, text}
        self._ended = False

        self._in_resampler = TwilioToGeminiResampler()
        self._out_resampler = GeminiToTwilioResampler()

        # Bounded + drop-oldest so a stalled/failed Gemini consumer can never make
        # this grow without limit for the whole call.
        self.audio_input_queue: asyncio.Queue = asyncio.Queue(maxsize=250)
        self.text_input_queue: asyncio.Queue = asyncio.Queue()
        self._gemini_task = None

        current_date, tzname = _local_date_str()
        prompt = build_intake_prompt(
            firm_name=config.settings.FIRM_NAME,
            agent_name=config.settings.AGENT_NAME,
            caller_number=session["caller_number"],
            current_date=current_date,
            timezone=tzname,
        )
        self.gemini = GeminiLivePhone(
            api_key=config.settings.GEMINI_API_KEY,
            model=config.settings.GEMINI_LIVE_MODEL,
            input_sample_rate=16000,
            system_instruction=prompt,
            tools=[
                submit_contact_details_tool(),
                submit_case_details_tool(),
                submit_injury_details_tool(),
            ],
            tool_mapping={
                "submit_contact_details": self._submit_contact_details,
                "submit_case_details": self._submit_case_details,
                "submit_injury_details": self._submit_injury_details,
            },
            voice=config.settings.GEMINI_VOICE,
        )

    # ── tools (silent; merge whatever the model sends so the schema can grow without
    #    touching these handlers; called repeatedly to enrich as facts come out) ──
    async def _submit_contact_details(self, **kwargs) -> str:
        s = self.intake_sessions[self.session_id]
        s["contact"] = {**(s.get("contact") or {}), **kwargs}
        # Default the callback number to the caller's own line if not captured.
        if not s["contact"].get("phone"):
            s["contact"]["phone"] = s.get("caller_number")
        logger.info("Contact details recorded (%s): %s", self.session_id, kwargs.get("full_name"))
        return "Contact details recorded"

    async def _submit_case_details(self, **kwargs) -> str:
        s = self.intake_sessions[self.session_id]
        s["case"] = {**(s.get("case") or {}), **kwargs}
        logger.info("Case details recorded (%s): %s", self.session_id, kwargs.get("practice_area"))
        return "Case details recorded"

    async def _submit_injury_details(self, **kwargs) -> str:
        s = self.intake_sessions[self.session_id]
        s["injury"] = {**(s.get("injury") or {}), **kwargs}
        logger.info("Injury details recorded (%s)", self.session_id)
        return "Injury details recorded"

    # ── audio in (non-blocking, drop-oldest when full) ──────────────────────────
    def _enqueue_audio(self, chunk: bytes):
        q = self.audio_input_queue
        try:
            q.put_nowait(chunk)
        except asyncio.QueueFull:
            try:
                q.get_nowait()  # drop oldest
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(chunk)
            except asyncio.QueueFull:
                pass

    # ── audio out (Gemini 24k PCM -> Twilio 8k mu-law frames) ───────────────────
    async def _send_buffered_audio(self):
        while len(self.output_buffer) >= MULAW_FRAME_SIZE:
            frame = bytes(self.output_buffer[:MULAW_FRAME_SIZE])
            del self.output_buffer[:MULAW_FRAME_SIZE]
            payload = base64.b64encode(frame).decode("ascii")
            await self.websocket.send_text(
                json.dumps(
                    {"event": "media", "streamSid": self.stream_sid, "media": {"payload": payload}}
                )
            )

    async def _audio_output_callback(self, pcm24: bytes):
        if not self.stream_sid or self.websocket is None:
            return
        self.output_buffer.extend(self._out_resampler.process(pcm24))
        await self._send_buffered_audio()

    async def _audio_interrupt_callback(self):
        # Barge-in: drop our queued audio + flush Twilio's playback buffer.
        self.output_buffer.clear()
        if self.stream_sid and self.websocket is not None:
            try:
                await self.websocket.send_text(
                    json.dumps({"event": "clear", "streamSid": self.stream_sid})
                )
            except Exception:  # noqa: BLE001
                pass

    # ── transcript accumulation (fragments stream incrementally) ────────────────
    def _accumulate(self, speaker, text):
        if self._cur and self._cur["speaker"] == speaker:
            self._cur["text"] += text
        else:
            self._flush_transcript()
            self._cur = {"speaker": speaker, "text": text}

    def _flush_transcript(self):
        cur = self._cur
        if cur and cur["text"].strip():
            self.intake_sessions[self.session_id]["transcripts"].append(
                {"speaker": cur["speaker"], "text": cur["text"].strip(), "ts": _now_epoch()}
            )
        self._cur = None

    # ── Gemini event consumer ───────────────────────────────────────────────────
    async def _run_gemini_session(self):
        try:
            async for event in self.gemini.start_session(
                self.audio_input_queue,
                self.text_input_queue,
                self._audio_output_callback,
                self._audio_interrupt_callback,
            ):
                etype = event.get("type")
                if etype == "user":
                    self._accumulate("caller", event["text"])
                elif etype == "gemini":
                    self._accumulate("agent", event["text"])
                elif etype == "turn_complete":
                    self._flush_transcript()
                elif etype == "error":
                    logger.error("gemini event error: %s", event.get("error"))
        except asyncio.CancelledError:
            return  # normal teardown — the WS loop is ending the call
        except Exception as e:  # noqa: BLE001
            logger.error("gemini session task error: %s", e)
        # Gemini ended on its own (connect failure or GoAway) while the call was
        # still up — end the call so we don't buffer inbound audio with no consumer.
        if self.websocket is not None and not self._ended:
            try:
                await self.websocket.close()
            except Exception:  # noqa: BLE001
                pass

    # ── Twilio WS loop ──────────────────────────────────────────────────────────
    async def handle_media_stream(self, websocket: WebSocket):
        self.websocket = websocket
        self._gemini_task = asyncio.create_task(self._run_gemini_session())
        timeout_task = asyncio.create_task(self._timeout_guard(websocket))
        try:
            async for message in websocket.iter_text():
                data = json.loads(message)
                event = data.get("event")
                if event == "start":
                    # Inbound: adopt Twilio's SIDs (no outbound callSid to match).
                    sess = self.intake_sessions[self.session_id]
                    self.call_sid = data["start"].get("callSid")
                    self.stream_sid = data["start"]["streamSid"]
                    sess["status"] = "in_call"
                    await self.text_input_queue.put(
                        "A client has just called the firm. Warmly greet them, introduce "
                        "yourself, and begin the intake."
                    )
                elif event == "media":
                    ulaw = base64.b64decode(data["media"]["payload"])
                    self._enqueue_audio(self._in_resampler.process(ulaw))
                elif event == "stop":
                    break
                # 'connected', 'mark', 'dtmf' -> ignore
        except WebSocketDisconnect:
            logger.info("Twilio WS disconnected (%s)", self.session_id)
        except Exception as e:  # noqa: BLE001
            logger.error("media stream error (%s): %s", self.session_id, e)
        finally:
            timeout_task.cancel()
            if self._gemini_task and not self._gemini_task.done():
                # Brief grace so the consumer drains the last buffered transcript
                # fragments, then hard-cancel.
                await asyncio.sleep(0.15)
                self._gemini_task.cancel()
            await self._end_call_handler()

    async def _timeout_guard(self, websocket: WebSocket):
        try:
            await asyncio.sleep(CALL_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return
        logger.warning("Intake call timeout (%ss) for %s — closing", CALL_TIMEOUT_SECONDS, self.session_id)
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass

    # ── end of call: persist to SQLite + push to the CRM stub ───────────────────
    async def _end_call_handler(self):
        if self._ended:
            return
        self._ended = True
        self._flush_transcript()
        sess = self.intake_sessions.get(self.session_id)
        if not sess:
            return
        sess["status"] = "completed"
        # Offload blocking SQLite I/O off the event loop (fsync on commit would
        # otherwise stall the real-time audio of other concurrent calls). Persist
        # first, guarded — a malformed session must never lose the captured intake.
        try:
            await asyncio.to_thread(store.save_intake, sess)  # UPSERT, DB status = 'captured'
        except Exception as e:  # noqa: BLE001
            logger.error("persist intake %s failed: %s", self.session_id, e)
            return
        try:
            result = await asyncio.to_thread(legaledge_client.create_prospect, sess)  # {"prospect_id","status"}
            sess["prospect_id"] = result["prospect_id"]
            sess["prospect_status"] = result["status"]
            await asyncio.to_thread(store.update_prospect, self.session_id, result["prospect_id"], "pushed")
            logger.info("Intake %s pushed: prospect_id=%s", self.session_id, result["prospect_id"])
        except Exception as e:  # noqa: BLE001
            logger.error("legaledge push failed for %s: %s", self.session_id, e)
            try:
                await asyncio.to_thread(store.update_prospect, self.session_id, None, "failed", error=str(e))
            except Exception as e2:  # noqa: BLE001
                logger.error("mark-failed also failed for %s: %s", self.session_id, e2)
