"""
Android platform köprüsü — pyjnius üzerinden Java/Android API'lerine erişim.

Masaüstünde (geliştirme sırasında) bu modül güvenle import edilebilir;
Android'e özel çağrılar yalnızca cihazda çalışır, aksi halde ON_ANDROID=False olur.
"""

from __future__ import annotations

from core.paths import ON_ANDROID

_autoclass = None
_cast = None


def _ensure_jnius():
    global _autoclass, _cast
    if _autoclass is None:
        from jnius import autoclass, cast  # type: ignore

        _autoclass = autoclass
        _cast = cast
    return _autoclass, _cast


def autoclass(name: str):
    ac, _ = _ensure_jnius()
    return ac(name)


def cast(name, obj):
    _, c = _ensure_jnius()
    return c(name, obj)


def get_activity():
    """Çalışan Kivy Activity'sini döndürür."""
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    return PythonActivity.mActivity


def get_context():
    """Uygulama Context'ini döndürür."""
    return get_activity().getApplicationContext()


def get_system_service(name: str):
    return get_context().getSystemService(name)


def run_on_ui_thread(func):
    """Bir Python fonksiyonunu Android UI thread'inde çalıştırır."""
    try:
        from android.runnable import run_on_ui_thread as _rou  # type: ignore

        return _rou(func)()
    except Exception:
        return func()


def request_permissions(permissions: list[str]) -> None:
    """Çalışma zamanı izinlerini ister (Android 6+)."""
    if not ON_ANDROID:
        return
    try:
        from android.permissions import request_permissions as _req  # type: ignore

        _req(permissions)
    except Exception:
        pass


def has_permission(permission: str) -> bool:
    if not ON_ANDROID:
        return False
    try:
        from android.permissions import check_permission  # type: ignore

        return bool(check_permission(permission))
    except Exception:
        return False
