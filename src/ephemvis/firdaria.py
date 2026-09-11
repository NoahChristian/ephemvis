#!/usr/bin/env python3
"""
firdaria.py — the firdaria (Persian time-lord) timeline as a self-contained SVG.  [SHIP]

Firdaria is a temporal sequence, not a zodiac wheel, so it renders as a horizontal
timeline: a top row of major planetary periods and a bottom row of their sub-periods,
each segment coloured by its ruling planet, with a marker at the current age. Input is
the chart dict openephem's ``assemble()`` returns; it must carry a ``firdaria`` block
(openephem adds one when given ``firdaria_as_of=``). The table companion is trivially
built from the same block.

Planet identity is carried by the glyph on each segment (and the legend); colour is a
supporting cue — nine categories can't all be maximally distinct, so the glyph is the
primary identifier (which also covers colour-vision-deficient and print cases).
"""

from __future__ import annotations

from datetime import date as _date

from .profection_wheel import theme_lord_colors
from .wheel import PALETTES

_GLYPH = {"Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
          "Jupiter": "♃", "Saturn": "♄", "North Node": "☊", "South Node": "☋"}
# The seven classical planets take theme-derived lord colours — the same `theme_lord_colors`
# the decennials timeline/chart use, in the same Chaldean order, so a planet reads the SAME
# colour across every renderer and the whole suite recolours together per theme. The two nodes
# keep fixed identity colours (they are not lords on the ramp). Glyph labels carry identity
# regardless — nine categories can't all be maximally distinct (checked with the dataviz validator).
_CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
_NODE_COLOR = {"North Node": "#0e8d92", "South Node": "#a9782f"}
_LEGEND = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
           "North Node", "South Node"]
_SYM = "'Segoe UI Symbol','Noto Sans Symbols2','Apple Symbols',system-ui,sans-serif"
_UI = "system-ui,-apple-system,Segoe UI,Roboto,sans-serif"


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _lum(h):
    a = _rgb(h)
    return 0.299 * a[0] + 0.587 * a[1] + 0.114 * a[2]


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ord(iso: str) -> int:
    return _date.fromisoformat(iso[:10]).toordinal()


def render_firdaria_svg(chart: dict, *, theme: str = "light", max_age: float = 84.0,
                        width: int = 1160, title: str = "Firdaria") -> str:
    """Render the firdaria timeline for ``chart`` as an SVG string.

    ``theme`` is any key of :data:`ephemvis.PALETTES` ('auto' -> light). ``max_age`` is
    the right edge of the timeline (years). Raises ``ValueError`` without a ``firdaria``
    block.
    """
    fd = chart.get("firdaria")
    if not fd:
        raise ValueError("chart has no 'firdaria' block (build it with openephem's "
                         "assemble(..., firdaria_as_of=))")
    pal = PALETTES.get("light" if theme == "auto" else theme, PALETTES["light"])
    ink, bg, muted, line = pal["planet"], pal["bg"][0], pal["deg"], pal["cusp"]
    col_map = {**theme_lord_colors(theme, _CHALDEAN), **_NODE_COLOR}   # per-theme lord colours
    cur_age = fd.get("age")                           # whole years, for the subtitle text
    # the marker / current outline track the actual as-of date (a fractional age)
    mark_age = cur_age
    tl0 = fd.get("timeline") or []
    if fd.get("as_of") and tl0:
        try:
            mark_age = (_ord(fd["as_of"]) - _ord(tl0[0]["start"])) / 365.2425
        except ValueError:                            # timeline lacks real dates → integer age
            mark_age = cur_age

    # `width` is the DISPLAY width; interior coordinates + hardcoded fonts/strokes/heights are
    # drawn in a fixed W-wide design space and the viewBox scales the whole thing to `width`, so
    # the timeline keeps its proportions at any width (the fonts used to bloat at a narrow one).
    W = 1160
    padL, padR = 20, 20
    x0, x1 = padL, W - padR
    major_y, major_h = 62, 48
    sub_y, sub_h = major_y + major_h + 7, 28
    axis_y = sub_y + sub_h
    height = axis_y + 82          # room for the AGE row + a clear line before the legend

    def X(age):
        return x0 + (x1 - x0) * min(age, max_age) / max_age

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
         f'width="{width}" height="{width / W * height:g}" font-family="{_UI}" role="img" '
         f'aria-label="{_esc(title)}"><rect width="{W}" height="{height}" fill="{bg}"/>']
    P.append(f'<text x="{padL}" y="28" fill="{ink}" font-size="20" font-weight="700">{_esc(title)}</text>')
    cur = fd.get("current", {})
    sub_txt = f' / {cur.get("sub", "")}' if cur.get("sub") else ""
    P.append(f'<text x="{padL}" y="50" fill="{muted}" font-size="15.5">{fd.get("sect", "").title()} '
             f'chart · age {cur_age} · {cur.get("major", "")}{sub_txt}</text>')

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

    def band(y, bh, ruler, a0, a1, glyph_fs, current=False):
        xa, xb = X(a0), X(a1)
        if a0 >= max_age or xb - xa < 0.6:
            return
        col = col_map.get(ruler, muted)
        P.append(f'<rect x="{xa:.1f}" y="{y}" width="{xb-xa:.1f}" height="{bh}" fill="{col}" '
                 f'stroke="{bg}" stroke-width="1.5" rx="3"/>')
        if current:
            P.append(f'<rect x="{xa+1:.1f}" y="{y+1}" width="{xb-xa-2:.1f}" height="{bh-2}" '
                     f'fill="none" stroke="{ink}" stroke-width="2.4" rx="2"/>')
        if xb - xa > 18:
            tc = "#141414" if _lum(col) > 140 else "#ffffff"
            P.append(f'<text x="{(xa+xb)/2:.1f}" y="{y + bh/2:.1f}" fill="{tc}" font-family="{_SYM}" '
                     f'font-size="{glyph_fs}" text-anchor="middle" dominant-baseline="central">'
                     f'{_esc(_GLYPH.get(ruler, ruler[:2]))}︎</text>')

    for b in fd["timeline"]:
        a0, a1 = b["age_start"], b["age_end"]
        maj_cur = mark_age is not None and a0 <= mark_age < a1
        band(major_y, major_h, b["ruler"], a0, a1, 18, current=maj_cur)
        subs = b.get("subs", [])
        for i, s in enumerate(subs):
            sa0 = a0 + (a1 - a0) * i / len(subs)
            sa1 = a0 + (a1 - a0) * (i + 1) / len(subs)
            band(sub_y, sub_h, s["ruler"], sa0, sa1, 13,
                 current=mark_age is not None and sa0 <= mark_age < sa1)

    # current-age marker + the as-of date, set up and to the right of the dot
    if mark_age is not None:
        cx = X(mark_age)
        P.append(f'<line x1="{cx:.1f}" y1="{major_y-8}" x2="{cx:.1f}" y2="{axis_y+3}" '
                 f'stroke="{ink}" stroke-width="2"/>')
        P.append(f'<circle cx="{cx:.1f}" cy="{major_y-8}" r="4" fill="{ink}"/>')
        if fd.get("as_of"):
            asof = _date.fromisoformat(fd["as_of"][:10])
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
        P.append(f'<rect x="{lx:.1f}" y="{ly-11}" width="14" height="14" rx="2" fill="{col_map[r]}"/>')
        P.append(f'<text x="{lx+19:.1f}" y="{ly}" fill="{muted}" font-size="13.5">{_esc(r)}{gtag}</text>')
        lx += 52 + len(r) * 7.6
    P.append("</svg>")
    return "\n".join(P)


if __name__ == "__main__":
    from openephem import assemble, resolve
    r = resolve(date=(2000, 1, 1), time=(12, 0), lat=51.4779, lon=-0.0015, tz="Europe/London")
    c = assemble(r, firdaria_as_of=(2026, 6, 1))
    with open("firdaria_demo.svg", "w", encoding="utf-8") as fh:
        fh.write(render_firdaria_svg(c, theme="dark"))
    print("wrote firdaria_demo.svg  |", c["firdaria"]["current"])
