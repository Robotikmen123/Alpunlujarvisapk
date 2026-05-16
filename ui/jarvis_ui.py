"""
JARVIS Android — Kivy arayüzü
Alp Ünlü tarafından yapılmıştır — @alppunlu

macOS Tkinter HUD'unun Android (Kivy) karşılığı:
eş merkezli halkalar, durum renkleri, konuşma günlüğü, metin girişi,
sustur/duraklat kontrolleri ve API anahtarı kurulum ekranı.
"""

from __future__ import annotations

import datetime
import math
import threading
import time

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from app_config import has_gemini_api_key, load_app_config, save_app_config
from core.paths import FONTS_DIR, ON_ANDROID, SFX_DIR

# ── Renk paleti (macOS sürümüyle aynı) ───────────────────────────────────────
C_BG = (2 / 255, 12 / 255, 12 / 255, 1)
C_PRI = (0, 212 / 255, 192 / 255, 1)
C_PANEL = (3 / 255, 15 / 255, 15 / 255, 1)
C_DIM = (10 / 255, 42 / 255, 40 / 255, 1)
C_TEXT = (125 / 255, 1, 246 / 255, 1)
C_ORG = (1, 102 / 255, 0, 1)

SYSTEM_NAME = "J.A.R.V.I.S"
MODEL_BADGE = "VOICE CORE · ANDROID"

VOICES = ["Charon", "Puck", "Aoede", "Kore", "Fenrir", "Leda", "Orus", "Zephyr"]

# Orb durum renkleri (0-1 normalize)
ORB_COLORS = {
    "LISTENING":    (0, 1, 136 / 255),
    "SPEAKING":     (68 / 255, 136 / 255, 1),
    "THINKING":     (1, 204 / 255, 0),
    "MUTED":        (200 / 255, 30 / 255, 80 / 255),
    "PAUSED":       (30 / 255, 60 / 255, 55 / 255),
    "ERROR":        (1, 51 / 255, 68 / 255),
    "INITIALISING": (1, 51 / 255, 68 / 255),
}

STATE_LABELS = {
    "LISTENING": "DİNLİYOR",
    "SPEAKING": "KONUŞUYOR",
    "THINKING": "DÜŞÜNÜYOR",
    "MUTED": "SESSİZ",
    "PAUSED": "DURAKLATILDI",
    "ERROR": "HATA",
    "INITIALISING": "BAŞLATILIYOR",
}

_FONT_BODY = "Roboto"
_FONT_DISPLAY = "Roboto"


def _register_fonts():
    global _FONT_BODY, _FONT_DISPLAY
    try:
        regular = FONTS_DIR / "Grift-Regular.ttf"
        bold = FONTS_DIR / "Grift-Bold.ttf"
        extra = FONTS_DIR / "Grift-ExtraBold.ttf"
        if regular.exists():
            LabelBase.register(
                name="Grift",
                fn_regular=str(regular),
                fn_bold=str(bold if bold.exists() else regular),
            )
            _FONT_BODY = "Grift"
        if extra.exists():
            LabelBase.register(name="GriftDisplay", fn_regular=str(extra))
            _FONT_DISPLAY = "GriftDisplay"
        elif regular.exists():
            _FONT_DISPLAY = "Grift"
    except Exception as exc:
        print(f"[ui] font kaydı hatası: {exc}")


# ── Ses yöneticisi ───────────────────────────────────────────────────────────
class SoundManager:
    def __init__(self):
        self._enabled = True
        self._cache: dict[str, object] = {}
        self._ambient = None
        self._ambient_on = False

    def _load(self, name: str):
        if name not in self._cache:
            path = SFX_DIR / name
            self._cache[name] = SoundLoader.load(str(path)) if path.exists() else None
        return self._cache[name]

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self.stop_ambient()

    def play(self, name: str, volume: float = 0.6):
        if not self._enabled:
            return
        snd = self._load(name)
        if snd is not None:
            try:
                snd.volume = volume
                snd.play()
            except Exception:
                pass

    def start_ambient(self):
        if not self._enabled or self._ambient_on:
            return
        self._ambient = self._load("HUD.mp3")
        if self._ambient is not None:
            try:
                self._ambient.loop = True
                self._ambient.volume = 0.20
                self._ambient.play()
                self._ambient_on = True
            except Exception:
                pass

    def stop_ambient(self):
        if self._ambient is not None:
            try:
                self._ambient.stop()
            except Exception:
                pass
        self._ambient_on = False


# ── Orb widget'ı (eş merkezli halkalar) ──────────────────────────────────────
class Orb(Widget):
    phase = NumericProperty(0.0)
    pulse = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._color = ORB_COLORS["INITIALISING"]
        self._target = ORB_COLORS["INITIALISING"]
        self.bind(pos=self._redraw, size=self._redraw,
                  phase=self._redraw, pulse=self._redraw)
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def set_color(self, rgb):
        self._target = rgb

    def _tick(self, dt):
        # rengi yumuşak geçişle hedefe yaklaştır
        self._color = tuple(
            c + (t - c) * 0.12 for c, t in zip(self._color, self._target)
        )
        self.phase += dt * 0.6
        self.pulse = 0.5 + 0.5 * math.sin(time.time() * 2.2)

    def _redraw(self, *_):
        self.canvas.clear()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        base = min(self.width, self.height) / 2 * 0.92
        r, g, b = self._color
        with self.canvas:
            # dış halkalar
            for i, frac in enumerate((1.0, 0.78, 0.56)):
                alpha = 0.20 + 0.18 * (3 - i)
                Color(r, g, b, alpha * (0.6 + 0.4 * self.pulse))
                Line(circle=(cx, cy, base * frac), width=1.4)
            # segmentli yay (dönen)
            seg = 36
            for k in range(seg):
                a0 = (k / seg) * 360 + math.degrees(self.phase) * 40
                a1 = a0 + (360 / seg) * 0.55
                Color(r, g, b, 0.85 if k % 2 == 0 else 0.25)
                Line(circle=(cx, cy, base * 0.88, a0, a1), width=3.0)
            # iç çekirdek
            core = base * 0.34 * (0.85 + 0.15 * self.pulse)
            Color(r, g, b, 0.16)
            Ellipse(pos=(cx - core * 1.5, cy - core * 1.5),
                    size=(core * 3, core * 3))
            Color(r, g, b, 0.92)
            Ellipse(pos=(cx - core, cy - core), size=(core * 2, core * 2))


# ── Günlük görünümü ──────────────────────────────────────────────────────────
class LogView(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bar_width = 4
        self.label = Label(
            size_hint_y=None, halign="left", valign="top",
            markup=True, font_name=_FONT_BODY, font_size="15sp",
            color=C_TEXT, padding=("12dp", "10dp"),
        )
        self.label.bind(width=lambda *_: setattr(self.label, "text_size",
                                                 (self.label.width, None)))
        self.label.bind(texture_size=lambda *_: setattr(
            self.label, "height", self.label.texture_size[1]))
        self.add_widget(self.label)
        self._lines: list[str] = []

    def append(self, line: str):
        self._lines.append(line)
        if len(self._lines) > 200:
            self._lines = self._lines[-200:]
        self.label.text = "\n".join(self._lines)
        Clock.schedule_once(lambda *_: setattr(self, "scroll_y", 0), 0.05)


# ── Kurulum ekranı ───────────────────────────────────────────────────────────
class SetupScreen(Screen):
    def __init__(self, on_ready, **kwargs):
        super().__init__(**kwargs)
        self._on_ready = on_ready
        cfg = load_app_config()

        root = BoxLayout(orientation="vertical", padding="22dp", spacing="14dp")
        with root.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg, "pos", root.pos),
                  size=lambda *_: setattr(self._bg, "size", root.size))

        root.add_widget(Label(
            text=SYSTEM_NAME, font_name=_FONT_DISPLAY, font_size="34sp",
            color=C_PRI, size_hint_y=None, height="60dp"))
        root.add_widget(Label(
            text="Başlamak için Gemini API anahtarını gir",
            font_name=_FONT_BODY, font_size="15sp", color=C_TEXT,
            size_hint_y=None, height="30dp"))

        self.key_input = TextInput(
            text=str(cfg.get("gemini_api_key", "")), hint_text="Gemini API Key",
            multiline=False, size_hint_y=None, height="48dp",
            background_color=C_PANEL, foreground_color=C_TEXT,
            cursor_color=C_PRI, font_name=_FONT_BODY, font_size="15sp",
            password=True,
        )
        root.add_widget(self.key_input)

        self.yt_key = TextInput(
            text=str(cfg.get("youtube_api_key", "")),
            hint_text="YouTube API Key (opsiyonel)",
            multiline=False, size_hint_y=None, height="48dp",
            background_color=C_PANEL, foreground_color=C_TEXT,
            cursor_color=C_PRI, font_name=_FONT_BODY, font_size="15sp",
        )
        root.add_widget(self.yt_key)

        self.yt_handle = TextInput(
            text=str(cfg.get("youtube_channel_handle", "")),
            hint_text="YouTube kanal handle (opsiyonel, örn. @kanal)",
            multiline=False, size_hint_y=None, height="48dp",
            background_color=C_PANEL, foreground_color=C_TEXT,
            cursor_color=C_PRI, font_name=_FONT_BODY, font_size="15sp",
        )
        root.add_widget(self.yt_handle)

        self.voice_btn = Button(
            text=f"Ses: {cfg.get('voice', 'Charon')}", size_hint_y=None,
            height="44dp", background_normal="", background_color=C_DIM,
            color=C_TEXT, font_name=_FONT_BODY, font_size="15sp",
        )
        self.voice_btn.bind(on_release=self._cycle_voice)
        root.add_widget(self.voice_btn)

        self.status = Label(
            text="", font_name=_FONT_BODY, font_size="13sp",
            color=C_ORG, size_hint_y=None, height="26dp")
        root.add_widget(self.status)

        start_btn = Button(
            text="JARVIS'i BAŞLAT", size_hint_y=None, height="56dp",
            background_normal="", background_color=C_PRI,
            color=C_BG, font_name=_FONT_DISPLAY, font_size="18sp",
        )
        start_btn.bind(on_release=self._start)
        root.add_widget(start_btn)
        root.add_widget(Widget())
        self.add_widget(root)

    def _cycle_voice(self, *_):
        current = self.voice_btn.text.replace("Ses: ", "").strip()
        idx = (VOICES.index(current) + 1) % len(VOICES) if current in VOICES else 0
        self.voice_btn.text = f"Ses: {VOICES[idx]}"

    def _start(self, *_):
        key = self.key_input.text.strip()
        if not key:
            self.status.text = "Gemini API anahtarı gerekli."
            return
        save_app_config({
            "gemini_api_key": key,
            "youtube_api_key": self.yt_key.text.strip(),
            "youtube_channel_handle": self.yt_handle.text.strip(),
            "voice": self.voice_btn.text.replace("Ses: ", "").strip(),
        })
        self._on_ready()


# ── HUD ekranı ───────────────────────────────────────────────────────────────
class HudScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        root = BoxLayout(orientation="vertical", padding="10dp", spacing="8dp")
        with root.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg, "pos", root.pos),
                  size=lambda *_: setattr(self._bg, "size", root.size))

        # üst bar
        top = BoxLayout(size_hint_y=None, height="40dp")
        top.add_widget(Label(
            text=SYSTEM_NAME, font_name=_FONT_DISPLAY, font_size="22sp",
            color=C_PRI, halign="left", valign="middle"))
        self.state_badge = Label(
            text="BAŞLATILIYOR", font_name=_FONT_BODY, font_size="14sp",
            color=C_ORG, halign="right", valign="middle")
        top.add_widget(self.state_badge)
        root.add_widget(top)

        # bilgi satırı (saat / sistem / hava)
        info = BoxLayout(size_hint_y=None, height="30dp", spacing="6dp")
        self.time_label = Label(text="--:--", font_name=_FONT_BODY,
                                font_size="13sp", color=C_TEXT)
        self.system_label = Label(text="Sistem —", font_name=_FONT_BODY,
                                  font_size="13sp", color=C_TEXT)
        self.weather_label = Label(text="Hava —", font_name=_FONT_BODY,
                                   font_size="13sp", color=C_TEXT)
        info.add_widget(self.time_label)
        info.add_widget(self.system_label)
        info.add_widget(self.weather_label)
        root.add_widget(info)

        # orb
        self.orb = Orb(size_hint_y=0.42)
        root.add_widget(self.orb)

        # günlük
        self.log = LogView(size_hint_y=0.38)
        root.add_widget(self.log)

        # giriş satırı
        input_row = BoxLayout(size_hint_y=None, height="48dp", spacing="6dp")
        self.text_input = TextInput(
            hint_text="JARVIS'e yaz...", multiline=False,
            background_color=C_PANEL, foreground_color=C_TEXT,
            cursor_color=C_PRI, font_name=_FONT_BODY, font_size="15sp",
        )
        self.text_input.bind(on_text_validate=self._send_text)
        send_btn = Button(text="GÖNDER", size_hint_x=None, width="92dp",
                          background_normal="", background_color=C_PRI,
                          color=C_BG, font_name=_FONT_BODY, font_size="14sp")
        send_btn.bind(on_release=self._send_text)
        input_row.add_widget(self.text_input)
        input_row.add_widget(send_btn)
        root.add_widget(input_row)

        # kontrol satırı
        controls = BoxLayout(size_hint_y=None, height="46dp", spacing="6dp")
        self.mute_btn = Button(text="SUSTUR", background_normal="",
                               background_color=C_DIM, color=C_TEXT,
                               font_name=_FONT_BODY, font_size="14sp")
        self.mute_btn.bind(on_release=self._toggle_mute)
        self.pause_btn = Button(text="DURAKLAT", background_normal="",
                                background_color=C_DIM, color=C_TEXT,
                                font_name=_FONT_BODY, font_size="14sp")
        self.pause_btn.bind(on_release=self._toggle_pause)
        self.fx_btn = Button(text="SES EFEKTİ: AÇIK", background_normal="",
                             background_color=C_DIM, color=C_TEXT,
                             font_name=_FONT_BODY, font_size="14sp")
        self.fx_btn.bind(on_release=self._toggle_fx)
        controls.add_widget(self.mute_btn)
        controls.add_widget(self.pause_btn)
        controls.add_widget(self.fx_btn)
        root.add_widget(controls)

        self.add_widget(root)

        Clock.schedule_interval(self._update_clock, 1.0)
        Clock.schedule_once(lambda *_: self.app.refresh_info_panels(), 2.0)
        Clock.schedule_interval(lambda *_: self.app.refresh_info_panels(), 600.0)

    def _update_clock(self, *_):
        now = datetime.datetime.now()
        self.time_label.text = now.strftime("%H:%M:%S")

    def _send_text(self, *_):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""
        cb = self.app.on_text_command
        if cb:
            threading.Thread(target=lambda: cb(text), daemon=True).start()

    def _toggle_mute(self, *_):
        self.app.set_muted(not self.app.muted)

    def _toggle_pause(self, *_):
        self.app.set_paused(not self.app.paused)

    def _toggle_fx(self, *_):
        self.app.set_effects(not self.app.effects_on)


# ── Ana uygulama ─────────────────────────────────────────────────────────────
class JarvisApp(App):
    title = "JARVIS"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # core tarafından atanan geri çağrılar
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_effects_state_change = None
        # durum
        self.muted = False
        self.paused = False
        self.effects_on = True
        self._state = "INITIALISING"
        self._core_started = False
        self.sound = SoundManager()
        self.hud = None

    # ── Kivy yaşam döngüsü ───────────────────────────────────────────────────
    def build(self):
        _register_fonts()
        Window.clearcolor = C_BG
        self.sm = ScreenManager(transition=FadeTransition(duration=0.3))
        self.setup_screen = SetupScreen(name="setup", on_ready=self._enter_hud)
        self.hud = HudScreen(self, name="hud")
        self.sm.add_widget(self.setup_screen)
        self.sm.add_widget(self.hud)
        if has_gemini_api_key():
            Clock.schedule_once(lambda *_: self._enter_hud(), 0.4)
        else:
            self.sm.current = "setup"
        return self.sm

    def on_start(self):
        self._request_android_permissions()

    def _request_android_permissions(self):
        if not ON_ANDROID:
            return
        try:
            from android.permissions import Permission, request_permissions

            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.INTERNET,
                Permission.READ_CALENDAR,
                Permission.WRITE_CALENDAR,
                Permission.POST_NOTIFICATIONS,
            ])
        except Exception as exc:
            print(f"[ui] izin isteği hatası: {exc}")

    def _enter_hud(self):
        self.sm.current = "hud"
        self.sound.start_ambient()
        if not self._core_started:
            self._core_started = True
            Clock.schedule_once(lambda *_: self._start_core(), 0.6)

    def _start_core(self):
        import asyncio

        from core.jarvis_core import JarvisLive

        def runner():
            try:
                jarvis = JarvisLive(self)
                asyncio.run(jarvis.run())
            except Exception as exc:
                import traceback
                traceback.print_exc()
                self.write_log(f"ERR: JARVIS çekirdeği başlatılamadı — {exc}")

        threading.Thread(target=runner, daemon=True).start()

    # ── core'un kullandığı arayüz ────────────────────────────────────────────
    @mainthread
    def write_log(self, text: str):
        if self.hud is None:
            return
        color = "7dfff6"
        if text.startswith("Siz:"):
            color = "ffcc00"
        elif text.startswith("JARVIS:"):
            color = "00d4c0"
        elif text.startswith("ERR:"):
            color = "ff3344"
        elif text.startswith("SYS:"):
            color = "00ff88"
        self.hud.log.append(f"[color=#{color}]{text}[/color]")

    @mainthread
    def write_debug(self, text: str, level: str = "INFO"):
        print(f"[JARVIS:{level}] {text}")

    @mainthread
    def set_state(self, state: str):
        self._state = state
        if self.muted and state in ("LISTENING", "SPEAKING"):
            state = "MUTED"
        if self.paused:
            state = "PAUSED"
        if self.hud is not None:
            self.hud.orb.set_color(ORB_COLORS.get(state, ORB_COLORS["INITIALISING"]))
            self.hud.state_badge.text = STATE_LABELS.get(state, state)

    def play_success_sfx(self):
        Clock.schedule_once(lambda *_: self.sound.play("Done.mp3", volume=0.7), 0)

    @mainthread
    def mark_user_activity(self, active: bool):
        pass

    @mainthread
    def focus_panel(self, name: str, duration_ms: int = 5000):
        if self.hud is None:
            return
        label = {
            "time": self.hud.time_label,
            "system": self.hud.system_label,
            "weather": self.hud.weather_label,
        }.get(name)
        if label is None:
            return
        label.color = C_ORG

        def _restore(*_):
            label.color = C_TEXT

        Clock.schedule_once(_restore, duration_ms / 1000.0)

    # ── kontrol eylemleri ────────────────────────────────────────────────────
    def set_muted(self, value: bool):
        self.muted = value
        if self.hud is not None:
            self.hud.mute_btn.text = "SESİ AÇ" if value else "SUSTUR"
            self.hud.mute_btn.background_color = C_ORG if value else C_DIM
        self.set_state(self._state)

    def set_paused(self, value: bool):
        self.paused = value
        if self.hud is not None:
            self.hud.pause_btn.text = "DEVAM ET" if value else "DURAKLAT"
            self.hud.pause_btn.background_color = C_ORG if value else C_DIM
        if self.on_pause_toggle:
            self.on_pause_toggle(value)
        self.set_state(self._state)

    def set_effects(self, value: bool):
        self.effects_on = value
        self.sound.set_enabled(value)
        if value:
            self.sound.start_ambient()
        if self.hud is not None:
            self.hud.fx_btn.text = f"SES EFEKTİ: {'AÇIK' if value else 'KAPALI'}"
        if self.on_effects_state_change:
            self.on_effects_state_change(value)

    # ── bilgi panelleri ──────────────────────────────────────────────────────
    def refresh_info_panels(self):
        def worker():
            try:
                from actions.sys_info import sys_info
                battery = sys_info("battery").splitlines()[0]
            except Exception:
                battery = "Sistem —"
            try:
                from actions.weather import get_weather_summary
                weather = get_weather_summary(None)
            except Exception:
                weather = "Hava —"
            self._apply_info_panels(battery, weather)

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _apply_info_panels(self, battery: str, weather: str):
        if self.hud is None:
            return
        self.hud.system_label.text = battery[:40]
        self.hud.weather_label.text = weather[:48]
