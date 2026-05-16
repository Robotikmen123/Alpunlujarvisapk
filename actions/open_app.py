"""
Uygulama açma — Android Intent / PackageManager ile çalışır.
Alp Ünlü tarafından yapılmıştır — @alppunlu

macOS'taki `open -a` komutunun Android karşılığı:
önce bilinen paket adıyla, bulunamazsa yüklü uygulamalar arasında
ada göre arama yaparak başlatır.
"""

from __future__ import annotations

import unicodedata

from core.paths import ON_ANDROID

from bridge.intents import launch_package
from bridge.platform import autoclass, get_activity


# Kısa isimden Android paket adına eşleme
APP_PACKAGES = {
    "chrome":      "com.android.chrome",
    "firefox":     "org.mozilla.firefox",
    "spotify":     "com.spotify.music",
    "youtube":     "com.google.android.youtube",
    "youtube music": "com.google.android.apps.youtube.music",
    "whatsapp":    "com.whatsapp",
    "telegram":    "org.telegram.messenger",
    "instagram":   "com.instagram.android",
    "facebook":    "com.facebook.katana",
    "messenger":   "com.facebook.orca",
    "x":           "com.twitter.android",
    "twitter":     "com.twitter.android",
    "tiktok":      "com.zhiliaoapp.musically",
    "gmail":       "com.google.android.gm",
    "mail":        "com.google.android.gm",
    "maps":        "com.google.android.apps.maps",
    "haritalar":   "com.google.android.apps.maps",
    "takvim":      "com.google.android.calendar",
    "calendar":    "com.google.android.calendar",
    "notes":       "com.google.android.keep",
    "notlar":      "com.google.android.keep",
    "keep":        "com.google.android.keep",
    "music":       "com.google.android.apps.youtube.music",
    "müzik":       "com.google.android.apps.youtube.music",
    "photos":      "com.google.android.apps.photos",
    "fotoğraflar": "com.google.android.apps.photos",
    "fotograflar": "com.google.android.apps.photos",
    "camera":      "com.android.camera2",
    "kamera":      "com.android.camera2",
    "settings":    "com.android.settings",
    "ayarlar":     "com.android.settings",
    "calculator":  "com.google.android.calculator",
    "hesap makinesi": "com.google.android.calculator",
    "clock":       "com.google.android.deskclock",
    "saat":        "com.google.android.deskclock",
    "discord":     "com.discord",
    "slack":       "com.Slack",
    "netflix":     "com.netflix.mediaclient",
    "zoom":        "us.zoom.videomeetings",
    "drive":       "com.google.android.apps.docs",
    "play store":  "com.android.vending",
    "store":       "com.android.vending",
}


def _normalize(text: str) -> str:
    text = (text or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.replace("ı", "i")


def _find_package_by_label(app_name: str) -> str | None:
    """Yüklü uygulamalar arasında görünen ada göre paket arar."""
    try:
        pm = get_activity().getPackageManager()
        Intent = autoclass("android.content.Intent")
        main_intent = Intent(Intent.ACTION_MAIN)
        main_intent.addCategory(Intent.CATEGORY_LAUNCHER)
        needle = _normalize(app_name)
        resolved = pm.queryIntentActivities(main_intent, 0)
        best = None
        for i in range(resolved.size()):
            info = resolved.get(i)
            label = _normalize(str(info.loadLabel(pm)))
            pkg = info.activityInfo.packageName
            if label == needle:
                return pkg
            if best is None and needle in label:
                best = pkg
        return best
    except Exception:
        return None


def open_app(app_name: str) -> str:
    """Uygulamayı açar, başarı/hata mesajı döndürür."""
    if not app_name:
        return "Uygulama adı belirtilmedi."

    if not ON_ANDROID:
        return f"'{app_name}' açılır (Android cihaz gerekli)."

    normalized = _normalize(app_name)
    package = APP_PACKAGES.get(normalized)

    if package and launch_package(package):
        return f"{app_name} açıldı."

    found = _find_package_by_label(app_name)
    if found and launch_package(found):
        return f"{app_name} açıldı."

    if package:
        # Yüklü değilse Play Store'da göster
        from bridge.intents import open_uri

        if open_uri(f"market://details?id={package}"):
            return f"'{app_name}' yüklü görünmüyor, Play Store'da açıldı."

    return f"'{app_name}' bulunamadı veya açılamadı."
