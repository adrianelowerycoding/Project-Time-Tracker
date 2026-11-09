"""The in-memory log of everything timed since the last Update Database, plus
the totals math built on top of it. No UI, no files."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from .config import OVERHEAD_BASELINE_SECONDS
from .models import LogEntry, Profile, ProjectTotal, RawEntry
from .timeutils import compute_shift_date

_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def compute_totals(entries: Iterable[LogEntry]) -> list[ProjectTotal]:
    """Sum entries into one row per (shift date, project number).

    Grouping key is (shift_date, project_number) - NOT the calendar date - so
    a 3rd-shift session that starts at 10pm and runs past midnight still lands
    in a single row, dated to the day the shift started on. Each entry already
    carries its own shift_date/shift, baked in when it was created."""
    seconds = defaultdict(int)
    names = {}
    shift = {}
    timezone = {}
    for entry in entries:
        key = (entry.shift_date, entry.project_number)
        seconds[key] += entry.duration_seconds
        names[entry.project_number] = entry.project_name
        shift[key] = entry.shift
        timezone[key] = entry.timezone

    return [
        ProjectTotal(
            project_name=names[number], project_number=number, seconds=secs,
            shift_date=shift_date, shift=shift[(shift_date, number)],
            timezone=timezone[(shift_date, number)],
        )
        for (shift_date, number), secs in seconds.items()
    ]


@dataclass(frozen=True)
class DaySummary:
    """Everything 'View Day's Data' shows for one shift date."""
    entries: list[LogEntry]
    totals: list[ProjectTotal]   # sorted by project name
    overhead_seconds: int        # baseline minus everything logged; negative if over


class SessionLog:
    """Every stop-click auto-fills a new entry here. Update Database commits
    them to the workbook and then clears the log so nothing is saved twice."""

    def __init__(self):
        self._entries: list[LogEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries = []

    def add(self, raw: RawEntry, profile: Profile) -> LogEntry:
        """The ONE place Shift/TimeZone/ShiftDate get resolved and baked into
        an entry, using whatever the profile currently says - so if the
        profile changes later, already-logged entries keep the values they
        were created with instead of silently being reinterpreted."""
        tz = ZoneInfo(profile.timezone)
        start_local = raw.start_utc.astimezone(tz)
        end_local = raw.end_utc.astimezone(tz)

        entry = LogEntry(
            project_name=raw.project_name,
            project_number=raw.project_number,
            start=start_local.strftime(_TIMESTAMP_FORMAT),
            end=end_local.strftime(_TIMESTAMP_FORMAT),
            duration_seconds=raw.duration_seconds,
            shift=profile.shift,
            timezone=profile.timezone,
            # Shift date is anchored to the LOCAL start time - a shift is
            # attributed to the day it started on, even if it runs past midnight.
            shift_date=compute_shift_date(start_local, profile.shift).isoformat(),
        )
        self._entries.append(entry)
        return entry

    def totals(self) -> list[ProjectTotal]:
        return compute_totals(self._entries)

    def day_summary(self, shift_date: str) -> DaySummary:
        """Entries, per-project totals, and Overhead Total for one shift date."""
        todays_entries = [e for e in self._entries if e.shift_date == shift_date]
        totals = sorted(compute_totals(todays_entries), key=lambda t: t.project_name)
        overhead = OVERHEAD_BASELINE_SECONDS - sum(t.seconds for t in totals)
        return DaySummary(entries=todays_entries, totals=totals, overhead_seconds=overhead)
