#!/usr/bin/env python3
"""
decennials.py — the Decennials (Valens time-lords) as a self-contained SVG.  [SHIP]

The Decennials are a temporal sequence of chronocratorships, so they render as a horizontal
timeline: a top row of the general decennial periods (each a fixed 10 years 9 months) and a
bottom row of their planetary sub-periods (unequal — each planet's minor years reckoned in
months), each segment colored and glyphed by its ruling planet, with the current general/
sub lord outlined and a marker at the current age. Input is the chart dict openephem's
``assemble()`` returns; it must carry a ``decennials`` block (openephem adds one when given
``decennials_as_of=``). The table companion is trivially built from the same block.

Planet identity is carried by the glyph on each segment (and the legend); color is a
supporting cue (which also covers color-vision-deficient and print cases).
"""

from __future__ import annotations

from datetime import date as _date

from .profection_wheel import glyphs_by_year, render_profection_wheel_svg, theme_lord_colors
from .wheel import PALETTES, SYM_FAMILY, TXT_FAMILY, font_face_css

_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces")
_GLYPH = {"Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
          "Jupiter": "♃", "Saturn": "♄"}
_LEGEND = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]   # Chaldean order
_SYM = SYM_FAMILY        # embedded symbol family (or system fallback)
_UI = TXT_FAMILY         # embedded text family (or system-ui)


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _lum(h):
    a = _rgb(h)
    return 0.299 * a[0] + 0.587 * a[1] + 0.114 * a[2]


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ord(iso: str) -> int:
    return _date.fromisoformat(iso[:10]).toordinal()


def _major_lord_at(dec: dict, age: float):
    """The general (major) decennial lord governing a given age, wrapping past the timeline
    into the repeating ~75¼-year cycle."""
    tl = dec.get("timeline") or []
    if not tl:
        return None
    cycle = tl[-1]["age_end"]
    if cycle > 0:
        while age >= cycle:
            age -= cycle
    for p in tl:
        if p["age_start"] <= age < p["age_end"]:
            return p["ruler"]
    return tl[-1]["ruler"]


def _sub_segments(dec: dict, max_age: float):
    """Every decennial sub-period as (age_start, age_end, ruler) in fractional ages, out to
    ``max_age`` (the ~75¼-year pattern repeats, so later cycles are shifted copies)."""
    tl = dec.get("timeline") or []
    if not tl:
        return []
    cycle = tl[-1]["age_end"]
    out = []
    reps = int(max_age / cycle) + 1 if cycle > 0 else 1
    for rep in range(reps):
        base = rep * cycle
        for p in tl:
            po0, po1 = _ord(p["start"]), _ord(p["end"])
            span = max(po1 - po0, 1)
            for s in p.get("subs", []):
                a0 = base + p["age_start"] + (_ord(s["start"]) - po0) / span * (p["age_end"] - p["age_start"])
                a1 = base + p["age_start"] + (_ord(s["end"]) - po0) / span * (p["age_end"] - p["age_start"])
                if a0 < max_age:
                    out.append((a0, min(a1, max_age), s["ruler"]))
    return out


def _chart_style(chart: dict, dec: dict, *, theme: str, size: int, title: str,
                 max_age: int, sub_style: str = "ticks", layout: str = "annulus") -> str:
    """Roll the decennial timeline onto the annual-profection wheel: keep the age annuli,
    but stamp each age cell with that year's decennial (sub-)lord glyph."""
    if not chart.get("profections"):
        raise ValueError("the decennials chart style draws on the annual-profection wheel, "
                         "so the chart also needs a 'profections' block — assemble with "
                         "both decennials_as_of= and profection_as_of= (same date)")
    cur = dec.get("current", {})
    major, sub = cur.get("major"), cur.get("sub")
    asc = (chart.get("angles") or {}).get("asc")
    asc_sign = _SIGNS[int(asc // 30) % 12] if asc is not None else ""
    nring = max_age // 12 + 1
    ages = range(nring * 12)
    major_by_age = [_major_lord_at(dec, a) for a in ages]      # band color = major lord
    sub_segments = _sub_segments(dec, nring * 12)              # exact sub-period boundaries
    # glyph per year: every sub-period claims its peak-coverage cell (not the sub at the
    # birthday instant), so a short sub — e.g. Venus, ~8 months — never drops out of the ring
    glyph_by_age = glyphs_by_year(sub_segments, nring * 12)
    subtitle = [f"{asc_sign} rising" if asc_sign else f"From {dec.get('start', '')}"]
    if dec.get("age") is not None:
        subtitle.append(f"Age {dec['age']}")
    caption = (f"Decennial lord: {major or ''}"
               + (f" / {sub}" if sub and sub != major else "") + "   (band = major · glyph = sub)")
    return render_profection_wheel_svg(
        chart, theme=theme, size=size, max_age=max_age, layout=layout,
        timelord={"title": title, "subtitle_lines": subtitle, "lord_names": list(_LEGEND),
                  "major_by_age": major_by_age, "glyph_by_age": glyph_by_age,
                  "sub_segments": sub_segments, "sub_style": sub_style,
                  "footer_caption": caption})


def render_decennials_svg(chart: dict, *, theme: str = "light", style: str = "timeline",
                          sub_style: str = "ticks", max_age: float = 76.0, width: int = 1160,
                          size: int = 620, title: str = "Decennials",
                          layout: str = "annulus") -> str:
    """Render the decennials for ``chart`` as an SVG string.

    ``style`` is ``"timeline"`` (default; the horizontal period bars) or ``"chart"`` (the
    active lord projected onto the natal whole-sign wheel). ``theme`` is any key of
    :data:`ephemvis.PALETTES` ('auto' -> light). ``max_age`` is the timeline's right edge
    (years; a full cycle is ~75¼); ``size`` is the chart-wheel side. ``layout`` (``"annulus"``
    default or ``"spiral"``) applies only to ``style="chart"`` — it lays the age bands as
    concentric rings or as one expanding coil; it is ignored for the horizontal timeline.
    Raises ``ValueError`` without a ``decennials`` block (or, for the chart style, without an
    Ascendant).
    """
    dec = chart.get("decennials")
    if not dec:
        raise ValueError("chart has no 'decennials' block (build it with openephem's "
                         "assemble(..., decennials_as_of=))")
    if style == "chart":
        return _chart_style(chart, dec, theme=theme, size=size, title=title,
                            max_age=int(round(max_age)), sub_style=sub_style, layout=layout)
    if style != "timeline":
        raise ValueError("style must be 'timeline' or 'chart'")
    pal = PALETTES.get("light" if theme == "auto" else theme, PALETTES["light"])
    ink, bg, muted, line = pal["planet"], pal["bg"][0], pal["deg"], pal["cusp"]
    lord_col = theme_lord_colors(theme, _LEGEND)      # theme-derived lord colors (match wheel)
    cur_age = dec.get("age")                          # whole years, for the subtitle text
    # the marker / current-outline track the *actual* as-of date (sub-periods can be short,
    # so the integer-age birthday can fall in a different sub than the as-of date does)
    mark_age = cur_age
    tl0 = dec.get("timeline") or []
    if dec.get("as_of") and tl0:
        mark_age = (_ord(dec["as_of"]) - _ord(tl0[0]["start"])) / 365.2425

    # `width` is the DISPLAY width; interior coordinates + hardcoded fonts/strokes/heights are
    # drawn in a fixed W-wide design space and the viewBox scales the whole thing to `width`, so
    # the timeline keeps its proportions at any width (the fonts used to bloat at a narrow one).
    W = 1160
    padL, padR = 20, 20
    x0, x1 = padL, W - padR
    major_y, major_h = 70, 50
    sub_y, sub_h = major_y + major_h + 8, 30
    axis_y = sub_y + sub_h
    height = axis_y + 82          # room for the AGE row + a clear line before the legend

    def X(age):
        return x0 + (x1 - x0) * min(age, max_age) / max_age

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
         f'width="{width}" height="{width / W * height:g}" font-family="{_UI}" role="img" '
         f'aria-label="{_esc(title)}"><rect width="{W}" height="{height}" fill="{bg}"/>']
    P.append(f'<text x="{padL}" y="28" fill="{ink}" font-size="20" font-weight="700">{_esc(title)}</text>')

    cur = dec.get("current", {})
    sub_txt = f' / {cur.get("sub", "")}' if cur.get("sub") else ""
    line2 = f'From {dec.get("start", "")}'
    if cur_age is not None:
        line2 += f' · age {cur_age} · {cur.get("major", "")}{sub_txt}'
    P.append(f'<text x="{padL}" y="50" fill="{muted}" font-size="15.5">{_esc(line2)}</text>')

    # age grid + labels
    step = 6
    a = 0
    while a <= max_age:
        gx = X(a)
        P.append(f'<line x1="{gx:.1f}" y1="{major_y}" x2="{gx:.1f}" y2="{axis_y}" '
                 f'stroke="{line}" stroke-width="1"/>')
        P.append(f'<text x="{gx:.1f}" y="{axis_y + 17}" fill="{muted}" font-size="13" '
                 f'text-anchor="middle">{a}</text>')
        a += step
    P.append(f'<text x="{(x0+x1)/2:.0f}" y="{axis_y + 34}" fill="{muted}" font-size="13" '
             f'text-anchor="middle" letter-spacing="1">AGE</text>')

    current_rects = []           # drawn as a final overlay so later bands don't clip them
    def band(y, bh, ruler, a0, a1, glyph_fs, current=False):
        xa, xb = X(a0), X(a1)
        if a0 >= max_age or xb - xa < 0.6:
            return
        col = lord_col.get(ruler, muted)
        P.append(f'<rect x="{xa:.1f}" y="{y}" width="{xb-xa:.1f}" height="{bh}" fill="{col}" '
                 f'stroke="{bg}" stroke-width="1.5" rx="3"/>')
        if current:
            current_rects.append((xa, y, xb - xa, bh))
        if xb - xa > 18:
            tc = "#141414" if _lum(col) > 140 else "#ffffff"
            P.append(f'<text x="{(xa+xb)/2:.1f}" y="{y + bh/2:.1f}" fill="{tc}" font-family="{_SYM}" '
                     f'font-size="{glyph_fs}" text-anchor="middle" dominant-baseline="central">'
                     f'{_esc(_GLYPH.get(ruler, ruler[:2]))}︎</text>')

    # the ~75¼-year cycle repeats, so tile it across the axis to fill max_age
    periods = dec["timeline"]
    cycle = periods[-1]["age_end"] if periods else 0.0
    shift = 0.0
    while shift < max_age - 1e-6:
        for b in periods:
            a0, a1 = b["age_start"] + shift, b["age_end"] + shift
            if a0 >= max_age:
                break
            maj_cur = mark_age is not None and a0 <= mark_age < a1
            band(major_y, major_h, b["ruler"], a0, a1, 20, current=maj_cur)
            subs = b.get("subs", [])
            if not subs:
                continue
            po0, po1 = _ord(b["start"]), _ord(b["end"])
            span = max(po1 - po0, 1)                  # subs are unequal → map by date
            for s in subs:
                sa0 = a0 + (a1 - a0) * (_ord(s["start"]) - po0) / span
                sa1 = a0 + (a1 - a0) * (_ord(s["end"]) - po0) / span
                band(sub_y, sub_h, s["ruler"], sa0, sa1, 13,
                     current=mark_age is not None and sa0 <= mark_age < sa1)
        if cycle <= 0:
            break
        shift += cycle

    # current major/sub outlines — overlay pass, on top of every band so nothing clips them
    for xa, y, w, bh in current_rects:
        P.append(f'<rect x="{xa+1:.1f}" y="{y+1}" width="{w-2:.1f}" height="{bh-2}" '
                 f'fill="none" stroke="{ink}" stroke-width="2.4" rx="2"/>')

    # current-age marker + the as-of date, set up and to the right of the dot
    if mark_age is not None:
        cx = X(mark_age)
        P.append(f'<line x1="{cx:.1f}" y1="{major_y-8}" x2="{cx:.1f}" y2="{axis_y+3}" '
                 f'stroke="{ink}" stroke-width="2"/>')
        P.append(f'<circle cx="{cx:.1f}" cy="{major_y-8}" r="4" fill="{ink}"/>')
        if dec.get("as_of"):
            asof = _date.fromisoformat(dec["as_of"][:10])
            months = ("January", "February", "March", "April", "May", "June", "July",
                      "August", "September", "October", "November", "December")
            label = f"{months[asof.month-1]} {asof.day}, {asof.year}"
            P.append(f'<text x="{cx+8:.1f}" y="{major_y-14:.0f}" fill="{ink}" font-family="{_UI}" '
                     f'font-size="13" font-weight="600">{label}</text>')

    # legend — swatch + "Name (glyph)" so the symbol is learnable from the label
    ly = height - 14
    lx = float(padL)
    for r in _LEGEND:
        gl = _GLYPH.get(r, "")
        gtag = f' (<tspan font-family="{_SYM}" font-size="15.5">{_esc(gl)}</tspan>)' if gl else ""
        P.append(f'<rect x="{lx:.1f}" y="{ly-11}" width="14" height="14" rx="2" fill="{lord_col[r]}"/>')
        P.append(f'<text x="{lx+19:.1f}" y="{ly}" fill="{muted}" font-size="13.5">{_esc(r)}{gtag}</text>')
        lx += 52 + len(r) * 7.6
    P.append(font_face_css())
    P.append("</svg>")
    return "\n".join(P)


if __name__ == "__main__":
    from openephem import assemble, resolve
    r = resolve(date=(2000, 1, 1), time=(12, 0), lat=51.4779, lon=-0.0015, tz="Europe/London")
    c = assemble(r, decennials_as_of=(2026, 6, 1))
    with open("decennials_demo.svg", "w", encoding="utf-8") as fh:
        fh.write(render_decennials_svg(c, theme="dark"))
    print("wrote decennials_demo.svg  |", c["decennials"]["current"])
