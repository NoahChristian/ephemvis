import xml.etree.ElementTree as ET

import pytest

from ephemvis import render_vedic_square_svg


def _chart():
    # a synthetic sidereal chart (Aries rising); TrueNode present so Rāhu/Ketu both place
    return {"zodiac": "sidereal", "angles": {"asc": 15.0},
            "bodies": {"Sun": {"lon": 256.5}, "Moon": {"lon": 199.47}, "Mars": {"lon": 304.1},
                       "Mercury": {"lon": 248.0}, "Jupiter": {"lon": 1.4}, "Venus": {"lon": 217.7},
                       "Saturn": {"lon": 16.5}, "TrueNode": {"lon": 100.1}}}


@pytest.mark.parametrize("style", ["south", "north", "east"])
@pytest.mark.parametrize("theme", ["light", "meadow", "infrared", "auto"])
def test_wellformed(style, theme):
    s = render_vedic_square_svg(_chart(), style=style, theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and s.rstrip().endswith("</svg>")


@pytest.mark.parametrize("style", ["south", "north", "east"])
def test_all_nine_grahas_placed(style):
    s = render_vedic_square_svg(_chart(), style=style)
    for g in ("☉", "☽", "♂", "☿", "♃", "♀", "♄", "☊", "☋"):   # incl. Rāhu/Ketu (node ± 180)
        assert g in s


def test_requires_ascendant():
    with pytest.raises(ValueError):
        render_vedic_square_svg({"bodies": {"Sun": {"lon": 0.0}}, "angles": {}})


def test_tropical_chart_raises():
    # The renderer uses longitudes as given, so a tropical chart would draw a
    # well-formed square shifted by the ayanamsa — nearly a whole rāśi.
    with pytest.raises(ValueError, match="sidereal"):
        render_vedic_square_svg(dict(_chart(), zodiac="tropical"))


def test_zodiac_absent_still_renders():
    # Any engine emitting the ChartResult shape may omit 'zodiac'. That cannot be
    # proven wrong, so it must still draw.
    c = _chart()
    c.pop("zodiac")
    ET.fromstring(render_vedic_square_svg(c))


def test_bad_style_raises():
    with pytest.raises(ValueError):
        render_vedic_square_svg(_chart(), style="west")


def test_varga_label_from_chart_tag():
    c = _chart()
    c["varga"] = {"division": 9, "name": "Navāṃśa"}
    assert "D-9" in render_vedic_square_svg(c, style="north")
    assert "D-1" in render_vedic_square_svg(_chart(), style="north")   # default when untagged
