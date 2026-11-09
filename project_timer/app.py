"""Application entry point: checks timezone data is installed, then opens the main window."""

import tkinter as tk
from tkinter import messagebox
from zoneinfo import ZoneInfo

from .ui.main_window import MainWindow


def _check_tzdata():
    """Windows doesn't ship an IANA timezone database the way Linux/macOS do,
    so `zoneinfo` needs the 'tzdata' PyPI package to look up zones like
    'America/Chicago'. Fails fast with a clear popup + fix instead of a raw
    traceback if it's missing."""
    try:
        ZoneInfo("UTC")
    except Exception:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            title="Missing Time Zone Data",
            message="This program needs the 'tzdata' package to handle timezones "
                    "correctly (Windows doesn't include it by default).\n\n"
                    "Run this in a terminal, then restart the program:\n\n"
                    "    pip install tzdata"
        )
        root.destroy()
        raise SystemExit(1)


def main():
    _check_tzdata()
    main_window = MainWindow()
    # Begins an event loop, listening for OS-level events and triggering callback functions
    main_window.mainloop()
