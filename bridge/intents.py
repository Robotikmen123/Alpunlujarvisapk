"""
Android Intent yardımcıları — URL açma, uygulama başlatma, paylaşım.
macOS'taki `open` / `open -a` komutlarının Android karşılığı.
"""

from __future__ import annotations

from core.paths import ON_ANDROID

from .platform import autoclass, get_activity


def _new_intent_view(uri_str: str):
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    intent = Intent(Intent.ACTION_VIEW)
    intent.setData(Uri.parse(uri_str))
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    return intent


def open_uri(uri_str: str) -> bool:
    """Bir URI'yi sistemin varsayılan uygulamasıyla açar."""
    if not ON_ANDROID:
        print(f"[intent] open_uri: {uri_str}")
        return False
    try:
        get_activity().startActivity(_new_intent_view(uri_str))
        return True
    except Exception as exc:
        print(f"[intent] open_uri hatası: {exc}")
        return False


def open_uri_with_package(uri_str: str, package: str) -> bool:
    """Bir URI'yi belirli bir uygulama paketiyle açmayı dener."""
    if not ON_ANDROID:
        print(f"[intent] open_uri_with_package: {package} -> {uri_str}")
        return False
    try:
        intent = _new_intent_view(uri_str)
        intent.setPackage(package)
        get_activity().startActivity(intent)
        return True
    except Exception:
        return open_uri(uri_str)


def launch_package(package: str) -> bool:
    """Bir uygulamayı paket adıyla başlatır."""
    if not ON_ANDROID:
        print(f"[intent] launch_package: {package}")
        return False
    try:
        activity = get_activity()
        pm = activity.getPackageManager()
        intent = pm.getLaunchIntentForPackage(package)
        if intent is None:
            return False
        Intent = autoclass("android.content.Intent")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)
        return True
    except Exception as exc:
        print(f"[intent] launch_package hatası: {exc}")
        return False


def start_intent_action(action: str, data: str = "", extras: dict | None = None,
                         package: str = "") -> bool:
    """Genel bir Intent başlatır (örn. ACTION_INSERT, ACTION_SENDTO)."""
    if not ON_ANDROID:
        print(f"[intent] action={action} data={data} extras={extras}")
        return False
    try:
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        intent = Intent(action)
        if data:
            intent.setData(Uri.parse(data))
        if package:
            intent.setPackage(package)
        for key, value in (extras or {}).items():
            if isinstance(value, bool):
                intent.putExtra(key, value)
            elif isinstance(value, int):
                intent.putExtra(key, autoclass("java.lang.Long")(value))
            else:
                intent.putExtra(key, str(value))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        get_activity().startActivity(intent)
        return True
    except Exception as exc:
        print(f"[intent] start_intent_action hatası: {exc}")
        return False


def share_text(text: str) -> bool:
    if not ON_ANDROID:
        print(f"[intent] share_text: {text}")
        return False
    try:
        Intent = autoclass("android.content.Intent")
        intent = Intent(Intent.ACTION_SEND)
        intent.setType("text/plain")
        intent.putExtra(Intent.EXTRA_TEXT, text)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        get_activity().startActivity(intent)
        return True
    except Exception:
        return False
