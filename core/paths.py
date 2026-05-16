"""
Ortak yol cozumleyici — masaustu ve Android'de calisir.
Android'de APK icindeki kaynak dizini salt-okunurdur; yazilabilir veriler
(config, memory) uygulamanin ozel depolama alanina yazilir.
"""

from __future__ import annotations

import os
from pathlib import Path


# APK icindeki / repodaki kaynak dizini (salt-okunur kabul edilir)
SRC_DIR = Path(__file__).resolve().parent.parent

# Android uzerinde calisip calismadigimiz
ON_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ


def _writable_dir() -> Path:
    if ON_ANDROID:
        try:
            from android.storage import app_storage_path  # type: ignore

            base = Path(app_storage_path())
            base.mkdir(parents=True, exist_ok=True)
            return base
        except Exception:
            env_path = os.environ.get("ANDROID_PRIVATE")
            if env_path:
                base = Path(env_path)
                base.mkdir(parents=True, exist_ok=True)
                return base
    return SRC_DIR


DATA_DIR = _writable_dir()
CONFIG_DIR = DATA_DIR / "config"
MEMORY_DIR = DATA_DIR / "memory"
CORE_DIR = SRC_DIR / "core"
SFX_DIR = SRC_DIR / "SFX"
FONTS_DIR = SRC_DIR / "Fonts"
ICON_DIR = SRC_DIR / "Icon"

for _d in (CONFIG_DIR, MEMORY_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def public_storage_dir() -> Path:
    """Kullanicinin disa aktardigi dosyalar icin paylasilan depolama dizini."""
    if ON_ANDROID:
        try:
            from android.storage import primary_external_storage_path  # type: ignore

            return Path(primary_external_storage_path()) / "JARVIS"
        except Exception:
            pass
    return DATA_DIR / "JARVIS"
