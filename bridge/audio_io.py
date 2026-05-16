"""
Çapraz platform ses giriş/çıkışı.

JARVIS canlı ses çekirdeği şunlara ihtiyaç duyar:
  • Mikrofon  : 16 kHz, mono, PCM16  (Gemini'ye gönderilir)
  • Hoparlör  : 24 kHz, mono, PCM16  (Gemini'den gelir)

Android : `audiostream` (AudioRecord + AudioTrack sarmalayıcısı)
Masaüstü: `pyaudio`  (geliştirme/test için yedek)

macOS sürümündeki PyAudio bağımlılığının doğrudan Android karşılığıdır.
"""

from __future__ import annotations

import threading

SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 1024


class _AudiostreamBackend:
    """Android — kivy audiostream üzerinden AudioRecord/AudioTrack."""

    name = "audiostream"

    def __init__(self):
        from audiostream import get_output  # type: ignore

        self._get_output = get_output
        self._mic = None
        self._output = None
        self._out_stream = None
        self._on_chunk = None

    def start_input(self, on_chunk):
        from audiostream import get_input  # type: ignore

        self._on_chunk = on_chunk

        def _cb(buf):
            cb = self._on_chunk
            if cb is not None and buf:
                cb(bytes(buf))

        self._mic = get_input(
            callback=_cb,
            source="voice_communication",
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            encoding=16,
            buffersize=CHUNK_SIZE,
        )
        self._mic.start()

    def stop_input(self):
        self._on_chunk = None
        if self._mic is not None:
            try:
                self._mic.stop()
            except Exception:
                pass
            self._mic = None

    def _ensure_output(self):
        if self._out_stream is None:
            self._output = self._get_output(
                channels=CHANNELS,
                rate=RECV_SAMPLE_RATE,
                encoding=16,
                buffersize=CHUNK_SIZE,
            )
            self._out_stream = self._output.add_stream()

    def write_output(self, chunk: bytes):
        self._ensure_output()
        self._out_stream.write(chunk)

    def stop_output(self):
        if self._out_stream is not None:
            try:
                self._out_stream.stop()
            except Exception:
                pass
        self._out_stream = None
        self._output = None


class _PyAudioBackend:
    """Masaüstü yedeği — pyaudio (Android'de kullanılmaz)."""

    name = "pyaudio"

    def __init__(self):
        import pyaudio  # type: ignore

        self._pyaudio = pyaudio
        self._pa = pyaudio.PyAudio()
        self._in_stream = None
        self._out_stream = None
        self._reader_thread = None
        self._reading = False
        self._on_chunk = None

    def start_input(self, on_chunk):
        self._on_chunk = on_chunk
        self._in_stream = self._pa.open(
            format=self._pyaudio.paInt16,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        self._reading = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def _read_loop(self):
        while self._reading and self._in_stream is not None:
            try:
                data = self._in_stream.read(CHUNK_SIZE, exception_on_overflow=False)
            except Exception:
                break
            cb = self._on_chunk
            if cb is not None and data:
                cb(data)

    def stop_input(self):
        self._reading = False
        self._on_chunk = None
        if self._in_stream is not None:
            try:
                self._in_stream.close()
            except Exception:
                pass
            self._in_stream = None

    def _ensure_output(self):
        if self._out_stream is None:
            self._out_stream = self._pa.open(
                format=self._pyaudio.paInt16,
                channels=CHANNELS,
                rate=RECV_SAMPLE_RATE,
                output=True,
            )

    def write_output(self, chunk: bytes):
        self._ensure_output()
        self._out_stream.write(chunk)

    def stop_output(self):
        if self._out_stream is not None:
            try:
                self._out_stream.close()
            except Exception:
                pass
            self._out_stream = None


def create_audio_backend():
    """Çalışılan platforma uygun ses arka ucunu döndürür."""
    try:
        return _AudiostreamBackend()
    except Exception as exc:
        print(f"[audio] audiostream kullanılamadı ({exc}), pyaudio deneniyor.")
    try:
        return _PyAudioBackend()
    except Exception as exc:
        raise RuntimeError(f"Kullanılabilir bir ses arka ucu bulunamadı: {exc}")
