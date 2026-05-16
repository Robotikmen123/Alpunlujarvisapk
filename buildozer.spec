# JARVIS Android — Buildozer yapılandırması
# Alp Ünlü tarafından yapılmıştır — @alppunlu
#
# APK üretmek için:
#   pip install buildozer cython
#   buildozer -v android debug
#
# Üretilen APK: bin/ klasörüne yazılır.

[app]

title = JARVIS
package.name = jarvis
package.domain = com.alppunlu

source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,otf,mp3,wav,txt,json,kv
source.include_patterns = SFX/*,Fonts/*,Icon/*,core/*,config/*,memory/*
# Geliştirme/araç dosyalarını APK dışında tut
source.exclude_dirs = bin,.git,.buildozer,__pycache__,tests
source.exclude_patterns = */__pycache__/*,*.pyc

version = 1.0.0

# ── Bağımlılıklar ────────────────────────────────────────────────────────────
# Tüm bağımlılıklar saf Python'dur (derlenmiş/Rust bağımlılığı yok). Gemini Live
# API'sine google-genai SDK'sı yerine doğrudan websockets ile bağlanılır, vision
# çağrıları requests ile REST üzerinden yapılır. audiostream + pyjnius Android
# ses ve Java köprüsü içindir; pillow'un python-for-android tarifi vardır.
requirements = python3,kivy==2.3.0,audiostream,pyjnius,android,plyer,pillow,requests,urllib3,certifi,charset-normalizer,idna,websockets

orientation = portrait
fullscreen = 0

# Açılış logosu / ikon (isteğe bağlı — kendi varlığınızı ekleyebilirsiniz)
# icon.filename = %(source.dir)s/Icon/app_icon.png
# presplash.filename = %(source.dir)s/Icon/presplash.png

# ── Android ayarları ─────────────────────────────────────────────────────────
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, RECORD_AUDIO, MODIFY_AUDIO_SETTINGS, READ_CALENDAR, WRITE_CALENDAR, POST_NOTIFICATIONS, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MEDIA_PROJECTION, READ_EXTERNAL_STORAGE, VIBRATE, WAKE_LOCK, QUERY_ALL_PACKAGES

android.api = 34
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a

# Donanım hızlandırması ve internet için
android.allow_backup = True
android.accept_sdk_license = True

# audiostream/pyjnius için gerekli java derlemesi
android.enable_androidx = True

# Uygulama sürüm kodu
android.numeric_version = 1

# Çalışma zamanı izinleri ui/jarvis_ui.py içinde request_permissions ile istenir.

[buildozer]

log_level = 2
warn_on_root = 1
