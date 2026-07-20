"""Python Gemini Live wrapper for LegalEdge inbound intake phone calls.

Reused verbatim from a production-tested Gemini Live pattern:
- no video track (phone audio only)
- the system instruction and voice are parameterised (intake prompt / GEMINI_VOICE)
- concurrent send_audio + send_text + receive tasks, tool-call handling with
  send_tool_response, and transcription / turn / interrupt events surfaced through
  an async event generator.

Runs entirely inside the FastAPI event loop (no asyncio.run()).
"""
import asyncio
import inspect
import logging
import traceback

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiLivePhone:
    def __init__(
        self,
        api_key,
        model,
        input_sample_rate,
        system_instruction,
        tools=None,
        tool_mapping=None,
        voice="Puck",
    ):
        self.api_key = api_key
        self.model = model
        self.input_sample_rate = input_sample_rate
        self.system_instruction = system_instruction
        self.voice = voice
        # Live API uses the v1beta surface; pin it explicitly.
        self.client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(api_version="v1beta")
        )
        self.tools = tools or []
        self.tool_mapping = tool_mapping or {}

    async def start_session(
        self,
        audio_input_queue,
        text_input_queue,
        audio_output_callback,
        audio_interrupt_callback=None,
    ):
        """Async generator. Connects to Gemini Live, bridges audio via the queues
        and callback, runs tool calls, and yields conversation events
        ({"type": "user"|"gemini"|"turn_complete"|"interrupted"|"tool_call"|"error"})."""
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice)
                )
            ),
            system_instruction=types.Content(parts=[types.Part(text=self.system_instruction)]),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY",
                # Tuned so the agent takes turns like a patient human on a phone call:
                # LOW start-sensitivity ignores background/line noise; LOW end-sensitivity
                # plus ~0.7s of trailing silence lets the caller finish their sentence (and
                # pause to recall a detail) before the agent responds, instead of talking
                # over them. prefix padding avoids clipping the caller's first word.
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    silence_duration_ms=700,
                    prefix_padding_ms=300,
                ),
            ),
            tools=self.tools,
            # Sliding-window compression so a long (up to 15 min) phone call does
            # not hit the context cap and drop mid-conversation.
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()
            ),
            # Provide resumption handles (future reconnect-on-GoAway hardening).
            session_resumption=types.SessionResumptionConfig(),
        )

        logger.info("Connecting to Gemini Live (phone) with model=%s", self.model)
        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                logger.info("Gemini Live phone session opened")

                async def send_audio():
                    try:
                        while True:
                            chunk = await audio_input_queue.get()
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=chunk,
                                    mime_type=f"audio/pcm;rate={self.input_sample_rate}",
                                )
                            )
                    except asyncio.CancelledError:
                        logger.debug("send_audio cancelled")
                    except Exception as e:  # noqa: BLE001
                        logger.error("send_audio error: %s\n%s", e, traceback.format_exc())

                async def send_text():
                    try:
                        while True:
                            text = await text_input_queue.get()
                            logger.info("Sending text to Gemini: %s", text)
                            # send_client_content (a full user turn) reliably makes
                            # the model speak first; send_realtime_input(text=) is
                            # VAD-gated and not deterministic for the opener.
                            await session.send_client_content(
                                turns=types.Content(role="user", parts=[types.Part(text=text)]),
                                turn_complete=True,
                            )
                    except asyncio.CancelledError:
                        logger.debug("send_text cancelled")
                    except Exception as e:  # noqa: BLE001
                        logger.error("send_text error: %s\n%s", e, traceback.format_exc())

                event_queue = asyncio.Queue()

                async def receive_loop():
                    try:
                        while True:
                            async for response in session.receive():
                                if response.go_away:
                                    logger.warning("Gemini GoAway: %s", response.go_away)

                                server_content = response.server_content
                                tool_call = response.tool_call

                                if server_content:
                                    if server_content.model_turn:
                                        for part in server_content.model_turn.parts:
                                            if part.inline_data:
                                                if inspect.iscoroutinefunction(audio_output_callback):
                                                    await audio_output_callback(part.inline_data.data)
                                                else:
                                                    audio_output_callback(part.inline_data.data)
                                    if (
                                        server_content.input_transcription
                                        and server_content.input_transcription.text
                                    ):
                                        await event_queue.put(
                                            {"type": "user", "text": server_content.input_transcription.text}
                                        )
                                    if (
                                        server_content.output_transcription
                                        and server_content.output_transcription.text
                                    ):
                                        await event_queue.put(
                                            {"type": "gemini", "text": server_content.output_transcription.text}
                                        )
                                    if server_content.turn_complete:
                                        await event_queue.put({"type": "turn_complete"})
                                    if server_content.interrupted:
                                        if audio_interrupt_callback:
                                            if inspect.iscoroutinefunction(audio_interrupt_callback):
                                                await audio_interrupt_callback()
                                            else:
                                                audio_interrupt_callback()
                                        await event_queue.put({"type": "interrupted"})

                                if tool_call:
                                    function_responses = []
                                    for fc in tool_call.function_calls:
                                        func_name = fc.name
                                        args = fc.args or {}
                                        result = "ok"
                                        if func_name in self.tool_mapping:
                                            try:
                                                tool_func = self.tool_mapping[func_name]
                                                if inspect.iscoroutinefunction(tool_func):
                                                    result = await tool_func(**args)
                                                else:
                                                    loop = asyncio.get_running_loop()
                                                    result = await loop.run_in_executor(
                                                        None, lambda tf=tool_func, a=args: tf(**a)
                                                    )
                                            except Exception as e:  # noqa: BLE001
                                                result = f"Error: {e}"
                                                logger.error("tool %s error: %s", func_name, e)
                                        function_responses.append(
                                            types.FunctionResponse(
                                                name=func_name, id=fc.id, response={"result": result}
                                            )
                                        )
                                        await event_queue.put(
                                            {"type": "tool_call", "name": func_name, "args": args, "result": result}
                                        )
                                    # MUST respond or Gemini stalls and stops talking.
                                    await session.send_tool_response(function_responses=function_responses)
                    except asyncio.CancelledError:
                        logger.debug("receive_loop cancelled")
                    except Exception as e:  # noqa: BLE001
                        logger.error(
                            "receive_loop error: %s: %s\n%s", type(e).__name__, e, traceback.format_exc()
                        )
                        await event_queue.put({"type": "error", "error": f"{type(e).__name__}: {e}"})
                    finally:
                        await event_queue.put(None)

                send_audio_task = asyncio.create_task(send_audio())
                send_text_task = asyncio.create_task(send_text())
                receive_task = asyncio.create_task(receive_loop())

                try:
                    while True:
                        event = await event_queue.get()
                        if event is None:
                            break
                        yield event
                finally:
                    send_audio_task.cancel()
                    send_text_task.cancel()
                    receive_task.cancel()
        except Exception as e:  # noqa: BLE001
            logger.error(
                "Gemini Live phone session error: %s: %s\n%s", type(e).__name__, e, traceback.format_exc()
            )
            raise
        finally:
            logger.info("Gemini Live phone session closed")
