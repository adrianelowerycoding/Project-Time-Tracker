"""View Day's Data window: one shift's entries, project totals, and Overhead Total."""

import tkinter as tk
from tkinter import ttk

from ..session import DaySummary
from ..timeutils import format_hhmmss
from .theme import BG, FG, FG_MUTED, apply_treeview_theme


class DayDataWindow(tk.Toplevel):
    """View Day's Data: a read-only look at one shift date's entries and
    totals, plus the Overhead Total. Everything shown comes from the
    DaySummary it's given - nothing here touches Excel."""

    def __init__(self, parent, shift_date: str, summary: DaySummary):
        super().__init__(parent)
        self.title(f"Data for Shift Date {shift_date}")
        self.configure(bg=BG)
        self.geometry("560x600")

        apply_treeview_theme(self)

        # -- Section: today's log entries --
        tk.Label(
            self, text="Today's Log", font=("Segoe UI", 11, "bold"), bg=BG, fg=FG
        ).pack(anchor="w", padx=10, pady=(10, 4))

        log_columns = ("project_name", "project_number", "start", "end", "duration")
        log_headers = ("Project Name", "Project Number", "Start", "End", "Duration")

        log_tree = ttk.Treeview(self, columns=log_columns, show="headings", height=8)
        for col, label in zip(log_columns, log_headers):
            log_tree.heading(col, text=label)
            log_tree.column(col, width=100, anchor="center")
        log_tree.pack(fill="x", padx=10)

        if summary.entries:
            for entry in summary.entries:
                log_tree.insert("", "end", values=(
                    entry.project_name, entry.project_number, entry.start, entry.end,
                    format_hhmmss(entry.duration_seconds)
                ))
        else:
            tk.Label(
                self, text="No entries recorded for today yet.",
                bg=BG, fg=FG_MUTED
            ).pack(anchor="w", padx=10, pady=4)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10, pady=12)

        # -- Section: project totals --
        tk.Label(
            self, text="Project Totals", font=("Segoe UI", 11, "bold"), bg=BG, fg=FG
        ).pack(anchor="w", padx=10, pady=(0, 4))

        totals_columns = ("project_name", "project_number", "total", "shift_date")
        totals_headers = ("Project Name", "Project Number", "Total for Shift", "Shift Date")

        totals_tree = ttk.Treeview(self, columns=totals_columns, show="headings", height=6)
        for col, label in zip(totals_columns, totals_headers):
            totals_tree.heading(col, text=label)
            totals_tree.column(col, width=130, anchor="center")
        totals_tree.pack(fill="x", padx=10, pady=(0, 10))

        if summary.totals:
            for total in summary.totals:
                totals_tree.insert("", "end", values=(
                    total.project_name, total.project_number,
                    format_hhmmss(total.seconds), shift_date
                ))
        else:
            tk.Label(
                self, text="No totals to show yet.",
                bg=BG, fg=FG_MUTED
            ).pack(anchor="w", padx=10, pady=4)

        # -- Overhead Total: 8 hours minus everything logged today. Goes negative
        #    (shown as -HH:MM:SS) if today's total already exceeds 8 hours. --
        tk.Label(
            self, text=f"Overhead Total: {format_hhmmss(summary.overhead_seconds)}",
            font=("Segoe UI", 11, "bold"), bg=BG, fg=FG
        ).pack(anchor="w", padx=10, pady=(4, 10))
