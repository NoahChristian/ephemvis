#!/usr/bin/env python3
"""
aspectgrid.py — render the aspectarian (triangular aspect grid) as a self-contained SVG.

Takes an openephem chart dict (needs ``bodies`` and ``aspects``) and returns an SVG
string: bodies run down the diagonal as glyphs; each lower-left cell shows the aspect
between its row and column body, colored by nature (hard / soft / neutral). Themed
via the same PALETTES as the wheel. Uses inline presentation attributes (no <style>),
so it is safe to embed in the same page as other inline SVGs.
"""

from __future__ import annotations

from typing import cast

from .wheel import (
    _L,
    PALETTES,
    PLANET_GLYPHS,
    SYM_FAMILY,
    TXT_FAMILY,
    _esc,
    _lerp_hex,
    body_label,
    font_face_css,
)

ASP_SYM = {"conjunction": "☌", "opposition": "☍", "square": "□", "trine": "△",
           "sextile": "⚹", "quincunx": "⚻", "semisextile": "⚺",
           "semisquare": "∠", "sesquiquadrate": "⚼", "quintile": "Q"}
ASP_CAT = {"conjunction": "aNeutral", "opposition": "aHard", "square": "aHard",
           "semisquare": "aHard", "sesquiquadrate": "aHard", "trine": "aSoft",
           "sextile": "aSoft", "quincunx": "aSoft", "semisextile": "aSoft", "quintile": "aSoft"}
ASP_LABEL = {"conjunction": "Conjunction", "opposition": "Opposition", "square": "Square",
             "trine": "Trine", "sextile": "Sextile", "quincunx": "Quincunx",
             "semisextile": "Semi-sextile", "semisquare": "Semi-square",
             "sesquiquadrate": "Sesquiquadrate", "quintile": "Quintile"}
# relational verb for the hover significance ("Sun conjunct Mercury ...")
ASP_REL = {"conjunction": "conjunct", "opposition": "opposite", "square": "square",
           "trine": "trine", "sextile": "sextile", "quincunx": "quincunx",
           "semisextile": "semi-sextile", "semisquare": "semi-square",
           "sesquiquadrate": "sesquiquadrate", "quintile": "quintile"}
_NICE = {"TrueNode": "North Node", "MeanNode": "North Node",
         "MeanLilith": "Lilith", "OscuLilith": "Lilith", "SouthNode": "South Node"}
DEFAULT_ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus",
                 "Neptune", "Pluto", "TrueNode", "MeanNode", "MeanLilith", "OscuLilith",
                 "Chiron", "Ceres", "Pallas", "Juno", "Vesta",
                 "Astraea", "Hygeia", "Eros", "Eris", "Sedna", "AsteroidLilith"]
SYM = SYM_FAMILY        # embedded symbol family (or system fallback)
TXT = TXT_FAMILY        # embedded text family (or system-ui)
# Themes whose two grid-gradient colors read better swapped (perceptual). The
# direction/anchoring is unchanged — only which color sits at the bottom-left nexus.
_GRID_GRAD_REVERSE = {"infrared"}


def render_aspect_grid_svg(chart: dict, theme: str = "light", order=None,
                           cell: float = 30.0, legend: bool = True) -> str:
    """Return an SVG string for the triangular aspect grid.

    Only bodies that appear in `order` AND in the chart's `bodies` are shown, in that
    order. Aspects are matched from `chart['aspects']` (undirected).
    """
    bodies = chart.get("bodies") or {}
    aspects = chart.get("aspects") or []
    pal = _L if theme == "auto" else PALETTES.get(theme, _L)
    gorder = [b for b in (order or DEFAULT_ORDER) if b in bodies]
    n = len(gorder)
    amap = {frozenset((a.get("a"), a.get("b"))): a for a in aspects}
    C, pad = float(cell), 8.0
    bg0 = cast("tuple[str, str]", pal["bg"])[0]
    diagbg = _lerp_hex(bg0, pal["planet"], 0.10)       # subtle diagonal-cell tint over bg
    accent = pal["anglelab"]                           # diagonal glyph color
    muted = pal["deg"]
    # grid gradient: two theme colors, nexus at the bottom-left corner
    gwarm, gcool = pal["aHard"], pal["aSoft"]
    if theme in _GRID_GRAD_REVERSE:                    # perceptual per-theme swap
        gwarm, gcool = gcool, gwarm
    gid = "aspgrid_%s_%d_%d" % (theme, int(round(C)), n)

    present = [k for k in ASP_SYM if any(a.get("aspect") == k for a in aspects)]
    leg_h = 26.0 if (legend and present) else 0.0
    gridW = n * C
    legW = sum(20.0 + len(ASP_LABEL[k]) * 7.2 + 22.0 for k in present) if leg_h else 0.0
    W = max(gridW, legW) + pad * 2
    H = gridW + pad * 2 + leg_h

    def X(j): return pad + j * C
    def Y(i): return pad + i * C

    P = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" '
         'width="%.0f" height="%.0f" style="cursor:default" role="img" '
         'aria-label="aspect grid">' % (W, H, W, H)]
    P.append(font_face_css())

    # gradient DIRECTION (pass one): warm nexus pinned at the bottom-left corner,
    # radiating perpendicular to the symbol diagonal toward the top-right. The axis
    # runs along (1,-1), so iso-color bands are straight lines PARALLEL to the symbol
    # diagonal; the cool 100% stop-band lands exactly on the line through the symbols'
    # top-right corners (x - y == one cell). End point (X((n+1)/2), Y((n-1)/2)) has
    # x - y == C and BL->end is along (1,-1).
    P.append('<defs><linearGradient id="%s" gradientUnits="userSpaceOnUse" '
             'x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f">'
             '<stop offset="0%%" stop-color="%s"/><stop offset="100%%" stop-color="%s"/>'
             '</linearGradient></defs>'
             % (gid, X(0), Y(n), X((n + 1) / 2.0), Y((n - 1) / 2.0), gwarm, gcool))

    # --- cell fills, glyphs & aspect symbols ---
    for i, bi in enumerate(gorder):
        for j in range(i + 1):
            x, y = X(j), Y(i)
            if j == i:
                # hover the body's diagonal cell -> its name, sign & degree
                P.append('<g><title>%s</title>' % _esc(body_label(bi, bodies.get(bi, {}))))
                P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                         % (x, y, C, C, diagbg))
                P.append('<text x="%.1f" y="%.1f" fill="%s" font-family="%s" font-size="%.1f" '
                         'text-anchor="middle" dominant-baseline="central">%s︎</text></g>'
                         % (x + C / 2, y + C / 2, accent, SYM, C * 0.52,
                            _esc(PLANET_GLYPHS.get(bi) or
                                 ("✦" if bodies.get(bi, {}).get("kind") == "star" else bi[:2]))))
            else:
                a = amap.get(frozenset((bi, gorder[j])))
                if not a:
                    continue
                col = pal[ASP_CAT.get(a.get("aspect"), "aSoft")]
                asp = a.get("aspect")
                tip = "%s %s %s · %.1f° orb" % (
                    _NICE.get(bi, bi), ASP_REL.get(asp, asp),
                    _NICE.get(gorder[j], gorder[j]), abs(float(a.get("orb", 0.0))))
                P.append('<g><title>%s</title>'
                         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.13"/>'
                         '<text x="%.1f" y="%.1f" fill="%s" font-family="%s" font-size="%.1f" '
                         'font-weight="600" text-anchor="middle" dominant-baseline="central">%s︎</text></g>'
                         % (_esc(tip), x, y, C, C, col, x + C / 2, y + C / 2, col, SYM, C * 0.46,
                            _esc(ASP_SYM.get(a.get("aspect"), "·"))))

    # --- interior gridlines: same gradient as the frame (pass two) ---
    for i in range(1, n):                        # row separators (span columns 0..i)
        P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="url(#%s)" stroke-width="1.5" '
                 'shape-rendering="crispEdges"/>' % (X(0), Y(i), X(i), Y(i), gid))
    for j in range(1, n):                        # column separators (span rows j..n)
        P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="url(#%s)" stroke-width="1.5" '
                 'shape-rendering="crispEdges"/>' % (X(j), Y(j), X(j), Y(n), gid))

    # --- outer edge of the triangle (staircase frame, themed gradient stroke) ---
    if n:
        pts = [(X(0), Y(0)), (X(0), Y(n)), (X(n), Y(n))]
        for i in range(n - 1, -1, -1):
            pts.append((X(i + 1), Y(i)))
            pts.append((X(i), Y(i)))
        P.append('<polygon points="%s" fill="none" stroke="url(#%s)" stroke-width="4" '
                 'stroke-linejoin="miter" shape-rendering="crispEdges"/>'
                 % (" ".join("%.1f,%.1f" % p for p in pts), gid))

    # --- legend ---
    if leg_h:
        ly, lx = pad + gridW + 17.0, pad
        for k in present:
            P.append('<text x="%.1f" y="%.1f" fill="%s" font-family="%s" font-size="14" '
                     'dominant-baseline="central">%s︎</text>' % (lx, ly, pal[ASP_CAT[k]], SYM, _esc(ASP_SYM[k])))
            lx += 20.0
            P.append('<text x="%.1f" y="%.1f" fill="%s" font-family="%s" '
                     'font-size="12.5" dominant-baseline="central">%s</text>' % (lx, ly, muted, TXT, ASP_LABEL[k]))
            lx += len(ASP_LABEL[k]) * 7.2 + 22.0

    P.append('</svg>')
    return "\n".join(P)


def render_synastry_grid_svg(inner_chart: dict, outer_chart: dict,
                             cross_aspects: list | None = None, theme: str = "light",
                             order=None, cell: float = 30.0, legend: bool = True,
                             labels=("Inner", "Outer")) -> str:
    """Return an SVG string for a synastry (cross-chart) aspect grid.

    Unlike the single-chart triangular aspectarian, this is a full **rectangular**
    matrix: the inner chart's bodies run down the left header column, the outer chart's
    across the top header row, and each interior cell shows the cross-aspect between its
    row (inner) and column (outer) body. `cross_aspects` is the list openephem's
    ``cross_aspects(inner, outer)`` returns (dicts with ``a`` = inner body, ``b`` =
    outer body). The frame/gridlines carry a gradient folded inward from **two** corners
    (bottom-left and top-right) — two triangular aspectarians folded into one rectangle.
    """
    inner_bodies = inner_chart.get("bodies") or {}
    outer_bodies = outer_chart.get("bodies") or {}
    xs = cross_aspects or []
    pal = _L if theme == "auto" else PALETTES.get(theme, _L)
    rows = [b for b in (order or DEFAULT_ORDER) if b in inner_bodies]   # inner (down)
    cols = [b for b in (order or DEFAULT_ORDER) if b in outer_bodies]   # outer (across)
    n, m = len(rows), len(cols)
    amap = {(a.get("a"), a.get("b")): a for a in xs}                    # (inner, outer) -> aspect

    C, pad = float(cell), 8.0
    lm = tm = 20.0                                     # left / top axis-label margins
    bg0 = cast("tuple[str, str]", pal["bg"])[0]
    diagbg = _lerp_hex(bg0, pal["planet"], 0.10)       # header-cell tint over bg
    accent = pal["anglelab"]                           # header glyph color
    muted = pal["deg"]
    gwarm, gcool = pal["aHard"], pal["aSoft"]
    if theme in _GRID_GRAD_REVERSE:
        gwarm, gcool = gcool, gwarm
    gid = "synas_%s_%d_%dx%d" % (theme, int(round(C)), n, m)

    x_head = pad + lm                                  # left header column x-start
    x0 = x_head + C                                    # interior x-start (after header col)
    y_head = pad + tm                                  # top header row y-start
    y0 = y_head + C                                    # interior y-start (after header row)
    gridW = C + m * C                                  # header col + m outer cols
    gridH = C + n * C                                  # header row + n inner rows

    present = [k for k in ASP_SYM if any(a.get("aspect") == k for a in xs)]
    leg_h = 26.0 if (legend and present) else 0.0
    W = x_head + gridW + pad
    H = y_head + gridH + pad + leg_h

    P = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" '
         'width="%.0f" height="%.0f" style="cursor:default" role="img" '
         'aria-label="synastry grid">' % (W, H, W, H)]
    P.append(font_face_css())

    # gradient folded in from TWO corners: warm at bottom-left AND top-right, cool at the
    # centre — the axis runs along the BL->TR diagonal of the matrix block.
    P.append('<defs><linearGradient id="%s" gradientUnits="userSpaceOnUse" '
             'x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f">'
             '<stop offset="0%%" stop-color="%s"/><stop offset="50%%" stop-color="%s"/>'
             '<stop offset="100%%" stop-color="%s"/></linearGradient></defs>'
             % (gid, x_head, y_head + gridH, x_head + gridW, y_head, gwarm, gcool, gwarm))

    # axis labels
    P.append('<text x="%.1f" y="%.1f" fill="%s" font-family="%s" '
             'font-size="12.5" font-weight="700" text-anchor="middle">%s</text>'
             % (x_head + gridW / 2.0, pad + tm * 0.6, muted, TXT, _esc(labels[1])))
    P.append('<text x="%.1f" y="%.1f" fill="%s" font-family="%s" '
             'font-size="12.5" font-weight="700" text-anchor="middle" '
             'transform="rotate(-90 %.1f %.1f)">%s</text>'
             % (pad + lm * 0.6, y_head + gridH / 2.0, muted, TXT,
                pad + lm * 0.6, y_head + gridH / 2.0, _esc(labels[0])))

    def _glyph(name, bodies):
        return _esc(PLANET_GLYPHS.get(name) or
                    ("✦" if bodies.get(name, {}).get("kind") == "star" else name[:2]))

    # top header row: outer bodies across
    for j, nm in enumerate(cols):
        x, y = x0 + j * C, y_head
        P.append('<g><title>%s</title>'
                 '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 '<text x="%.1f" y="%.1f" fill="%s" font-family="%s" font-size="%.1f" '
                 'text-anchor="middle" dominant-baseline="central">%s︎</text></g>'
                 % (_esc(body_label(nm, outer_bodies.get(nm, {}))), x, y, C, C, diagbg,
                    x + C / 2, y + C / 2, accent, SYM, C * 0.52, _glyph(nm, outer_bodies)))
    # left header column: inner bodies down
    for i, nm in enumerate(rows):
        x, y = x_head, y0 + i * C
        P.append('<g><title>%s</title>'
                 '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 '<text x="%.1f" y="%.1f" fill="%s" font-family="%s" font-size="%.1f" '
                 'text-anchor="middle" dominant-baseline="central">%s︎</text></g>'
                 % (_esc(body_label(nm, inner_bodies.get(nm, {}))), x, y, C, C, diagbg,
                    x + C / 2, y + C / 2, accent, SYM, C * 0.52, _glyph(nm, inner_bodies)))

    # interior cells: cross-aspect symbol + category color
    for i, ri in enumerate(rows):
        for j, cj in enumerate(cols):
            a = amap.get((ri, cj))
            if not a:
                continue
            x, y = x0 + j * C, y0 + i * C
            col = pal[ASP_CAT.get(a.get("aspect"), "aSoft")]
            asp = a.get("aspect")
            tip = "%s %s %s · %.1f° orb" % (
                _NICE.get(ri, ri), ASP_REL.get(asp, asp),
                _NICE.get(cj, cj), abs(float(a.get("orb", 0.0))))
            P.append('<g><title>%s</title>'
                     '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.13"/>'
                     '<text x="%.1f" y="%.1f" fill="%s" font-family="%s" font-size="%.1f" '
                     'font-weight="600" text-anchor="middle" dominant-baseline="central">%s︎</text></g>'
                     % (_esc(tip), x, y, C, C, col, x + C / 2, y + C / 2, col, SYM, C * 0.46,
                        _esc(ASP_SYM.get(asp, "·"))))

    # gridlines + frame (same two-corner gradient)
    for i in range(n + 1):
        yy = y0 + i * C
        P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="url(#%s)" stroke-width="1.5" '
                 'shape-rendering="crispEdges"/>' % (x_head, yy, x_head + gridW, yy, gid))
    for j in range(m + 1):
        xx = x0 + j * C
        P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="url(#%s)" stroke-width="1.5" '
                 'shape-rendering="crispEdges"/>' % (xx, y_head, xx, y_head + gridH, gid))
    # separators bordering the header row/column
    P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="url(#%s)" stroke-width="1.5" '
             'shape-rendering="crispEdges"/>' % (x0, y_head, x0, y_head + gridH, gid))
    P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="url(#%s)" stroke-width="1.5" '
             'shape-rendering="crispEdges"/>' % (x_head, y0, x_head + gridW, y0, gid))
    P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" '
             'stroke="url(#%s)" stroke-width="4" shape-rendering="crispEdges"/>'
             % (x_head, y_head, gridW, gridH, gid))

    # legend
    if leg_h:
        ly, lx = y_head + gridH + 17.0, x_head
        for k in present:
            P.append('<text x="%.1f" y="%.1f" fill="%s" font-family="%s" font-size="14" '
                     'dominant-baseline="central">%s︎</text>' % (lx, ly, pal[ASP_CAT[k]], SYM, _esc(ASP_SYM[k])))
            lx += 20.0
            P.append('<text x="%.1f" y="%.1f" fill="%s" font-family="%s" '
                     'font-size="12.5" dominant-baseline="central">%s</text>' % (lx, ly, muted, TXT, ASP_LABEL[k]))
            lx += len(ASP_LABEL[k]) * 7.2 + 22.0

    P.append('</svg>')
    return "\n".join(P)
