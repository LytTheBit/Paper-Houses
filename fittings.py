"""Doors and windows as drawings: their shapes and their styles.

Windows: classic (wood frame), stone (stone frame), castle (a narrow slit
without glass), stained (stained glass).
Doors: wood (planks), iron (planks with iron bands), studded (a heavy gate
with iron studs).
"""

from __future__ import annotations

import math

from reportlab.lib.units import cm

from drawing import darken

FRAME = (0.30, 0.20, 0.12)
GLASS = (0.70, 0.85, 0.95)
GLINT = (0.93, 0.97, 1.00)
DOOR_PLANKS = (0.42, 0.26, 0.13)
BRASS = (0.88, 0.72, 0.27)
DARK_OUTLINE = (0.15, 0.10, 0.05)
WINDOW_FRAME_CM = 0.10
DOOR_FRAME_CM = 0.12
PLANK_SHADES = (1.00, 0.90, 1.06, 0.95)
STONE = (0.62, 0.61, 0.58)
SLIT = (0.07, 0.06, 0.07)
IRON = (0.20, 0.21, 0.24)
LEAD = (0.15, 0.15, 0.17)
STAINED = ((0.18, 0.34, 0.78), (0.80, 0.17, 0.20), (0.95, 0.76, 0.18),
           (0.18, 0.60, 0.34), (0.58, 0.28, 0.66))


def _glint(c, x0, y0, x1, y1):
    """Small diagonal highlight in a window pane."""
    pw, ph = x1 - x0, y1 - y0
    c.setStrokeColorRGB(*GLINT)
    c.setLineWidth(0.6)
    c.line(x0 + 0.18 * pw, y0 + 0.55 * ph, x0 + 0.42 * pw, y0 + 0.85 * ph)


def window(c, cx, cy, w, h, panes_x=2, style="classic"):
    """A window. `panes_x` is the number of panes side by side (2 for the
    usual one, more for a long low window)."""
    if style == "stone":
        _window_stone(c, cx, cy, w, h, panes_x)
    elif style == "castle":
        _window_castle(c, cx, cy, w, h, panes_x)
    elif style == "stained":
        _window_stained(c, cx, cy, w, h, panes_x)
    else:
        _window_classic(c, cx, cy, w, h, panes_x)


def _window_classic(c, cx, cy, w, h, panes_x):
    """A window with a wood frame, a sill and glass in two rows of panes."""
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


def _arch_path(c, x, y, width, height):
    """A rectangle with a half circle on top (a window with an arch)."""
    p = c.beginPath()
    if height <= width / 2:
        p.rect(x, y, width, height)
        return p
    r = width / 2
    yc = y + height - r
    p.moveTo(x, y)
    p.lineTo(x, yc)
    p.arcTo(x, yc - r, x + width, yc + r, 180, -180)
    p.lineTo(x + width, y)
    p.close()
    return p


def _window_stone(c, cx, cy, w, h, panes_x):
    """A window with glass in a frame of stone blocks, a lintel and a sill."""
    f = 0.15 * cm
    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = cx + w / 2, cy + h / 2
    edge = darken(STONE, 0.55)

    c.setStrokeColorRGB(*edge)
    c.setLineWidth(0.35)

    # Sill, wider and thicker than the frame
    c.setFillColorRGB(*darken(STONE, 1.08))
    c.rect(x0 - f - 0.07 * cm, y0 - f - 0.10 * cm, w + 2 * f + 0.14 * cm,
           0.10 * cm, stroke=1, fill=1)

    # The frame
    c.setFillColorRGB(*STONE)
    c.rect(x0 - f, y0 - f, w + 2 * f, h + 2 * f, stroke=1, fill=1)

    # Joints between the stones of the frame
    c.setLineWidth(0.3)
    rows = max(2, int((h + 2 * f) / (0.45 * cm)))
    for i in range(1, rows):
        y = y0 - f + (h + 2 * f) * i / rows
        c.line(x0 - f, y, x0, y)
        c.line(x1, y, x1 + f, y)
    columns = max(2, int((w + 2 * f) / (0.5 * cm)))
    for i in range(1, columns):
        x = x0 - f + (w + 2 * f) * i / columns
        c.line(x, y1, x, y1 + f)
        c.line(x, y0 - f, x, y0)

    # Glass and the stone bars
    c.setFillColorRGB(*GLASS)
    c.rect(x0, y0, w, h, stroke=0, fill=1)
    columns = [x0 + w * i / panes_x for i in range(panes_x + 1)]
    for px0, px1 in zip(columns, columns[1:]):
        for py0, py1 in ((y0, cy), (cy, y1)):
            _glint(c, px0, py0, px1, py1)
    c.setStrokeColorRGB(*darken(STONE, 0.85))
    c.setLineWidth(1.3)
    for x in columns[1:-1]:
        c.line(x, y0, x, y1)
    c.line(x0, cy, x1, cy)
    c.setStrokeColorRGB(*edge)
    c.setLineWidth(0.35)
    c.rect(x0, y0, w, h, stroke=1, fill=0)


def _window_castle(c, cx, cy, w, h, panes_x):
    """Narrow tall slits with an arched top, no glass: the dark of the
    inside is all that shows. A wide window is a row of slits."""
    slits = max(1, panes_x // 2)
    frame = 0.11 * cm
    slit_w = min(w * 0.45, 0.55 * cm)
    slit_h = h * 1.15
    edge = darken(STONE, 0.55)

    for k in range(slits):
        sx = cx + (k - (slits - 1) / 2) * (w / slits)
        x = sx - slit_w / 2
        y = cy - slit_h / 2

        # Stone around the slit
        c.setFillColorRGB(*STONE)
        c.setStrokeColorRGB(*edge)
        c.setLineWidth(0.4)
        c.drawPath(_arch_path(c, x - frame, y - frame * 0.6,
                              slit_w + 2 * frame, slit_h + frame * 1.6),
                   stroke=1, fill=1)
        # The dark opening
        c.setFillColorRGB(*SLIT)
        c.drawPath(_arch_path(c, x, y, slit_w, slit_h), stroke=0, fill=1)
        # A light edge on one side shows how deep the wall is
        c.setStrokeColorRGB(*darken(STONE, 0.9))
        c.setLineWidth(0.8)
        c.line(x + slit_w - 0.02 * cm, y + 0.05 * cm,
               x + slit_w - 0.02 * cm, y + slit_h - slit_w * 0.55)
        # Sill
        c.setFillColorRGB(*darken(STONE, 1.08))
        c.setStrokeColorRGB(*edge)
        c.setLineWidth(0.3)
        c.rect(x - frame - 0.05 * cm, y - frame * 0.6 - 0.07 * cm,
               slit_w + 2 * frame + 0.10 * cm, 0.07 * cm, stroke=1, fill=1)


def _window_stained(c, cx, cy, w, h, panes_x):
    """A stained glass window: coloured panes held by lead, with an arch on
    top when the window is tall enough."""
    f = 0.09 * cm
    x0, y0 = cx - w / 2, cy - h / 2
    arched = h > w * 0.9

    # Frame
    c.setFillColorRGB(*LEAD)
    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.4)
    c.drawPath(_arch_path(c, x0 - f, y0 - f, w + 2 * f, h + 2 * f),
               stroke=1, fill=1)

    # The coloured panes, cut to the shape of the window
    glass = _arch_path(c, x0, y0, w, h)
    c.saveState()
    c.clipPath(glass, stroke=0, fill=0)
    columns = max(3, panes_x + 1) if not arched else 3
    rows = 5 if arched else 2
    pw, ph = w / columns, h / rows
    for i in range(columns):
        for j in range(rows):
            colour = STAINED[(i * 2 + j * 3 + i * j) % len(STAINED)]
            c.setFillColorRGB(*colour)
            c.rect(x0 + i * pw, y0 + j * ph, pw + 0.5, ph + 0.5,
                   stroke=0, fill=1)
            c.setFillColorRGB(*[min(1.0, v + 0.25) for v in colour])
            c.circle(x0 + (i + 0.3) * pw, y0 + (j + 0.7) * ph,
                     min(pw, ph) * 0.12, stroke=0, fill=1)
    # Lead between the panes
    c.setStrokeColorRGB(*LEAD)
    c.setLineWidth(1.0)
    for i in range(1, columns):
        c.line(x0 + i * pw, y0, x0 + i * pw, y0 + h)
    for j in range(1, rows):
        c.line(x0, y0 + j * ph, x0 + w, y0 + j * ph)
    c.restoreState()

    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.4)
    c.drawPath(glass, stroke=1, fill=0)

    # Sill
    c.setFillColorRGB(*darken(STONE, 1.05))
    c.setStrokeColorRGB(*darken(STONE, 0.55))
    c.setLineWidth(0.3)
    c.rect(x0 - f - 0.06 * cm, y0 - f - 0.09 * cm, w + 2 * f + 0.12 * cm,
           0.09 * cm, stroke=1, fill=1)


def round_window(c, cx, cy, r, style="classic"):
    """The small round window of the gable, in the style of the windows."""
    if style == "stone":
        _round_stone(c, cx, cy, r, glass=True)
        return
    if style == "castle":
        _round_stone(c, cx, cy, r, glass=False)
        return
    if style == "stained":
        _round_stained(c, cx, cy, r)
        return

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


def _round_stone(c, cx, cy, r, glass):
    """A round window in a ring of stone, with glass or open (dark)."""
    f = 0.13 * cm
    c.setFillColorRGB(*STONE)
    c.setStrokeColorRGB(*darken(STONE, 0.55))
    c.setLineWidth(0.4)
    c.circle(cx, cy, r, stroke=1, fill=1)
    c.setFillColorRGB(*(GLASS if glass else SLIT))
    c.circle(cx, cy, r - f, stroke=0, fill=1)
    if glass:
        _glint(c, cx - r + f, cy - r + f, cx + r - f, cy + r - f)
        c.setStrokeColorRGB(*darken(STONE, 0.85))
        c.setLineWidth(1.3)
        c.line(cx - r, cy, cx + r, cy)
        c.line(cx, cy - r, cx, cy + r)


def _round_stained(c, cx, cy, r):
    """A rose window: wedges of coloured glass held by lead."""
    f = 0.08 * cm
    c.setFillColorRGB(*LEAD)
    c.setStrokeColorRGB(*DARK_OUTLINE)
    c.setLineWidth(0.4)
    c.circle(cx, cy, r, stroke=1, fill=1)
    inner = r - f
    wedges = 8
    for k in range(wedges):
        c.setFillColorRGB(*STAINED[k % len(STAINED)])
        c.wedge(cx - inner, cy - inner, cx + inner, cy + inner,
                k * 360 / wedges, 360 / wedges, stroke=0, fill=1)
    c.setStrokeColorRGB(*LEAD)
    c.setLineWidth(0.9)
    for k in range(wedges):
        angle = math.radians(k * 360 / wedges)
        c.line(cx, cy, cx + inner * math.cos(angle), cy + inner * math.sin(angle))
    c.circle(cx, cy, inner * 0.45, stroke=1, fill=0)
    c.setFillColorRGB(*STAINED[2])
    c.circle(cx, cy, inner * 0.2, stroke=1, fill=1)


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


def door(c, cx, y, w, h, arched, style="wood"):
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
    planks = {"iron": darken(DOOR_PLANKS, 0.85),
              "studded": darken(DOOR_PLANKS, 0.70)}.get(style, DOOR_PLANKS)
    for k in range(n):
        c.setFillColorRGB(*darken(planks, PLANK_SHADES[k]))
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

    if style == "iron":
        _door_iron_bands(c, cx, y, w, h, leaf)
        return
    if style == "studded":
        _door_studs(c, cx, y, w, h, arched, leaf)
        return

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


def _iron_ring(c, cx, y, w, h):
    """A ring handle of iron on a small plate."""
    hx = cx + w * 0.28
    hy = y + h * 0.45
    c.setFillColorRGB(*IRON)
    c.circle(hx, hy + 0.1 * cm, 0.05 * cm, stroke=0, fill=1)
    c.setStrokeColorRGB(*IRON)
    c.setLineWidth(1.2)
    c.circle(hx, hy, 0.10 * cm, stroke=1, fill=0)


def _door_iron_bands(c, cx, y, w, h, leaf):
    """Three bands of riveted iron across the planks."""
    x0 = cx - w / 2
    c.saveState()
    c.clipPath(leaf, stroke=0, fill=0)
    for t in (0.14, 0.48, 0.80):
        c.setFillColorRGB(*IRON)
        c.rect(x0, y + h * t - 0.07 * cm, w, 0.14 * cm, stroke=0, fill=1)
        rivets = max(3, int(w / (0.32 * cm)))
        c.setFillColorRGB(*[min(1.0, v + 0.25) for v in IRON])
        for k in range(rivets):
            c.circle(x0 + w * (k + 0.5) / rivets, y + h * t, 0.025 * cm,
                     stroke=0, fill=1)
    c.restoreState()
    _iron_ring(c, cx, y, w, h)


def _door_studs(c, cx, y, w, h, arched, leaf):
    """A heavy gate: two long iron straps and a grid of studs."""
    x0 = cx - w / 2
    c.saveState()
    c.clipPath(leaf, stroke=0, fill=0)

    # Straps from the hinges, with a pointed end
    c.setFillColorRGB(*IRON)
    for t in (0.20, 0.62):
        yy = y + h * t
        strap = c.beginPath()
        strap.moveTo(x0, yy - 0.07 * cm)
        strap.lineTo(x0 + w * 0.62, yy - 0.07 * cm)
        strap.lineTo(x0 + w * 0.72, yy)
        strap.lineTo(x0 + w * 0.62, yy + 0.07 * cm)
        strap.lineTo(x0, yy + 0.07 * cm)
        strap.close()
        c.drawPath(strap, stroke=0, fill=1)

    # Studs
    columns = max(3, int(w / (0.45 * cm)))
    rows = max(4, int(h / (0.5 * cm)))
    top = 0.74 if arched else 0.9
    for i in range(columns):
        for j in range(rows):
            sx = x0 + w * (i + 0.5) / columns
            sy = y + h * (0.08 + (top - 0.08) * j / (rows - 1))
            c.setFillColorRGB(*IRON)
            c.circle(sx, sy, 0.045 * cm, stroke=0, fill=1)
            c.setFillColorRGB(*[min(1.0, v + 0.35) for v in IRON])
            c.circle(sx - 0.012 * cm, sy + 0.014 * cm, 0.015 * cm,
                     stroke=0, fill=1)
    c.restoreState()
    _iron_ring(c, cx, y, w, h)
