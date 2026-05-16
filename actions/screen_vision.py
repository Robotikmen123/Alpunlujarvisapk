# Alp Ünlü tarafından yapılmıştır — @alppunlu
# Android port — ekran analizi MediaProjection + Gemini vision ile yapılır.
from __future__ import annotations

import io
import mimetypes
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from PIL import Image, ImageStat

from app_config import get_app_config_value
from core.paths import ON_ANDROID
from bridge.screen_capture import capture_screen


VISION_MODELS = (
    "models/gemini-2.0-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.5-flash",
)
VISION_MAX_DIMENSION = 1800
VISION_MAX_INLINE_BYTES = 5_500_000


def _screen_permission_message() -> str:
    return (
        "Ekran analizi icin ekran kaydi izni gerekiyor. "
        "Acilan pencerede 'Simdi Basla' diyerek JARVIS'e ekran kaydi izni ver. "
        "Izin verdikten sonra tekrar dene."
    )


def _image_looks_blank(image_path: Path) -> bool:
    try:
        with Image.open(image_path) as img:
            sample = img.convert("RGB")
            stat = ImageStat.Stat(sample)
            means = stat.mean
            extrema = stat.extrema
            max_seen = max(channel[1] for channel in extrema)
            mean_total = sum(means) / max(1, len(means))
            return max_seen <= 8 or mean_total <= 3
    except Exception:
        return False


def _build_image_part(image_path: Path) -> types.Part:
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/png"
    try:
        with Image.open(image_path) as img:
            work = img.copy()
        if work.mode not in {"RGB", "L"}:
            work = work.convert("RGB")
        if max(work.size) > VISION_MAX_DIMENSION:
            work.thumbnail((VISION_MAX_DIMENSION, VISION_MAX_DIMENSION), Image.Resampling.LANCZOS)
        png_buffer = io.BytesIO()
        work.save(png_buffer, format="PNG", optimize=True)
        png_bytes = png_buffer.getvalue()
        if len(png_bytes) <= VISION_MAX_INLINE_BYTES:
            return types.Part.from_bytes(data=png_bytes, mime_type="image/png")
        jpg_buffer = io.BytesIO()
        rgb = work.convert("RGB") if work.mode != "RGB" else work
        rgb.save(jpg_buffer, format="JPEG", quality=88, optimize=True)
        return types.Part.from_bytes(data=jpg_buffer.getvalue(), mime_type="image/jpeg")
    except Exception:
        return types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type)


def _vision_prompt(query: str) -> str:
    user_query = (query or "Ekranda ne var?").strip()
    return (
        "Sen Android uzerinde JARVIS icin ekran analizi yapan bir goruntu yorumlayicisisin.\n"
        "Asagidaki goruntu cihazin o anki ekranina ait.\n\n"
        "Gorevlerin:\n"
        "1. Ekrandaki uygulamanin/icerigin genel amacini 1-2 cumlede acikla.\n"
        "2. Gorunen onemli metinleri, hata mesajlarini, butonlari, basliklari ve durum etiketlerini oku.\n"
        "3. Kullanici sorusunu bu goruntuye gore dogrudan cevapla.\n"
        "4. Eger bir hata, uyari veya dikkat edilmesi gereken bir sey varsa bunu ayri ve net belirt.\n"
        "5. Uydurma yapma. Emin olmadigin kisimlarda bunu soyle.\n\n"
        f"Kullanici sorusu: {user_query}\n\n"
        "Yaniti Turkce ver. Gereksiz uzun olma, ama okunabilir detay ver."
    )


def _extract_response_text(response) -> str:
    text = str(getattr(response, "text", "") or "").strip()
    if text:
        return text
    candidates = getattr(response, "candidates", None) or []
    chunks: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = str(getattr(part, "text", "") or "").strip()
            if part_text:
                chunks.append(part_text)
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _is_transient_vision_error(exc: Exception) -> bool:
    if isinstance(exc, (errors.ServerError, TimeoutError)):
        return True
    message = str(exc or "").lower()
    transient_markers = (
        "503", "429", "deadline", "timed out", "timeout", "unavailable",
        "temporarily unavailable", "service unavailable", "internal error",
        "busy", "overloaded", "resource exhausted", "try again later",
        "backend error", "connection reset",
    )
    return any(marker in message for marker in transient_markers)


def _is_quota_vision_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    quota_markers = (
        "quota", "rate limit", "resource exhausted", "too many requests",
        "quota exceeded", "limit exceeded", "billing",
    )
    return any(marker in message for marker in quota_markers)


def _friendly_vision_error(exc: Exception) -> str:
    if _is_quota_vision_error(exc):
        return "Gemini vision istegi kota veya hiz limitine takildi. Biraz bekleyip tekrar dene ya da API planini kontrol et."
    if _is_transient_vision_error(exc):
        return "Gemini vision servisi su anda yogun veya gecici olarak ulasilamiyor. Biraz sonra tekrar dene."
    return f"Gemini vision istegi basarisiz oldu: {exc}"


def _analyze_with_gemini(query: str, image_path: Path) -> str:
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        return "Gemini API anahtari eksik oldugu icin ekran analizi yapilamadi."

    prompt = _vision_prompt(query)
    client = genai.Client(api_key=api_key)
    image_part = _build_image_part(image_path)
    retry_delays = (0.9, 1.8, 3.0)
    last_error: Exception | None = None

    for model_name in VISION_MODELS:
        for attempt, delay in enumerate(retry_delays, start=1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[types.Part.from_text(text=prompt), image_part],
                    config=types.GenerateContentConfig(temperature=0.2),
                )
                merged = _extract_response_text(response)
                if merged:
                    return merged
                raise RuntimeError("Gemini gecerli bir ekran analizi metni dondurmedi.")
            except Exception as exc:
                last_error = exc
                if attempt < len(retry_delays) and _is_transient_vision_error(exc):
                    time.sleep(delay)
                    continue
                if _is_transient_vision_error(exc):
                    break
                raise RuntimeError(_friendly_vision_error(exc)) from exc

    assert last_error is not None
    raise RuntimeError(_friendly_vision_error(last_error))


def analyze_screen(query: str, target: str = "active_window") -> str:
    if not ON_ANDROID:
        return "Ekran analizi yalnizca Android cihazda kullanilabilir."

    handle = tempfile.NamedTemporaryFile(prefix="jarvis-screen-", suffix=".png", delete=False)
    image_path = Path(handle.name)
    handle.close()

    ok, detail = capture_screen(str(image_path))
    if not ok:
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass
        low = detail.lower()
        if "permission" in low or "izin" in low:
            return _screen_permission_message()
        return f"Ekran goruntusu alinamadi: {detail}"

    try:
        if not image_path.exists() or image_path.stat().st_size <= 0:
            return "Ekran goruntusu bos geldi. " + _screen_permission_message()
        if _image_looks_blank(image_path):
            return ("Ekran goruntusu siyah veya bos gorunuyor. " + _screen_permission_message())
        try:
            return _analyze_with_gemini(query, image_path)
        except Exception as exc:
            return f"Ekran goruntusu alindi ama analiz tamamlanamadi: {exc}"
    finally:
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass
