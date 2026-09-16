#!/usr/bin/env python3
"""
biwheel.py — the double wheel (bi-wheel): two charts on one wheel.  [SHIP]

Overlays two charts on a single zodiac ring and house framework so they can be
compared — natal + transit, two transits, synastry (compatibility), natal + solar/
lunar return, natal + progressed. The **inner** chart (first argument, the radix)
owns the orientation, the zodiac ring, the house cusps and the angles; the **outer**
chart's planets are placed by longitude against that same ring, on their own outer
planet band. Between the two planet bands sits a middle divider ring — every planet's
true-position tick points to it (not out to the zodiac).

Both rings carry the full readout — body glyph + degree° + sign glyph + minute′ — laid
radially with the same reading rules as the single natal wheel (degree→sign→minute,
reversed on the right half so both halves read left→right, kept upright), each ring's
readout laying away from the middle divider.

Three aspect layers cross the central hub, each independently switchable: **cross**
(inner×outer, bold, ON by default) plus each chart's own internal aspects (faint, OFF
by default). Cross-aspects are DATA, computed upstream — pass the list openephem's
``cross_aspects(inner, outer)`` returns as ``cross_aspects=``; this module only draws.

Input is the same plain chart dict the rest of ephemvis renders (openephem's
``assemble()`` shape). The outer chart may legitimately have ``angles=None`` /
``cusps=None`` (an untimed transit) — only the inner chart needs a house framework,
and even that is optional (a timeless inner chart falls back to 0° Aries at left).
"""

from __future__ import annotations

import math

from . import _fontdata
from .wheel import (
    _HALO_ROT_DEG,
    _HALO_TURN,
    _L,
    _SIGNS,
    ASPECT_CAT,
    ASPECT_STYLE,
    PALETTES,
    PLANET_ABBR,
    PLANET_GLYPHS,
    SIGN_ABBR,
    SIGN_GLYPHS,
    _conic,
    _dm_round,
    _dms_round,
    _esc,
    _is_wholesign_cusps,
    _spread,
    _theme_markup,
    body_label,
    sign_label,
)

# Radial clearance from a glyph's centre to its first readout token, as a fraction of the
# glyph size. This is now MEASURED per glyph from the embedded font's real ink bbox
# (_fontdata.GLYPH_METRICS) rather than guessed: a tall glyph (Saturn/Uranus) reserves half its
# real ink height, a short glyph (the lunar nodes) far less, so neither wastes radial space nor
# crowds the neighbouring ring. The fallback covers glyphs with no metric (a star ✦, a 2-letter
# abbreviation) and reproduces the old tall-glyph default.
_GLYPH_CLEAR_DEFAULT = 0.62
_GLYPH_CLEAR_GAP = 0.10          # radial gap beyond the glyph's ink, as a fraction of glyph size


def _glyph_clear(name: str) -> float:
    """Radial clearance (fraction of the glyph size) from a body's glyph centre to its first
    readout token = half the glyph's real ink height + a fixed gap. Falls back to the tall-glyph
    default when the body has no single-codepoint metric."""
    g = PLANET_GLYPHS.get(name)
    if g:
        m = _fontdata.GLYPH_METRICS.get(ord(g[0]))
        if m:
            _adv, ymin, ymax, _xmin, _xmax = m
            return (ymax - ymin) / 2.0 + _GLYPH_CLEAR_GAP
    return _GLYPH_CLEAR_DEFAULT


def render_biwheel_svg(inner_chart: dict, outer_chart: dict, *,
                       cross_aspects: list | None = None,
                       theme: str = "auto", size: int = 760,
                       title: str | None = None,
                       labels: tuple[str, str] = ("Inner", "Outer"),
                       key: bool = False,
                       show_cross_aspects: bool = True,
                       show_inner_aspects: bool = False,
                       show_outer_aspects: bool = False,
                       text_labels: bool = False) -> str:
    """Return an SVG string for a bi-wheel comparing two charts.

    ``inner_chart`` (radix) owns the ring, houses and orientation; ``outer_chart``'s
    planets are placed against it on the outer band. ``cross_aspects`` is the list from
    openephem's ``cross_aspects(inner, outer)`` (dicts with ``a`` = inner body, ``b`` =
    outer body); only the cross layer is drawn by default. Set ``show_inner_aspects`` /
    ``show_outer_aspects`` to also draw each chart's own internal aspects (faint).
    ``key=True`` draws a small legend naming the two charts from ``labels``.
    """
    inner_bodies = inner_chart.get("bodies") or {}
    if not inner_bodies:
        raise ValueError("the inner chart has no bodies to draw")
    outer_bodies = outer_chart.get("bodies") or {}

    cx = cy = size / 2.0
    r_out = size * 0.45              # outer edge (leaves a margin for AC/MC outside)
    Z = r_out * 0.890                # inner edge of the zodiac band (~20% thinner than the single wheel)
    # Two planet bands straddling a shared middle divider ring. The bands sit SYMMETRIC
    # about it: the outer band's inner edge and the inner band's outer edge are the same
    # distance from the ring. Both read glyph→degree→sign→minute laid INWARD, so from the
    # rim in: [outer glyph, deg, sign, min] · tick · ring · tick · [inner glyph, deg, sign, min].
    r_hnum_out = Z * 0.287           # house-ring outer (+5%, then +2.5%)
    r_hnum = Z * 0.256               # house numbers, centered in the ring band
    r_hub = Z * 0.225                # aspect hub == house-ring inner edge
    # The two planet rings are equal-width annuli: the shared ring sits centered between
    # the zodiac inner edge (Z) and the house ring, so [r_mid, Z] and [r_hnum_out, r_mid]
    # have the same radial width. Each chart's glyph hugs the OUTER edge of its band
    # (outer chart against the zodiac, inner chart just inside the shared ring); the
    # readout lays inward from the glyph.
    r_mid = (Z + r_hnum_out) / 2.0   # shared middle ring — centered -> equal-width bands
    r_glyph_out = Z * 0.945          # OUTER chart glyph, up against the zodiac ring
    r_glyph_in = r_mid - Z * 0.055 - size * 0.006    # INNER glyph just off the shared ring — only a
    #                                small nudge in, since the tight (near-true) spread means the
    #                                true-position leaders are short and don't need the extra room;
    #                                this keeps the readout band from being compressed.
    tick_len = Z * 0.02              # short true-position ticks straddling the shared ring
    glyphs = None if not text_labels else True
    apal = _L if theme == "auto" else PALETTES.get(theme, _L)

    angles = inner_chart.get("angles") or {}
    asc = angles.get("asc", 0.0)     # unknown-time -> 0 Aries at left
    cusps = inner_chart.get("cusps")

    rot_ref = asc
    if cusps and len(cusps) >= 12 and cusps[0] is not None and cusps[0] == cusps[0]:
        rot_ref = cusps[0]

    label_cusps = bool(cusps and len(cusps) >= 12 and not _is_wholesign_cusps(cusps, asc))
    wholesign = bool(cusps and len(cusps) >= 12 and _is_wholesign_cusps(cusps, asc))
    cusp_darc = 4.5
    cusp_dsec = 3.0
    cusp_hband = 5.0

    fpl = size * 0.0407 * 0.95       # planet glyph — biwheel draws it at 95% of the natal .planet
    #                                 size (applied inline below); fpl stays == the REAL rendered
    #                                 size, so glyph-clearance / spread math reflect it
    fdeg = size * 0.016              # degree/minute label spacing (tighter — two rings to fit)

    def pol(r, lon):
        """Ecliptic longitude -> (x, y). House-1 cusp at left, zodiac CCW."""
        a = math.radians(180.0 + (lon - rot_ref))
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def sp(r, deg):
        """Screen-space polar (independent of rotation) for halo bands."""
        a = math.radians(deg)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    P = []
    P.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
             f'width="{size}" height="{size}" style="cursor:default" role="img" '
             f'aria-label="{_esc(title or "bi-wheel")}">')
    P.append(_theme_markup(theme, size))
    P.append(f'<rect x="0" y="0" width="{size}" height="{size}" class="bg" fill="url(#bggrad)"/>')

    ring_radii = (r_out, Z, r_mid, r_hnum_out, r_hub)
    if apal.get("halo"):
        stops = apal["ring"]
        turn = _HALO_TURN - _HALO_ROT_DEG.get(theme, 0) / 360.0
        N = 120
        for rin, rout in ((Z, r_out), (r_hub, r_hnum_out)):
            for sgi in range(N):
                a0, a1 = 360.0 * sgi / N, 360.0 * (sgi + 1) / N
                col = _conic((a0 + a1) / 720.0 + turn, stops)
                x1, y1 = sp(rout, a0)
                x2, y2 = sp(rout, a1)
                x3, y3 = sp(rin, a1)
                x4, y4 = sp(rin, a0)
                P.append(f'<polygon points="{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} '
                         f'{x3:.1f},{y3:.1f} {x4:.1f},{y4:.1f}" fill="{col}"/>')
        for r in ring_radii:
            P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                     f'fill="none" stroke="rgba(38,44,60,.28)" stroke-width="1.4"/>')
    else:
        for r in ring_radii:
            P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="ring"/>')

    # --- zodiac: signs on the rim (inner chart's orientation) ---
    if wholesign:
        for i in range(12):
            gx, gy = pol((Z + r_out) / 2.0, i * 30.0)
            label = SIGN_ABBR[i] if glyphs else SIGN_GLYPHS[i] + "︎"
            P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="sign" '
                     f'dominant-baseline="central" text-anchor="middle">'
                     f'<title>{_esc(sign_label(i, angles, cusps))}</title>{label}</text>')
    elif not label_cusps:
        for i in range(12):
            lon0 = i * 30.0
            x1, y1 = pol(Z, lon0)
            x2, y2 = pol(r_out, lon0)
            P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="tick"/>')
            gx, gy = pol((Z + r_out) / 2.0, lon0 + 15.0)
            label = SIGN_ABBR[i] if glyphs else SIGN_GLYPHS[i] + "︎"
            P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="sign" '
                     f'dominant-baseline="central" text-anchor="middle">'
                     f'<title>{_esc(sign_label(i, angles, cusps))}</title>{label}</text>')

    # --- houses (inner chart): dividers in the number ring + dotted cusp out to the
    # middle ring only (never across the outer chart's band); sign glyph + DMS on the rim ---
    house_labels: list[str] = []
    if cusps and len(cusps) >= 12:
        _asc, _mc = angles.get("asc"), angles.get("mc")
        quad = (_asc is not None and _mc is not None
                and abs((cusps[0] - _asc + 180.0) % 360.0 - 180.0) < 0.5
                and abs((cusps[9] - _mc + 180.0) % 360.0 - 180.0) < 0.5)
        for i, c in enumerate(cusps):
            if c is None or c != c:
                continue
            cls = "cusp-angle" if (quad and i in (0, 3, 6, 9)) else "cusp"
            hx1, hy1 = pol(r_hub, c)
            hx2, hy2 = pol(r_hnum_out, c)
            P.append(f'<line x1="{hx1:.1f}" y1="{hy1:.1f}" x2="{hx2:.1f}" y2="{hy2:.1f}" class="hdiv"/>')
            # dotted cusp from the number ring all the way out to the zodiac — through both
            # planet rings and the shared divider, so the house framework spans the wheel
            dx1, dy1 = pol(r_hnum_out, c)
            dx2, dy2 = pol(Z, c)
            P.append(f'<line x1="{dx1:.1f}" y1="{dy1:.1f}" x2="{dx2:.1f}" y2="{dy2:.1f}" class="{cls}"/>')
            nc = cusps[(i + 1) % 12]
            if nc is not None and nc == nc:
                mid = c + (((nc - c) % 360.0) / 2.0)
                nx, ny = pol(r_hnum, mid)
                house_labels.append(f'<text x="{nx:.1f}" y="{ny:.1f}" class="housenum" '
                                    f'dominant-baseline="central" text-anchor="middle">{i + 1}</text>')
            if label_cusps:
                sidx, d, m, s = _dms_round(c)
                glyph = SIGN_ABBR[sidx] if glyphs else SIGN_GLYPHS[sidx] + "︎"
                rr = (Z + r_out) / 2.0
                ggx, ggy = pol(rr, c)
                htxt = "House %d cusp: %s %d°%02d′%02d″" % (i + 1, _SIGNS[sidx], d, m, s)
                P.append(f'<text x="{ggx:.1f}" y="{ggy:.1f}" class="sign" '
                         f'dominant-baseline="central" text-anchor="middle">'
                         f'<title>{_esc(htxt)}</title>{glyph}</text>')
                da = (c - rot_ref) % 360.0
                xm, ym = pol(rr, c - cusp_darc)
                xp, yp = pol(rr, c + cusp_darc)
                if da < cusp_hband or da > 360.0 - cusp_hband or abs(da - 180.0) < cusp_hband:
                    forward = ym <= yp
                else:
                    forward = xm <= xp
                unit = -1.0 if forward else 1.0
                dgx, dgy = pol(rr, c + unit * cusp_darc)
                mnx, mny = pol(rr, c - unit * cusp_darc)
                scx, scy = pol(rr, c - unit * (cusp_darc + cusp_dsec))
                P.append(f'<text x="{dgx:.1f}" y="{dgy:.1f}" class="cuspdeg" '
                         f'dominant-baseline="central" text-anchor="middle">{d}°</text>')
                P.append(f'<text x="{mnx:.1f}" y="{mny:.1f}" class="cuspmin" '
                         f'dominant-baseline="central" text-anchor="middle">{m:02d}′</text>')
                # seconds a touch smaller than the minutes (biwheel-only inline override).
                # inline STYLE, not a font-size attribute, so it beats the .cuspsec class's
                # `font:` shorthand.
                P.append(f'<text x="{scx:.1f}" y="{scy:.1f}" class="cuspsec" '
                         f'style="font-size:{size * 0.011:.1f}px" '
                         f'dominant-baseline="central" text-anchor="middle">{s:02d}″</text>')
        if label_cusps:
            placed_signs = {_dms_round(c)[0] for c in cusps if c is not None and c == c}
            rr = (Z + r_out) / 2.0
            for si in range(12):
                if si in placed_signs:
                    continue
                gx, gy = pol(rr, si * 30.0 + 15.0)
                glyph = SIGN_ABBR[si] if glyphs else SIGN_GLYPHS[si] + "︎"
                htxt = "%s — intercepted (no house cusp)" % _SIGNS[si]
                P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="sign-icept" '
                         f'dominant-baseline="central" text-anchor="middle">'
                         f'<title>{_esc(htxt)}</title>{glyph}</text>')

    def _tw(s: str, f: float) -> float:
        # rendered width of a readout token at font size f, summed from the embedded font's
        # REAL advance widths (_fontdata.GLYPH_METRICS[cp][0], a fraction of the em); the
        # fallback covers any char absent from the subset.
        total = 0.0
        for ch in s:
            m = _fontdata.GLYPH_METRICS.get(ord(ch))
            total += f * (m[0] if m else 0.55)
        return total

    def place_ring(bodies, r_glyph, tick_dir, r_floor):
        """Draw one chart's planet band. The glyph sits at ``r_glyph`` and the readout
        lays INWARD from it — glyph → degree → sign → minute — the SAME order on both
        bands (so both read the same way from the rim). A short true-position tick
        straddles the shared ring on this chart's side (``tick_dir`` = +1 just outside it
        for the outer chart, -1 just inside for the inner). Returns {name: hub point}."""
        # true per-glyph collision spacing (the whole point of the embedded metrics): each body's
        # angular half-width is its REAL ink width, so a narrow glyph (a node) barely nudges and
        # only genuinely wide/overlapping glyphs push apart — planets stay near their true longitude.
        def _hw(name):
            g = PLANET_GLYPHS.get(name)
            w = None
            if g:
                m = _fontdata.GLYPH_METRICS.get(ord(g[0]))
                if m:
                    w = m[4] - m[3]                  # ink width (xmax - xmin), em fractions
            if w is None:
                w = 0.62                             # 2-letter mark / glyph with no metric
            return math.degrees((w * fpl / 2.0) / r_glyph)
        half_widths = {n: _hw(n) for n in bodies}
        pad = math.degrees(fpl * 0.30 / r_glyph)     # small breathing gap between adjacent glyphs
        placed = _spread([(n, bodies[n]["lon"]) for n in bodies],
                         half_widths=half_widths, pad=pad)
        hub: dict[str, tuple[float, float]] = {}
        for name, lon, disp in placed:
            rx, ry = pol(r_mid, lon)                      # short tick on the shared ring
            ex, ey = pol(r_mid + tick_dir * tick_len, lon)
            P.append(f'<line x1="{rx:.1f}" y1="{ry:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" class="pmark"/>')
            gx, gy = pol(r_glyph, disp)
            if abs((disp - lon + 180.0) % 360.0 - 180.0) > 1.0:
                dxl, dyl = ex - gx, ey - gy              # dotted leader: glyph edge -> the tick
                te = min(fpl * 0.42 / abs(dxl) if dxl else 1e9,
                         fpl * 0.46 / abs(dyl) if dyl else 1e9)
                sx, sy = gx + dxl * te, gy + dyl * te
                P.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" class="leader"/>')
            retro = bodies[name].get("retro")
            lbl = _esc(body_label(name, bodies[name]))
            if glyphs:
                g = PLANET_ABBR.get(name, name[:2])
            else:
                base = PLANET_GLYPHS.get(name) or ("✦" if bodies[name].get("kind") == "star" else name[:2])
                g = base + "︎"
            # inline font-size (not the class): the .planet class sets size via the CSS `font:`
            # shorthand, which overrides a font-size *attribute* — so render the glyph at fpl (95%).
            P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="planet" '
                     f'style="font-size:{fpl:.2f}px" '
                     f'dominant-baseline="central" text-anchor="middle">'
                     f'<title>{lbl}</title>{_esc(g)}</text>')
            sidx_p, d0, m0 = _dm_round(lon)
            sgl = SIGN_ABBR[sidx_p] if glyphs else SIGN_GLYPHS[sidx_p] + "︎"
            rxm = "℞" if retro else ""
            ncls = "deg deg-rx" if retro else "deg"
            scls = "signn signn-rx" if retro else "signn"
            a = math.radians(180.0 + disp - rot_ref)
            rot0 = math.degrees(math.atan2(math.sin(a), -math.cos(a)))
            rot = rot0 - 180.0 if rot0 > 90.0 else (rot0 + 180.0 if rot0 < -90.0 else rot0)
            deg_t, min_t = f"{d0}°{rxm}", f"{m0:02d}′"
            # Rendered sizes: degree at the .deg class (f_deg), minute ~ the rim-minute size
            # (.cuspmin = f_deg*0.76), sign glyph ~ the degree size. Widths use each token's
            # OWN rendered size so the fit math below is accurate.
            deg_fs = size * 0.0215                        # .deg class size
            min_fs = size * 0.0215 * 0.76
            sign_fs = size * 0.0215
            toks = [(deg_t, ncls, None, _tw(deg_t, deg_fs)),   # (text, class, inline-size|None, width)
                    (sgl, scls, sign_fs, sign_fs),
                    (min_t, ncls, min_fs, _tw(min_t, min_fs))]
            if gx >= cx:                                  # right half: keep degree→sign→minute L→R
                toks.reverse()
            # per-glyph clearance from the real ink height: short glyphs (nodes) start their
            # readout closer in, tall glyphs (Saturn/Uranus) reserve the room they need
            r_lab0 = r_glyph - fpl * _glyph_clear(name)
            # Fit the readout into the band [r_floor, r_lab0] so it can't cross the glyph
            # (outer end) or the neighbouring ring (inner end): natural spacing when it fits,
            # else shrink the gaps, then (last resort) the slots for a wide retrograde degree.
            base_gap = fdeg * 0.30
            span = sum(w for (_, _, _, w) in toks)
            avail = r_lab0 - r_floor
            n = len(toks)
            if avail >= span + base_gap * (n - 1):
                gap, wscale = base_gap, 1.0
            elif avail >= span:
                gap, wscale = (avail - span) / (n - 1), 1.0
            else:
                gap, wscale = 0.0, max(0.55, avail / span)
            edge = r_lab0
            for tok, tcls, tfs, w in toks:                # tokens step INWARD (toward centre)
                ww = w * wscale
                lx, ly = pol(edge - ww / 2.0, disp)
                # inline STYLE (not a font-size attribute): the .deg/.signn classes set size
                # via the CSS `font:` shorthand, which overrides a font-size *attribute*.
                fs = f' style="font-size:{tfs:.1f}px"' if tfs else ""
                P.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="{tcls}"{fs} '
                         f'transform="rotate({rot:.1f} {lx:.1f} {ly:.1f})" '
                         f'dominant-baseline="central" text-anchor="middle">'
                         f'<title>{lbl}</title>{tok}</text>')
                edge -= ww + gap
            hub[name] = pol(r_hub, lon)
        return hub

    # both bands read the same way (glyph→deg→sign→min inward); ticks straddle the ring.
    # Each readout is fit between the glyph and the neighbouring ring: the outer band stops
    # just outside the shared ring, the inner band just outside the house-number ring.
    hub_outer = place_ring(outer_bodies, r_glyph_out, +1.0, r_mid + fdeg * 0.15)
    hub_inner = place_ring(inner_bodies, r_glyph_in, -1.0, r_hnum_out + fdeg * 0.15)

    # --- aspects (lines across the hub) ---
    def _draw_aspect(x1, y1, x2, y2, kind, faint):
        cat = ASPECT_CAT.get(kind, "soft")
        color = apal["a" + cat.capitalize()]
        _, dash = ASPECT_STYLE.get(kind, ("", "2 3"))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        op = ' opacity="0.42"' if faint else ""
        P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{color}" class="aspect"{da}{op}/>')

    if show_inner_aspects:
        for asp in inner_chart.get("aspects") or []:
            a, b = asp.get("a"), asp.get("b")
            if a in hub_inner and b in hub_inner:
                (x1, y1), (x2, y2) = hub_inner[a], hub_inner[b]
                _draw_aspect(x1, y1, x2, y2, asp.get("aspect"), faint=True)
    if show_outer_aspects:
        for asp in outer_chart.get("aspects") or []:
            a, b = asp.get("a"), asp.get("b")
            if a in hub_outer and b in hub_outer:
                (x1, y1), (x2, y2) = hub_outer[a], hub_outer[b]
                _draw_aspect(x1, y1, x2, y2, asp.get("aspect"), faint=True)
    if show_cross_aspects:
        for asp in cross_aspects or []:
            a, b = asp.get("a"), asp.get("b")
            if a in hub_inner and b in hub_outer:
                (x1, y1), (x2, y2) = hub_inner[a], hub_outer[b]
                _draw_aspect(x1, y1, x2, y2, asp.get("aspect"), faint=False)

    # house numbers last, on top of the cusp lines
    P.extend(house_labels)

    # --- optional key (bottom-left): names the two charts ---
    if key:
        kx = size * 0.024
        li, lo = labels
        P.append(f'<text x="{kx:.1f}" y="{size*0.930:.1f}" class="prof-key">'
                 f'<tspan class="prof-key-em">Inner:</tspan> {_esc(li)}</text>')
        P.append(f'<text x="{kx:.1f}" y="{size*0.962:.1f}" class="prof-key">'
                 f'<tspan class="prof-key-em">Outer:</tspan> {_esc(lo)}</text>')

    if title:
        P.append(f'<text x="{cx:.1f}" y="{size*0.04:.1f}" class="title" '
                 f'text-anchor="middle">{_esc(title)}</text>')
    P.append('</svg>')
    return "\n".join(P)


if __name__ == "__main__":
    from openephem import assemble, cross_aspects, resolve  # type: ignore
    _inner = assemble(resolve(date=(1990, 5, 15), time=(14, 30), place="New York, NY"))
    _outer = assemble(resolve(date=(2026, 9, 15), time=(12, 0), place="New York, NY"))
    _cx = cross_aspects(_inner, _outer)
    with open("biwheel_demo.svg", "w", encoding="utf-8") as _f:
        _f.write(render_biwheel_svg(_inner, _outer, cross_aspects=_cx,
                                    labels=("Natal", "Transit"), title="Bi-wheel"))
