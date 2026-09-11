import xml.etree.ElementTree as ET

import pytest

from ephemvis import render_firdaria_svg
from ephemvis.wheel import PALETTES


def _chart():
    # a minimal firdaria block (openephem's shape), night chart, age 55 -> Venus/Mars
    def _major(ruler, a0, a1, subs):
        return {"ruler": ruler, "start": "x", "end": "y", "age_start": a0, "age_end": a1,
                "subs": [{"ruler": s, "start": "x", "end": "y"} for s in subs]}
    NIGHT = ["Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury"]
    tl = []
    a = 0.0
    seq = [("Moon", 9), ("Saturn", 11), ("Jupiter", 12), ("Mars", 7), ("Sun", 10),
           ("Venus", 8), ("Mercury", 13), ("North Node", 3), ("South Node", 2)]
    for ruler, yrs in seq:
        si = NIGHT.index(ruler) if ruler in NIGHT else 0
        subs = [NIGHT[(si + i) % 7] for i in range(7)]
        tl.append(_major(ruler, a, a + yrs, subs))
        a += yrs
    return {"firdaria": {"sect": "night", "age": 55, "as_of": "2026-06-01",
                         "current": {"major": "Venus", "sub": "Mars"}, "timeline": tl}}


@pytest.mark.parametrize("theme", list(PALETTES) + ["auto"])
def test_wellformed_all_themes(theme):
    s = render_firdaria_svg(_chart(), theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and s.rstrip().endswith("</svg>")


def test_title_and_subtitle():
    s = render_firdaria_svg(_chart())
    assert ">Firdaria<" in s
    assert "Night chart" in s and "age 55" in s and "Venus / Mars" in s
    assert ">Zodiacal Releasing<" in render_firdaria_svg(_chart(), title="Zodiacal Releasing")


def test_planet_glyphs_and_legend():
    s = render_firdaria_svg(_chart())
    for g in ("☽", "♄", "♃", "♂", "☉", "♀", "☿", "☊", "☋"):   # all nine glyphs
        assert g in s
    assert "North Node" in s and "South Node" in s              # legend labels


def test_current_period_outlined():
    s = render_firdaria_svg(_chart())
    assert 'stroke-width="2.4"' in s          # the current major/sub outline
    assert 'stroke-width="2"' in s            # the age marker line


def test_requires_firdaria_block():
    with pytest.raises(ValueError):
        render_firdaria_svg({"bodies": {}})


def test_deterministic():
    a = render_firdaria_svg(_chart(), theme="infrared")
    assert a == render_firdaria_svg(_chart(), theme="infrared")
