"""Static configuration: the company shift schedule, the timezone choices, and
where files live on disk. Nothing in here touches the UI."""

import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

# -- Profile options: shift labels shown in the dropdown, and the timezone
#    labels mapped to their real IANA zone names. IANA names (not raw UTC
#    offsets) so DST is handled automatically for the US-based folks, while
#    Vietnam (which doesn't observe DST) stays correct year-round. --
SHIFT_LABELS = ["1st Shift", "2nd Shift", "3rd Shift"]
TIMEZONE_OPTIONS = {
    "Eastern - New Jersey (America/New_York)": "America/New_York",
    "Central - Arkansas (America/Chicago)": "America/Chicago",
    "Vietnam (Asia/Ho_Chi_Minh)": "Asia/Ho_Chi_Minh",
}

# Used until the user picks their own via Options > Profile
DEFAULT_SHIFT = 1
DEFAULT_TIMEZONE = "America/New_York"

# -- Shift windows are anchored to a single reference timezone - Central Time,
#    Arkansas (headquarters) - since that's how the shift schedule is
#    actually defined company-wide, not something each site invents locally.
#    A worker elsewhere experiences a DIFFERENT local clock window for the
#    same shift - e.g. 3rd shift's 10pm-7am Central lands in the middle of
#    the afternoon/evening in Vietnam - so these hours get converted
#    per-person with real zoneinfo math (not a fixed hour offset), which
#    stays correct across DST changes even though Vietnam doesn't observe
#    DST at all. --
CENTRAL_TZ = ZoneInfo("America/Chicago")
SHIFT_WINDOWS_CENTRAL = {
    1: (datetime.time(6, 0), datetime.time(14, 0)),   # 1st shift: 6:00 AM - 2:00 PM Central
    2: (datetime.time(14, 0), datetime.time(23, 0)),  # 2nd shift: 2:00 PM - 11:00 PM Central
    3: (datetime.time(22, 0), datetime.time(7, 0)),   # 3rd shift: 10:00 PM - 7:00 AM Central
}

# Overhead Total = this much time minus everything logged for the shift
OVERHEAD_BASELINE_SECONDS = 8 * 3600


def tracker_folder() -> Path:
    """The folder everything lives under: <user profile>/Documents/Project Tracker.
    Created on first use. Holds profile.json and the per-database folders."""
    folder = Path(os.environ.get("USERPROFILE", r"C:\Users\Default")) / "Documents" / "Project Tracker"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
