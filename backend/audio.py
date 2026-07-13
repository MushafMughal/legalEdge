"""Telephony audio conversion (audioop — stdlib on Python 3.12).

Twilio Media Streams use G.711 mu-law @ 8kHz mono; Gemini Live consumes PCM16 @
16kHz and emits PCM16 @ 24kHz. Each resampler keeps the ratecv state across
chunks (per stage / direction) so there are no seam clicks. Use one instance per
call, per direction, accessed from a single task.

audioop is built-in on 3.12 (removed in 3.13 — do NOT install audioop-lts here).
"""
import audioop


class TwilioToGeminiResampler:
    """Twilio mu-law 8kHz -> PCM16 16kHz (Gemini Live input)."""

    def __init__(self) -> None:
        self._state = None  # ratecv state, persists across chunks

    def process(self, ulaw_bytes: bytes) -> bytes:
        pcm8 = audioop.ulaw2lin(ulaw_bytes, 2)
        pcm16, self._state = audioop.ratecv(pcm8, 2, 1, 8000, 16000, self._state)
        return pcm16


class GeminiToTwilioResampler:
    """Gemini PCM16 24kHz -> mu-law 8kHz (Twilio output).

    Two-step downsample (24->16->8) rather than a single 3:1 decimation: ratecv
    has no anti-alias filter, so staging it markedly reduces metallic aliasing.
    """

    def __init__(self) -> None:
        self._s1 = None  # 24k -> 16k
        self._s2 = None  # 16k -> 8k
        self._rem = b""  # leftover odd byte carried across chunks

    def process(self, pcm24: bytes) -> bytes:
        # ratecv needs whole 16-bit frames; carry any odd trailing byte so a chunk
        # split mid-sample can never raise audioop.error and kill the call.
        data = self._rem + pcm24
        n = len(data) & ~1
        self._rem = data[n:]
        data = data[:n]
        if not data:
            return b""
        a, self._s1 = audioop.ratecv(data, 2, 1, 24000, 16000, self._s1)
        b, self._s2 = audioop.ratecv(a, 2, 1, 16000, 8000, self._s2)
        return audioop.lin2ulaw(b, 2)
