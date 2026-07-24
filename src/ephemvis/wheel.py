#!/usr/bin/env python3
"""
wheel.py — render a natal chart as a self-contained SVG wheel.  [SHIP]

Pure Python, zero dependencies. Takes the dict from chart.assemble() (or any dict
with the same shape) and returns an SVG string. Ascendant is placed at the left
(9 o'clock) with the zodiac increasing counter-clockwise — the standard chart
convention. Theme-aware (light/dark) via a CSS block.

Glyphs are standard Unicode astrological symbols (no font-licensing issue); if a
viewer's font lacks them, pass text_labels=True for 2-3 letter abbreviations.
"""

from __future__ import annotations

import math

SIGN_GLYPHS = ["♈", "♉", "♊", "♋", "♌", "♍",
               "♎", "♏", "♐", "♑", "♒", "♓"]
SIGN_ABBR = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]

PLANET_GLYPHS = {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀",
    "Mars": "♂", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅",
    "Neptune": "♆", "Pluto": "♇", "TrueNode": "☊", "MeanNode": "☊", "SouthNode": "☋",
    "MeanLilith": "⚸", "OscuLilith": "⚸", "Chiron": "⚷",
    "Ceres": "⚳", "Pallas": "⚴", "Juno": "⚵", "Vesta": "⚶",
    "Eros": "♡", "Eris": "⯰", "AsteroidLilith": "☾",   # no standard Unicode glyphs
    "Hygeia": "⚕", "Astraea": "As", "Sedna": "⯲",
    "PartOfFortune": "⊗", "Vertex": "Vx", "EastPoint": "Ep",
    "Descendant": "Dc", "ImumCoeli": "Ic", "AriesPoint": "♈", "LibraPoint": "♎",
    "CoAscendant": "Co",
    # Uranian / hypothetical bodies — no standard Unicode glyphs, so 2-letter marks
    "Cupido": "Cu", "Hades": "Ha", "Zeus": "Ze", "Kronos": "Kr", "Apollon": "Ap",
    "Admetos": "Ad", "Vulcanus": "Vl", "Poseidon": "Po", "TransPluto": "TP",
    "Vulcan": "Vu", "WhiteMoon": "Se",   # Weston's Vulcan; Selena / White Moon
}
PLANET_ABBR = {k: (k[:2] if k not in ("Sun", "Moon") else k[:2]) for k in PLANET_GLYPHS}

_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces")
_NICE_NAMES = {"TrueNode": "North Node", "MeanNode": "North Node", "SouthNode": "South Node",
               "MeanLilith": "Black Moon Lilith", "OscuLilith": "Black Moon Lilith",
               "AsteroidLilith": "Asteroid Lilith", "PartOfFortune": "Part of Fortune",
               "EastPoint": "East Point", "ImumCoeli": "Imum Coeli", "CoAscendant": "Co-Ascendant",
               "AriesPoint": "Aries Point", "LibraPoint": "Libra Point",
               "WhiteMoon": "White Moon (Selena)", "TransPluto": "Trans-Pluto"}


def body_label(name, body):
    """Hover text for a body: 'Moon in Pisces at 5.00°' (+ ' ℞' when retrograde)."""
    lon = float(body.get("lon", 0.0)) % 360.0
    sign = body.get("sign") or _SIGNS[int(lon // 30) % 12]
    deg = body.get("deg_in_sign")
    if deg is None:
        deg = lon % 30.0
    s = "%s in %s at %.2f°" % (_NICE_NAMES.get(name, name), sign, float(deg))
    return s + " ℞" if body.get("retro") else s


_ORDINALS = ("1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th",
             "9th", "10th", "11th", "12th")


def _house_of_lon(lon, cusps):
    for i in range(12):
        span = (cusps[(i + 1) % 12] - cusps[i]) % 360.0
        if span == 0.0 or (lon - cusps[i]) % 360.0 < span:
            return i + 1
    return 12


def sign_label(i, angles, cusps):
    """Hover text for a zodiac sign: 'Virgo · 2nd house' (+ ' (Rising)' on the Asc sign)."""
    name = _SIGNS[i % 12]
    asc = (angles or {}).get("asc")
    rising = asc is not None and int(asc // 30) % 12 == i % 12
    if cusps and len(cusps) >= 12:
        s = "%s · %s house" % (name, _ORDINALS[_house_of_lon(i * 30.0 + 15.0, cusps) - 1])
    else:
        s = name
    return s + " (Rising)" if rising else s


def angle_label(key, lon):
    """Hover text for the Asc/MC: 'Leo Ascendant at 12.34°'."""
    lon %= 360.0
    nm = {"asc": "Ascendant", "mc": "Midheaven"}.get(key, key)
    return "%s %s at %.2f°" % (_SIGNS[int(lon // 30) % 12], nm, lon % 30.0)

# Aspect line styling (color, dash). Class names keyed for the CSS block.
ASPECT_STYLE = {
    "conjunction": ("#8a8a8a", ""),
    "opposition": ("#d7263d", ""),
    "square": ("#d7263d", ""),
    "trine": ("#1f7a8c", ""),
    "sextile": ("#1f7a8c", "4 3"),
    "quincunx": ("#3f8f3f", "2 3"),
    "semisextile": ("#3f8f3f", "2 3"),
    "semisquare": ("#c08a2e", "2 3"),
    "sesquiquadrate": ("#c08a2e", "2 3"),
    "quintile": ("#7a4fb0", "2 3"),
}

# Which aspects read as hard / soft / neutral (for per-theme aspect colouring).
ASPECT_CAT = {
    "conjunction": "neutral",
    "opposition": "hard", "square": "hard",
    "semisquare": "hard", "sesquiquadrate": "hard",
    "trine": "soft", "sextile": "soft",
    "quincunx": "soft", "semisextile": "soft", "quintile": "soft",
}

# ---- colour palettes -> selectable "modes" ---------------------------------
# Each palette: bg (radial gradient in/out), ring (3 linear-gradient stops), then
# per-element colours. light/dark are functional; the rest are pastel "pretty"
# modes with a prism-like ring sweep. All are valid `theme=` values.
_L = dict(bg=("#ffffff", "#ffffff"), ring=("#b0b0b0", "#b0b0b0", "#b0b0b0"),
          tick="#b0b0b0", sign="#3a3a3a", cusp="#7f9fd4", cuspA="#3f5f9c",
          hdiv="#a3aab8", leader="#c3c7cf", housenum="#3a3a3a", anglelab="#1c1c1c",
          pmark="#b6b6b6", planet="#111111", deg="#5f5f5f", degRx="#c0392b",
          title="#222222", aHard="#d7263d", aSoft="#1f7a8c", aNeutral="#8a8a8a", halo=False)
_D = dict(bg=("#14161a", "#0f1114"), ring=("#3a3f47", "#3a3f47", "#3a3f47"),
          tick="#3a3f47", sign="#c9cdd4", cusp="#6a84ad", cuspA="#a6c1ec",
          hdiv="#5b6474", leader="#4c525e", housenum="#7a828c", anglelab="#d5d9df",
          pmark="#454b54", planet="#f2f4f7", deg="#9aa1ab", degRx="#ff6f6f",
          title="#e6e9ee", aHard="#e06c78", aSoft="#5fb0c0", aNeutral="#7a828c", halo=False)


def _pretty(bg, bg2, ring, ink, mid, line, lineA, accent, hard, soft):
    return dict(bg=(bg, bg2), ring=ring, tick=line, sign=ink, cusp=line, cuspA=lineA,
                hdiv=mid, leader=line, housenum=ink, anglelab=accent, pmark=mid,
                planet=ink, deg=mid, degRx=hard, title=ink,
                aHard=hard, aSoft=soft, aNeutral=mid, halo=True)


def _lerp_hex(c1, c2, t):
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))


def _conic(p, stops):
    """Colour at fraction p in [0,1) sweeping the three ring stops around a loop."""
    seg = (p % 1.0) * 3.0
    i = int(seg) % 3
    return _lerp_hex(stops[i], stops[(i + 1) % 3], seg - int(seg))


# Rotation applied to the halo sweep so the brightest/warmest ring stop (stops[2],
# naturally at screen 240° = ~7 o'clock) lands at the TOP of the wheel (screen 90°).
# colour = _conic(mid/360 + _HALO_TURN); stops[2] shows where the arg == 2/3, so
# 90/360 + _HALO_TURN == 2/3  ->  _HALO_TURN = 2/3 - 1/4 = 150/360.
_HALO_TURN = 150.0 / 360.0

# Per-theme perceptual nudge of the halo nexus, in degrees CCW from the top (the
# nexus screen angle = 240 - 360*turn, and CCW = increasing screen angle, so the
# effective turn is (_HALO_TURN - deg/360)). Tuned by eye per palette; 0 = at top.
_HALO_ROT_DEG = {
    "twilight": 30, "aurora": 30, "opal": 30, "seafoam": 30,
    "meadow": 45, "dawn": 90, "blossom": 60, "infrared": 30,
    # prism, ultraviolet (and the halo-less light/dark): 0
}


PALETTES = {
    "light": _L, "dark": _D,
    "aurora": _pretty("#f4f7fd", "#e8eef8", ("#8fb3e6", "#b9c9ee", "#d9b8e6"),
                      "#2a3550", "#5f6a86", "#a9bfe4", "#5f79b8", "#bf8f4a", "#cf7a8a", "#5f96b0"),
    "seafoam": _pretty("#eef8f4", "#ddf0ea", ("#6fc2c9", "#a5dcd2", "#cfe6b0"),
                       "#22403c", "#567a74", "#9fd0cb", "#4f9a92", "#a98a45", "#d07a6e", "#3f9a90"),
    "twilight": _pretty("#f2eef8", "#e6e0f0", ("#6a7fd0", "#9a8fd8", "#d29ac0"),
                        "#2e2846", "#6a6484", "#b3a6dd", "#6a5fb0", "#b98a4e", "#cf6a8a", "#6a7fc8"),
    "dawn": _pretty("#fcf5ee", "#f7e9dc", ("#8fbce6", "#f0c69a", "#f0a48f"),
                    "#40342a", "#7a6a58", "#e3c3a3", "#c98f6f", "#bf7f3a", "#d0705a", "#5f96b8"),
    "prism": _pretty("#f4f7fb", "#e8f0f8", ("#6aa0e0", "#7fd0c0", "#e8d98f"),
                     "#263242", "#5f6f80", "#a7c4e6", "#4f86c8", "#b98a3e", "#cf6f6a", "#3f9aa0"),
    "opal": _pretty("#f6f5fb", "#edeef6", ("#a9c4ea", "#cdc2ec", "#ecd6b0"),
                    "#33324a", "#6a6a82", "#bfcbe8", "#7a86bf", "#b28a4a", "#cf7a90", "#6f96b8"),
    "meadow": _pretty("#f2f7ee", "#e7f0de", ("#7fb0d8", "#a8cfa8", "#d8d68f"),
                      "#2c3a2a", "#5f6f56", "#aecbb0", "#6a9a72", "#a98a40", "#d0705a", "#4f9a86"),
    "blossom": _pretty("#fbf3f6", "#f6e7ee", ("#8fb3e6", "#dab0d8", "#f0aab8"),
                       "#402a38", "#7a5f6e", "#e0bcd2", "#b06a92", "#bf7f5a", "#d06a86", "#6f96b8"),
    # spectral "beyond visible" pair — dark grounds with a thermal / black-light glow
    "infrared": _pretty("#1a0a0a", "#0d0404", ("#7a0d0d", "#e0431f", "#f2b705"),
                        "#f6e3d8", "#a06a52", "#5a2f28", "#ff7a3c", "#ff5a2e", "#ff3b2f", "#ffd25e"),
    "ultraviolet": _pretty("#120a24", "#080413", ("#7a3cff", "#b03cff", "#3c9cff"),
                           "#ece4ff", "#7a68b0", "#3a2a5e", "#a06cff", "#b57bff", "#ff5ad0", "#6ab8ff"),
}


def _defs(pal):
    b0, b1 = pal["bg"]
    r0, r1, r2 = pal["ring"]
    return ('<defs>'
            '<radialGradient id="bggrad" cx="50%" cy="40%" r="82%">'
            '<stop id="bs0" offset="0%" stop-color="' + b0 + '"/>'
            '<stop id="bs1" offset="100%" stop-color="' + b1 + '"/>'
            '</radialGradient>'
            '<linearGradient id="ringgrad" x1="0.05" y1="0.05" x2="0.95" y2="0.95">'
            '<stop id="rs0" offset="0%" stop-color="' + r0 + '"/>'
            '<stop id="rs1" offset="50%" stop-color="' + r1 + '"/>'
            '<stop id="rs2" offset="100%" stop-color="' + r2 + '"/>'
            '</linearGradient></defs>')


def _style(pal):
    sym = '"Segoe UI Symbol","Noto Sans Symbols2","Apple Symbols",system-ui,sans-serif'
    rules = [
        (".ring", "fill:none;stroke:url(#ringgrad);stroke-width:3.4"),
        (".tick", "stroke:%s;stroke-width:3.4" % pal["tick"]),
        (".sign", "fill:%s;font:600 28px %s" % (pal["sign"], sym)),
        (".cusp", "stroke:%s;stroke-width:2" % pal["cusp"]),
        (".cusp-angle", "stroke:%s;stroke-width:2.4" % pal["cuspA"]),
        (".hdiv", "stroke:%s;stroke-width:1.3" % pal["hdiv"]),
        (".leader", "stroke:%s;stroke-width:2;stroke-dasharray:1 5;stroke-linecap:round" % pal["leader"]),
        (".housenum", "fill:%s;font:600 19px system-ui,sans-serif" % pal["housenum"]),
        (".anglelab", "fill:%s;font:800 28px system-ui,sans-serif" % pal["anglelab"]),
        (".ac-sm", "font-size:0.5em"),
        (".pmark", "stroke:%s;stroke-width:1.6" % pal["pmark"]),
        (".planet", "fill:%s;font:600 33px %s" % (pal["planet"], sym)),
        (".deg", "fill:%s;font:600 18px system-ui,sans-serif" % pal["deg"]),
        (".deg-rx", "fill:%s" % pal["degRx"]),
        (".aspect", "stroke-width:1.1;fill:none;opacity:.85"),
        (".title", "fill:%s;font:600 15px system-ui,sans-serif" % pal["title"]),
    ]
    return "<style>" + "".join("%s{%s}" % (s, p) for s, p in rules) + "</style>"


def _dark_media():
    d = _D
    return ('<style>@media (prefers-color-scheme: dark){'
            '#bs0{stop-color:' + d["bg"][0] + '}#bs1{stop-color:' + d["bg"][1] + '}'
            '#rs0,#rs1,#rs2{stop-color:' + d["ring"][0] + '}'
            '.tick{stroke:' + d["tick"] + '}.sign{fill:' + d["sign"] + '}'
            '.cusp{stroke:' + d["cusp"] + '}.cusp-angle{stroke:' + d["cuspA"] + '}'
            '.hdiv{stroke:' + d["hdiv"] + '}.leader{stroke:' + d["leader"] + '}'
            '.housenum{fill:' + d["housenum"] + '}.anglelab{fill:' + d["anglelab"] + '}'
            '.pmark{stroke:' + d["pmark"] + '}.planet{fill:' + d["planet"] + '}'
            '.deg{fill:' + d["deg"] + '}.deg-rx{fill:' + d["degRx"] + '}'
            '.title{fill:' + d["title"] + '}}</style>')


def _theme_markup(theme):
    """Return the <defs> gradients + <style> for a theme (auto = light + dark media)."""
    if theme == "auto":
        return _defs(_L) + _style(_L) + _dark_media()
    pal = PALETTES.get(theme, _L)
    return _defs(pal) + _style(pal)


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_svg(chart: dict, size: int = 760, theme: str = "auto",
               text_labels: bool = False, title: str | None = None) -> str:
    cx = cy = size / 2.0
    r_out = size * 0.45              # outer edge (leaves a margin for AC/MC outside)
    r_zod_in = r_out * 0.862         # inner edge of the zodiac band (signs live here)
    r_house = r_zod_in               # house-cusp lines reach the zodiac inner edge
    r_tick_in = r_zod_in * 0.905     # inner end of the planet pointer ticks
    r_glyph = r_zod_in * 0.845       # planet-glyph ring (pushed out for more room)
    r_hnum_out = r_zod_in * 0.43     # house-ring outer = former aspect-circle radius
    r_hub = r_zod_in * 0.33          # aspect circle == house-ring inner edge (they meet)
    r_hnum = r_zod_in * 0.38         # house numbers, centred in the (wider) ring band
    glyphs = None if not text_labels else True
    apal = _L if theme == "auto" else PALETTES.get(theme, _L)  # aspect colours

    angles = chart.get("angles") or {}
    asc = angles.get("asc", 0.0)     # unknown-time -> 0 Aries at left
    cusps = chart.get("cusps")

    def pol(r, lon):
        """Ecliptic longitude -> (x, y). Asc at left, zodiac CCW."""
        a = math.radians(180.0 + (lon - asc))
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def sp(r, deg):
        """Screen-space polar (independent of the chart's rotation) for halo bands."""
        a = math.radians(deg)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    P = []  # svg fragments
    P.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
             f'width="{size}" height="{size}" style="cursor:default" role="img" '
             f'aria-label="{_esc(title or "natal chart")}">')
    P.append(_theme_markup(theme))
    P.append(f'<rect x="0" y="0" width="{size}" height="{size}" class="bg" fill="url(#bggrad)"/>')

    # --- rings / prism-halo bands ---
    if apal.get("halo"):
        # fill the zodiac band and the house-number band with an angular sweep of
        # the ring stops (a true "halo" around the wheel), then outline the edges.
        stops = apal["ring"]
        turn = _HALO_TURN - _HALO_ROT_DEG.get(theme, 0) / 360.0   # per-theme CCW nudge
        N = 120
        for rin, rout in ((r_zod_in, r_out), (r_hub, r_hnum_out)):
            for sgi in range(N):
                a0, a1 = 360.0 * sgi / N, 360.0 * (sgi + 1) / N
                col = _conic((a0 + a1) / 720.0 + turn, stops)
                x1, y1 = sp(rout, a0)
                x2, y2 = sp(rout, a1)
                x3, y3 = sp(rin, a1)
                x4, y4 = sp(rin, a0)
                P.append(f'<polygon points="{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} '
                         f'{x3:.1f},{y3:.1f} {x4:.1f},{y4:.1f}" fill="{col}"/>')
        for r in (r_out, r_zod_in, r_hnum_out, r_hub):
            P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                     f'fill="none" stroke="rgba(38,44,60,.28)" stroke-width="1.4"/>')
    else:
        for r in (r_out, r_zod_in, r_hnum_out, r_hub):
            P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="ring"/>')

    # --- zodiac: 12 sectors (fixed to longitude) ---
    for i in range(12):
        lon0 = i * 30.0
        x1, y1 = pol(r_zod_in, lon0)
        x2, y2 = pol(r_out, lon0)
        P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="tick"/>')
        gx, gy = pol((r_zod_in + r_out) / 2.0, lon0 + 15.0)
        label = SIGN_ABBR[i] if glyphs else SIGN_GLYPHS[i] + "︎"  # text, not emoji
        P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="sign" '
                 f'dominant-baseline="central" text-anchor="middle">'
                 f'<title>{_esc(sign_label(i, angles, cusps))}</title>{label}</text>')

    # --- houses (cusp lines here; numbers collected and drawn last, on top) ---
    house_labels = []
    if cusps and len(cusps) >= 12:
        # emphasise the four angle cusps only when they ARE the angles (quadrant
        # systems like Placidus); in whole-sign/equal the cusps are sign boundaries,
        # so every division stays uniform.
        _asc, _mc = angles.get("asc"), angles.get("mc")
        quad = (_asc is not None and _mc is not None
                and abs((cusps[0] - _asc + 180.0) % 360.0 - 180.0) < 0.5
                and abs((cusps[9] - _mc + 180.0) % 360.0 - 180.0) < 0.5)
        for i, c in enumerate(cusps):
            cls = "cusp-angle" if (quad and i in (0, 3, 6, 9)) else "cusp"
            # solid divider between house numbers, within the number ring
            hx1, hy1 = pol(r_hub, c)
            hx2, hy2 = pol(r_hnum_out, c)
            P.append(f'<line x1="{hx1:.1f}" y1="{hy1:.1f}" x2="{hx2:.1f}" y2="{hy2:.1f}" class="hdiv"/>')
            # dotted cusp continues from the number ring out to the zodiac
            dx1, dy1 = pol(r_hnum_out, c)
            dx2, dy2 = pol(r_house, c)
            P.append(f'<line x1="{dx1:.1f}" y1="{dy1:.1f}" x2="{dx2:.1f}" y2="{dy2:.1f}" class="{cls}"/>')
            mid = c + (((cusps[(i + 1) % 12] - c) % 360.0) / 2.0)
            nx, ny = pol(r_hnum, mid)
            house_labels.append(f'<text x="{nx:.1f}" y="{ny:.1f}" class="housenum" '
                                f'dominant-baseline="central" text-anchor="middle">{i + 1}</text>')
        # Asc / MC labels, OUTSIDE the ring (so the halo bands don't clobber them);
        # the trailing "C" is half-height, baseline-aligned (not descending).
        r_ang = r_out + size * 0.03
        for key, first in (("asc", "A"), ("mc", "M")):
            if key in angles:
                lx, ly = pol(r_ang, angles[key])
                P.append(f'<text x="{lx:.1f}" y="{ly + size*0.008:.1f}" class="anglelab" '
                         f'text-anchor="middle"><title>{_esc(angle_label(key, angles[key]))}</title>'
                         f'{first}<tspan class="ac-sm">C</tspan></text>')

    # --- planets (with simple angular de-collision on the display ring) ---
    bodies = chart.get("bodies") or {}
    # Combined de-collision: a gentle angular (circumferential) spread PLUS radial
    # tiers where bodies pile up. Glyphs stay near their true longitude; a dotted
    # leader ties any displaced glyph back to its true mark, so nothing is lost.
    ANG = 6.0                        # angular min-gap (deg) — gentle circumferential fan
    RAD_TH = 12.0                    # within this angular gap, stack radially instead
    STEP = r_zod_in * 0.173          # radial gap between tiers
    DOFF = r_zod_in * 0.086          # degree label offset below its glyph
    placed = _spread([(n, bodies[n]["lon"]) for n in bodies], min_gap=ANG)
    order = sorted(range(len(placed)), key=lambda k: placed[k][2])
    last: list[float] = []
    tier = [0] * len(placed)
    for k in order:
        d = placed[k][2]
        t = 0
        while t < len(last) and (d - last[t]) % 360.0 < RAD_TH:
            t += 1
        if t == len(last):
            last.append(d)
        else:
            last[t] = d
        tier[k] = t
    hub_pts = {}
    for k, (name, lon, disp) in enumerate(placed):
        rg = r_glyph - tier[k] * STEP
        # true-position mark: a short spoke just inside the zodiac
        tx1, ty1 = pol(r_tick_in, lon)
        tx2, ty2 = pol(r_house, lon)
        P.append(f'<line x1="{tx1:.1f}" y1="{ty1:.1f}" x2="{tx2:.1f}" y2="{ty2:.1f}" class="pmark"/>')
        # displaced glyph: dotted leader back to its true mark (keeps the link)
        drift = abs((disp - lon + 180.0) % 360.0 - 180.0)
        if tier[k] > 0 or drift > 2.5:
            gx0, gy0 = pol(rg + r_zod_in * 0.045, disp)
            P.append(f'<line x1="{gx0:.1f}" y1="{gy0:.1f}" x2="{tx1:.1f}" y2="{ty1:.1f}" class="leader"/>')
        gx, gy = pol(rg, disp)
        if glyphs:
            g = PLANET_ABBR.get(name, name[:2])
        else:  # fixed stars share one ✦ marker; the name identifies them in the key
            base = PLANET_GLYPHS.get(name) or ("✦" if bodies[name].get("kind") == "star" else name[:2])
            g = base + "︎"  # text, not emoji
        retro = bodies[name].get("retro")
        lbl = _esc(body_label(name, bodies[name]))          # hover: name in sign at deg
        P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="planet" '
                 f'dominant-baseline="central" text-anchor="middle">'
                 f'<title>{lbl}</title>{_esc(g)}</text>')
        dxp, dyp = pol(rg - DOFF, disp)
        deg = f'{int(lon % 30)}°' + ("℞" if retro else "")
        dcls = "deg deg-rx" if retro else "deg"
        P.append(f'<text x="{dxp:.1f}" y="{dyp:.1f}" class="{dcls}" '
                 f'dominant-baseline="central" text-anchor="middle">'
                 f'<title>{lbl}</title>{deg}</text>')
        hub_pts[name] = pol(r_hub, lon)

    # --- aspects (lines across the hub) ---
    for asp in chart.get("aspects") or []:
        a, b = asp.get("a"), asp.get("b")
        if a in hub_pts and b in hub_pts:
            cat = ASPECT_CAT.get(asp.get("aspect"), "soft")
            color = apal["a" + cat.capitalize()]
            _, dash = ASPECT_STYLE.get(asp.get("aspect"), ("", "2 3"))
            (x1, y1), (x2, y2) = hub_pts[a], hub_pts[b]
            da = f' stroke-dasharray="{dash}"' if dash else ""
            P.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{color}" class="aspect"{da}/>')

    # house numbers last, so they sit in front of the cusp lines and ticks
    P.extend(house_labels)

    if title:
        P.append(f'<text x="{cx:.1f}" y="{size*0.04:.1f}" class="title" '
                 f'text-anchor="middle">{_esc(title)}</text>')
    P.append('</svg>')
    return "\n".join(P)


def _spread(items, min_gap=7.0):
    """De-collide glyph display angles while preserving zodiacal order. Cut the
    circle at its widest gap so a cluster can open into free space, enforce the
    minimum gap in one forward sweep (no crossovers), then recentre on the true
    centroid to keep drift minimal and symmetric. Returns (name, true_lon, disp)."""
    items = sorted(items, key=lambda t: t[1])
    n = len(items)
    if n < 2:
        return [(nm, lo, lo) for nm, lo in items]
    lons = [lo for _, lo in items]
    gaps = [(lons[(i + 1) % n] - lons[i]) % 360.0 for i in range(n)]
    s = max(range(n), key=lambda i: gaps[i])          # widest gap -> seam
    order = [(s + 1 + k) % n for k in range(n)]        # chain order from the seam
    u, prev = [], lons[order[0]]                       # unwrap along the chain
    for idx in order:
        v = lons[idx]
        while v < prev - 1e-9:
            v += 360.0
        u.append(v)
        prev = v
    tgt = u[:]
    for k in range(1, n):                              # forward sweep: enforce gap
        if u[k] < u[k - 1] + min_gap:
            u[k] = u[k - 1] + min_gap
    shift = sum(tgt[k] - u[k] for k in range(n)) / n   # recentre on true centroid
    disp = [0.0] * n
    for k, idx in enumerate(order):
        disp[idx] = (u[k] + shift) % 360.0
    return [(items[i][0], items[i][1], disp[i]) for i in range(n)]


if __name__ == "__main__":
    from openephem import houses
    # Real analytic houses (no skyfield) + a few mock planets, to a file.
    h = houses.houses_from_jd(2448027.270833, 40.7128, -74.0060, "Placidus")
    demo = {
        "angles": {"asc": h.asc, "mc": h.mc, "vertex": h.vertex, "east_point": h.east_point},
        "cusps": h.cusps,
        "bodies": {
            "Sun": {"lon": 54.6, "retro": False}, "Moon": {"lon": 300.2, "retro": False},
            "Mercury": {"lon": 47.1, "retro": True}, "Venus": {"lon": 78.0, "retro": False},
            "Mars": {"lon": 300.9, "retro": False}, "Saturn": {"lon": 293.4, "retro": False},
        },
        "aspects": [
            {"a": "Sun", "b": "Mercury", "aspect": "conjunction", "orb": 7.5},
            {"a": "Moon", "b": "Saturn", "aspect": "conjunction", "orb": 6.8},
            {"a": "Sun", "b": "Moon", "aspect": "trine", "orb": -5.6},
        ],
    }
    svg = render_svg(demo, title="Demo Chart")
    with open("demo_chart.svg", "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote demo_chart.svg ({len(svg)} bytes); asc={h.asc:.2f} mc={h.mc:.2f}")
