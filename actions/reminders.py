"""
Anımsatıcı aracı — Android'de takvim olayı + alarm olarak gerçeklenir.
Alp Ünlü tarafından yapılmıştır — @alppunlu

Android'de macOS Anımsatıcılar uygulamasının doğrudan bir karşılığı yoktur.
En yakın işlevsel alternatif: anımsatıcılar, sistem takvimine özel bir işaretle
(JARVIS-REMINDER) yazılan ve bir alarm/bildirim taşıyan olaylardır. Böylece
gerçek bir bildirim alır ve sistemde kalıcı olurlar.
"""

from __future__ import annotations

import datetime as dt
import re

from core.paths import ON_ANDROID
from bridge import calendar_provider as cp

TR_WEEKDAYS = ["Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"]
TR_MONTHS = ["", "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
             "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"]


def _normalize_query(query: str) -> tuple[str, int]:
    q = (query or "").strip().lower()
    if any(t in q for t in ("bugun", "today")):
        return "today", 8
    if any(t in q for t in ("geciken", "gecmis", "overdue")):
        return "overdue", 8
    if any(t in q for t in ("siradaki", "sıradaki", "next")):
        return "next", 1
    if any(t in q for t in ("hepsi", "tum", "tüm", "all", "listele")):
        return "all", 10
    return "upcoming", 8


def _encode_description(notes: str, priority: str, list_name: str) -> str:
    parts = [cp.REMINDER_MARKER]
    if priority:
        parts.append(f"priority={priority}")
    if list_name:
        parts.append(f"list={list_name}")
    if notes:
        parts.append(f"notes={notes}")
    return "|".join(parts)


def _decode_description(description: str) -> dict:
    info = {"priority": "", "list_name": "", "notes": ""}
    for chunk in (description or "").split("|"):
        if chunk.startswith("priority="):
            info["priority"] = chunk[9:]
        elif chunk.startswith("list="):
            info["list_name"] = chunk[5:]
        elif chunk.startswith("notes="):
            info["notes"] = chunk[6:]
    return info


def _day_label(when: dt.datetime, now: dt.datetime) -> str:
    today = now.date()
    target = when.date()
    if target == today:
        return "bugun"
    if target == today + dt.timedelta(days=1):
        return "yarin"
    return f"{when.day} {TR_MONTHS[when.month]} {TR_WEEKDAYS[when.weekday()]}"


def _format_due(item: dict, now: dt.datetime) -> str:
    if item["due_ts"] <= 0:
        return "zaman atanmamis"
    due = dt.datetime.fromtimestamp(item["due_ts"])
    if item.get("all_day"):
        return f"{_day_label(due, now)} tum gun"
    return f"{_day_label(due, now)} {due.strftime('%H:%M')}"


def _format_reminder_line(item: dict, now: dt.datetime) -> str:
    parts = [f"{_format_due(item, now)} - {item['title']}"]
    if item.get("list_name"):
        parts.append(f"[{item['list_name']}]")
    if item.get("priority") == "high":
        parts.append("(yuksek oncelik)")
    return " ".join(parts)


def _event_to_reminder(event: dict) -> dict:
    info = _decode_description(event.get("description", ""))
    return {
        "title": event["title"],
        "due_ts": event["start_ts"],
        "all_day": event.get("all_day", False),
        "priority": info["priority"],
        "list_name": info["list_name"],
        "notes": info["notes"],
    }


def _ms(value: dt.datetime) -> int:
    return int(value.timestamp() * 1000)


def get_reminders(query: str = "upcoming", limit: int = 8, list_name: str = "") -> str:
    if not ON_ANDROID:
        return "Anımsatıcılar yalnızca Android cihazda okunabilir."
    mode, default_limit = _normalize_query(query)
    limit = max(1, min(20, int(limit or default_limit)))

    now = dt.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if mode == "today":
        start, end = today_start, today_start + dt.timedelta(days=1)
    elif mode == "overdue":
        start, end = now - dt.timedelta(days=60), now
    elif mode == "next":
        start, end = now, now + dt.timedelta(days=120)
    elif mode == "all":
        start, end = now - dt.timedelta(days=30), now + dt.timedelta(days=120)
    else:
        start, end = now, now + dt.timedelta(days=30)

    try:
        events = cp.query_events(_ms(start), _ms(end))
    except Exception as exc:
        return f"Animsaticilar okunamadi: {exc}. Takvim izni gerekebilir."

    reminders = [_event_to_reminder(e) for e in events
                 if cp.REMINDER_MARKER in (e.get("description") or "")]
    if list_name.strip():
        needle = list_name.strip().lower()
        reminders = [r for r in reminders if needle in (r["list_name"] or "").lower()]
    reminders.sort(key=lambda r: (r["due_ts"] <= 0, r["due_ts"] or 0, r["title"].lower()))
    reminders = reminders[:limit]

    if not reminders:
        return {
            "today": "Bugun icin animsatici gorunmuyor.",
            "overdue": "Geciken animsatici gorunmuyor.",
            "next": "Siradaki animsaticiyi bulamadim.",
            "all": "Kayitli acik animsatici gorunmuyor.",
        }.get(mode, "Yaklasan animsatici gorunmuyor.")

    if mode == "next":
        return f"Siradaki animsatici: {_format_reminder_line(reminders[0], now)}."

    header = {
        "today": f"Bugun icin {len(reminders)} animsatici buldum:",
        "overdue": f"Gecikmis {len(reminders)} animsatici buldum:",
        "all": f"Acik {len(reminders)} animsatici buldum:",
    }.get(mode, f"Yaklasan {len(reminders)} animsatici buldum:")

    lines = [header]
    for item in reminders:
        lines.append(f"- {_format_reminder_line(item, now)}")
    return "\n".join(lines)


def _normalize_due_iso(due_iso: str) -> tuple[dt.datetime | None, bool]:
    raw = (due_iso or "").strip()
    if not raw:
        return None, False
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")
    candidates = (
        ("%Y-%m-%dT%H:%M:%S", False),
        ("%Y-%m-%dT%H:%M", False),
        ("%Y-%m-%d %H:%M:%S", False),
        ("%Y-%m-%d %H:%M", False),
        ("%d.%m.%Y %H:%M", False),
        ("%Y-%m-%d", True),
        ("%d.%m.%Y", True),
    )
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", raw):
        try:
            parsed = dt.datetime.fromisoformat(raw)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed, False
        except ValueError:
            pass
    for fmt, is_all_day in candidates:
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            return parsed, is_all_day
        except ValueError:
            continue
    raise ValueError(
        "Animsatici tarihi gecersiz. due_iso icin 'YYYY-MM-DD' veya 'YYYY-MM-DDTHH:MM' kullan."
    )


def add_reminder(
    title: str,
    due_iso: str = "",
    notes: str = "",
    list_name: str = "",
    priority: str = "",
    all_day: bool = False,
) -> str:
    if not ON_ANDROID:
        return "Anımsatıcılar yalnızca Android cihazda kullanılabilir."
    if not title or not title.strip():
        return "Animsatici basligi bos olamaz."

    normalized_all_day = bool(all_day)
    try:
        due, inferred_all_day = _normalize_due_iso(due_iso)
    except ValueError as exc:
        return str(exc)
    normalized_all_day = normalized_all_day or inferred_all_day

    if due is None:
        # Zaman verilmediyse 1 saat sonrasına ayarla
        due = dt.datetime.now() + dt.timedelta(hours=1)

    if normalized_all_day:
        start = due.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + dt.timedelta(days=1)
    else:
        start = due
        end = due + dt.timedelta(minutes=1)

    priority_norm = (priority or "").strip().lower()
    description = _encode_description(
        (notes or "").strip(), priority_norm, (list_name or "").strip()
    )

    try:
        cp.insert_event(
            title.strip(), int(start.timestamp() * 1000), int(end.timestamp() * 1000),
            all_day=normalized_all_day, notes=description, reminder_minutes=0,
        )
    except Exception as exc:
        return f"Animsatici eklenemedi: {exc}"

    item = {
        "title": title.strip(),
        "due_ts": int(start.timestamp()),
        "all_day": normalized_all_day,
        "priority": priority_norm,
        "list_name": (list_name or "").strip(),
    }
    when = _format_due(item, dt.datetime.now())
    list_suffix = f" [{item['list_name']}]" if item["list_name"] else ""
    return f"Animsatici eklendi: {when} - {item['title']}{list_suffix}"
