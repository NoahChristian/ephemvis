#!/usr/bin/env python3
"""
vedic_chart.py — the Vedic (Jyotiṣa) rāśi chart as a self-contained SVG.  [SHIP]

Vedic charts are drawn as **squares**, not wheels. This renders the two classic diagram
styles from a **sidereal** chart:

* ``style="south"`` — the South-Indian chart: a fixed 4×4 grid whose twelve perimeter
  cells hold the twelve rāśis in *fixed* positions (Pisces top-left, running clockwise);
  the grahas are placed into their rāśi's cell and the Lagna (Ascendant) cell is marked.
* ``style="north"`` — the North-Indian chart: a fixed diamond of twelve houses (the 1st
  house always the top-center diamond), with the rāśi *number* in each house and the
  grahas placed by house from the Lagna.

Input is the chart dict openephem's ``assemble(..., zodiac="sidereal")`` returns — it needs
``bodies`` and ``angles.asc``. Pure drawing; positions are computed upstream.
"""

from __future__ import annotations

import math

from .profection_wheel import theme_lord_colors
from .wheel import PALETTES, SIGN_GLYPHS, SYM_FAMILY, TXT_FAMILY, font_face_css

# the nine grahas (Rāhu = the north node, Ketu = its opposite point). Classical Vedic uses
# these only — the outer planets are omitted.
_GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
_GLYPH = {"Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿", "Jupiter": "♃",
          "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"}
_RASHI = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula",
          "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
# grahas take the suite's theme-derived lord colors (same Chaldean order + node colors as the
# firdaria / decennials / daśā renderers, so a planet reads the same color everywhere).
_CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
_NODE_COLOR = {"Rahu": "#0e8d92", "Ketu": "#a9782f"}


def _lord_colors(theme):
    return {**theme_lord_colors(theme, _CHALDEAN), **_NODE_COLOR}
# South-Indian fixed cell for each sign index (0 = Aries), in a 4×4 grid (row, col): the signs
# run clockwise from Pisces at the top-left corner.
_SOUTH_CELL = {11: (0, 0), 0: (0, 1), 1: (0, 2), 2: (0, 3),
               3: (1, 3), 4: (2, 3), 5: (3, 3),
               6: (3, 2), 7: (3, 1), 8: (3, 0),
               9: (2, 0), 10: (1, 0)}
_SYM = SYM_FAMILY        # embedded symbol family (or system fallback)
_UI = TXT_FAMILY         # embedded text family (or system-ui)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _varga_label(chart: dict) -> str:
    """The divisional label ("D-9 Navāṃśa", or "D-1 Rāśi") from a chart's ``varga`` tag."""
    vg = chart.get("varga")
    if vg and vg.get("division"):
        return f"D-{vg['division']} {vg.get('name', '')}".strip()
    return "D-1 Rāśi"


def _grahas_by_sign(chart: dict):
    """(sign_index -> [(name, deg_in_sign, retro)]) for the nine grahas, sidereal."""
    bodies = chart.get("bodies") or {}
    node = bodies.get("TrueNode") or bodies.get("MeanNode")
    node_lon = float(node["lon"]) if node else None
    out: dict[int, list] = {}
    for g in _GRAHAS:
        if g == "Rahu":
            lon = node_lon
            retro = True
        elif g == "Ketu":
            lon = (node_lon + 180.0) if node_lon is not None else None
            retro = True
        else:
            b = bodies.get(g)
            lon = float(b["lon"]) if b else None
            retro = bool(b.get("retro")) if b else False
        if lon is None:
            continue
        lon %= 360.0
        out.setdefault(int(lon // 30), []).append((g, lon % 30.0, retro))
    return out


def _render_south(chart, pal, lord_col, size, title):
    ink, bg, line, muted = (pal["planet"], pal["bg"][0], pal["cusp"], pal["deg"])
    asc = (chart.get("angles") or {}).get("asc")
    asc_sign = int(asc // 30) % 12 if asc is not None else None
    by_sign = _grahas_by_sign(chart)

    m = size * 0.06
    G = size - 2 * m
    cs = G / 4.0
    fs_sign = cs * 0.194                             # rāśi glyph, averaged with the East chart's
    fs_body = cs * 0.32
    fs_deg = cs * 0.22

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
         f'width="{size}" height="{size}" role="img" aria-label="{_esc(title)}">']
    P.append(f'<rect width="{size}" height="{size}" fill="{bg}"/>')
    # outer frame + the grid lines, but the middle segments are omitted so the central 2×2 reads
    # as ONE open square (the traditional South-Indian center panel), not four cells.
    P.append(f'<rect x="{m:.1f}" y="{m:.1f}" width="{G:.1f}" height="{G:.1f}" fill="none" '
             f'stroke="{line}" stroke-width="2"/>')
    lo, hi = m + cs, m + 3 * cs        # the central block spans cols/rows 1..3
    for i in (1, 2, 3):
        gx, gy = m + i * cs, m + i * cs
        if i == 2:                     # split the middle lines around the center square
            P.append(f'<line x1="{gx:.1f}" y1="{m:.1f}" x2="{gx:.1f}" y2="{lo:.1f}" stroke="{line}" stroke-width="1.2"/>')
            P.append(f'<line x1="{gx:.1f}" y1="{hi:.1f}" x2="{gx:.1f}" y2="{m+G:.1f}" stroke="{line}" stroke-width="1.2"/>')
            P.append(f'<line x1="{m:.1f}" y1="{gy:.1f}" x2="{lo:.1f}" y2="{gy:.1f}" stroke="{line}" stroke-width="1.2"/>')
            P.append(f'<line x1="{hi:.1f}" y1="{gy:.1f}" x2="{m+G:.1f}" y2="{gy:.1f}" stroke="{line}" stroke-width="1.2"/>')
        else:
            P.append(f'<line x1="{gx:.1f}" y1="{m:.1f}" x2="{gx:.1f}" y2="{m+G:.1f}" stroke="{line}" stroke-width="1.2"/>')
            P.append(f'<line x1="{m:.1f}" y1="{gy:.1f}" x2="{m+G:.1f}" y2="{gy:.1f}" stroke="{line}" stroke-width="1.2"/>')

    def _graha(px, gy, name, deg, retro, gsc):
        rx, dcol = ("℞", pal["degRx"]) if retro else ("", muted)   # retrograde → red degree + ℞
        return (f'<text x="{px:.1f}" y="{gy:.1f}" text-anchor="end" dominant-baseline="central" '
                f'fill="{lord_col.get(name, ink)}" font-family="{_SYM}" '
                f'font-size="{fs_body*gsc:.1f}">{_esc(_GLYPH[name])}︎'
                f'<tspan font-family="{_UI}" font-size="{fs_deg*gsc:.1f}" fill="{dcol}" '
                f'dx="2">{int(deg)}°{rx}</tspan></text>')

    for sidx in range(12):
        r, c = _SOUTH_CELL[sidx]
        x, y = m + c * cs, m + r * cs
        # rāśi glyph tucked into the cell's top-left corner, small so the grahas own the cell;
        # the Lagna's glyph goes red to match its 'La' and box.
        sgcol = pal["degRx"] if sidx == asc_sign else muted
        P.append(f'<text x="{x+cs*0.16:.1f}" y="{y+cs*0.16:.1f}" text-anchor="middle" '
                 f'dominant-baseline="central" fill="{sgcol}" '
                 f'font-family="{_SYM}" font-size="{fs_sign:.1f}">{SIGN_GLYPHS[sidx]}︎</text>')
        # Lagna: red cell outline + a small red "La" beside the sign (no crossing diagonal)
        if sidx == asc_sign:
            P.append(f'<rect x="{x+cs*0.015:.1f}" y="{y+cs*0.015:.1f}" width="{cs*0.97:.1f}" '
                     f'height="{cs*0.97:.1f}" fill="none" stroke="{pal["degRx"]}" '
                     f'stroke-width="{cs*0.03:.1f}"/>')
            P.append(f'<text x="{x+cs*0.34:.1f}" y="{y+cs*0.16:.1f}" fill="{pal["degRx"]}" '
                     f'font-family="{_UI}" font-size="{cs*0.13:.1f}" font-weight="600" '
                     f'text-anchor="start" dominant-baseline="central">La</text>')
        # grahas: a uniform, slightly-reduced size, right-justified and listed from the TOP downward
        # beside the sign, with a row step wider than the glyph so they never touch. One right-hand
        # column; on overrun the overflow wraps into a second column tucked under the sign.
        planets = by_sign.get(sidx, [])
        n = len(planets)
        if not n:
            continue
        rtop, rbot, step = cs * 0.16, cs * 0.90, cs * 0.235
        maxrows = max(1, int((rbot - rtop) / step) + 1)      # rows that fit at the nice size (~4)
        if n <= maxrows:                                     # one right-hand column, nice size
            for j, (nm, dg, rt) in enumerate(planets):
                P.append(_graha(x + cs * 0.95, y + rtop + j * step, nm, dg, rt, 0.564))
        else:                                                # overflow → two columns, each ≤ half wide
            half = (n + 1) // 2
            g2, st2 = 0.353, cs * 0.185                        # smaller so a column fits half the cell
            for j, (nm, dg, rt) in enumerate(planets[:half]):
                P.append(_graha(x + cs * 0.95, y + cs * 0.16 + j * st2, nm, dg, rt, g2))
            for j, (nm, dg, rt) in enumerate(planets[half:]):
                P.append(_graha(x + cs * 0.47, y + cs * 0.42 + j * st2, nm, dg, rt, g2))

    # center 2×2: title
    cx = m + 2 * cs
    P.append(f'<text x="{cx:.1f}" y="{cx-cs*0.18:.1f}" text-anchor="middle" fill="{ink}" '
             f'font-family="{_UI}" font-size="{cs*0.34:.1f}" font-weight="700">{_esc(title)}</text>')
    P.append(f'<text x="{cx:.1f}" y="{cx+cs*0.08:.1f}" text-anchor="middle" fill="{muted}" '
             f'font-family="{_UI}" font-size="{cs*0.16:.1f}">{_esc(_varga_label(chart))} · South Indian</text>')
    if asc_sign is not None:
        P.append(f'<text x="{cx:.1f}" y="{cx+cs*0.34:.1f}" text-anchor="middle" fill="{muted}" '
                 f'font-family="{_UI}" font-size="{cs*0.16:.1f}">Lagna {_RASHI[asc_sign]}</text>')
    P.append(font_face_css())
    P.append("</svg>")
    return "\n".join(P)


# North-Indian houses are FIXED (1st = top-center diamond), numbered counter-clockwise. Each house
# is a polygon in unit-square coords (y down); `_NORTH_HOUSE[h]` = (polygon points, label anchor).
_C = {"TL": (0, 0), "TR": (1, 0), "BR": (1, 1), "BL": (0, 1),
      "T": (0.5, 0), "R": (1, 0.5), "B": (0.5, 1), "L": (0, 0.5), "O": (0.5, 0.5),
      "tl": (0.25, 0.25), "tr": (0.75, 0.25), "br": (0.75, 0.75), "bl": (0.25, 0.75)}
_NORTH_HOUSE = {
    1:  (("T", "tr", "O", "tl"), (0.5, 0.26)),      # top-center diamond = Lagna
    2:  (("T", "tl", "TL"), (0.25, 0.13)),          # each corner triangle: anchored in its body,
    3:  (("TL", "tl", "L"), (0.13, 0.25)),          # pulled just off the frame edge (not into the
    4:  (("L", "tl", "O", "bl"), (0.25, 0.5)),      # narrow tip) so a 2-graha stack + degree clears
    5:  (("L", "bl", "BL"), (0.13, 0.75)),
    6:  (("BL", "bl", "B"), (0.25, 0.87)),
    7:  (("B", "bl", "O", "br"), (0.5, 0.74)),      # bottom diamond
    8:  (("B", "br", "BR"), (0.75, 0.87)),
    9:  (("BR", "br", "R"), (0.87, 0.75)),
    10: (("R", "br", "O", "tr"), (0.75, 0.5)),      # right diamond
    11: (("R", "tr", "TR"), (0.87, 0.25)),
    12: (("TR", "tr", "T"), (0.75, 0.13)),
}


def _north_is_corner(p):
    return p[0] in (0.0, 1.0) and p[1] in (0.0, 1.0)


def _north_is_edgemid(p):
    return (p[0] in (0.0, 1.0)) ^ (p[1] in (0.0, 1.0))


def _north_diamond_plan(n):
    """Row plan for a North diamond: ``(t, count)`` per row, ``t`` the median fraction from the
    outer vertex (0) toward the center (1). Rows widen toward the middle then narrow, tracing the
    rhombus — a centered diamond of grahas above the number, which sits low near the center."""
    presets = {
        1: [(0.46, 1)],
        2: [(0.34, 1), (0.58, 1)],
        3: [(0.30, 1), (0.54, 2)],
        4: [(0.26, 1), (0.48, 2), (0.68, 1)],
        5: [(0.26, 1), (0.46, 2), (0.64, 2)],
        6: [(0.24, 1), (0.42, 2), (0.58, 2), (0.72, 1)],
        7: [(0.24, 1), (0.42, 3), (0.60, 2), (0.74, 1)],
    }
    if n <= 0:
        return []
    return presets.get(n, presets[7])


def _north_diamond_pts(poly_u, n):
    """Placement points inside a North diamond (houses 1/4/7/10), arranged as a diamond that
    follows the rhombus. Works in the diamond's own axes (``e1``, ``e2`` from the outer vertex),
    so it rotates correctly for all four houses; the rāśi number is placed low by
    :func:`_north_number_u`, and the grahas form a centered diamond above it."""
    ov = next(p for p in poly_u if _north_is_edgemid(p))
    s1, s2 = [p for p in poly_u if p != ov and p != (0.5, 0.5)]
    e1 = (s1[0] - ov[0], s1[1] - ov[1])
    e2 = (s2[0] - ov[0], s2[1] - ov[1])
    cg = 0.22                                     # lateral gap between grahas in a row (fits a label)
    pts = []
    for t, cnt in _north_diamond_plan(n):
        lim = min(t, 1 - t) * 0.92                # stay inside the rhombus at this median position
        for i in range(cnt):
            cross = max(-lim, min(lim, (i - (cnt - 1) / 2) * cg))
            a, b = t + cross, t - cross
            pts.append((ov[0] + a * e1[0] + b * e2[0], ov[1] + a * e1[1] + b * e2[1]))
    return pts[:n]


def _north_tri_plan(n):
    """Row plan for a North triangle: a list of ``(s, count)`` where ``s = u+v`` is the fraction
    from the apex (right-angle vertex) toward the hypotenuse and ``count`` grahas sit on that row.
    Rows fill toward the frame and widen as they go, so the central apex stays free for the number
    (a base-heavy pyramid). Presets 1–6 are hand-placed; larger counts fall back to 3 even rows."""
    presets = {
        1: [(0.58, 1)],
        2: [(0.64, 2)],
        3: [(0.48, 1), (0.80, 2)],
        4: [(0.50, 1), (0.82, 3)],
        5: [(0.52, 2), (0.84, 3)],
        6: [(0.44, 1), (0.66, 2), (0.88, 3)],
    }
    if n in presets:
        return presets[n]
    if n <= 0:
        return []
    rows = (0.44, 0.66, 0.88)
    counts = [n // 3, n // 3, n // 3]
    for k in range(n % 3):
        counts[2 - k] += 1                        # spill into the wider outer rows first
    return [(rows[i], counts[i]) for i in range(3) if counts[i] > 0]


def _north_tri_pts(poly_u, n):
    """Placement points inside a North triangle (the eight non-angular houses). The right angle is
    at the interior diagonal point ``rv``; the hypotenuse lies on the frame. Grahas fill in rows
    parallel to the hypotenuse, widening toward the frame, so the apex (``rv``, the most central
    corner) is left clear for the rāśi number placed by :func:`_north_number_u`."""
    rv = min(poly_u, key=lambda p: (p[0] - 0.5) ** 2 + (p[1] - 0.5) ** 2)
    others = [p for p in poly_u if p != rv]
    corner_v = next(p for p in others if _north_is_corner(p))
    emid_v = next(p for p in others if p != corner_v)
    ec = (corner_v[0] - rv[0], corner_v[1] - rv[1])   # leg toward the frame corner
    ee = (emid_v[0] - rv[0], emid_v[1] - rv[1])        # leg toward the frame edge-midpoint
    pts = []
    for s, cnt in _north_tri_plan(n):
        for i in range(cnt):
            w = (i + 1) / (cnt + 1)               # position across the row, insetting from the legs
            u, v = s * (1 - w), s * w
            pts.append((rv[0] + u * ec[0] + v * ee[0], rv[1] + u * ec[1] + v * ee[1]))
    return pts[:n]


def _north_number_u(h, poly_u):
    """Where house ``h``'s rāśi number sits (unit coords) — pulled toward the chart center.
    Diamonds → near the central junction (the inner vertex O); triangles → tucked against the
    innermost right-angle corner, on the bisector toward the hypotenuse so it stays off both leg
    edges and clear of the grahas, which fill the outer rows away from the corner."""
    if h in (1, 4, 7, 10):
        ov = next(p for p in poly_u if _north_is_edgemid(p))
        return (ov[0] + 0.85 * (0.5 - ov[0]), ov[1] + 0.85 * (0.5 - ov[1]))
    rv = min(poly_u, key=lambda p: (p[0] - 0.5) ** 2 + (p[1] - 0.5) ** 2)
    others = [p for p in poly_u if p != rv]
    hypmid = ((others[0][0] + others[1][0]) / 2, (others[0][1] + others[1][1]) / 2)
    return (rv[0] + 0.20 * (hypmid[0] - rv[0]), rv[1] + 0.20 * (hypmid[1] - rv[1]))


def _render_north(chart, pal, lord_col, size, title):
    ink, bg, line, muted = (pal["planet"], pal["bg"][0], pal["cusp"], pal["deg"])
    asc = (chart.get("angles") or {}).get("asc")
    asc_sign = int(asc // 30) % 12
    by_sign = _grahas_by_sign(chart)
    m = size * 0.07
    G = size - 2 * m

    def pt(u):
        return (m + _C[u][0] * G, m + _C[u][1] * G)

    def xy(uxy):
        return (m + uxy[0] * G, m + uxy[1] * G)

    fs_num = G * 0.050                               # a touch smaller now the numbers sit central
    fs_body = G * 0.050
    fs_deg = G * 0.034

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
         f'width="{size}" height="{size}" role="img" aria-label="{_esc(title)}">']
    P.append(f'<rect width="{size}" height="{size}" fill="{bg}"/>')
    P.append(f'<rect x="{m:.1f}" y="{m:.1f}" width="{G:.1f}" height="{G:.1f}" fill="none" '
             f'stroke="{line}" stroke-width="2"/>')
    for a, b in (("TL", "BR"), ("TR", "BL")):        # the two diagonals
        (x1, y1), (x2, y2) = pt(a), pt(b)
        P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{line}" stroke-width="1.2"/>')
    dia = " ".join(f"{pt(u)[0]:.1f},{pt(u)[1]:.1f}" for u in ("T", "R", "B", "L"))
    P.append(f'<polygon points="{dia}" fill="none" stroke="{line}" stroke-width="1.2"/>')
    # Lagna house (house 1, the top-center diamond) gets a red border instead of the default line
    lag = " ".join(f"{pt(u)[0]:.1f},{pt(u)[1]:.1f}" for u in _NORTH_HOUSE[1][0])
    P.append(f'<polygon points="{lag}" fill="none" stroke="{pal["degRx"]}" stroke-width="2.4"/>')

    diamonds = {1, 4, 7, 10}
    gsc = 1.116                                      # uniform graha scale across the whole chart
    bf, df = fs_body * gsc, fs_deg * gsc
    for h in range(1, 13):
        keys, _anchor = _NORTH_HOUSE[h]
        poly_u = [_C[k] for k in keys]
        sign_idx = (asc_sign + h - 1) % 12          # whole-sign: house 1 = Lagna's sign
        planets = by_sign.get(sign_idx, [])
        nx, ny = xy(_north_number_u(h, poly_u))     # rāśi number, off in its own reserved spot
        P.append(f'<text x="{nx:.1f}" y="{ny:.1f}" text-anchor="middle" dominant-baseline="central" '
                 f'fill="{muted}" font-family="{_UI}" font-size="{fs_num:.1f}">{sign_idx + 1}</text>')
        if h == 1:                                   # mark the Lagna: a small red 'La' above the number
            P.append(f'<text x="{nx:.1f}" y="{ny - fs_num*1.05:.1f}" text-anchor="middle" '
                     f'dominant-baseline="central" fill="{pal["degRx"]}" font-family="{_UI}" '
                     f'font-size="{fs_deg*1.1:.1f}" font-weight="700" letter-spacing="1">La</text>')
        if not planets:
            continue
        pts = (_north_diamond_pts(poly_u, len(planets)) if h in diamonds
               else _north_tri_pts(poly_u, len(planets)))
        for (name, deg, retro), pu in zip(planets, pts, strict=False):
            px, py = xy(pu)
            rx, dcol = ("℞", pal["degRx"]) if retro else ("", muted)   # retrograde → red degree + ℞
            P.append(f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="middle" '
                     f'dominant-baseline="central" fill="{lord_col.get(name, ink)}" font-family="{_SYM}" '
                     f'font-size="{bf:.1f}">{_esc(_GLYPH[name])}︎'
                     f'<tspan font-family="{_UI}" font-size="{df:.1f}" fill="{dcol}" '
                     f'dx="1">{int(deg)}{rx}</tspan></text>')

    P.append(f'<text x="{m:.1f}" y="{m - size*0.022:.1f}" fill="{ink}" font-family="{_UI}" '
             f'font-size="{size*0.03:.1f}" font-weight="700">{_esc(title)}</text>')
    P.append(f'<text x="{m+G:.1f}" y="{m - size*0.022:.1f}" text-anchor="end" fill="{muted}" '
             f'font-family="{_UI}" font-size="{size*0.021:.1f}">{_esc(_varga_label(chart))} · '
             f'North Indian · Lagna {_RASHI[asc_sign]}</text>')
    P.append(font_face_css())
    P.append("</svg>")
    return "\n".join(P)


# East-Indian (Bengali) layout: a 3×3 grid whose four corner cells are each split by a diagonal
# into two triangles → 8 triangles + 4 edge squares = 12 houses, with a central info box. Houses
# are FIXED (like the North-Indian chart): house 1 is the LEFT-CENTER square (holding the rising
# sign) and the numbering runs CLOCKWISE from there; each house shows its whole-sign rāśi. The
# polygons are listed in that house order (index 0 = house 1).
_ET, _ETT = 1 / 3.0, 2 / 3.0
_EAST_HOUSES = [
    [(0, _ET), (_ET, _ET), (_ET, _ETT), (0, _ETT)],       # 1  left-center square (Lagna)
    [(0, 0), (_ET, _ET), (0, _ET)],                        # 2  top-left, left triangle
    [(0, 0), (_ET, 0), (_ET, _ET)],                        # 3  top-left, upper triangle
    [(_ET, 0), (_ETT, 0), (_ETT, _ET), (_ET, _ET)],        # 4  top-center square
    [(_ETT, 0), (1, 0), (_ETT, _ET)],                      # 5  top-right, upper triangle
    [(1, 0), (1, _ET), (_ETT, _ET)],                       # 6  top-right, right triangle
    [(_ETT, _ET), (1, _ET), (1, _ETT), (_ETT, _ETT)],      # 7  right-center square
    [(1, _ETT), (1, 1), (_ETT, _ETT)],                     # 8  bottom-right, right triangle
    [(_ETT, 1), (1, 1), (_ETT, _ETT)],                     # 9  bottom-right, lower triangle
    [(_ET, _ETT), (_ETT, _ETT), (_ETT, 1), (_ET, 1)],      # 10 bottom-center square
    [(0, 1), (_ET, 1), (_ET, _ETT)],                       # 11 bottom-left, lower triangle
    [(0, _ETT), (_ET, _ETT), (0, 1)],                      # 12 bottom-left, left triangle
]
# Where each house's zodiac glyph sits (unit coords): triangles → tucked at the square's OUTER
# corner (on the triangle's own outer edge, so the two sharing a corner don't clash); edge squares
# → centered on the OUTER edge.
_EAST_SIGN_ANCHOR = [
    (0.045, 0.50),   # 1  left-center square — left edge, centered
    (0.05, 0.135),   # 2  top-left, left triangle — left edge by the corner
    (0.135, 0.05),   # 3  top-left, upper triangle — top edge by the corner
    (0.50, 0.045),   # 4  top-center square — top edge, centered
    (0.865, 0.05),   # 5  top-right, upper triangle — top edge by the corner
    (0.955, 0.135),  # 6  top-right, right triangle — right edge by the corner
    (0.955, 0.50),   # 7  right-center square — right edge, centered
    (0.955, 0.865),  # 8  bottom-right, right triangle — right edge by the corner
    (0.865, 0.955),  # 9  bottom-right, lower triangle — bottom edge by the corner
    (0.50, 0.955),   # 10 bottom-center square — bottom edge, centered
    (0.135, 0.955),  # 11 bottom-left, lower triangle — bottom edge by the corner
    (0.05, 0.865),   # 12 bottom-left, left triangle — left edge by the corner
]


def _render_east(chart, pal, lord_col, size, title):
    ink, bg, line, muted, accent = (pal["planet"], pal["bg"][0], pal["cusp"],
                                    pal["deg"], pal["aHard"])
    asc = (chart.get("angles") or {}).get("asc")
    asc_sign = int(asc // 30) % 12
    by_sign = _grahas_by_sign(chart)
    m = size * 0.06
    G = size - 2 * m
    fs_sign, fs_body, fs_deg = G * 0.0485, G * 0.050, G * 0.034   # sign glyph averaged with South's

    def X(u):
        return m + u * G

    def Y(v):
        return m + v * G

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
         f'width="{size}" height="{size}" role="img" aria-label="{_esc(title)}">']
    P.append(f'<rect width="{size}" height="{size}" fill="{bg}"/>')
    P.append(f'<rect x="{m:.1f}" y="{m:.1f}" width="{G:.1f}" height="{G:.1f}" fill="none" '
             f'stroke="{line}" stroke-width="2"/>')
    for u in (_ET, _ETT):
        P.append(f'<line x1="{X(u):.1f}" y1="{Y(0):.1f}" x2="{X(u):.1f}" y2="{Y(1):.1f}" '
                 f'stroke="{line}" stroke-width="1.2"/>')
        P.append(f'<line x1="{X(0):.1f}" y1="{Y(u):.1f}" x2="{X(1):.1f}" y2="{Y(u):.1f}" '
                 f'stroke="{line}" stroke-width="1.2"/>')
    for (u1, v1, u2, v2) in ((0, 0, _ET, _ET), (1, 0, _ETT, _ET),
                             (1, 1, _ETT, _ETT), (0, 1, _ET, _ETT)):   # corner diagonals
        P.append(f'<line x1="{X(u1):.1f}" y1="{Y(v1):.1f}" x2="{X(u2):.1f}" y2="{Y(v2):.1f}" '
                 f'stroke="{line}" stroke-width="1.2"/>')

    def _egraha(px, py, name, deg, retro, g):
        rx, dcol = ("℞", pal["degRx"]) if retro else ("", muted)   # retrograde → red degree + ℞
        return (f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="middle" dominant-baseline="central" '
                f'fill="{lord_col.get(name, ink)}" font-family="{_SYM}" font-size="{fs_body*g:.1f}">'
                f'{_esc(_GLYPH[name])}︎<tspan font-family="{_UI}" font-size="{fs_deg*g:.1f}" '
                f'fill="{dcol}" dx="1">{int(deg)}{rx}</tspan></text>')

    for i, poly in enumerate(_EAST_HOUSES):
        rashi = (asc_sign + i) % 12                    # whole-sign: house 1 = rising sign
        is_lagna = (i == 0)
        if is_lagna:                                   # outline the Lagna house
            pts = " ".join(f"{X(u):.1f},{Y(v):.1f}" for u, v in poly)
            P.append(f'<polygon points="{pts}" fill="none" stroke="{accent}" '
                     f'stroke-width="{G*0.006:.1f}"/>')
        # zodiac glyph: triangles → outer corner, squares → centered on the outer edge
        sgx, sgy = _EAST_SIGN_ANCHOR[i]
        scol = accent if is_lagna else muted
        P.append(f'<text x="{X(sgx):.1f}" y="{Y(sgy):.1f}" text-anchor="middle" '
                 f'dominant-baseline="central" fill="{scol}" font-family="{_SYM}" '
                 f'font-size="{fs_sign:.1f}">{SIGN_GLYPHS[rashi]}︎</text>')
        if is_lagna:                                   # Lagna: a small red 'La' just above the rising sign
            P.append(f'<text x="{X(sgx):.1f}" y="{Y(sgy) - fs_sign*0.95:.1f}" text-anchor="middle" '
                     f'dominant-baseline="central" fill="{pal["degRx"]}" font-family="{_UI}" '
                     f'font-size="{fs_sign*0.8:.1f}" font-weight="700" letter-spacing="1">La</text>')
        planets = by_sign.get(rashi, [])
        n = len(planets)
        if not n:
            continue
        if len(poly) == 4:                            # SQUARE — content box = the rest of the cell
            us = [p[0] for p in poly]
            vs = [p[1] for p in poly]
            u0, u1_, v0, v1_ = min(us), max(us), min(vs), max(vs)
            # reserve twice the sign's edge-gap (edge→sign, then sign→content box); the other
            # three sides get a thin pad, so the content box is the rest of the square.
            res, pad = 0.15, 0.02                     # wider gap between the rāśi sign and the grahas
            gu0, gu1, gv0, gv1 = u0 + pad, u1_ - pad, v0 + pad, v1_ - pad
            if sgx < u0 + 0.10:
                gu0 = u0 + res
            elif sgx > u1_ - 0.10:
                gu1 = u1_ - res
            if sgy < v0 + 0.10:
                gv0 = v0 + res
            elif sgy > v1_ - 0.10:
                gv1 = v1_ - res
            cols = 1 if n <= 3 else 2
            rows = math.ceil(n / cols)
            gsc = 0.902                               # uniform with the triangles
            for k, (nm, dg, rt) in enumerate(planets):
                cc, rr = k // rows, k % rows          # column-major: fill down, then next column
                px = gu0 + (cc + 0.5) / cols * (gu1 - gu0)
                py = gv0 + (rr + 0.5) / rows * (gv1 - gv0)
                P.append(_egraha(X(px), Y(py), nm, dg, rt, gsc))
        else:                                         # TRIANGLE — one columnar grid over the content
            # Local axes at the right-angle vertex: a1 runs toward the outer corner (the glyph's
            # sub-triangle) and a2 toward the inner apex. The content box is the inner square
            # (a1,a2 ≤ L/2) plus the apex sub-triangle (a1+a2 ≤ L), so we lay a grid there, fill the
            # 2×2 square first, then let the columns extend toward the apex (which reads as "under"
            # or "to the left" etc. depending on the triangle's orientation).
            corner = next(p for p in poly if p[0] in (0.0, 1.0) and p[1] in (0.0, 1.0))
            inner = min(poly, key=lambda p: math.hypot(p[0] - 0.5, p[1] - 0.5))
            right = next(p for p in poly if p not in (corner, inner))
            leg = math.hypot(corner[0] - right[0], corner[1] - right[1])
            a1h = ((corner[0] - right[0]) / leg, (corner[1] - right[1]) / leg)   # toward glyph
            a2h = ((inner[0] - right[0]) / leg, (inner[1] - right[1]) / leg)     # toward apex
            d, inset = leg * 0.26, leg * 0.16        # wider step + more padding off the outer frame
            cells = []                                # two columns (a1), extending in a2 toward apex
            for icol in (0, 1):
                a1v = inset + icol * d
                if a1v > leg * 0.5:
                    continue
                j = 0
                while inset + j * d <= leg - a1v - inset * 0.6 + 1e-9:
                    cells.append((icol, j, a1v, inset + j * d))
                    j += 1
            cells.sort(key=lambda c: (c[1], c[0]))    # 2×2 square first, then rows toward the apex
            gsc = 0.902                                # uniform — the content box fits 6 at one size
            for k, (nm, dg, rt) in enumerate(planets[:len(cells)]):
                _i, _j, a1v, a2v = cells[k]
                px = right[0] + a1v * a1h[0] + a2v * a2h[0]
                py = right[1] + a1v * a1h[1] + a2v * a2h[1]
                P.append(_egraha(X(px), Y(py), nm, dg, rt, gsc))

    # central info box
    cxp = X(0.5)
    P.append(f'<text x="{cxp:.1f}" y="{Y(0.5)-G*0.03:.1f}" text-anchor="middle" fill="{ink}" '
             f'font-family="{_UI}" font-size="{G*0.05:.1f}" font-weight="700">{_esc(title)}</text>')
    P.append(f'<text x="{cxp:.1f}" y="{Y(0.5)+G*0.015:.1f}" text-anchor="middle" fill="{muted}" '
             f'font-family="{_UI}" font-size="{G*0.028:.1f}">{_esc(_varga_label(chart))}</text>')
    P.append(f'<text x="{cxp:.1f}" y="{Y(0.5)+G*0.055:.1f}" text-anchor="middle" fill="{muted}" '
             f'font-family="{_UI}" font-size="{G*0.026:.1f}">East Indian · Lagna {_RASHI[asc_sign]}</text>')
    P.append(font_face_css())
    P.append("</svg>")
    return "\n".join(P)


def render_vedic_square_svg(chart: dict, *, style: str = "south", theme: str = "light",
                           size: int = 620, title: str = "Rāśi") -> str:
    """Render a Vedic square chart for ``chart`` (a **sidereal** chart) as an SVG string.

    ``style`` is ``"south"`` (South-Indian fixed-rāśi grid), ``"north"`` (North-Indian
    fixed-house diamond), or ``"east"`` (East-Indian / Bengali corner-triangle square).
    ``theme`` is any key of :data:`ephemvis.PALETTES` ('auto' -> light). Raises ``ValueError``
    for an unknown style, a chart without an Ascendant, or a chart that is
    explicitly not sidereal."""
    if (chart.get("angles") or {}).get("asc") is None:
        raise ValueError("a Vedic chart needs a known Ascendant (angles.asc); assemble with a "
                         "birth time, zodiac='sidereal'")
    # A rāśi square drawn from tropical longitudes is wrong by the ayanamsa — ~24° in this
    # era, so nearly a whole sign: the Lagna and every graha land in the neighbouring rāśi,
    # and the result is a well-formed chart that quietly says the wrong thing. Refuse only
    # what we can prove wrong: a chart from another engine may carry no 'zodiac' key at
    # all, and those still render.
    zodiac = chart.get("zodiac")
    if zodiac is not None and zodiac != "sidereal":
        raise ValueError("a Vedic rāśi chart needs the sidereal zodiac, but this chart is "
                         f"{zodiac!r}; rebuild it with assemble(..., zodiac='sidereal')")
    pal = PALETTES.get("light" if theme == "auto" else theme, PALETTES["light"])
    lord_col = _lord_colors(theme)
    if style == "south":
        return _render_south(chart, pal, lord_col, size, title)
    if style == "north":
        return _render_north(chart, pal, lord_col, size, title)
    if style == "east":
        return _render_east(chart, pal, lord_col, size, title)
    raise ValueError("style must be 'south', 'north', or 'east'")


if __name__ == "__main__":
    from openephem import assemble, resolve
    r = resolve(date=(2000, 1, 1), time=(12, 0), lat=51.4779, lon=-0.0015, tz="Europe/London")
    c = assemble(r, zodiac="sidereal")
    with open("vedic_south_demo.svg", "w", encoding="utf-8") as fh:
        fh.write(render_vedic_square_svg(c, theme="light"))
    print("wrote vedic_south_demo.svg")
