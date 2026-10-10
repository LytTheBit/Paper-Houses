"""Paper Houses: procedural, printable paper houses for tabletop RPGs.

Draws the cutting/folding templates of a small house, sized on the
2.5 cm battle-map grid, with optional procedural textures, door and
windows. Everything is vector graphics written straight into PDFs.

Edit the defaults of `Config` below, or override them from the command
line (run `python main.py --help`).
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Callable, Optional

from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from i18n import LANGUAGES, tr


# ============================================================
# SETTINGS
# ============================================================

def _f(default, help="", choices=None, cli=True, type=None, group="House",
       gui=True):
    """Declares a setting: default value, help text, how the command line
    should treat it, the group it belongs to and whether the window shows
    it among the settings."""
    return field(default=default, metadata={
        "help": help, "choices": choices, "cli": cli, "type": type,
        "group": group, "gui": gui})


@dataclass
class Config:
    # WIDTH, LENGTH and HEIGHT are the measurements of the INNER
    # rectangle (the D&D squares, multiples of 2.5 cm).
    # The tabs (tab_width_cm) are added on the outside.

    # --- House: sizes ---
    generate_full_house: bool = _f(
        True, "generate the whole house (4 PDFs) instead of a single wall")
    width_cm: float = _f(7.5, "short side of the house (the one with the gable)")
    length_cm: float = _f(12.5, "long side of the house")
    height_cm: float = _f(7.5, "wall height (same for both sides)")
    tab_width_cm: float = _f(1.0, "width of the tabs around the inner rectangle")
    roof_height_cm: float = _f(5.0, "height of the roof gable (triangle)")
    roof_flap_cm: float = _f(1.0, "width of the flaps on the roof gable")
    roof_overhang_cm: float = _f(
        0.5, "how far the roof slope extends beyond the gable side")
    roof_margin_cm: float = _f(
        1.0, "extra margin added on every side of the roof sheet")
    use_roof: bool = _f(True, "single-wall mode only: draw the roof gable")

    # --- Look: lines and textures ---
    textures_enabled: bool = _f(
        False, "paint textures (otherwise only lines)", group="Look")
    wall_material: str = _f(
        "wood", "wall material", choices=lambda: list(WALL_PALETTES),
        group="Look")
    roof_material: str = _f(
        "thatch", "roof material", choices=lambda: list(ROOF_PALETTES),
        group="Look")
    generate_all_variants: bool = _f(
        False, "generate every wall/roof material combination", group="Look")
    seed: int = _f(
        7, "different seed, different variation of the textures", group="Look")
    texture_on_roof_overhang: bool = _f(
        True, "texture also covers the extra margin of the roof sheet",
        group="Look")
    reuse_textures: bool = _f(
        True, "draw each texture once per PDF and reuse it for every copy "
              "(smaller, faster files)", group="Look")
    line_width: float = _f(0.5, "line width in points", group="Look")
    draw_roof_base: bool = _f(
        False, "also draw the base of the gable triangle (fold line)",
        group="Look")
    line_color: tuple = _f((0, 0, 0), "colour of fold/cut lines", cli=False)
    dash: tuple = _f((3, 3), "dash pattern (dash, gap) in points", cli=False)
    marker_color: tuple = _f(
        (0.85, 0.10, 0.10),
        "preferred colour of the half-height mark on the side tabs "
        "(black or white is used instead when it would be hard to see)",
        cli=False)

    # --- Door and windows ---
    door_and_windows: bool = _f(
        True, "draw door and windows", group="Door & windows")
    door_on: str = _f("short", "side of the house with the door",
                      choices=["short", "long"], group="Door & windows")
    one_door_per_house: bool = _f(
        True, "only one wall per house gets the door (the other gets a "
              "window in its place)", group="Door & windows")
    door_arched: bool = _f(
        True, "door with a rounded top", group="Door & windows")
    door_width_min_m: float = _f(
        1.0, "door width on a 3-square wall", group="Door & windows")
    door_width_max_m: float = _f(
        1.5, "door width on a 5-square wall or more", group="Door & windows")
    door_height_m: float = _f(2.0, "door height", group="Door & windows")
    window_width_m: float = _f(0.8, "window width", group="Door & windows")
    window_height_m: float = _f(0.9, "window height", group="Door & windows")
    window_sill_m: float = _f(
        1.0, "height of the window sill above the ground", group="Door & windows")
    round_window_radius_m: float = _f(
        0.35, "radius of the small window in the gable", group="Door & windows")
    floor_height_cm: float = _f(
        5.0, "one floor of windows for every this many cm of wall height",
        group="Door & windows")
    window_spacing_cells: float = _f(
        2.0, "target distance between windows, in game squares "
             "(lower: more windows)", group="Door & windows")
    cell_cm: float = _f(
        2.5, "side of a game square", group="Door & windows")
    meters_per_cell: float = _f(
        1.5, "size of a game square in the fiction", group="Door & windows")

    # --- Pages and output ---
    complete_only: bool = _f(
        True, "write only the complete PDF, not the PDFs of the single "
              "pieces", group="Pages & output")
    paper: str = _f("A4", "paper size of the complete PDF",
                    choices=lambda: list(PAPER_SIZES), group="Pages & output")
    houses: Optional[int] = _f(
        None, "number of houses to print. Without it, every page is "
              "filled with as many copies of one piece as fit",
        type=int, group="Pages & output")
    mix_pieces: bool = _f(
        False, "needs a number of houses: pack different pieces on the "
               "same page to save paper", group="Pages & output")
    allow_rotation: bool = _f(
        True, "allow rotating pieces by 90 degrees", group="Pages & output")
    joint_labels: bool = _f(
        True, "write corner letters on the side tabs: tabs with the same "
              "letter go together", group="Pages & output")
    calibration_ruler: bool = _f(
        True, "draw a 5 cm ruler on every page of the complete PDF, to "
              "check the print scale", group="Pages & output")
    page_margin_cm: float = _f(
        0.5, "white margin along the edges of the page", group="Pages & output")
    copy_gap_cm: float = _f(
        0.5, "gap between two pieces", group="Pages & output")
    output_dir: str = _f(
        "output", "folder for the PDFs (relative to this script)",
        group="Pages & output")
    base_name: str = _f(
        "house_DnD", "base name of the PDFs", group="Pages & output")
    language: str = _f(
        "en", "language of the messages and of the window",
        choices=lambda: list(LANGUAGES), group="Pages & output", gui=False)


# ============================================================
# COLOURS
# ============================================================

FRAME = (0.30, 0.20, 0.12)
GLASS = (0.70, 0.85, 0.95)
GLINT = (0.93, 0.97, 1.00)
DOOR_PLANKS = (0.42, 0.26, 0.13)
BRASS = (0.88, 0.72, 0.27)
DARK_OUTLINE = (0.15, 0.10, 0.05)

# Frame thickness of windows and door, in cm
WINDOW_FRAME_CM = 0.10
DOOR_FRAME_CM = 0.12

# Shade of each door plank (slightly different, for a wooden look)
PLANK_SHADES = (1.00, 0.90, 1.06, 0.95)

PAPER_SIZES = {"A4": A4, "Letter": letter}

# Space reserved at the bottom of the page for the calibration ruler
RULER_STRIP_CM = 1.0


# ============================================================
# UTILITIES
# ============================================================

def meters(cfg, m):
    """Converts metres of the fiction into PDF points
    (by default 2.5 cm = 1.5 m)."""
    return m * (cfg.cell_cm / cfg.meters_per_cell) * cm


def vary(color, rnd, amplitude):
    """Lightens or darkens a colour by a random amount."""
    f = 1 + rnd.uniform(-amplitude, amplitude)
    return tuple(max(0.0, min(1.0, v * f)) for v in color)


def darken(color, factor):
    return tuple(max(0.0, min(1.0, v * factor)) for v in color)


def _linear(v):
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminance(color):
    r, g, b = (_linear(v) for v in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable_on(base, preferred, minimum=3.0):
    """Returns `preferred` if it is easy to see on `base`, otherwise
    black or white, whichever contrasts more."""
    if contrast_ratio(base, preferred) >= minimum:
        return preferred
    return max(((0, 0, 0), (1, 1, 1)),
               key=lambda color: contrast_ratio(base, color))


def fill_path(c, path, color):
    """Fills a path; the stroke in the same colour avoids thin
    white gaps between adjacent areas."""
    c.setFillColorRGB(*color)
    c.setStrokeColorRGB(*color)
    c.setLineWidth(0.5)
    c.drawPath(path, stroke=1, fill=1)


def polygon(c, points):
    p = c.beginPath()
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    p.close()
    return p


def validate(cfg):
    """Raises ValueError with a readable message if a setting is wrong."""
    def t(key, **values):
        return tr(cfg.language, key, **values)

    errors = []

    if cfg.language not in LANGUAGES:
        errors.append(t("err.language", options=list(LANGUAGES),
                        value=cfg.language))
    if cfg.wall_material not in WALL_PALETTES:
        errors.append(t("err.wall_material", options=list(WALL_PALETTES),
                        value=cfg.wall_material))
    if cfg.roof_material not in ROOF_PALETTES:
        errors.append(t("err.roof_material", options=list(ROOF_PALETTES),
                        value=cfg.roof_material))
    if cfg.door_on not in ("short", "long"):
        errors.append(t("err.door_on", value=cfg.door_on))
    if cfg.paper not in PAPER_SIZES:
        errors.append(t("err.paper", options=list(PAPER_SIZES),
                        value=cfg.paper))
    if cfg.houses is not None and cfg.houses < 1:
        errors.append(t("err.houses", value=cfg.houses))

    for name in ("width_cm", "length_cm", "height_cm", "tab_width_cm",
                 "roof_height_cm", "cell_cm", "meters_per_cell",
                 "floor_height_cm", "window_spacing_cells"):
        if getattr(cfg, name) <= 0:
            errors.append(t("err.positive", name=name,
                            value=getattr(cfg, name)))

    if errors:
        raise ValueError("\n".join(errors))


def check_settings(cfg):
    """Returns a warning for every setting that has no effect because
    of another one."""
    warnings = []
    if cfg.mix_pieces and cfg.houses is None:
        warnings.append(tr(cfg.language, "msg.warn_mix"))
    if cfg.generate_all_variants and not cfg.textures_enabled:
        warnings.append(tr(cfg.language, "msg.warn_variants"))
    return warnings


def check_dimensions(cfg):
    """Returns a warning for every measurement that is not a multiple
    of a game square."""
    dimensions = [("width_cm", cfg.width_cm), ("height_cm", cfg.height_cm)]
    if cfg.generate_full_house:
        dimensions.append(("length_cm", cfg.length_cm))

    warnings = []
    for name, value in dimensions:
        squares = value / cfg.cell_cm
        if abs(squares - round(squares)) > 1e-6:
            warnings.append(tr(cfg.language, "msg.warn_dimension",
                               name=name, value=value, cell=cfg.cell_cm,
                               squares=squares))
    return warnings


# ============================================================
# WALL TEXTURES
# Each one fills the rectangle (x0, y0)-(x1, y1);
# clipping to the exact shape is done by the caller.
# To add a material, write a function and register it with
# @wall_texture("name", base=(r, g, b), ...).
# ============================================================

WALL_TEXTURES = {}
WALL_PALETTES = {}


def wall_texture(name, **palette):
    def register(function):
        WALL_TEXTURES[name] = function
        WALL_PALETTES[name] = palette
        return function
    return register


@wall_texture("brick", base=(0.60, 0.25, 0.20), mortar=(0.82, 0.79, 0.72))
def texture_brick(c, x0, y0, x1, y1, pal, rnd):
    c.setFillColorRGB(*pal["mortar"])
    c.rect(x0, y0, x1 - x0, y1 - y0, stroke=0, fill=1)

    bw = 1.1 * cm
    bh = 0.45 * cm
    gap = 0.06 * cm

    row = 0
    y = y0
    while y < y1:
        x = x0 - (bw / 2 if row % 2 else 0)
        while x < x1:
            col = vary(pal["base"], rnd, 0.14)
            c.setFillColorRGB(*col)
            c.rect(x + gap / 2, y + gap / 2, bw - gap, bh - gap,
                   stroke=0, fill=1)

            # Small speckles on the brick
            c.setFillColorRGB(*vary(col, rnd, 0.3))
            for _ in range(2):
                c.circle(x + rnd.uniform(0.1, 0.9) * bw,
                         y + rnd.uniform(0.2, 0.8) * bh,
                         0.02 * cm, stroke=0, fill=1)
            x += bw
        y += bh
        row += 1


@wall_texture("stone", base=(0.58, 0.58, 0.58), mortar=(0.30, 0.30, 0.30))
def texture_stone(c, x0, y0, x1, y1, pal, rnd):
    c.setFillColorRGB(*pal["mortar"])
    c.rect(x0, y0, x1 - x0, y1 - y0, stroke=0, fill=1)

    gap = 0.06 * cm

    y = y0
    while y < y1:
        height = rnd.uniform(0.55, 0.95) * cm
        x = x0 - rnd.uniform(0.0, 1.0) * cm
        while x < x1:
            width = rnd.uniform(0.8, 1.6) * cm

            col = vary(pal["base"], rnd, 0.18)
            col = tuple(max(0.0, min(1.0, v + rnd.uniform(-0.03, 0.03)))
                        for v in col)
            c.setFillColorRGB(*col)
            radius = min(0.16 * cm, (height - gap) / 2.2)
            c.roundRect(x + gap / 2, y + gap / 2,
                        width - gap, height - gap, radius,
                        stroke=0, fill=1)

            # Small pits
            c.setFillColorRGB(*darken(col, 0.7))
            for _ in range(3):
                c.circle(x + rnd.uniform(0.15, 0.85) * width,
                         y + rnd.uniform(0.2, 0.8) * height,
                         rnd.uniform(0.01, 0.03) * cm, stroke=0, fill=1)
            x += width
        y += height


@wall_texture("wood", base=(0.55, 0.37, 0.21))
def texture_wood_wall(c, x0, y0, x1, y1, pal, rnd):
    """HORIZONTAL planks, with grain, knots and joints."""
    plank_height = 0.6 * cm
    width = x1 - x0

    y = y0
    while y < y1:
        col = vary(pal["base"], rnd, 0.13)
        c.setFillColorRGB(*col)
        c.rect(x0, y, width, plank_height, stroke=0, fill=1)

        # Grain (along the plank, so horizontal)
        c.setStrokeColorRGB(*darken(col, 0.78))
        c.setLineWidth(0.3)
        for _ in range(rnd.randint(2, 4)):
            gy = y + rnd.uniform(0.15, 0.85) * plank_height
            c.bezier(x0, gy,
                     x0 + width / 3,
                     gy + rnd.uniform(-1, 1) * 0.06 * cm,
                     x0 + 2 * width / 3,
                     gy + rnd.uniform(-1, 1) * 0.06 * cm,
                     x1, gy)

        # Knot
        if rnd.random() < 0.45:
            kx = x0 + rnd.uniform(0.1, 0.9) * width
            ky = y + rnd.uniform(0.3, 0.7) * plank_height
            c.setFillColorRGB(*darken(col, 0.65))
            c.ellipse(kx - 0.12 * cm, ky - 0.07 * cm,
                      kx + 0.12 * cm, ky + 0.07 * cm, stroke=0, fill=1)

        # Joint between two consecutive planks (vertical cut)
        if rnd.random() < 0.6:
            jx = x0 + rnd.uniform(0.15, 0.85) * width
            c.setStrokeColorRGB(*darken(col, 0.55))
            c.setLineWidth(0.5)
            c.line(jx, y, jx, y + plank_height)

        # Gap between one plank and the next
        c.setStrokeColorRGB(*darken(pal["base"], 0.45))
        c.setLineWidth(0.7)
        c.line(x0, y, x1, y)

        y += plank_height


# ============================================================
# ROOF TEXTURES
# Drawn in a local system where the eaves are at y = 0
# and the ridge at y = d. The same function is used for both
# slopes (the second one is mirrored).
# ============================================================

ROOF_TEXTURES = {}
ROOF_PALETTES = {}


def roof_texture(name, **palette):
    def register(function):
        ROOF_TEXTURES[name] = function
        ROOF_PALETTES[name] = palette
        return function
    return register


def _element_rows(c, w, d, pal, rnd, tw, rh, length, curved, amplitude):
    """Rows of tiles (curved) or shingles (straight), from the eaves
    to the ridge: each higher row covers the top of the one below."""

    # Dark background: visible in the gaps between elements
    c.setFillColorRGB(*darken(pal["base"], 0.5))
    c.rect(0, 0, w, d, stroke=0, fill=1)

    rad = 0.3 * cm
    row = 0
    while row * rh < d:
        yb = row * rh
        x = -(tw / 2 if row % 2 else 0)
        while x < w:
            col = vary(pal["base"], rnd, amplitude)

            p = c.beginPath()
            if curved:
                p.moveTo(x, yb + length)
                p.lineTo(x, yb + rad)
                p.curveTo(x, yb - 0.35 * rad,
                          x + tw, yb - 0.35 * rad,
                          x + tw, yb + rad)
                p.lineTo(x + tw, yb + length)
                p.close()
            else:
                p.rect(x, yb, tw, length)

            c.setFillColorRGB(*col)
            c.setStrokeColorRGB(*darken(col, 0.55))
            c.setLineWidth(0.4)
            c.drawPath(p, stroke=1, fill=1)

            if not curved:
                # Shingle grain
                c.setStrokeColorRGB(*darken(col, 0.75))
                c.setLineWidth(0.3)
                gx = x + rnd.uniform(0.2, 0.8) * tw
                c.line(gx, yb + 0.05 * cm, gx, yb + rh * 0.9)

            x += tw
        row += 1


@roof_texture("tiles", base=(0.78, 0.38, 0.20))
def texture_roof_tiles(c, w, d, pal, rnd):
    _element_rows(c, w, d, pal, rnd,
                  tw=0.9 * cm, rh=0.55 * cm, length=1.3 * cm,
                  curved=True, amplitude=0.12)


@roof_texture("wood", base=(0.42, 0.28, 0.16))
def texture_roof_wood(c, w, d, pal, rnd):
    _element_rows(c, w, d, pal, rnd,
                  tw=0.75 * cm, rh=0.6 * cm, length=0.9 * cm,
                  curved=False, amplitude=0.16)


@roof_texture("thatch", base=(0.86, 0.71, 0.34))
def texture_roof_thatch(c, w, d, pal, rnd):
    bh = 0.9 * cm
    row = 0
    while row * bh < d:
        yb = row * bh

        # Band of thatch
        c.setFillColorRGB(*vary(pal["base"], rnd, 0.08))
        c.rect(0, yb, w, bh * 1.8, stroke=0, fill=1)

        # Straw strands
        n = int((w / cm) * (bh / cm) * 30)
        for _ in range(n):
            x = rnd.uniform(0, w)
            y = rnd.uniform(yb, yb + bh * 1.6)
            length = rnd.uniform(0.5, 1.0) * cm
            ang = rnd.uniform(-0.12, 0.12)
            c.setStrokeColorRGB(*vary(pal["base"], rnd, 0.22))
            c.setLineWidth(rnd.uniform(0.3, 0.7))
            c.line(x, y, x + math.sin(ang) * length,
                   y + math.cos(ang) * length)

        # Irregular edge at the bottom of the band
        c.setStrokeColorRGB(*darken(pal["base"], 0.55))
        c.setLineWidth(0.8)
        p = c.beginPath()
        x = 0.0
        p.moveTo(x, yb)
        while x < w:
            x += 0.1 * cm
            p.lineTo(x, yb + rnd.uniform(-0.05, 0.05) * cm)
        c.drawPath(p, stroke=1, fill=0)

        row += 1


# ============================================================
# DOOR AND WINDOWS
# ============================================================

def _glint(c, x0, y0, x1, y1):
    """Small diagonal highlight in a window pane."""
    pw, ph = x1 - x0, y1 - y0
    c.setStrokeColorRGB(*GLINT)
    c.setLineWidth(0.6)
    c.line(x0 + 0.18 * pw, y0 + 0.55 * ph, x0 + 0.42 * pw, y0 + 0.85 * ph)


def window(c, cx, cy, w, h):
    f = WINDOW_FRAME_CM * cm

    # Sill, wider than the window
    c.setFillColorRGB(*FRAME)
    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.3)
    c.rect(cx - w / 2 - 0.09 * cm, cy - h / 2 - 0.11 * cm,
           w + 0.18 * cm, 0.11 * cm, stroke=1, fill=1)

    # Frame
    c.setLineWidth(0.4)
    c.rect(cx - w / 2, cy - h / 2, w, h, stroke=1, fill=1)

    # Glass
    gx0, gx1 = cx - w / 2 + f, cx + w / 2 - f
    gy0, gy1 = cy - h / 2 + f, cy + h / 2 - f
    c.setFillColorRGB(*GLASS)
    c.rect(gx0, gy0, gx1 - gx0, gy1 - gy0, stroke=0, fill=1)

    # Highlights in each of the four panes
    for px0, px1 in ((gx0, cx), (cx, gx1)):
        for py0, py1 in ((gy0, cy), (cy, gy1)):
            _glint(c, px0, py0, px1, py1)

    # Cross
    c.setStrokeColorRGB(*FRAME)
    c.setLineWidth(1.3)
    c.line(cx, cy - h / 2, cx, cy + h / 2)
    c.line(cx - w / 2, cy, cx + w / 2, cy)


def round_window(c, cx, cy, r):
    f = WINDOW_FRAME_CM * cm

    c.setFillColorRGB(*FRAME)
    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.4)
    c.circle(cx, cy, r, stroke=1, fill=1)

    c.setFillColorRGB(*GLASS)
    c.circle(cx, cy, r - f, stroke=0, fill=1)

    _glint(c, cx - r + f, cy - r + f, cx + r - f, cy + r - f)

    c.setStrokeColorRGB(*FRAME)
    c.setLineWidth(1.3)
    c.line(cx - r, cy, cx + r, cy)
    c.line(cx, cy - r, cx, cy + r)


def _door_path(c, cx, y, w, h, grow, arched):
    """Outline of the door, optionally enlarged by `grow` on the
    left, right and top (used for the frame)."""
    x = cx - w / 2 - grow
    ww = w + 2 * grow

    p = c.beginPath()
    if arched and h > w / 2:
        r = ww / 2
        yc = y + h - w / 2          # height of the centre of the arch
        p.moveTo(x, y)
        p.lineTo(x, yc)
        p.arcTo(x, yc - r, x + ww, yc + r, 180, -180)
        p.lineTo(x + ww, y)
        p.close()
    else:
        p.rect(x, y, ww, h + grow)
    return p


def door(c, cx, y, w, h, arched):
    f = DOOR_FRAME_CM * cm
    x0 = cx - w / 2

    # Frame, a little larger than the door
    c.setFillColorRGB(*FRAME)
    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.4)
    c.drawPath(_door_path(c, cx, y, w, h, f, arched), stroke=1, fill=1)

    # Planks: clipped to the door shape, so they run up to the very
    # top, even inside the arch
    leaf = _door_path(c, cx, y, w, h, 0, arched)
    c.saveState()
    c.clipPath(leaf, stroke=0, fill=0)

    n = len(PLANK_SHADES)
    pw = w / n
    top = y + h + f
    for k in range(n):
        c.setFillColorRGB(*darken(DOOR_PLANKS, PLANK_SHADES[k]))
        c.rect(x0 + k * pw, y, pw, top - y, stroke=0, fill=1)

    c.setStrokeColorRGB(*darken(DOOR_PLANKS, 0.55))
    c.setLineWidth(0.5)
    for k in range(1, n):
        c.line(x0 + k * pw, y, x0 + k * pw, top)
    c.restoreState()

    # Outline of the door leaf
    c.setStrokeColorRGB(*darken(FRAME, 0.6))
    c.setLineWidth(0.6)
    c.drawPath(leaf, stroke=1, fill=0)

    # Hinges on the left
    c.setFillColorRGB(*darken(FRAME, 0.55))
    for t in (0.22, 0.62):
        c.rect(x0 + 0.02 * cm, y + h * t, 0.24 * cm, 0.075 * cm,
               stroke=0, fill=1)

    # Handle: backplate, bigger knob and a small highlight
    hx = cx + w * 0.30
    hy = y + h * 0.42
    c.setFillColorRGB(*darken(BRASS, 0.55))
    c.circle(hx, hy, 0.105 * cm, stroke=0, fill=1)
    c.setFillColorRGB(*BRASS)
    c.circle(hx, hy, 0.078 * cm, stroke=0, fill=1)
    c.setFillColorRGB(1.0, 0.95, 0.72)
    c.circle(hx - 0.022 * cm, hy + 0.024 * cm, 0.026 * cm,
             stroke=0, fill=1)


def door_width(cfg, width_cm):
    """Door width (in points) based on the wall:
    door_width_min_m with 3 squares, door_width_max_m with 5 or more."""
    squares = width_cm / cfg.cell_cm
    t = max(0.0, min(1.0, (squares - 3) / 2))
    return meters(cfg, cfg.door_width_min_m
                  + t * (cfg.door_width_max_m - cfg.door_width_min_m))


def opening_positions(cfg, width_cm, door_layout, door_present):
    """
    Returns [(type, offset from the centre in points)].

    The openings are spread evenly: the wall is split into k equal bays
    and every bay gets one opening. k is odd, so there is always an
    opening in the centre: the door on the wall with the door (a window
    if the door is missing), a window on the other walls. The windows
    end up about `window_spacing_cells` squares apart; if they would not
    fit, k shrinks. Both kinds of wall get the same number of openings.
    """
    width = width_cm * cm
    squares = width_cm / cfg.cell_cm
    window_w = meters(cfg, cfg.window_width_m)
    margin = 0.3 * cm

    centre_w = max(window_w, door_width(cfg, width_cm)) if door_layout \
        else window_w
    min_bay = max(centre_w / 2 + window_w / 2 + margin,   # next to the centre
                  window_w + 2 * margin)                  # next to the edge

    k = 1 + 2 * int(squares / (2 * cfg.window_spacing_cells) + 0.5)
    while k > 1 and width / k < min_bay:
        k -= 2

    bay = width / k
    centre = (k - 1) // 2

    out = []
    for i in range(k):
        off = (i - centre) * bay
        if i == centre and door_layout and door_present:
            out.append(("door", off))
        else:
            out.append(("window", off))
    return out


def floors_for(cfg, height_cm):
    """Number of floors of windows: one for every `floor_height_cm`
    of wall height, and at least one."""
    return max(1, int(height_cm / cfg.floor_height_cm + 1e-9))


def openings_for(cfg, width_cm, height_cm, door_layout, door_present):
    """
    Returns [(type, offset from the centre in points, floor)].

    The ground floor has the door (if any) and its windows. The upper
    floors repeat the same columns, with a window where the door is.
    """
    ground = opening_positions(cfg, width_cm, door_layout, door_present)
    upper = opening_positions(cfg, width_cm, door_layout, False)

    result = [(kind, off, 0) for kind, off in ground]
    for floor in range(1, floors_for(cfg, height_cm)):
        result += [(kind, off, floor) for kind, off in upper]
    return result


def draw_openings(cfg, c, x1, y1, width_cm, height_cm,
                  door_layout, door_present):
    cx0 = x1 + width_cm * cm / 2
    floor_height = height_cm * cm / floors_for(cfg, height_cm)

    for kind, off, floor in openings_for(cfg, width_cm, height_cm,
                                         door_layout, door_present):
        cx = cx0 + off
        base = y1 + floor * floor_height

        if kind == "door":
            h = min(meters(cfg, cfg.door_height_m), floor_height - 0.4 * cm)
            door(c, cx, base, door_width(cfg, width_cm), h, cfg.door_arched)
        else:
            wh = min(meters(cfg, cfg.window_height_m), floor_height * 0.6)
            sill = min(meters(cfg, cfg.window_sill_m),
                       floor_height - wh - 0.2 * cm)
            window(c, cx, base + sill + wh / 2,
                   meters(cfg, cfg.window_width_m), wh)


# ============================================================
# GEOMETRY
# ============================================================

def outward_parallel(x1, y1, x2, y2, distance):
    """
    Returns the endpoints of the parallel line
    shifted towards the outside of the triangle.
    """

    dx = x2 - x1
    dy = y2 - y1

    length = math.sqrt(dx**2 + dy**2)

    # Normal vector
    nx = -dy / length
    ny = dx / length

    return (
        x1 + nx * distance,
        y1 + ny * distance,
        x2 + nx * distance,
        y2 + ny * distance
    )


def slope_side_cm(cfg, inner_width_cm):
    """Length (in cm) of the sloping side of the triangle.
    The base of the triangle is the inner width."""
    return math.hypot(inner_width_cm / 2, cfg.roof_height_cm)


# ============================================================
# PIECES
#
# A Piece knows its size and how to draw itself with the
# bottom-left corner of its bounding box at the origin (0, 0),
# so it can be placed anywhere (single sheet or full page).
#   body(c, door_present)   colours, textures, door, windows
#   outline(c, labels)      fold/cut lines, tab marks and letters
# An Item is one physical copy of a piece on paper.
# ============================================================

@dataclass(frozen=True)
class Piece:
    name: str
    role: str                   # "short" | "long" | "roof" | "wall"
    width: float                # points
    height: float               # points
    body: Callable
    outline: Callable
    has_door: bool = False
    per_house: int = 1          # copies needed for one house


@dataclass(frozen=True)
class Item:
    piece: Piece
    door: bool = True
    labels: Optional[tuple] = None      # (left tab, right tab)


# Corner letters, going around the house: tabs with the same letter
# are glued together. Keys are (role, wall index within the house).
JOINTS = {
    ("short", 0): ("D", "A"),
    ("long", 0): ("A", "B"),
    ("short", 1): ("B", "C"),
    ("long", 1): ("C", "D"),
}


def wall_piece(cfg, name, role, width_cm, height_cm, with_roof,
               has_door, material, seed_id, per_house=2):
    """
    width_cm and height_cm are the INNER measurements.

    Convention:
      - solid line  = fold
      - dashed line = cut

    Base colour on tabs and flaps, texture only inside the solid
    lines. The corners between two tabs stay white (they are cut away).
    """

    B = cfg.tab_width_cm * cm
    ROOF_H = cfg.roof_height_cm * cm
    FLAP = cfg.roof_flap_cm * cm

    # Size of the outer rectangle (inner + tabs)
    W = width_cm * cm + 2 * B
    H = height_cm * cm + 2 * B

    # Inner rectangle
    x1 = B
    x2 = W - B
    y1 = B
    y2 = H - B

    # --------------------------------------------------------
    # Roof geometry and bounding box size
    # --------------------------------------------------------

    if with_roof:
        # The base of the triangle coincides with the top side
        # of the inner rectangle.
        base_left = x1
        base_right = x2
        base_y = y2

        apex_x = (base_left + base_right) / 2
        apex_y = base_y + ROOF_H

        # Flaps: parallel to the two sloping sides
        flap_left = outward_parallel(
            base_left, base_y, apex_x, apex_y, FLAP)
        flap_right = outward_parallel(
            apex_x, apex_y, base_right, base_y, FLAP)

        # The drawing ends where the roof border ends
        points_x = [0, W, flap_left[0], flap_left[2],
                    flap_right[0], flap_right[2], apex_x]
        points_y = [0, apex_y, flap_left[1], flap_left[3],
                    flap_right[1], flap_right[3]]

        # If the flaps stick out on the left, shift everything
        offset_x = -min(0, min(points_x))
        bbox_w = max(points_x) + offset_x
        bbox_h = max(points_y)
    else:
        offset_x = 0
        bbox_w = W
        bbox_h = H

    palette = WALL_PALETTES[material] if cfg.textures_enabled else None
    tab_color = palette["base"] if palette else (1, 1, 1)
    marker_color = readable_on(tab_color, cfg.marker_color)
    text_color = readable_on(tab_color, (0, 0, 0), minimum=4.5)

    # --------------------------------------------------------
    # Body: colours, texture, door and windows
    # --------------------------------------------------------

    def body(c, door_present=True):
        if palette is None:
            return

        c.saveState()
        c.translate(offset_x, 0)

        rnd = random.Random(f"{cfg.seed}/{seed_id}/{material}")

        # Base colour: central band (side tabs + inner rectangle) and
        # bottom tab (and top tab without roof). Corners stay white.
        if with_roof:
            zones = [(x1, 0, x2, y1), (0, y1, W, y2)]
        else:
            zones = [(x1, 0, x2, H), (0, y1, W, y2)]

        for xa, ya, xb, yb in zones:
            fill_path(c, polygon(c, [(xa, ya), (xb, ya),
                                     (xb, yb), (xa, yb)]),
                      palette["base"])

        if with_roof:
            # Triangle and flaps
            fill_path(c, polygon(c, [(base_left, base_y),
                                     (base_right, base_y),
                                     (apex_x, apex_y)]),
                      palette["base"])
            fill_path(c, polygon(c, [(base_left, base_y),
                                     (flap_left[0], flap_left[1]),
                                     (flap_left[2], flap_left[3]),
                                     (apex_x, apex_y)]),
                      palette["base"])
            fill_path(c, polygon(c, [(apex_x, apex_y),
                                     (flap_right[0], flap_right[1]),
                                     (flap_right[2], flap_right[3]),
                                     (base_right, base_y)]),
                      palette["base"])

        # Texture, clipped inside the solid lines
        c.saveState()
        area = c.beginPath()
        area.moveTo(x1, y1)
        area.lineTo(x2, y1)
        area.lineTo(x2, y2)
        if with_roof:
            area.lineTo(apex_x, apex_y)
        area.lineTo(x1, y2)
        area.close()
        c.clipPath(area, stroke=0, fill=0)

        top_y = apex_y if with_roof else y2
        WALL_TEXTURES[material](c, x1, y1, x2, top_y, palette, rnd)
        c.restoreState()

        # Door and windows
        if cfg.door_and_windows:
            draw_openings(cfg, c, x1, y1, width_cm, height_cm,
                          has_door, door_present)
            if with_roof:
                # Small round window in the gable
                radius = min(meters(cfg, cfg.round_window_radius_m),
                             0.3 * ROOF_H)
                round_window(c, apex_x, base_y + 0.4 * ROOF_H, radius)

        c.restoreState()

    # --------------------------------------------------------
    # Outline: lines, tab marks and corner letters
    # --------------------------------------------------------

    def outline(c, labels=None):
        c.saveState()
        c.translate(offset_x, 0)

        c.setStrokeColorRGB(*cfg.line_color)
        c.setLineWidth(cfg.line_width)

        # Outer outline (DASHED: it is the cut). It has a cross
        # shape: the corners between two tabs are removed.
        c.setDash(*cfg.dash)

        p = c.beginPath()
        if with_roof:
            # No top edge: the roof is there
            p.moveTo(0, y2)
            p.lineTo(0, y1)
            p.lineTo(x1, y1)
            p.lineTo(x1, 0)
            p.lineTo(x2, 0)
            p.lineTo(x2, y1)
            p.lineTo(W, y1)
            p.lineTo(W, y2)
            c.drawPath(p, stroke=1, fill=0)

            # Top side of the side tabs
            c.line(0, y2, x1, y2)
            c.line(x2, y2, W, y2)
        else:
            p.moveTo(x1, H)
            p.lineTo(x1, y2)
            p.lineTo(0, y2)
            p.lineTo(0, y1)
            p.lineTo(x1, y1)
            p.lineTo(x1, 0)
            p.lineTo(x2, 0)
            p.lineTo(x2, y1)
            p.lineTo(W, y1)
            p.lineTo(W, y2)
            p.lineTo(x2, y2)
            p.lineTo(x2, H)
            p.close()
            c.drawPath(p, stroke=1, fill=0)

        # Mark at half height of the side tabs
        # (where to cut for the interlocking joint)
        ym = (y1 + y2) / 2
        c.setStrokeColorRGB(*marker_color)
        c.line(0, ym, x1, ym)
        c.line(x2, ym, W, ym)
        c.setStrokeColorRGB(*cfg.line_color)

        # Corner letters on the side tabs
        if labels:
            c.setFillColorRGB(*text_color)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x1 / 2, ym + 0.22 * cm, labels[0])
            c.drawCentredString((x2 + W) / 2, ym + 0.22 * cm, labels[1])

        # Inner rectangle (solid)
        c.setDash()

        p = c.beginPath()
        if with_roof:
            # Top side omitted: the roof is there
            p.moveTo(x1, y2)
            p.lineTo(x1, y1)
            p.lineTo(x2, y1)
            p.lineTo(x2, y2)
        else:
            p.rect(x1, y1, x2 - x1, y2 - y1)
        c.drawPath(p, stroke=1, fill=0)

        # Roof
        if with_roof:

            # Main triangle (solid)
            c.line(base_left, base_y, apex_x, apex_y)
            c.line(apex_x, apex_y, base_right, base_y)

            if cfg.draw_roof_base:
                c.line(base_left, base_y, base_right, base_y)

            # Flaps (dashed)
            c.setDash(*cfg.dash)

            # Left flap
            c.line(*flap_left)                                        # outer side
            c.line(base_left, base_y, flap_left[0], flap_left[1])     # closing at the base
            c.line(apex_x, apex_y, flap_left[2], flap_left[3])        # closing at the apex

            # Right flap
            c.line(*flap_right)                                       # outer side
            c.line(apex_x, apex_y, flap_right[0], flap_right[1])      # closing at the apex
            c.line(base_right, base_y, flap_right[2], flap_right[3])  # closing at the base

        c.restoreState()

    return Piece(name, role, bbox_w, bbox_h, body, outline,
                 has_door=has_door, per_house=per_house)


def roof_piece(cfg, material, seed_id):
    """
    Rectangular sheet with two equal slopes.
      - dashed outer border (cut)
      - ridge in the middle, solid line (fold)

    Base size (from the walls):
      - length = inner length of the long wall
      - each slope = sloping side of the triangle + overhang
    The sheet is then enlarged by roof_margin_cm on every side.
    """

    side = slope_side_cm(cfg, cfg.width_cm)
    slope = side + cfg.roof_overhang_cm

    Wr = (cfg.length_cm + 2 * cfg.roof_margin_cm) * cm
    Hr = (2 * slope + 2 * cfg.roof_margin_cm) * cm

    palette = ROOF_PALETTES[material] if cfg.textures_enabled else None

    def body(c, door_present=True):
        if palette is None:
            return

        c.saveState()
        rnd = random.Random(f"{cfg.seed}/{seed_id}/{material}")

        # Base colour over the whole sheet
        fill_path(c, polygon(c, [(0, 0), (Wr, 0), (Wr, Hr), (0, Hr)]),
                  palette["base"])

        # Margin without texture, if requested
        m = 0 if cfg.texture_on_roof_overhang else cfg.roof_margin_cm * cm

        # Two slopes: the first from the bottom, the second mirrored
        # from the top. In both the eaves are at y = 0 (local).
        for half in (0, 1):
            c.saveState()
            if half == 1:
                c.translate(0, Hr)
                c.scale(1, -1)

            area = c.beginPath()
            area.rect(m, m, Wr - 2 * m, Hr / 2 - m)
            c.clipPath(area, stroke=0, fill=0)

            ROOF_TEXTURES[material](c, Wr, Hr / 2, palette, rnd)
            c.restoreState()

        c.restoreState()

    def outline(c, labels=None):
        c.saveState()
        c.setStrokeColorRGB(*cfg.line_color)
        c.setLineWidth(cfg.line_width)

        # Outer border (cut)
        c.setDash(*cfg.dash)
        c.rect(0, 0, Wr, Hr, stroke=1, fill=0)

        # Ridge (fold), in the middle
        c.setDash()
        c.line(0, Hr / 2, Wr, Hr / 2)

        c.restoreState()

    return Piece("roof", "roof", Wr, Hr, body, outline, per_house=1)


def make_pieces(cfg, wall_material, roof_material):
    """The three pieces of a house: short wall, long wall, roof."""
    short_wall = wall_piece(
        cfg, "short wall", "short", cfg.width_cm, cfg.height_cm,
        True, cfg.door_on == "short", wall_material, seed_id=1)
    long_wall = wall_piece(
        cfg, "long wall", "long", cfg.length_cm, cfg.height_cm,
        False, cfg.door_on == "long", wall_material, seed_id=2)
    roof = roof_piece(cfg, roof_material, seed_id=3)
    return short_wall, long_wall, roof


# ============================================================
# PACKING
# MaxRects: places rectangles in a page, trying both
# orientations, so that as many as possible fit.
# ============================================================

def _intersects(a, b, eps=1e-6):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (bx >= ax + aw - eps or bx + bw <= ax + eps
                or by >= ay + ah - eps or by + bh <= ay + eps)


def _contains(a, b, eps=1e-6):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (bx >= ax - eps and by >= ay - eps
            and bx + bw <= ax + aw + eps and by + bh <= ay + ah + eps)


def _split_free(free, placed):
    """Cuts the placed rectangle out of every free rectangle."""
    px, py, pw, ph = placed
    result = []

    for rect in free:
        if not _intersects(rect, placed):
            result.append(rect)
            continue

        fx, fy, fw, fh = rect
        if px > fx:
            result.append((fx, fy, px - fx, fh))
        if px + pw < fx + fw:
            result.append((px + pw, fy, fx + fw - (px + pw), fh))
        if py > fy:
            result.append((fx, fy, fw, py - fy))
        if py + ph < fy + fh:
            result.append((fx, py + ph, fw, fy + fh - (py + ph)))

    # Drop duplicates and rectangles contained in another one
    unique = list(dict.fromkeys(result))
    return [r for i, r in enumerate(unique)
            if not any(j != i and _contains(other, r)
                       for j, other in enumerate(unique))]


def maxrects_pack(sizes, bx, by, bw, bh, allow_rotation=True):
    """
    Packs rectangles (w, h) into the area starting at (bx, by) of size
    (bw, bh). Returns {index: (x, y, rotated)} for the rectangles that
    fit; the others are left out.
    """
    eps = 1e-6
    free = [(bx, by, bw, bh)]
    placed = {}

    # Biggest first; ties keep their original order
    order = sorted(range(len(sizes)), key=lambda i: -max(sizes[i]))

    for i in order:
        w, h = sizes[i]
        best = None

        for fx, fy, fw, fh in free:
            for rotated in ((False, True) if allow_rotation else (False,)):
                pw, ph = (h, w) if rotated else (w, h)
                if pw <= fw + eps and ph <= fh + eps:
                    # Best short side fit
                    score = (min(fw - pw, fh - ph), max(fw - pw, fh - ph))
                    if best is None or score < best[0]:
                        best = (score, fx, fy, pw, ph, rotated)

        if best is None:
            continue

        _, x, y, pw, ph, rotated = best
        placed[i] = (x, y, rotated)
        free = _split_free(free, (x, y, pw, ph))

    return placed


@dataclass
class Placement:
    item: Item
    x: float
    y: float
    rotated: bool


@dataclass
class Page:
    size: tuple
    placements: list


def _usable_area(cfg, page_size):
    """(x, y, w, h) of the area of the page available for pieces."""
    pw, ph = page_size
    m = cfg.page_margin_cm * cm
    strip = RULER_STRIP_CM * cm if cfg.calibration_ruler else 0
    return m, m + strip, pw - 2 * m, ph - 2 * m - strip


def pack_one_page(cfg, items, page_size):
    """Places as many items as possible on one page.
    Returns (placements, items that did not fit)."""
    g = cfg.copy_gap_cm * cm
    ux, uy, uw, uh = _usable_area(cfg, page_size)

    # Inflating pieces and area by the gap keeps pieces apart
    sizes = [(it.piece.width + g, it.piece.height + g) for it in items]
    placed = maxrects_pack(sizes, ux, uy, uw + g, uh + g,
                           cfg.allow_rotation)

    placements = []
    for i in sorted(placed):
        x, y, rotated = placed[i]
        placements.append(Placement(items[i], x, y, rotated))

    rest = [it for i, it in enumerate(items) if i not in placed]

    # Centre the block of pieces in the usable area
    if placements:
        def extent(p):
            w, h = p.item.piece.width, p.item.piece.height
            return (h, w) if p.rotated else (w, h)

        min_x = min(p.x for p in placements)
        min_y = min(p.y for p in placements)
        max_x = max(p.x + extent(p)[0] for p in placements)
        max_y = max(p.y + extent(p)[1] for p in placements)

        dx = ux + (uw - (max_x - min_x)) / 2 - min_x
        dy = uy + (uh - (max_y - min_y)) / 2 - min_y
        for p in placements:
            p.x += dx
            p.y += dy

    return placements, rest


def pack_pages(cfg, items):
    """Packs the items into as few pages as possible."""
    base = PAPER_SIZES[cfg.paper]
    pages = []
    remaining = list(items)

    while remaining:
        best = None
        for size in (landscape(base), base):
            placed, rest = pack_one_page(cfg, remaining, size)
            area = sum(p.item.piece.width * p.item.piece.height
                       for p in placed)
            if best is None or area > best[0] + 1e-6:
                best = (area, size, placed, rest)

        _, size, placed, rest = best

        if not placed:
            # The piece is bigger than the paper: it gets a page of its own
            item = remaining[0]
            piece = item.piece
            print(tr(cfg.language, "msg.warn_oversize",
                     piece=tr(cfg.language, f"piece.{piece.role}"),
                     w=piece.width / cm, h=piece.height / cm,
                     paper=cfg.paper))
            ux, uy, _, _ = _usable_area(cfg, (0, 0))
            m = cfg.page_margin_cm * cm
            size = (piece.width + 2 * m, piece.height + uy + m)
            placed = [Placement(item, m, uy, False)]
            rest = remaining[1:]

        pages.append(Page(size, placed))
        remaining = rest

    return pages


# ============================================================
# WHAT TO PRINT
# ============================================================

def _labels(cfg, piece, wall_index, house, show_house):
    """Corner letters for the two side tabs of a wall, or None."""
    if not cfg.joint_labels or (piece.role, wall_index) not in JOINTS:
        return None

    def text(letter_):
        return f"{house + 1}{letter_}" if show_house else letter_

    left, right = JOINTS[(piece.role, wall_index)]
    return text(left), text(right)


def _make_item(cfg, piece, copy_index, show_house):
    """Item number `copy_index` of a piece: copies of a wall come in
    pairs (the two walls of the same kind of one house)."""
    wall_index = copy_index % piece.per_house
    house = copy_index // piece.per_house

    if piece.has_door and cfg.one_door_per_house:
        door_present = wall_index == 0
    else:
        door_present = True

    return Item(piece, door_present,
                _labels(cfg, piece, wall_index, house, show_house))


MAX_FILL = 60


def max_copies(cfg, piece):
    """How many copies of a piece fit on one page."""
    base = PAPER_SIZES[cfg.paper]
    probe = [Item(piece)] * MAX_FILL
    best = max(len(pack_one_page(cfg, probe, size)[0])
               for size in (landscape(base), base))

    # A house needs the walls in pairs: do not leave a lone wall
    if piece.per_house == 2 and best >= 2 and best % 2:
        best -= 1
    return best


def plan_pages(cfg, pieces):
    """Lays out the complete PDF. Returns a list of Page."""

    if cfg.houses is None:
        # Every page is filled with copies of one piece
        pages = []
        for piece in pieces:
            count = max_copies(cfg, piece)
            items = [_make_item(cfg, piece, k, show_house=False)
                     for k in range(count)]
            pages += pack_pages(cfg, items)
        return pages

    # Exactly the pieces needed for the requested number of houses
    show_house = cfg.houses > 1
    items = []
    for house in range(cfg.houses):
        for piece in pieces:
            for wall_index in range(piece.per_house):
                items.append(_make_item(
                    cfg, piece, house * piece.per_house + wall_index,
                    show_house))

    if cfg.mix_pieces:
        return pack_pages(cfg, items)

    pages = []
    for piece in pieces:
        pages += pack_pages(cfg, [it for it in items if it.piece is piece])
    return pages


# ============================================================
# PDF OUTPUT
# ============================================================

class OutputError(Exception):
    """A PDF could not be written."""


def save_pdf(cfg, c, path):
    try:
        c.save()
    except PermissionError:
        raise OutputError(tr(cfg.language, "err.locked", path=path)) from None


class FormCache:
    """Draws the body of a piece (texture, door, windows) once per PDF
    as a reusable form, instead of once per copy."""

    def __init__(self, c):
        self.c = c
        self.names = {}

    def get(self, piece, door):
        key = (piece.name, door if piece.has_door else True)
        if key not in self.names:
            name = f"piece{len(self.names)}"
            self.c.beginForm(name, -2, -2, piece.width + 2, piece.height + 2)
            piece.body(self.c, key[1])
            self.c.endForm()
            self.names[key] = name
        return self.names[key]


def draw_item(cfg, c, item, forms):
    piece = item.piece

    if forms is not None and cfg.textures_enabled:
        c.saveState()
        c.setDash()
        c.setLineWidth(1)
        c.doForm(forms.get(piece, item.door))
        c.restoreState()
    else:
        piece.body(c, item.door)

    piece.outline(c, item.labels)


def draw_ruler(cfg, c):
    """5 cm ruler in the bottom-left corner, to check the print scale."""
    m = cfg.page_margin_cm * cm
    y = m + 0.30 * cm

    c.saveState()
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    c.setDash()

    c.line(m, y, m + 5 * cm, y)
    for i in range(6):
        tick = 0.30 * cm if i in (0, 5) else 0.15 * cm
        c.line(m + i * cm, y, m + i * cm, y + tick)

    c.setFont("Helvetica", 6.5)
    c.drawString(m + 5 * cm + 0.25 * cm, y - 0.04 * cm,
                 tr(cfg.language, "pdf.ruler"))
    c.restoreState()


def write_single_pdf(cfg, path, pieces):
    """A PDF with one page per piece, each page as large as the piece."""
    c = canvas.Canvas(str(path), invariant=1)

    for piece in pieces:
        c.setPageSize((piece.width, piece.height))
        draw_item(cfg, c, Item(piece), None)
        c.showPage()

    save_pdf(cfg, c, path)

    if len(pieces) == 1:
        p = pieces[0]
        print(tr(cfg.language, "msg.pdf_one", path=path,
                 w=p.width / cm, h=p.height / cm))
    else:
        print(tr(cfg.language, "msg.pdf_pages", path=path,
                 count=len(pieces)))


def write_complete_pdf(cfg, path, pages):
    """The complete PDF: pages of paper with several pieces on each."""
    c = canvas.Canvas(str(path), invariant=1)
    forms = FormCache(c) if cfg.reuse_textures else None

    print(tr(cfg.language, "msg.pdf_complete", path=path,
             count=len(pages), paper=cfg.paper))

    for number, page in enumerate(pages, start=1):
        pw, ph = page.size
        c.setPageSize(page.size)

        for p in page.placements:
            c.saveState()
            if p.rotated:
                # Rotated by 90 degrees: it occupies x..x+height, y..y+width
                c.translate(p.x + p.item.piece.height, p.y)
                c.rotate(90)
            else:
                c.translate(p.x, p.y)
            draw_item(cfg, c, p.item, forms)
            c.restoreState()

        if cfg.calibration_ruler:
            draw_ruler(cfg, c)

        c.showPage()

        print(tr(cfg.language, "msg.page", number=number,
                 description=describe_page(cfg, page)))

    save_pdf(cfg, c, path)


def describe_page(cfg, page):
    def t(key, **values):
        return tr(cfg.language, key, **values)

    counts = {}
    doors = 0
    for p in page.placements:
        role = p.item.piece.role
        counts[role] = counts.get(role, 0) + 1
        if p.item.piece.has_door and p.item.door:
            doors += 1

    pw, ph = page.size
    orientation = t("orientation.landscape" if pw > ph
                    else "orientation.portrait")
    parts = ", ".join(t("msg.part", count=n, name=t(f"piece.{role}"))
                      for role, n in counts.items())
    rotated = sum(p.rotated for p in page.placements)

    return t("msg.page_desc", paper=cfg.paper, orientation=orientation,
             parts=parts,
             doors=t("msg.with_door", count=doors) if doors else "",
             rotated=t("msg.rotated", count=rotated) if rotated else "")


def generate_house(cfg, out_dir, prefix, wall_material, roof_material):
    """Writes the PDFs of a house with the given materials: the complete
    one and, unless `complete_only` is set, one for each piece."""
    short_wall, long_wall, roof = make_pieces(cfg, wall_material,
                                              roof_material)

    paths = []
    if not cfg.complete_only:
        for piece, suffix in ((short_wall, "short_wall"),
                              (long_wall, "long_wall"),
                              (roof, "roof")):
            path = out_dir / f"{prefix}_{suffix}.pdf"
            write_single_pdf(cfg, path, [piece])
            paths.append(path)

    path = out_dir / f"{prefix}_complete.pdf"
    write_complete_pdf(cfg, path, plan_pages(cfg, [short_wall, long_wall, roof]))
    paths.append(path)

    return paths, roof


def resolve_output_dir(cfg):
    path = Path(cfg.output_dir)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    return path


def run(cfg):
    """Generates everything described by the configuration.
    Returns the list of PDFs written."""
    validate(cfg)

    def t(key, **values):
        return tr(cfg.language, key, **values)

    print()
    for warning in check_dimensions(cfg) + check_settings(cfg):
        print(warning)

    out_dir = resolve_output_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = []

    if cfg.generate_full_house:

        if cfg.generate_all_variants and cfg.textures_enabled:
            for wall in WALL_PALETTES:
                for roof_mat in ROOF_PALETTES:
                    print(t("msg.variant", wall=wall, roof=roof_mat))
                    paths, roof = generate_house(
                        cfg, out_dir, f"{cfg.base_name}_{wall}_{roof_mat}",
                        wall, roof_mat)
                    files += paths
                    print()
        else:
            paths, roof = generate_house(cfg, out_dir, cfg.base_name,
                                         cfg.wall_material, cfg.roof_material)
            files += paths

        side = slope_side_cm(cfg, cfg.width_cm)
        slope = side + cfg.roof_overhang_cm

        print()
        print(t("msg.roof_title"))
        print(t("msg.roof_side", value=side))
        print(t("msg.roof_depth", value=slope))
        print(t("msg.roof_base", length=cfg.length_cm, depth=2 * slope))
        print(t("msg.roof_sheet", margin=cfg.roof_margin_cm,
                w=roof.width / cm, h=roof.height / cm))
        print()
        print(t("msg.door_side", side=t(f"side.{cfg.door_on}")))

    else:
        piece = wall_piece(cfg, "wall", "wall", cfg.width_cm, cfg.height_cm,
                           cfg.use_roof, True, cfg.wall_material,
                           seed_id=4, per_house=1)
        path = out_dir / f"{cfg.base_name}.pdf"
        write_single_pdf(cfg, path, [piece])
        files.append(path)

    print()
    print(t("msg.inner"))
    print(f"  {cfg.width_cm} × {cfg.height_cm} cm")
    print()
    print(t("msg.outer"))
    print(f"  {cfg.width_cm + 2 * cfg.tab_width_cm} × "
          f"{cfg.height_cm + 2 * cfg.tab_width_cm} cm")

    return files


# ============================================================
# COMMAND LINE AND WINDOW
# ============================================================

def cli_fields():
    """The settings that can be set from the command line / the window."""
    return [f for f in fields(Config) if f.metadata.get("cli", True)]


def config_to_args(cfg):
    """The command-line options that reproduce `cfg`: only the ones that
    differ from the defaults, as a list of strings."""
    defaults = Config()
    args = []
    for f in cli_fields():
        value = getattr(cfg, f.name)
        if value == getattr(defaults, f.name) or value is None:
            continue
        flag = "--" + f.name.replace("_", "-")
        if isinstance(value, bool):
            args.append(flag if value else "--no-" + flag[2:])
        else:
            args += [flag, str(value)]
    return args


def build_parser():
    parser = argparse.ArgumentParser(
        description="Procedural, printable paper houses for tabletop RPGs. "
                    "Started with no options it opens a window to edit the "
                    "settings. Every setting of the Config class can also "
                    "be given here; whatever is not given keeps the default "
                    "of the file.")

    parser.add_argument(
        "--gui", action=argparse.BooleanOptionalAction, default=None,
        help="open the window (the default when no option is given); with "
             "other options, they fill the window in. --no-gui generates "
             "straight away")

    for f in cli_fields():
        flag = "--" + f.name.replace("_", "-")
        help_text = f"{f.metadata.get('help', '')} (default: {f.default})"

        if isinstance(f.default, bool):
            parser.add_argument(flag, action=argparse.BooleanOptionalAction,
                                default=None, help=help_text)
        else:
            choices = f.metadata.get("choices")
            if callable(choices):
                choices = choices()
            parser.add_argument(flag, dest=f.name, default=None,
                                type=f.metadata.get("type") or type(f.default),
                                choices=choices, help=help_text)

    return parser


def launch_window(overrides):
    """Opens the window. Returns the exit code."""
    language = overrides.get("language", "en")

    try:
        import gui
    except ImportError as error:
        print(tr(language, "msg.no_tkinter", error=error), file=sys.stderr)
        return 1

    palettes = {"wall_material": WALL_PALETTES,
                "roof_material": ROOF_PALETTES}
    try:
        gui.launch(Config, run, validate, resolve_output_dir, config_to_args,
                   overrides, palettes)
    except gui.NoDisplayError as error:
        print(tr(language, "msg.no_display", error=error), file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = build_parser().parse_args(argv)

    use_window = args.gui if args.gui is not None else not argv
    overrides = {k: v for k, v in vars(args).items()
                 if v is not None and k != "gui"}

    if use_window:
        return launch_window(overrides)

    cfg = Config(**overrides)
    try:
        run(cfg)
    except ValueError as error:
        print(tr(cfg.language, "msg.invalid", error=error), file=sys.stderr)
        return 2
    except OutputError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())