"""Procedural textures of walls and roofs.

Every texture is a function drawn straight into the PDF and registered with
the `@wall_texture` or `@roof_texture` decorator, together with the colours
of the material (`base` is the one used for the tabs). A new texture shows
up in the options and in the window by itself.
"""

from __future__ import annotations

import math

from reportlab.lib.units import cm

from drawing import darken, vary


def blend(colour, other, amount):
    """`colour` with `amount` (0 to 1) of `other` mixed in: what a
    transparent layer would look like, without using transparency."""
    return tuple(a * (1 - amount) + b * amount for a, b in zip(colour, other))


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

    bw = 2.2 * cm
    bh = 1.1 * cm
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

    bw = 1.8 * cm
    bh = 1.0 * cm
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


@wall_texture("earth", base=(0.55, 0.40, 0.26))
def texture_earth(c, x0, y0, x1, y1, pal, rnd):
    """Rammed earth: layers of packed earth, with pebbles and small cracks."""
    width = x1 - x0
    c.setFillColorRGB(*pal["base"])
    c.rect(x0, y0, width, y1 - y0, stroke=0, fill=1)

    # The layers, from the bottom up, each with a wavy top. The edges are
    # drawn at the end, so no layer covers the edge of the one under it
    edges_to_draw = []
    y = y0 - rnd.uniform(0.0, 0.5) * cm
    while y < y1:
        layer = rnd.uniform(0.55, 1.15) * cm
        n = max(3, int(width / (0.9 * cm)))
        step = width / n

        edge = [y + layer + rnd.uniform(-0.10, 0.10) * cm for _ in range(n + 1)]
        top = c.beginPath()
        top.moveTo(x0, edge[0])
        for i in range(n):
            top.curveTo(x0 + (i + 0.4) * step, edge[i],
                        x0 + (i + 0.6) * step, edge[i + 1],
                        x0 + (i + 1) * step, edge[i + 1])

        body = c.beginPath()
        body.moveTo(x0, y - 0.2 * cm)
        body.lineTo(x0, edge[0])
        for i in range(n):
            body.curveTo(x0 + (i + 0.4) * step, edge[i],
                         x0 + (i + 0.6) * step, edge[i + 1],
                         x0 + (i + 1) * step, edge[i + 1])
        body.lineTo(x1, y - 0.2 * cm)
        body.close()

        c.setFillColorRGB(*darken(vary(pal["base"], rnd, 0.06),
                                  rnd.choice((0.82, 0.92, 1.08, 1.18))))
        c.drawPath(body, stroke=0, fill=1)
        edges_to_draw.append(top)
        y += layer

    c.setStrokeColorRGB(*darken(pal["base"], 0.55))
    c.setLineWidth(0.8)
    for top in edges_to_draw:
        c.drawPath(top, stroke=1, fill=0)

    # Pebbles, grains and a few cracks
    area = (width * (y1 - y0)) / cm ** 2
    for _ in range(int(area * 2.2)):
        px = rnd.uniform(x0, x1)
        py = rnd.uniform(y0, y1)
        r = rnd.uniform(0.02, 0.07) * cm
        stone = vary((0.52, 0.47, 0.42), rnd, 0.25)
        c.setFillColorRGB(*stone)
        c.ellipse(px - r, py - r * 0.75, px + r, py + r * 0.75,
                  stroke=0, fill=1)
        c.setFillColorRGB(*[min(1.0, v + 0.12) for v in stone])
        c.circle(px - r * 0.3, py + r * 0.25, r * 0.3, stroke=0, fill=1)
    c.setFillColorRGB(*darken(pal["base"], 0.6))
    for _ in range(int(area * 5)):
        c.circle(rnd.uniform(x0, x1), rnd.uniform(y0, y1),
                 rnd.uniform(0.008, 0.02) * cm, stroke=0, fill=1)
    c.setStrokeColorRGB(*darken(pal["base"], 0.5))
    c.setLineWidth(0.4)
    for _ in range(int(area / 18) + 1):
        px = rnd.uniform(x0, x1)
        py = rnd.uniform(y0, y1)
        p = c.beginPath()
        p.moveTo(px, py)
        for _ in range(4):
            px += rnd.uniform(-0.12, 0.12) * cm
            py -= rnd.uniform(0.1, 0.25) * cm
            p.lineTo(px, py)
        c.drawPath(p, stroke=1, fill=0)


@wall_texture("fieldstone", base=(0.60, 0.58, 0.54), mortar=(0.30, 0.28, 0.26))
def texture_fieldstone(c, x0, y0, x1, y1, pal, rnd):
    """Rough stones of every size, not in neat courses, with dark joints."""
    c.setFillColorRGB(*pal["mortar"])
    c.rect(x0, y0, x1 - x0, y1 - y0, stroke=0, fill=1)

    gap = 0.05 * cm
    y = y0 - rnd.uniform(0.0, 0.6) * cm
    while y < y1:
        rh = rnd.uniform(0.85, 1.6) * cm
        x = x0 - rnd.uniform(0.0, 1.2) * cm
        while x < x1:
            sw = rnd.uniform(0.9, 2.2) * cm

            def inset(amount):
                return rnd.uniform(0.0, amount)

            # An irregular outline: every point a little inside the cell
            pts = [
                (x + gap + inset(0.20 * sw), y + gap + inset(0.18 * rh)),
                (x + sw * 0.5 + rnd.uniform(-0.1, 0.1) * sw,
                 y + gap + inset(0.10 * rh)),
                (x + sw - gap - inset(0.20 * sw), y + gap + inset(0.18 * rh)),
                (x + sw - gap - inset(0.06 * sw),
                 y + rh * 0.5 + rnd.uniform(-0.1, 0.1) * rh),
                (x + sw - gap - inset(0.20 * sw), y + rh - gap - inset(0.18 * rh)),
                (x + sw * 0.5 + rnd.uniform(-0.1, 0.1) * sw,
                 y + rh - gap - inset(0.10 * rh)),
                (x + gap + inset(0.20 * sw), y + rh - gap - inset(0.18 * rh)),
                (x + gap + inset(0.06 * sw),
                 y + rh * 0.5 + rnd.uniform(-0.1, 0.1) * rh),
            ]
            warm = rnd.uniform(-0.06, 0.06)
            col = vary((pal["base"][0] + warm, pal["base"][1],
                        pal["base"][2] - warm), rnd, 0.14)

            p = c.beginPath()
            p.moveTo(*pts[0])
            for point in pts[1:]:
                p.lineTo(*point)
            p.close()
            c.setFillColorRGB(*col)
            c.setStrokeColorRGB(*darken(col, 0.5))
            c.setLineWidth(0.5)
            c.drawPath(p, stroke=1, fill=1)

            # Light on the upper left edge
            c.setStrokeColorRGB(*[min(1.0, v + 0.14) for v in col])
            c.setLineWidth(0.8)
            q = c.beginPath()
            q.moveTo(*pts[6])
            q.lineTo(*pts[7])
            q.lineTo(*pts[0])
            q.lineTo(*pts[1])
            c.drawPath(q, stroke=1, fill=0)

            # Grains
            c.setFillColorRGB(*darken(col, 0.78))
            for _ in range(rnd.randint(1, 4)):
                c.circle(x + rnd.uniform(0.2, 0.8) * sw,
                         y + rnd.uniform(0.2, 0.8) * rh,
                         rnd.uniform(0.012, 0.03) * cm, stroke=0, fill=1)
            x += sw
        y += rh


@wall_texture("stucco", base=(0.91, 0.85, 0.72))
def texture_stucco(c, x0, y0, x1, y1, pal, rnd):
    """Plaster: smooth, with soft patches, trowel marks, a few cracks and
    some spots where it has come off and the bricks show."""
    width, height = x1 - x0, y1 - y0
    area = (width * height) / cm ** 2

    c.setFillColorRGB(*pal["base"])
    c.rect(x0, y0, width, height, stroke=0, fill=1)

    c.saveState()
    clip = c.beginPath()
    clip.rect(x0, y0, width, height)
    c.clipPath(clip, stroke=0, fill=0)

    # Soft patches of a slightly different tone
    for _ in range(int(area * 1.6) + 2):
        r = rnd.uniform(0.35, 1.1) * cm
        px = rnd.uniform(x0, x1)
        py = rnd.uniform(y0, y1)
        shade = darken(pal["base"], rnd.choice((0.84, 0.90, 1.05, 1.09)))
        c.setFillColorRGB(*blend(pal["base"], shade, 0.6))
        c.ellipse(px - r, py - r * 0.7, px + r, py + r * 0.7, stroke=0, fill=1)

    # Trowel marks: short curved strokes
    c.setLineWidth(0.6)
    for _ in range(int(area * 1.4) + 2):
        px = rnd.uniform(x0, x1)
        py = rnd.uniform(y0, y1)
        length = rnd.uniform(0.3, 0.7) * cm
        light = rnd.random() < 0.5
        c.setStrokeColorRGB(*(darken(pal["base"], 1.08 if light else 0.86)))
        c.bezier(px, py, px + length * 0.3, py + rnd.uniform(-0.1, 0.1) * cm,
                 px + length * 0.7, py + rnd.uniform(-0.1, 0.1) * cm,
                 px + length, py + rnd.uniform(-0.05, 0.05) * cm)

    # Grain
    for _ in range(int(area * 14)):
        c.setFillColorRGB(*darken(pal["base"], rnd.choice((0.72, 0.82, 1.10))))
        c.circle(rnd.uniform(x0, x1), rnd.uniform(y0, y1),
                 rnd.uniform(0.008, 0.02) * cm, stroke=0, fill=1)

    # Cracks
    c.setStrokeColorRGB(*darken(pal["base"], 0.55))
    c.setLineWidth(0.4)
    for _ in range(int(area / 30) + 1):
        px = rnd.uniform(x0, x1)
        py = rnd.uniform(y0, y1)
        p = c.beginPath()
        p.moveTo(px, py)
        for _ in range(rnd.randint(3, 6)):
            px += rnd.uniform(-0.14, 0.14) * cm
            py -= rnd.uniform(0.08, 0.22) * cm
            p.lineTo(px, py)
        c.drawPath(p, stroke=1, fill=0)

    # Where the plaster has come off: the bricks under it
    for _ in range(int(area / 55) + 1):
        px = rnd.uniform(x0 + 0.5 * cm, x1 - 0.5 * cm)
        py = rnd.uniform(y0 + 0.5 * cm, y1 - 0.5 * cm)
        points = []
        steps = rnd.randint(7, 9)
        for k in range(steps):
            angle = 2 * math.pi * k / steps
            r = rnd.uniform(0.28, 0.55) * cm
            points.append((px + r * math.cos(angle) * 1.2,
                           py + r * math.sin(angle)))
        patch = c.beginPath()
        patch.moveTo(*points[0])
        for point in points[1:]:
            patch.lineTo(*point)
        patch.close()
        c.setFillColorRGB(*darken(pal["base"], 0.8))          # edge of the plaster
        c.setStrokeColorRGB(*darken(pal["base"], 0.55))
        c.setLineWidth(1.4)
        c.drawPath(patch, stroke=1, fill=1)
        c.setFillColorRGB(*vary((0.62, 0.33, 0.26), rnd, 0.12))
        c.setStrokeColorRGB(0.40, 0.20, 0.16)
        c.setLineWidth(0.5)
        c.drawPath(patch, stroke=1, fill=1)
        c.setStrokeColorRGB(0.82, 0.78, 0.70)
        c.setLineWidth(0.7)
        c.line(px - 0.5 * cm, py, px + 0.5 * cm, py)
        c.line(px - 0.5 * cm, py + 0.2 * cm, px + 0.5 * cm, py + 0.2 * cm)
    c.restoreState()


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


@roof_texture("yellow_tiles", base=(0.90, 0.74, 0.28))
@roof_texture("green_tiles", base=(0.27, 0.55, 0.32))
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


@roof_texture("grass", base=(0.33, 0.55, 0.22))
def texture_roof_grass(c, w, d, pal, rnd):
    """A turf roof: grass with soft patches, and a few small flowers."""
    area = (w * d) / cm ** 2

    c.setFillColorRGB(*pal["base"])
    c.rect(0, 0, w, d, stroke=0, fill=1)

    # Patches of a darker or lighter green
    for _ in range(int(area * 0.5) + 2):
        r = rnd.uniform(0.4, 1.0) * cm
        px = rnd.uniform(0, w)
        py = rnd.uniform(0, d)
        shade = darken(pal["base"], rnd.choice((0.8, 0.9, 1.12, 1.2)))
        c.setFillColorRGB(*blend(pal["base"], shade, 0.6))
        c.ellipse(px - r, py - r * 0.7, px + r, py + r * 0.7, stroke=0, fill=1)

    # Blades of grass
    for _ in range(int(area * 38)):
        px = rnd.uniform(0, w)
        py = rnd.uniform(0, d)
        length = rnd.uniform(0.18, 0.42) * cm
        lean = rnd.uniform(-0.25, 0.25) * length
        shade = rnd.choice((0.62, 0.78, 0.95, 1.12, 1.3))
        c.setStrokeColorRGB(*darken(pal["base"], shade))
        c.setLineWidth(rnd.uniform(0.5, 0.9))
        c.line(px, py, px + lean, py + length)

    # Flowers
    colours = ((1.0, 1.0, 0.95), (0.98, 0.85, 0.25), (0.95, 0.70, 0.80))
    for _ in range(int(area * 0.22) + 1):
        c.setFillColorRGB(*rnd.choice(colours))
        c.circle(rnd.uniform(0, w), rnd.uniform(0, d),
                 rnd.uniform(0.018, 0.035) * cm, stroke=0, fill=1)
