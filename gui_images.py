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
    elif name == "earth" and role == "wall":
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
    elif name == "fieldstone":                  # a rock face
        cols, rows = 6, 5
        cw, ch = w / (cols - 1), h / (rows - 2)
        corners = {(i, j): (int(i * cw - cw * 0.2 + rnd.uniform(-0.3, 0.3) * cw),
                            int(j * ch - ch * 0.5 + rnd.uniform(-0.3, 0.3) * ch))
                   for i in range(cols + 1) for j in range(rows + 1)}
        for j in range(rows):
            tone = rnd.uniform(-0.1, 0.1)
            for i in range(cols):
                a, b = corners[i, j], corners[i + 1, j]
                e, f = corners[i, j + 1], corners[i + 1, j + 1]
                for triangle in ((a, b, f), (a, f, e)):
                    factor = 1 + tone + rnd.uniform(-0.22, 0.22)
                    colour = tuple(max(0, min(255, int(v * factor)))
                                   for v in base)
                    d.polygon(list(triangle), fill=colour,
                              outline=darker(colour, 0.7))
        d.line([0, int(h * 0.42), int(w * 0.4), int(h * 0.38),
                int(w * 0.7), int(h * 0.45), w, int(h * 0.4)],
               fill=darker(base, 0.4), width=max(1, s))
    elif name == "earth":                       # a roof of packed earth
        for _ in range(16):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.randint(5, 10) * s
            d.ellipse([px - r, py - r // 2, px + r, py + r // 2],
                      fill=shade(base, 0.12))
        y = 6 * s
        while y < h:
            d.line([0, y, w // 3, y - s, 2 * w // 3, y + s, w, y],
                   fill=darker(base, 0.72), width=max(1, s // 2))
            y += rnd.randint(9, 13) * s
        for _ in range(60):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.randint(1, 2) * s
            d.ellipse([px - r, py - r, px + r, py + r],
                      fill=shade(base, 0.25))
        for _ in range(12):
            px, py = rnd.randint(0, w), rnd.randint(0, h)
            r = s
            d.ellipse([px - r, py - r, px + r, py + r],
                      fill=shade((140, 134, 126), 0.15))
    elif name == "rubble":
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
    elif name in ("old_stucco", "new_stucco"):
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
        if name == "old_stucco":
            d.polygon([(bx - 6 * s, by), (bx - 2 * s, by - 5 * s),
                       (bx + 5 * s, by - 4 * s), (bx + 6 * s, by + 3 * s),
                       (bx, by + 6 * s)], fill=(158, 84, 66),
                      outline=darker(base, 0.55))
            bx, by = int(w * 0.22), int(h * 0.3)
            d.polygon([(bx - 4 * s, by), (bx, by - 4 * s),
                       (bx + 4 * s, by - 1 * s), (bx + 2 * s, by + 4 * s),
                       (bx - 3 * s, by + 3 * s)], fill=(158, 84, 66),
                      outline=darker(base, 0.55))
        else:
            beam = (74, 48, 28)
            width = max(2, 2 * s)
            for fx in (0.0, 0.5, 1.0):
                d.line([int(w * fx), 0, int(w * fx), h], fill=beam,
                       width=width)
            for fy in (0.0, 0.58, 1.0):
                d.line([0, int(h * fy), w, int(h * fy)], fill=beam,
                       width=width)
            d.line([int(w * 0.5), int(h * 0.58), w, 0], fill=beam,
                   width=width)
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


def draw_fitting_swatch(kind, style, size=(64, 44)):
    """A small picture of a style of window or door, for the choice of look.
    `kind` is "window" or "door"."""
    s = SUPER
    w, h = size[0] * s, size[1] * s
    img = Image.new("RGB", (w, h), (226, 215, 192))
    d = ImageDraw.Draw(img)
    cx = w // 2

    stone = (160, 158, 152)
    glass = (176, 216, 240)
    wood = (92, 58, 36)
    iron = (52, 54, 60)

    def darker(rgb, f):
        return tuple(max(0, min(255, int(v * f))) for v in rgb)

    def arch_mask(x0, y0, x1, y1):
        """A rectangle with a half circle on top."""
        mask = Image.new("L", (w, h), 0)
        m = ImageDraw.Draw(mask)
        r = (x1 - x0) // 2
        m.rectangle([x0, y0 + r, x1, y1], fill=255)
        m.ellipse([x0, y0, x1, y0 + 2 * r], fill=255)
        return mask

    def paste_arch(colour, box):
        img.paste(Image.new("RGB", (w, h), colour), (0, 0), arch_mask(*box))

    if kind == "window" and style == "castle":
        sw, sh = 10 * s, 34 * s
        x0, y0 = cx - sw // 2, (h - sh) // 2
        paste_arch(stone, (x0 - 3 * s, y0 - 2 * s, x0 + sw + 3 * s,
                           y0 + sh + 2 * s))
        paste_arch((18, 16, 18), (x0, y0, x0 + sw, y0 + sh))
        d.rectangle([x0 - 5 * s, y0 + sh + 2 * s, x0 + sw + 5 * s,
                     y0 + sh + 4 * s], fill=darker(stone, 1.1),
                    outline=darker(stone, 0.55))

    elif kind == "window" and style == "stained":
        ww, wh = 20 * s, 32 * s
        x0, y0 = cx - ww // 2, (h - wh) // 2
        paste_arch((38, 38, 44), (x0 - 2 * s, y0 - 2 * s, x0 + ww + 2 * s,
                                  y0 + wh + 2 * s))
        layer = Image.new("RGB", (w, h), (38, 38, 44))
        ld = ImageDraw.Draw(layer)
        colours = [(46, 87, 199), (204, 43, 51), (242, 194, 46),
                   (46, 153, 87), (148, 71, 168)]
        cols, rows = 3, 5
        for i in range(cols):
            for j in range(rows):
                ld.rectangle([x0 + i * ww // cols + s // 2,
                              y0 + j * wh // rows + s // 2,
                              x0 + (i + 1) * ww // cols - s // 2,
                              y0 + (j + 1) * wh // rows - s // 2],
                             fill=colours[(i * 2 + j * 3 + i * j) % 5])
        img.paste(layer, (0, 0), arch_mask(x0, y0, x0 + ww, y0 + wh))

    elif kind == "window":
        ww, wh = 22 * s, 28 * s
        x0, y0 = cx - ww // 2, (h - wh) // 2 - s
        x1, y1 = x0 + ww, y0 + wh
        if style == "stone":
            f = 4 * s
            edge = darker(stone, 0.55)
            d.rectangle([x0 - f, y0 - f, x1 + f, y1 + f], fill=stone,
                        outline=edge)
            for k in range(1, 4):
                yy = y0 - f + (wh + 2 * f) * k // 4
                d.line([x0 - f, yy, x0, yy], fill=edge)
                d.line([x1, yy, x1 + f, yy], fill=edge)
            d.rectangle([x0 - f - 2 * s, y1 + f, x1 + f + 2 * s,
                         y1 + f + 3 * s], fill=darker(stone, 1.08),
                        outline=edge)
            bar = darker(stone, 0.85)
        else:
            f = 2 * s
            d.rectangle([x0 - f, y0 - f, x1 + f, y1 + f], fill=wood)
            d.rectangle([x0 - f - s, y1 + f, x1 + f + s, y1 + f + 2 * s],
                        fill=wood)
            bar = wood
        d.rectangle([x0, y0, x1, y1], fill=glass)
        d.line([cx, y0, cx, y1], fill=bar, width=max(1, int(1.5 * s)))
        d.line([x0, (y0 + y1) // 2, x1, (y0 + y1) // 2], fill=bar,
               width=max(1, int(1.5 * s)))

    else:                                   # a door
        dw, dh = 22 * s, 36 * s
        x0, y1 = cx - dw // 2, h - 2 * s
        y0 = y1 - dh
        plank = {"iron": (98, 62, 36),
                 "studded": (78, 50, 28)}.get(style, (112, 72, 42))
        paste_arch(darker(wood, 0.7), (x0 - 2 * s, y0 - 2 * s, x0 + dw + 2 * s,
                                       y1))
        layer = Image.new("RGB", (w, h), plank)
        ld = ImageDraw.Draw(layer)
        for k in range(5):
            ld.line([x0 + k * dw // 5, y0, x0 + k * dw // 5, y1],
                    fill=darker(plank, 0.7), width=max(1, s))
        if style == "iron":
            for t in (0.2, 0.5, 0.8):
                yy = y1 - int(dh * t)
                ld.rectangle([x0, yy - 2 * s, x0 + dw, yy + 2 * s], fill=iron)
        elif style == "studded":
            for t in (0.28, 0.66):
                yy = y1 - int(dh * t)
                ld.polygon([(x0, yy - 2 * s), (x0 + int(dw * 0.65), yy - 2 * s),
                            (x0 + int(dw * 0.78), yy),
                            (x0 + int(dw * 0.65), yy + 2 * s),
                            (x0, yy + 2 * s)], fill=iron)
            for i in range(3):
                for j in range(5):
                    sx = x0 + dw * (2 * i + 1) // 6
                    sy = y1 - int(dh * (0.1 + 0.6 * j / 4))
                    ld.ellipse([sx - s, sy - s, sx + s, sy + s],
                               fill=(150, 152, 160))
        else:
            for t in (0.25, 0.62):
                yy = y1 - int(dh * t)
                ld.rectangle([x0, yy - s, x0 + 5 * s, yy + s],
                             fill=darker(wood, 0.55))
        kx, ky = x0 + int(dw * 0.74), y1 - int(dh * 0.42)
        if style == "wood":
            ld.ellipse([kx - 2 * s, ky - 2 * s, kx + 2 * s, ky + 2 * s],
                       fill=(200, 160, 60))
        else:
            ld.ellipse([kx - 3 * s, ky - 3 * s, kx + 3 * s, ky + 3 * s],
                       outline=iron, width=max(1, s))
        img.paste(layer, (0, 0), arch_mask(x0, y0, x0 + dw, y1))

    return img.resize(size, Image.LANCZOS)