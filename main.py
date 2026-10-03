from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4, landscape
import math
import random


# ============================================================
# SETTINGS
# ============================================================

# WIDTH, LENGTH and HEIGHT are the measurements of the INNER
# rectangle (the D&D squares, multiples of 2.5 cm).
# The tabs (TAB_WIDTH_CM) are added on the outside.

# If True, generates 4 PDFs: short wall with roof gable, long wall,
# roof, and a fourth PDF (A4) with all the pieces, several copies each.
# If False, generates a single PDF (short wall, with or without roof).
GENERATE_FULL_HOUSE = True

# Short side of the house (the one with the gable): 3 squares
WIDTH_CM = 7.5

# Long side of the house: 5 squares
# (only used if GENERATE_FULL_HOUSE = True)
LENGTH_CM = 12.5

# Wall height (same for both sides): 3 squares
HEIGHT_CM = 7.5

# Width of the tabs around the inner rectangle
TAB_WIDTH_CM = 1.0

# Height of the roof gable (triangle)
ROOF_HEIGHT_CM = 2.5

# Width of the flaps on the roof gable
ROOF_FLAP_CM = 1.0

# How far the roof slope extends beyond the gable side
ROOF_OVERHANG_CM = 0.5

# How much the roof sheet is enlarged, on EVERY side, compared
# to its base size (computed from the walls)
ROOF_MARGIN_CM = 1.0

# Single-PDF mode only: set to False to remove the roof
USE_ROOF = True

# If True, also draws the base of the triangle (fold line)
DRAW_ROOF_BASE = False

# Line width
LINE_WIDTH = 0.5

# Colour of the fold/cut lines (R, G, B between 0 and 1)
LINE_COLOR = (0, 0, 0)

# Dash pattern (dash length, gap length) in points
DASH = (3, 3)

# Mark at half height of the side tabs
# (where to cut for the interlocking joint)
MARKER_COLOR = (0.85, 0.10, 0.10)


# --- TEXTURES ---

# If False: no colours, only the lines
TEXTURES_ENABLED = True

# Wall material: "brick" | "stone" | "wood"
WALL_MATERIAL = "stone"

# Roof material: "wood" | "tiles" | "thatch"
ROOF_MATERIAL = "tiles"

# If True, generates ALL wall/roof combinations (9 houses),
# each with its own PDFs. Ignores the two settings above.
GENERATE_ALL_VARIANTS = False

# Change the number to get a different version of the same
# textures (bricks, wood grain, etc.)
SEED = 7

# Roof: True = the texture covers the whole sheet (the enlarged
# part is a visible overhang). False = the texture covers only
# the base size and the margin gets the plain colour only.
TEXTURE_ON_ROOF_OVERHANG = True


# --- DOOR AND WINDOWS ---

DOOR_AND_WINDOWS = True

# Which side of the house gets the door: "short" | "long"
DOOR_ON = "short"

# Side of a game square and its size in the fiction:
# 2.5 cm = 1.5 m
CELL_CM = 2.5
METERS_PER_CELL = 1.5

# Real-world sizes (in metres) of door and windows.
# Door width grows with the wall:
# MIN for a 3-square wall, MAX for 5 squares or more
DOOR_WIDTH_MIN_M = 1.0
DOOR_WIDTH_MAX_M = 1.5
DOOR_HEIGHT_M = 2.0
DOOR_ARCHED = True          # door with a rounded top

WINDOW_WIDTH_M = 0.8
WINDOW_HEIGHT_M = 0.9
WINDOW_SILL_M = 1.0         # height of the sill above the ground
ROUND_WINDOW_RADIUS_M = 0.25  # small window in the gable


# --- COMPLETE PDF (A4) ---

# White margin along the edges of the A4 page
A4_MARGIN_CM = 0.5

# Gap between two copies of the same piece
COPY_GAP_CM = 0.5

# Allowed layouts (columns, rows), most preferred first:
# 4 copies are tried first, then 2, then 1.
# (to also try 6 copies, add (3, 2) and (2, 3) at the top)
LAYOUTS = [
    (2, 2), (4, 1), (1, 4),   # 4 copies
    (2, 1), (1, 2),           # 2 copies
    (1, 1),                   # 1 copy
]

# If True, in the complete PDF only half of the copies of the wall
# with the door get the door (the others get a window in its
# place), so every house ends up with a single door.
HALVE_DOORS_ON_COPIES = True

# Base name of the PDFs
BASE_NAME = "house_DnD"


# ============================================================
# COLOURS
# ============================================================

WALLS = {
    "brick": {"base": (0.60, 0.25, 0.20), "mortar": (0.82, 0.79, 0.72)},
    "stone": {"base": (0.58, 0.58, 0.58), "mortar": (0.30, 0.30, 0.30)},
    "wood":  {"base": (0.55, 0.37, 0.21)},
}

ROOFS = {
    "wood":   {"base": (0.42, 0.28, 0.16)},
    "tiles":  {"base": (0.78, 0.38, 0.20)},
    "thatch": {"base": (0.86, 0.71, 0.34)},
}

FRAME = (0.30, 0.20, 0.12)
GLASS = (0.70, 0.85, 0.95)
DOOR_PLANKS = (0.42, 0.26, 0.13)
BRASS = (0.85, 0.70, 0.25)
DARK_OUTLINE = (0.15, 0.10, 0.05)


# ============================================================
# UTILITIES
# ============================================================

def meters(m):
    """Converts metres of the fiction into PDF points
    (2.5 cm = 1.5 m)."""
    return m * (CELL_CM / METERS_PER_CELL) * cm


def vary(color, rnd, amplitude):
    """Lightens or darkens a colour by a random amount."""
    f = 1 + rnd.uniform(-amplitude, amplitude)
    return tuple(max(0.0, min(1.0, v * f)) for v in color)


def darken(color, factor):
    return tuple(max(0.0, min(1.0, v * factor)) for v in color)


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


def check_dimensions():
    """Warns if the measurements are not multiples of a square."""
    dimensions = [("WIDTH_CM", WIDTH_CM), ("HEIGHT_CM", HEIGHT_CM)]
    if GENERATE_FULL_HOUSE:
        dimensions.append(("LENGTH_CM", LENGTH_CM))

    for name, value in dimensions:
        squares = value / CELL_CM
        if abs(squares - round(squares)) > 1e-6:
            print(f"WARNING: {name} = {value} cm is not a multiple "
                  f"of {CELL_CM} cm ({squares:.2f} squares).")


# ============================================================
# WALL TEXTURES
# Each one fills the rectangle (x0, y0)-(x1, y1);
# clipping to the exact shape is done by the caller.
# ============================================================

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


WALL_TEXTURES = {
    "brick": texture_brick,
    "stone": texture_stone,
    "wood": texture_wood_wall,
}


# ============================================================
# ROOF TEXTURES
# Drawn in a local system where the eaves are at y = 0
# and the ridge at y = d. The same function is used for both
# slopes (the second one is mirrored).
# ============================================================

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


def texture_roof_tiles(c, w, d, pal, rnd):
    _element_rows(c, w, d, pal, rnd,
                  tw=0.9 * cm, rh=0.55 * cm, length=1.3 * cm,
                  curved=True, amplitude=0.12)


def texture_roof_wood(c, w, d, pal, rnd):
    _element_rows(c, w, d, pal, rnd,
                  tw=0.75 * cm, rh=0.6 * cm, length=0.9 * cm,
                  curved=False, amplitude=0.16)


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


ROOF_TEXTURES = {
    "tiles": texture_roof_tiles,
    "wood": texture_roof_wood,
    "thatch": texture_roof_thatch,
}


# ============================================================
# DOOR AND WINDOWS
# ============================================================

def window(c, cx, cy, w, h):
    # Sill
    c.setFillColorRGB(*FRAME)
    c.rect(cx - w / 2 - 0.05 * cm, cy - h / 2 - 0.07 * cm,
           w + 0.10 * cm, 0.07 * cm, stroke=0, fill=1)

    # Frame and glass
    border = 0.07 * cm
    c.setFillColorRGB(*FRAME)
    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.4)
    c.rect(cx - w / 2, cy - h / 2, w, h, stroke=1, fill=1)

    c.setFillColorRGB(*GLASS)
    c.rect(cx - w / 2 + border, cy - h / 2 + border,
           w - 2 * border, h - 2 * border, stroke=0, fill=1)

    # Cross
    c.setStrokeColorRGB(*FRAME)
    c.setLineWidth(1.0)
    c.line(cx, cy - h / 2, cx, cy + h / 2)
    c.line(cx - w / 2, cy, cx + w / 2, cy)


def round_window(c, cx, cy, r):
    c.setFillColorRGB(*FRAME)
    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.4)
    c.circle(cx, cy, r, stroke=1, fill=1)

    c.setFillColorRGB(*GLASS)
    c.circle(cx, cy, r - 0.05 * cm, stroke=0, fill=1)

    c.setStrokeColorRGB(*FRAME)
    c.setLineWidth(1.0)
    c.line(cx - r, cy, cx + r, cy)
    c.line(cx, cy - r, cx, cy + r)


def door(c, cx, y, w, h):
    x = cx - w / 2

    p = c.beginPath()
    if DOOR_ARCHED and h > w / 2:
        p.moveTo(x, y)
        p.lineTo(x, y + h - w / 2)
        p.arcTo(x, y + h - w, x + w, y + h, 180, -180)
        p.lineTo(x + w, y)
        p.close()
        planks_height = h - w / 2
    else:
        p.rect(x, y, w, h)
        planks_height = h

    c.setFillColorRGB(*DOOR_PLANKS)
    c.setStrokeColorRGB(*FRAME)
    c.setLineWidth(1.2)
    c.drawPath(p, stroke=1, fill=1)

    # Planks
    c.setStrokeColorRGB(*darken(DOOR_PLANKS, 0.6))
    c.setLineWidth(0.5)
    for k in (1, 2):
        c.line(x + k * w / 3, y, x + k * w / 3, y + planks_height)

    # Handle
    c.setFillColorRGB(*BRASS)
    c.circle(cx + w * 0.28, y + h * 0.4, 0.04 * cm, stroke=0, fill=1)


def door_width(width_cm):
    """Door width (in points) based on the wall:
    DOOR_WIDTH_MIN_M with 3 squares, DOOR_WIDTH_MAX_M with 5 or more."""
    squares = width_cm / CELL_CM
    t = (squares - 3) / 2
    t = max(0.0, min(1.0, t))
    return meters(DOOR_WIDTH_MIN_M + t * (DOOR_WIDTH_MAX_M - DOOR_WIDTH_MIN_M))


def opening_positions(width_cm, door_layout, door_present):
    """
    Returns [(type, offset from the centre in points)].

    Door layout: the door in the centre (or a window if the door is
    missing), windows one square from the centre, then three...
    No-door layout: windows in the centre, two squares away, etc.
    """
    cell = CELL_CM * cm
    half = width_cm * cm / 2
    ww = meters(WINDOW_WIDTH_M)
    margin = 0.3 * cm

    out = []
    k_max = int(half // cell) + 1

    for k in range(-k_max, k_max + 1):
        off = k * cell

        if abs(off) + ww / 2 > half - margin and k != 0:
            continue

        if door_layout:
            if k == 0:
                out.append(("door" if door_present else "window", off))
            elif abs(k) % 2 == 1:
                out.append(("window", off))
        else:
            if abs(k) % 2 == 0:
                out.append(("window", off))

    return out


def draw_openings(c, x1, y1, width_cm, height_cm,
                  door_layout, door_present):
    cx0 = x1 + width_cm * cm / 2
    height = height_cm * cm

    for kind, off in opening_positions(width_cm, door_layout,
                                       door_present):
        cx = cx0 + off

        if kind == "door":
            h = min(meters(DOOR_HEIGHT_M), height - 0.3 * cm)
            door(c, cx, y1, door_width(width_cm), h)
        else:
            wh = min(meters(WINDOW_HEIGHT_M), height * 0.6)
            sill = min(meters(WINDOW_SILL_M), height - wh - 0.2 * cm)
            window(c, cx, y1 + sill + wh / 2, meters(WINDOW_WIDTH_M), wh)


# ============================================================
# FUNCTION TO COMPUTE A PARALLEL LINE
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


# ============================================================
# LENGTH OF THE SLOPING SIDE OF THE TRIANGLE
# ============================================================

def slope_side_cm(inner_width_cm):
    """Length (in cm) of the sloping side of the triangle.
    The base of the triangle is the inner width."""
    return math.hypot(inner_width_cm / 2, ROOF_HEIGHT_CM)


# ============================================================
# FIGURE = (name, width, height, draw function, has_door)
#
# The draw function draws the figure with the bottom-left corner
# of its bounding box at the origin (0, 0), so it can be placed
# anywhere (single sheet or A4).
# draw(c, door_present=True): if door_present=False, the wall that
# would have the door gets a window in its place.
# ============================================================

def wall_figure(name, width_cm, height_cm, with_roof,
                has_door, material):
    """
    width_cm and height_cm are the INNER measurements.

    Convention:
      - solid line  = fold
      - dashed line = cut

    Base colour on tabs and flaps, texture only inside the solid
    lines. The corners between two tabs stay white (they are cut away).
    """

    B = TAB_WIDTH_CM * cm
    ROOF_H = ROOF_HEIGHT_CM * cm
    FLAP = ROOF_FLAP_CM * cm

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
            base_left, base_y, apex_x, apex_y, FLAP
        )
        flap_right = outward_parallel(
            apex_x, apex_y, base_right, base_y, FLAP
        )

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

    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------

    def draw(c, door_present=True):
        c.saveState()
        c.translate(offset_x, 0)

        # ----------------------------------------------------
        # Base colour and texture
        # ----------------------------------------------------

        if TEXTURES_ENABLED:
            pal = WALLS[material]
            rnd = random.Random(f"{SEED}-{name}-{material}")

            # Base colour: central band (side tabs + inner
            # rectangle) and bottom tab (and top tab without
            # roof). The corners stay white.
            if with_roof:
                zones = [(x1, 0, x2, y1), (0, y1, W, y2)]
            else:
                zones = [(x1, 0, x2, H), (0, y1, W, y2)]

            for xa, ya, xb, yb in zones:
                fill_path(c, polygon(c, [(xa, ya), (xb, ya),
                                         (xb, yb), (xa, yb)]),
                          pal["base"])

            if with_roof:
                # Triangle and flaps
                fill_path(c, polygon(c, [(base_left, base_y),
                                         (base_right, base_y),
                                         (apex_x, apex_y)]),
                          pal["base"])
                fill_path(c, polygon(c, [(base_left, base_y),
                                         (flap_left[0], flap_left[1]),
                                         (flap_left[2], flap_left[3]),
                                         (apex_x, apex_y)]),
                          pal["base"])
                fill_path(c, polygon(c, [(apex_x, apex_y),
                                         (flap_right[0], flap_right[1]),
                                         (flap_right[2], flap_right[3]),
                                         (base_right, base_y)]),
                          pal["base"])

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
            WALL_TEXTURES[material](c, x1, y1, x2, top_y, pal, rnd)
            c.restoreState()

            # Door and windows
            if DOOR_AND_WINDOWS:
                draw_openings(c, x1, y1, width_cm, height_cm,
                              has_door, door_present)
                if with_roof:
                    # Small round window in the gable
                    round_window(c, apex_x,
                                 base_y + 0.4 * ROOF_H,
                                 meters(ROUND_WINDOW_RADIUS_M))

        # ----------------------------------------------------
        # Lines
        # ----------------------------------------------------

        c.setStrokeColorRGB(*LINE_COLOR)
        c.setLineWidth(LINE_WIDTH)

        # Outer outline (DASHED: it is the cut). It has a cross
        # shape: the corners between two tabs are removed.
        c.setDash(*DASH)

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
        c.setStrokeColorRGB(*MARKER_COLOR)
        c.line(0, ym, x1, ym)
        c.line(x2, ym, W, ym)
        c.setStrokeColorRGB(*LINE_COLOR)

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
            c.setDash()

            c.line(base_left, base_y, apex_x, apex_y)
            c.line(apex_x, apex_y, base_right, base_y)

            if DRAW_ROOF_BASE:
                c.line(base_left, base_y, base_right, base_y)

            # Flaps (dashed)
            c.setDash(*DASH)

            # Left flap
            c.line(*flap_left)                                        # outer side
            c.line(base_left, base_y, flap_left[0], flap_left[1])     # closing at the base
            c.line(apex_x, apex_y, flap_left[2], flap_left[3])        # closing at the apex

            # Right flap
            c.line(*flap_right)                                       # outer side
            c.line(apex_x, apex_y, flap_right[0], flap_right[1])      # closing at the apex
            c.line(base_right, base_y, flap_right[2], flap_right[3])  # closing at the base

        c.restoreState()

    return name, bbox_w, bbox_h, draw, has_door


def roof_figure(name, material):
    """
    Rectangular sheet with two equal slopes.
      - dashed outer border (cut)
      - ridge in the middle, solid line (fold)

    Base size (from the walls):
      - length = inner length of the long wall
      - each slope = sloping side of the triangle + overhang
    The sheet is then enlarged by ROOF_MARGIN_CM on every side.
    """

    side = slope_side_cm(WIDTH_CM)
    slope = side + ROOF_OVERHANG_CM

    base_length = LENGTH_CM
    base_depth = 2 * slope

    Wr = (base_length + 2 * ROOF_MARGIN_CM) * cm
    Hr = (base_depth + 2 * ROOF_MARGIN_CM) * cm

    def draw(c, door_present=True):
        c.saveState()

        if TEXTURES_ENABLED:
            pal = ROOFS[material]
            rnd = random.Random(f"{SEED}-{name}-{material}")

            # Base colour over the whole sheet
            fill_path(c, polygon(c, [(0, 0), (Wr, 0), (Wr, Hr), (0, Hr)]),
                      pal["base"])

            # Margin without texture, if requested
            m = 0 if TEXTURE_ON_ROOF_OVERHANG else ROOF_MARGIN_CM * cm

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

                ROOF_TEXTURES[material](c, Wr, Hr / 2, pal, rnd)
                c.restoreState()

        c.setStrokeColorRGB(*LINE_COLOR)
        c.setLineWidth(LINE_WIDTH)

        # Outer border (cut)
        c.setDash(*DASH)
        c.rect(0, 0, Wr, Hr, stroke=1, fill=0)

        # Ridge (fold), in the middle
        c.setDash()
        c.line(0, Hr / 2, Wr, Hr / 2)

        c.restoreState()

    return name, Wr, Hr, draw, False


# ============================================================
# A4 LAYOUT
# ============================================================

def compute_layout(w, h, page_w, page_h):
    """
    Returns (columns, rows) to use on a page of the given
    size, or (0, 0) if the figure does not fit.
    """

    m = A4_MARGIN_CM * cm
    g = COPY_GAP_CM * cm
    eps = 1e-6

    max_columns = int((page_w - 2 * m + g) // (w + g) + eps)
    max_rows = int((page_h - 2 * m + g) // (h + g) + eps)

    for columns, rows in LAYOUTS:
        if columns <= max_columns and rows <= max_rows:
            return columns, rows

    return 0, 0


def choose_orientation(w, h):
    """
    Tries A4 landscape and portrait and picks the one that
    fits more copies (landscape if tied).
    """

    landscape_size = landscape(A4)
    portrait_size = A4

    col_l, row_l = compute_layout(w, h, *landscape_size)
    col_p, row_p = compute_layout(w, h, *portrait_size)

    if col_p * row_p > col_l * row_l:
        return portrait_size, "portrait", col_p, row_p

    return landscape_size, "landscape", col_l, row_l


# ============================================================
# PDF GENERATION
# ============================================================

def generate_pdf(file_name, figures):
    """
    A PDF with one page per figure, each page as large
    as the figure itself.
    """

    c = canvas.Canvas(file_name)

    for name, w, h, draw, _ in figures:
        c.setPageSize((w, h))
        draw(c)
        c.showPage()

    c.save()

    if len(figures) == 1:
        w, h = figures[0][1], figures[0][2]
        print(f"PDF created: {file_name} ({w / cm:.2f} × {h / cm:.2f} cm)")
    else:
        print(f"PDF created: {file_name} ({len(figures)} pages)")
        for i, (name, w, h, _, _) in enumerate(figures, start=1):
            print(f"    page {i}: {name} ({w / cm:.2f} × {h / cm:.2f} cm)")


def generate_a4_pdf(file_name, figures):
    """
    A PDF with one A4 page per figure, with 1, 2 or 4 copies
    of the figure (depending on how many fit).
    If HALVE_DOORS_ON_COPIES is on, for the wall with the door
    only half of the copies get the door.
    """

    c = canvas.Canvas(file_name)

    g = COPY_GAP_CM * cm

    print(f"PDF created: {file_name} ({len(figures)} A4 pages)")

    for i, (name, w, h, draw, has_door) in enumerate(figures, start=1):

        (page_w, page_h), orientation, columns, rows = \
            choose_orientation(w, h)

        if columns == 0:
            print(f"    page {i}: {name} does NOT fit on an A4 "
                  f"({w / cm:.2f} × {h / cm:.2f} cm), placing it alone")
            columns, rows = 1, 1

        copies = columns * rows

        # How many copies get the door
        if has_door and HALVE_DOORS_ON_COPIES and copies > 1:
            with_door = copies // 2
        else:
            with_door = copies

        c.setPageSize((page_w, page_h))

        # Block of copies centred on the page
        block_w = columns * w + (columns - 1) * g
        block_h = rows * h + (rows - 1) * g

        x0 = (page_w - block_w) / 2
        y_top = (page_h + block_h) / 2

        index = 0
        for row in range(rows):
            for column in range(columns):
                x = x0 + column * (w + g)
                y = y_top - (row + 1) * h - row * g

                c.saveState()
                c.translate(x, y)
                draw(c, index < with_door)
                c.restoreState()

                index += 1

        c.showPage()

        detail = f", {with_door} with door" if has_door else ""
        noun = "copy" if copies == 1 else "copies"
        print(f"    page {i}: {name} - {copies} {noun} "
              f"({columns} × {rows}), A4 {orientation}{detail}")

    c.save()


def generate_house(prefix, wall_material, roof_material):
    """Generates the 4 PDFs of a house with the given materials."""

    short_wall = wall_figure("short wall", WIDTH_CM, HEIGHT_CM,
                             True, DOOR_ON == "short", wall_material)
    long_wall = wall_figure("long wall", LENGTH_CM, HEIGHT_CM,
                            False, DOOR_ON == "long", wall_material)
    roof = roof_figure("roof", roof_material)

    # 1-3) Separate PDFs, each as large as its figure
    generate_pdf(f"{prefix}_short_wall.pdf", [short_wall])
    generate_pdf(f"{prefix}_long_wall.pdf", [long_wall])
    generate_pdf(f"{prefix}_roof.pdf", [roof])

    # 4) Complete PDF: A4 pages with several copies
    generate_a4_pdf(
        f"{prefix}_complete.pdf",
        [short_wall, long_wall, roof]
    )

    return roof


# ============================================================
# GENERATION
# ============================================================

print()

if DOOR_ON not in ("short", "long"):
    raise ValueError('DOOR_ON must be "short" or "long"')

check_dimensions()

if GENERATE_FULL_HOUSE:

    if GENERATE_ALL_VARIANTS and TEXTURES_ENABLED:
        for wall in WALLS:
            for roof_mat in ROOFS:
                print(f"--- walls: {wall}, roof: {roof_mat} ---")
                roof = generate_house(f"{BASE_NAME}_{wall}_{roof_mat}",
                                      wall, roof_mat)
                print()
    else:
        roof = generate_house(BASE_NAME, WALL_MATERIAL, ROOF_MATERIAL)

    side = slope_side_cm(WIDTH_CM)
    slope = side + ROOF_OVERHANG_CM

    print()
    print("Roof:")
    print(f"  triangle side = {side:.2f} cm")
    print(f"  base depth of each slope = {slope:.2f} cm")
    print(f"  base size = "
          f"{LENGTH_CM:.2f} × {2 * slope:.2f} cm")
    print(f"  final sheet (+{ROOF_MARGIN_CM} cm per side) = "
          f"{roof[1] / cm:.2f} × {roof[2] / cm:.2f} cm")

    print()
    print(f"Door on the {DOOR_ON} side")

else:

    figure = wall_figure("wall", WIDTH_CM, HEIGHT_CM,
                         USE_ROOF, True, WALL_MATERIAL)
    generate_pdf(f"{BASE_NAME}.pdf", [figure])

print()
print("Inner rectangle (game squares):")
print(f"  {WIDTH_CM} × {HEIGHT_CM} cm")
print()
print("Outer rectangle (with tabs):")
print(f"  {WIDTH_CM + 2 * TAB_WIDTH_CM} × {HEIGHT_CM + 2 * TAB_WIDTH_CM} cm")