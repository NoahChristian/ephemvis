#!/usr/bin/env python3
"""
profection_wheel.py — the annual-profection wheel as a self-contained SVG.  [SHIP]

A whole-sign profection wheel in the traditional Hellenistic style: twelve house wedges
(ASC..12th) counter-clockwise from the left, the natal planets in their whole-sign
houses, the zodiac signs on the rim, and concentric **age rings** — each house lists
the ages that profect there (0,12,24… in the 1st; 1,13,25… in the 2nd; …). The
profected house + sign for the chart's current age are highlighted, and the age
cells are a **heatmap** keyed to age along the theme's ramp.

Input is the same plain chart dict the rest of ephemvis renders (openephem's
``assemble()`` shape); it must carry a ``profections`` block (openephem adds one
when given ``profection_age=`` / ``profection_as_of=``) and ``angles`` with an
Ascendant. Pure computation is done upstream — this only draws.
"""

from __future__ import annotations

import math

from .wheel import PALETTES, PLANET_GLYPHS, SIGN_GLYPHS, SYM_FAMILY, TXT_FAMILY, font_face_css

_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces")
_HOUSE_SHORT = ("Asc", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12")
# traditional whole-sign domicile rulers by sign index (0 = Aries): the Lord of the Year for
# each sign when it profects. Fixed, so a sign always carries the same lord on every turn.
_DOMICILE = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter")
# Chaldean order — the list firdaria/decennials pass to theme_lord_colors, so a planet keeps its
# color across the whole time-lord suite (the profection rim uses the same mapping).
_LORD_ORDER = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
_CLASSICAL = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_MODERN_EXTRA = ("Uranus", "Neptune", "Pluto")
_SYM = SYM_FAMILY        # embedded symbol family (or system fallback)
_UI = TXT_FAMILY         # embedded text family (or system-ui)


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _lerp(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))


def _ramp_at(stops, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    n = len(stops) - 1
    seg = t * n
    i = min(int(seg), n - 1)
    return _lerp(stops[i], stops[i + 1], seg - i)


def _lum(h):
    a = _rgb(h)
    return 0.299 * a[0] + 0.587 * a[1] + 0.114 * a[2]


def _rgb2hsl(hexc):
    r, g, b = (v / 255.0 for v in _rgb(hexc))
    mx, mn = max(r, g, b), min(r, g, b)
    lum = (mx + mn) / 2.0
    if mx == mn:
        return 0.0, 0.0, lum
    d = mx - mn
    s = d / (2.0 - mx - mn) if lum > 0.5 else d / (mx + mn)
    if mx == r:
        h = (g - b) / d + (6.0 if g < b else 0.0)
    elif mx == g:
        h = (b - r) / d + 2.0
    else:
        h = (r - g) / d + 4.0
    return h / 6.0, s, lum


def _hsl2hex(h, s, lum):
    def hue(p, q, t):
        t %= 1.0
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p
    if s == 0:
        r = g = b = lum
    else:
        q = lum * (1 + s) if lum < 0.5 else lum + s - lum * s
        p = 2 * lum - q
        r, g, b = hue(p, q, h + 1 / 3), hue(p, q, h), hue(p, q, h - 1 / 3)
    return "#%02x%02x%02x" % tuple(round(max(0.0, min(1.0, c)) * 255) for c in (r, g, b))


def _distinct_from_ramp(stops, n):
    """Return ``n`` lord colors drawn from a theme ramp: hues picked farthest-point along
    the ramp (so they keep the theme's character), then their lightness staggered evenly so
    the bands stay legible even when the ramp is narrow."""
    if n <= 0:
        return []
    samples = [_ramp_at(stops, s / 72.0) for s in range(73)]

    def dist(p, q):
        a, b = _rgb(p), _rgb(q)
        return sum((a[i] - b[i]) ** 2 for i in range(3))

    chosen = [samples[0], samples[-1]][:max(n, 1)]
    while len(chosen) < n:
        chosen.append(max(samples, key=lambda c: min(dist(c, x) for x in chosen)))
    chosen = chosen[:n]
    if n == 1:
        return chosen
    hsl = [_rgb2hsl(c) for c in chosen]
    order = sorted(range(n), key=lambda i: hsl[i][2])   # rank by current lightness
    lo, hi = 0.30, 0.82                                  # wide lightness spread → distinct bands
    out = [""] * n
    for rank, i in enumerate(order):
        h, s, _ = hsl[i]
        sat = max(s, 0.42) * (1.06 if rank % 2 else 0.92)   # alternate saturation to split near hues
        out[i] = _hsl2hex(h, max(0.0, min(1.0, sat)), lo + (hi - lo) * rank / (n - 1))
    return out


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _adapt(pal):
    """Map an ephemvis palette to the profection wheel's slots + a heatmap ramp."""
    bg = pal["bg"][0]
    acc = pal["prof"]
    ring = pal["ring"]
    heat = list(ring) if len(set(ring)) > 1 else [_lerp(bg, acc, 0.42), acc, _lerp(acc, "#000000", 0.42)]
    return dict(bg=bg, sign=pal["sign"], planet=pal["planet"], house=pal["housenum"],
                line=pal["cusp"], spoke=pal["hdiv"], accent=acc, title=pal["title"],
                sub=pal["deg"], signbg=_lerp(bg, pal["cusp"], 0.16), grid=_lerp(bg, pal["cusp"], 0.5),
                heat=heat)


def _resolve_planets(planets):
    if planets == "classical":
        return list(_CLASSICAL)
    if planets == "all":
        return list(_CLASSICAL) + list(_MODERN_EXTRA)
    if isinstance(planets, (list, tuple)):
        return list(planets)
    raise ValueError("planets must be 'classical', 'all', or a list of body names")


def theme_lord_colors(theme, names):
    """Theme-derived categorical colors for a set of lords, using the same derivation the
    chart wheel uses (hue from the theme ramp, lightness staggered) — so any other view
    (e.g. the horizontal timeline) can color the same lords identically."""
    pal = _adapt(PALETTES.get("light" if theme == "auto" else theme, PALETTES["light"]))
    return dict(zip(names, _distinct_from_ramp(pal["heat"], len(names)), strict=True))


def glyphs_by_year(sub_segments, n_years: int):
    """One sub-lord glyph per age-ring cell, chosen so no sub-period is dropped — the shared
    helper every time-lord chart projection uses (decennials, firdaria, zodiacal releasing).

    Each age cell has room for a single glyph, but sub-periods are unequal and several are
    shorter than a year, so sampling the sub at each birthday silently loses any sub that opens
    *and* closes between two birthdays. Instead every sub-period claims the one year cell where
    it has the most coverage (its "home" cell), biggest claimant first so ties go to the sub
    that fills more of the cell; any cell no sub called home falls back to whichever sub covers
    the most of that year. Each sub-period thus surfaces in exactly one cell (bar a sliver
    clipped at the ``n_years`` horizon). ``sub_segments`` is ``(age_start, age_end, name)``.
    """
    dom: list[dict] = [dict() for _ in range(n_years)]
    ranked = []                                   # (peak_coverage, name, cells-by-coverage)
    for a0, a1, name in sub_segments:
        cells = []
        for y in range(int(a0), min(int(a1) + 1, n_years)):
            cov = min(a1, y + 1.0) - max(a0, float(y))
            if cov > 0:
                dom[y][name] = dom[y].get(name, 0.0) + cov
                cells.append((cov, y))
        if cells:
            cells.sort(reverse=True)              # highest-coverage cell first
            ranked.append((cells[0][0], name, [y for _, y in cells]))
    ranked.sort(key=lambda t: t[0], reverse=True)  # let the biggest claimant win a shared cell
    glyph: list = [None] * n_years
    claimed = [False] * n_years
    for _, name, cell_ys in ranked:
        for y in cell_ys:                         # first still-unclaimed cell it overlaps
            if not claimed[y]:
                glyph[y], claimed[y] = name, True
                break
    for y in range(n_years):                      # unclaimed cells: the sub covering most of it
        if glyph[y] is None and dom[y]:
            glyph[y] = max(dom[y].items(), key=lambda kv: kv[1])[0]
    return glyph


def render_profection_wheel_svg(chart: dict, *, theme: str = "light", max_age: int = 83,
                                size: int = 760, title: str = "Annual Profections",
                                planets="classical", timelord=None,
                                layout: str = "annulus") -> str:
    """Render the annual-profection wheel for ``chart`` as an SVG string.

    ``theme`` is any key of :data:`ephemvis.PALETTES` (``'auto'`` renders as light).
    ``max_age`` sets the final year shown; the outer ring is always completed, so a
    value like 83 gives seven full rings (ages 0-83), 84 gives eight (0-95).
    ``planets`` is ``'classical'`` (default seven), ``'all'``, or a list of body names.
    ``layout`` is ``'annulus'`` (default — the age bands as concentric rings) or
    ``'spiral'`` — the same bands unrolled into one continuous expanding coil, each
    12-year turn abutting the next, the natal hub and sign rim unchanged. ``'spiral'``
    is purely a layout of the band region; coloring, glyphs, sub-periods and the
    profection highlight are identical to ``'annulus'``.
    Raises ``ValueError`` if the chart has no ``profections`` block or no Ascendant.

    ``timelord`` (optional) projects another time-lord technique onto this same wheel: a
    dict ``{"title": str, "subtitle_lines": [str, ...], "ring_bodies": [{"name","role"},
    ...]}``. When given, its title/subtitle replace the profection header and each named
    natal planet is ringed at its position (``role`` ``"major"`` draws a bolder ring than
    ``"sub"``) — the annuli and profection highlight stay as the natal-chart context.
    """
    pr = chart.get("profections")
    if not pr:
        raise ValueError("chart has no 'profections' block (build it with openephem's "
                         "assemble(..., profection_age=/profection_as_of=))")
    asc = (chart.get("angles") or {}).get("asc")
    if asc is None:
        raise ValueError("profection wheel needs a known Ascendant (angles.asc)")

    pal = _adapt(PALETTES.get("light" if theme == "auto" else theme, PALETTES["light"]))
    tl = timelord or {}
    tl_roles = {r["name"]: r.get("role", "major") for r in tl.get("ring_bodies", [])}
    tl_ring = pal["title"]                    # the time-lord ring, distinct from the accent
    # A time-lord may color the annuli by the ruling lord. The lord palette is derived
    # from THIS theme's ramp (so every theme codes the lords in its own colors). We pick
    # the lords' colors by farthest-point selection along the ramp, so they are as
    # mutually distinct as that ramp allows (a narrow ramp simply yields closer colors).
    lord_names = tl.get("lord_names") or []
    major_by_age = tl.get("major_by_age") or []
    glyph_by_age = tl.get("glyph_by_age") or []      # the per-year sub-lord (glyph + stripe)
    # A technique may supply its own color and glyph maps (firdaria's two nodes have fixed
    # identity colors; zodiacal releasing colors by element and glyphs by sign) — otherwise
    # the lords take farthest-point ramp colors and the classical planet glyphs.
    lord_col = tl.get("lord_colors") or dict(
        zip(lord_names, _distinct_from_ramp(pal["heat"], len(lord_names)), strict=True))
    glyph_map = tl.get("glyph_map") or PLANET_GLYPHS

    def cell_fill(a):                        # major-lord color if given, else age heatmap
        if a < len(major_by_age) and major_by_age[a] in lord_col:
            return lord_col[major_by_age[a]]
        return _ramp_at(pal["heat"], a / emax)

    sub_segments = tl.get("sub_segments") or []   # (age_start, age_end, sub_name) fractional
    sub_style = tl.get("sub_style") or "stripe"   # 'stripe' | 'ticks' | 'gradient'

    body_names = _resolve_planets(planets)
    asc_idx = int(asc // 30) % 12
    age = int(pr.get("age", 0))
    cur_h = age % 12
    prof_sidx = (asc_idx + cur_h) % 12
    nring = max_age // 12 + 1
    emax = nring * 12 - 1                 # complete the outer ring
    has_glyphs = bool(tl.get("glyph_by_age"))
    has_legend = bool(tl.get("legend") or lord_names)
    # Plain annual wheel (no time-lord overlay): color each sign's rim arc by its Lord of the Year
    # (the sign's domicile ruler), with a lord-color legend + the age heatmap gradient beneath it.
    show_lords = not timelord
    dom_col = theme_lord_colors(theme, _LORD_ORDER) if show_lords else {}
    s = size / 760.0                     # scale factor: every px below scales with size (the
    #                                      fonts/strokes were hardcoded for 760, so smaller wheels
    #                                      bloated and the 6/9 underline stroke never scaled).

    def _n(v):                           # compact number ("1" not "1.0", "3.4" stays "3.4")
        return f"{round(v, 2):g}"
    legend_items = ([(nm, lord_col[nm]) for nm in lord_names] if lord_names
                    else (tl.get("legend") or []))

    def _legend_rows(items):             # wrap the swatch legend to the wheel width
        rows: list[list] = [[]]
        lx = 22.0 * s
        for name, col in items:
            w = (50 + len(str(name)) * 9.0) * s
            if rows[-1] and lx + w > size - 22.0 * s:
                rows.append([])
                lx = 22.0 * s
            rows[-1].append((name, col, lx))
            lx += w
        return rows

    legend_rows = _legend_rows(legend_items) if (has_legend and not show_lords) else [[]]
    # footer: the lord-rim wheel carries two stacked legends; a time-lord legend takes one row
    # per wrapped line (7 planets fit one row, 9 firdaria lords need two).
    footer = ((96 if show_lords else
               68 + (len(legend_rows) - 1) * 24 if has_legend else 22) * s)
    height = size + footer
    cx = cy = size / 2.0
    base = asc_idx * 30.0 + 15.0          # center the 1st sign at 9 o'clock
    # Locked outer split (share of R_out): inner white ring 30% · annuli 60% · sign rim 10% —
    # shared by the plain annual wheel and the time-lord chart, so the whole wheel is one size.
    R_out = size * 0.478
    a_in = R_out * 0.30           # inner white ring — locked size
    a_out = R_out * 0.895         # annuli 30% → ~90%
    R_sign_in = R_out * 0.905     # sign rim ~90% → 100%
    sign_fs, planet_fs = 22 * s, 18 * s
    # Inside the inner ring, three stacked bands tile it (hub 22% / house numbers 35% / natal
    # planets = the remaining 43%), with one merged house ring and centered numbers — shared by
    # the plain annual wheel and the time-lord chart so both inner hubs are identical.
    hub_pct, house_pct = 0.22, 0.35
    R_hub = a_in * hub_pct
    R_mid = a_in * (hub_pct + house_pct)      # house | planet boundary
    R_house = (R_hub + R_mid) / 2.0           # house numbers centered in the merged ring
    R_planet = (R_mid + a_in) / 2.0           # natal planets centered in the planet band
    R_sign = (R_out + R_sign_in) / 2.0
    bw = (a_out - a_in) / nring

    def pol(rr, lon):
        a = math.radians(180.0 + (lon - base))
        return cx + rr * math.cos(a), cy - rr * math.sin(a)

    def sector(r1, r2, lo, span=30.0, n=10):
        pts = [pol(r2, lo + span * k / n) for k in range(n + 1)]
        pts += [pol(r1, lo + span - span * k / n) for k in range(n + 1)]
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    # ---- layout: the band region is drawn as concentric rings (annulus) or one coil (spiral) ----
    # Everything else (hub, house ring, natal planets, sign rim, profection highlight) is shared,
    # so the two layouts are the same chart with the age bands laid down differently. The coil
    # advances outward by one band-width per 12-year turn (so successive turns abut seamlessly);
    # a year's cell keeps the same house angle on every turn, which for profections — exactly
    # 12-periodic — makes each sign a single aligned radial wedge.
    if layout not in ("annulus", "spiral"):
        raise ValueError("layout must be 'annulus' or 'spiral'")
    spiral = layout == "spiral"
    sbw = (a_out - a_in) / (nring + 1)            # coil band-width (advance per turn)
    active_bw = sbw if spiral else bw             # band thickness of a cell in the active layout

    def _coil_r(p):                               # inner edge of the coil at position p (years)
        return a_in + (sbw / 12.0) * p

    def _coil_ang(p):                             # continuous longitude at position p (30 deg/yr)
        return asc_idx * 30.0 + 30.0 * p

    def cell_points(a):                           # a year-cell polygon in the active layout
        h, k = a % 12, a // 12
        lo = (asc_idx + h) * 30.0
        if not spiral:
            return sector(a_in + k * bw, a_in + (k + 1) * bw, lo)
        m = 8
        pts = [pol(_coil_r(a + i / m), lo + 30.0 * i / m) for i in range(m + 1)]
        pts += [pol(_coil_r(a + (m - i) / m) + sbw, lo + 30.0 * (m - i) / m) for i in range(m + 1)]
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    def stripe_points(a):                         # inner-30% stripe of a cell (stripe sub_style)
        h, k = a % 12, a // 12
        lo = (asc_idx + h) * 30.0
        if not spiral:
            r1 = a_in + k * bw
            return sector(r1, r1 + 0.30 * bw, lo)
        m = 8
        pts = [pol(_coil_r(a + i / m), lo + 30.0 * i / m) for i in range(m + 1)]
        pts += [pol(_coil_r(a + (m - i) / m) + 0.30 * sbw, lo + 30.0 * (m - i) / m) for i in range(m + 1)]
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    def cell_center(a):                           # placement of the age number for a cell
        h, k = a % 12, a // 12
        lo = (asc_idx + h) * 30.0
        rc = (_coil_r(a + 0.5) + sbw / 2.0) if spiral else (a_in + (k + 0.5) * bw)
        return pol(rc, lo + 15.0)

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {height}" '
         f'width="{size}" height="{height}" role="img" aria-label="{_esc(title)}">']
    P.append(f'<rect width="{size}" height="{height}" fill="{pal["bg"]}"/>')

    # sign ring — plain wheel: each arc filled by its Lord of the Year (domicile ruler); time-lord
    # overlay: the original neutral rim with the profected sign highlighted in the accent.
    for i in range(12):
        if show_lords:
            col, op = dom_col[_DOMICILE[i]], "1"
        else:
            col = pal["accent"] if i == prof_sidx else pal["signbg"]
            op = "0.85" if i == prof_sidx else "1"
        P.append(f'<polygon points="{sector(R_sign_in, R_out, i*30.0)}" fill="{col}" fill-opacity="{op}"/>')
    if show_lords:                                  # mark the profected sign with an accent arc outline
        P.append(f'<polygon points="{sector(R_sign_in, R_out, prof_sidx*30.0)}" fill="none" '
                 f'stroke="{pal["accent"]}" stroke-width="{_n(2.6*s)}"/>')

    # age heatmap band cells (annulus) / coil cells (spiral)
    for h in range(12):
        for k in range(nring):
            a = k * 12 + h
            P.append(f'<polygon points="{cell_points(a)}" fill="{cell_fill(a)}"/>')
            if sub_style == "stripe" and a < len(glyph_by_age) and glyph_by_age[a] in lord_col:
                P.append(f'<polygon points="{stripe_points(a)}" '
                         f'fill="{lord_col[glyph_by_age[a]]}"/>')

    # sub-period detail: draw each sub-segment (fractional ages) into its year-wedge(s).
    # A wedge spans one year, so a segment's angular slice within it = its share of that year.
    if not spiral:
        def _seg_arcs(a0, a1, ifrac, ofrac):
            a = int(a0)
            while a < a1 and a < nring * 12:
                c0, c1 = max(a0, a), min(a1, a + 1)
                k, h = a // 12, a % 12
                lo0 = (asc_idx + h) * 30.0 + (c0 - a) * 30.0
                r1, r2 = a_in + (k + ifrac) * bw, a_in + (k + ofrac) * bw
                yield r1, r2, lo0, (c1 - c0) * 30.0
                a += 1

        if sub_style == "gradient":
            for a0, a1, name in sub_segments:      # inner ~half of each band = sub-lord slices
                col = lord_col.get(name)
                if not col:
                    continue
                for r1, r2, l0, sp in _seg_arcs(a0, a1, 0.0, 0.5):
                    P.append(f'<polygon points="{sector(r1, r2, l0, span=sp)}" fill="{col}"/>')

        if sub_style in ("ticks", "gradient"):     # radial ticks at every sub-period boundary
            for a0, _a1, _name in sub_segments:
                if a0 <= 0 or a0 >= nring * 12:
                    continue
                k, h = int(a0) // 12, int(a0) % 12
                lon = (asc_idx + h) * 30.0 + (a0 - int(a0)) * 30.0
                x1, y1 = pol(a_in + k * bw, lon)
                x2, y2 = pol(a_in + (k + 1) * bw, lon)
                P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                         f'stroke="{pal["bg"]}" stroke-width="{_n(1.6*s)}"/>')
        for k in range(nring + 1):
            P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{a_in + k*bw:.1f}" fill="none" '
                     f'stroke="{pal["grid"]}" stroke-width="{_n(1*s)}"/>')
        for i in range(12):
            x1, y1 = pol(a_in, i * 30.0)
            x2, y2 = pol(a_out, i * 30.0)
            P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{pal["grid"]}" stroke-width="{_n(1*s)}"/>')
    else:
        # spiral: the sub-slices and boundary ticks follow the coil, then one continuous edge
        # traces every turn seam (outer edge of turn k == inner edge of turn k+1) plus the final
        # outer edge, and the 12 house spokes cross the whole band exactly as in the annulus.
        if sub_style == "gradient":
            for a0, a1, name in sub_segments:      # inner half of the coil = sub-lord slices
                col = lord_col.get(name)
                if not col:
                    continue
                m = max(2, int((a1 - a0) * 8) + 1)
                pts = [pol(_coil_r(a0 + (a1 - a0) * i / m), _coil_ang(a0 + (a1 - a0) * i / m))
                       for i in range(m + 1)]
                pts += [pol(_coil_r(a0 + (a1 - a0) * (m - i) / m) + 0.5 * sbw,
                            _coil_ang(a0 + (a1 - a0) * (m - i) / m)) for i in range(m + 1)]
                P.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{col}"/>')
        if sub_style in ("ticks", "gradient"):     # radial ticks at every sub-period boundary
            for a0, _a1, _name in sub_segments:
                if a0 <= 0 or a0 >= nring * 12:
                    continue
                lon = _coil_ang(a0)
                x1, y1 = pol(_coil_r(a0), lon)
                x2, y2 = pol(_coil_r(a0) + sbw, lon)
                P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                         f'stroke="{pal["bg"]}" stroke-width="{_n(1.6*s)}"/>')
        pmax = nring * 12 + 12                      # +12 carries the guide out to the final outer edge
        steps = pmax * 6
        edge = []
        for i in range(steps + 1):
            p = pmax * i / steps
            x, y = pol(_coil_r(p), _coil_ang(p))
            edge.append(f"{x:.1f},{y:.1f}")
        P.append(f'<polyline points="{" ".join(edge)}" fill="none" stroke="{pal["grid"]}" '
                 f'stroke-width="{_n(1*s)}" stroke-linejoin="round"/>')
        for i in range(12):
            x1, y1 = pol(a_in, i * 30.0)
            x2, y2 = pol(a_out, i * 30.0)
            P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{pal["grid"]}" stroke-width="{_n(1*s)}"/>')

    # age numbers — baseline toward center; 2nd..6th flipped to read upright. When a
    # time-lord's per-age lord series is supplied, each cell also carries that year's
    # lord glyph (the age annuli become the technique's timeline — the "Gantt rolled on").
    # age number — the same dynamic size in both wheels (bw*0.56, capped 15.5)
    fs = gfs = max(11.5 * s, min(15.5 * s, active_bw * 0.56))     # active_bw scales with size;
    glyph_fs = max(13.0 * s, min(18.0 * s, active_bw * 0.65))     # scale the clamp bounds too

    def _digit_underline(a, ax, ay, rot, size_fs, dcx, txt, cf):
        # A solitary 6 or 9 is ambiguous under the cell rotation: a rotated 6 reads as a 9, so
        # reading the ages around a ring the run appears to jump (…, 5, 9 instead of …, 5, 6).
        # Underline the digit's foot to fix which end is down. It must be an explicit <line>:
        # CSS `text-underline-offset` is a no-op on SVG <text> in Chromium (verified in both
        # Chrome and Edge — the underline never moves), so a drawn rule is the only placeable
        # one. `dcx` is the digit's center (= ax for a bare number, shifted left when a glyph
        # follows it); a band-color knockout sits behind so a grid line / tick can't cross it.
        # Shared by the plain age wheel and the time-lord (glyph) overlay so they never diverge.
        if a not in (6, 9):
            return
        y_ul = ay + size_fs * 0.60
        hw = size_fs * 0.32
        rt = f'transform="rotate({rot:.1f} {ax:.1f} {ay:.1f})"'
        ln = f'x1="{dcx-hw:.1f}" y1="{y_ul:.1f}" x2="{dcx+hw:.1f}" y2="{y_ul:.1f}"'
        P.append(f'<line {ln} stroke="{cf}" stroke-width="{_n(3.4*s)}" {rt}/>')   # knockout
        P.append(f'<line {ln} stroke="{txt}" stroke-width="{_n(1.5*s)}" {rt}/>')  # the rule

    for h in range(12):
        lo = (asc_idx + h) * 30.0
        px, py = pol(a_in, lo + 15.0)
        rot = math.degrees(math.atan2(py - cy, px - cx)) + 90.0
        if 1 <= h <= 5:
            rot += 180.0
        for k in range(nring):
            a = k * 12 + h
            cf = cell_fill(a)
            txt = "#141414" if _lum(cf) > 140 else "#ffffff"
            ax, ay = cell_center(a)
            if a == age:
                weight = "700" if has_glyphs else "800"
            else:
                weight = "500" if has_glyphs else "600"
            name = glyph_by_age[a] if a < len(glyph_by_age) else None
            if has_glyphs:
                # one line per cell: "year glyph" (number + its lord glyph, side by side)
                gl = (f'<tspan font-family="{_SYM}" font-size="{glyph_fs:.0f}" dx="2"> '
                      f'{_esc(glyph_map.get(name, name[:2]))}︎</tspan>') if name else ""
                # knockout halo in the band's own color: the number+glyph carve a moat of
                # band color around themselves, breaking any sub-period tick that would
                # otherwise cross (and merge with) the glyph. paint-order draws it behind.
                P.append(f'<text x="{ax:.1f}" y="{ay:.1f}" text-anchor="middle" '
                         f'dominant-baseline="central" transform="rotate({rot:.1f} {ax:.1f} {ay:.1f})" '
                         f'fill="{txt}" font-size="{gfs:.0f}" paint-order="stroke" stroke="{cf}" '
                         f'stroke-width="{_n(3.4*s)}" stroke-linejoin="round">'
                         f'<tspan font-family="{_UI}" font-weight="{weight}">{a}</tspan>{gl}</text>')
                # digit sits at the left of the centered "N glyph" string, so its center is half
                # the glyph-part's advance (≈0.445·glyph_fs) left of ax — pixel-verified.
                _digit_underline(a, ax, ay, rot, gfs, ax - 0.445 * glyph_fs, txt, cf)
            else:
                P.append(f'<text x="{ax:.1f}" y="{ay:.1f}" text-anchor="middle" dominant-baseline="central" '
                         f'transform="rotate({rot:.1f} {ax:.1f} {ay:.1f})" fill="{txt}" '
                         f'font-family="{_UI}" font-size="{fs:.0f}" font-weight="{weight}">{a}</text>')
                _digit_underline(a, ax, ay, rot, fs, ax, txt, cf)   # bare number → centered on ax

    # current age cell outline
    if age // 12 < nring:
        P.append(f'<polygon points="{cell_points(age)}" '
                 f'fill="none" stroke="{pal["accent"]}" stroke-width="{_n(3.4*s)}"/>')

    # structural rings + spokes. The empty inner ring is merged into the house ring, so there
    # is a single boundary circle (R_mid) inside the natal chart — in both modes.
    inner_circles = (R_out, R_sign_in, R_mid, R_hub)
    for rr in inner_circles:
        P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" fill="none" '
                 f'stroke="{pal["line"]}" stroke-width="{_n(1.1*s)}"/>')
    for i in range(12):
        x1, y1 = pol(R_hub, i * 30.0)
        x2, y2 = pol(a_in, i * 30.0)
        P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{pal["spoke"]}" stroke-width="{_n(0.9*s)}"/>')
    P.append(f'<polygon points="{sector(R_hub, R_sign_in, prof_sidx*30.0)}" fill="none" '
             f'stroke="{pal["accent"]}" stroke-width="{_n(2*s)}"/>')

    # sign glyphs
    for i in range(12):
        gx, gy = pol(R_sign, i * 30.0 + 15.0)
        if show_lords:                              # ink chosen for contrast against the lord arc
            col = "#141414" if _lum(dom_col[_DOMICILE[i]]) > 140 else "#ffffff"
        else:
            col = "#ffffff" if (i == prof_sidx and _lum(pal["accent"]) < 150) else pal["sign"]
        P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" text-anchor="middle" dominant-baseline="central" '
                 f'fill="{col}" font-family="{_SYM}" font-size="{sign_fs}">{SIGN_GLYPHS[i]}︎</text>')
    # house labels — short ("Asc 2 3…12"), centered and bold in the merged ring, in both modes
    # (ordinals overran the merged ring); light so they don't fight the annuli.
    h_labels = _HOUSE_SHORT
    h_col = pal["sub"]
    h_fs, h_wt = 13 * s, "700"
    for h in range(12):
        hx, hy = pol(R_house, (asc_idx + h) * 30.0 + 15.0)
        P.append(f'<text x="{hx:.1f}" y="{hy:.1f}" text-anchor="middle" dominant-baseline="central" '
                 f'fill="{h_col}" font-family="{_UI}" font-size="{h_fs}" font-weight="{h_wt}">{h_labels[h]}</text>')
    # planets in whole-sign houses
    byhouse: dict[int, list[str]] = {}
    for name in body_names:
        b = (chart.get("bodies") or {}).get(name)
        if b and "lon" in b:
            byhouse.setdefault((int(b["lon"] // 30) - asc_idx) % 12, []).append(name)
    for h, names in byhouse.items():
        mid = (asc_idx + h) * 30.0 + 15.0
        n = len(names)
        for j, name in enumerate(names):
            gx, gy = pol(R_planet, mid + (j - (n - 1) / 2.0) * 10.0)
            role = tl_roles.get(name)                     # ring the active time-lord(s)
            if role:
                rr = (14.0 if role == "major" else 11.0) * s
                sw = (3.0 if role == "major" else 2.0) * s
                P.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{rr:.1f}" fill="{pal["bg"]}" '
                         f'stroke="{tl_ring}" stroke-width="{_n(sw)}"/>')
            P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" text-anchor="middle" dominant-baseline="central" '
                     f'fill="{pal["planet"]}" font-family="{_SYM}" font-size="{planet_fs}">'
                     f'{_esc(PLANET_GLYPHS.get(name, name[:2]))}︎</text>')
    P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R_hub:.1f}" fill="{pal["bg"]}" '
             f'stroke="{pal["line"]}" stroke-width="{_n(1.1*s)}"/>')

    # title (top-left) + subtitle — a time-lord overlay supplies its own header
    head = _esc(tl.get("title", title))
    sub_lines = tl.get("subtitle_lines") or (f"Lord: {_esc(pr.get('ruler', ''))}",
                                             f"{_SIGNS[asc_idx]} rising")
    P.append(f'<text x="{_n(22*s)}" y="{_n(32*s)}" fill="{pal["title"]}" font-family="{_UI}" '
             f'font-size="{_n(18*s)}" font-weight="700">{head}</text>')
    for i, line in enumerate(sub_lines):
        P.append(f'<text x="{_n(22*s)}" y="{_n((58 + i*23)*s)}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(19*s)}" font-weight="600">{_esc(line)}</text>')

    if show_lords:
        # two stacked legends in the footer: Lord of the Year (the rim colors), then the age
        # heatmap gradient (the coil/annuli colors) below it.
        ex = 22.0 * s
        P.append(f'<text x="{ex:.1f}" y="{size + 15*s:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(11.5*s)}" letter-spacing="1" font-weight="700">LORD OF THE YEAR</text>')
        ly = size + 33 * s
        lx = ex
        for nm in _LORD_ORDER:
            gl = PLANET_GLYPHS.get(nm, "")
            gtag = f' (<tspan font-family="{_SYM}" font-size="{_n(16*s)}">{_esc(gl)}</tspan>)' if gl else ""
            P.append(f'<rect x="{lx:.1f}" y="{ly-11*s:.1f}" width="{_n(13*s)}" height="{_n(13*s)}" rx="2" fill="{dom_col[nm]}"/>')
            P.append(f'<text x="{lx+18*s:.1f}" y="{ly:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                     f'font-size="{_n(13*s)}">{_esc(nm)}{gtag}</text>')
            lx += (50 + len(nm) * 9.0) * s
        ay0, lw = size + 62 * s, 160 * s           # age heatmap gradient bar
        cw = lw / 24
        for j in range(24):
            P.append(f'<rect x="{ex + j*cw:.1f}" y="{ay0:.1f}" width="{cw + 0.6:.1f}" height="{_n(9*s)}" '
                     f'fill="{_ramp_at(pal["heat"], j/23)}"/>')
        P.append(f'<text x="{ex:.1f}" y="{ay0 - 5*s:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(11.5*s)}" letter-spacing="1" font-weight="700">AGE</text>')
        P.append(f'<text x="{ex:.1f}" y="{ay0 + 20*s:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(12*s)}">0</text>')
        P.append(f'<text x="{ex + lw:.0f}" y="{ay0 + 20*s:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(12*s)}" text-anchor="end">{emax}</text>')
    elif legend_items:
        # footer band below the wheel: an optional caption (e.g. the current lords) then the
        # lord-color legend, wrapped to as many rows as the wheel width needs (7 planets fit
        # one row; firdaria's 9 lords with the node names take two)
        fy = size + 16 * s
        caption = tl.get("footer_caption")
        if caption:
            P.append(f'<text x="{_n(22*s)}" y="{fy:.0f}" fill="{pal["title"]}" font-family="{_UI}" '
                     f'font-size="{_n(13.5*s)}" font-weight="700">{_esc(caption)}</text>')
            fy += 26 * s
        for r, row in enumerate(legend_rows):
            ry = fy + r * 24 * s
            for name, col, lx in row:
                gl = glyph_map.get(name, "")
                gtag = f' (<tspan font-family="{_SYM}" font-size="{_n(18*s)}">{_esc(gl)}</tspan>)' if gl else ""
                P.append(f'<rect x="{lx:.1f}" y="{ry-13*s:.0f}" width="{_n(15*s)}" height="{_n(15*s)}" rx="2" fill="{col}"/>')
                P.append(f'<text x="{lx+20*s:.1f}" y="{ry:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                         f'font-size="{_n(16*s)}">{_esc(name)}{gtag}</text>')
    else:
        # heatmap legend (discrete swatches; no gradient id -> safe when inlined). Sits a line
        # lower than the wheel and reads at 12px.
        lx, ly, lw = 22 * s, size - 22 * s, 160 * s
        cw = lw / 24
        for j in range(24):
            P.append(f'<rect x="{lx + j*cw:.1f}" y="{ly:.1f}" width="{cw + 0.6:.1f}" height="{_n(10*s)}" '
                     f'fill="{_ramp_at(pal["heat"], j/23)}"/>')
        P.append(f'<text x="{lx:.1f}" y="{ly - 6*s:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(12*s)}" letter-spacing="1">AGE</text>')
        P.append(f'<text x="{lx:.1f}" y="{ly + 24*s:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(12*s)}">0</text>')
        P.append(f'<text x="{lx + lw:.0f}" y="{ly + 24*s:.0f}" fill="{pal["sub"]}" font-family="{_UI}" '
                 f'font-size="{_n(12*s)}" text-anchor="end">{emax}</text>')
    P.append(font_face_css())
    P.append("</svg>")
    return "\n".join(P)


if __name__ == "__main__":
    from openephem import assemble, resolve
    r = resolve(date=(2000, 1, 1), time=(12, 0), lat=51.4779, lon=-0.0015, tz="Europe/London")
    c = assemble(r, profection_as_of=(2026, 6, 1))
    with open("profection_demo.svg", "w", encoding="utf-8") as fh:
        fh.write(render_profection_wheel_svg(c, theme="infrared"))
    print("wrote profection_demo.svg  |  age", c["profections"]["age"],
          "lord", c["profections"]["ruler"])
