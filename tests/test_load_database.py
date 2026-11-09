"""Tests for loading a database: tidying the workbook and restoring project names."""

import json

import openpyxl

from project_timer.database import ProjectDatabase


def _rows(path, sheet_name):
    """Every row of one sheet as a list of lists, read straight from the file."""
    wb = openpyxl.load_workbook(path)
    rows = [list(row) for row in wb[sheet_name].iter_rows(values_only=True)]
    wb.close()
    return rows


def test_loading_a_database_tidies_the_workbook_and_restores_project_names(tmp_path):
    """Loading an older database merges duplicate totals, fills in the missing
    Shift / Time Zone headers, leaves existing data alone, and rebuilds the
    project names from the JSON file saved next to the workbook.

    The workbook is built by hand in the older format (no Shift / Time Zone
    columns), with Kitchen Remodel saved twice for the Nov 9 shift:
        1 h 15 min + 30 min = 1 h 45 min  ->  01:45:00
    """
    path = tmp_path / "tester_Project_Tracker_db_Kitchen_Bath.xlsx"

    wb = openpyxl.Workbook()
    daily_log = wb.active
    daily_log.title = "Daily Log"
    daily_log.append(["Project Name", "Project Number", "Start", "End", "Duration"])
    daily_log.append(["Kitchen Remodel", "123456", "2026-11-09 08:00:00", "2026-11-09 09:15:00", "01:15:00"])
    totals = wb.create_sheet("Project Totals")
    totals.append(["Project Name", "Project Number", "Total", "Shift Date"])
    totals.append(["Kitchen Remodel", "123456", "01:15:00", "2026-11-09"])
    totals.append(["Bath", "654321", "01:00:00", "2026-11-09"])
    totals.append(["Kitchen Remodel", "123456", "00:20:00", "2026-11-10"])
    totals.append(["Kitchen Remodel", "123456", "00:30:00", "2026-11-09"])  # same shift + project as row 1
    wb.save(path)
    path.with_suffix(".json").write_text(
        json.dumps({"123456": "Kitchen Remodel", "654321": "Bath"}), encoding="utf-8"
    )

    database = ProjectDatabase.load(path)

    # Names come back from the JSON file
    assert database.project_names == {"123456": "Kitchen Remodel", "654321": "Bath"}

    # Missing headers were filled in
    assert _rows(path, "Daily Log")[0] == [
        "Project Name", "Project Number", "Start", "End", "Duration", "Shift", "Time Zone"
    ]
    assert _rows(path, "Project Totals")[0] == [
        "Project Name", "Project Number", "Total", "Shift Date", "Shift", "Time Zone"
    ]

    # The duplicate Nov 9 Kitchen Remodel rows were combined into one
    assert [row[:4] for row in _rows(path, "Project Totals")[1:]] == [
        ["Kitchen Remodel", "123456", "01:45:00", "2026-11-09"],
        ["Bath", "654321", "01:00:00", "2026-11-09"],
        ["Kitchen Remodel", "123456", "00:20:00", "2026-11-10"],
    ]

    # Existing log data was not touched
    assert _rows(path, "Daily Log")[1][:5] == [
        "Kitchen Remodel", "123456", "2026-11-09 08:00:00", "2026-11-09 09:15:00", "01:15:00"
    ]
