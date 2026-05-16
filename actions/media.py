"""
Medya oynatma — YouTube, Spotify ve Apple Music (Android uygulamaları).
Alp Ünlü tarafından yapılmıştır — @alppunlu

Android port:
- YouTube : ilk video sonucu çözümlenip YouTube uygulamasında oynatılır.
- Spotify : spotify: arama URI'si ile uygulama içinde arama açılır.
- Apple Music: Apple Music uygulamasında arama açılır.

Not: Android'de üçüncü taraf uygulamalarda otomatik oynatma sınırlıdır;
YouTube doğrudan oynar, Spotify/Apple Music arama ekranını açar.
"""

from __future__ import annotations

import urllib.parse

from bridge.intents import launch_package, open_uri, open_uri_with_package
from actions.browser import browser_control

SPOTIFY_PACKAGE = "com.spotify.music"
APPLE_MUSIC_PACKAGE = "com.apple.android.music"


def _play_youtube(query: str) -> str:
    return browser_control("play_youtube", query=query)


def _play_spotify(query: str, autoplay: bool = True) -> str:
    encoded = urllib.parse.quote(query.strip())
    if open_uri_with_package(f"spotify:search:{encoded}", SPOTIFY_PACKAGE):
        return f"Spotify içinde '{query}' araması açıldı."
    if open_uri(f"https://open.spotify.com/search/{encoded}"):
        return f"Spotify '{query}' araması açıldı."
    return "Spotify açılamadı veya yüklü değil."


def _play_apple_music(query: str, autoplay: bool = True) -> str:
    encoded = urllib.parse.quote(query.strip())
    url = f"https://music.apple.com/search?term={encoded}"
    if open_uri_with_package(url, APPLE_MUSIC_PACKAGE):
        return f"Apple Music içinde '{query}' araması açıldı."
    if open_uri(url):
        return f"Apple Music '{query}' araması açıldı."
    return "Apple Music açılamadı veya yüklü değil."


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    if not query or not query.strip():
        return "Çalınacak içerik belirtilmedi."

    normalized = (provider or "auto").strip().lower()
    if normalized in {"yt", "youtube music"}:
        normalized = "youtube"
    elif normalized in {"apple music", "music", "apple_music"}:
        normalized = "apple_music"

    if normalized == "spotify":
        return _play_spotify(query, autoplay=autoplay)
    if normalized == "apple_music":
        return _play_apple_music(query, autoplay=autoplay)
    if normalized == "youtube":
        return _play_youtube(query)

    # auto: Spotify yüklüyse onu dene, değilse YouTube'da doğrudan oynat
    from core.paths import ON_ANDROID

    if ON_ANDROID:
        try:
            from bridge.platform import get_activity

            pm = get_activity().getPackageManager()
            pm.getLaunchIntentForPackage(SPOTIFY_PACKAGE)
            spotify_installed = pm.getLaunchIntentForPackage(SPOTIFY_PACKAGE) is not None
        except Exception:
            spotify_installed = False
        if spotify_installed:
            return _play_spotify(query, autoplay=autoplay)
    return _play_youtube(query)
