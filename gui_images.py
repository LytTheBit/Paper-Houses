"""The pictures of the window: the colours, the icons and the swatches of the
materials. They are drawn with Pillow and do not need tkinter."""

from __future__ import annotations

import math
import random

try:
    from PIL import Image, ImageDraw
except Exception:        # no Pillow: the window works without pictures
    Image = ImageDraw = None


COLORS = {
    "bg": "#f7f2ea",            # page
    "card": "#ffffff",
    "border": "#e4d8c8",
    "text": "#2d2118",
    "muted": "#8a796a",
    "trough": "#eadfce",
    "disabled": "#d9cdbd",
    "accent": "#c0562f",        # terracotta
    "accent_dark": "#9c4220",
    "accent_light": "#f4d9cb",
    "accent_hover": "#e9b9a2",
    "wing": "#e8a37f",          # the second wing of an L
    "empty": "#efe6da",
    "empty_border": "#dccfbd",
    "sidebar": "#2f2420",
    "sidebar_text": "#eadccb",
    "sidebar_muted": "#a89684",
    "nav_selected": "#5a3a2c",
    "nav_hover": "#43322a",
    "icon": "#5a4638",
    "log_bg": "#271e19",
    "log_text": "#eadccb",
}


# ============================================================
# PICTURES: icons and material swatches (drawn with Pillow)
# ============================================================

SUPER = 4          # drawn 4 times bigger, then shrunk: smooth edges


def draw_icon(name, size, color):
    """A simple line icon, as an RGBA image of size x size."""
    big = size * SUPER
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = big / 64
    width = max(2, round(5.5 * k))

    def pts(values):
        return [(values[i] * k, values[i + 1] * k)
                for i in range(0, len(values), 2)]

    def line(*values):
        points = pts(values)
        d.line(points, fill=color, width=width, joint="curve")
        for x, y in (points[0], points[-1]):
            d.ellipse([x - width / 2, y - width / 2,
                       x + width / 2, y + width / 2], fill=color)

    def box(*values):
        return [v * k for v in values]

    def dot(x, y, r):
        d.ellipse(box(x - r, y - r, x + r, y + r), fill=color)

    if name == "house":
        line(8, 32, 32, 10, 56, 32)
        line(14, 28, 14, 54, 50, 54, 50, 28)
        line(27, 54, 27, 40, 37, 40, 37, 54)
    elif name == "palette":
        d.ellipse(box(6, 8, 58, 56), outline=color, width=width)
        for x, y in ((21, 25), (35, 19), (47, 29), (21, 41)):
            dot(x, y, 4.5)
    elif name == "door":
        d.arc(box(14, 8, 50, 44), start=180, end=360, fill=color, width=width)
        line(14, 26, 14, 56)
        line(50, 26, 50, 56)
        line(8, 56, 56, 56)
        dot(41, 40, 3.5)
    elif name == "page":
        line(14, 8, 40, 8, 52, 20, 52, 56, 14, 56, 14, 8)
        line(40, 8, 40, 20, 52, 20)
        line(22, 33, 44, 33)
        line(22, 44, 44, 44)
    elif name == "gear":
        d.ellipse(box(17, 17, 47, 47), outline=color, width=width)
        for angle in range(0, 360, 45):
            a = math.radians(angle)
            line(32 + 17 * math.cos(a), 32 + 17 * math.sin(a),
                 32 + 25 * math.cos(a), 32 + 25 * math.sin(a))
        dot(32, 32, 4)
    elif name == "play":
        d.polygon(pts((20, 12, 20, 52, 54, 32)), fill=color)
    elif name == "folder":
        line(6, 16, 24, 16, 30, 23, 58, 23, 58, 52, 6, 52, 6, 16)
    elif name == "copy":
        d.rounded_rectangle(box(24, 22, 56, 56), radius=5 * k, outline=color,
                            width=width)
        line(18, 44, 8, 44, 8, 8, 40, 8, 40, 18)
    elif name in ("upload", "download"):
        if name == "upload":
            line(32, 44, 32, 10)
            line(18, 24, 32, 10, 46, 24)
        else:
            line(32, 10, 32, 44)
            line(18, 30, 32, 44, 46, 30)
        line(10, 44, 10, 56, 54, 56, 54, 44)
    elif name == "reset":
        d.arc(box(12, 14, 52, 54), start=20, end=310, fill=color,
              width=width)
        cx, cy, r, theta = 32, 34, 20, math.radians(310)
        px, py = cx + r * math.cos(theta), cy + r * math.sin(theta)
        tx, ty = -math.sin(theta), math.cos(theta)         # direction
        nx, ny = -ty, tx                                   # across it
        d.polygon(pts((px + tx * 9, py + ty * 9,
                       px - tx * 1 + nx * 8, py - ty * 1 + ny * 8,
                       px - tx * 1 - nx * 8, py - ty * 1 - ny * 8)),
                  fill=color)
    elif name == "dice":
        d.rounded_rectangle(box(8, 8, 56, 56), radius=10 * k, outline=color,
                            width=width)
        for x, y in ((22, 22), (42, 22), (32, 32), (22, 42), (42, 42)):
            dot(x, y, 3.8)

    return img.resize((size, size), Image.LANCZOS)


def draw_logo(size):
    """The coloured house used as the logo and as the window icon."""
    big = size * SUPER
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = big / 64

    def p(*v):
        return [x * k for x in v]

    dark = "#4a2a1c"
    d.rounded_rectangle(p(2, 2, 62, 62), radius=14 * k, fill="#f4d9cb")
    d.rectangle(p(14, 30, 50, 54), fill="#f8efe2", outline=dark,
                width=round(2.2 * k))
    d.polygon(p(8, 32, 32, 9, 56, 32), fill="#c0562f", outline=dark)
    d.rounded_rectangle(p(27, 40, 37, 54), radius=4 * k, fill="#6b3f22")
    d.rectangle(p(17, 37, 24, 44), fill="#b9d8ee", outline=dark,
                width=round(1.5 * k))
    d.rectangle(p(40, 37, 47, 44), fill="#b9d8ee", outline=dark,
                width=round(1.5 * k))
    return img.resize((size, size), Image.LANCZOS)


def draw_swatch(role, name, base, size=(64, 44)):
    """A small picture of a material, for the choice of walls and roof."""
    s = SUPER
    w, h = size[0] * s, size[1] * s
    rnd = random.Random(f"{role}-{name}")
    base = tuple(int(v * 255) for v in base)

    def shade(rgb, amount):
        f = 1 + rnd.uniform(-amount, amount)
        return tuple(max(0, min(255, int(v * f))) for v in rgb)

    def darker(rgb, f):
        return tuple(int(v * f) for v in rgb)

    img = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(img)
    gap = s

    if name == "brick":
        d.rectangle([0, 0, w, h], fill=(209, 201, 184))
        bh, bw, y, row = 10 * s, 22 * s, 0, 0
        while y < h:
            x = -(bw // 2) if row % 2 else 0
            while x < w:
                d.rectangle([x + gap, y + gap, x + bw - gap, y + bh - gap],
                            fill=shade(base, 0.12))
                x += bw
            y, row = y + bh, row + 1
    elif name == "stone" and role == "wall":
        d.rectangle([0, 0, w, h], fill=(80, 80, 80))
        y = 0
        while y < h:
            rh = rnd.randint(9, 14) * s
            x = -rnd.randint(0, 10) * s
            while x < w:
                rw = rnd.randint(14, 26) * s
                d.rounded_rectangle(
                    [x + gap, y + gap, x + rw - gap, y + rh - gap],
                    radius=3 * s, fill=shade(base, 0.15))
                x += rw
            y += rh
    elif name == "earth":
        d.rectangle([0, 0, w, h], fill=base)
        y = 0
        while y < h:
            lh = rnd.randint(9, 15) * s
            d.rectangle([0, y, w, y + lh], fill=shade(base, 0.12))
            d.line([0, y + lh, w // 3, y + lh - 2 * s, 2 * w // 3,
                    y + lh + s, w, y + lh - s], fill=darker(base, 0.6),
                   width=max(1, s))
            y += lh
        for _ in range(26):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.randint(1, 2) * s
            d.ellipse([px - r, py - r, px + r, py + r],
                      fill=shade((135, 120, 106), 0.2))
    elif name == "fieldstone":
        d.rectangle([0, 0, w, h], fill=(77, 71, 66))
        y = -rnd.randint(0, 6) * s
        while y < h:
            rh = rnd.randint(11, 18) * s
            x = -rnd.randint(0, 10) * s
            while x < w:
                sw = rnd.randint(12, 26) * s
                col = shade(base, 0.14)
                pts = [(x + rnd.randint(1, 4) * s, y + rnd.randint(1, 3) * s),
                       (x + sw // 2, y + rnd.randint(1, 2) * s),
                       (x + sw - rnd.randint(1, 4) * s, y + rnd.randint(1, 3) * s),
                       (x + sw - rnd.randint(1, 2) * s, y + rh // 2),
                       (x + sw - rnd.randint(1, 4) * s, y + rh - rnd.randint(1, 3) * s),
                       (x + sw // 2, y + rh - rnd.randint(1, 2) * s),
                       (x + rnd.randint(1, 4) * s, y + rh - rnd.randint(1, 3) * s),
                       (x + rnd.randint(0, 2) * s, y + rh // 2)]
                d.polygon(pts, fill=col, outline=darker(col, 0.5))
                x += sw
            y += rh
    elif name == "stucco":
        d.rectangle([0, 0, w, h], fill=base)
        for _ in range(14):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.randint(5, 11) * s
            d.ellipse([px - r, py - r // 2, px + r, py + r // 2],
                      fill=shade(base, 0.07))
        for _ in range(40):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            d.point((px, py), fill=darker(base, 0.78))
        bx, by = int(w * 0.68), int(h * 0.62)
        d.polygon([(bx - 5 * s, by), (bx - 2 * s, by - 4 * s),
                   (bx + 4 * s, by - 3 * s), (bx + 5 * s, by + 2 * s),
                   (bx, by + 5 * s)], fill=(158, 84, 66),
                  outline=darker(base, 0.55))
    elif name == "grass":
        d.rectangle([0, 0, w, h], fill=base)
        for _ in range(180):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            length = rnd.randint(3, 6) * s
            lean = rnd.randint(-2, 2) * s
            d.line([px, py, px + lean, py - length],
                   fill=shade(base, 0.32), width=max(1, s // 2))
        for _ in range(5):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            d.ellipse([px - s, py - s, px + s, py + s],
                      fill=rnd.choice([(255, 253, 240), (250, 217, 64)]))
    elif name == "stone":                       # slabs on a roof
        d.rectangle([0, 0, w, h], fill=darker(base, 0.42))
        rh, y = 9 * s, 0
        while y < h:
            x = -rnd.randint(0, 10) * s
            while x < w:
                sw = rnd.randint(14, 26) * s
                col = shade(base, 0.14)
                d.rounded_rectangle(
                    [x + gap, y + gap, x + sw - gap, y + rh * 1.4],
                    radius=2 * s, fill=col, outline=darker(col, 0.6),
                    width=max(1, s // 2))
                d.line([x + 3 * s, y + gap + s, x + sw - 3 * s, y + gap + s],
                       fill=darker(col, 0.68), width=s)
                x += sw
            y += rh
    elif name == "marble":
        d.rectangle([0, 0, w, h], fill=(158, 160, 172))
        bh, bw, y, row = 12 * s, 26 * s, 0, 0
        while y < h:
            x = -(bw // 2) if row % 2 else 0
            while x < w:
                d.rectangle([x + gap, y + gap, x + bw - gap, y + bh - gap],
                            fill=shade(base, 0.03))
                vx, vy = x + rnd.randint(2, 8) * s, y + rnd.randint(3, 9) * s
                d.line([vx, vy, vx + 6 * s, vy + rnd.randint(-3, 3) * s,
                        vx + 13 * s, vy + rnd.randint(-4, 4) * s],
                       fill=(150, 154, 170), width=max(1, s // 2))
                x += bw
            y, row = y + bh, row + 1
    elif name == "ice":
        d.rectangle([0, 0, w, h], fill=(102, 166, 214))
        bh, bw, y, row = 11 * s, 22 * s, 0, 0
        while y < h:
            x = -(bw // 2) if row % 2 else 0
            while x < w:
                col = shade(base, 0.07)
                d.rectangle([x + gap, y + gap, x + bw - gap, y + bh - gap],
                            fill=col)
                d.rectangle([x + gap, y + gap, x + bw - gap, y + 3 * s],
                            fill=tuple(min(255, v + 25) for v in col))
                hx = x + rnd.randint(3, 9) * s
                d.line([hx, y + 4 * s, hx + 3 * s, y + 9 * s],
                       fill=(250, 253, 255), width=max(1, s * 2 // 3))
                x += bw
            y, row = y + bh, row + 1
    elif name == "wood" and role == "wall":
        ph, y = 11 * s, 0
        while y < h:
            d.rectangle([0, y, w, y + ph], fill=shade(base, 0.10))
            for _ in range(3):
                gy = y + rnd.randint(2, 9) * s
                d.line([0, gy, w, gy + rnd.randint(-1, 1) * s],
                       fill=darker(base, 0.78), width=max(1, s // 2))
            d.line([0, y, w, y], fill=darker(base, 0.55), width=s)
            y += ph
    elif name == "wood":                        # shingles on a roof
        d.rectangle([0, 0, w, h], fill=darker(base, 0.5))
        rh, tw, y, row = 9 * s, 14 * s, 0, 0
        while y < h:
            x = -(tw // 2) if row % 2 else 0
            while x < w:
                d.rectangle([x + gap, y + gap, x + tw - gap, y + rh * 2],
                            fill=shade(base, 0.14))
                x += tw
            y, row = y + rh, row + 1
    elif name in ("tiles", "blue_tiles", "green_tiles", "yellow_tiles"):
        d.rectangle([0, 0, w, h], fill=darker(base, 0.5))
        rh, tw = 8 * s, 14 * s
        rows, y, row = [], 0, 0
        while y < h + rh:
            rows.append((y, row))
            y, row = y + rh, row + 1
        for y, row in reversed(rows):
            x = -(tw // 2) if row % 2 else 0
            while x < w:
                col = shade(base, 0.12)
                d.rectangle([x, y - rh, x + tw, y], fill=col)
                d.pieslice([x, y - tw // 2, x + tw, y + tw // 2], 0, 180,
                           fill=col, outline=darker(col, 0.6),
                           width=max(1, s // 2))
                x += tw
    elif name == "thatch":
        for _ in range(260):
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            length = rnd.randint(8, 18) * s
            d.line([x, y, x + rnd.randint(-2, 2) * s, y + length],
                   fill=shade(base, 0.22), width=s)

    d.rectangle([0, 0, w - 1, h - 1], outline=darker(base, 0.45), width=s)
    return img.resize(size, Image.LANCZOS)


def draw_indicator(kind, state, size, pad):
    """The little box of a check button or circle of a radio button.
    state: normal, hover, selected, disabled or selected_disabled."""
    big = size * SUPER
    img = Image.new("RGBA", ((size + pad) * SUPER, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = SUPER

    selected = state in ("selected", "selected_disabled")
    disabled = state in ("disabled", "selected_disabled")
    if disabled:
        fill = COLORS["disabled"] if selected else "#f1ebe2"
        outline = "#ddd2c2"
    elif selected:
        fill = outline = COLORS["accent"]
    else:
        fill = "white"
        outline = COLORS["accent"] if state == "hover" else "#c9baa7"
    box = [1.5 * k, 1.5 * k, big - 1.5 * k, big - 1.5 * k]
    width = round(1.8 * k)

    if kind == "check":
        d.rounded_rectangle(box, radius=size * 0.24 * k, fill=fill,
                            outline=outline, width=width)
        if selected:
            tick = [(0.27, 0.53), (0.44, 0.70), (0.75, 0.32)]
            d.line([(x * big, y * big) for x, y in tick], fill="white",
                   width=round(size * 0.14 * k), joint="curve")
    else:
        d.ellipse(box, fill="white" if not disabled else fill,
                  outline=outline, width=width)
        if selected:
            r = big * 0.25
            c = big / 2
            d.ellipse([c - r, c - r, c + r, c + r],
                      fill=COLORS["disabled"] if disabled else COLORS["accent"])

    return img.resize((size + pad, size), Image.LANCZOS)
