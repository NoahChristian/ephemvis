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

from . import _fontdata

# Deterministic glyph rendering: the astrology glyphs are embedded (subset OFL Noto fonts, via
# the astroglyphs_2K toolkit) so charts render identically regardless of the viewer's fonts.
# Set EMBED_FONTS = False to skip the embed and fall back to the viewer's system fonts.
EMBED_FONTS = True
SYM_FAMILY = _fontdata.SYM_FAMILY    # font-family stack for symbol glyphs
TXT_FAMILY = _fontdata.TXT_FAMILY    # font-family stack for numerals / labels / ℞ / ° / ′ / ″


def font_face_css() -> str:
    """The ``@font-face`` ``<style>`` for the embedded glyphs, or ``""`` when EMBED_FONTS is off."""
    return _fontdata.font_face_css() if EMBED_FONTS else ""

SIGN_GLYPHS = ["♈", "♉", "♊", "♋", "♌", "♍",
               "♎", "♏", "♐", "♑", "♒", "♓"]
SIGN_ABBR = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

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


def _is_wholesign_cusps(cusps, asc):
    """True iff the 12 cusps ARE the whole-sign sign boundaries (floor(asc/30)*30 + k*30).

    Only whole-sign makes the equal, centered-sign outer ring correct; every other house
    system (Equal, Porphyry, Placidus, Koch, Campanus, Regiomontanus — and any future one)
    has cusps that diverge from the signs, so the ring is drawn from the true cusps instead.
    Detected from the data, not a system name, so it needs no hardcoded list. A missing or
    NaN cusp counts as "not whole-sign" (→ per-cusp guarded when drawn)."""
    if not cusps or len(cusps) < 12 or asc is None:
        return False
    base = math.floor(asc / 30.0) * 30.0
    for k, c in enumerate(cusps):
        if c is None or c != c:                      # None / NaN
            return False
        exp = (base + 30.0 * k) % 360.0
        if abs((c - exp + 180.0) % 360.0 - 180.0) > 0.05:
            return False
    return True


# Degree/minute/second readout convention.
# Note: we have deliberately chosen rounding and not truncating when displaying only
# degrees, degrees and minutes, or DMS.
def _dm_round(lon):
    """(sign_index, degree, minute) for `lon`, rounded to the nearest arc-minute — carrying
    through degree and sign (e.g. 29°59.7' -> next sign 0°00')."""
    tm = int(round((lon % 360.0) * 60.0)) % 21600      # nearest minute over the whole circle
    sidx, within = divmod(tm, 1800)                     # 1800 arc-min per 30° sign
    d, m = divmod(within, 60)
    return sidx % 12, d, m


def _dms_round(lon):
    """(sign_index, degree, minute, second) for `lon`, rounded to the nearest arc-second —
    carrying through minute, degree and sign."""
    ts = int(round((lon % 360.0) * 3600.0)) % 1296000  # nearest second over the whole circle
    sidx, within = divmod(ts, 108000)                  # 108000 arc-sec per 30° sign
    d, rem = divmod(within, 3600)
    m, s = divmod(rem, 60)
    return sidx % 12, d, m, s


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

# Which aspects read as hard / soft / neutral (for per-theme aspect coloring).
ASPECT_CAT = {
    "conjunction": "neutral",
    "opposition": "hard", "square": "hard",
    "semisquare": "hard", "sesquiquadrate": "hard",
    "trine": "soft", "sextile": "soft",
    "quincunx": "soft", "semisextile": "soft", "quintile": "soft",
}

# ---- color palettes -> selectable "modes" ---------------------------------
# Each palette: bg (radial gradient in/out), ring (3 linear-gradient stops), then
# per-element colors. light/dark are functional; the rest are pastel "pretty"
# modes with a prism-like ring sweep. All are valid `theme=` values.
_L = dict(bg=("#ffffff", "#ffffff"), ring=("#b0b0b0", "#b0b0b0", "#b0b0b0"),
          tick="#b0b0b0", sign="#3a3a3a", cusp="#7f9fd4", cuspA="#3f5f9c",
          hdiv="#a3aab8", leader="#c3c7cf", housenum="#3a3a3a", anglelab="#1c1c1c",
          pmark="#b6b6b6", planet="#111111", deg="#5f5f5f", degRx="#c0392b",
          title="#222222", aHard="#d7263d", aSoft="#1f7a8c", aNeutral="#8a8a8a",
          prof="#c9962e", halo=False)
_D = dict(bg=("#14161a", "#0f1114"), ring=("#3a3f47", "#3a3f47", "#3a3f47"),
          tick="#3a3f47", sign="#c9cdd4", cusp="#6a84ad", cuspA="#a6c1ec",
          hdiv="#5b6474", leader="#4c525e", housenum="#7a828c", anglelab="#d5d9df",
          pmark="#454b54", planet="#f2f4f7", deg="#9aa1ab", degRx="#ff6f6f",
          title="#e6e9ee", aHard="#e06c78", aSoft="#5fb0c0", aNeutral="#7a828c",
          prof="#e8c15a", halo=False)


def _pretty(bg, bg2, ring, ink, mid, line, lineA, accent, hard, soft):
    return dict(bg=(bg, bg2), ring=ring, tick=line, sign=ink, cusp=line, cuspA=lineA,
                hdiv=mid, leader=line, housenum=ink, anglelab=accent, pmark=mid,
                planet=ink, deg=mid, degRx=hard, title=ink,
                aHard=hard, aSoft=soft, aNeutral=mid, prof=accent, halo=True)


def _lerp_hex(c1, c2, t):
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))


def _conic(p, stops):
    """Color at fraction p in [0,1) sweeping the three ring stops around a loop."""
    seg = (p % 1.0) * 3.0
    i = int(seg) % 3
    return _lerp_hex(stops[i], stops[(i + 1) % 3], seg - int(seg))


# Rotation applied to the halo sweep so the brightest/warmest ring stop (stops[2],
# naturally at screen 240° = ~7 o'clock) lands at the TOP of the wheel (screen 90°).
# color = _conic(mid/360 + _HALO_TURN); stops[2] shows where the arg == 2/3, so
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


def _style(pal, size=760):
    sym = SYM_FAMILY                 # embedded symbol family (falls back to system symbol fonts)
    txt = TXT_FAMILY                 # embedded text family (falls back to system-ui)
    # Fonts and stroke widths scale with `size`. They used to be hardcoded px tuned for one
    # size, so at any smaller size the glyphs bloated relative to the (size-scaled) geometry
    # and the degree labels collided with their glyphs — a scaling bug present since 0.1.0.
    # Font PROPORTIONS are set a touch smaller than the old 760 px so a wide retrograde degree
    # label (e.g. "2°℞") clears its glyph at every size; strokes use a 760 reference so the
    # 760 output (the snapshot size) keeps its exact line weights.
    def _n(v):                       # compact number: "2" not "2.0", "3.4" stays "3.4"
        return f"{round(v, 2):g}"
    k = size / 760.0                 # stroke reference (identity at 760)
    f_sign = size * 0.0315           # sign glyph   (~23.9px @760, was 28)
    f_planet = size * 0.0407         # planet glyph (+10%)
    f_deg = size * 0.0215            # degree/minute label (+10%)
    f_hnum = size * 0.0210           # house number (~16.0px @760, was 19)
    f_angle = size * 0.0315          # Asc/MC label (~23.9px @760, was 28)
    f_title = size * 0.0197          # title        (~15.0px @760, unchanged proportion)
    rules = [
        (".ring", "fill:none;stroke:url(#ringgrad);stroke-width:%s" % _n(3.4 * k)),
        (".tick", "stroke:%s;stroke-width:%s" % (pal["tick"], _n(3.4 * k))),
        (".sign", "fill:%s;font:600 %spx %s" % (pal["sign"], _n(f_sign), sym)),
        # an intercepted sign (unequal systems): present on the ring but holding no
        # house cusp, so drawn faded and without a degree readout
        (".sign-icept", "fill:%s;font:600 %spx %s;opacity:0.5" % (pal["sign"], _n(f_sign), sym)),
        (".cusp", "stroke:%s;stroke-width:%s" % (pal["cusp"], _n(2 * k))),
        (".cusp-angle", "stroke:%s;stroke-width:%s" % (pal["cuspA"], _n(2.4 * k))),
        (".hdiv", "stroke:%s;stroke-width:%s" % (pal["hdiv"], _n(1.3 * k))),
        (".leader", "stroke:%s;stroke-width:%s;stroke-dasharray:1 5;stroke-linecap:round"
         % (pal["leader"], _n(2 * k))),
        (".housenum", "fill:%s;font:600 %spx %s" % (pal["housenum"], _n(f_hnum), txt)),
        (".anglelab", "fill:%s;font:800 %spx %s" % (pal["anglelab"], _n(f_angle), txt)),
        (".ac-sm", "font-size:0.5em"),
        (".pmark", "stroke:%s;stroke-width:%s" % (pal["pmark"], _n(1.6 * k))),
        (".planet", "fill:%s;font:600 %spx %s" % (pal["planet"], _n(f_planet), sym)),
        (".deg", "fill:%s;font:600 %spx %s" % (pal["deg"], _n(f_deg), txt)),
        (".deg-rx", "fill:%s" % pal["degRx"]),
        # cusp position marks on the outer ring (non-whole-sign systems): the cusp's whole
        # degree and arc-minute flanking the sign glyph that sits on the house-cusp axis.
        (".cuspdeg", "fill:%s;font:700 %spx %s" % (pal["deg"], _n(f_deg * 0.92), txt)),
        (".cuspmin", "fill:%s;font:600 %spx %s" % (pal["deg"], _n(f_deg * 0.76), txt)),
        (".cuspsec", "fill:%s;font:600 %spx %s" % (pal["deg"], _n(f_deg * 0.64), txt)),
        # sign glyph shown inline in a planet's position readout (the sign the planet is in);
        # goes red with the degree/minute when the body is retrograde
        (".signn", "fill:%s;font:600 %spx %s" % (pal["sign"], _n(f_deg * 1.15), sym)),
        (".signn-rx", "fill:%s" % pal["degRx"]),
        (".aspect", "stroke-width:%s;fill:none;opacity:.85" % _n(1.1 * k)),
        (".title", "fill:%s;font:600 %spx %s" % (pal["title"], _n(f_title), txt)),
        # profection: annual sign band (filled) + Lord-of-the-Year ring (tagged "TL").
        # The month/day cadences read in the bottom-left key, not as arcs across the wheel
        # (an unlabelled arc through a sign glyph is meaningless to a casual viewer).
        (".prof-band", "fill:%s;fill-opacity:.16;stroke:%s;stroke-opacity:.85;stroke-width:%s"
         % (pal["prof"], pal["prof"], _n(2 * k))),
        (".prof-ruler", "fill:none;stroke:%s;stroke-opacity:.9;stroke-width:%s" % (pal["prof"], _n(2.4 * k))),
        (".prof-tl", "fill:%s;font:800 %spx %s" % (pal["prof"], _n(f_deg * 0.86), txt)),
        (".prof-key", "fill:%s;font:600 %spx %s" % (pal["deg"], _n(f_deg), txt)),
        (".prof-key-em", "fill:%s;font-weight:700" % pal["prof"]),
        (".prof-key-eyebrow", "fill:%s;font:800 %spx %s;letter-spacing:%spx"
         % (pal["prof"], _n(f_deg * 0.82), txt, _n(1.4 * k))),
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
            '.prof-band{fill:' + d["prof"] + ';stroke:' + d["prof"] + '}'
            '.prof-ruler{stroke:' + d["prof"] + '}'
            '.prof-tl,.prof-key-em,.prof-key-eyebrow{fill:' + d["prof"] + '}'
            '.prof-key{fill:' + d["deg"] + '}'
            '.title{fill:' + d["title"] + '}}</style>')


def _theme_markup(theme, size=760):
    """Return the embedded @font-face + <defs> gradients + <style> for a theme (auto = light + dark)."""
    if theme == "auto":
        return font_face_css() + _defs(_L) + _style(_L, size) + _dark_media()
    pal = PALETTES.get(theme, _L)
    return font_face_css() + _defs(pal) + _style(pal, size)


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_svg(chart: dict, size: int = 760, theme: str = "auto",
               text_labels: bool = False, title: str | None = None,
               show_profection: bool = True) -> str:
    cx = cy = size / 2.0
    r_out = size * 0.45              # outer edge (leaves a margin for AC/MC outside)
    r_zod_in = r_out * 0.890         # inner edge of the zodiac band (signs live here); matches the
    #                                  bi-wheel's outer ring width (~20% thinner than the old 0.862)
    r_house = r_zod_in               # house-cusp lines reach the zodiac inner edge
    r_tick_in = r_zod_in * 0.905     # inner end of the planet pointer ticks
    r_hnum_out = r_zod_in * 0.43     # house-ring outer = former aspect-circle radius
    r_hub = r_zod_in * 0.33          # aspect circle == house-ring inner edge (they meet)
    r_hnum = r_zod_in * 0.38         # house numbers, centered in the (wider) ring band
    glyphs = None if not text_labels else True
    apal = _L if theme == "auto" else PALETTES.get(theme, _L)  # aspect colors

    angles = chart.get("angles") or {}
    asc = angles.get("asc", 0.0)     # unknown-time -> 0 Aries at left
    cusps = chart.get("cusps")

    # Rotation anchor: the house-1 cusp is placed on the left horizon (9 o'clock). For quadrant
    # and equal systems cusps[0] == the Ascendant, so this is unchanged; but in whole-sign the
    # house 1/12 division is the SIGN boundary, so anchoring there puts that division straight
    # across the horizon and lifts the Ascendant degree to its true place inside the first house.
    rot_ref = asc
    if cusps and len(cusps) >= 12 and cusps[0] is not None and cusps[0] == cusps[0]:
        rot_ref = cusps[0]

    # Non-whole-sign house systems (Equal, Porphyry, Placidus, Koch, Campanus, Regiomontanus)
    # have cusps that diverge from the sign boundaries, so the outer ring shows the TRUE cusps
    # (the sign glyph on each cusp axis + the cusp's degree/minute) rather than the equal
    # centered-sign ring. Whole-sign keeps the centered ring exactly as before.
    label_cusps = bool(cusps and len(cusps) >= 12 and not _is_wholesign_cusps(cusps, asc))
    wholesign = bool(cusps and len(cusps) >= 12 and _is_wholesign_cusps(cusps, asc))
    cusp_darc = 4.5                  # arc-step (deg of longitude) for deg/min flanking every cusp glyph
    cusp_dsec = 3.0                  # tighter arc-gap between the minute and the seconds mark
    cusp_hband = 5.0                 # within this many deg of the Asc-Desc horizontal -> order top/bottom

    def pol(r, lon):
        """Ecliptic longitude -> (x, y). House-1 cusp at left, zodiac CCW."""
        a = math.radians(180.0 + (lon - rot_ref))
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def sp(r, deg):
        """Screen-space polar (independent of the chart's rotation) for halo bands."""
        a = math.radians(deg)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    P = []  # svg fragments
    P.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
             f'width="{size}" height="{size}" style="cursor:default" role="img" '
             f'aria-label="{_esc(title or "natal chart")}">')
    P.append(_theme_markup(theme, size))
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

    # --- profection: annual sign band (under ticks/glyphs) ---
    # The filled 30° band is the annual profected sign (Lord of the Year). The Lord's
    # glyph gets a ring + "TL" tag later; the month/day cadences are spelled out in the
    # bottom-left key rather than drawn as arcs across the ring (an unlabelled arc
    # through a sign glyph tells a casual viewer nothing). Whole-sign, counted from Asc.
    prof = chart.get("profections") if show_profection else None
    if prof and prof.get("profected_sign_index") is not None:

        def _place_txt(block):
            _o = _ORDINALS[(int(block.get("profected_house", 1)) - 1) % 12]
            return "%s · %s place" % (block.get("profected_sign", ""), _o)

        # annual: a filled 30° wedge across the whole zodiac ring
        pidx = int(prof["profected_sign_index"]) % 12
        band = " ".join("%.1f,%.1f" % pol(r_out, pidx * 30.0 + 30.0 * k / 12) for k in range(13))
        band += " " + " ".join(
            "%.1f,%.1f" % pol(r_zod_in, pidx * 30.0 + 30.0 - 30.0 * k / 12) for k in range(13))
        htxt = "Profected sign: " + _place_txt(prof)
        if prof.get("age") is not None:
            htxt += " · age %s" % prof["age"]
        if prof.get("ruler"):
            htxt += " · Lord of the Year: %s" % prof["ruler"]
        P.append(f'<polygon class="prof-band" points="{band}"><title>{_esc(htxt)}</title></polygon>')

    # --- zodiac: 12 sectors (fixed to longitude) ---
    if wholesign:
        # Whole-sign: no dividing lines on the outer ring, and each sign glyph sits ON its house
        # cusp (the sign boundary) rather than centered in the sector — at the sign's LEADING
        # cusp, so the rising sign (Leo here) lands on the far-left horizon (its 12/1 cusp).
        for i in range(12):
            gx, gy = pol((r_zod_in + r_out) / 2.0, i * 30.0)         # leading cusp of sign i
            label = SIGN_ABBR[i] if glyphs else SIGN_GLYPHS[i] + "︎"  # text, not emoji
            P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="sign" '
                     f'dominant-baseline="central" text-anchor="middle">'
                     f'<title>{_esc(sign_label(i, angles, cusps))}</title>{label}</text>')
    elif not label_cusps:
        # No house cusps (timeless chart): the standard equal zodiac ring — 30° dividers with the
        # sign glyph centered in each sector. (Non-whole-sign house systems draw the ring from the
        # true cusps in the house block below, so they skip this too.)
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
            if c is None or c != c:              # skip a missing/NaN cusp (Placidus near poles)
                continue
            cls = "cusp-angle" if (quad and i in (0, 3, 6, 9)) else "cusp"
            # solid divider between house numbers, within the number ring
            hx1, hy1 = pol(r_hub, c)
            hx2, hy2 = pol(r_hnum_out, c)
            P.append(f'<line x1="{hx1:.1f}" y1="{hy1:.1f}" x2="{hx2:.1f}" y2="{hy2:.1f}" class="hdiv"/>')
            # dotted cusp from the number ring out to the zodiac inner edge only — no divider
            # crosses the zodiac band (the cusp is marked there by its on-axis glyph instead)
            dx1, dy1 = pol(r_hnum_out, c)
            dx2, dy2 = pol(r_house, c)
            P.append(f'<line x1="{dx1:.1f}" y1="{dy1:.1f}" x2="{dx2:.1f}" y2="{dy2:.1f}" class="{cls}"/>')
            nc = cusps[(i + 1) % 12]              # next cusp, for the house-number midpoint
            if nc is not None and nc == nc:
                mid = c + (((nc - c) % 360.0) / 2.0)
                nx, ny = pol(r_hnum, mid)
                house_labels.append(f'<text x="{nx:.1f}" y="{ny:.1f}" class="housenum" '
                                    f'dominant-baseline="central" text-anchor="middle">{i + 1}</text>')
            # outer ring (non-whole-sign): the sign glyph on the cusp axis + degree/minute
            if label_cusps:
                sidx, d, m, s = _dms_round(c)             # DMS, rounded (see _dms_round)
                glyph = SIGN_ABBR[sidx] if glyphs else SIGN_GLYPHS[sidx] + "︎"
                rr = (r_zod_in + r_out) / 2.0
                ggx, ggy = pol(rr, c)
                htxt = "House %d cusp: %s %d°%02d′%02d″" % (i + 1, _SIGNS[sidx], d, m, s)
                P.append(f'<text x="{ggx:.1f}" y="{ggy:.1f}" class="sign" '
                         f'dominant-baseline="central" text-anchor="middle">'
                         f'<title>{_esc(htxt)}</title>{glyph}</text>')
                # degree before the glyph, then minute and seconds after it, all sharing the
                # glyph's RADIUS and stepping along the arc. Off the horizon they read
                # left->right (degree on the screen-left); at the Asc/Desc the arc is vertical,
                # so they order top->bottom (degree on top).
                da = (c - rot_ref) % 360.0
                xm, ym = pol(rr, c - cusp_darc)
                xp, yp = pol(rr, c + cusp_darc)
                if da < cusp_hband or da > 360.0 - cusp_hband or abs(da - 180.0) < cusp_hband:
                    forward = ym <= yp           # -darc side is higher on screen -> degree there
                else:
                    forward = xm <= xp           # -darc side is further left -> degree there
                unit = -1.0 if forward else 1.0        # step direction along the arc
                dgx, dgy = pol(rr, c + unit * cusp_darc)                # degree (before the glyph)
                mnx, mny = pol(rr, c - unit * cusp_darc)                # minute (after the glyph)
                scx, scy = pol(rr, c - unit * (cusp_darc + cusp_dsec))  # seconds (tighter to minute)
                P.append(f'<text x="{dgx:.1f}" y="{dgy:.1f}" class="cuspdeg" '
                         f'dominant-baseline="central" text-anchor="middle">{d}°</text>')
                P.append(f'<text x="{mnx:.1f}" y="{mny:.1f}" class="cuspmin" '
                         f'dominant-baseline="central" text-anchor="middle">{m:02d}′</text>')
                P.append(f'<text x="{scx:.1f}" y="{scy:.1f}" class="cuspsec" '
                         f'dominant-baseline="central" text-anchor="middle">{s:02d}″</text>')
        # Intercepted signs (unequal/quadrant systems): a sign holding no house cusp
        # sits entirely inside one house. Show its glyph at the sign's own midpoint —
        # between its two neighbouring cusp signs on the ring — faded and with no degree
        # readout, since it owns no cusp. Whole-sign has one cusp per sign, so none here.
        if label_cusps:
            placed = {_dms_round(c)[0] for c in cusps if c is not None and c == c}
            rr = (r_zod_in + r_out) / 2.0
            for si in range(12):
                if si in placed:
                    continue
                gx, gy = pol(rr, si * 30.0 + 15.0)
                glyph = SIGN_ABBR[si] if glyphs else SIGN_GLYPHS[si] + "︎"
                htxt = "%s — intercepted (no house cusp)" % _SIGNS[si]
                P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="sign-icept" '
                         f'dominant-baseline="central" text-anchor="middle">'
                         f'<title>{_esc(htxt)}</title>{glyph}</text>')
        # Non-whole-sign only: Asc/MC as a guide OUTSIDE the ring (their exact positions are
        # already published on the rim as cusp labels). Whole-sign draws them inside among the
        # planets instead. The trailing "C" is half-height, baseline-aligned (not descending).
        if label_cusps:
            r_ang = r_out + size * 0.03
            for key, first in (("asc", "A"), ("mc", "M")):
                if key in angles:
                    lx, ly = pol(r_ang, angles[key])
                    P.append(f'<text x="{lx:.1f}" y="{ly + size*0.008:.1f}" class="anglelab" '
                             f'text-anchor="middle"><title>{_esc(angle_label(key, angles[key]))}</title>'
                             f'{first}<tspan class="ac-sm">C</tspan></text>')

    # --- planets (+ Asc/MC on whole-sign): radial readouts, angular rubber-band de-collision ---
    # The planet glyph is the marker, set just inside the zodiac (clear of the tick line so the
    # ring can't clip it). Its readout runs RADIALLY inward from the glyph — degree nearest the
    # ring, then the sign glyph, then the minute — each token rotated to the spoke and kept
    # upright (so it reads one way on the left of the wheel, the other on the right). Bodies too
    # close in angle are rubber-banded apart (bounded); nothing is drawn below the house numbers.
    bodies = chart.get("bodies") or {}
    angle_glyph = {"asc": "Ac", "mc": "Mc"}     # Asc/MC drawn as markers among the planets
    fdeg = size * 0.0215                        # degree/minute label (+10%, matches _style)
    fpl = size * 0.0407                         # planet glyph (+10%, matches _style)
    r_sym = r_tick_in - fpl * 0.62             # glyph just inside the ring, with clearance
    r_lab0 = r_sym - fpl * 0.70                # outer edge of the readout block (gap from the glyph)
    gap = math.degrees(fpl * 1.40 / r_sym)     # min angular spacing (glyph width + margin) for the fan
    # Whole-sign only: the Asc/MC sit in the planet band and carry the same degree/sign/minute
    # readout as a body, de-collided in the same fan; drawn at the true angle longitude. On other
    # systems they stay as outside guides (above) since the rim already publishes their positions.
    marker_lons = [(n, bodies[n]["lon"]) for n in bodies]
    if wholesign:
        for akey in ("asc", "mc"):
            av = angles.get(akey)
            if av is not None and av == av:
                marker_lons.append((akey, av))
    placed = _spread(marker_lons, min_gap=gap)

    def _tw(s: str) -> float:                  # approx rendered width of a numeric readout token
        return sum(fdeg * (0.42 if ch == "°" else 0.30 if ch == "′" else 0.72 if ch == "℞"
                           else 0.56 if ch.isdigit() else 0.60) for ch in s)

    hub_pts = {}
    for name, lon, disp in placed:
        is_angle = name in angle_glyph
        # true-position mark: a short spoke just inside the zodiac
        tx1, ty1 = pol(r_tick_in, lon)
        tx2, ty2 = pol(r_house, lon)
        P.append(f'<line x1="{tx1:.1f}" y1="{ty1:.1f}" x2="{tx2:.1f}" y2="{ty2:.1f}" class="pmark"/>')
        gx, gy = pol(r_sym, disp)
        # dotted leader from the glyph's bounding-box EDGE nearest the mark (not its centre)
        if abs((disp - lon + 180.0) % 360.0 - 180.0) > 1.0:
            dxl, dyl = tx1 - gx, ty1 - gy
            te = min(fpl * 0.42 / abs(dxl) if dxl else 1e9,
                     fpl * 0.46 / abs(dyl) if dyl else 1e9)
            sx, sy = gx + dxl * te, gy + dyl * te      # exit point on the glyph box toward the mark
            P.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{tx1:.1f}" y2="{ty1:.1f}" class="leader"/>')
        if prof and name == prof.get("ruler"):   # ring + "TL" tag on the year-lord glyph
            P.append(f'<circle class="prof-ruler" cx="{gx:.1f}" cy="{gy:.1f}" '
                     f'r="{size*0.028:.1f}"><title>{_esc("Lord of the Year (time-lord)")}'
                     f'</title></circle>')
            P.append(f'<text x="{gx + size*0.026:.1f}" y="{gy - size*0.020:.1f}" class="prof-tl" '
                     f'text-anchor="start"><title>{_esc("Lord of the Year (time-lord)")}</title>'
                     f'TL</text>')
        retro = False if is_angle else bodies[name].get("retro")
        lbl = _esc(angle_label(name, lon) if is_angle          # hover: name in sign at deg
                   else body_label(name, bodies[name]))
        if is_angle:
            # Asc/MC keep their prior label style ("A"/"M" + a half-height "C"), just moved
            # inside among the planets (whole-sign only).
            first = "A" if name == "asc" else "M"
            # Center the big letter on the marker point like the planet glyphs (so it doesn't
            # ride high), then drop the half-height "C" down onto that letter's baseline.
            cdy = size * 0.0055
            P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="anglelab" '
                     f'dominant-baseline="central" text-anchor="middle">'
                     f'<title>{lbl}</title>{first}'
                     f'<tspan class="ac-sm" dy="{cdy:.1f}">C</tspan></text>')
        else:
            if glyphs:
                g = PLANET_ABBR.get(name, name[:2])
            else:  # fixed stars share one ✦ marker; the name identifies them in the key
                base = PLANET_GLYPHS.get(name) or ("✦" if bodies[name].get("kind") == "star" else name[:2])
                g = base + "︎"  # text, not emoji
            # planet glyph = the marker, upright, just inside the ring
            P.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="planet" '
                     f'dominant-baseline="central" text-anchor="middle">'
                     f'<title>{lbl}</title>{_esc(g)}</text>')
        sidx_p, d0, m0 = _dm_round(lon)                     # rounded deg/min + the sign it's in
        sgl = SIGN_ABBR[sidx_p] if glyphs else SIGN_GLYPHS[sidx_p] + "︎"
        rxm = "℞" if retro else ""
        ncls = "deg deg-rx" if retro else "deg"             # degree/minute (red when retro)
        scls = "signn signn-rx" if retro else "signn"       # sign glyph too (red when retro)
        # readout tokens down the spoke (degree at the ring, then sign, then minute), each
        # rotated to the spoke and kept upright
        a = math.radians(180.0 + disp - rot_ref)
        rot0 = math.degrees(math.atan2(math.sin(a), -math.cos(a)))   # spoke direction (inward)
        rot = rot0 - 180.0 if rot0 > 90.0 else (rot0 + 180.0 if rot0 < -90.0 else rot0)
        deg_t, min_t = f"{d0}°{rxm}", f"{m0:02d}′"
        # tokens run ALONG the spoke, so each occupies its WIDTH radially — lay them end-to-end
        # with a gap so ℞/sign never collide. On the LEFT half degree sits at the ring (outer);
        # on the RIGHT half the order is reversed so both halves read degree→sign→minute L→R.
        toks = [(deg_t, ncls, _tw(deg_t)), (sgl, scls, fdeg * 1.20), (min_t, ncls, _tw(min_t))]
        if gx >= cx:                            # right half of the wheel
            toks.reverse()
        edge = r_lab0
        for tok, tcls, w in toks:
            lx, ly = pol(edge - w / 2.0, disp)
            P.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="{tcls}" '
                     f'transform="rotate({rot:.1f} {lx:.1f} {ly:.1f})" '
                     f'dominant-baseline="central" text-anchor="middle">'
                     f'<title>{lbl}</title>{tok}</text>')
            edge -= w + fdeg * 0.42
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

    # --- profection key (bottom-left corner) ---
    # Annual lord + rising sign (as on the dedicated profection wheel), then the as-of
    # date with each component tagged by the sign it profects to: month→Lord of the
    # Month's sign, day→Lord of the Day's sign, year→the annual sign. This spells out
    # the month/day cadences the old arcs only hinted at, without crossing any glyph.
    if prof and prof.get("profected_sign_index") is not None:
        kx = size * 0.024
        P.append(f'<text x="{kx:.1f}" y="{size*0.898:.1f}" class="prof-key-eyebrow">PROFECTION</text>')
        seg = []
        if prof.get("ruler"):
            seg.append(f'Lord: <tspan class="prof-key-em">{_esc(prof["ruler"])}</tspan>')
        if angles.get("asc") is not None:
            seg.append(f'{_esc(SIGN_NAMES[int(asc // 30) % 12])} rising')
        if seg:
            P.append(f'<text x="{kx:.1f}" y="{size*0.930:.1f}" class="prof-key">'
                     + " · ".join(seg) + '</text>')
        asof = prof.get("as_of")
        try:
            y, m, dd = (int(v) for v in str(asof)[:10].split("-")) if asof else (0, 0, 0)
        except (ValueError, TypeError):
            y = m = dd = 0
        if m:
            MON = ("January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December")
            osfx = "th" if 10 <= dd % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(dd % 10, "th")

            def _gtag(block):
                if block and block.get("profected_sign_index") is not None:
                    gi = int(block["profected_sign_index"]) % 12
                    return f'<tspan class="prof-key-em" dx="3">{SIGN_GLYPHS[gi]}︎</tspan>'
                return ""

            yr_gly = f'<tspan class="prof-key-em" dx="3">{SIGN_GLYPHS[pidx]}︎</tspan>'
            line = (f'{MON[m-1]}{_gtag(prof.get("monthly"))} · '
                    f'{dd}{osfx}{_gtag(prof.get("daily"))} · {y}{yr_gly}')
            P.append(f'<text x="{kx:.1f}" y="{size*0.962:.1f}" class="prof-key">{line}</text>')

    if title:
        P.append(f'<text x="{cx:.1f}" y="{size*0.04:.1f}" class="title" '
                 f'text-anchor="middle">{_esc(title)}</text>')
    P.append('</svg>')
    return "\n".join(P)


def _spread(items, min_gap=7.0, half_widths=None, pad=0.0):
    """De-collide glyph display angles while preserving zodiacal order. Cut the circle at its
    widest gap so clusters can open into free space, then push apart ONLY the pairs that would
    actually collide, symmetrically (half each). Bodies whose neighbours are already far enough
    keep their true longitude — no global recenter — so an isolated planet never drifts. A cluster
    expands evenly about its own centre, cascading into a neighbour only if it genuinely reaches it.

    When ``half_widths`` (a ``{name: angular half-width in degrees}`` map, derived from the real
    glyph metrics) is given, an adjacent pair is separated only until centre-to-centre reaches
    ``half_widths[a] + half_widths[b] + pad`` — true per-glyph collision spacing, so each glyph
    stays as near its true longitude as its own width allows (a narrow node barely moves; only a
    wide glyph pushes). Otherwise the flat ``min_gap`` is used for every pair.
    Returns (name, true_lon, disp)."""
    items = sorted(items, key=lambda t: t[1])
    n = len(items)
    if n < 2:
        return [(nm, lo, lo) for nm, lo in items]
    lons = [lo for _, lo in items]
    hw = [half_widths.get(nm, min_gap / 2.0) for nm, _ in items] if half_widths is not None else None
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
    for _ in range(400):                              # relax: push only-too-close pairs apart
        moved = False
        for k in range(n - 1):
            need = (hw[order[k]] + hw[order[k + 1]] + pad) if hw is not None else min_gap
            over = need - (u[k + 1] - u[k])
            if over > 1e-9:
                u[k] -= over / 2.0
                u[k + 1] += over / 2.0
                moved = True
        if not moved:
            break
    disp = [0.0] * n
    for k, idx in enumerate(order):
        disp[idx] = u[k] % 360.0
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
