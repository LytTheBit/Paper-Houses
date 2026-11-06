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
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Callable, Optional

from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from i18n import LANGUAGES, has_text, tr


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
    house_shape: str = _f(
        "rectangle", "shape of the house: a rectangle, or an L made of "
                     "two wings", choices=["rectangle", "L"])
    wing_length_cm: float = _f(
        10.0, "L shape only: total length of the second wing, measured "
              "along the outside of the house")
    roof_type: str = _f(
        "gabled", "shape of the roof: gabled (two slopes) or flat",
        choices=["gabled", "flat"])
    top_tabs: bool = _f(
        True, "print the tabs at the top of the walls (the side tabs are "
              "always printed)")
    bottom_tabs: bool = _f(
        True, "print the tabs at the bottom of the walls (the side tabs are "
              "always printed)")
    tab_corners: str = _f(
        "cut", "corners of the tabs at the top and at the bottom of the "
               "walls and of the flaps of the gables: 'cut' cuts the whole "
               "corner at an angle (a trapezoid), so neighbouring pieces "
               "never overlap; 'square' keeps them square and cuts only "
               "the ones that would overlap", choices=["cut", "square"])

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
    door: bool = _f(True, "draw the door", group="Door & windows")
    windows: bool = _f(
        True, "draw the windows (and the small round one in the gable)",
        group="Door & windows")
    door_on: str = _f("short", "side of the house with the door",
                      choices=["short", "long"], group="Door & windows")
    door_position: str = _f(
        "center", "where the door is on its wall, seen from outside: in the "
                  "centre, or towards the left or the right",
        choices=["center", "left", "right"], group="Door & windows")
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
    roof_windows: bool = _f(
        False, "cut flat windows into the roof, halfway down each slope, "
               "where miniatures can stand (a strip of paper under them "
               "is the wall and the support)", group="Door & windows")
    roof_window_position: float = _f(
        0.5, "where a roof window sits on the slope, from 0 (at the ridge) "
             "to 1 (at the eaves); 0.5 is halfway", group="Door & windows")
    roof_window_clearance_cm: float = _f(
        0.1, "extra room around a roof window, on every side, so that the "
             "strip fits easily", group="Door & windows")
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
    if cfg.house_shape not in ("rectangle", "L"):
        errors.append(t("err.house_shape", value=cfg.house_shape))
    if cfg.roof_type not in ("gabled", "flat"):
        errors.append(t("err.roof_type", value=cfg.roof_type))
    if cfg.tab_corners not in ("cut", "square"):
        errors.append(t("err.tab_corners", value=cfg.tab_corners))
    if cfg.door_position not in ("center", "left", "right"):
        errors.append(t("err.door_position", value=cfg.door_position))
    if cfg.house_shape == "L" and (
            cfg.length_cm < cfg.width_cm + cfg.cell_cm - 0.01
            or cfg.wing_length_cm < cfg.width_cm + cfg.cell_cm - 0.01):
        errors.append(t("err.wing_short"))

    for name in ("width_cm", "length_cm", "height_cm", "tab_width_cm",
                 "roof_height_cm", "cell_cm", "meters_per_cell",
                 "floor_height_cm", "window_spacing_cells",
                 "wing_length_cm"):
        if getattr(cfg, name) <= 0:
            errors.append(t("err.positive", name=name,
                            value=getattr(cfg, name)))

    if errors:
        raise ValueError("\n".join(errors))


def tr_or(language, key, default, **values):
    """tr(), or `default` (English) for a text that is not in i18n.py yet."""
    if has_text(language, key):
        return tr(language, key, **values)
    return default.format(**values) if values else default


ROLE_NAMES = {"strip": "roof window strip"}


def role_label(cfg, role):
    """The name of a kind of piece, in the language of the messages."""
    return tr_or(cfg.language, f"piece.{role}", ROLE_NAMES.get(role, role))


def check_settings(cfg):
    """Returns a warning for every setting that has no effect because
    of another one."""
    warnings = []
    if cfg.mix_pieces and cfg.houses is None:
        warnings.append(tr(cfg.language, "msg.warn_mix"))
    if cfg.generate_all_variants and not cfg.textures_enabled:
        warnings.append(tr(cfg.language, "msg.warn_variants"))
    if cfg.roof_windows:
        plan = roof_window_plan(cfg)
        if not plan.runs:
            warnings.append(tr(cfg.language, "msg.warn_roof_windows",
                               reason=tr(cfg.language,
                                         f"msg.rw_{plan.reason}")))
    return warnings


def check_dimensions(cfg):
    """Returns a warning for every measurement that is not a multiple
    of a game square."""
    dimensions = [("width_cm", cfg.width_cm), ("height_cm", cfg.height_cm)]
    if cfg.generate_full_house:
        dimensions.append(("length_cm", cfg.length_cm))
        if cfg.house_shape == "L":
            dimensions.append(("wing_length_cm", cfg.wing_length_cm))

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


@wall_texture("marble", base=(0.93, 0.92, 0.90), mortar=(0.62, 0.63, 0.68))
def texture_marble(c, x0, y0, x1, y1, pal, rnd):
    """Big blocks of white marble with grey veins."""
    c.setFillColorRGB(*pal["mortar"])
    c.rect(x0, y0, x1 - x0, y1 - y0, stroke=0, fill=1)

    bw = 1.7 * cm
    bh = 0.8 * cm
    gap = 0.05 * cm

    row = 0
    y = y0
    while y < y1:
        x = x0 - (bw / 2 if row % 2 else 0)
        while x < x1:
            # A slightly warm or cool white for every block
            shift = rnd.uniform(-0.03, 0.03)
            col = (min(1.0, pal["base"][0] + shift),
                   min(1.0, pal["base"][1] + shift * 0.5),
                   min(1.0, pal["base"][2] - shift * 0.6))

            c.saveState()
            area = c.beginPath()
            area.rect(x + gap / 2, y + gap / 2, bw - gap, bh - gap)
            c.clipPath(area, stroke=0, fill=0)
            c.setFillColorRGB(*col)
            c.rect(x, y, bw, bh, stroke=0, fill=1)

            # Veins: thin wandering lines, darker and lighter
            for k in range(rnd.randint(1, 3)):
                vx = x + rnd.uniform(0.0, 0.4) * bw
                vy = y + rnd.uniform(0.1, 0.9) * bh
                dark = k % 2 == 0
                c.setStrokeColorRGB(*((0.58, 0.60, 0.67) if dark
                                      else (0.80, 0.81, 0.86)))
                c.setLineWidth(rnd.uniform(0.25, 0.65) if dark else 0.9)
                c.bezier(vx, vy,
                         vx + 0.20 * bw, vy + rnd.uniform(-0.4, 0.4) * bh,
                         vx + 0.45 * bw, vy + rnd.uniform(-0.5, 0.5) * bh,
                         vx + rnd.uniform(0.6, 1.0) * bw,
                         vy + rnd.uniform(-0.4, 0.4) * bh)
            c.restoreState()
            x += bw
        y += bh
        row += 1


@wall_texture("ice", base=(0.70, 0.88, 0.97), mortar=(0.40, 0.65, 0.84))
def texture_ice(c, x0, y0, x1, y1, pal, rnd):
    """Blocks of blue ice with white highlights and cracks."""
    c.setFillColorRGB(*pal["mortar"])
    c.rect(x0, y0, x1 - x0, y1 - y0, stroke=0, fill=1)

    bw = 1.3 * cm
    bh = 0.7 * cm
    gap = 0.05 * cm

    row = 0
    y = y0
    while y < y1:
        x = x0 - (bw / 2 if row % 2 else 0)
        while x < x1:
            col = vary(pal["base"], rnd, 0.07)

            c.saveState()
            area = c.beginPath()
            area.rect(x + gap / 2, y + gap / 2, bw - gap, bh - gap)
            c.clipPath(area, stroke=0, fill=0)
            c.setFillColorRGB(*col)
            c.rect(x, y, bw, bh, stroke=0, fill=1)

            # Paler band along the top, like light on the edge
            c.setFillColorRGB(*[min(1.0, v + 0.10) for v in col])
            c.rect(x, y + bh * 0.72, bw, bh * 0.28, stroke=0, fill=1)

            # Two diagonal highlights
            c.setStrokeColorRGB(0.97, 0.99, 1.0)
            c.setLineWidth(0.8)
            hx = x + bw * rnd.uniform(0.12, 0.45)
            c.line(hx, y + bh * 0.2, hx + bw * 0.14, y + bh * 0.62)
            c.setLineWidth(0.5)
            c.line(hx + bw * 0.2, y + bh * 0.2, hx + bw * 0.28, y + bh * 0.46)

            # Sparkles
            c.setFillColorRGB(1, 1, 1)
            for _ in range(rnd.randint(1, 3)):
                c.circle(x + rnd.uniform(0.1, 0.9) * bw,
                         y + rnd.uniform(0.15, 0.85) * bh,
                         rnd.uniform(0.012, 0.03) * cm, stroke=0, fill=1)

            # A crack in some of the blocks
            if rnd.random() < 0.35:
                c.setStrokeColorRGB(0.93, 0.98, 1.0)
                c.setLineWidth(0.45)
                px = x + rnd.uniform(0.4, 0.9) * bw
                py = y + bh
                p = c.beginPath()
                p.moveTo(px, py)
                for _ in range(3):
                    px += rnd.uniform(-0.12, 0.12) * bw
                    py -= bh * rnd.uniform(0.2, 0.35)
                    p.lineTo(px, py)
                c.drawPath(p, stroke=1, fill=0)
            c.restoreState()
            x += bw
        y += bh
        row += 1


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


@roof_texture("blue_tiles", base=(0.20, 0.41, 0.72))
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


@roof_texture("stone", base=(0.50, 0.52, 0.55))
def texture_roof_stone(c, w, d, pal, rnd):
    """Slabs of grey stone, in rows, each row a little over the one below."""
    c.setFillColorRGB(*darken(pal["base"], 0.42))
    c.rect(0, 0, w, d, stroke=0, fill=1)

    rh = 0.75 * cm
    row = 0
    while row * rh < d:
        yb = row * rh
        x = -rnd.uniform(0.0, 1.2) * cm
        while x < w:
            sw = rnd.uniform(1.0, 1.9) * cm
            col = vary(pal["base"], rnd, 0.14)

            c.setFillColorRGB(*col)
            c.setStrokeColorRGB(*darken(col, 0.55))
            c.setLineWidth(0.4)
            c.roundRect(x, yb, sw, rh * 1.35, 0.12 * cm, stroke=1, fill=1)

            # Shadow under the edge of the slab
            c.setStrokeColorRGB(*darken(col, 0.68))
            c.setLineWidth(0.8)
            c.line(x + 0.1 * cm, yb + 0.05 * cm, x + sw - 0.1 * cm,
                   yb + 0.05 * cm)

            # Small marks on the stone
            c.setFillColorRGB(*darken(col, 0.8))
            for _ in range(rnd.randint(1, 3)):
                c.circle(x + rnd.uniform(0.15, 0.85) * sw,
                         yb + rnd.uniform(0.35, 1.1) * rh,
                         rnd.uniform(0.01, 0.03) * cm, stroke=0, fill=1)
            x += sw
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


def window(c, cx, cy, w, h, panes_x=2):
    """A window with a frame, a sill and glass. `panes_x` is the number of
    panes side by side (2 for the usual one, more for a long low window);
    there are always two rows of panes."""
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

    # Highlights in every pane
    columns = [gx0 + (gx1 - gx0) * i / panes_x for i in range(panes_x + 1)]
    for px0, px1 in zip(columns, columns[1:]):
        for py0, py1 in ((gy0, cy), (cy, gy1)):
            _glint(c, px0, py0, px1, py1)

    # Bars between the panes
    c.setStrokeColorRGB(*FRAME)
    c.setLineWidth(1.3)
    for x in [cx - w / 2 + w * i / panes_x for i in range(1, panes_x)]:
        c.line(x, cy - h / 2, x, cy + h / 2)
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


def shifted_door_positions(cfg, width_cm, door_present, window_w, margin):
    """The openings of a wall whose door is not in the centre.

    The door is a quarter of the wall from the left (or from the right) edge:
    on a wall 6 squares wide it is around the second (or the fifth) square.
    The windows fill what is left on each side of the door, spread the same
    way as on the other walls: about `window_spacing_cells` squares apart.
    Returns [(type, offset from the centre in points)].
    """
    width = width_cm * cm
    door_w = door_width(cfg, width_cm)
    fraction = 0.25 if cfg.door_position == "left" else 0.75
    centre = fraction * width
    # not too close to the edge of the wall
    centre = min(max(centre, door_w / 2 + margin), width - door_w / 2 - margin)

    out = [("door" if door_present else "window", centre - width / 2)]

    spacing = cfg.window_spacing_cells * cfg.cell_cm * cm
    min_bay = window_w + 2 * margin
    for start, end in ((0.0, centre - door_w / 2),
                       (centre + door_w / 2, width)):
        span = end - start
        n = int(span / spacing + 0.5 + 1e-9)       # round, the same on both sides
        while n > 0 and span / n < min_bay - 1e-9:
            n -= 1
        for i in range(n):
            out.append(("window", start + (i + 0.5) * span / n - width / 2))

    return sorted(out, key=lambda opening: opening[1])


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

    if door_layout and cfg.door_position != "center":
        return shifted_door_positions(cfg, width_cm, door_present, window_w,
                                      margin)

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

    # Without the door there is a window where the door would be; without
    # the windows only the door is drawn
    door_present = door_present and cfg.door

    for kind, off, floor in openings_for(cfg, width_cm, height_cm,
                                         door_layout, door_present):
        cx = cx0 + off
        base = y1 + floor * floor_height

        if kind == "window" and not cfg.windows:
            continue

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

def outward_parallel(x1, y1, x2, y2, distance, inset=0):
    """
    Returns the endpoints of the parallel line
    shifted towards the outside of the triangle.

    With `inset` the line is also made shorter at both ends: a flap that
    has the two ends cut at an angle (the whole corner), a trapezoid.
    """

    dx = x2 - x1
    dy = y2 - y1

    length = math.sqrt(dx**2 + dy**2)

    # Normal vector
    nx = -dy / length
    ny = dx / length

    # Direction of the line
    ux = dx / length
    uy = dy / length

    return (
        x1 + nx * distance + ux * inset,
        y1 + ny * distance + uy * inset,
        x2 + nx * distance - ux * inset,
        y2 + ny * distance - uy * inset
    )


def slope_side_cm(cfg, inner_width_cm):
    """Length (in cm) of the sloping side of the triangle.
    The base of the triangle is the inner width."""
    return math.hypot(inner_width_cm / 2, cfg.roof_height_cm)


# ============================================================
# ROOF WINDOWS
#
# A roof window is a flat spot on the roof where a miniature can stand.
# On each slope, halfway between the ridge and the eaves, a rectangle is
# cut on three sides; the fourth side, the one towards the ridge, stays
# as a fold. The flap is lifted until it is flat and rests on a strip of
# paper folded into a rectangle: the strip is the wall under the flap
# and its support. It goes from the window on one slope to the window on
# the other, under the part of the roof near the ridge that is left whole.
#
#                         ridge
#                         /\
#        flap, flat      /  \      flap, flat
#      ________________ /    \ ________________    <- both at the same height
#     |  strip (wall)  |      |  strip (wall)  |
#  ___|                |  g   |                |___ <- the two slopes
#     |<--- c --->|    |<2g-->|    |<--- c --->|
#
#   c = one square + a little room, measured flat (the "2.6 cm" leg of the
#       right triangle)
#   g = distance, measured flat, from the ridge to the fold of the flap;
#       the window is halfway: g = (half the width - c) / 2
#   hypotenuse = c / cos(roof angle): the same distance along the slope,
#       which is how deep the cut is
#   h = sqrt(hypotenuse^2 - c^2): the height of the strip
#   the strip is 2 * (g + c) long, and as wide as the window
# ============================================================

def roof_window_runs(squares):
    """Which squares of a house `squares` long get a roof window, as runs
    of neighbouring squares: [(first square, how many), ...].

    The first and last square stay free. In between, the windows take
    every other square starting from the ends, mirrored, so the result is
    always symmetric:
      3 squares: one window in the middle
      4 squares: two windows joined in the middle
      5 squares: two windows with an empty square between them
      6 squares: a window at the second and at the fifth square
    """
    inside = squares - 2
    if inside < 1:
        return []

    half = (inside + 1) // 2
    pattern = [i % 2 == 0 for i in range(half)]
    pattern += pattern[::-1][inside % 2:]

    runs, i = [], 0
    while i < inside:
        if pattern[i]:
            start = i
            while i < inside and pattern[i]:
                i += 1
            runs.append((start + 1, i - start))
        else:
            i += 1
    return runs


@dataclass(frozen=True)
class RoofWindowPlan:
    runs: tuple = ()               # ((first square, squares), ...)
    holes: tuple = ()              # ((x0, x1), ...) in cm, on the roof sheet
    hinge_cm: float = 0.0          # along the slope: ridge to the fold
    hypotenuse_cm: float = 0.0     # along the slope: depth of the cut
    wall_height_cm: float = 0.0    # height of the strip
    ring_across_cm: float = 0.0    # length of the strip, across the roof
    gap_cm: float = 0.0            # between the two windows, measured flat
    reason: str = ""               # why there are no windows


def roof_window_plan(cfg):
    """Sizes and places of the roof windows, or an empty plan."""
    if not cfg.roof_windows:
        return RoofWindowPlan(reason="off")
    if cfg.house_shape != "rectangle" or cfg.roof_type != "gabled":
        return RoofWindowPlan(reason="shape")

    cell = cfg.cell_cm
    clearance = max(0.0, cfg.roof_window_clearance_cm)
    half = cfg.width_cm / 2
    c = cell + clearance                              # flat depth of a window

    squares = int(cfg.length_cm / cell + 1e-6)
    if squares < 3:
        return RoofWindowPlan(reason="short")
    free = half - c                                   # flat room on a slope
    if free < 0.3:
        return RoofWindowPlan(reason="narrow")

    position = min(1.0, max(0.0, cfg.roof_window_position))
    g = position * free                               # ridge to the fold, flat

    side = slope_side_cm(cfg, cfg.width_cm)
    cos = half / side
    hinge = g / cos                                   # the same, on the slope
    hypotenuse = c / cos
    height = math.sqrt(hypotenuse ** 2 - c ** 2)      # Pythagoras

    runs = roof_window_runs(squares)
    offset = (cfg.length_cm - squares * cell) / 2
    start = cfg.roof_margin_cm + offset
    holes = tuple((start + first * cell - clearance,
                   start + (first + count) * cell + clearance)
                  for first, count in runs)

    return RoofWindowPlan(tuple(runs), holes, hinge, hypotenuse, height,
                          2 * (g + c), 2 * g)


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
    suffix: str = ""            # tells apart pieces of the same role: " 3"
    joints: Optional[tuple] = None   # fixed corner letters (left, right)


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
               has_door, material, seed_id, per_house=2,
               gable_span_cm=None):
    """
    width_cm and height_cm are the INNER measurements.

    With `gable_span_cm` the gable covers only that much of the wall, at its
    right end; the rest of the top edge is flat and has its tab. It is the
    wall that holds the end of one roof and the side of another.

    Convention:
      - solid line  = fold
      - dashed line = cut

    Base colour on tabs and flaps, texture only inside the solid
    lines. The corners between two tabs stay white (they are cut away).
    """

    B = cfg.tab_width_cm * cm
    ROOF_H = cfg.roof_height_cm * cm
    FLAP = cfg.roof_flap_cm * cm

    # The tabs at the bottom and at the top can be left out (a wall with
    # a roof gable has no tab at the top anyway)
    partial = bool(with_roof and gable_span_cm is not None
                   and gable_span_cm < width_cm - 1e-6)
    bottom_tab = B if cfg.bottom_tabs else 0
    top_tab = B if cfg.top_tabs and (not with_roof or partial) else 0

    # Size of the outer rectangle (inner + tabs)
    W = width_cm * cm + 2 * B
    H = height_cm * cm + bottom_tab + top_tab

    # Inner rectangle
    x1 = B
    x2 = W - B
    y1 = bottom_tab
    y2 = y1 + height_cm * cm

    # Corners of the tabs at the top and at the bottom: the whole corner is
    # cut at 45 degrees, so each tab is a trapezoid and the tabs of
    # neighbouring pieces never overlap (the side tabs stay square)
    cut = min(B, (x2 - x1) / 4) if cfg.tab_corners == "cut" else 0

    def corner_points(*points):
        """The points of a tab, without the ones that are the same."""
        result = []
        for point in points:
            if not result or point != result[-1]:
                result.append(point)
        return result

    # The tab at the bottom, from the left fold to the right fold
    bottom_poly = corner_points(
        (x1, y1), (x1, cut), (x1 + cut, 0), (x2 - cut, 0), (x2, cut),
        (x2, y1))

    # --------------------------------------------------------
    # Roof geometry and bounding box size
    # --------------------------------------------------------

    if with_roof:
        # The base of the triangle coincides with the top side
        # of the inner rectangle.
        base_left = x2 - gable_span_cm * cm if partial else x1
        base_right = x2
        base_y = y2

        apex_x = (base_left + base_right) / 2
        apex_y = base_y + ROOF_H

        # Flaps: parallel to the two sloping sides
        # (with cut corners the ends of a flap are cut at 45 degrees, like
        # the tabs: a trapezoid)
        def flap_inset(xa, ya, xb, yb):
            if cfg.tab_corners != "cut":
                return 0
            return min(FLAP, math.hypot(xb - xa, yb - ya) / 4)

        flap_left = outward_parallel(
            base_left, base_y, apex_x, apex_y, FLAP,
            flap_inset(base_left, base_y, apex_x, apex_y))
        flap_right = outward_parallel(
            apex_x, apex_y, base_right, base_y, FLAP,
            flap_inset(apex_x, apex_y, base_right, base_y))

        # The drawing ends where the roof border ends
        points_x = [0, W, flap_left[0], flap_left[2],
                    flap_right[0], flap_right[2], apex_x]
        points_y = [0, apex_y, flap_left[1], flap_left[3],
                    flap_right[1], flap_right[3]]

        # The flat part of a wall with a partial gable has its tab next to the
        # flap of the gable. The flap goes up and to the left, so the corner
        # of the tab that is near it is cut along the flap, even when the
        # other corners are square.
        flat_tab = []
        if partial and top_tab:
            gap = 0.06 * cm
            fx, fy = flap_left[0], flap_left[1]
            reach = fy - y2
            if reach <= 1e-6:
                near = [(base_left, y2), (base_left, y2 + top_tab)]
            elif reach >= top_tab:
                x_top = base_left + (fx - base_left) * top_tab / reach
                near = [(base_left - gap, y2),
                        (x_top - gap, y2 + top_tab)]
            else:
                near = [(base_left - gap, y2), (fx - gap, fy),
                        (fx - gap, y2 + top_tab)]
            if cfg.tab_corners == "cut":
                # The flaps of a gable are trapezoids too and do not reach
                # over the tab: it is a trapezoid like the other tabs
                near = [(base_left, y2), (base_left - cut, y2 + top_tab)]
            flat_tab = corner_points(
                *near, (x1 + cut, y2 + top_tab),
                (x1, y2 + top_tab - cut), (x1, y2))

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
        zones = [[(0, y1), (W, y1), (W, y2), (0, y2)]]
        if bottom_tab:
            zones.append(bottom_poly)
        if top_tab and partial:
            zones.append(flat_tab)
        elif top_tab:
            zones.append(corner_points(
                (x2, y2), (x2, H - cut), (x2 - cut, H), (x1 + cut, H),
                (x1, H - cut), (x1, y2)))

        for zone in zones:
            fill_path(c, polygon(c, zone), palette["base"])

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
            if partial:
                area.lineTo(base_left, y2)
        area.lineTo(x1, y2)
        area.close()
        c.clipPath(area, stroke=0, fill=0)

        top_y = apex_y if with_roof else y2
        WALL_TEXTURES[material](c, x1, y1, x2, top_y, palette, rnd)
        c.restoreState()

        # Door and windows
        if cfg.door or cfg.windows:
            draw_openings(cfg, c, x1, y1, width_cm, height_cm,
                          has_door, door_present)
        if cfg.windows and with_roof:
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

        bottom_path = ([(0, y1)] + bottom_poly + [(W, y1)]
                       if bottom_tab else [(0, 0), (W, 0)])

        p = c.beginPath()
        if with_roof:
            # No top edge: the roof is there
            points = [(0, y2)] + bottom_path + [(W, y2)]
            p.moveTo(*points[0])
            for point in points[1:]:
                p.lineTo(*point)
            c.drawPath(p, stroke=1, fill=0)

            # Top side of the side tabs
            c.line(0, y2, x1, y2)
            c.line(x2, y2, W, y2)

            # The flat part of a partial gable: its tab, or a plain cut
            if partial and top_tab:
                tab_path = c.beginPath()
                tab_path.moveTo(*flat_tab[0])
                for point in flat_tab[1:]:
                    tab_path.lineTo(*point)
                c.drawPath(tab_path, stroke=1, fill=0)
            elif partial:
                c.line(x1, y2, base_left, y2)
        else:
            top_path = ([(W, y2), (x2, y2), (x2, H - cut), (x2 - cut, H),
                         (x1 + cut, H), (x1, H - cut), (x1, y2), (0, y2)]
                        if top_tab else [(W, y2), (0, y2)])
            points = bottom_path + top_path
            p.moveTo(*points[0])
            for point in points[1:]:
                p.lineTo(*point)
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
        if partial and top_tab:
            c.line(x1, y2, flat_tab[0][0], y2)        # fold of the flat tab

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


def roof_piece(cfg, material, seed_id, guides=()):
    """
    Rectangular sheet with two equal slopes. `guides` are lines (in cm,
    on the sheet) that only show where something else is glued.
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
    plan = roof_window_plan(cfg)

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

        # Guides: thin dotted lines, nothing to cut or fold
        if guides:
            c.setDash(1, 3)
            c.setLineWidth(cfg.line_width * 0.7)
            for (xa, ya), (xb, yb) in guides:
                c.line(xa * cm, ya * cm, xb * cm, yb * cm)
            c.setDash()
            c.setLineWidth(cfg.line_width)

        # Roof windows: on each slope a flap, cut on three sides and
        # folded on the side towards the ridge
        hinge = plan.hinge_cm * cm
        depth = plan.hypotenuse_cm * cm
        for x0, x1 in plan.holes:
            for sign in (-1, 1):                    # lower and upper slope
                y_fold = Hr / 2 + sign * hinge
                y_far = Hr / 2 + sign * (hinge + depth)

                c.setDash(*cfg.dash)
                p = c.beginPath()
                p.moveTo(x0 * cm, y_fold)
                p.lineTo(x0 * cm, y_far)
                p.lineTo(x1 * cm, y_far)
                p.lineTo(x1 * cm, y_fold)
                c.drawPath(p, stroke=1, fill=0)

                c.setDash()
                c.line(x0 * cm, y_fold, x1 * cm, y_fold)

        c.restoreState()

    return Piece("roof", "roof", Wr, Hr, body, outline, per_house=1)


def strip_piece(cfg, material, squares, count, plan, seed_id):
    """The strip of paper under the roof windows: folded into a rectangle,
    it is the wall under the flaps and their support.

    Two sides are as long as the window (`squares` squares) and are the
    walls that face outside: they get the picture of a window. The other
    two go from one window to the other, under the part of the roof near
    the ridge. The height is the other leg of the right triangle: see the
    notes on roof windows above.

      +-----------+---------------------+-----------+---------------------+-+
      | window    | from one window to  | window    | from one window to  |g|
      | (outside) | the other           | (outside) | the other           |l|
      +-----------+---------------------+-----------+---------------------+-+
         solid lines = folds, dashed = cuts, g = glue tab
    """
    along = squares * cfg.cell_cm * cm
    across = plan.ring_across_cm * cm
    height = plan.wall_height_cm * cm
    glue = 0.5 * cm
    chamfer = min(glue, height / 3)

    edges = [0.0, along, along + across, 2 * along + across,
             2 * along + 2 * across]
    end = edges[-1]
    width = end + glue

    net = [(0, 0), (end, 0), (end + glue, chamfer),
           (end + glue, height - chamfer), (end, height), (0, height)]

    palette = WALL_PALETTES[material] if cfg.textures_enabled else None

    def body(c, door_present=True):
        if palette is None:
            return

        c.saveState()
        rnd = random.Random(f"{cfg.seed}/{seed_id}/{material}")

        # Base colour everywhere, glue tab included
        fill_path(c, polygon(c, net), palette["base"])

        # Wall texture on the four sides
        for x0, x1 in zip(edges, edges[1:]):
            c.saveState()
            area = c.beginPath()
            area.rect(x0, 0, x1 - x0, height)
            c.clipPath(area, stroke=0, fill=0)
            WALL_TEXTURES[material](c, x0, 0, x1, height, palette, rnd)
            c.restoreState()

        # A window on the two sides that face outside: lower and longer
        # than the ones of the walls
        if cfg.windows and height >= 0.7 * cm:
            for x0, x1 in ((edges[0], edges[1]), (edges[2], edges[3])):
                face = x1 - x0
                w = face * 0.72
                panes = max(2, round(w / (1.0 * cm)))
                window(c, (x0 + x1) / 2, height * 0.56, w, height * 0.58,
                       panes_x=panes)

        c.restoreState()

    def outline(c, labels=None):
        c.saveState()
        c.setStrokeColorRGB(*cfg.line_color)
        c.setLineWidth(cfg.line_width)

        # Cut: the outline of the strip with its glue tab
        c.setDash(*cfg.dash)
        p = c.beginPath()
        p.moveTo(*net[0])
        for point in net[1:]:
            p.lineTo(*point)
        p.close()
        c.drawPath(p, stroke=1, fill=0)

        # Fold: between the sides, and before the glue tab
        c.setDash()
        for x in edges[1:]:
            c.line(x, 0, x, height)

        c.restoreState()

    return Piece(f"roof strip {squares}", "strip", width, height, body,
                 outline, per_house=count)


def offset_polygon(points, margin):
    """A polygon with only right angles, moved outwards by `margin`.
    The points go counter-clockwise."""
    n = len(points)
    result = []
    for i in range(n):
        px, py = points[i - 1]
        x, y = points[i]
        nx_, ny_ = points[(i + 1) % n]

        def outward(ax, ay, bx, by):
            length = math.hypot(bx - ax, by - ay)
            dx, dy = (bx - ax) / length, (by - ay) / length
            return dy, -dx                      # the right of the direction

        a1, a2 = outward(px, py, x, y)
        b1, b2 = outward(x, y, nx_, ny_)
        result.append((x + margin * (a1 + b1), y + margin * (a2 + b2)))
    return result


def paving(c, w, h, origin, cell, pal, rnd):
    """Floor tiles, two to a side of a game square, with the squares of the
    game marked: a thicker joint along every square and a small cross at
    every corner. `origin` is where the squares start."""
    ox, oy = origin
    tile = cell / 2
    gap = 0.045 * cm

    grout = darken(pal["base"], 0.55)
    c.setFillColorRGB(*grout)
    c.rect(0, 0, w, h, stroke=0, fill=1)

    for ix in range(math.floor(-ox / tile), math.ceil((w - ox) / tile)):
        for iy in range(math.floor(-oy / tile), math.ceil((h - oy) / tile)):
            x = ox + ix * tile
            y = oy + iy * tile

            # The squares of the game are slightly lighter and darker, like
            # a chess board, so they can be seen at a glance
            checker = (ix // 2 + iy // 2) % 2
            col = vary(darken(pal["base"], 1.05 if checker else 0.94), rnd,
                       0.05)
            c.setFillColorRGB(*col)
            c.rect(x + gap / 2, y + gap / 2, tile - gap, tile - gap,
                   stroke=0, fill=1)

            # A small chip on some tiles
            if rnd.random() < 0.25:
                c.setFillColorRGB(*darken(col, 0.82))
                c.circle(x + rnd.uniform(0.2, 0.8) * tile,
                         y + rnd.uniform(0.2, 0.8) * tile,
                         rnd.uniform(0.012, 0.03) * cm, stroke=0, fill=1)

    # Thicker joint along the squares of the game
    c.setStrokeColorRGB(*darken(pal["base"], 0.42))
    c.setLineWidth(1.3)
    xs = [ox + i * cell for i in range(math.floor(-ox / cell),
                                       math.ceil((w - ox) / cell) + 1)]
    ys = [oy + i * cell for i in range(math.floor(-oy / cell),
                                       math.ceil((h - oy) / cell) + 1)]
    for x in xs:
        c.line(x, 0, x, h)
    for y in ys:
        c.line(0, y, w, y)

    # A cross at every corner of a square
    c.setStrokeColorRGB(*[min(1.0, v + 0.35) for v in pal["base"]])
    c.setLineWidth(0.9)
    arm = 0.16 * cm
    for x in xs:
        for y in ys:
            c.line(x - arm, y, x + arm, y)
            c.line(x, y - arm, x, y + arm)


def flat_roof_piece(cfg, material, footprint_cm, seed_id, suffix=""):
    """A flat roof: a sheet shaped like the house, paved with tiles that show
    the squares of the game, with a tab along every side. The tabs are
    trapezoids (the whole corner is cut at 45 degrees, like the tabs of the
    walls) so the corners at the outside stay empty and the tabs never
    overlap, not even at the inside corner of an L."""
    margin = cfg.roof_margin_cm
    min_x = min(x for x, _ in footprint_cm) - margin
    min_y = min(y for _, y in footprint_cm) - margin
    max_x = max(x for x, _ in footprint_cm) + margin
    max_y = max(y for _, y in footprint_cm) + margin

    def to_sheet(point):
        return ((point[0] - min_x) * cm, (point[1] - min_y) * cm)

    shape = [to_sheet(point) for point in footprint_cm]
    house_corner = shape[0]
    width, height = (max_x - min_x) * cm, (max_y - min_y) * cm

    # One tab on every side. The points go counter-clockwise, so the
    # outside is on the right of every side.
    tabs = []
    n = len(footprint_cm)
    for i in range(n):
        (ax, ay), (bx, by) = footprint_cm[i], footprint_cm[(i + 1) % n]
        length = math.hypot(bx - ax, by - ay)
        dx, dy = (bx - ax) / length, (by - ay) / length
        nx, ny = dy, -dx

        def turn(point_before, point, point_after):
            """> 0 at a corner that sticks out, < 0 at one that goes in."""
            d1 = (point[0] - point_before[0], point[1] - point_before[1])
            d2 = (point_after[0] - point[0], point_after[1] - point[1])
            return d1[0] * d2[1] - d1[1] * d2[0]

        inset = min(margin, length / 4)
        corner_a = turn(footprint_cm[i - 1], footprint_cm[i],
                        footprint_cm[(i + 1) % n])
        corner_b = turn(footprint_cm[i], footprint_cm[(i + 1) % n],
                        footprint_cm[(i + 2) % n])
        # Square tabs are cut only where they would overlap: at the
        # corners that go in
        cut_a = inset if cfg.tab_corners == "cut" or corner_a < 0 else 0
        cut_b = inset if cfg.tab_corners == "cut" or corner_b < 0 else 0

        tabs.append([
            to_sheet((ax, ay)),
            to_sheet((ax + nx * margin + dx * cut_a,
                      ay + ny * margin + dy * cut_a)),
            to_sheet((bx + nx * margin - dx * cut_b,
                      by + ny * margin - dy * cut_b)),
            to_sheet((bx, by))])

    palette = ROOF_PALETTES[material] if cfg.textures_enabled else None

    def body(c, door_present=True):
        if palette is None:
            return

        c.saveState()
        rnd = random.Random(f"{cfg.seed}/{seed_id}/{material}")

        # The tabs have the base colour only
        for tab in tabs:
            fill_path(c, polygon(c, tab), palette["base"])

        fill_path(c, polygon(c, shape), palette["base"])
        area = c.beginPath()
        area.moveTo(*shape[0])
        for point in shape[1:]:
            area.lineTo(*point)
        area.close()
        c.clipPath(area, stroke=0, fill=0)
        paving(c, width, height, house_corner, cfg.cell_cm * cm, palette, rnd)
        c.restoreState()

    def outline(c, labels=None):
        c.saveState()
        c.setStrokeColorRGB(*cfg.line_color)
        c.setLineWidth(cfg.line_width)

        # Cut: the three free sides of every tab
        c.setDash(*cfg.dash)
        for tab in tabs:
            p = c.beginPath()
            p.moveTo(*tab[0])
            for point in tab[1:]:
                p.lineTo(*point)
            c.drawPath(p, stroke=1, fill=0)

        # Fold: the sides of the roof
        c.setDash()
        p = c.beginPath()
        p.moveTo(*shape[0])
        for point in shape[1:]:
            p.lineTo(*point)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
        c.restoreState()

    return Piece("roof", "roof", width, height, body, outline, per_house=1,
                 suffix=suffix)


def valley_roof_piece(cfg, material, name, suffix, wing_length_cm, seed_id):
    """The roof of the second wing of an L-shaped house.

    Two slopes folded along the ridge, like a normal roof. It rests on the
    gable wall at one end; at the other end it rests on the long roof of the
    first wing: the end of each slope is cut at an angle, along the valley
    where the two roofs meet, and has a tab to glue under the long roof.
    The ridge ends where it meets the ridge of the long roof.
    """
    half = cfg.width_cm / 2
    side = slope_side_cm(cfg, cfg.width_cm)
    eave = cfg.roof_overhang_cm + cfg.roof_margin_cm       # beyond the walls
    end = cfg.roof_margin_cm                               # beyond the gable
    tab = 0.6
    depth = side + eave
    height = 2 * depth
    ridge = height / 2

    ridge_left = tab                         # where the two ridges meet
    x_gable = ridge_left + wing_length_cm - half            # gable wall
    x_end = x_gable + end
    x_far = ridge_left + depth * half / side    # the slanted edge, at the eave
    y_low, y_high = ridge - depth, ridge + depth

    lower = [(ridge_left, ridge), (x_end, ridge), (x_end, y_low),
             (x_far, y_low)]
    upper = [(ridge_left, ridge), (x_end, ridge), (x_end, y_high),
             (x_far, y_high)]
    tabs = [[(ridge_left, ridge), (x_far, y_low), (x_far - tab, y_low),
             (0, ridge)],
            [(ridge_left, ridge), (x_far, y_high), (x_far - tab, y_high),
             (0, ridge)]]
    sheet = [(0, ridge), (x_far - tab, y_low), (x_end, y_low),
             (x_end, y_high), (x_far - tab, y_high)]

    def scaled(points):
        return [(x * cm, y * cm) for x, y in points]

    width = x_end
    palette = ROOF_PALETTES[material] if cfg.textures_enabled else None

    def body(c, door_present=True):
        if palette is None:
            return

        c.saveState()
        rnd = random.Random(f"{cfg.seed}/{seed_id}/{material}")

        for face, is_lower in ((lower, True), (upper, False)):
            fill_path(c, polygon(c, scaled(face)), palette["base"])
            c.saveState()
            area = c.beginPath()
            pts = scaled(face)
            area.moveTo(*pts[0])
            for point in pts[1:]:
                area.lineTo(*point)
            area.close()
            c.clipPath(area, stroke=0, fill=0)
            if not is_lower:                    # the slope above the ridge
                c.translate(0, height * cm)
                c.scale(1, -1)
            ROOF_TEXTURES[material](c, width * cm, ridge * cm, palette, rnd)
            c.restoreState()

        for piece_tab in tabs:
            fill_path(c, polygon(c, scaled(piece_tab)), palette["base"])
        c.restoreState()

    def outline(c, labels=None):
        c.saveState()
        c.setStrokeColorRGB(*cfg.line_color)
        c.setLineWidth(cfg.line_width)

        c.setDash(*cfg.dash)
        outer = scaled(sheet)
        p = c.beginPath()
        p.moveTo(*outer[0])
        for point in outer[1:]:
            p.lineTo(*point)
        p.close()
        c.drawPath(p, stroke=1, fill=0)

        # Folds: the ridge, and the two slanted edges that have a tab
        c.setDash()
        c.line(ridge_left * cm, ridge * cm, x_end * cm, ridge * cm)
        c.line(ridge_left * cm, ridge * cm, x_far * cm, y_low * cm)
        c.line(ridge_left * cm, ridge * cm, x_far * cm, y_high * cm)
        c.restoreState()

    return Piece(name, "roof", width * cm, height * cm, body, outline,
                 per_house=1, suffix=suffix)


def make_l_pieces(cfg, wall_material, roof_material):
    """The pieces of an L-shaped house: six walls and the roof.

    The house is made of two wings of the same width. The first one is
    `length_cm` long, the second one `wing_length_cm`, and they meet in a
    corner. Seen from above the walls go around like this:

        wall 6 ... the long outside wall of the second wing; the end of it
                   that is next to the first wing has a gable
        wall 5 ... the gable of the second wing
        wall 4 ... inside, along the second wing
        wall 3 ... inside, along the first wing
        wall 2 ... the gable of the first wing
        wall 1 ... the long outside wall of the first wing

    The gabled roof has two pieces. The first is a long roof over the whole
    first wing: it rests on the gable of wall 2 and on the gable at the end
    of wall 6. The second one covers the second wing: it rests on the gable
    of wall 5 and, at the other end, on the long roof.
    """
    width, length, wing = cfg.width_cm, cfg.length_cm, cfg.wing_length_cm
    gabled = cfg.roof_type == "gabled"
    footprint = [(0, 0), (length, 0), (length, width), (width, width),
                 (width, wing), (0, wing)]

    lengths = [length, width, length - width, wing - width, width, wing]
    gables = {1, 4, 5} if gabled else set()
    door_wall = 1 if cfg.door_on == "short" else 0

    pieces = []
    for i, wall_length in enumerate(lengths):
        piece = wall_piece(cfg, f"wall {i + 1}", "wall", wall_length,
                           cfg.height_cm, i in gables, i == door_wall,
                           wall_material, seed_id=20 + i, per_house=1,
                           gable_span_cm=width if i == 5 else None)
        corners = (chr(65 + (i - 1) % 6), chr(65 + i))
        pieces.append(replace(piece, suffix=f" {i + 1}", joints=corners))

    if gabled:
        # Where the second roof is glued on the long one: the two valleys,
        # from the point where the ridges meet to the eaves, on the slope
        # that faces the second wing
        side = slope_side_cm(cfg, width)
        margin = cfg.roof_margin_cm
        ridge_y = side + cfg.roof_overhang_cm + margin
        meeting = (margin + width / 2, ridge_y)
        guides = [(meeting, (margin, ridge_y + side)),
                  (meeting, (margin + width, ridge_y + side))]
        long_roof = roof_piece(cfg, roof_material, seed_id=3, guides=guides)
        pieces.append(replace(long_roof, name="roof wing A", suffix=" A"))
        pieces.append(valley_roof_piece(cfg, roof_material, "roof wing B",
                                        " B", wing, seed_id=4))
    else:
        pieces.append(flat_roof_piece(cfg, roof_material, footprint,
                                      seed_id=3))
    return pieces


def make_pieces(cfg, wall_material, roof_material):
    """The pieces of a house: the walls, the roof and, if there are roof
    windows, a strip of paper for each."""
    if cfg.house_shape == "L":
        return make_l_pieces(cfg, wall_material, roof_material)

    gabled = cfg.roof_type == "gabled"
    short_wall = wall_piece(
        cfg, "short wall", "short", cfg.width_cm, cfg.height_cm,
        gabled, cfg.door_on == "short", wall_material, seed_id=1)
    long_wall = wall_piece(
        cfg, "long wall", "long", cfg.length_cm, cfg.height_cm,
        False, cfg.door_on == "long", wall_material, seed_id=2)
    if gabled:
        roof = roof_piece(cfg, roof_material, seed_id=3)
    else:
        footprint = [(0, 0), (cfg.length_cm, 0),
                     (cfg.length_cm, cfg.width_cm), (0, cfg.width_cm)]
        roof = flat_roof_piece(cfg, roof_material, footprint, seed_id=3)
    pieces = [short_wall, long_wall, roof]

    # One strip for every roof window; windows of the same width share
    # the same piece
    plan = roof_window_plan(cfg)
    widths = {}
    for _, squares in plan.runs:
        widths[squares] = widths.get(squares, 0) + 1
    for squares in sorted(widths):
        pieces.append(strip_piece(cfg, wall_material, squares,
                                  widths[squares], plan,
                                  seed_id=10 + squares))
    return pieces


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
                     piece=role_label(cfg, piece.role),
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
    if not cfg.joint_labels:
        return None
    if piece.joints is not None:
        left, right = piece.joints
    elif (piece.role, wall_index) in JOINTS:
        left, right = JOINTS[(piece.role, wall_index)]
    else:
        return None

    def text(letter_):
        return f"{house + 1}{letter_}" if show_house else letter_

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
    door_present = door_present and cfg.door

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
        kind = (p.item.piece.role, p.item.piece.suffix)
        counts[kind] = counts.get(kind, 0) + 1
        if p.item.piece.has_door and p.item.door:
            doors += 1

    pw, ph = page.size
    orientation = t("orientation.landscape" if pw > ph
                    else "orientation.portrait")
    parts = ", ".join(t("msg.part", count=n,
                        name=role_label(cfg, role) + suffix)
                      for (role, suffix), n in counts.items())
    rotated = sum(p.rotated for p in page.placements)

    return t("msg.page_desc", paper=cfg.paper, orientation=orientation,
             parts=parts,
             doors=t("msg.with_door", count=doors) if doors else "",
             rotated=t("msg.rotated", count=rotated) if rotated else "")


def generate_house(cfg, out_dir, prefix, wall_material, roof_material):
    """Writes the PDFs of a house with the given materials: the complete
    one and, unless `complete_only` is set, one for each piece."""
    pieces = make_pieces(cfg, wall_material, roof_material)

    paths = []
    if not cfg.complete_only:
        for piece in pieces:
            path = out_dir / f"{prefix}_{piece.name.replace(' ', '_')}.pdf"
            write_single_pdf(cfg, path, [piece])
            paths.append(path)

    path = out_dir / f"{prefix}_complete.pdf"
    write_complete_pdf(cfg, path, plan_pages(cfg, pieces))
    paths.append(path)

    roof = next(piece for piece in pieces if piece.role == "roof")
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

        if cfg.house_shape == "rectangle" and cfg.roof_type == "gabled":
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