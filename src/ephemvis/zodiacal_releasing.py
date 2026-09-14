#!/usr/bin/env python3
"""
zodiacal_releasing.py — the Zodiacal Releasing (Valens) timeline as a self-contained SVG.  [SHIP]

Zodiacal Releasing is a nested temporal sequence, not a zodiac wheel, so it renders as a
horizontal timeline: a top row of level-1 (L1) periods and a bottom row of their level-2
(L2) sub-periods, each segment colored by the *element* of its sign (Fire/Earth/Air/Water
— four categories separate cleanly for color-vision deficiency) and carrying the sign's
glyph as the primary identifier. Each period's **angularity** from the Lot is shown as a
top accent bar: a solid ink bar for *angular* (a peak), a two-color *dotted* bar (ink
interleaved with a light tone, so it stays legible on the dark Earth/Water bands) for
*succedent*, nothing for *cadent* — pattern, not opacity, carrying the "less angular" distinction. A Loosing-of-the-Bond
jump is marked where it occurs, its weight matching its structural depth: an **L1** loosing is
the deepest, rarest cut (a full L1 circuit ≈ 211 years, so it surfaces only in extended /
teaching horizons); the **L2** loosing — about 17½ years into a long chapter — is the one that
actually punctuates a life, and stays clearly legible.
Input is the chart dict openephem's ``assemble()`` returns; it must carry a
``zodiacal_releasing`` block (openephem adds one when given ``releasing_as_of=``). The table
companion is trivially built from the same block.
"""

from __future__ import annotations

from datetime import date as _date

from .profection_wheel import glyphs_by_year, render_profection_wheel_svg, theme_lord_colors
from .wheel import PALETTES

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_GLYPH = {"Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋", "Leo": "♌",
          "Virgo": "♍", "Libra": "♎", "Scorpio": "♏", "Sagittarius": "♐",
          "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓"}
_ELEMENT = ["Fire", "Earth", "Air", "Water"]      # by sign_index % 4 (Aries=Fire)
_EL_SIGNS = {"Fire": ("Aries", "Leo", "Sagittarius"), "Earth": ("Taurus", "Virgo", "Capricorn"),
             "Air": ("Gemini", "Libra", "Aquarius"), "Water": ("Cancer", "Scorpio", "Pisces")}
# The four elements take theme-derived colors (the shared theme_lord_colors derivation, four
# categories off each theme's ramp) so releasing recolors per theme like the rest of the suite.
# The sign glyph on every band — and in the legend — is the primary identifier; color supports.
_SYM = "'Segoe UI Symbol','Noto Sans Symbols2','Apple Symbols',system-ui,sans-serif"
_UI = "system-ui,-apple-system,Segoe UI,Roboto,sans-serif"


def _element(sign_index: int) -> str:
    return _ELEMENT[sign_index % 4]


def _ang(period: dict) -> str | None:
    """A period's angularity for the accent bar. openephem emits it directly; fall back to
    the older ``peak`` boolean (angular / none) for data that predates the field."""
    return period.get("angularity") or ("angular" if period.get("peak") else None)


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _lum(h):
    a = _rgb(h)
    return 0.299 * a[0] + 0.587 * a[1] + 0.114 * a[2]


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ord(iso: str) -> int:
    return _date.fromisoformat(iso[:10]).toordinal()


def _l1_element_by_age(zr: dict, ages) -> list:
    """The element of the level-1 releasing sign at each integer age (band color)."""
    tl = zr.get("timeline") or []
    out: list = []
    for a in ages:
        el = None
        for p in tl:
            if p["age_start"] <= a < p["age_end"]:
                el = _element(p["sign_index"])
                break
        out.append(el)
    return out


def _l2_segments(zr: dict, max_age: float):
    """Every level-2 sub-period as (age_start, age_end, sign_index), fractional ages (mapped
    from the L2 ISO dates onto each L1 span). An L1 period with no L2 contributes itself."""
    tl = zr.get("timeline") or []
    out = []
    for b in tl:
        a0, a1 = b["age_start"], b["age_end"]
        l2 = b.get("l2", [])
        if not l2:
            if a0 < max_age:
                out.append((a0, min(a1, max_age), b["sign_index"]))
            continue
        po0, po1 = _ord(b["start"]), _ord(b["end"])
        span = max(po1 - po0, 1)
        for sub in l2:
            sa0 = a0 + (a1 - a0) * (_ord(sub["start"]) - po0) / span
            sa1 = a0 + (a1 - a0) * (_ord(sub["end"]) - po0) / span
            if sa0 < max_age:
                out.append((sa0, min(sa1, max_age), sub["sign_index"]))
    return out


def _chart_style(chart: dict, zr: dict, *, theme: str, size: int, title: str,
                 max_age: int, sub_style: str = "ticks", layout: str = "annulus") -> str:
    """Roll releasing onto the annual-profection wheel: each age cell takes the L1 sign's
    element color and the L2 sign's glyph, on the shared natal-chart core. (Angularity /
    peak / loosing-of-the-bond markers stay on the horizontal timeline for now.)"""
    if not chart.get("profections"):
        raise ValueError("the zodiacal-releasing chart style draws on the annual-profection "
                         "wheel, so the chart also needs a 'profections' block — assemble with "
                         "both releasing_as_of= and profection_as_of= (same date)")
    asc = (chart.get("angles") or {}).get("asc")
    asc_sign = SIGNS[int(asc // 30) % 12] if asc is not None else ""
    nring = max_age // 12 + 1
    ages = range(nring * 12)
    major_by_age = _l1_element_by_age(zr, ages)                 # band color = L1 element
    l2 = _l2_segments(zr, nring * 12)
    glyph_by_age = glyphs_by_year([(a0, a1, SIGNS[si]) for a0, a1, si in l2], nring * 12)
    sub_segments = [(a0, a1, _element(si)) for a0, a1, si in l2]   # sub color = L2 element
    glyph_map = dict(_GLYPH)          # L2 sign name -> its glyph (cells); legend is element+swatch
    cur = zr.get("current", {})
    path = " › ".join(cur[lvl]["sign"] for lvl in ("l1", "l2", "l3", "l4") if lvl in cur)
    lot = str(zr.get("lot", "fortune")).title()
    subtitle = [f"{lot} in {zr.get('lot_sign', '')}"]       # short stacked lines: clear of the wheel
    if asc_sign:
        subtitle.append(f"{asc_sign} rising")
    if zr.get("age") is not None:
        subtitle.append(f"Age {zr['age']}")
    caption = ((f"Releasing: {path}   " if path else "")
               + "(band = L1 element · glyph = L2 sign)")
    return render_profection_wheel_svg(
        chart, theme=theme, size=size, max_age=max_age, layout=layout,
        timelord={"title": title, "subtitle_lines": subtitle, "lord_names": list(_ELEMENT),
                  "lord_colors": theme_lord_colors(theme, _ELEMENT), "glyph_map": glyph_map,
                  "major_by_age": major_by_age, "glyph_by_age": glyph_by_age,
                  "sub_segments": sub_segments, "sub_style": sub_style, "footer_caption": caption})


def render_zodiacal_releasing_svg(chart: dict, *, theme: str = "light",
                                  max_age: float = 84.0, width: int = 1160,
                                  title: str = "Zodiacal Releasing", style: str = "timeline",
                                  sub_style: str = "ticks", size: int = 620,
                                  layout: str = "annulus") -> str:
    """Render the zodiacal releasing for ``chart`` as an SVG string.

    ``style`` is ``"timeline"`` (default; the horizontal L1/L2 bars with angularity and
    loosing-of-the-bond markers) or ``"chart"`` (releasing projected onto the natal
    whole-sign wheel, colored by element and glyphed by sign). ``theme`` is any key of
    :data:`ephemvis.PALETTES` ('auto' -> light). ``max_age`` is the timeline's right edge
    (years); ``size`` is the chart-wheel side; ``layout`` (``"annulus"`` default or
    ``"spiral"``) applies only to ``style="chart"``. Raises ``ValueError`` without a
    ``zodiacal_releasing`` block (or, for the chart style, without a ``profections`` block).
    """
    zr = chart.get("zodiacal_releasing")
    if not zr:
        raise ValueError("chart has no 'zodiacal_releasing' block (build it with "
                         "openephem's assemble(..., releasing_as_of=))")
    if style == "chart":
        return _chart_style(chart, zr, theme=theme, size=size, title=title,
                            max_age=int(round(max_age)), sub_style=sub_style, layout=layout)
    if style != "timeline":
        raise ValueError("style must be 'timeline' or 'chart'")
    pal = PALETTES.get("light" if theme == "auto" else theme, PALETTES["light"])
    ink, bg, muted, line = pal["planet"], pal["bg"][0], pal["deg"], pal["cusp"]
    el_col = theme_lord_colors(theme, _ELEMENT)       # per-theme element colors (match the suite)
    cur_age = zr.get("age")                           # whole years, for the subtitle text
    # the marker / current outline track the actual as-of date (a fractional age)
    mark_age = cur_age
    tl0 = zr.get("timeline") or []
    if zr.get("as_of") and tl0:
        try:
            mark_age = (_ord(zr["as_of"]) - _ord(tl0[0]["start"])) / 365.2425
        except ValueError:                            # timeline lacks real dates → integer age
            mark_age = cur_age

    # `width` is the DISPLAY width; all interior coordinates + the hardcoded fonts/strokes/heights
    # are drawn in a fixed W-wide design space, and the viewBox scales the whole thing to `width`.
    # So the timeline keeps its proportions at any width (the fonts used to bloat at a narrow one).
    W = 1160
    padL, padR = 20, 20
    x0, x1 = padL, W - padR
    l1_y, l1_h = 70, 50
    l2_y, l2_h = l1_y + l1_h + 8, 30
    axis_y = l2_y + l2_h
    height = axis_y + 82          # room for the AGE row + a clear line before the legend

    def X(age):
        return x0 + (x1 - x0) * min(age, max_age) / max_age

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
         f'width="{width}" height="{width / W * height:g}" font-family="{_UI}" role="img" '
         f'aria-label="{_esc(title)}"><rect width="{W}" height="{height}" fill="{bg}"/>']
    P.append(f'<text x="{padL}" y="28" fill="{ink}" font-size="20" font-weight="700">{_esc(title)}</text>')

    cur = zr.get("current", {})
    path = " › ".join(cur[lvl]["sign"] for lvl in ("l1", "l2", "l3", "l4") if lvl in cur)
    lot = str(zr.get("lot", "fortune")).title()
    sub = f'Lot of {lot} in {zr.get("lot_sign", "")}'
    if cur_age is not None:
        sub += f' · age {cur_age}'
    if path:
        sub += f' · {path}'
    P.append(f'<text x="{padL}" y="50" fill="{muted}" font-size="15.5">{_esc(sub)}</text>')

    # age grid + labels
    step = 6
    a = 0
    while a <= max_age:
        gx = X(a)
        P.append(f'<line x1="{gx:.1f}" y1="{l1_y}" x2="{gx:.1f}" y2="{axis_y}" '
                 f'stroke="{line}" stroke-width="1"/>')
        P.append(f'<text x="{gx:.1f}" y="{axis_y + 17}" fill="{muted}" font-size="13" '
                 f'text-anchor="middle">{a}</text>')
        a += step
    P.append(f'<text x="{(x0+x1)/2:.0f}" y="{axis_y + 34}" fill="{muted}" font-size="13" '
             f'text-anchor="middle" letter-spacing="1">AGE</text>')

    def band(y, bh, sign_index, a0, a1, glyph_fs, *, angularity=None, current=False,
             lb=False, lb_major=False):
        xa, xb = X(a0), X(a1)
        if a0 >= max_age or xb - xa < 0.6:
            return
        col = el_col[_element(sign_index)]
        P.append(f'<rect x="{xa:.1f}" y="{y}" width="{xb-xa:.1f}" height="{bh}" fill="{col}" '
                 f'stroke="{bg}" stroke-width="1.5" rx="3"/>')
        # current-period box FIRST, so the angularity bar below caps its top edge instead of
        # running as a second parallel line beside it (which read as a stray extra marker).
        if current:
            P.append(f'<rect x="{xa+1:.1f}" y="{y+1}" width="{xb-xa-2:.1f}" height="{bh-2}" '
                     f'fill="none" stroke="{ink}" stroke-width="2.4" rx="2"/>')
        # angularity accent bar along the top edge, drawn on top: a *solid* ink bar = angular (a
        # peak), a two-color *dotted* bar = succedent, nothing = cadent. The succedent dots
        # interleave ink with the light band-border color (no transparent gaps), so one color
        # always contrasts — legible on the dark Earth/Water bands where an ink-only dash blends.
        if angularity == "angular":
            P.append(f'<rect x="{xa+1.5:.1f}" y="{y}" width="{max(xb-xa-3,0):.1f}" height="3.5" '
                     f'fill="{ink}" rx="1.5"/>')
        elif angularity == "succedent":
            for _c, _o in ((ink, 0), (bg, 4)):
                P.append(f'<line x1="{xa+2:.1f}" y1="{y+2.2:.1f}" x2="{xb-2:.1f}" y2="{y+2.2:.1f}" '
                         f'stroke="{_c}" stroke-width="3.2" stroke-dasharray="4 4" '
                         f'stroke-dashoffset="{_o}"/>')
        if lb:                                           # loosing-of-the-bond jump marker
            # Both rows carry a true "LB", distinguished by structural depth: the L1 loosing is
            # the deepest, rarest cut (a full L1 circuit ≈ 211 yr, so it appears only in extended
            # / teaching horizons) — heaviest; the L2 loosing (≈17½ yr into a long chapter) is the
            # one that actually punctuates a life — kept clearly legible, a touch lighter.
            ext, sw, lfs, lwt = (7, 2.2, 11, "800") if lb_major else (5, 1.5, 9.5, "700")
            P.append(f'<line x1="{xa:.1f}" y1="{y-ext}" x2="{xa:.1f}" y2="{y+bh+ext}" '
                     f'stroke="{ink}" stroke-width="{sw}" stroke-dasharray="3 2"/>')
            P.append(f'<text x="{xa+3:.1f}" y="{y-8:.0f}" fill="{ink}" font-size="{lfs}" '
                     f'font-weight="{lwt}">LB</text>')
        if xb - xa > 18:
            tc = "#141414" if _lum(col) > 140 else "#ffffff"
            P.append(f'<text x="{(xa+xb)/2:.1f}" y="{y + bh/2:.1f}" fill="{tc}" font-family="{_SYM}" '
                     f'font-size="{glyph_fs}" text-anchor="middle" dominant-baseline="central">'
                     f'{_esc(_GLYPH[SIGNS[sign_index]])}︎</text>')

    for b in zr["timeline"]:
        a0, a1 = b["age_start"], b["age_end"]
        si = b["sign_index"]
        l1_cur = mark_age is not None and a0 <= mark_age < a1
        band(l1_y, l1_h, si, a0, a1, 19, angularity=_ang(b),
             current=l1_cur, lb=b.get("lb", False), lb_major=True)
        # L2 sub-periods tile the L1 span; map their ISO dates onto the age axis
        l2 = b.get("l2", [])
        if not l2:
            continue
        po0, po1 = _ord(b["start"]), _ord(b["end"])
        span = max(po1 - po0, 1)
        for s in l2:
            sa0 = a0 + (a1 - a0) * (_ord(s["start"]) - po0) / span
            sa1 = a0 + (a1 - a0) * (_ord(s["end"]) - po0) / span
            band(l2_y, l2_h, s["sign_index"], sa0, sa1, 13,
                 angularity=_ang(s), lb=s.get("lb", False), lb_major=False,
                 current=mark_age is not None and sa0 <= mark_age < sa1)

    # current-age marker + the as-of date, set up and to the right of the dot
    if mark_age is not None:
        cx = X(mark_age)
        P.append(f'<line x1="{cx:.1f}" y1="{l1_y-10}" x2="{cx:.1f}" y2="{axis_y+3}" '
                 f'stroke="{ink}" stroke-width="2"/>')
        P.append(f'<circle cx="{cx:.1f}" cy="{l1_y-10}" r="4" fill="{ink}"/>')
        if zr.get("as_of"):
            asof = _date.fromisoformat(zr["as_of"][:10])
            months = ("January", "February", "March", "April", "May", "June", "July",
                      "August", "September", "October", "November", "December")
            label = f"{months[asof.month-1]} {asof.day}, {asof.year}"
            P.append(f'<text x="{cx+8:.1f}" y="{l1_y-16:.0f}" fill="{ink}" font-family="{_UI}" '
                     f'font-size="13" font-weight="600">{label}</text>')

    # legend — each element with its three sign glyphs (the bands' identifier), then peak + LB,
    # sized to match the firdaria / decennials timelines
    ly = height - 14
    lx = float(padL)
    for el in _ELEMENT:
        glyphs = " ".join(_GLYPH[s] for s in _EL_SIGNS[el])
        gtag = f' (<tspan font-family="{_SYM}" font-size="15.5">{glyphs}</tspan>)'
        P.append(f'<rect x="{lx:.1f}" y="{ly-11}" width="14" height="14" rx="2" fill="{el_col[el]}"/>')
        P.append(f'<text x="{lx+19:.1f}" y="{ly}" fill="{muted}" font-size="13.5">{el}{gtag}</text>')
        lx += 40 + len(el) * 7.6 + 56
    lx += 6
    # angularity, most to least active: angular (a peak) = solid bar, succedent = two-color
    # dotted bar (ink + band-border, legible on any band), cadent = none.
    P.append(f'<rect x="{lx:.1f}" y="{ly-9}" width="14" height="5" rx="1.5" fill="{ink}"/>')
    P.append(f'<text x="{lx+19:.1f}" y="{ly}" fill="{muted}" font-size="13.5">angular (peak)</text>')
    lx += 40 + len("angular (peak)") * 6.9
    for _c, _o in ((ink, 0), (bg, 4)):       # same (ink, bg) pair as the bands, so it matches
        P.append(f'<line x1="{lx:.1f}" y1="{ly-6.5}" x2="{lx+14:.1f}" y2="{ly-6.5}" stroke="{_c}" '
                 f'stroke-width="3.2" stroke-dasharray="4 4" stroke-dashoffset="{_o}"/>')
    P.append(f'<text x="{lx+19:.1f}" y="{ly}" fill="{muted}" font-size="13.5">succedent</text>')
    lx += 40 + len("succedent") * 6.9
    P.append(f'<line x1="{lx+6:.1f}" y1="{ly-12}" x2="{lx+6:.1f}" y2="{ly+2}" stroke="{ink}" '
             f'stroke-width="1.6" stroke-dasharray="3 2"/>')
    P.append(f'<text x="{lx+16:.1f}" y="{ly}" fill="{muted}" font-size="13.5">loosing of the bond</text>')
    P.append("</svg>")
    return "\n".join(P)


if __name__ == "__main__":
    from openephem import assemble, resolve
    r = resolve(date=(2000, 1, 1), time=(12, 0), lat=51.4779, lon=-0.0015, tz="Europe/London")
    c = assemble(r, releasing_as_of=(2026, 6, 1))
    with open("zr_demo.svg", "w", encoding="utf-8") as fh:
        fh.write(render_zodiacal_releasing_svg(c, theme="dark"))
    print("wrote zr_demo.svg  |", {k: v["sign"] for k, v in c["zodiacal_releasing"]["current"].items()})
