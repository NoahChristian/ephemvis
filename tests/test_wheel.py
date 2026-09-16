import re
import xml.etree.ElementTree as ET

import pytest

from ephemvis import aspectgrid, wheel

THEMES = ["light", "dark", "auto"] + [k for k in wheel.PALETTES if k not in ("light", "dark")]


def _mock_chart():
    # self-contained: no openephem needed to exercise the renderers
    return {
        "angles": {"asc": 45.0, "mc": 304.36},
        "cusps": [45.0, 68.27, 96.27, 124.36, 152.27, 180.27,
                  225.0, 248.27, 276.27, 304.36, 332.27, 0.27],
        "bodies": {"Sun": {"lon": 50.0, "retro": False},
                   "Moon": {"lon": 230.0, "retro": True},
                   "Mercury": {"lon": 47.0, "retro": True},
                   "Mars": {"lon": 232.0, "retro": False}},
        "aspects": [{"a": "Sun", "b": "Moon", "aspect": "opposition", "orb": 0.5},
                    {"a": "Sun", "b": "Mercury", "aspect": "conjunction", "orb": -3.0},
                    {"a": "Moon", "b": "Mars", "aspect": "conjunction", "orb": 2.0}],
    }


def test_svg_wellformed():
    s = wheel.render_svg(_mock_chart(), title="test")
    assert s.lstrip().startswith("<svg")
    assert s.rstrip().endswith("</svg>")
    assert "planet" in s and "aspect" in s and "sign" in s


def test_svg_show_aspects_toggle():
    chart = _mock_chart()
    on = wheel.render_svg(chart)
    off = wheel.render_svg(chart, show_aspects=False)
    assert on.count('class="aspect"') == len(chart["aspects"])
    assert 'class="aspect"' not in off
    # everything else still draws: this suppresses one layer, not the wheel
    assert "planet" in off and "sign" in off
    # and it is a drawing choice, not an edit to the caller's chart
    assert len(chart["aspects"]) == 3


def test_svg_show_aspects_off_is_wellformed():
    ET.fromstring(wheel.render_svg(_mock_chart(), show_aspects=False))


def test_svg_no_nan_coordinates():
    s = wheel.render_svg(_mock_chart())
    assert not re.search(r'"[-\d.]*nan[-\d.]*"', s.lower())


@pytest.mark.parametrize("theme", THEMES)
def test_svg_wellformed_xml_all_themes(theme):
    ET.fromstring(wheel.render_svg(_mock_chart(), theme=theme))


def test_svg_without_houses():
    chart = {"angles": None, "cusps": None,
             "bodies": {"Sun": {"lon": 10.0}}, "aspects": []}
    s = wheel.render_svg(chart)
    assert s.lstrip().startswith("<svg")


def _prof_chart():
    c = _mock_chart()
    # Moon (in bodies) is the Lord of the Year -> its glyph gets the ring
    c["profections"] = {
        "method": "annual+monthly+daily", "age": 34, "as_of": "2024-06-15",
        "profected_house": 11, "profected_sign": "Cancer", "profected_sign_index": 3,
        "profected_sign_lon": 90.0, "ruler": "Moon", "ruler_sign": "Scorpio", "ruler_house": 4,
        "monthly": {"index": 7, "period_start": "2024-12-14", "period_end": "2025-01-13",
                    "profected_house": 6, "profected_sign": "Aquarius",
                    "profected_sign_index": 10, "profected_sign_lon": 300.0, "ruler": "Saturn"},
        "daily": {"index": 7, "period_start": "2025-01-01", "period_end": "2025-01-03",
                  "profected_house": 1, "profected_sign": "Virgo",
                  "profected_sign_index": 5, "profected_sign_lon": 150.0, "ruler": "Mercury"},
    }
    return c


def test_profection_markers_present():
    s = wheel.render_svg(_prof_chart(), theme="light")
    assert '<polygon class="prof-band"' in s           # annual sign band
    assert '<polyline class="prof-month"' not in s      # month/day arcs are gone…
    assert '<polyline class="prof-day"' not in s        # …they read in the corner key
    assert s.count('<circle class="prof-ruler"') == 1  # only the year lord (Moon)
    assert 'class="prof-tl"' in s and ">TL</text>" in s   # the Lord-of-the-Year tag
    assert "Lord of the Year: Moon" in s               # band tooltip


def test_profection_key_present():
    # bottom-left key: eyebrow, lord + rising, and the as-of date tagged by sign.
    s = wheel.render_svg(_prof_chart(), theme="light")
    assert 'class="prof-key-eyebrow">PROFECTION' in s
    assert 'Lord: <tspan class="prof-key-em">Moon</tspan>' in s
    assert "Taurus rising" in s                         # asc 45° -> Taurus
    # date key: September (monthly ♒) · 10th (daily ♍) · 2025 (annual ♋)
    assert "June" in s and "15th" in s and "2024" in s
    assert "♒" in s and "♍" in s and "♋" in s


@pytest.mark.parametrize("theme", THEMES)
def test_profection_wellformed_all_themes(theme):
    ET.fromstring(wheel.render_svg(_prof_chart(), theme=theme))


def test_profection_can_be_disabled():
    s = wheel.render_svg(_prof_chart(), show_profection=False)
    assert '<polygon class="prof-band"' not in s
    assert '<circle class="prof-ruler"' not in s
    assert 'class="prof-tl"' not in s
    assert 'class="prof-key-eyebrow"' not in s


def test_no_profection_block_no_markers():
    s = wheel.render_svg(_mock_chart())
    assert '<polygon class="prof-band"' not in s
    assert '<circle class="prof-ruler"' not in s


def _quad_chart():
    # Placidus-like: unequal cusps, Ascendant at Leo 16°44' (136.727°). Not on sign boundaries.
    return {
        "house_system": "Placidus",
        "angles": {"asc": 136.727, "mc": 36.08},
        "cusps": [136.727, 157.59, 183.62, 216.08, 252.77, 287.40,
                  316.727, 337.59, 3.62, 36.08, 72.77, 107.40],
        "bodies": {"Sun": {"lon": 170.0, "retro": False}},
        "aspects": [],
    }


def test_cusp_labels_on_quadrant_ring():
    # Non-whole-sign: the outer ring is drawn from the cusps — a sign glyph on each cusp
    # axis plus the cusp's degree/minute; the equal sign-boundary ticks are dropped.
    s = wheel.render_svg(_quad_chart(), theme="light")
    assert s.count('class="cuspdeg"') == 12          # one degree mark per cusp
    assert s.count('class="cuspmin"') == 12          # one minute mark per cusp
    assert s.count('class="cuspsec"') == 12          # one seconds mark per cusp
    assert 'class="tick"' not in s                    # equal sign dividers dropped
    # the Ascendant cusp reads Leo 16°43'37" (16.727° -> 16°43'37.2"; deg/min/sec truncated)
    assert "House 1 cusp: Leo 16°43′37″" in s
    assert ">16°</text>" in s and ">43′</text>" in s and ">37″</text>" in s
    assert "♌" in s


def test_wholesign_ring_no_dividers():
    # Whole-sign: no cusp-degree labels and no equal dividing lines on the outer ring; the 12
    # sign glyphs sit on the house cusps instead.
    c = _mock_chart()
    c["angles"] = {"asc": 45.0, "mc": 315.0}
    c["cusps"] = [(30.0 + 30.0 * k) % 360.0 for k in range(12)]   # boundaries of Taurus-rising
    c["house_system"] = "WholeSign"
    s = wheel.render_svg(c, theme="light")
    assert 'class="cuspdeg"' not in s and 'class="cuspmin"' not in s
    assert 'class="tick"' not in s                    # equal sign dividers removed
    assert s.count('class="sign"') == 12              # 12 sign glyphs, on the cusps


def test_cusp_labels_skip_nan_cusp():
    # A NaN cusp (Placidus near the poles) is skipped, not rendered as "nan".
    c = _quad_chart()
    c["cusps"] = list(c["cusps"])
    c["cusps"][5] = float("nan")
    s = wheel.render_svg(c, theme="light")
    ET.fromstring(s)
    assert not re.search(r'"[-\d.]*nan[-\d.]*"', s.lower())
    assert s.count('class="cuspdeg"') == 11           # the NaN cusp is dropped


@pytest.mark.parametrize("theme", ["light", "dark", "prism"])
def test_aspect_grid_wellformed_xml(theme):
    s = aspectgrid.render_aspect_grid_svg(_mock_chart(), theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and "polygon" in s


def test_aspect_grid_empty_ok():
    # no aspects, few bodies -> still valid SVG
    chart = {"bodies": {"Sun": {"lon": 10.0}}, "aspects": []}
    ET.fromstring(aspectgrid.render_aspect_grid_svg(chart))


def _intercept_chart_taurus_scorpio():
    # Placidus-shaped, ~33°N Gemini rising: Cancer and Capricorn each hold two cusps, so
    # Taurus and Scorpio hold none (intercepted). Values are a real assemble() output.
    return {
        "house_system": "Placidus",
        "angles": {"asc": 65.947, "mc": 317.105},
        "cusps": [65.947, 90.308, 112.644, 137.105, 167.489, 205.747,
                  245.947, 270.308, 292.644, 317.105, 347.489, 25.747],
        "bodies": {"Sun": {"lon": 170.0, "retro": False}},
        "aspects": [],
    }


def test_intercepted_signs_shown_unequal_33n():
    # Taurus + Scorpio have no cusp -> each drawn faded (class="sign-icept") with a tooltip,
    # while the 12 cusps still carry their own on-axis sign glyphs (two of them Cancer/Capricorn).
    s = wheel.render_svg(_intercept_chart_taurus_scorpio(), theme="light")
    ET.fromstring(s)
    assert s.count('class="sign-icept"') == 2
    assert "intercepted" in s
    assert s.count('class="cuspdeg"') == 12           # every cusp still labelled


def _intercept_chart_virgo_pisces():
    # Placidus, Panama City ~9°N, Gemini rising: Virgo and Pisces hold no cusp (intercepted),
    # their opposite pair each holding two. Values are a real assemble() output.
    return {
        "house_system": "Placidus",
        "angles": {"asc": 67.221, "mc": 329.738},
        "cusps": [67.221, 94.082, 120.727, 149.738, 182.051, 215.574,
                  247.221, 274.082, 300.727, 329.738, 2.051, 35.574],
        "bodies": {"Sun": {"lon": 170.0, "retro": False}},
        "aspects": [],
    }


def test_intercepted_signs_shown_unequal_panama():
    # Virgo + Pisces have no cusp -> each drawn faded (class="sign-icept") with a tooltip,
    # while all 12 cusps still carry their own on-axis sign glyphs and degree labels.
    s = wheel.render_svg(_intercept_chart_virgo_pisces(), theme="light")
    ET.fromstring(s)
    assert s.count('class="sign-icept"') == 2
    assert "intercepted" in s
    assert s.count('class="cuspdeg"') == 12           # every cusp still labelled


def test_no_intercept_glyphs_when_every_sign_has_a_cusp():
    # A quadrant chart with no interception must not draw any faded intercepted glyphs.
    assert 'class="sign-icept"' not in wheel.render_svg(_quad_chart(), theme="light")


def test_no_intercept_glyphs_on_wholesign():
    c = _quad_chart()
    c["angles"] = {"asc": 65.95, "mc": 305.0}
    c["cusps"] = [(60.0 + 30.0 * k) % 360.0 for k in range(12)]   # whole-sign boundaries
    assert 'class="sign-icept"' not in wheel.render_svg(c, theme="light")
