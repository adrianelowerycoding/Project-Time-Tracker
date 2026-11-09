"""Tests for SessionLog: turning a stopped timer into a logged entry."""

import datetime

from project_timer.models import LogEntry, Profile, RawEntry
from project_timer.session import SessionLog

UTC = datetime.timezone.utc


def test_logging_an_entry_converts_to_profile_timezone_and_assigns_shift_date():
    """A Vietnam 1st-shift worker stops a timer at 2:15 AM local time.

    Expected values are worked out by hand from the shift schedule, not copied
    from the code's output:

    - 1st shift is 6:00 AM - 2:00 PM Central. On Nov 10, 2026 Central is on
      standard time (UTC-6; clocks changed Nov 1), so the shift runs
      12:00-20:00 UTC. Vietnam is UTC+7 with no DST, so that is
      19:00 on Nov 10 to 03:00 on Nov 11 local time.
    - The timer runs 18:30-19:15:30 UTC = 01:30-02:15:30 AM on Nov 11 in
      Vietnam. That is after local midnight, but still inside the shift that
      began at 19:00 on Nov 10, so the shift date is Nov 10, not Nov 11.
    - 18:30:00 to 19:15:30 is 45 minutes 30 seconds = 2730 seconds.
    """
    raw = RawEntry(
        project_name="Kitchen Remodel",
        project_number="123456",
        start_utc=datetime.datetime(2026, 11, 10, 18, 30, 0, tzinfo=UTC),
        end_utc=datetime.datetime(2026, 11, 10, 19, 15, 30, tzinfo=UTC),
        duration_seconds=2730,
    )
    profile = Profile(shift=1, timezone="Asia/Ho_Chi_Minh")
    session = SessionLog()

    entry = session.add(raw, profile)

    assert entry == LogEntry(
        project_name="Kitchen Remodel",
        project_number="123456",
        start="2026-11-11 01:30:00",
        end="2026-11-11 02:15:30",
        duration_seconds=2730,
        shift=1,
        timezone="Asia/Ho_Chi_Minh",
        shift_date="2026-11-10",
    )
    assert session.entries == [entry]
