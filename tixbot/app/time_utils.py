from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo


def tz_name() -> str:
    """Configured timezone name (defaults to Asia/Shanghai)."""
    return (os.getenv("TZ_NAME", "Asia/Shanghai") or "Asia/Shanghai").strip()


def now_local() -> datetime:
    """Return naive datetime in configured TZ_NAME.

    This project uses *naive datetimes* everywhere, but treats them as "local time"
    in TZ_NAME for both display and scheduling.
    """
    tz = ZoneInfo(tz_name())
    return datetime.now(tz).replace(tzinfo=None, microsecond=0)


def fmt(dt: datetime | None, with_seconds: bool = True) -> str | None:
    if not dt:
        return None
    if with_seconds:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M")
