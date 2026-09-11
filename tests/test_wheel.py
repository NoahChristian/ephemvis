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


@pytest.mark.parametrize("theme", ["light", "dark", "prism"])
def test_aspect_grid_wellformed_xml(theme):
    s = aspectgrid.render_aspect_grid_svg(_mock_chart(), theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and "polygon" in s


def test_aspect_grid_empty_ok():
    # no aspects, few bodies -> still valid SVG
    chart = {"bodies": {"Sun": {"lon": 10.0}}, "aspects": []}
    ET.fromstring(aspectgrid.render_aspect_grid_svg(chart))
