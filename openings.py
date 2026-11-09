"""Door and windows: how they look and where they go on a wall."""

from __future__ import annotations

from reportlab.lib.units import cm

from drawing import meters
from fittings import door, round_window, window

# ============================================================
# DOOR AND WINDOWS
# ============================================================

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
    # A copy of the wall that has no door gets its windows as any other wall.
    # (When the door is in the centre the same layout is kept, with a window
    # in place of the door; with the door on the left or on the right that
    # would be a window too many, next to the other ones)
    if door_layout and not door_present and cfg.door_position != "center":
        door_layout = False

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
            door(c, cx, base, door_width(cfg, width_cm), h, cfg.door_arched,
                 cfg.door_style)
        else:
            wh = min(meters(cfg, cfg.window_height_m), floor_height * 0.6)
            sill = min(meters(cfg, cfg.window_sill_m),
                       floor_height - wh - 0.2 * cm)
            window(c, cx, base + sill + wh / 2,
                   meters(cfg, cfg.window_width_m), wh,
                   style=cfg.window_style)
