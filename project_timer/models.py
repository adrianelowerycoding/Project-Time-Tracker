"""Plain data containers shared between the logic layers and the UI."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from .config import DEFAULT_SHIFT, DEFAULT_TIMEZONE


@dataclass(frozen=True)
class Profile:
    """Shift + timezone for whoever is running this instance."""
    shift: int = DEFAULT_SHIFT
    timezone: str = DEFAULT_TIMEZONE

    def to_dict(self) -> dict:
        return {"shift": self.shift, "timezone": self.timezone}


@dataclass(frozen=True)
class RawEntry:
    """What a TimerBox hands up the instant it's stopped: raw UTC timestamps
    only. The current Profile is applied later, when the entry joins the
    SessionLog, so Shift/TimeZone/ShiftDate get baked in exactly once."""
    project_name: str
    project_number: str
    start_utc: datetime.datetime
    end_utc: datetime.datetime
    duration_seconds: int


@dataclass(frozen=True)
class LogEntry:
    """One finished start/stop entry with the Profile already applied.
    `start`/`end` are 'YYYY-MM-DD HH:MM:SS' in the profile's timezone;
    `shift_date` is an ISO date string."""
    project_name: str
    project_number: str
    start: str
    end: str
    duration_seconds: int
    shift: int
    timezone: str
    shift_date: str


@dataclass(frozen=True)
class ProjectTotal:
    """Total seconds for one project on one shift date - one row of the
    'Project Totals' tab."""
    project_name: str
    project_number: str
    seconds: int
    shift_date: str
    shift: int
    timezone: str
