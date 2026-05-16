#!/usr/bin/env python3
"""
JARVIS Android — uygulama giriş noktası
Alp Ünlü tarafından yapılmıştır — @alppunlu

macOS sürümünün Android (Kivy + Buildozer) portu.
Buildozer bu dosyayı APK'nın ana giriş noktası olarak kullanır.
"""

from ui.jarvis_ui import JarvisApp


def main():
    JarvisApp().run()


if __name__ == "__main__":
    main()
