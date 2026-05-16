"""
Android ekran yakalama — MediaProjection + ImageReader.

macOS sürümündeki ScreenCaptureKit/Swift helper'ının Android karşılığı.
İlk çağrıda kullanıcıdan ekran kaydı izni ister; izin verildikten sonra
proje belirteci oturum boyunca yeniden kullanılır.

Not: Android 14+ üzerinde MediaProjection, mediaProjection türünde bir ön plan
servisi gerektirir; bu yakalayıcı tek kare alır ve servisi kısa süre çalıştırır.
"""

from __future__ import annotations

import threading
import time

from core.paths import ON_ANDROID

from .platform import autoclass, get_activity, get_context

_REQUEST_CODE = 0xCA11

_lock = threading.Lock()
_result_event = threading.Event()
_result_code = None
_result_data = None
_bound = False


def _on_activity_result(request_code, result_code, intent):
    global _result_code, _result_data
    if request_code == _REQUEST_CODE:
        _result_code = result_code
        _result_data = intent
        _result_event.set()


def _ensure_bound():
    global _bound
    if _bound:
        return
    try:
        from android import activity  # type: ignore

        activity.bind(on_activity_result=_on_activity_result)
        _bound = True
    except Exception as exc:
        print(f"[screen] activity bind hatası: {exc}")


def _request_projection(timeout: float = 60.0):
    """Ekran kaydı izni ister, (resultCode, dataIntent) döndürür."""
    _ensure_bound()
    _result_event.clear()
    mpm = get_context().getSystemService("media_projection")
    intent = mpm.createScreenCaptureIntent()
    get_activity().startActivityForResult(intent, _REQUEST_CODE)
    if not _result_event.wait(timeout):
        raise RuntimeError("Ekran kaydı izni zaman aşımına uğradı.")
    Activity = autoclass("android.app.Activity")
    if _result_code != Activity.RESULT_OK or _result_data is None:
        raise PermissionError("permission_denied: ekran kaydı izni verilmedi.")
    return _result_code, _result_data


def capture_screen(out_path: str, timeout: float = 60.0) -> tuple[bool, str]:
    """Ekranın tek karesini yakalar ve PNG olarak out_path'e yazar."""
    if not ON_ANDROID:
        return False, "Ekran yakalama yalnızca Android cihazda kullanılabilir."

    with _lock:
        try:
            result_code, data = _request_projection(timeout)
        except PermissionError as exc:
            return False, str(exc)
        except Exception as exc:
            return False, f"Ekran kaydı izni alınamadı: {exc}"

        try:
            return _do_capture(result_code, data, out_path)
        except Exception as exc:
            return False, f"Ekran yakalama hatası: {exc}"


def _do_capture(result_code, data, out_path: str) -> tuple[bool, str]:
    activity = get_activity()
    mpm = get_context().getSystemService("media_projection")
    projection = mpm.getMediaProjection(result_code, data)
    if projection is None:
        return False, "MediaProjection oluşturulamadı."

    DisplayMetrics = autoclass("android.util.DisplayMetrics")
    metrics = DisplayMetrics()
    activity.getWindowManager().getDefaultDisplay().getRealMetrics(metrics)
    width = metrics.widthPixels
    height = metrics.heightPixels
    density = metrics.densityDpi

    PixelFormat = autoclass("android.graphics.PixelFormat")
    ImageReader = autoclass("android.media.ImageReader")
    reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)

    DisplayManager = autoclass("android.hardware.display.DisplayManager")
    flags = DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR
    virtual_display = projection.createVirtualDisplay(
        "jarvis-screen", width, height, density, flags,
        reader.getSurface(), None, None,
    )

    image = None
    for _ in range(30):
        time.sleep(0.12)
        image = reader.acquireLatestImage()
        if image is not None:
            break

    if image is None:
        _cleanup(reader, virtual_display, projection)
        return False, "Ekran karesi alınamadı."

    try:
        planes = image.getPlanes()
        buffer = planes[0].getBuffer()
        pixel_stride = planes[0].getPixelStride()
        row_stride = planes[0].getRowStride()
        row_padding = row_stride - pixel_stride * width

        Bitmap = autoclass("android.graphics.Bitmap")
        BitmapConfig = autoclass("android.graphics.Bitmap$Config")
        padded_width = width + row_padding // pixel_stride
        bitmap = Bitmap.createBitmap(padded_width, height, BitmapConfig.ARGB_8888)
        bitmap.copyPixelsFromBuffer(buffer)
        cropped = Bitmap.createBitmap(bitmap, 0, 0, width, height)

        FileOutputStream = autoclass("java.io.FileOutputStream")
        CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
        out = FileOutputStream(out_path)
        cropped.compress(CompressFormat.PNG, 100, out)
        out.flush()
        out.close()
        return True, out_path
    finally:
        try:
            image.close()
        except Exception:
            pass
        _cleanup(reader, virtual_display, projection)


def _cleanup(reader, virtual_display, projection):
    for obj, method in ((virtual_display, "release"),
                        (reader, "close"),
                        (projection, "stop")):
        try:
            if obj is not None:
                getattr(obj, method)()
        except Exception:
            pass
