"""Reads and writes the Excel database and its JSON sidecar. No UI; errors are
raised as DatabaseError with a message ready to show the user."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import openpyxl

from .models import LogEntry, ProjectTotal
from .timeutils import format_hhmmss, parse_hhmmss

DAILY_LOG_SHEET = "Daily Log"
TOTALS_SHEET = "Project Totals"
DAILY_LOG_HEADERS = ["Project Name", "Project Number", "Start", "End", "Duration", "Shift", "Time Zone"]
TOTALS_HEADERS = ["Project Name", "Project Number", "Total", "Shift Date", "Shift", "Time Zone"]


class DatabaseError(Exception):
    """Base class. str(error) is a message that's ready to show the user."""


class DatabaseOpenError(DatabaseError):
    """The file couldn't be opened as an Excel workbook at all."""


class DatabaseFormatError(DatabaseError):
    """It's a workbook, but not a Project Tracker one (required tabs missing)."""


class ProjectDatabase:
    """One tracking database: an .xlsx workbook with two static tabs (headers
    only, no formulas) plus a .json sidecar next to it.

    - "Daily Log" holds one row per start/stop entry.
    - "Project Totals" holds one row per project per shift date.
    - The sidecar holds {project_number: project_name} so timer names survive
      a reload. It's just a plain text file next to the workbook - not a
      database engine, still nothing but openpyxl + stdlib. It is a
      convenience, not the source of truth for hours worked.

    The file is named for the project(s) it covers, but every row still
    carries a Project Number column, so the data stays searchable/keyed by
    project number."""

    def __init__(self, path: Path, project_names: dict[str, str] | None = None):
        self.path = Path(path)
        self.project_names: dict[str, str] = dict(project_names or {})

    @property
    def name(self) -> str:
        """Display name, e.g. 'john_Project_Tracker_db_123.xlsx'."""
        return self.path.name

    @property
    def sidecar_path(self) -> Path:
        """Same folder, same filename, '.json' instead of '.xlsx'."""
        return self.path.with_suffix(".json")

    # -- Creating / loading --

    @classmethod
    def create(cls, path: Path) -> ProjectDatabase:
        """Write a fresh workbook (headers only) and an empty sidecar."""
        wb = openpyxl.Workbook()
        ws_log = wb.active
        ws_log.title = DAILY_LOG_SHEET
        ws_log.append(DAILY_LOG_HEADERS)

        ws_totals = wb.create_sheet(TOTALS_SHEET)
        ws_totals.append(TOTALS_HEADERS)

        wb.save(path)

        database = cls(path)
        database.save_project_names()
        return database

    @classmethod
    def load(cls, path: Path) -> ProjectDatabase:
        """Open an existing database. Raises DatabaseError if it isn't one.

        Opens the workbook writable because it also tidies it: older files get
        their missing headers back-filled, and any duplicate (shift date,
        project number) rows left over from prior sessions are combined."""
        path = Path(path)

        try:
            wb = openpyxl.load_workbook(path)
        except Exception as exc:
            raise DatabaseOpenError("That file couldn't be opened as an Excel database.") from exc

        if DAILY_LOG_SHEET not in wb.sheetnames or TOTALS_SHEET not in wb.sheetnames:
            wb.close()
            raise DatabaseFormatError(
                "That file doesn't look like a Project Tracker database "
                '(missing the "Daily Log" / "Project Totals" tabs).'
            )

        # Heal headers on older databases created before the Shift/Time Zone
        # columns existed - the columns already had data once this program
        # started writing to them, just no label in row 1.
        cls._ensure_headers(wb[DAILY_LOG_SHEET], DAILY_LOG_HEADERS)
        cls._ensure_headers(wb[TOTALS_SHEET], TOTALS_HEADERS)
        cls._combine_duplicate_totals(wb[TOTALS_SHEET])

        wb.save(path)
        wb.close()

        return cls(path, project_names=cls._read_sidecar(path.with_suffix(".json")))

    # -- Project names (the JSON sidecar) --

    @staticmethod
    def _read_sidecar(sidecar_path: Path) -> dict[str, str]:
        if sidecar_path.exists():
            try:
                with open(sidecar_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def save_project_names(self) -> None:
        try:
            with open(self.sidecar_path, "w", encoding="utf-8") as f:
                json.dump(self.project_names, f, indent=2, sort_keys=True)
        except OSError:
            pass  # sidecar is a convenience file, not the source of truth for hours worked

    def add_project(self, project_number: str, project_name: str) -> None:
        """Keep the sidecar's name mapping current."""
        self.project_names[project_number] = project_name
        self.save_project_names()

    # -- Updating --

    def append_session(self, entries: Sequence[LogEntry], totals: Sequence[ProjectTotal]) -> None:
        """The only place an existing workbook gets new data. Appends `entries`
        as static rows to "Daily Log". For "Project Totals", a row for the same
        (shift date, project number) gets its total added to rather than
        duplicated - so saving more than once for the same project on the same
        shift day still yields one row."""
        wb = openpyxl.load_workbook(self.path)

        # Heal headers on older databases created before the Shift/Time Zone
        # columns existed.
        self._ensure_headers(wb[DAILY_LOG_SHEET], DAILY_LOG_HEADERS)
        self._ensure_headers(wb[TOTALS_SHEET], TOTALS_HEADERS)

        ws_log = wb[DAILY_LOG_SHEET]
        for entry in entries:
            ws_log.append([
                entry.project_name, entry.project_number, entry.start, entry.end,
                format_hhmmss(entry.duration_seconds), entry.shift, entry.timezone
            ])

        ws_totals = wb[TOTALS_SHEET]

        # Look up any row that already exists for (shift date, project number),
        # so a second save for the same project on the same shift day adds to
        # it instead of creating a duplicate row.
        existing_rows = {}
        for row_idx, row in enumerate(ws_totals.iter_rows(min_row=2, values_only=True), start=2):
            if not row or row[1] is None:
                continue
            _, existing_number, _, existing_shift_date = row[:4]
            existing_rows[(existing_shift_date, existing_number)] = row_idx

        for total in totals:
            key = (total.shift_date, total.project_number)
            if key in existing_rows:
                row_idx = existing_rows[key]
                previous_total = ws_totals.cell(row=row_idx, column=3).value
                combined_seconds = parse_hhmmss(previous_total) + total.seconds
                ws_totals.cell(row=row_idx, column=3, value=format_hhmmss(combined_seconds))
                if not ws_totals.cell(row=row_idx, column=1).value:
                    ws_totals.cell(row=row_idx, column=1, value=total.project_name)
                if not ws_totals.cell(row=row_idx, column=5).value:
                    ws_totals.cell(row=row_idx, column=5, value=total.shift)
                if not ws_totals.cell(row=row_idx, column=6).value:
                    ws_totals.cell(row=row_idx, column=6, value=total.timezone)
            else:
                ws_totals.append([
                    total.project_name, total.project_number, format_hhmmss(total.seconds),
                    total.shift_date, total.shift, total.timezone
                ])

        wb.save(self.path)

    # -- Worksheet helpers --

    @staticmethod
    def _ensure_headers(ws, expected_headers):
        """Backfill any missing header cells in row 1 against `expected_headers`.
        Databases created before the Shift/Time Zone columns existed already
        have data written into those columns (since column position is fixed
        by list order), just no header label - this patches the label in
        without touching any existing data."""
        for col_idx, header in enumerate(expected_headers, start=1):
            if not ws.cell(row=1, column=col_idx).value:
                ws.cell(row=1, column=col_idx, value=header)

    @staticmethod
    def _combine_duplicate_totals(ws_totals):
        """Combine duplicate (shift date, project number) rows into one summed row."""
        combined = {}  # (shift_date, project_number) -> {"name": ..., "seconds": ..., "shift": ..., "timezone": ...}
        for row in ws_totals.iter_rows(min_row=2, values_only=True):
            if not row or row[1] is None:
                continue
            # Pad to 6 columns so older files (saved before the Shift/Time
            # Zone columns existed) still load without crashing.
            project_name, project_number, total_str, shift_date_str, shift_value, timezone_value = (list(row) + [None] * 6)[:6]
            key = (shift_date_str, project_number)
            seconds = parse_hhmmss(total_str)
            if key in combined:
                combined[key]["seconds"] += seconds
                if not combined[key]["name"] and project_name:
                    combined[key]["name"] = project_name
                if not combined[key]["shift"] and shift_value:
                    combined[key]["shift"] = shift_value
                if not combined[key]["timezone"] and timezone_value:
                    combined[key]["timezone"] = timezone_value
            else:
                combined[key] = {"name": project_name, "seconds": seconds, "shift": shift_value, "timezone": timezone_value}

        if ws_totals.max_row > 1:
            ws_totals.delete_rows(2, ws_totals.max_row - 1)
        for (shift_date_str, project_number), data in sorted(combined.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "")):
            ws_totals.append([
                data["name"], project_number, format_hhmmss(data["seconds"]), shift_date_str,
                data["shift"], data["timezone"]
            ])
