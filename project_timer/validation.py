"""Turning raw text typed into dialogs into validated values. Pure functions -
the UI decides how to show an error, this decides whether there is one."""

from __future__ import annotations

import re
from collections.abc import Iterable


class ProjectInputError(ValueError):
    """Bad 'Name, Project Number' input. Carries the dialog title and message
    the UI should show."""

    def __init__(self, title: str, message: str):
        super().__init__(message)
        self.title = title
        self.message = message


def sanitize_for_filename(text: str) -> str:
    """Strip characters Windows doesn't allow in filenames."""
    return re.sub(r'[<>:"/\\|?*]', "", text)


def database_name_from_input(text: str) -> str:
    """Commas become underscores, spaces are dropped entirely, then characters
    Windows doesn't allow in filenames are stripped. May return '' if nothing
    usable is left."""
    return sanitize_for_filename(text.replace(",", "_").replace(" ", ""))


def parse_project_input(user_input: str, existing_numbers: Iterable[str]) -> tuple[str, str]:
    """Parse 'Name, Project Number' into (name, number). The project number
    must be at least 6 digits, since it's the identifier the JSON sidecar and
    Excel both key off of, and must not already have a timer.

    Raises ProjectInputError (with the title/message to show) on bad input.
    The caller is expected to have already dealt with cancelled/blank input."""
    if "," not in user_input:
        raise ProjectInputError(
            "Invalid Format",
            "Please enter using the format: Name, Project Number\n"
            "e.g. Kitchen Remodel, 123456",
        )

    name_part, _, number_part = user_input.partition(",")
    project_name = name_part.strip()
    project_number = number_part.strip().replace(" ", "")

    if not project_name:
        raise ProjectInputError(
            "Invalid Format",
            "Please include a project name before the comma.",
        )

    if not project_number.isdigit() or len(project_number) < 6:
        raise ProjectInputError(
            "Invalid Project Number",
            "Project number must be at least 6 digits (numbers only).",
        )

    if project_number in set(existing_numbers):
        raise ProjectInputError(
            "Duplicate Project Number",
            f"A timer for project number {project_number} already exists.",
        )

    return project_name, project_number
