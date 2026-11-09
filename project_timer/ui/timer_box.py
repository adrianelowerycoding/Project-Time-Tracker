"""TimerBox: the per-project widget with a start/stop button and a live clock."""

import datetime
import tkinter as tk
from tkinter import messagebox

from ..models import RawEntry
from ..timeutils import format_hhmmss
from .theme import ACCENT, BG_ALT, BORDER, DELETE_RED, FG, FG_MUTED, RUNNING


# The timer you create per project
class TimerBox(tk.Frame):
    def __init__(self, parent, project_name, project_number, on_delete, on_log_entry, on_state_change, **kwargs):
        # A slightly bigger frame so it reads as a "medium-sized square" button
        super().__init__(
            parent, bd=1, relief="solid", padx=10, pady=10,
            bg=BG_ALT, highlightbackground=BORDER,
            width=150, height=180, **kwargs
        )
        # Keep the frame from shrinking to fit its children so it stays square-ish
        self.pack_propagate(False)
        self.grid_propagate(False)

        self.project_name = project_name
        self.project_number = project_number
        self.on_delete = on_delete            # callback: on_delete(self)
        self.on_log_entry = on_log_entry      # callback: on_log_entry(raw_entry)
        self.on_state_change = on_state_change  # callback: on_state_change(self, running)

        # -- timer state --
        self.running = False
        self.start_time = None
        self._tick_job = None
        # locked while MainWindow is in "delete mode" so a click can't
        # accidentally start/stop a timer while the user is trying to delete one
        self.locked = False

        # -- "x" delete button, placed in the top-right corner --
        # Hidden by default; MainWindow toggles visibility via show_delete_x()/hide_delete_x()
        self.delete_btn = tk.Button(
            self, text="x", font=("Segoe UI", 8, "bold"),
            bg=DELETE_RED, fg="white", activebackground="#e74c3c", activeforeground="white",
            relief="flat", highlightthickness=0, bd=0,
            width=2, height=1, command=self.confirm_delete
        )
        # place() lets it float in the corner without disturbing the pack layout below

        self.title_label = tk.Label(
            self, text=project_name, font=("Segoe UI", 11, "bold"),
            bg=BG_ALT, fg=FG, wraplength=110, justify="center"
        )
        self.title_label.pack(pady=(0, 2))

        self.number_label = tk.Label(
            self, text=f"#{project_number}", font=("Segoe UI", 8),
            bg=BG_ALT, fg=FG_MUTED
        )
        self.number_label.pack(pady=(0, 4))

        self.canvas = tk.Canvas(self, width=70, height=70, highlightthickness=0, bg=BG_ALT)
        self.canvas.pack()

        self.circle = self.canvas.create_oval(4, 4, 66, 66, fill=ACCENT, outline="")
        self.circle_text = self.canvas.create_text(35, 35, text="Start", fill="white", font=("Segoe UI", 10, "bold"))
        self.canvas.bind("<Button-1>", self.on_toggle_clicked)

        self.time_label = tk.Label(self, text="00:00:00", font=("Consolas", 10), bg=BG_ALT, fg=FG_MUTED)
        self.time_label.pack(pady=(6, 0))

    # -- Start/stop logic --

    def on_toggle_clicked(self, event=None):
        if self.locked:
            return  # ignore clicks while delete mode is active
        if self.running:
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        self.running = True
        # Captured in UTC (timezone-aware) rather than naive local time, so the
        # entry doesn't depend on the machine's OS timezone being set correctly -
        # MainWindow converts it to the user's profile timezone at log time.
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

        self.canvas.itemconfig(self.circle, fill=RUNNING)
        self.canvas.itemconfig(self.circle_text, text="Stop")

        self._tick()
        self.on_state_change(self, True)

    def _tick(self):
        # Called once a second while running, to keep the on-screen clock live
        if not self.running:
            return
        elapsed = datetime.datetime.now(datetime.timezone.utc) - self.start_time
        self.time_label.config(text=self._format_duration(elapsed))
        self._tick_job = self.after(1000, self._tick)

    def stop_timer(self):
        if not self.running:
            return

        self.running = False
        if self._tick_job is not None:
            self.after_cancel(self._tick_job)
            self._tick_job = None

        end_time = datetime.datetime.now(datetime.timezone.utc)
        duration = end_time - self.start_time

        # Reset visuals
        self.canvas.itemconfig(self.circle, fill=ACCENT)
        self.canvas.itemconfig(self.circle_text, text="Start")
        self.time_label.config(text="00:00:00")

        # Raw UTC timestamps only - the SessionLog resolves these against the
        # CURRENT profile (shift + timezone) and bakes in Shift, TimeZone, and
        # ShiftDate once, at the moment the entry is created.
        entry = RawEntry(
            project_name=self.project_name,
            project_number=self.project_number,
            start_utc=self.start_time,
            end_utc=end_time,
            duration_seconds=int(duration.total_seconds()),
        )
        self.start_time = None

        # Hand the finished entry straight up to MainWindow's in-memory session log
        self.on_log_entry(entry)
        self.on_state_change(self, False)

    @staticmethod
    def _format_duration(td):
        return format_hhmmss(td.total_seconds())

    # -- Delete mode / deletion --

    def show_delete_x(self):
        self.locked = True
        # Anchor to the top-right corner of the frame
        self.delete_btn.place(relx=1.0, x=-2, y=2, anchor="ne")

    def hide_delete_x(self):
        self.locked = False
        self.delete_btn.place_forget()

    def confirm_delete(self):
        if self.running:
            messagebox.showwarning(
                title="Timer Running",
                message=f'"{self.project_name}" is currently running. Stop it before deleting.'
            )
            return

        answer = messagebox.askyesno(
            title="Delete Timer",
            message=f'Do you really want to delete "{self.project_name}" (#{self.project_number})\'s timer?'
        )
        if answer:
            self.on_delete(self)
