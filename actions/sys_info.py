"""
Sistem bilgisi — Android API'leri ile (BatteryManager, ActivityManager,
StatFs, ConnectivityManager) + /proc okuması.
Alp Ünlü tarafından yapılmıştır — @alppunlu

macOS'taki psutil + subprocess tabanlı sürümün Android karşılığı.
"""

from __future__ import annotations

import datetime
import os
import time

from core.paths import DATA_DIR, ON_ANDROID

from bridge.platform import autoclass, get_context, get_system_service


def sys_info(query: str) -> str:
    query = (query or "").lower().strip()
    results = []

    if query in ("battery", "pil", "all"):
        results.append(_battery())
    if query in ("cpu", "işlemci", "islemci", "all"):
        results.append(_cpu())
    if query in ("ram", "bellek", "memory", "all"):
        results.append(_ram())
    if query in ("disk", "depolama", "all"):
        results.append(_disk())
    if query in ("time", "saat", "zaman", "all"):
        now = datetime.datetime.now()
        results.append(f"Saat: {now.strftime('%H:%M:%S')}")
    if query in ("date", "tarih", "all"):
        now = datetime.datetime.now()
        results.append(f"Tarih: {now.strftime('%d %B %Y, %A')}")
    if query in ("network", "ağ", "ag", "wifi", "all"):
        results.append(_network())

    if not results:
        results.append(
            f"Bilinmeyen sorgu: {query}. battery/cpu/ram/disk/time/date/network/all kullanın."
        )
    return "\n".join(r for r in results if r)


def _battery() -> str:
    if not ON_ANDROID:
        return "Pil bilgisi alınamadı (Android cihaz gerekli)."
    try:
        Intent = autoclass("android.content.Intent")
        IntentFilter = autoclass("android.content.IntentFilter")
        BatteryManager = autoclass("android.os.BatteryManager")
        context = get_context()
        flt = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        battery = context.registerReceiver(None, flt)
        level = battery.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        scale = battery.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        plugged = battery.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1)
        pct = (level * 100.0 / scale) if scale > 0 else -1
        status = "Şarj oluyor" if plugged > 0 else "Pilde"
        if pct >= 0:
            return f"Pil: %{pct:.0f} — {status}"
    except Exception:
        pass
    return "Pil bilgisi alınamadı."


def _cpu() -> str:
    try:
        cores = os.cpu_count() or 1
        usage = _cpu_usage_percent()
        if usage is not None:
            return f"CPU: %{usage:.1f} kullanım — {cores} çekirdek"
        return f"CPU: {cores} çekirdek"
    except Exception:
        return "CPU bilgisi alınamadı."


def _cpu_usage_percent() -> float | None:
    try:
        def _snapshot():
            with open("/proc/stat", "r") as f:
                parts = f.readline().split()
            values = [float(x) for x in parts[1:]]
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            total = sum(values)
            return idle, total

        idle1, total1 = _snapshot()
        time.sleep(0.4)
        idle2, total2 = _snapshot()
        delta_total = total2 - total1
        delta_idle = idle2 - idle1
        if delta_total <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (delta_total - delta_idle) / delta_total))
    except Exception:
        return None


def _ram() -> str:
    if not ON_ANDROID:
        return "RAM bilgisi alınamadı (Android cihaz gerekli)."
    try:
        ActivityManager = autoclass("android.app.ActivityManager")
        MemoryInfo = autoclass("android.app.ActivityManager$MemoryInfo")
        am = get_system_service("activity")
        info = MemoryInfo()
        am.getMemoryInfo(info)
        total = info.totalMem / (1024 ** 3)
        avail = info.availMem / (1024 ** 3)
        used = total - avail
        pct = (used / total * 100) if total else 0
        return f"RAM: {used:.1f}GB / {total:.1f}GB kullanımda (%{pct:.0f})"
    except Exception:
        return "RAM bilgisi alınamadı."


def _disk() -> str:
    try:
        StatFs = autoclass("android.os.StatFs")
        stat = StatFs(str(DATA_DIR))
        block = stat.getBlockSizeLong()
        total = stat.getBlockCountLong() * block / (1024 ** 3)
        free = stat.getAvailableBlocksLong() * block / (1024 ** 3)
        used = total - free
        return f"Depolama: {used:.1f}GB kullanıldı, {free:.1f}GB boş (toplam {total:.1f}GB)"
    except Exception:
        try:
            usage = os.statvfs(str(DATA_DIR))
            total = usage.f_blocks * usage.f_frsize / (1024 ** 3)
            free = usage.f_bavail * usage.f_frsize / (1024 ** 3)
            used = total - free
            return f"Depolama: {used:.1f}GB kullanıldı, {free:.1f}GB boş (toplam {total:.1f}GB)"
        except Exception:
            return "Depolama bilgisi alınamadı."


def _network() -> str:
    if not ON_ANDROID:
        return "Ağ bağlantısı bulunamadı (Android cihaz gerekli)."
    try:
        cm = get_system_service("connectivity")
        active = cm.getActiveNetworkInfo()
        if active is None or not active.isConnected():
            return "Ağ bağlantısı bulunamadı."
        type_name = str(active.getTypeName() or "").lower()
        if "wifi" in type_name:
            try:
                wifi = get_system_service("wifi")
                ssid = str(wifi.getConnectionInfo().getSSID() or "").strip('"')
                if ssid and ssid.lower() != "<unknown ssid>":
                    return f"WiFi: {ssid} bağlı"
            except Exception:
                pass
            return "WiFi bağlı"
        if "mobile" in type_name or "cellular" in type_name:
            return "Mobil veri bağlı"
        return f"Ağ bağlı ({active.getTypeName()})"
    except Exception:
        return "Ağ bağlantısı bulunamadı."
