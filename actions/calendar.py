"""
Takvim aracı — Android CalendarContract üzerinden çalışır.
Alp Ünlü tarafından yapılmıştır — @alppunlu

macOS sürümündeki Apple Calendar / EventKit erişiminin Android karşılığı.
Doğal dil sorgu çözümlemesi ve çıktı biçimi macOS sürümüyle aynıdır.
"""

from __future__ import annotations

import datetime as dt
import re

from core.paths import ON_ANDROID
from bridge import calendar_provider as cp


TR_WEEKDAYS = ["Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"]
TR_MONTHS = ["", "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
             "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"]

DEFAULT_EVENT_MINUTES = 60


def _month_start(value: dt.datetime) -> dt.datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(value: dt.datetime, months: int) -> dt.datetime:
    total = (value.year * 12 + (value.month - 1)) + months
    year = total // 12
    month = total % 12 + 1
    return value.replace(year=year, month=month, day=1)


def _normalize_query(query: str) -> dict:
    q = (query or "today").strip().lower()
    now = dt.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    month_match = re.search(r"(\d+)\s*(ay|month|months)", q)
    if any(t in q for t in ("gelecek ay", "önümüzdeki ay", "onumuzdeki ay", "next month")):
        start = _add_months(_month_start(now), 1)
        end = _add_months(start, 1)
        return dict(start=start, end=end, default_limit=24, kind="next_month",
                    header="Gelecek ay icin {count} etkinlik buldum:",
                    empty="Gelecek ay takviminde etkinlik gorunmuyor.")
    if "bu ay" in q or "this month" in q:
        start = _month_start(now)
        end = _add_months(start, 1)
        return dict(start=start, end=end, default_limit=24, kind="this_month",
                    header="Bu ay icin {count} etkinlik buldum:",
                    empty="Bu ay takviminde etkinlik gorunmuyor.")
    if month_match:
        months = max(1, min(12, int(month_match.group(1))))
        return dict(start=today_start, end=_add_months(_month_start(now), months),
                    default_limit=min(60, max(12, months * 12)), kind="months",
                    header=f"Onumuzdeki {months} ay icin {{count}} etkinlik buldum:",
                    empty=f"Onumuzdeki {months} ayda takviminde etkinlik gorunmuyor.")

    week_match = re.search(r"(\d+)\s*(hafta|week|weeks)", q)
    if week_match:
        weeks = max(1, min(12, int(week_match.group(1))))
        return dict(start=today_start, end=today_start + dt.timedelta(days=weeks * 7),
                    default_limit=min(60, max(8, weeks * 8)), kind="weeks",
                    header=f"Onumuzdeki {weeks} hafta icin {{count}} etkinlik buldum:",
                    empty=f"Onumuzdeki {weeks} haftada takviminde etkinlik gorunmuyor.")

    day_match = re.search(r"(\d+)\s*(g[uü]n|gun|day|days)", q)
    if day_match:
        days = max(1, min(365, int(day_match.group(1))))
        return dict(start=today_start, end=today_start + dt.timedelta(days=days),
                    default_limit=min(60, max(8, days * 2)), kind="days",
                    header=f"Onumuzdeki {days} gun icin {{count}} etkinlik buldum:",
                    empty=f"Onumuzdeki {days} gunde takviminde etkinlik gorunmuyor.")

    if any(t in q for t in ("yarin", "tomorrow")):
        start = today_start + dt.timedelta(days=1)
        return dict(start=start, end=start + dt.timedelta(days=1),
                    default_limit=6, kind="tomorrow",
                    header="Yarin icin {count} etkinlik buldum:",
                    empty="Yarin takviminde etkinlik gorunmuyor.")
    if any(t in q for t in ("hafta", "week", "7 gun")):
        return dict(start=today_start, end=today_start + dt.timedelta(days=7),
                    default_limit=10, kind="week",
                    header="Onumuzdeki 7 gun icin {count} etkinlik buldum:",
                    empty="Onumuzdeki 7 gunde takviminde etkinlik gorunmuyor.")
    if any(t in q for t in ("siradaki", "sıradaki", "sonraki", "next")):
        return dict(start=now, end=now + dt.timedelta(days=120),
                    default_limit=1, kind="next", header="",
                    empty="Siradaki takvim etkinligini bulamadim.")
    if any(t in q for t in ("ajanda", "agenda", "yaklasan", "yaklaşan", "upcoming")):
        return dict(start=now, end=now + dt.timedelta(days=14),
                    default_limit=8, kind="agenda",
                    header="Yaklasan ajandanda {count} etkinlik var:",
                    empty="Yaklasan takvim etkinligi gorunmuyor.")
    return dict(start=today_start, end=today_start + dt.timedelta(days=1),
                default_limit=6, kind="today",
                header="Bugun icin {count} etkinlik buldum:",
                empty="Bugun takviminde etkinlik gorunmuyor.")


def _day_label(when: dt.datetime, now: dt.datetime) -> str:
    today = now.date()
    target = when.date()
    if target == today:
        return "bugun"
    if target == today + dt.timedelta(days=1):
        return "yarin"
    return f"{when.day} {TR_MONTHS[when.month]} {TR_WEEKDAYS[when.weekday()]}"


def _format_time_range(event: dict, now: dt.datetime) -> str:
    start = dt.datetime.fromtimestamp(event["start_ts"])
    end = dt.datetime.fromtimestamp(event["end_ts"])
    prefix = _day_label(start, now)
    if event.get("all_day"):
        return f"{prefix} tum gun"
    return f"{prefix} {start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def _format_event_line(event: dict, now: dt.datetime) -> str:
    pieces = [f"{_format_time_range(event, now)} - {event['title']}"]
    if event.get("calendar"):
        pieces.append(f"[{event['calendar']}]")
    if event.get("location"):
        pieces.append(f"@ {event['location']}")
    return " ".join(pieces)


def _parse_iso(raw: str) -> dt.datetime:
    raw = (raw or "").strip()
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")
    candidates = (
        None,  # fromisoformat
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M", "%Y-%m-%d", "%d.%m.%Y",
    )
    for fmt in candidates:
        try:
            if fmt is None:
                parsed = dt.datetime.fromisoformat(raw)
            else:
                parsed = dt.datetime.strptime(raw, fmt)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    raise ValueError("Tarih çözümlenemedi. ISO veya 'YYYY-MM-DD HH:MM' kullan.")


def _ms(value: dt.datetime) -> int:
    return int(value.timestamp() * 1000)


def get_calendar_events(query: str = "today", limit: int = 6) -> str:
    if not ON_ANDROID:
        return "Takvim yalnızca Android cihazda okunabilir."
    window = _normalize_query(query)
    limit = max(1, min(60, int(limit or window["default_limit"])))

    try:
        events = cp.query_events(_ms(window["start"]), _ms(window["end"]))
    except Exception as exc:
        return f"Takvim okunamadi: {exc}. Takvim izni gerekebilir."

    # Animsatici olarak isaretli olaylari takvim listesinden cikar
    events = [e for e in events if cp.REMINDER_MARKER not in (e.get("description") or "")]
    events.sort(key=lambda e: (e["start_ts"], e["title"].lower()))

    now = dt.datetime.now()
    if window["kind"] in {"next", "agenda"}:
        events = [e for e in events if e["end_ts"] >= int(now.timestamp())]

    if not events:
        return window["empty"]

    if window["kind"] == "next":
        return f"Siradaki etkinlik: {_format_event_line(events[0], now)}."

    selected = events[:limit]
    header = str(window["header"]).format(count=len(selected))
    lines = [header]
    for event in selected:
        lines.append(f"- {_format_event_line(event, now)}")
    return "\n".join(lines)


def add_calendar_event(
    title: str,
    start_iso: str,
    end_iso: str = "",
    notes: str = "",
    location: str = "",
    calendar_name: str = "",
    all_day: bool = False,
) -> str:
    if not ON_ANDROID:
        return "Takvim yalnızca Android cihazda kullanılabilir."
    title = (title or "").strip()
    if not title:
        return "Takvime eklemek icin etkinlik basligi gerekli."
    if not (start_iso or "").strip():
        return "Takvime eklemek icin baslangic tarihi gerekli."

    try:
        start = _parse_iso(start_iso)
    except ValueError as exc:
        return str(exc)

    if (end_iso or "").strip():
        try:
            end = _parse_iso(end_iso)
        except ValueError as exc:
            return str(exc)
    elif all_day:
        end = start + dt.timedelta(days=1)
    else:
        end = start + dt.timedelta(minutes=DEFAULT_EVENT_MINUTES)

    try:
        event = cp.insert_event(
            title, _ms(start), _ms(end), all_day=bool(all_day),
            location=(location or "").strip(), notes=(notes or "").strip(),
        )
    except Exception as exc:
        return f"Takvim etkinligi eklenemedi: {exc}"

    line = _format_event_line(event, dt.datetime.now())
    return f"Takvime eklendi: {line}."


def delete_calendar_event(
    title: str,
    start_iso: str = "",
    calendar_name: str = "",
    delete_all_matches: bool = False,
) -> str:
    if not ON_ANDROID:
        return "Takvim yalnızca Android cihazda kullanılabilir."
    title = (title or "").strip()
    if not title:
        return "Takvimden silmek icin etkinlik basligi gerekli."

    now = dt.datetime.now()
    search_start = now - dt.timedelta(days=365)
    search_end = now + dt.timedelta(days=365)

    target_ts = None
    if (start_iso or "").strip():
        try:
            target_ts = int(_parse_iso(start_iso).timestamp())
        except ValueError:
            target_ts = None

    try:
        events = cp.query_events(_ms(search_start), _ms(search_end))
    except Exception as exc:
        return f"Takvim etkinligi silinemedi: {exc}"

    needle = title.lower()
    matches = [e for e in events if needle in (e.get("title") or "").lower()
               and cp.REMINDER_MARKER not in (e.get("description") or "")]
    if target_ts is not None:
        matches = [e for e in matches if abs(e["start_ts"] - target_ts) <= 3600] or matches

    if not matches:
        return f"'{title}' adli bir takvim etkinligi bulamadim."

    if len(matches) > 1 and not delete_all_matches and target_ts is None:
        preview = " | ".join(_format_event_line(e, now) for e in matches[:3])
        return (f"Ayni ada sahip birden fazla etkinlik var. "
                f"Hangisini sileyim? Eslesenler: {preview}")

    to_delete = matches if delete_all_matches else matches[:1]
    deleted = [e for e in to_delete if cp.delete_event(e["event_id"])]
    if not deleted:
        return "Takvim etkinligi silinemedi."

    line = _format_event_line(deleted[0], now)
    if len(deleted) > 1:
        return f"Takvimden {len(deleted)} etkinlik silindi: {line} ve digerleri."
    return f"Takvimden silindi: {line}."
