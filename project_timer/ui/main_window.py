"""The main window: connects the buttons and timers to the database, session, and profile logic."""

import os
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter import filedialog, simpledialog, messagebox

from ..config import tracker_folder
from ..database import DatabaseError, ProjectDatabase
from ..profile_store import ProfileStore
from ..session import SessionLog
from ..timeutils import current_shift_date
from ..validation import ProjectInputError, database_name_from_input, parse_project_input
from .day_view import DayDataWindow
from .profile_dialog import ProfileDialog
from .theme import BG, BG_ALT, BORDER, FG, FG_MUTED, apply_app_theme, make_button
from .timer_box import TimerBox


# The main window. It only wires the UI to the logic layers:
#   ProjectDatabase (Excel + sidecar files), SessionLog (the day's entries),
#   ProfileStore (profile.json). No file formats or totals math live in here.
class MainWindow(tk.Tk):

    COLUMNS = 3

    # __init__ gets called as soon as mainWindow() object is called
    def __init__(self):
        super().__init__()
        self.title("Project Time Tracker")
        self.geometry("800x500")
        self.minsize(550, 325) #x, y
        self.configure(bg=BG)

        # The loaded database (None until one is created/loaded). It also owns
        # the project_number -> project_name mapping that's mirrored to a JSON
        # sidecar next to the .xlsx so Load Database can rebuild named timers.
        self.database = None
        self.current_database_name = tk.StringVar(value="Current Database: None")  # Initial text

        # In-memory data for the day. Every stop-click auto-fills a new entry here.
        self.session = SessionLog()

        # Profile settings (Shift + Timezone) for whoever is running this instance.
        # Lives in its own JSON file, independent of whichever database is loaded -
        # a person's shift/timezone doesn't change based on which project they're
        # tracking. Loaded once here; edited via Options > Profile.
        self.profile_store = ProfileStore()
        self.profile = self.profile_store.load()

        apply_app_theme(self)

        # Keeps track of every TimerBox currently on screen
        self.timers = []
        # Whether the "x" delete buttons are currently showing on the timers
        self.delete_mode = False

        # Runs every single function inside mainWindow()
        # Creates the buttons and registers their references/callbacks
        self._build_section1()
        self._build_section2()
        self._build_title_bar()
        self._build_section3()

        # No database loaded yet - Create/Delete Timer start greyed out
        self._refresh_timer_controls()

        # Catch the window's own close button ("X") so we can warn about unsaved work
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # -- SECTION 1: Create Database / Load Database / View Day's Data / Update Database / Options --
    # Creates the button(s) and hands Tkinter a reference to run logic once the button is pressed
    def _build_section1(self):
        frame = tk.Frame(self, pady=10, bg=BG)
        frame.pack(fill="x", padx=10)

        # Each button is kept as an attribute so we can disable it during delete mode
        self.create_db_btn = make_button(frame, "Create Database", self.on_create_database)
        self.create_db_btn.pack(side="left", padx=(0, 10))

        self.load_db_btn = make_button(frame, "Load Database", self.on_load_database)
        self.load_db_btn.pack(side="left", padx=(0, 10))

        self.view_days_btn = make_button(frame, "View Day's Data", self.on_view_days_data)
        self.view_days_btn.pack(side="left", padx=(0, 10))

        self.update_db_btn = make_button(frame, "Update Database", self.on_update_database)
        self.update_db_btn.pack(side="left")

        # -- Options dropdown: currently just "Profile", room to grow later --
        options_mb = tk.Menubutton(
            frame, text="Options", bg=BG_ALT, fg=FG,
            activebackground=BORDER, activeforeground=FG,
            relief="flat", highlightthickness=0
        )
        options_menu = tk.Menu(
            options_mb, tearoff=0, bg=BG_ALT, fg=FG,
            activebackground=BORDER, activeforeground=FG
        )
        options_menu.add_command(label="Profile", command=self.on_open_profile)
        options_mb.config(menu=options_menu)
        options_mb.pack(side="left", padx=(10, 0))
        self.options_mb = options_mb  # kept so we can disable it during delete mode / running timers

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=5, pady=(0, 5))

    # -- SECTION 2: Create/Delete timer buttons --
    def _build_section2(self):
        frame = tk.Frame(self, pady=5, bg=BG)
        frame.pack(fill="x", padx=10)

        self.create_timer_btn = make_button(frame, "Create Project Timer", self.on_create_project_timer)
        self.create_timer_btn.pack(side="left", padx=(0, 10))

        # Keep a reference to this button so we can re-label it Done/Delete Timer
        self.delete_timer_btn = make_button(frame, "Delete Timer", self.on_delete_timer)
        self.delete_timer_btn.pack(side="left")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=5, pady=(5, 5))

    # -- Dynamic title bar: shows current database name --
    def _build_title_bar(self):
        label = tk.Label(
            self, textvariable=self.current_database_name,
            font=("Segoe UI", 9, "italic"), bg=BG, fg=FG_MUTED
        )
        label.pack(fill="x", padx=10, pady=(0, 5))

    # -- SECTION 3: Scrollable box of timer widgets --
    def _build_section3(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(outer, highlightthickness=0, bg=BG)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.timers_container = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.timers_container, anchor="nw")

        self.timers_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

    # -- Callback stubs --
    # All of the logic behind the buttons live in these callback functions

    # -- Unsaved-work guard, shared by the window close button, Create Database,
    #    and Load Database. Returns True if it's OK to proceed (nothing unsaved,
    #    or the user confirmed they're fine discarding it). --
    def _confirm_discard_if_unsaved(self):
        if not self.session:
            return True
        if self.database:
            message = f"Are you sure you want to exit without saving {self.database.name}?"
        else:
            message = "Are you sure you want to exit without saving your current time entries?"
        return messagebox.askyesno(title="Unsaved Changes", message=message)

    # -- Called when the window's own close button ("X") is clicked --
    def on_close(self):
        if self._confirm_discard_if_unsaved():
            self.destroy()

    # -- Wipes the current timers/session so a new or freshly loaded database
    #    starts from a clean slate. (The old database object, and the name
    #    mapping it owns, is simply replaced by the caller.) --
    def _clear_workspace(self):
        if self.delete_mode:
            self.on_delete_timer()  # exit delete mode cleanly first
        for timer in list(self.timers):
            timer.destroy()
        self.timers = []
        self.session.clear()

    # -- Makes `database` the current one and shows its name in the title bar --
    def _set_database(self, database):
        self.database = database
        self.set_current_database(database.name)
        self._refresh_timer_controls()

    # -- Create Project Timer / Delete Timer only make sense once a database is
    #    loaded (that's what the sidecar writes get attached to). Grey them out
    #    otherwise. --
    def _refresh_timer_controls(self):
        state = tk.NORMAL if self.database else tk.DISABLED
        self.create_timer_btn.config(state=state)
        self.delete_timer_btn.config(state=state)

    # -- Profile: shift + timezone for whoever is running this instance --

    def on_open_profile(self):
        ProfileDialog(self, self.profile, on_save=self._on_profile_saved)

    def _on_profile_saved(self, profile):
        self.profile = profile
        self.profile_store.save(profile)

    # User creates database
    def on_create_database(self):

        # Switching databases while one's already loaded - make sure nothing
        # unsaved gets silently thrown away first
        if self.database and not self._confirm_discard_if_unsaved():
            return

        # User names this database after the project(s) it covers. Individual
        # project numbers are still attached per-timer via Create Project Timer -
        # this input just builds the file/folder name.
        user_input_project_names = simpledialog.askstring(
            title="Input Project Names",
            prompt="Input name of your database\nSuggested format 'Project1_Project2_Project3`")

        if user_input_project_names is None:
            return  # Cancelled - stop here, don't open save dialog
        if user_input_project_names.strip() == "":
            return  # Input was blank - re-prompt instead of just quitting

        db_name = database_name_from_input(user_input_project_names)
        if not db_name:
            messagebox.showerror(
                title="Invalid Name",
                message="Please enter a database name"
            )
            return

        # Captures username and sets path for suggested_folder and creates it
        username = os.environ.get("USERNAME", "user")  # Captures Window's username
        suggested_folder = tracker_folder() / f"db {db_name}"
        suggested_folder.mkdir(parents=True, exist_ok=True)  # creates folder

        # Opens File Explorer into created folder and offers save options
        filepath = filedialog.asksaveasfilename(
            title="Choose location for your Time Tracking database",
            initialdir=suggested_folder,
            initialfile=f"{username}_Project_Tracker_db_{db_name}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel file", "*.xlsx")]
        )

        if not filepath:
            return

        database = ProjectDatabase.create(Path(filepath))

        # New database means a clean slate - old timers/session don't carry over
        self._clear_workspace()
        self._set_database(database)

    # Updates the "Curent Database: <database>" title. Showcases name in Title
    def set_current_database(self, name):
        self.current_database_name.set(f"Current Database: {name}")

    # User loads a previously created database to pick up where they left off.
    # Real names/numbers come from the JSON sidecar file saved next to the workbook -
    # the filename itself is just a human-readable label now, not an encoding of
    # project numbers, so there's no filename to fall back on parsing anymore.
    def on_load_database(self):
        # Switching databases while one's already loaded - make sure nothing
        # unsaved gets silently thrown away first
        if self.database and not self._confirm_discard_if_unsaved():
            return

        filepath = filedialog.askopenfilename(
            title="Select a Project Tracker database",
            initialdir=tracker_folder(),
            filetypes=[("Excel file", "*.xlsx")]
        )

        if not filepath:
            return

        try:
            database = ProjectDatabase.load(Path(filepath))
        except DatabaseError as error:
            messagebox.showerror(title="Load Database", message=str(error))
            return

        # Clear out the current workspace - old database's timers/session don't carry over
        self._clear_workspace()

        # Recreate one timer per project number/name pair
        for number, name in database.project_names.items():
            self._add_timer(name, number)
        self._relayout_timers()

        self._set_database(database)

        if not database.project_names:
            messagebox.showinfo(
                title="Load Database",
                message="Database loaded, but no name file (.json) was found next to "
                        "it, so no timers could be rebuilt. Use Create Project Timer "
                        "to add them manually - a name file will be created from there."
            )

    # -- "Update Database": the only place Excel gets touched. Hands the day's
    #    in-memory session entries (and their per-project totals) to the database
    #    to be appended. --
    def on_update_database(self):
        if not self.database:
            messagebox.showwarning(
                title="No Database",
                message="Please create a database first (Create Database)."
            )
            return

        if not self.session:
            messagebox.showinfo(
                title="Update Database",
                message="No new time entries to save yet."
            )
            return

        entries = self.session.entries
        self.database.append_session(entries, self.session.totals())

        messagebox.showinfo(
            title="Update Database",
            message=f"Saved {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} to the database."
        )

        # Committed to the archive - clear the in-memory session so it isn't saved twice
        self.session.clear()

    # -- "View Day's Data": read-only look at today's entries, pulled straight from
    #    the in-memory session (auto-filled on every stop-click). Update Database
    #    plays no part in this - nothing here touches Excel. --
    def on_view_days_data(self):
        # "Today" here means the CURRENT shift date under the active profile,
        # not the literal calendar date - so a 3rd-shift worker checking this
        # at 2am still sees the shift they're in the middle of, not an empty
        # "today" with last night's entries missing.
        shift_date = current_shift_date(self.profile.timezone, self.profile.shift).isoformat()
        DayDataWindow(self, shift_date, self.session.day_summary(shift_date))

    # -- Creates a new TimerBox. Input format is "Name, Project Number" - the
    #    project number must be at least 6 digits, since it's the identifier the
    #    JSON sidecar and Excel both key off of. --
    def on_create_project_timer(self):
        user_input = simpledialog.askstring(
            title="New Project Timer",
            prompt="Enter as: Name, Project Number\n"
                   "(project number must be at least 6 digits)\n"
                   "e.g. Kitchen Remodel, 123456"
        )

        if user_input is None:
            return  # Cancelled
        if user_input.strip() == "":
            return  # Blank input, ignore

        try:
            project_name, project_number = parse_project_input(
                user_input, [t.project_number for t in self.timers]
            )
        except ProjectInputError as error:
            messagebox.showerror(title=error.title, message=error.message)
            return

        self._add_timer(project_name, project_number)
        self._relayout_timers()

        # Keep the sidecar's name mapping current
        self.database.add_project(project_number, project_name)

    # -- Builds a TimerBox wired up to this window's callbacks and tracks it --
    def _add_timer(self, project_name, project_number):
        timer = TimerBox(
            self.timers_container, project_name, project_number,
            on_delete=self.remove_timer,
            on_log_entry=self.add_log_entry,
            on_state_change=self.handle_timer_state_change
        )
        self.timers.append(timer)

    # -- Called by a TimerBox every time a stop-click produces a finished entry.
    #    This is the auto-fill: the session updates the instant a timer is stopped. --
    def add_log_entry(self, raw_entry):
        self.session.add(raw_entry, self.profile)

    # -- Called by a TimerBox the instant it starts or stops. While any timer is
    #    running, every other button in every section is disabled, and every other
    #    timer is locked - only the running timer's own "Stop" stays clickable. --
    def handle_timer_state_change(self, active_timer, running):
        if running:
            self._lock_everything_except(active_timer)
        else:
            # Only unlock once nothing else is still running
            if not any(t.running for t in self.timers):
                self._unlock_everything()

    def _lock_everything_except(self, active_timer):
        for btn in (
            self.create_db_btn, self.load_db_btn, self.view_days_btn,
            self.update_db_btn, self.options_mb, self.create_timer_btn, self.delete_timer_btn
        ):
            btn.config(state=tk.DISABLED)

        for timer in self.timers:
            if timer is not active_timer:
                timer.locked = True

    def _unlock_everything(self):
        # Respect delete mode's own lock if it's somehow still active
        if not self.delete_mode:
            for btn in (self.create_db_btn, self.load_db_btn, self.view_days_btn, self.update_db_btn, self.options_mb):
                btn.config(state=tk.NORMAL)
            self._refresh_timer_controls()  # Create/Delete Timer respect the "database loaded?" rule too
            for timer in self.timers:
                timer.locked = False

    # -- Toggles delete mode: shows/hides the "x" on every timer box, and disables
    #    every other button so "Done Deleting" is the only way out --
    def on_delete_timer(self):
        self.delete_mode = not self.delete_mode

        for timer in self.timers:
            if self.delete_mode:
                timer.show_delete_x()
            else:
                timer.hide_delete_x()

        # Stored as 'self' attributes so now reachable from 'on_delete_timer()'
        other_state = tk.DISABLED if self.delete_mode else tk.NORMAL
        self.create_db_btn.config(state=other_state)
        self.load_db_btn.config(state=other_state)
        self.view_days_btn.config(state=other_state)
        self.create_timer_btn.config(state=other_state)
        self.update_db_btn.config(state=other_state)
        self.options_mb.config(state=other_state)

        self.delete_timer_btn.config(text="Done Deleting" if self.delete_mode else "Delete Timer")

    # -- Called by a TimerBox once the user confirms deletion --
    def remove_timer(self, timer):
        if timer in self.timers:
            self.timers.remove(timer)
        timer.destroy()
        self._relayout_timers()

    # -- Arranges all current TimerBoxes into a grid inside timers_container --
    def _relayout_timers(self):
        for widget in self.timers_container.winfo_children():
            widget.grid_forget()

        for index, timer in enumerate(self.timers):
            row = index // self.COLUMNS
            col = index % self.COLUMNS
            timer.grid(row=row, column=col, padx=8, pady=8)
