"""KLD-30 (F5-B, 09/10): one sortable form for the two clock formats of the database before any string comparison.

`usage_events.at` is SQLite `datetime('now')` → "2026-10-07 02:38:05" (UTC, a space); `jobs.created_at` is Python
`isoformat` → "2026-10-07T02:38:05+00:00" (a 'T', an offset). Compared as strings, " " < "T", so a usage row at 06:00 sorted BEFORE a job
mark of 05:00 the same day (#22 thống kê). `utc_key` turns both into "YYYY-MM-DD HH:MM:SS" UTC.
"""
from datetime import datetime, timezone


def utc_key(ts) -> str:
    """'YYYY-MM-DD HH:MM:SS' in UTC for any of the formats above (a date alone = midnight; no zone = UTC). Unreadable text is
    returned with 'T' → ' ' so sentinels such as '0000' / '9999' still sort as before."""
    text = str(ts or "").strip()
    if not text:
        return ""
    try:
        dt = datetime.fromisoformat(text.replace(" ", "T", 1).replace("Z", "+00:00"))
    except ValueError:
        return text.replace("T", " ", 1)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
