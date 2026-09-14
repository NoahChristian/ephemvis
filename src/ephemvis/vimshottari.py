#!/usr/bin/env python3
"""
vimshottari.py — the Vimśottarī daśā (Vedic time-lords) as a self-contained SVG.  [SHIP]

Vimśottarī is a nested temporal sequence of planetary chronocratorships, so — like
firdaria and the decennials — it renders as a horizontal **timeline** by default: a top
row of Mahādaśā periods and a bottom row of their Antardaśās, each segment colored and
glyphed by its ruling graha (the seven classical planets plus Rāhu / Ketu), the current
Mahā/Antar outlined with a marker at the current age. Pass ``style="chart"`` to project
it onto the annual-profection wheel instead (band = Mahā lord, glyph = Antar lord), and
``layout="spiral"`` for the expanding coil — the same shared natal core as every other
time-lord chart.

Input is the chart dict openephem's ``assemble()`` returns; it must carry a
``vimshottari`` block (openephem adds one when given ``vimshottari_as_of=``). Graha identity
is carried by the glyph (nine categories can't all be maximally distinct); color supports.
"""

from __future__ import annotations

from datetime import date as _date

from .profection_wheel import glyphs_by_year, render_profection_wheel_svg, theme_lord_colors
from .wheel import PALETTES

_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces")
# Western glyphs for the nine grahas; Rāhu / Ketu are the lunar nodes (north / south).
_GLYPH = {"Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
          "Jupiter": "♃", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"}
# the seven classical planets take theme-derived lord colors (shared with firdaria/decennials,
# same Chaldean order → a planet reads the same color across the suite); the two nodes keep
# fixed identity colors (matching the firdaria nodes).
_CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
_NODE_COLOR = {"Rahu": "#0e8d92", "Ketu": "#a9782f"}
_LEGEND = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
_SYM = "'Segoe UI Symbol','Noto Sans Symbols2','Apple Symbols',system-ui,sans-serif"
_UI = "system-ui,-apple-system,Segoe UI,Roboto,sans-serif"


def _lum(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ord(iso: str) -> int:
    return _date.fromisoformat(iso[:10]).toordinal()


def _antar_segments(vim: dict, max_age: float):
    """Every Antardaśā as (age_start, age_end, ruler) in fractional ages — the Antar ISO dates
    mapped onto each Mahādaśā's age span (Antardaśās are unequal)."""
    out = []
    for m in vim.get("timeline", []):
        ma0, ma1 = m["age_start"], m["age_end"]
        mo0, mo1 = _ord(m["start"]), _ord(m["end"])
        span = max(mo1 - mo0, 1)
        for a in m.get("subs", []):
            aa0 = ma0 + (ma1 - ma0) * (_ord(a["start"]) - mo0) / span
            aa1 = ma0 + (ma1 - ma0) * (_ord(a["end"]) - mo0) / span
            if aa0 < max_age:
                out.append((aa0, min(aa1, max_age), a["ruler"]))
    return out


def _maha_by_age(vim: dict, ages) -> list:
    tl = vim.get("timeline", [])
    out: list = []
    for a in ages:
        lord = None
        for m in tl:
            if m["age_start"] <= a < m["age_end"]:
                lord = m["ruler"]
                break
        out.append(lord)
    return out


def _dasha_path(vim: dict) -> str:
    cur = vim.get("current", {})
    return " › ".join(cur[k] for k in ("maha", "antar", "pratyantar") if cur.get(k))


def _chart_style(chart: dict, vim: dict, *, theme: str, size: int, title: str,
                 max_age: int, sub_style: str = "ticks", layout: str = "annulus") -> str:
    """Project the daśā onto the annual-profection wheel: band = Mahā lord, glyph = Antar lord,
    on the shared natal core."""
    if not chart.get("profections"):
        raise ValueError("the vimshottari chart style draws on the annual-profection wheel, so "
                         "the chart also needs a 'profections' block — assemble with both "
                         "vimshottari_as_of= and profection_as_of= (same date)")
    asc = (chart.get("angles") or {}).get("asc")
    asc_sign = _SIGNS[int(asc // 30) % 12] if asc is not None else ""
    nring = max_age // 12 + 1
    ages = range(nring * 12)
    major_by_age = _maha_by_age(vim, ages)
    sub_segments = _antar_segments(vim, nring * 12)
    glyph_by_age = glyphs_by_year(sub_segments, nring * 12)
    nak = vim.get("moon_nakshatra", {})
    subtitle = [f"{nak.get('name', '')} · {nak.get('lord', '')}" if nak else ""]
    if asc_sign:
        subtitle.append(f"{asc_sign} rising")
    if vim.get("age") is not None:
        subtitle.append(f"Age {vim['age']}")
    caption = ((f"Daśā: {_dasha_path(vim)}   " if _dasha_path(vim) else "")
               + "(band = mahā · glyph = antar)")
    return render_profection_wheel_svg(
        chart, theme=theme, size=size, max_age=max_age, layout=layout,
        timelord={"title": title, "subtitle_lines": [s for s in subtitle if s],
                  "lord_names": list(_LEGEND),
                  "lord_colors": {**theme_lord_colors(theme, _CHALDEAN), **_NODE_COLOR},
                  "glyph_map": _GLYPH, "major_by_age": major_by_age,
                  "glyph_by_age": glyph_by_age, "sub_segments": sub_segments,
                  "sub_style": sub_style, "footer_caption": caption})


def render_vimshottari_svg(chart: dict, *, theme: str = "light", max_age: float = 100.0,
                           width: int = 1160, title: str = "Vimśottarī Daśā",
                           style: str = "timeline", sub_style: str = "ticks",
                           size: int = 620, layout: str = "annulus") -> str:
    """Render the Vimśottarī daśā for ``chart`` as an SVG string.

    ``style`` is ``"timeline"`` (default; the horizontal Mahā/Antar bars) or ``"chart"`` (the
    daśā projected onto the natal whole-sign wheel; ``layout="spiral"`` for the coil). ``theme``
    is any key of :data:`ephemvis.PALETTES` ('auto' -> light). ``max_age`` is the timeline's
    right edge (years). Raises ``ValueError`` without a ``vimshottari`` block (or, for the chart
    style, without a ``profections`` block).
    """
    vim = chart.get("vimshottari")
    if not vim:
        raise ValueError("chart has no 'vimshottari' block (build it with openephem's "
                         "assemble(..., vimshottari_as_of=))")
    if style == "chart":
        return _chart_style(chart, vim, theme=theme, size=size, title=title,
                            max_age=int(round(max_age)), sub_style=sub_style, layout=layout)
    if style != "timeline":
        raise ValueError("style must be 'timeline' or 'chart'")

    pal = PALETTES.get("light" if theme == "auto" else theme, PALETTES["light"])
    ink, bg, muted, line = pal["planet"], pal["bg"][0], pal["deg"], pal["cusp"]
    col_map = {**theme_lord_colors(theme, _CHALDEAN), **_NODE_COLOR}
    cur_age = vim.get("age")
    mark_age = cur_age
    tl0 = vim.get("timeline") or []
    if vim.get("as_of") and tl0:
        try:
            mark_age = (_ord(vim["as_of"]) - _ord(tl0[0]["start"])) / 365.2425
        except ValueError:
            mark_age = cur_age

    # `width` is the DISPLAY width; the interior is drawn in a fixed W-wide design space and the
    # viewBox scales the whole thing to `width`, so proportions hold at any width.
    W = 1160
    padL, padR = 20, 20
    x0, x1 = padL, W - padR
    maha_y, maha_h = 70, 50
    antar_y, antar_h = maha_y + maha_h + 8, 30
    axis_y = antar_y + antar_h
    height = axis_y + 82

    def X(age):
        return x0 + (x1 - x0) * min(age, max_age) / max_age

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
         f'width="{width}" height="{width / W * height:g}" font-family="{_UI}" role="img" '
         f'aria-label="{_esc(title)}"><rect width="{W}" height="{height}" fill="{bg}"/>']
    P.append(f'<text x="{padL}" y="28" fill="{ink}" font-size="20" font-weight="700">{_esc(title)}</text>')

    nak = vim.get("moon_nakshatra", {})
    bal = vim.get("balance", {})
    sub = f"{nak.get('name', '')} ({nak.get('lord', '')})"
    if bal:
        sub += f" · balance {bal.get('years', '')}y"
    if cur_age is not None:
        sub += f" · age {cur_age}"
    if _dasha_path(vim):
        sub += f" · {_dasha_path(vim)}"
    P.append(f'<text x="{padL}" y="50" fill="{muted}" font-size="15.5">{_esc(sub)}</text>')

    step = 12
    a = 0
    while a <= max_age:
        gx = X(a)
        P.append(f'<line x1="{gx:.1f}" y1="{maha_y}" x2="{gx:.1f}" y2="{axis_y}" '
                 f'stroke="{line}" stroke-width="1"/>')
        P.append(f'<text x="{gx:.1f}" y="{axis_y + 17}" fill="{muted}" font-size="13" '
                 f'text-anchor="middle">{a}</text>')
        a += step
    P.append(f'<text x="{(x0+x1)/2:.0f}" y="{axis_y + 34}" fill="{muted}" font-size="13" '
             f'text-anchor="middle" letter-spacing="1">AGE</text>')

    current_rects = []
    def band(y, bh, ruler, a0, a1, glyph_fs, current=False):
        xa, xb = X(a0), X(a1)
        if a0 >= max_age or xb - xa < 0.6:
            return
        col = col_map.get(ruler, muted)
        P.append(f'<rect x="{xa:.1f}" y="{y}" width="{xb-xa:.1f}" height="{bh}" fill="{col}" '
                 f'stroke="{bg}" stroke-width="1.5" rx="3"/>')
        if current:
            current_rects.append((xa, y, xb - xa, bh))
        if xb - xa > 16:
            tc = "#141414" if _lum(col) > 140 else "#ffffff"
            P.append(f'<text x="{(xa+xb)/2:.1f}" y="{y + bh/2:.1f}" fill="{tc}" font-family="{_SYM}" '
                     f'font-size="{glyph_fs}" text-anchor="middle" dominant-baseline="central">'
                     f'{_esc(_GLYPH.get(ruler, ruler[:2]))}︎</text>')

    for m in vim["timeline"]:
        ma0, ma1 = m["age_start"], m["age_end"]
        band(maha_y, maha_h, m["ruler"], ma0, ma1, 19,
             current=mark_age is not None and ma0 <= mark_age < ma1)
    for aa0, aa1, ruler in _antar_segments(vim, max_age):
        band(antar_y, antar_h, ruler, aa0, aa1, 13,
             current=mark_age is not None and aa0 <= mark_age < aa1)

    for xa, y, w, bh in current_rects:      # current outlines on top, so nothing clips them
        P.append(f'<rect x="{xa+1:.1f}" y="{y+1}" width="{w-2:.1f}" height="{bh-2}" '
                 f'fill="none" stroke="{ink}" stroke-width="2.4" rx="2"/>')

    if mark_age is not None:
        cx = X(mark_age)
        P.append(f'<line x1="{cx:.1f}" y1="{maha_y-8}" x2="{cx:.1f}" y2="{axis_y+3}" '
                 f'stroke="{ink}" stroke-width="2"/>')
        P.append(f'<circle cx="{cx:.1f}" cy="{maha_y-8}" r="4" fill="{ink}"/>')
        if vim.get("as_of"):
            asof = _date.fromisoformat(vim["as_of"][:10])
            months = ("January", "February", "March", "April", "May", "June", "July",
                      "August", "September", "October", "November", "December")
            label = f"{months[asof.month-1]} {asof.day}, {asof.year}"
            P.append(f'<text x="{cx+8:.1f}" y="{maha_y-14:.0f}" fill="{ink}" font-family="{_UI}" '
                     f'font-size="13" font-weight="600">{label}</text>')

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
    c = assemble(r, vimshottari_as_of=(2040, 6, 1), profection_as_of=(2040, 6, 1))
    with open("vimshottari_demo.svg", "w", encoding="utf-8") as fh:
        fh.write(render_vimshottari_svg(c, theme="dark"))
    print("wrote vimshottari_demo.svg  |", c["vimshottari"]["current"])
