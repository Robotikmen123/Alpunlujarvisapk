"""
TTS (Text-to-Speech) — Android'in yerleşik TextToSpeech motorunu kullanır.
Alp Ünlü tarafından yapılmıştır — @alppunlu

macOS'taki `say` komutunun Android karşılığı. Türkçe ve İngilizce destekler.

Not: JARVIS'in normal sesli yanıtları Gemini canlı ses akışından gelir;
bu modül bağımsız metin okuma için kullanılabilir bir yardımcıdır.
"""

from __future__ import annotations

import threading
import time

from core.paths import ON_ANDROID

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine
    with _engine_lock:
        if _engine is not None:
            return _engine
        if not ON_ANDROID:
            return None
        try:
            from bridge.platform import autoclass, get_context

            TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            _engine = TextToSpeech(get_context(), None)
            time.sleep(0.6)  # motorun başlaması için kısa bekleme
            try:
                Locale = autoclass("java.util.Locale")
                _engine.setLanguage(Locale("tr", "TR"))
            except Exception:
                pass
        except Exception as exc:
            print(f"[tts] TextToSpeech başlatılamadı: {exc}")
            _engine = None
        return _engine


def speak_text(text: str, on_done=None, blocking: bool = False):
    """Metni sesli olarak okur."""
    if not text or not text.strip():
        if on_done:
            on_done()
        return

    max_len = 500
    if len(text) > max_len:
        text = text[:max_len] + "..."

    def _run():
        engine = _get_engine()
        if engine is not None:
            try:
                from bridge.platform import autoclass

                TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
                engine.speak(text, TextToSpeech.QUEUE_FLUSH, None, "jarvis-tts")
                while engine.isSpeaking():
                    time.sleep(0.1)
            except Exception as exc:
                print(f"[tts] okuma hatası: {exc}")
        if on_done:
            on_done()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


def get_available_voices() -> list[str]:
    """Kullanılabilir TTS dillerini listeler."""
    engine = _get_engine()
    if engine is None:
        return []
    try:
        langs = engine.getAvailableLanguages()
        if langs is None:
            return []
        return [str(langs.get(i)) for i in range(langs.size())]
    except Exception:
        return []
