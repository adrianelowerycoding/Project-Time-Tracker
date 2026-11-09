"""Pure time helpers: shift-date math and HH:MM:SS formatting. No UI, no files."""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from .config import CENTRAL_TZ, SHIFT_WINDOWS_CENTRAL


def _shift_local_window(worker_tz, shift_number, central_anchor_date):
    """Convert the Central-time-defined window for `shift_number` - the
    specific occurrence anchored to `central_anchor_date` (a Central calendar
    date) - into the equivalent timezone-aware start/end datetimes in
    `worker_tz`. Uses real zoneinfo conversion rather than arithmetic on raw
    hours, so DST (and Vietnam's lack of it) comes out correct automatically."""
    start_t, end_t = SHIFT_WINDOWS_CENTRAL.get(shift_number, SHIFT_WINDOWS_CENTRAL[1])
    start_central = datetime.datetime.combine(central_anchor_date, start_t, tzinfo=CENTRAL_TZ)
    end_date = central_anchor_date if end_t > start_t else central_anchor_date + datetime.timedelta(days=1)
    end_central = datetime.datetime.combine(end_date, end_t, tzinfo=CENTRAL_TZ)
    return start_central.astimezone(worker_tz), end_central.astimezone(worker_tz)


def compute_shift_date(local_dt, shift_number):
    """Return the date (a datetime.date, in the WORKER's own local calendar)
    that an entire shift should be attributed to, given a timezone-aware
    local datetime and a shift number. This is the "Shift Date" used to
    group Project Totals.

    Shift hours are defined once, in Central time (SHIFT_WINDOWS_CENTRAL).
    Step 1 figures out which Central calendar day's occurrence of the shift
    this instant belongs to, using the "before the end time -> previous day"
    rule evaluated in Central time, since that's where the boundaries are
    actually defined. Step 2 converts THAT specific occurrence's start time
    into the worker's own local calendar - that converted date is what gets
    recorded. This stays correct even when a shift that doesn't cross
    midnight in Central time ends up crossing midnight once translated into
    a worker's own local time (or vice versa) - no special-casing needed,
    since the "crossing" behavior falls out naturally from converting one
    real, absolute instant into another timezone.
    """
    worker_tz = local_dt.tzinfo
    central_dt = local_dt.astimezone(CENTRAL_TZ)

    start_t, end_t = SHIFT_WINDOWS_CENTRAL.get(shift_number, SHIFT_WINDOWS_CENTRAL[1])
    crosses_midnight_central = end_t <= start_t
    if crosses_midnight_central and central_dt.time() < end_t:
        central_anchor_date = (central_dt - datetime.timedelta(days=1)).date()
    else:
        central_anchor_date = central_dt.date()

    start_local, _end_local = _shift_local_window(worker_tz, shift_number, central_anchor_date)
    return start_local.date()


def current_shift_date(timezone_name, shift_number, now_utc=None):
    """The shift date for 'right now' under the given profile settings - not
    the literal calendar date - so a 3rd-shift worker checking this at 2am
    still gets the shift they're in the middle of. `now_utc` is injectable
    so this can be tested without depending on the real clock."""
    tz = ZoneInfo(timezone_name)
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_local = now_utc.astimezone(tz)
    return compute_shift_date(now_local, shift_number)


def format_hhmmss(total_seconds):
    """Format a number of seconds (int or float) as HH:MM:SS. Negative values
    (e.g. an Overhead Total that's gone over budget) are shown as -HH:MM:SS."""
    total_seconds = int(round(total_seconds))
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{sign}{hours:02}:{minutes:02}:{seconds:02}"


def parse_hhmmss(text):
    """Reverse of format_hhmmss: 'HH:MM:SS' (optionally '-HH:MM:SS') -> seconds."""
    text = str(text).strip()
    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("-")
    parts = text.split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = (int(p) for p in parts)
    except ValueError:
        return 0
    return sign * (hours * 3600 + minutes * 60 + seconds)
