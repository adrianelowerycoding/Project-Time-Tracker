"""Tests for project totals: summing logged entries per project per shift date."""

import datetime

from project_timer.models import Profile, ProjectTotal, RawEntry
from project_timer.session import SessionLog

UTC = datetime.timezone.utc


def _raw_entry(name, number, start_utc, minutes):
    """A stopped timer that ran for `minutes` starting at `start_utc`."""
    return RawEntry(
        project_name=name,
        project_number=number,
        start_utc=start_utc,
        end_utc=start_utc + datetime.timedelta(minutes=minutes),
        duration_seconds=minutes * 60,
    )


def test_project_totals_group_by_shift_date_not_calendar_date():
    """A 3rd-shift worker's time after midnight counts toward the shift that
    started the evening before, and each project is summed once per shift.

    Expected values are worked out by hand. 3rd shift is 10 PM - 7 AM Central,
    and the worker is on Central time (UTC-6 on these dates, after the Nov 1
    clock change). Times below are Central; the UTC value is what the timer
    actually records.

    Shift of Nov 9 (10 PM Nov 9 - 7 AM Nov 10):
      - Kitchen Remodel  10:30 PM Nov 9 (04:30 UTC)  30 min
      - Kitchen Remodel  12:15 AM Nov 10 (06:15 UTC) 45 min   <- past midnight, same shift
      - Bath              2:00 AM Nov 10 (08:00 UTC) 60 min   <- past midnight, same shift
    Shift of Nov 10:
      - Kitchen Remodel  11:00 PM Nov 10 (05:00 UTC Nov 11) 20 min

    So Kitchen Remodel is 30 + 45 = 75 min on Nov 9 and 20 min on Nov 10;
    Bath is 60 min on Nov 9. Grouping by calendar date would wrongly split the
    Nov 9 shift across two days.
    """
    session = SessionLog()
    profile = Profile(shift=3, timezone="America/Chicago")
    for raw in [
        _raw_entry("Kitchen Remodel", "123456", datetime.datetime(2026, 11, 10, 4, 30, tzinfo=UTC), 30),
        _raw_entry("Kitchen Remodel", "123456", datetime.datetime(2026, 11, 10, 6, 15, tzinfo=UTC), 45),
        _raw_entry("Bath", "654321", datetime.datetime(2026, 11, 10, 8, 0, tzinfo=UTC), 60),
        _raw_entry("Kitchen Remodel", "123456", datetime.datetime(2026, 11, 11, 5, 0, tzinfo=UTC), 20),
    ]:
        session.add(raw, profile)

    totals = sorted(session.totals(), key=lambda t: (t.shift_date, t.project_number))

    assert totals == [
        ProjectTotal("Kitchen Remodel", "123456", seconds=75 * 60, shift_date="2026-11-09",
                     shift=3, timezone="America/Chicago"),
        ProjectTotal("Bath", "654321", seconds=60 * 60, shift_date="2026-11-09",
                     shift=3, timezone="America/Chicago"),
        ProjectTotal("Kitchen Remodel", "123456", seconds=20 * 60, shift_date="2026-11-10",
                     shift=3, timezone="America/Chicago"),
    ]
