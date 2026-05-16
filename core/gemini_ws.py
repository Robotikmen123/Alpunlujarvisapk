"""
Gemini Live API — saf Python WebSocket istemcisi.
Alp Ünlü tarafından yapılmıştır — @alppunlu

google-genai SDK'sı, Rust ile derlenen pydantic-core'a bağlı olduğu için
Android (python-for-android) ortamında derlenemiyordu. Bu modül, Gemini Live
(BidiGenerateContent) protokolüne yalnızca `websockets` ile doğrudan bağlanır;
böylece hiçbir derlenmiş bağımlılık gerekmez ve davranış SDK ile aynı kalır.
"""

from __future__ import annotations

import base64
import json

import websockets

# Native-audio modeli v1alpha uç noktasında sunulur (macOS sürümüyle aynı).
WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
)

SEND_SAMPLE_RATE = 16000


class GeminiLiveSession:
    """Gemini Live çift yönlü ses oturumu (async context manager)."""

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        self.ws = None

    async def __aenter__(self) -> "GeminiLiveSession":
        url = f"{WS_URL}?key={self._api_key}"
        self.ws = await websockets.connect(
            url, max_size=None, ping_interval=20, ping_timeout=30,
        )
        return self

    async def __aexit__(self, *exc):
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    # ── Gönderim ─────────────────────────────────────────────────────────────
    async def send_setup(self, config: dict):
        await self.ws.send(json.dumps({"setup": config}))

    async def send_audio(self, pcm: bytes):
        payload = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                        "data": base64.b64encode(pcm).decode("ascii"),
                    }
                ]
            }
        }
        await self.ws.send(json.dumps(payload))

    async def send_text(self, text: str):
        payload = {
            "clientContent": {
                "turns": [{"role": "user", "parts": [{"text": text}]}],
                "turnComplete": True,
            }
        }
        await self.ws.send(json.dumps(payload))

    async def send_audio_stream_end(self):
        await self.ws.send(json.dumps({"realtimeInput": {"audioStreamEnd": True}}))

    async def send_tool_response(self, function_responses: list[dict]):
        payload = {"toolResponse": {"functionResponses": function_responses}}
        await self.ws.send(json.dumps(payload))

    # ── Alım ─────────────────────────────────────────────────────────────────
    async def events(self):
        """Sunucudan gelen JSON olaylarını çözümleyerek üretir."""
        async for raw in self.ws:
            if isinstance(raw, (bytes, bytearray)):
                raw = bytes(raw).decode("utf-8", errors="replace")
            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                continue
