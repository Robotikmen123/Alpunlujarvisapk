"""
Android CalendarContract köprüsü.

macOS sürümündeki EventKit/Swift helper'ının doğrudan Android karşılığı.
Takvim olaylarını okur, ekler ve siler; READ_CALENDAR / WRITE_CALENDAR izni gerekir.
"""

from __future__ import annotations

from core.paths import ON_ANDROID

from .platform import autoclass, get_context


REMINDER_MARKER = "JARVIS-REMINDER"


def _content_resolver():
    return get_context().getContentResolver()


def _events_uri():
    return autoclass("android.provider.CalendarContract$Events").CONTENT_URI


def _instances_base_uri():
    return autoclass("android.provider.CalendarContract$Instances").CONTENT_URI


def _calendars_uri():
    return autoclass("android.provider.CalendarContract$Calendars").CONTENT_URI


def _reminders_uri():
    return autoclass("android.provider.CalendarContract$Reminders").CONTENT_URI


def writable_calendar_id() -> int | None:
    """Sahibi tarafından yazılabilir ilk takvimin kimliğini döndürür."""
    if not ON_ANDROID:
        return None
    try:
        cr = _content_resolver()
        projection = ["_id", "calendar_displayName", "calendar_access_level", "visible"]
        cur = cr.query(_calendars_uri(), projection, None, None, None)
        if cur is None:
            return None
        chosen = None
        try:
            while cur.moveToNext():
                access = cur.getInt(2)
                if access >= 500:  # CAL_ACCESS_OWNER / CONTRIBUTOR
                    chosen = cur.getLong(0)
                    break
                if chosen is None:
                    chosen = cur.getLong(0)
        finally:
            cur.close()
        return chosen
    except Exception as exc:
        print(f"[calendar] writable_calendar_id hatası: {exc}")
        return None


def query_events(begin_ms: int, end_ms: int) -> list[dict]:
    """Belirtilen zaman aralığındaki olayları döndürür."""
    if not ON_ANDROID:
        return []
    ContentUris = autoclass("android.content.ContentUris")
    builder = _instances_base_uri().buildUpon()
    ContentUris.appendId(builder, int(begin_ms))
    ContentUris.appendId(builder, int(end_ms))
    uri = builder.build()

    projection = [
        "event_id", "title", "begin", "end", "allDay",
        "calendar_displayName", "eventLocation", "description",
    ]
    cr = _content_resolver()
    cur = cr.query(uri, projection, None, None, "begin ASC")
    events: list[dict] = []
    if cur is None:
        return events
    try:
        while cur.moveToNext():
            events.append({
                "event_id": cur.getLong(0),
                "title": cur.getString(1) or "Adsiz etkinlik",
                "start_ts": int(cur.getLong(2) / 1000),
                "end_ts": int(cur.getLong(3) / 1000),
                "all_day": cur.getInt(4) == 1,
                "calendar": cur.getString(5) or "",
                "location": cur.getString(6) or "",
                "description": cur.getString(7) or "",
            })
    finally:
        cur.close()
    return events


def insert_event(title: str, start_ms: int, end_ms: int, all_day: bool = False,
                  location: str = "", notes: str = "",
                  reminder_minutes: int | None = None) -> dict:
    """Yeni bir takvim olayı ekler. Eklenen olayın bilgisini döndürür."""
    if not ON_ANDROID:
        raise RuntimeError("Takvim yalnızca Android cihazda kullanılabilir.")

    cal_id = writable_calendar_id()
    if cal_id is None:
        raise RuntimeError("Yazılabilir bir takvim bulunamadı.")

    ContentValues = autoclass("android.content.ContentValues")
    ContentUris = autoclass("android.content.ContentUris")
    TimeZone = autoclass("java.util.TimeZone")
    JavaLong = autoclass("java.lang.Long")
    JavaInteger = autoclass("java.lang.Integer")

    values = ContentValues()
    values.put("calendar_id", JavaLong(int(cal_id)))
    values.put("title", str(title))
    values.put("dtstart", JavaLong(int(start_ms)))
    values.put("dtend", JavaLong(int(end_ms)))
    values.put("eventTimezone",
               "UTC" if all_day else TimeZone.getDefault().getID())
    if all_day:
        values.put("allDay", JavaInteger(1))
    if location:
        values.put("eventLocation", str(location))
    if notes:
        values.put("description", str(notes))

    cr = _content_resolver()
    uri = cr.insert(_events_uri(), values)
    event_id = ContentUris.parseId(uri)

    if reminder_minutes is not None:
        try:
            rvalues = ContentValues()
            rvalues.put("event_id", JavaLong(int(event_id)))
            rvalues.put("minutes", JavaInteger(int(reminder_minutes)))
            rvalues.put("method", JavaInteger(1))  # METHOD_ALERT
            cr.insert(_reminders_uri(), rvalues)
        except Exception as exc:
            print(f"[calendar] hatırlatma eklenemedi: {exc}")

    return {
        "event_id": event_id,
        "title": title,
        "start_ts": int(start_ms / 1000),
        "end_ts": int(end_ms / 1000),
        "all_day": all_day,
        "location": location,
        "calendar": "",
        "description": notes,
    }


def delete_event(event_id: int) -> bool:
    if not ON_ANDROID:
        return False
    try:
        ContentUris = autoclass("android.content.ContentUris")
        uri = ContentUris.withAppendedId(_events_uri(), int(event_id))
        deleted = _content_resolver().delete(uri, None, None)
        return deleted > 0
    except Exception as exc:
        print(f"[calendar] delete_event hatası: {exc}")
        return False
