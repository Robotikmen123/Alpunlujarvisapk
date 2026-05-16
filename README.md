# JARVIS — Android

Alp Ünlü tarafından yapılmıştır — @alppunlu

macOS için yazılmış JARVIS sesli asistanının Android (Kivy + Buildozer) portu.
Gemini canlı ses çekirdeği, hafıza, hava durumu, takvim, anımsatıcı, WhatsApp,
medya, YouTube istatistikleri ve ekran analizi özellikleri Android karşılıklarıyla
korunmuştur.

## Proje yapısı

```
main.py                 Kivy uygulama giriş noktası
buildozer.spec          Android APK derleme yapılandırması
app_config.py           API anahtarı / ayar yönetimi
core/
  jarvis_core.py        Gemini canlı ses çekirdeği (macOS main.py portu)
  tools.py              Gemini araç tanımları
  prompt.txt            Sistem istemi
  paths.py              Platform yolu çözümleyici
ui/jarvis_ui.py         Kivy HUD arayüzü (Tkinter UI'nin karşılığı)
android/                Android köprüleri (ses, intent, takvim, ekran yakalama)
actions/                Asistan araçları (Android'e uyarlanmış)
memory/                 Kalıcı bellek
SFX/ Fonts/ Icon/       Ses, font ve görsel varlıklar
```

## APK derleme

```bash
pip install buildozer cython
buildozer -v android debug
```

Üretilen APK `bin/` klasörüne yazılır. İlk derleme Android SDK/NDK indireceği
için uzun sürer. Tüm bağımlılıklar saf Python olduğundan derlenmiş/Rust
bağımlılığı gerekmez.

Alternatif olarak `.github/workflows/build-apk.yml` iş akışı, her push'ta APK'yı
GitHub Actions üzerinde otomatik derler ve artifact olarak yayınlar.

## Kurulum / kullanım

1. APK'yı cihaza yükleyin.
2. İlk açılışta Gemini API anahtarını girin (YouTube anahtarı ve kanal handle'ı
   opsiyoneldir).
3. Uygulama mikrofon, takvim ve bildirim izinlerini ister.
4. Konuşarak ya da metin kutusuna yazarak JARVIS'e komut verin.

## macOS sürümüne göre değişenler

| Özellik | macOS | Android karşılığı |
|---|---|---|
| Arayüz | Tkinter HUD | Kivy HUD |
| Ses G/Ç | PyAudio | audiostream (AudioRecord/AudioTrack) |
| Uygulama açma | `open -a` | PackageManager / Intent |
| Tarayıcı / medya | `open` + AppleScript | Intent (ACTION_VIEW) |
| Takvim / anımsatıcı | EventKit (Swift helper) | CalendarContract |
| WhatsApp | AppleScript otomasyonu | `wa.me` derin bağlantısı (tek dokunuş gönderim) |
| Ekran analizi | ScreenCaptureKit | MediaProjection + ImageReader |
| Sistem bilgisi | psutil / `pmset` | BatteryManager / ActivityManager / StatFs |
| `shell_run` | macOS bash | Kaldırıldı — Android'de güvenli bir karşılığı yok |

`shell_run` dışındaki tüm araçlar ve davranışlar korunmuştur.
