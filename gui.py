"""The window to edit the settings and generate the PDFs.

Started by main.py. It knows nothing about houses: the settings come from
the fields of the Config class, the texts from i18n.py.

  - The first four pages are the simple view: sizes in game squares (with a
    grid to pick them), materials as pictures, switches.
  - The "Advanced" page lists every setting in its own unit (cm, metres).
  Both views edit the same values.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import random
import shlex
import subprocess
import sys
import threading
import tkinter as tk
import traceback
from dataclasses import fields
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from i18n import LANGUAGES, detect_language, has_text, tr

try:
    from PIL import Image, ImageDraw, ImageTk
except Exception:        # no Pillow (or no tkinter support in it): no icons
    Image = ImageDraw = ImageTk = None


class NoDisplayError(Exception):
    """There is no screen to open the window on."""


# ============================================================
# LOOK
# ============================================================

from gui_images import (COLORS, SUPER, draw_icon, draw_indicator, draw_logo,
                        draw_swatch)

# Pages of the window, in order, with the icon of each
PAGES = [("house", "house"), ("look", "palette"), ("doors", "door"),
         ("pages", "page"), ("advanced", "gear")]

# Order of the groups in the Advanced page; any other group goes after
GROUP_ORDER = ["House", "Look", "Door & windows", "Pages & output"]

# Settings in cm that the simple view shows in game squares
SQUARE_LINKS = ("width_cm", "length_cm", "height_cm", "roof_height_cm",
                "floor_height_cm", "wing_length_cm")


# ============================================================
# PURE HELPERS
# ============================================================

def pretty_label(name):
    """'door_width_min_m' -> 'Door width min (m)' (used when a setting has
    no text in i18n.py)."""
    words = name.split("_")
    unit = ""
    units = {"cm": "cm", "m": "m", "cells": "squares"}
    if words[-1] in units:
        unit = f" ({units[words[-1]]})"
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


def parse_float(text):
    """A number typed by the user (7,5 works too), or None."""
    try:
        return float(str(text).strip().replace(",", "."))
    except ValueError:
        return None


def parse_value(kind, text, optional=False, language="en"):
    """Turns what was typed into a number or a string.
    Raises ValueError with a readable message."""
    text = text.strip()
    if kind not in ("int", "float"):
        return text

    if not text:
        if optional:
            return None
        raise ValueError(tr(language, "err.number_needed"))

    number = text.replace(",", ".")
    try:
        return int(number) if kind == "int" else float(number)
    except ValueError:
        key = "err.not_whole" if kind == "int" else "err.not_number"
        raise ValueError(tr(language, key, text=text)) from None


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


# Settings that do nothing in some situations are greyed out.
DOOR_ONLY = {
    "door_on", "door_position", "door_style", "one_door_per_house",
    "door_arched", "door_width_min_m", "door_width_max_m", "door_height_m",
}
WINDOW_ONLY = {
    "window_style", "window_width_m", "window_height_m", "window_sill_m",
    "round_window_radius_m", "floor_height_cm", "window_spacing_cells",
}
DOOR_SETTINGS = DOOR_ONLY | WINDOW_ONLY
TEXTURE_SETTINGS = {
    "wall_material", "roof_material", "generate_all_variants", "seed",
    "texture_on_roof_overhang", "reuse_textures",
}
FULL_HOUSE_ONLY = {
    "length_cm", "roof_overhang_cm", "roof_margin_cm",
    "generate_all_variants", "houses", "mix_pieces", "allow_rotation",
    "paper", "page_margin_cm", "copy_gap_cm", "calibration_ruler",
    "joint_labels", "one_door_per_house", "door_on", "complete_only",
    "house_shape", "wing_length_cm", "roof_type", "roof_windows",
}
# Only a roof with two slopes has these
GABLED_ONLY = {
    "roof_height_cm", "roof_flap_cm", "roof_overhang_cm", "draw_roof_base",
    "round_window_radius_m", "roof_windows",
}
ROOF_WINDOW_SETTINGS = {"roof_window_position", "roof_window_clearance_cm"}


def disabled_fields(values):
    """Names of the settings to grey out, given what is in the form now
    (booleans as bool, everything else as text). 'houses_spin' is the
    number box next to the 'specific number of houses' switch."""
    off = set()
    full = values["generate_full_house"]

    if full:
        off.add("use_roof")
    else:
        off |= FULL_HOUSE_ONLY | {"houses_spin"}

    if not values["textures_enabled"]:
        off |= TEXTURE_SETTINGS
    elif values["generate_all_variants"]:
        off |= {"wall_material", "roof_material"}

    if not values.get("door", True):
        off |= DOOR_ONLY
    if not values.get("windows", True):
        off |= WINDOW_ONLY

    if not str(values["houses"]).strip():
        off |= {"mix_pieces", "houses_spin"}

    if values["house_shape"] != "L":
        off.add("wing_length_cm")

    if not (values.get("top_tabs", True) or values.get("bottom_tabs", True)):
        off.add("tab_corners")

    if values["roof_type"] == "flat":
        off |= GABLED_ONLY
    if values["house_shape"] == "L":
        off.add("roof_windows")
    if (not values["roof_windows"] or values["house_shape"] == "L"
            or values["roof_type"] == "flat" or not full):
        off |= ROOF_WINDOW_SETTINGS

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
# WIDGETS
# ============================================================

class SizePicker(tk.Canvas):
    """A grid like the one used to choose the size of a table in a word
    processor: move over it, click, and the house gets that many squares.
    A right click chooses how far down the second wing of an L goes."""

    ROWS, COLS = 8, 10

    def __init__(self, parent, scale, font, on_pick, on_hover, on_wing=None):
        self.cell = round(26 * scale)
        self.gap = round(3 * scale)
        self.left = round(26 * scale)
        self.top = round(24 * scale)
        width = self.left + self.COLS * (self.cell + self.gap) + self.gap
        height = self.top + self.ROWS * (self.cell + self.gap) + self.gap

        super().__init__(parent, width=width, height=height, bg=COLORS["card"],
                         highlightthickness=0, cursor="hand2")
        self.on_pick = on_pick
        self.on_hover = on_hover
        self.on_wing = on_wing
        self.selection = None       # (rows, columns) as counts
        self.wing = None            # rows, counting the ones of the house
        self.hover = None           # (row index, column index)

        self.items = {}
        for r in range(self.ROWS):
            for c in range(self.COLS):
                x = self.left + self.gap + c * (self.cell + self.gap)
                y = self.top + self.gap + r * (self.cell + self.gap)
                self.items[(r, c)] = self.create_rectangle(
                    x, y, x + self.cell, y + self.cell, width=1,
                    fill=COLORS["empty"], outline=COLORS["empty_border"])

        self.long_label = self.create_text(
            self.left + self.gap, self.top / 2, anchor="w", font=font,
            fill=COLORS["muted"])
        self.gable_label = self.create_text(
            self.left / 2, self.top + self.gap, anchor="ne", font=font,
            fill=COLORS["muted"], angle=90)

        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            self.bind(sequence, self._right_click)      # Windows, Mac

    def set_labels(self, long_text, gable_text):
        self.itemconfigure(self.long_label, text=long_text)
        self.itemconfigure(self.gable_label, text=gable_text)

    def _cell_at(self, event):
        step = self.cell + self.gap
        c = (event.x - self.left - self.gap) // step
        r = (event.y - self.top - self.gap) // step
        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
            return int(r), int(c)
        return None

    def _motion(self, event):
        position = self._cell_at(event)
        if position != self.hover:
            self.hover = position
            self._paint()
            self.on_hover(None if position is None
                          else (position[0] + 1, position[1] + 1))

    def _leave(self, _event):
        if self.hover is not None:
            self.hover = None
            self._paint()
            self.on_hover(None)

    def _click(self, event):
        position = self._cell_at(event)
        if position is not None:
            self.on_pick(position[0] + 1, position[1] + 1)

    def _right_click(self, event):
        position = self._cell_at(event)
        if position is not None and self.on_wing:
            self.on_wing(position[0] + 1)

    def set_selection(self, rows, cols, wing=None):
        self.selection = (rows, cols) if rows and cols else None
        self.wing = wing if self.selection else None
        self._paint()

    def _paint(self):
        for (r, c), item in self.items.items():
            if self.hover and r <= self.hover[0] and c <= self.hover[1]:
                fill, outline = COLORS["accent_hover"], COLORS["accent_hover"]
            elif self.selection and r < self.selection[0] \
                    and c < self.selection[1]:
                fill, outline = COLORS["accent"], COLORS["accent_dark"]
            elif (self.selection and self.wing and c < self.selection[0]
                  and self.selection[0] <= r < self.wing):
                fill, outline = COLORS["wing"], COLORS["accent_dark"]
            else:
                fill, outline = COLORS["empty"], COLORS["empty_border"]
            self.itemconfigure(item, fill=fill, outline=outline)


class ScrollFrame(ttk.Frame):
    """A frame that scrolls vertically when its content does not fit.
    Put the widgets in `.inner`."""

    def __init__(self, parent):
        super().__init__(parent, style="Page.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0,
                                bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical",
                                 command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.bar.grid(row=0, column=1, sticky="ns")

        self.inner = ttk.Frame(self.canvas, style="Page.TFrame")
        self.window = self.canvas.create_window((0, 0), window=self.inner,
                                                anchor="nw")
        self.inner.bind("<Configure>", self._content_changed)
        self.canvas.bind("<Configure>", self._size_changed)

    def _content_changed(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._toggle_bar()

    def _size_changed(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        self._toggle_bar()

    def _toggle_bar(self):
        if self.inner.winfo_reqheight() > self.canvas.winfo_height() > 1:
            self.bar.grid()
        else:
            self.bar.grid_remove()
            self.canvas.yview_moveto(0)

    def scroll(self, lines):
        if self.inner.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(lines, "units")


# ============================================================
# THE WINDOW
# ============================================================

class App:
    def __init__(self, config_cls, run, validate, resolve_dir, to_args,
                 overrides=None, palettes=None):
        self.config_cls = config_cls
        self.run = run
        self.validate = validate
        self.resolve_dir = resolve_dir
        self.to_args = to_args
        self.palettes = palettes or {}
        overrides = dict(overrides or {})

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

        self.scale = max(1.0, self.root.winfo_fpixels("1i") / 96)

        language = overrides.get("language") or detect_language()
        self.language = language if language in LANGUAGES else "en"

        self.running = False
        self.built = False
        self.messages = queue.Queue()
        self._images = []
        self._icon_cache = {}
        self._linking = False
        self._linking_houses = False

        self.root.geometry(f"{self.px(1160)}x{self.px(900)}")
        self.root.minsize(self.px(1000), self.px(700))
        self.root.configure(bg=COLORS["bg"])
        self.root.title(self.t("ui.title"))
        self._set_window_icon()

        self._setup_fonts()
        self._setup_style()
        self._make_variables()

        self._build_ui()
        self.set_values(self.config_cls(**overrides))

        self.root.bind_all("<MouseWheel>", self._wheel)
        self.root.bind_all("<Button-4>", self._wheel)
        self.root.bind_all("<Button-5>", self._wheel)

    # ----------------------------------------------------------
    # Small helpers
    # ----------------------------------------------------------

    def t(self, key, **values):
        return tr(self.language, key, **values)

    def px(self, n):
        return int(round(n * self.scale))

    def num(self, value):
        """A number for a label: 7.5, or 7,5 in Italian."""
        text = format_value(value)
        return text.replace(".", ",") if self.language == "it" else text

    def _fields(self):
        return [f for f in fields(self.config_cls)
                if f.metadata.get("cli", True) and f.metadata.get("gui", True)]

    def label_for(self, name):
        key = f"label.{name}"
        return self.t(key) if has_text("en", key) else pretty_label(name)

    def help_for(self, name):
        key = f"help.{name}"
        if has_text("en", key):
            return self.t(key)
        return self.fields[name].metadata.get("help", "")

    def describe(self, name):
        default = format_value(self.fields[name].default) or self.t("ui.none")
        return (f"{self.label_for(name)}: {self.help_for(name)} "
                f"({self.t('ui.default', value=default)})")

    def material_label(self, name):
        key = f"material.{name}"
        return self.t(key) if has_text("en", key) else name

    def icon(self, name, color, size=18):
        if Image is None:
            return None
        key = (name, color, size)
        if key not in self._icon_cache:
            image = ImageTk.PhotoImage(draw_icon(name, self.px(size), color),
                                       master=self.root)
            self._icon_cache[key] = image
        return self._icon_cache[key]

    def _set_window_icon(self):
        if Image is None:
            return
        try:
            logo = ImageTk.PhotoImage(draw_logo(64), master=self.root)
            self._images.append(logo)
            self.root.iconphoto(True, logo)
        except Exception:
            pass

    # ----------------------------------------------------------
    # Fonts and style
    # ----------------------------------------------------------

    def _setup_fonts(self):
        preferred = {"win32": "Segoe UI", "darwin": "Helvetica Neue"}.get(
            sys.platform)
        family = tkfont.nametofont("TkDefaultFont").actual("family")
        if preferred and preferred in tkfont.families(self.root):
            family = preferred

        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.nametofont(name).configure(family=family, size=10)

        self.fonts = {
            "base": (family, 10),
            "small": (family, 9),
            "bold": (family, 10, "bold"),
            "nav": (family, 11),
            "title": (family, 20, "bold"),
            "section": (family, 12, "bold"),
            "card": (family, 11, "bold"),
        }

    def _setup_style(self):
        c, f = COLORS, self.fonts
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=c["bg"], foreground=c["text"],
                        font=f["base"], bordercolor=c["border"],
                        lightcolor=c["bg"], darkcolor=c["bg"],
                        troughcolor=c["trough"], focuscolor=c["bg"])
        style.configure("Page.TFrame", background=c["bg"])
        style.configure("Card.TFrame", background=c["card"])

        style.configure("Page.TLabel", background=c["bg"])
        style.map("Page.TLabel", background=[("disabled", c["bg"])])
        style.configure("Title.Page.TLabel", font=f["title"])
        style.configure("Subtitle.Page.TLabel", foreground=c["muted"])
        style.configure("Section.Page.TLabel", font=f["section"])
        style.configure("Help.Page.TLabel", foreground=c["muted"],
                        font=f["small"])
        style.configure("Card.TLabel", background=c["card"])
        style.map("Card.TLabel",
                  background=[("disabled", c["card"])],
                  foreground=[("disabled", c["muted"])])
        style.configure("Muted.Card.TLabel", foreground=c["muted"],
                        font=f["small"])
        style.configure("CardTitle.Card.TLabel", font=f["card"])

        self._setup_indicators(style)

        for name in ("TEntry", "TSpinbox", "TCombobox"):
            style.configure(name, fieldbackground="white",
                            foreground=c["text"], bordercolor=c["border"],
                            lightcolor="white", darkcolor="white",
                            insertcolor=c["text"], arrowcolor=c["text"],
                            padding=4, arrowsize=self.px(15))
            style.map(name,
                      bordercolor=[("focus", c["accent"])],
                      fieldbackground=[("disabled", c["bg"]),
                                       ("readonly", "white")],
                      foreground=[("disabled", c["muted"])],
                      arrowcolor=[("disabled", c["disabled"])])
        self.root.option_add("*TCombobox*Listbox.background", "white")
        self.root.option_add("*TCombobox*Listbox.foreground", c["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground",
                             c["accent"])

        style.configure("TButton", background="white", foreground=c["text"],
                        bordercolor=c["border"], lightcolor="white",
                        darkcolor="white", padding=(12, 7))
        style.map("TButton",
                  background=[("active", c["accent_light"]),
                              ("disabled", c["bg"])],
                  bordercolor=[("active", c["accent_hover"])],
                  foreground=[("disabled", c["muted"])])
        style.configure("TMenubutton", background="white",
                        foreground=c["text"], bordercolor=c["border"],
                        lightcolor="white", darkcolor="white",
                        arrowcolor=c["text"], padding=(12, 7))
        style.map("TMenubutton",
                  background=[("active", c["accent_light"])],
                  bordercolor=[("active", c["accent_hover"])])
        style.configure("Primary.TButton", background=c["accent"],
                        foreground="white", bordercolor=c["accent"],
                        lightcolor=c["accent"], darkcolor=c["accent"],
                        padding=(20, 9), font=f["bold"])
        style.map("Primary.TButton",
                  background=[("active", c["accent_dark"]),
                              ("disabled", c["accent_hover"])],
                  bordercolor=[("active", c["accent_dark"])],
                  foreground=[("disabled", "#fff4ee")])

        style.configure("Vertical.TScrollbar", arrowsize=self.px(14),
                        background=c["trough"],
                        troughcolor=c["bg"], bordercolor=c["bg"],
                        arrowcolor=c["muted"], lightcolor=c["trough"],
                        darkcolor=c["trough"])

    def _setup_indicators(self, style):
        """Check buttons and radio buttons with hand-drawn indicators
        (the ones of the theme are tiny). Without Pillow the theme's own
        are kept."""
        c = COLORS
        for kind in ("Check", "Radio"):
            name = f"Card.T{kind}button"
            style.configure(name, background=c["card"],
                            foreground=c["text"], padding=(2, 3))
            style.map(name, background=[("active", c["card"])],
                      foreground=[("disabled", c["muted"])])
            if Image is None:
                continue

            size, pad = self.px(18), self.px(7)
            images = {}
            for state in ("normal", "hover", "selected", "disabled",
                          "selected_disabled"):
                image = ImageTk.PhotoImage(
                    draw_indicator(kind.lower(), state, size, pad),
                    master=self.root)
                self._images.append(image)
                images[state] = image

            element = f"Card.{kind}.indicator"
            style.element_create(
                element, "image", images["normal"],
                ("disabled", "selected", images["selected_disabled"]),
                ("disabled", images["disabled"]),
                ("selected", images["selected"]),
                ("active", images["hover"]), sticky="w")
            base = f"{kind}button"
            style.layout(name, [(f"{base}.padding", {
                "sticky": "nswe", "children": [
                    (element, {"side": "left", "sticky": ""}),
                    (f"{base}.focus", {"side": "left", "sticky": "w",
                                       "children": [(f"{base}.label",
                                                     {"sticky": "nswe"})]}),
                ]})])

    # ----------------------------------------------------------
    # Values shared by every view of the settings
    # ----------------------------------------------------------

    def _make_variables(self):
        self.fields = {f.name: f for f in self._fields()}
        self.kinds = {name: field_kind(f) for name, f in self.fields.items()}
        self.vars = {}
        for name, kind in self.kinds.items():
            self.vars[name] = tk.BooleanVar() if kind == "bool" \
                else tk.StringVar()

        self.page_var = tk.StringVar(value="house")
        self.lang_var = tk.StringVar(value=self.language)
        self.help_text = tk.StringVar(value=self.t("ui.hint"))
        self.picker_caption = tk.StringVar()
        self.use_houses = tk.BooleanVar()

        # The simple view shows some sizes in squares instead of cm
        self.squares = {n: tk.StringVar() for n in SQUARE_LINKS
                        if n in self.vars}
        self.cm_text = {n: tk.StringVar() for n in self.squares}

        for var in self.vars.values():
            var.trace_add("write", lambda *_: self.refresh())
        for name in self.squares:
            self.vars[name].trace_add("write", self._cm_changed)
            self.squares[name].trace_add(
                "write", lambda *_, n=name: self._squares_changed(n))
        if "cell_cm" in self.vars:
            self.vars["cell_cm"].trace_add("write", self._cm_changed)
        self.vars["houses"].trace_add("write", self._houses_changed)
        self.use_houses.trace_add("write", self._use_houses_changed)

    def _cell_size(self):
        value = parse_float(self.vars["cell_cm"].get())
        return value if value and value > 0 else None

    def _cm_changed(self, *_):
        """A value in cm changed: update the squares shown for it."""
        if self._linking:
            return
        cell = self._cell_size()
        self._linking = True
        try:
            for name, squares in self.squares.items():
                cm = parse_float(self.vars[name].get())
                if cm is None or cell is None:
                    self.cm_text[name].set("")
                    continue
                squares.set(format_value(round(cm / cell, 4)))
                self.cm_text[name].set(self.t("ui.cm", value=self.num(cm)))
        finally:
            self._linking = False
        self._update_picker()

    def _squares_changed(self, name):
        """Squares were typed: update the cm behind them."""
        if self._linking:
            return
        cell = self._cell_size()
        value = parse_float(self.squares[name].get())
        if cell is None or value is None:
            return
        self._linking = True
        try:
            cm = round(value * cell, 4)
            self.vars[name].set(format_value(cm))
            self.cm_text[name].set(self.t("ui.cm", value=self.num(cm)))
        finally:
            self._linking = False
        self._update_picker()

    def _normalize_square(self, name):
        """After the arrows of a number box: '3.0' becomes '3'."""
        value = parse_float(self.squares[name].get())
        if value is not None:
            self._linking = True
            try:
                self.squares[name].set(format_value(round(value, 4)))
            finally:
                self._linking = False

    def _houses_changed(self, *_):
        if self._linking_houses:
            return
        self._linking_houses = True
        try:
            self.use_houses.set(bool(self.vars["houses"].get().strip()))
        finally:
            self._linking_houses = False

    def _use_houses_changed(self, *_):
        if self._linking_houses:
            return
        self._linking_houses = True
        try:
            houses = self.vars["houses"]
            if self.use_houses.get():
                if not houses.get().strip():
                    houses.set("1")
            else:
                houses.set("")
        finally:
            self._linking_houses = False
        self.refresh()

    # ----------------------------------------------------------
    # Building the window
    # ----------------------------------------------------------

    def _build_ui(self):
        self.built = False
        self.widgets = {}
        self.pages = {}
        self.scrollers = {}
        self.swatch_buttons = {}

        self.shell = tk.Frame(self.root, bg=COLORS["bg"])
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.shell.columnconfigure(1, weight=1)
        self.shell.rowconfigure(0, weight=1)

        self._build_sidebar()

        right = tk.Frame(self.shell, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.container = tk.Frame(right, bg=COLORS["bg"])
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        self._build_house_page()
        self._build_look_page()
        self._build_doors_page()
        self._build_pages_page()
        self._build_advanced_page()

        ttk.Label(right, textvariable=self.help_text, style="Help.Page.TLabel",
                  wraplength=self.px(760), justify="left", anchor="nw").grid(
            row=1, column=0, sticky="ew", padx=self.px(32), pady=(0, 6))

        self._build_actions(right, row=2)
        self._build_log(right, row=3)

        self.built = True
        self.show_page(self.page_var.get())
        self._cm_changed()
        self.refresh()

    def _build_sidebar(self):
        c = COLORS
        sidebar = tk.Frame(self.shell, bg=c["sidebar"], width=self.px(236))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.pack_propagate(False)

        header = tk.Frame(sidebar, bg=c["sidebar"])
        header.pack(fill="x", padx=self.px(18), pady=(self.px(22), self.px(24)))
        if Image is not None:
            logo = ImageTk.PhotoImage(draw_logo(self.px(38)), master=self.root)
            self._images.append(logo)
            tk.Label(header, image=logo, bg=c["sidebar"]).pack(side="left")
        tk.Label(header, text=self.t("ui.title"), bg=c["sidebar"],
                 fg="white", font=(self.fonts["section"])).pack(
            side="left", padx=(self.px(10), 0))

        for key, icon_name in PAGES:
            image = self.icon(icon_name, c["sidebar_text"], 20)
            kwargs = {"image": image, "compound": "left"} if image else {}
            tk.Radiobutton(
                sidebar, text="  " + self.t(f"page.{key}"),
                variable=self.page_var, value=key, indicatoron=False,
                command=lambda k=key: self.show_page(k), anchor="w",
                bg=c["sidebar"], fg=c["sidebar_text"],
                selectcolor=c["nav_selected"], activebackground=c["nav_hover"],
                activeforeground="white", bd=0, relief="flat",
                overrelief="flat", offrelief="flat", highlightthickness=0,
                padx=self.px(20), pady=self.px(11), font=self.fonts["nav"],
                cursor="hand2", **kwargs).pack(fill="x")

        language = tk.Frame(sidebar, bg=c["sidebar"])
        language.pack(side="bottom", fill="x", padx=self.px(18),
                      pady=(0, self.px(20)))
        tk.Label(language, text=self.t("ui.language"), bg=c["sidebar"],
                 fg=c["sidebar_muted"], font=self.fonts["small"]).pack(
            anchor="w", pady=(0, 4))
        row = tk.Frame(language, bg=c["sidebar"])
        row.pack(anchor="w")
        for code, name in LANGUAGES.items():
            tk.Radiobutton(
                row, text=name, variable=self.lang_var, value=code,
                indicatoron=False, command=self.change_language,
                bg=c["sidebar"], fg=c["sidebar_text"],
                selectcolor=c["accent"], activebackground=c["nav_hover"],
                activeforeground="white", bd=0, relief="flat",
                overrelief="flat", offrelief="flat", highlightthickness=0,
                padx=self.px(12), pady=self.px(5), font=self.fonts["small"],
                cursor="hand2").pack(side="left", padx=(0, 4))

    def _page(self, key):
        """A page of the window. Returns the frame for its content."""
        page = ttk.Frame(self.container, style="Page.TFrame",
                         padding=(self.px(32), self.px(26), self.px(32),
                                  self.px(6)))
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(2, weight=1)

        ttk.Label(page, text=self.t(f"title.{key}"),
                  style="Title.Page.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(page, text=self.t(f"sub.{key}"), style="Subtitle.Page.TLabel",
                  wraplength=self.px(740), justify="left").grid(
            row=1, column=0, sticky="w", pady=(2, self.px(16)))

        scroller = ScrollFrame(page)
        scroller.grid(row=2, column=0, sticky="nsew")
        self.pages[key] = page
        self.scrollers[key] = scroller
        return scroller.inner

    def show_page(self, key):
        self.page_var.set(key)
        if key in self.pages:
            self.pages[key].tkraise()
        self.help_text.set(self.t("ui.hint"))

    def _card(self, parent, title, row, column=0, columnspan=1, sticky="new",
              pady=(0, 14), padx=0):
        outer = tk.Frame(parent, bg=COLORS["card"],
                         highlightbackground=COLORS["border"],
                         highlightcolor=COLORS["border"], highlightthickness=1)
        outer.grid(row=row, column=column, columnspan=columnspan,
                   sticky=sticky, pady=pady, padx=padx)
        inner = ttk.Frame(outer, style="Card.TFrame", padding=self.px(18))
        inner.pack(fill="both", expand=True)
        if title:
            ttk.Label(inner, text=title, style="CardTitle.Card.TLabel").grid(
                row=0, column=0, columnspan=6, sticky="w",
                pady=(0, self.px(12)))
        return inner

    def _reg(self, name, *widgets):
        self.widgets.setdefault(name, []).extend(widgets)

    def _help(self, text, *widgets):
        for w in widgets:
            w.bind("<Enter>", lambda e, t=text: self.help_text.set(t), add="+")
            w.bind("<FocusIn>", lambda e, t=text: self.help_text.set(t),
                   add="+")
            w.bind("<Leave>", lambda e: self.help_text.set(self.t("ui.hint")),
                   add="+")

    # ---- Simple widgets bound to a setting ----

    def _check(self, parent, name, row, column=0, columnspan=4, text=None,
               pady=(2, 2)):
        widget = ttk.Checkbutton(parent, text=text or self.label_for(name),
                                 variable=self.vars[name],
                                 style="Card.TCheckbutton")
        widget.grid(row=row, column=column, columnspan=columnspan, sticky="w",
                    pady=pady)
        self._reg(name, widget)
        self._help(self.describe(name), widget)
        return widget

    def _radios(self, parent, name, row, labels, column=1):
        box = ttk.Frame(parent, style="Card.TFrame")
        box.grid(row=row, column=column, columnspan=3, sticky="w")
        widgets = []
        for i, (value, text) in enumerate(labels):
            widget = ttk.Radiobutton(box, text=text, value=value,
                                     variable=self.vars[name],
                                     style="Card.TRadiobutton")
            widget.grid(row=0, column=i, padx=(0, 16))
            widgets.append(widget)
        self._reg(name, *widgets)
        self._help(self.describe(name), *widgets)

    def _square_row(self, parent, row, name, step=1):
        label = ttk.Label(parent, text=self.t(f"ui.sq.{name}"),
                          style="Card.TLabel")
        label.grid(row=row, column=0, sticky="w", padx=(0, 16), pady=5)
        spin = ttk.Spinbox(parent, textvariable=self.squares[name], from_=0.5,
                           to=60, increment=step, width=7,
                           command=lambda n=name: self._normalize_square(n))
        spin.grid(row=row, column=1, sticky="w", pady=5)
        note = ttk.Label(parent, textvariable=self.cm_text[name],
                         style="Muted.Card.TLabel")
        note.grid(row=row, column=2, sticky="w", padx=(10, 0))
        self._reg(name, label, spin)
        self._help(self.describe(name), label, spin)

    # ---- House page ----

    def _build_house_page(self):
        body = self._page("house")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)       # as wide as the grid needs

        # Two columns, each with two cards one under the other
        left = ttk.Frame(body, style="Page.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        right = ttk.Frame(body, style="Page.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)

        size = self._card(left, self.t("card.size"), row=0, sticky="new")
        for i, (name, step) in enumerate((("width_cm", 1), ("length_cm", 1),
                                          ("height_cm", 1),
                                          ("roof_height_cm", 0.5))):
            self._square_row(size, i + 1, name, step)

        shape = self._card(left, self.t("card.shape"), row=1, sticky="new")
        label = ttk.Label(shape, text=self.t("ui.shape"), style="Card.TLabel")
        label.grid(row=1, column=0, sticky="w", padx=(0, 16), pady=5)
        self._radios(shape, "house_shape", 1,
                     [("rectangle", self.t("ui.shape_rect")),
                      ("L", self.t("ui.shape_l"))])
        self._reg("house_shape", label)
        self._square_row(shape, 2, "wing_length_cm", 1)
        label = ttk.Label(shape, text=self.t("ui.roof_shape"),
                          style="Card.TLabel")
        label.grid(row=3, column=0, sticky="w", padx=(0, 16), pady=5)
        self._radios(shape, "roof_type", 3,
                     [("gabled", self.t("ui.roof_gabled")),
                      ("flat", self.t("ui.roof_flat"))])
        self._reg("roof_type", label)

        picker_card = self._card(right, self.t("card.picker"), row=0,
                                 sticky="new")
        self.picker = SizePicker(picker_card, self.scale, self.fonts["small"],
                                 self._pick, self._picker_hover,
                                 self._pick_wing)
        self.picker.grid(row=1, column=0, sticky="w")
        self.picker.set_labels(self.t("ui.picker_long"),
                               self.t("ui.picker_gable"))
        ttk.Label(picker_card, textvariable=self.picker_caption,
                  style="Muted.Card.TLabel", wraplength=self.px(330),
                  justify="left").grid(row=2, column=0, sticky="w",
                                       pady=(8, 0))
        ttk.Label(picker_card, text=self.t("ui.picker_hint"),
                  style="Muted.Card.TLabel").grid(row=3, column=0, sticky="w",
                                                  pady=(2, 0))
        self._reg("width_cm", self.picker)
        self._help(self.t("ui.picker_help"), self.picker)

        amount = self._card(right, self.t("card.amount"), row=1, sticky="new")
        check = ttk.Checkbutton(amount, text=self.t("ui.specific_houses"),
                                variable=self.use_houses,
                                style="Card.TCheckbutton")
        check.grid(row=1, column=0, sticky="w")
        spin = ttk.Spinbox(amount, textvariable=self.vars["houses"], from_=1,
                           to=99, increment=1, width=6)
        spin.grid(row=1, column=1, sticky="w", padx=(14, 0))
        ttk.Label(amount, text=self.t("ui.houses_hint"),
                  style="Muted.Card.TLabel", wraplength=self.px(330),
                  justify="left").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self._reg("houses", check)
        self._reg("houses_spin", spin)
        self._help(self.describe("houses"), check, spin)

    def _pick(self, rows, cols):
        self.squares["width_cm"].set(format_value(rows))
        self.squares["length_cm"].set(format_value(cols))

    def _pick_wing(self, rows):
        """Right click on the grid: the second wing goes down that far. A
        click inside the house itself takes the second wing away."""
        width = parse_float(self.squares["width_cm"].get())
        if width is None:
            return
        if rows <= round(width):
            self.vars["house_shape"].set("rectangle")
            return
        self.vars["house_shape"].set("L")
        self.squares["wing_length_cm"].set(format_value(rows))

    def _picker_hover(self, position):
        if position is None:
            self._update_picker(caption_only=True)
            return
        rows, cols = position
        cell = self._cell_size() or 2.5
        self.picker_caption.set(self.t(
            "ui.picker_caption", rows=rows, cols=cols,
            w=self.num(round(rows * cell, 4)),
            l=self.num(round(cols * cell, 4))))

    def _update_picker(self, caption_only=False):
        """Show the current size on the grid, if it is a whole number of
        squares that fits."""
        cell = self._cell_size()
        width = parse_float(self.squares["width_cm"].get())
        length = parse_float(self.squares["length_cm"].get())

        selection = None
        if cell and width and length:
            rows, cols = round(width), round(length)
            if (abs(width - rows) < 1e-6 and abs(length - cols) < 1e-6
                    and 1 <= rows <= SizePicker.ROWS
                    and 1 <= cols <= SizePicker.COLS):
                selection = (rows, cols)

        # The second wing of an L, if it is a whole number of squares that
        # fits and goes beyond the house
        wing = None
        if selection and self.vars["house_shape"].get() == "L":
            value = parse_float(self.squares["wing_length_cm"].get())
            if value and abs(value - round(value)) < 1e-6 \
                    and selection[0] < round(value) <= SizePicker.ROWS:
                wing = round(value)

        if not caption_only and hasattr(self, "picker"):
            self.picker.set_selection(*(selection or (0, 0)), wing)

        if selection and wing:
            self.picker_caption.set(self.t(
                "ui.picker_caption_l", rows=selection[0], cols=selection[1],
                w=self.num(round(selection[0] * cell, 4)),
                l=self.num(round(selection[1] * cell, 4)),
                wing=wing, wl=self.num(round(wing * cell, 4))))
        elif selection:
            self.picker_caption.set(self.t(
                "ui.picker_caption", rows=selection[0], cols=selection[1],
                w=self.num(round(selection[0] * cell, 4)),
                l=self.num(round(selection[1] * cell, 4))))
        else:
            self.picker_caption.set(self.t("ui.picker_none"))

    # ---- Look page ----

    def _build_look_page(self):
        body = self._page("look")
        body.columnconfigure(0, weight=1)

        card = self._card(body, self.t("card.textures"), row=0)
        self._check(card, "textures_enabled", 1)

        self._materials(card, 2, "wall_material", "wall", self.t("ui.walls"))
        self._materials(card, 3, "roof_material", "roof", self.t("ui.roof"))
        self._check(card, "generate_all_variants", 4, pady=(10, 2))

        variation = self._card(body, self.t("card.variation"), row=1)
        label = ttk.Label(variation, text=self.t("ui.variation_number"),
                          style="Card.TLabel")
        label.grid(row=1, column=0, sticky="w", padx=(0, 14))
        spin = ttk.Spinbox(variation, textvariable=self.vars["seed"], from_=0,
                           to=99999, increment=1, width=8)
        spin.grid(row=1, column=1, sticky="w")
        dice = self.icon("dice", COLORS["icon"], 18)
        kwargs = {"image": dice, "compound": "left"} if dice else {}
        button = ttk.Button(variation, text=" " + self.t("ui.new_variation"),
                            command=self.new_variation, **kwargs)
        button.grid(row=1, column=2, sticky="w", padx=(14, 0))
        self._reg("seed", label, spin, button)
        self._help(self.describe("seed"), label, spin, button)

    def _materials(self, parent, row, name, role, caption):
        label = ttk.Label(parent, text=caption, style="Card.TLabel")
        label.grid(row=row, column=0, sticky="nw", padx=(0, 16),
                   pady=(12, 0))
        box = ttk.Frame(parent, style="Card.TFrame")
        box.grid(row=row, column=1, sticky="w", pady=(6, 0))

        choices = self.fields[name].metadata.get("choices")
        choices = list(choices() if callable(choices) else choices)
        palettes = self.palettes.get(name, {})
        buttons = []
        for i, choice in enumerate(choices):
            kwargs = {}
            if Image is not None and choice in palettes:
                image = ImageTk.PhotoImage(
                    draw_swatch(role, choice, palettes[choice]["base"],
                                (self.px(64), self.px(44))),
                    master=self.root)
                self._images.append(image)
                kwargs = {"image": image, "compound": "top"}
            button = tk.Radiobutton(
                box, text=self.material_label(choice),
                variable=self.vars[name], value=choice, indicatoron=False,
                bg=COLORS["card"], fg=COLORS["text"],
                activebackground=COLORS["accent_light"],
                selectcolor=COLORS["accent_light"], bd=0, relief="flat",
                overrelief="flat", offrelief="flat",
                highlightthickness=self.px(2),
                highlightbackground=COLORS["card"],
                highlightcolor=COLORS["accent"], padx=self.px(5),
                pady=self.px(6), font=self.fonts["small"], cursor="hand2",
                **kwargs)
            button.grid(row=0, column=i, padx=(0, self.px(5)))
            buttons.append(button)

        self.swatch_buttons[name] = buttons
        self.vars[name].trace_add("write",
                                  lambda *_, n=name: self._paint_materials(n))
        self._reg(name, label, *buttons)
        self._help(self.describe(name), label, *buttons)
        self._paint_materials(name)

    def _paint_materials(self, name):
        """Frame the chosen material."""
        if not self.built and not hasattr(self, "swatch_buttons"):
            return
        chosen = self.vars[name].get()
        for button in self.swatch_buttons.get(name, []):
            try:
                selected = button.cget("value") == chosen
                button.configure(highlightbackground=COLORS["accent"]
                                 if selected else COLORS["card"])
            except tk.TclError:
                pass

    def new_variation(self):
        self.vars["seed"].set(str(random.randint(1, 9999)))

    # ---- Doors and windows page ----

    def _build_doors_page(self):
        body = self._page("doors")
        body.columnconfigure(0, weight=1)

        door = self._card(body, self.t("card.door"), row=0)
        self._check(door, "door", 1)

        label = ttk.Label(door, text=self.t("ui.door_side"),
                          style="Card.TLabel")
        label.grid(row=2, column=0, sticky="w", padx=(0, 16), pady=(8, 2))
        self._radios(door, "door_on", 2,
                     [("short", self.t("ui.side_short")),
                      ("long", self.t("ui.side_long"))])
        self._reg("door_on", label)

        label = ttk.Label(door, text=self.t("ui.door_position"),
                          style="Card.TLabel")
        label.grid(row=3, column=0, sticky="w", padx=(0, 16), pady=(2, 2))
        self._radios(door, "door_position", 3,
                     [("center", self.t("ui.pos_center")),
                      ("left", self.t("ui.pos_left")),
                      ("right", self.t("ui.pos_right"))])
        self._reg("door_position", label)

        label = ttk.Label(door, text=self.t("ui.door_style"),
                          style="Card.TLabel")
        label.grid(row=4, column=0, sticky="w", padx=(0, 16), pady=(2, 2))
        self._radios(door, "door_style", 4,
                     [("wood", self.t("ui.dstyle_wood")),
                      ("iron", self.t("ui.dstyle_iron")),
                      ("studded", self.t("ui.dstyle_studded"))])
        self._reg("door_style", label)

        self._check(door, "one_door_per_house", 5, pady=(8, 2))
        self._check(door, "door_arched", 6)

        windows = self._card(body, self.t("card.windows"), row=1)
        self._check(windows, "windows", 1)

        label = ttk.Label(windows, text=self.t("ui.window_style"),
                          style="Card.TLabel")
        label.grid(row=2, column=0, sticky="w", padx=(0, 16), pady=(8, 2))
        self._radios(windows, "window_style", 2,
                     [("classic", self.t("ui.wstyle_classic")),
                      ("stone", self.t("ui.wstyle_stone")),
                      ("castle", self.t("ui.wstyle_castle")),
                      ("stained", self.t("ui.wstyle_stained"))])
        self._reg("window_style", label)

        self._square_row(windows, 3, "floor_height_cm", 0.5)
        label = ttk.Label(windows, text=self.t("ui.window_spacing"),
                          style="Card.TLabel")
        label.grid(row=4, column=0, sticky="w", padx=(0, 16), pady=5)
        spin = ttk.Spinbox(windows, textvariable=self.vars["window_spacing_cells"],
                           from_=0.5, to=20, increment=0.5, width=7)
        spin.grid(row=4, column=1, sticky="w", pady=5)
        self._reg("window_spacing_cells", label, spin)
        self._help(self.describe("window_spacing_cells"), label, spin)

        self._check(windows, "roof_windows", 5, pady=(12, 0))
        ttk.Label(windows, text=self.t("ui.roof_windows_hint"),
                  style="Muted.Card.TLabel").grid(
            row=6, column=0, columnspan=4, sticky="w", padx=(30, 0))
        ttk.Label(windows, text=self.t("ui.more_in_advanced"),
                  style="Muted.Card.TLabel").grid(
            row=7, column=0, columnspan=4, sticky="w", pady=(10, 0))

    # ---- Pages and files page ----

    def _build_pages_page(self):
        body = self._page("pages")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        pdf = self._card(body, self.t("card.pdf"), row=0, column=0,
                         sticky="nsew", padx=(0, 8))
        self._check(pdf, "complete_only", 1)
        ttk.Label(pdf, text=self.t("ui.complete_hint"),
                  style="Muted.Card.TLabel").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=(30, 0))
        label = ttk.Label(pdf, text=self.label_for("paper"),
                          style="Card.TLabel")
        label.grid(row=3, column=0, sticky="w", padx=(0, 16), pady=(14, 2))
        self._radios(pdf, "paper", 3, [("A4", "A4"), ("Letter", "Letter")])
        self._reg("paper", label)

        layout = self._card(body, self.t("card.layout"), row=0, column=1,
                            sticky="nsew", padx=(8, 0))
        for i, name in enumerate(("mix_pieces", "allow_rotation",
                                  "joint_labels", "calibration_ruler")):
            self._check(layout, name, i + 1)

        files = self._card(body, self.t("card.files"), row=1, column=0,
                           columnspan=2, sticky="new")
        label = ttk.Label(files, text=self.t("ui.folder"), style="Card.TLabel")
        label.grid(row=1, column=0, sticky="w", padx=(0, 16), pady=4)
        folder = ttk.Entry(files, textvariable=self.vars["output_dir"],
                           width=44)
        folder.grid(row=1, column=1, sticky="w", pady=4)
        browse = ttk.Button(files, text=self.t("ui.browse"),
                            command=self.browse_output)
        browse.grid(row=1, column=2, sticky="w", padx=(8, 0))
        self._reg("output_dir", label, folder, browse)
        self._help(self.describe("output_dir"), label, folder, browse)

        label = ttk.Label(files, text=self.t("ui.file_name"),
                          style="Card.TLabel")
        label.grid(row=2, column=0, sticky="w", padx=(0, 16), pady=4)
        name_entry = ttk.Entry(files, textvariable=self.vars["base_name"],
                               width=44)
        name_entry.grid(row=2, column=1, sticky="w", pady=4)
        self._reg("base_name", label, name_entry)
        self._help(self.describe("base_name"), label, name_entry)

    # ---- Advanced page ----

    def _build_advanced_page(self):
        inner = self._page("advanced")
        inner.columnconfigure(0, weight=1)

        groups = {}
        for f in self._fields():
            groups.setdefault(f.metadata.get("group", "House"), []).append(f)
        names = [g for g in GROUP_ORDER if g in groups]
        names += [g for g in groups if g not in GROUP_ORDER]

        row = 0
        for group in names:
            key = f"group.{group}"
            title = self.t(key) if has_text("en", key) else group
            ttk.Label(inner, text=title, style="Section.Page.TLabel").grid(
                row=row, column=0, sticky="w", pady=(4, 6))
            card = self._card(inner, None, row=row + 1, sticky="ew",
                              pady=(0, 16))
            card.columnconfigure(1, weight=1)
            for i, f in enumerate(groups[group]):
                self._advanced_field(card, i, f)
            row += 2

    def _advanced_field(self, parent, row, f):
        name, kind = f.name, self.kinds[f.name]
        variable = self.vars[name]
        description = self.describe(name)

        if kind == "bool":
            widget = ttk.Checkbutton(parent, text=self.label_for(name),
                                     variable=variable,
                                     style="Card.TCheckbutton")
            widget.grid(row=row, column=0, columnspan=3, sticky="w", pady=3)
            widgets = [widget]
        else:
            label = ttk.Label(parent, text=self.label_for(name),
                              style="Card.TLabel")
            label.grid(row=row, column=0, sticky="w", padx=(0, 16), pady=3)
            if kind == "choice":
                choices = f.metadata["choices"]
                choices = choices() if callable(choices) else choices
                widget = ttk.Combobox(parent, textvariable=variable,
                                      values=list(choices), state="readonly",
                                      width=16)
            else:
                widget = ttk.Entry(parent, textvariable=variable,
                                   width=34 if kind == "str" else 16)
            widget.grid(row=row, column=1, sticky="w", pady=3)
            widgets = [label, widget]

        self._reg(name, *widgets)
        self._help(description, *widgets)

    def _wheel(self, event):
        frame = self.scrollers.get(self.page_var.get())
        if frame is None or not str(event.widget).startswith(str(frame)):
            return
        if getattr(event, "num", None) == 4:
            lines = -3
        elif getattr(event, "num", None) == 5:
            lines = 3
        else:
            lines = -3 if event.delta > 0 else 3
        frame.scroll(lines)

    # ---- Buttons and log ----

    def _button(self, parent, key, command, icon=None, primary=False):
        color = "#ffffff" if primary else COLORS["icon"]
        image = self.icon(icon, color, 18) if icon else None
        kwargs = {"image": image, "compound": "left"} if image else {}
        return ttk.Button(parent, text=" " + self.t(key), command=command,
                          style="Primary.TButton" if primary else "TButton",
                          **kwargs)

    def _build_actions(self, parent, row):
        bar = tk.Frame(parent, bg=COLORS["bg"])
        bar.grid(row=row, column=0, sticky="ew", padx=self.px(32),
                 pady=(0, 10))
        bar.columnconfigure(3, weight=1)

        self.generate_button = self._button(bar, "ui.generate", self.start,
                                            "play", primary=True)
        self.generate_button.grid(row=0, column=0, padx=(0, 8))
        self._button(bar, "ui.open_folder", self.open_folder, "folder").grid(
            row=0, column=1, padx=4)
        self._button(bar, "ui.copy_command", self.copy_command, "copy").grid(
            row=0, column=2, padx=4)

        menu = tk.Menu(self.root, tearoff=False, bg="white",
                       fg=COLORS["text"], activebackground=COLORS["accent"],
                       activeforeground="white", bd=0,
                       font=self.fonts["base"])
        menu.add_command(label=self.t("ui.load_preset"),
                         command=self.load_preset)
        menu.add_command(label=self.t("ui.save_preset"),
                         command=self.save_preset)
        menu.add_separator()
        menu.add_command(label=self.t("ui.reset"), command=self.reset)

        image = self.icon("upload", COLORS["icon"], 18)
        kwargs = {"image": image, "compound": "left"} if image else {}
        self.presets_button = ttk.Menubutton(
            bar, text=" " + self.t("ui.presets"), menu=menu, **kwargs)
        self.presets_button.grid(row=0, column=4, padx=(4, 0))

    def _build_log(self, parent, row):
        frame = tk.Frame(parent, bg=COLORS["bg"])
        frame.grid(row=row, column=0, sticky="ew", padx=self.px(32),
                   pady=(0, self.px(22)))
        frame.columnconfigure(0, weight=1)

        self.log = tk.Text(frame, height=6, wrap="word", state="disabled",
                           font="TkFixedFont", bg=COLORS["log_bg"],
                           fg=COLORS["log_text"], bd=0, relief="flat",
                           padx=self.px(12), pady=self.px(10),
                           insertbackground=COLORS["log_text"])
        scrollbar = ttk.Scrollbar(frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="ew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    # ----------------------------------------------------------
    # Reading and writing the form
    # ----------------------------------------------------------

    def set_values(self, source):
        """Fills the form from a Config or from a dict of settings."""
        for name, var in self.vars.items():
            if isinstance(source, dict):
                if name not in source:
                    continue
                value = source[name]
            else:
                value = getattr(source, name)

            if self.kinds[name] == "bool":
                var.set(bool(value))
            else:
                var.set(format_value(value))
        self._cm_changed()

    def collect(self):
        """Returns (Config, []) or (None, [what is wrong])."""
        values, errors = {}, []
        for name, var in self.vars.items():
            kind = self.kinds[name]
            try:
                if kind == "bool":
                    values[name] = bool(var.get())
                else:
                    values[name] = parse_value(
                        kind, var.get(),
                        optional=self.fields[name].default is None,
                        language=self.language)
            except ValueError as error:
                errors.append(f"{self.label_for(name)}: {error}")

        if errors:
            return None, errors
        values["language"] = self.language
        return self.config_cls(**values), []

    def refresh(self):
        """Greys out the settings that do nothing right now."""
        if not self.built:
            return
        values = {name: self.vars[name].get() for name in (
            "generate_full_house", "textures_enabled", "generate_all_variants",
            "door", "windows", "houses", "house_shape", "roof_type",
            "roof_windows", "top_tabs", "bottom_tabs")}
        off = disabled_fields(values)

        for name, widgets in self.widgets.items():
            enabled = name not in off
            for widget in widgets:
                try:
                    if isinstance(widget, ttk.Widget):
                        widget.state(["!disabled"] if enabled else ["disabled"])
                    elif not isinstance(widget, tk.Canvas):
                        widget.configure(state="normal" if enabled
                                         else "disabled")
                except tk.TclError:
                    pass

        # The drawing of the L on the grid follows the shape
        if hasattr(self, "picker"):
            self._update_picker()

    # ----------------------------------------------------------
    # Language
    # ----------------------------------------------------------

    def change_language(self):
        new = self.lang_var.get()
        if new == self.language:
            return
        self.language = new

        saved_log = self.log.get("1.0", "end-1c")
        page = self.page_var.get()
        self.shell.destroy()
        self.help_text.set(self.t("ui.hint"))
        self.root.title(self.t("ui.title"))
        self._build_ui()
        self.show_page(page)
        self.set_running(self.running)
        if saved_log:
            self.append(saved_log)

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
            messagebox.showerror(self.t("ui.check_settings"),
                                 "\n".join(errors))
            return
        try:
            self.validate(cfg)
        except ValueError as error:
            messagebox.showerror(self.t("ui.invalid_settings"), str(error))
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
            text=" " + self.t("ui.generating" if running else "ui.generate"),
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
        self.append("\n" + self.t("ui.done", count=len(files), folder=folder)
                    + "\n")

    def failed(self, error, trace):
        self.set_running(False)
        if type(error).__name__ in ("ValueError", "OutputError"):
            self.append(f"\n{error}\n")
        else:
            self.append(f"\n{trace}\n")
        messagebox.showerror(
            self.t("ui.could_not_generate"),
            str(error) if str(error) else type(error).__name__)

    def open_folder(self):
        text = self.vars["output_dir"].get()
        path = self.resolve_dir(self.config_cls(output_dir=text))
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def browse_output(self):
        chosen = filedialog.askdirectory(title=self.t("ui.dialog_folder"))
        if chosen:
            self.vars["output_dir"].set(chosen)

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
            messagebox.showerror(self.t("ui.check_settings"),
                                 "\n".join(errors))
            return
        command = self.command_text(cfg)
        self.root.clipboard_clear()
        self.root.clipboard_append(command)
        self.append(self.t("ui.copied", command=command) + "\n")

    def save_preset(self):
        cfg, errors = self.collect()
        if errors:
            messagebox.showerror(self.t("ui.check_settings"),
                                 "\n".join(errors))
            return
        path = filedialog.asksaveasfilename(
            title=self.t("ui.dialog_save"), defaultextension=".json",
            filetypes=[(self.t("ui.preset_files"), "*.json")])
        if not path:
            return
        data = {name: getattr(cfg, name) for name in self.vars}
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.append(self.t("ui.preset_saved", path=path) + "\n")

    def load_preset(self):
        path = filedialog.askopenfilename(
            title=self.t("ui.dialog_load"),
            filetypes=[(self.t("ui.preset_files"), "*.json")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("not a preset")
        except (OSError, ValueError) as error:
            messagebox.showerror(self.t("ui.cannot_load_preset"), str(error))
            return
        self.set_values(data)
        self.append(self.t("ui.preset_loaded", path=path) + "\n")

    def reset(self):
        self.set_values(self.config_cls())
        self.append(self.t("ui.reset_done") + "\n")


def launch(config_cls, run, validate, resolve_dir, to_args, overrides=None,
           palettes=None):
    """Opens the window and waits until it is closed."""
    app = App(config_cls, run, validate, resolve_dir, to_args, overrides,
              palettes)
    app.root.mainloop()
    return app