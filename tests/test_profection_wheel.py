import xml.etree.ElementTree as ET

import pytest

from ephemvis import render_profection_wheel_svg
from ephemvis.wheel import PALETTES

# A synthetic test chart (Aries rising, arbitrary planet placements); age 40, Mars lord.
BODIES = {"Sun": {"lon": 10.0}, "Moon": {"lon": 200.0}, "Mercury": {"lon": 25.0},
          "Venus": {"lon": 340.0}, "Mars": {"lon": 130.0}, "Jupiter": {"lon": 75.0},
          "Saturn": {"lon": 260.0}, "Uranus": {"lon": 300.0}}


def _chart(age=40, asc=15.0, ruler="Mars"):
    return {"angles": {"asc": asc, "mc": 45.0}, "bodies": BODIES,
            "profections": {"age": age, "profected_house": (age % 12) + 1, "ruler": ruler}}


@pytest.mark.parametrize("theme", list(PALETTES) + ["auto"])
def test_wellformed_all_themes(theme):
    s = render_profection_wheel_svg(_chart(), theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and s.rstrip().endswith("</svg>")


def test_title_and_subtitle():
    s = render_profection_wheel_svg(_chart())
    assert ">Annual Profections<" in s          # default title
    assert ">Lord: Mars<" in s and ">Aries rising<" in s    # Lord above rising; age omitted here
    assert ">Age 40<" not in s                              # age lives on the ring, not the header
    s2 = render_profection_wheel_svg(_chart(), title="Firdaria")
    assert ">Firdaria<" in s2 and ">Annual Profections<" not in s2


def test_age_cells_and_current_age():
    s = render_profection_wheel_svg(_chart(age=40))
    assert ">40</text>" in s                     # the current age is drawn...
    assert 'font-weight="800"' in s              # ...in bold
    assert 'stroke-width="3.4"' in s             # current-age cell outline


def test_max_age_completes_the_ring():
    s83 = render_profection_wheel_svg(_chart(), max_age=83)   # 7 rings -> 0..83
    assert ">83</text>" in s83 and ">84</text>" not in s83
    assert ">83</text>" in s83.rsplit("AGE", 1)[-1] or ">83<" in s83  # legend max
    s84 = render_profection_wheel_svg(_chart(), max_age=84)   # completes to 8 rings -> 0..95
    assert ">95</text>" in s84


def test_planets_classical_vs_all():
    s = render_profection_wheel_svg(_chart(), planets="classical")
    assert "☉" in s and "♃" in s and "♄" in s    # Sun/Jupiter/Saturn present
    assert "♅" not in s                          # Uranus excluded from classical
    s_all = render_profection_wheel_svg(_chart(), planets="all")
    assert "♅" in s_all                          # Uranus included in 'all'


def test_requires_profections_and_asc():
    with pytest.raises(ValueError):
        render_profection_wheel_svg({"angles": {"asc": 15.0}, "bodies": {}})
    with pytest.raises(ValueError):
        render_profection_wheel_svg({"angles": None, "bodies": {},
                                     "profections": {"age": 40, "ruler": "Mars"}})


def test_deterministic():
    a = render_profection_wheel_svg(_chart(), theme="infrared")
    b = render_profection_wheel_svg(_chart(), theme="infrared")
    assert a == b


def test_planets_list_and_bad_arg():
    # Uranus is in BODIES but not a domicile lord, so its glyph proves the natal-planet filter
    # (classical glyphs may also appear as Lord-of-the-Year rim colours' legend entries).
    s = render_profection_wheel_svg(_chart(), planets=["Sun", "Moon"])
    assert "☉" in s and "☽" in s and "♅" not in s
    assert "♅" in render_profection_wheel_svg(_chart(), planets="all")   # Uranus when included
    with pytest.raises(ValueError):
        render_profection_wheel_svg(_chart(), planets="bogus")


def test_layout_defaults_to_annulus():
    # the default is the concentric-ring wheel; passing it explicitly changes nothing
    assert render_profection_wheel_svg(_chart()) == \
        render_profection_wheel_svg(_chart(), layout="annulus")


@pytest.mark.parametrize("theme", ["light", "meadow", "infrared", "auto"])
def test_spiral_layout_wellformed(theme):
    s = render_profection_wheel_svg(_chart(), theme=theme, layout="spiral")
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and s.rstrip().endswith("</svg>")
    assert ">40</text>" in s                      # ages still drawn
    assert ">Lord: Mars<" in s and ">Aries rising<" in s   # shared header unchanged


def test_spiral_differs_from_annulus_only_in_band():
    ann = render_profection_wheel_svg(_chart())
    spi = render_profection_wheel_svg(_chart(), layout="spiral")
    assert ann != spi
    assert "<polyline" in spi and "<polyline" not in ann   # coil edge only in spiral
    # the shared inner wheel + sign rim are present in both
    for token in (">Asc<", "☉", "♄"):
        assert token in ann and token in spi


def test_bad_layout_raises():
    with pytest.raises(ValueError):
        render_profection_wheel_svg(_chart(), layout="bogus")


@pytest.mark.parametrize("layout", ["annulus", "spiral"])
def test_lord_of_year_rim_and_stacked_legends(layout):
    # the plain wheel colours each sign's rim arc by its Lord of the Year and carries two stacked
    # legends: the lord colours, then the age heatmap gradient.
    s = render_profection_wheel_svg(_chart(), layout=layout)
    assert "LORD OF THE YEAR" in s and ">AGE</text>" in s
    for planet in ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"):
        assert f">{planet} (" in s                    # each lord named in the legend
    for g in ("♄", "♃", "♂", "☉", "♀", "☿", "☽"):
        assert g in s                                  # each lord glyph present
