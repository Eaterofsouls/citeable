# areos/util/clock.py
# Centralized UTC timestamp helper.
# All AREOS modules MUST use this instead of datetime.now().

import datetime

def utc_now_iso() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def utc_today_iso() -> str:
    """Return current UTC date as YYYY-MM-DD."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
