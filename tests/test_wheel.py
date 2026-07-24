import re
import xml.etree.ElementTree as ET
import pytest
from ephemvis import wheel, aspectgrid

THEMES = ["light", "dark", "auto"] + [k for k in wheel.PALETTES if k not in ("light", "dark")]


def _mock_chart():
    # self-contained: no openephem needed to exercise the renderers
    return {
        "angles": {"asc": 136.73, "mc": 36.09},
        "cusps": [136.73, 160.0, 188.0, 216.09, 244.0, 272.0,
                  316.73, 340.0, 8.0, 36.09, 64.0, 92.0],
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


@pytest.mark.parametrize("theme", ["light", "dark", "prism"])
def test_aspect_grid_wellformed_xml(theme):
    s = aspectgrid.render_aspect_grid_svg(_mock_chart(), theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and "polygon" in s


def test_aspect_grid_empty_ok():
    # no aspects, few bodies -> still valid SVG
    chart = {"bodies": {"Sun": {"lon": 10.0}}, "aspects": []}
    ET.fromstring(aspectgrid.render_aspect_grid_svg(chart))
