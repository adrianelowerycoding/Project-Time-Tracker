"""The dark-mode look: palette plus helpers that apply it to Tk/ttk widgets."""

import tkinter as tk
from tkinter import ttk

# -- Dark mode palette: tweak these hex values to taste --
BG = "#1e1e1e"          # main window / frame background
BG_ALT = "#2b2b2b"      # slightly lighter background (boxes, buttons)
FG = "#e0e0e0"          # primary text color
FG_MUTED = "#a0a0a0"    # secondary/less prominent text
ACCENT = "#4CAF50"      # accent color (e.g. idle circle button)
RUNNING = "#c0392b"     # accent color while a timer is running
BORDER = "#3c3c3c"      # borders/separators
DELETE_RED = "#c0392b"  # color for the "x" delete button


def make_button(parent, text, command, **overrides):
    """A flat dark-mode tk.Button. Pass extra Button options (e.g. width=10)
    through `overrides`."""
    options = dict(
        bg=BG_ALT, fg=FG, activebackground=BORDER, activeforeground=FG,
        relief="flat", highlightthickness=0
    )
    options.update(overrides)
    return tk.Button(parent, text=text, command=command, **options)


def apply_app_theme(root):
    """One-time theme setup on the root window."""
    # ttk widgets (just the Separators here) need a Style, since bg/fg
    # kwargs don't work on them directly like they do on plain tk widgets.
    style = ttk.Style(root)
    style.theme_use("clam")  # 'clam' respects custom colors; 'default'/'vista' mostly ignore them
    style.configure("TSeparator", background=BG)

    # A ttk Combobox's dropdown list (the "popdown") is an internal plain
    # Tk Listbox that ttk.Style doesn't reach - it needs the classic Tk
    # option database instead. Without this, the highlighted/selected
    # item renders in light text on a light highlight and is basically
    # unreadable against the dark theme. Applied once here, at the root,
    # so every Combobox in the app (including ones in Toplevels, like
    # Profile) picks it up.
    root.option_add("*TCombobox*Listbox.background", BG_ALT)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", BG)


def apply_combobox_theme(window):
    """Dark styling for the readonly Comboboxes in the Profile window."""
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=BG_ALT, background=BG_ALT, foreground=FG_MUTED)
    # The 'clam' theme maps its own fieldbackground/foreground for the
    # "readonly" state (which is what our Comboboxes use), overriding the
    # configure() call above once a value is selected and focus leaves the
    # box. Explicitly map the readonly state too, or the closed box falls
    # back to a light field with light text.
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG_ALT)],
        foreground=[("readonly", FG_MUTED)],
        selectforeground=[("readonly", FG_MUTED)],
        selectbackground=[("readonly", BG_ALT)],
    )


def apply_treeview_theme(window):
    """Dark styling for the tables in the View Day's Data window."""
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("Treeview", background=BG_ALT, fieldbackground=BG_ALT, foreground=FG)
    style.configure("Treeview.Heading", background=BG, foreground=FG)
