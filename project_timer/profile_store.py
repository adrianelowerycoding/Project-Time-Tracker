"""Saving/loading the user's Profile (shift + timezone) to profile.json."""

from __future__ import annotations

import json
from pathlib import Path

from .config import tracker_folder
from .models import Profile


class ProfileStore:
    """Profile settings live in their own JSON file, independent of whichever
    database is loaded - a person's shift/timezone doesn't change based on
    which project they're tracking."""

    FILENAME = "profile.json"

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else tracker_folder() / self.FILENAME

    def load(self) -> Profile:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "shift" in data and "timezone" in data:
                    return Profile(shift=data["shift"], timezone=data["timezone"])
            except (OSError, json.JSONDecodeError):
                pass
        # Sane defaults until the user sets their own via Options > Profile
        return Profile()

    def save(self, profile: Profile) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=2, sort_keys=True)
        except OSError:
            pass  # profile is a convenience file; app still runs fine without it persisting
