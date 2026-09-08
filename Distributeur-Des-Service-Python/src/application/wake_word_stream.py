"""Server-side Azure Speech streaming session for the Pi's WebSocket wake-word client.

The Pi connects to ``/ws/wake-word/{robot_id}``, sends one JSON config frame
(language + keyword variants), then streams raw S16_LE 16 kHz mono PCM frames.
This class wraps an Azure ``SpeechRecognizer`` configured in continuous mode
and bridges Azure's partial/final events to JSON events sent back to the Pi:

    {"event": "ready"}
    {"event": "partial", "text": "...", "matched": false}
    {"event": "wake_detected", "keyword": "محسن", "transcript": "...",
     "latency_ms": 320}
    {"event": "error", "message": "..."}

Why a class?
    Each WebSocket has its own short-lived Azure recognizer (~minutes max) —
    we tear it down between sessions so we don't burn the streaming budget
    while no one is talking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

import azure.cognitiveservices.speech as speechsdk

from src.config.config import settings

logger = logging.getLogger(__name__)


# --- Keyword matcher (light copy of the Pi-side WakeWordMatcher) -----------

_ARABIC_NORMALISATION = {
    "آ": "ا",  # آ → ا
    "أ": "ا",  # أ → ا
    "إ": "ا",  # إ → ا
    "ٱ": "ا",  # ٱ → ا
    "ى": "ي",  # ى → ي
    "ة": "ه",  # ة → ه
    "‌": "",
    "‍": "",
    "\u200F": "",
    "\u200E": "",
}
_NON_ALNUM = re.compile(r"[^\w]+", flags=re.UNICODE)


def _normalize(text: str) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text).casefold()
    out = []
    for ch in s:
        out.append(_ARABIC_NORMALISATION.get(ch, ch))
    s = "".join(out)
    s = _NON_ALNUM.sub(" ", s).strip()
    return re.sub(r"\s+", " ", s)


@dataclass
class WakeMatch:
    keyword: str
    transcript: str


class _Matcher:
    def __init__(self, keywords: List[str]) -> None:
        seen = set()
        norm: List[tuple[str, str]] = []
        for kw in keywords or []:
            n = _normalize(kw)
            if n and n not in seen:
                seen.add(n)
                norm.append((kw, n))
        self._norm = norm

    def match(self, transcript: str) -> Optional[WakeMatch]:
        if not self._norm:
            return None
        t = _normalize(transcript)
        if not t:
            return None
        for raw, n in self._norm:
            if n and n in t:
                return WakeMatch(keyword=raw, transcript=transcript)
        return None


# --- WebSocket session ----------------------------------------------------

SendJson = Callable[[dict], Awaitable[None]]


class WakeWordStreamSession:
    """One session = one WS = one Azure recognizer."""

    def __init__(
        self,
        send_json: SendJson,
        *,
        language: str,
        keywords: List[str],
        sample_rate: int = 16000,
        channels: int = 1,
        bits_per_sample: int = 16,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._send_json = send_json
        self._matcher = _Matcher(keywords)
        self._language = language
        self._sample_rate = sample_rate
        self._channels = channels
        self._bits = bits_per_sample
        self._loop = loop or asyncio.get_event_loop()
        self._recognizer: Optional[speechsdk.SpeechRecognizer] = None
        self._push_stream: Optional[speechsdk.audio.PushAudioInputStream] = None
        self._started_at: float = 0.0
        self._closed = False
        self._last_partial: str = ""

    def _schedule_send(self, payload: dict) -> None:
        """Bridge Azure SDK threads -> asyncio. Azure SDK fires callbacks from
        worker threads, so we can't ``await`` directly; instead we hand the
        coroutine back to the WS event loop."""
        if self._closed:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._send_json(payload), self._loop)
        except RuntimeError:
            pass  # loop is gone — websocket already closed

    def start(self) -> None:
        if self._recognizer is not None:
            return
        if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
            raise RuntimeError(
                "AZURE_SPEECH_KEY/REGION not configured — wake-word streaming disabled."
            )

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION,
        )
        speech_config.speech_recognition_language = self._language

        fmt = speechsdk.audio.AudioStreamFormat(
            samples_per_second=self._sample_rate,
            bits_per_sample=self._bits,
            channels=self._channels,
        )
        self._push_stream = speechsdk.audio.PushAudioInputStream(stream_format=fmt)
        audio_config = speechsdk.audio.AudioConfig(stream=self._push_stream)
        self._recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        self._recognizer.recognizing.connect(self._on_recognizing)
        self._recognizer.recognized.connect(self._on_recognized)
        self._recognizer.canceled.connect(self._on_canceled)

        self._started_at = time.perf_counter()
        self._recognizer.start_continuous_recognition_async().get()
        logger.info(
            "Wake-word stream session started (lang=%s, keywords=%d)",
            self._language, len(self._matcher._norm),
        )
        self._schedule_send({"event": "ready"})

    def push_pcm(self, chunk: bytes) -> None:
        if self._push_stream is None or self._closed:
            return
        self._push_stream.write(chunk)

    def _on_recognizing(self, evt) -> None:
        text = (evt.result.text or "").strip()
        if not text or text == self._last_partial:
            return
        self._last_partial = text
        match = self._matcher.match(text)
        latency_ms = int((time.perf_counter() - self._started_at) * 1000)
        if match is not None:
            logger.info("Wake word matched (partial) keyword=%r in %r (%dms)",
                        match.keyword, text, latency_ms)
            self._schedule_send({
                "event": "wake_detected",
                "keyword": match.keyword,
                "transcript": text,
                "latency_ms": latency_ms,
                "source": "azure_partial",
            })
        else:
            self._schedule_send({
                "event": "partial",
                "text": text[:200],
                "matched": False,
                "latency_ms": latency_ms,
            })

    def _on_recognized(self, evt) -> None:
        text = (evt.result.text or "").strip()
        if not text:
            return
        match = self._matcher.match(text)
        if match is not None:
            latency_ms = int((time.perf_counter() - self._started_at) * 1000)
            logger.info("Wake word matched (final) keyword=%r in %r (%dms)",
                        match.keyword, text, latency_ms)
            self._schedule_send({
                "event": "wake_detected",
                "keyword": match.keyword,
                "transcript": text,
                "latency_ms": latency_ms,
                "source": "azure_final",
            })

    def _on_canceled(self, evt) -> None:
        details = getattr(evt, "error_details", "") or getattr(evt, "reason", "")
        logger.warning("Azure recognizer canceled: %s", details)
        self._schedule_send({"event": "error", "message": f"azure canceled: {details!s}"[:240]})

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._push_stream is not None:
            try:
                self._push_stream.close()
            except Exception:
                pass
            self._push_stream = None
        if self._recognizer is not None:
            try:
                self._recognizer.stop_continuous_recognition_async().get()
            except Exception:
                pass
            self._recognizer = None
        logger.info("Wake-word stream session closed")
