"""Options > Profile window for choosing a shift and timezone."""

import tkinter as tk
from tkinter import ttk

from ..config import SHIFT_LABELS, TIMEZONE_OPTIONS
from ..models import Profile
from .theme import BG, FG, apply_combobox_theme, make_button


class ProfileDialog(tk.Toplevel):
    """Options > Profile: pick a shift and a timezone. Calls
    `on_save(new_profile)` when the user presses Save; Cancel just closes."""

    def __init__(self, parent, profile, on_save):
        super().__init__(parent)
        self._on_save = on_save

        self.title("Profile")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # small modal-style window

        apply_combobox_theme(self)

        current_shift_label = SHIFT_LABELS[profile.shift - 1]
        tz_labels = list(TIMEZONE_OPTIONS.keys())
        current_tz_label = next(
            (label for label, value in TIMEZONE_OPTIONS.items() if value == profile.timezone),
            tz_labels[0]
        )

        # -- Status titles: show exactly what's currently selected, updated
        #    live as the dropdowns change, so it's never ambiguous what's
        #    about to be saved. --
        shift_status_var = tk.StringVar(value=f"Shift: {current_shift_label}")
        tz_status_var = tk.StringVar(value=f"Timezone: {current_tz_label}")

        tk.Label(
            self, textvariable=shift_status_var, font=("Segoe UI", 10, "bold"), bg=BG, fg=FG
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(14, 2))

        self._shift_var = tk.StringVar(value=current_shift_label)
        shift_box = ttk.Combobox(
            self, textvariable=self._shift_var, values=SHIFT_LABELS,
            state="readonly", width=24
        )
        shift_box.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))
        shift_box.bind("<<ComboboxSelected>>", lambda e: shift_status_var.set(f"Shift: {self._shift_var.get()}"))

        tk.Label(
            self, textvariable=tz_status_var, font=("Segoe UI", 10, "bold"), bg=BG, fg=FG
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 2))

        self._tz_var = tk.StringVar(value=current_tz_label)
        tz_box = ttk.Combobox(
            self, textvariable=self._tz_var, values=tz_labels,
            state="readonly", width=34
        )
        tz_box.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))
        tz_box.bind("<<ComboboxSelected>>", lambda e: tz_status_var.set(f"Timezone: {self._tz_var.get()}"))

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(10, 14))

        make_button(btn_frame, "Save", self._save_and_close, width=10).pack(side="left", padx=6)
        make_button(btn_frame, "Cancel", self.destroy, width=10).pack(side="left", padx=6)

        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")

    def _save_and_close(self):
        self._on_save(Profile(
            shift=SHIFT_LABELS.index(self._shift_var.get()) + 1,
            timezone=TIMEZONE_OPTIONS[self._tz_var.get()],
        ))
        self.destroy()
