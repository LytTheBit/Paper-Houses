"""Small tools shared by the drawing code: colours, sizes in metres, paths."""

from __future__ import annotations

from reportlab.lib.units import cm


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
