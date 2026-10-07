"""The window to edit the settings and generate the PDFs.

Started by main.py. It knows nothing about houses: the form is built from
the fields of the Config class, so a new setting shows up here by itself
(in the tab named by its `group`).
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import shlex
import subprocess
import sys
import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class NoDisplayError(Exception):
    """There is no screen to open the window on."""


# ============================================================
# WHAT THE FORM LOOKS LIKE
# ============================================================

# Order of the tabs; any other group goes after these
GROUP_ORDER = ["House", "Look", "Door & windows", "Pages & output"]

# Nicer names than the ones derived from the setting names
LABELS = {
    "generate_full_house": "Whole house (4 PDFs)",
    "use_roof": "Draw the roof gable (single wall)",
    "textures_enabled": "Paint textures",
    "generate_all_variants": "All material combinations",
    "reuse_textures": "Reuse textures (smaller files)",
    "draw_roof_base": "Draw the base line of the gable",
    "door_and_windows": "Door and windows",
    "door_arched": "Arched door",
    "one_door_per_house": "One door per house",
    "houses": "Number of houses (empty: fill the pages)",
    "mix_pieces": "Mix pieces on the same pages",
    "allow_rotation": "Allow rotating pieces",
    "joint_labels": "Corner letters on the tabs",
    "calibration_ruler": "5 cm ruler on every page",
    "texture_on_roof_overhang": "Texture on the roof overhang",
}

UNITS = {"cm": "cm", "m": "m", "cells": "squares"}

HINT = "Move the mouse over a setting to see what it does."


def pretty_label(name):
    """'door_width_min_m' -> 'Door width min (m)'."""
    if name in LABELS:
        return LABELS[name]
    words = name.split("_")
    unit = ""
    if words[-1] in UNITS:
        unit = f" ({UNITS[words[-1]]})"
        words = words[:-1]
    return " ".join(words).capitalize() + unit


def field_kind(f):
    """'bool', 'choice', 'int', 'float' or 'str'."""
    if isinstance(f.default, bool):
        return "bool"
    if f.metadata.get("choices"):
        return "choice"
    typ = f.metadata.get("type") or type(f.default)
    return typ.__name__


def parse_value(kind, text, optional=False):
    """Turns what was typed into a number or a string.
    Raises ValueError with a readable message."""
    text = text.strip()
    if kind not in ("int", "float"):
        return text

    if not text:
        if optional:
            return None
        raise ValueError("a number is needed")

    number = text.replace(",", ".")        # 7,5 works too
    try:
        return int(number) if kind == "int" else float(number)
    except ValueError:
        what = "a whole number" if kind == "int" else "a number"
        raise ValueError(f"'{text}' is not {what}") from None


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


# Settings that do nothing in some situations are greyed out.
DOOR_SETTINGS = {
    "door_on", "one_door_per_house", "door_arched", "door_width_min_m",
    "door_width_max_m", "door_height_m", "window_width_m", "window_height_m",
    "window_sill_m", "round_window_radius_m", "floor_height_cm",
    "window_spacing_cells",
}
TEXTURE_SETTINGS = {
    "wall_material", "roof_material", "generate_all_variants", "seed",
    "texture_on_roof_overhang", "reuse_textures",
}
FULL_HOUSE_ONLY = {
    "length_cm", "roof_overhang_cm", "roof_margin_cm",
    "generate_all_variants", "houses", "mix_pieces", "allow_rotation",
    "paper", "page_margin_cm", "copy_gap_cm", "calibration_ruler",
    "joint_labels", "one_door_per_house", "door_on",
}


def disabled_fields(values):
    """Names of the settings to grey out, given what is in the form now
    (booleans as bool, everything else as text)."""
    off = set()

    if values["generate_full_house"]:
        off.add("use_roof")
    else:
        off |= FULL_HOUSE_ONLY

    if not values["textures_enabled"]:
        off |= TEXTURE_SETTINGS
    elif values["generate_all_variants"]:
        off |= {"wall_material", "roof_material"}

    if not values["door_and_windows"]:
        off |= DOOR_SETTINGS

    if not str(values["houses"]).strip():
        off.add("mix_pieces")

    return off


def open_path(path):
    """Opens a folder or file with the system's default program."""
    path = str(path)
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class QueueWriter:
    """Receives what the generator prints and hands it to the window."""

    def __init__(self, messages):
        self.messages = messages

    def write(self, text):
        if text:
            self.messages.put(("text", text))
        return len(text)

    def flush(self):
        pass


# ============================================================
# THE WINDOW
# ============================================================

class App:
    def __init__(self, config_cls, run, validate, resolve_dir, to_args,
                 overrides=None):
        self.config_cls = config_cls
        self.run = run
        self.validate = validate
        self.resolve_dir = resolve_dir
        self.to_args = to_args

        if sys.platform == "win32":
            try:        # sharp text on high-resolution screens
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            raise NoDisplayError(str(error)) from None

        self.root.title("Paper Houses")
        self.root.geometry("880x780")
        self.root.minsize(780, 660)

        self.entries = {}       # name -> (field, kind, variable, widgets)
        self.running = False
        self.messages = queue.Queue()
        self.help_text = tk.StringVar(value=HINT)

        self._build()
        self.set_values(self.config_cls(**(overrides or {})))
        self.refresh()

    # ----------------------------------------------------------
    # Building the window
    # ----------------------------------------------------------

    def _build(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        outer = ttk.Frame(root, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=3)
        outer.rowconfigure(3, weight=2)

        # Tabs, one per group of settings
        self.notebook = ttk.Notebook(outer)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        groups = {}
        for f in self._fields():
            groups.setdefault(f.metadata.get("group", "House"), []).append(f)

        names = [g for g in GROUP_ORDER if g in groups]
        names += [g for g in groups if g not in GROUP_ORDER]
        for group in names:
            tab = ttk.Frame(self.notebook, padding=14)
            self.notebook.add(tab, text=group)
            for row, f in enumerate(groups[group]):
                self._build_field(tab, row, f)

        # What the setting under the mouse does
        background = ttk.Style().lookup("TFrame", "background") or None
        tk.Label(outer, textvariable=self.help_text, wraplength=820,
                 justify="left", anchor="nw", height=3,
                 background=background).grid(
            row=1, column=0, sticky="ew", pady=(8, 4))

        # Buttons
        buttons = ttk.Frame(outer)
        buttons.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        buttons.columnconfigure(3, weight=1)

        self.generate_button = ttk.Button(
            buttons, text="Generate PDFs", command=self.start)
        self.generate_button.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Open output folder",
                   command=self.open_folder).grid(row=0, column=1, padx=6)
        ttk.Button(buttons, text="Copy command",
                   command=self.copy_command).grid(row=0, column=2, padx=6)
        ttk.Button(buttons, text="Load preset...",
                   command=self.load_preset).grid(row=0, column=4, padx=6)
        ttk.Button(buttons, text="Save preset...",
                   command=self.save_preset).grid(row=0, column=5, padx=6)
        ttk.Button(buttons, text="Reset",
                   command=self.reset).grid(row=0, column=6, padx=(6, 0))

        # What the generator reports
        log_frame = ttk.Frame(outer)
        log_frame.grid(row=3, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=9, wrap="word",
                           font="TkFixedFont", state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def _fields(self):
        from dataclasses import fields
        return [f for f in fields(self.config_cls)
                if f.metadata.get("cli", True)]

    def _build_field(self, parent, row, f):
        kind = field_kind(f)
        label = pretty_label(f.name)
        description = (f"{label}: {f.metadata.get('help', '')} "
                       f"(default: {format_value(f.default) or 'none'})")

        caption = None
        extra = None

        if kind == "bool":
            variable = tk.BooleanVar()
            widget = ttk.Checkbutton(parent, text=label, variable=variable)
            widget.grid(row=row, column=0, columnspan=3, sticky="w", pady=3)
        else:
            variable = tk.StringVar()
            caption = ttk.Label(parent, text=label)
            caption.grid(row=row, column=0, sticky="w", padx=(0, 14), pady=3)

            if kind == "choice":
                choices = f.metadata["choices"]
                if callable(choices):
                    choices = choices()
                widget = ttk.Combobox(parent, textvariable=variable,
                                      values=list(choices), state="readonly",
                                      width=16)
            else:
                width = 34 if kind == "str" else 16
                widget = ttk.Entry(parent, textvariable=variable, width=width)
            widget.grid(row=row, column=1, sticky="w", pady=3)

            if f.name == "output_dir":
                extra = ttk.Button(parent, text="Browse...",
                                   command=self.browse_output)
                extra.grid(row=row, column=2, sticky="w", padx=6)

        for w in (widget, caption):
            if w is not None:
                w.bind("<Enter>", lambda e, t=description: self.help_text.set(t))
                w.bind("<Leave>", lambda e: self.help_text.set(HINT))
        widget.bind("<FocusIn>", lambda e, t=description: self.help_text.set(t))

        variable.trace_add("write", lambda *_: self.refresh())
        self.entries[f.name] = (f, kind, variable, [w for w in (widget, caption) if w])

    # ----------------------------------------------------------
    # Reading and writing the form
    # ----------------------------------------------------------

    def set_values(self, source):
        """Fills the form from a Config or from a dict of settings."""
        for name, (f, kind, variable, _) in self.entries.items():
            if isinstance(source, dict):
                if name not in source:
                    continue
                value = source[name]
            else:
                value = getattr(source, name)

            if kind == "bool":
                variable.set(bool(value))
            else:
                variable.set(format_value(value))

    def collect(self):
        """Returns (Config, []) or (None, [what is wrong])."""
        values, errors = {}, []
        for name, (f, kind, variable, _) in self.entries.items():
            try:
                if kind == "bool":
                    values[name] = bool(variable.get())
                else:
                    values[name] = parse_value(
                        kind, variable.get(), optional=f.default is None)
            except ValueError as error:
                errors.append(f"{pretty_label(name)}: {error}")

        if errors:
            return None, errors
        return self.config_cls(**values), []

    def refresh(self):
        """Greys out the settings that do nothing right now."""
        if not hasattr(self, "generate_button"):
            return
        values = {}
        for name in ("generate_full_house", "textures_enabled",
                     "generate_all_variants", "door_and_windows", "houses"):
            variable = self.entries[name][2]
            values[name] = variable.get()

        off = disabled_fields(values)
        for name, (_, _, _, widgets) in self.entries.items():
            for w in widgets:
                w.state(["disabled"] if name in off else ["!disabled"])

    # ----------------------------------------------------------
    # Buttons
    # ----------------------------------------------------------

    def append(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def start(self):
        """Generate the PDFs, without freezing the window."""
        if self.running:
            return

        cfg, errors = self.collect()
        if errors:
            messagebox.showerror("Check the settings", "\n".join(errors))
            return
        try:
            self.validate(cfg)
        except ValueError as error:
            messagebox.showerror("Invalid settings", str(error))
            return

        self.clear_log()
        self.set_running(True)

        def work():
            writer = QueueWriter(self.messages)
            try:
                with contextlib.redirect_stdout(writer), \
                        contextlib.redirect_stderr(writer):
                    files = self.run(cfg)
                self.messages.put(("done", files))
            except Exception as error:
                self.messages.put(("error", (error, traceback.format_exc())))

        threading.Thread(target=work, daemon=True).start()
        self.poll()

    def set_running(self, running):
        self.running = running
        self.generate_button.configure(
            text="Generating..." if running else "Generate PDFs",
            state="disabled" if running else "normal")

    def poll(self):
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "text":
                    self.append(payload)
                elif kind == "done":
                    self.finished(payload)
                    return
                elif kind == "error":
                    self.failed(*payload)
                    return
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def finished(self, files):
        self.set_running(False)
        folder = Path(files[0]).parent if files else ""
        self.append(f"\nDone: {len(files)} PDF files in {folder}\n")

    def failed(self, error, trace):
        self.set_running(False)
        if type(error).__name__ in ("ValueError", "OutputError"):
            self.append(f"\n{error}\n")
        else:
            self.append(f"\n{trace}\n")
        messagebox.showerror(
            "Could not generate the PDFs",
            str(error) if str(error) else type(error).__name__)

    def open_folder(self):
        text = self.entries["output_dir"][2].get()
        path = self.resolve_dir(self.config_cls(output_dir=text))
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def browse_output(self):
        chosen = filedialog.askdirectory(title="Folder for the PDFs")
        if chosen:
            self.entries["output_dir"][2].set(chosen)

    def command_text(self, cfg):
        """The command that does the same as the window."""
        args = self.to_args(cfg) or ["--no-gui"]
        if sys.platform == "win32":
            joined = subprocess.list2cmdline(args)
        else:
            joined = shlex.join(args)
        return f"python main.py {joined}"

    def copy_command(self):
        cfg, errors = self.collect()
        if errors:
            messagebox.showerror("Check the settings", "\n".join(errors))
            return
        command = self.command_text(cfg)
        self.root.clipboard_clear()
        self.root.clipboard_append(command)
        self.append(f"Copied to the clipboard:\n{command}\n")

    def save_preset(self):
        cfg, errors = self.collect()
        if errors:
            messagebox.showerror("Check the settings", "\n".join(errors))
            return
        path = filedialog.asksaveasfilename(
            title="Save the settings", defaultextension=".json",
            filetypes=[("Preset", "*.json")])
        if not path:
            return
        data = {name: getattr(cfg, name) for name in self.entries}
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.append(f"Preset saved: {path}\n")

    def load_preset(self):
        path = filedialog.askopenfilename(
            title="Load settings", filetypes=[("Preset", "*.json")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("not a preset")
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot load the preset", str(error))
            return
        self.set_values(data)
        self.append(f"Preset loaded: {path}\n")

    def reset(self):
        self.set_values(self.config_cls())
        self.append("Settings back to the defaults.\n")


def launch(config_cls, run, validate, resolve_dir, to_args, overrides=None):
    """Opens the window and waits until it is closed."""
    app = App(config_cls, run, validate, resolve_dir, to_args, overrides)
    app.root.mainloop()
    return app
