import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pytest

from ephemvis import render_zodiacal_releasing_svg
from ephemvis.wheel import PALETTES

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def _iso(y, doy):
    return (date(y, 1, 1) + timedelta(days=doy)).isoformat()


def _chart():
    # a minimal zodiacal_releasing block (openephem's shape): Aquarius lot, Fortune in
    # Leo -> peaks Leo/Scorpio/Aquarius/Taurus. Two L1 periods, each with L2 sub-periods.
    def _l2(idx, y0, d0, y1, d1, peak=False, lb=False, ang=None):
        return {"sign": SIGNS[idx], "sign_index": idx, "start": _iso(y0, d0),
                "end": _iso(y1, d1), "peak": peak,
                "angularity": ang or ("angular" if peak else "cadent"), "lb": lb}

    aqu = {"sign": "Aquarius", "sign_index": 10, "start": "2000-01-01",
           "end": "2030-01-01", "age_start": 0.0, "age_end": 30.0, "peak": True,
           "angularity": "angular", "lb": False,
           "l2": [_l2(10, 2000, 256, 2003, 60, peak=True),
                  _l2(11, 2003, 60, 2004, 100, ang="succedent"),  # a succedent sub-period
                  _l2(4, 2018, 13, 2019, 200, lb=True)]}          # a level-2 loosing -> "lb"
    # second L1 = Gemini (a wide sign not used in the first L1, so its glyph is unique); a
    # succedent L1 that itself begins on a loosing of the bond -> the major "LB" marker.
    gem = {"sign": "Gemini", "sign_index": 2, "start": "2030-01-01",
           "end": "2050-01-01", "age_start": 30.0, "age_end": 50.0, "peak": False,
           "angularity": "succedent", "lb": True,
           "l2": [_l2(2, 2030, 256, 2033, 100),
                  _l2(3, 2033, 100, 2035, 50)]}
    return {"zodiacal_releasing": {
        "lot": "fortune", "lot_sign": "Aquarius", "lot_lon": 310.0, "peak_from": "Leo",
        "age": 22, "as_of": "2013-01-01",
        "current": {"l1": {"sign": "Aquarius"}, "l2": {"sign": "Scorpio"},
                    "l3": {"sign": "Virgo"}, "l4": {"sign": "Cancer"}},
        "timeline": [aqu, gem]}}


@pytest.mark.parametrize("theme", list(PALETTES) + ["auto"])
def test_wellformed_all_themes(theme):
    s = render_zodiacal_releasing_svg(_chart(), theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and s.rstrip().endswith("</svg>")


def test_title_and_subtitle():
    s = render_zodiacal_releasing_svg(_chart())
    assert ">Zodiacal Releasing<" in s
    assert "Lot of Fortune in Aquarius" in s and "age 22" in s
    assert "Aquarius › Scorpio › Virgo › Cancer" in s          # the current L1-L4 path
    assert ">Time Lords<" in render_zodiacal_releasing_svg(_chart(), title="Time Lords")


def test_sign_glyphs_and_legend():
    s = render_zodiacal_releasing_svg(_chart())
    for g in ("♒", "♊"):                                       # the two wide L1 sign glyphs
        assert g in s
    for el in ("Fire", "Earth", "Air", "Water"):               # element legend: "Element (glyphs)"
        assert f">{el} (" in s
    # angularity legend: angular (peak) + succedent, plus the loosing-of-the-bond key
    assert ">angular (peak)<" in s and ">succedent<" in s and ">loosing of the bond<" in s


def test_peak_and_lb_and_current_markers():
    s = render_zodiacal_releasing_svg(_chart())
    assert "stroke-dasharray" in s               # a loosing-of-the-bond marker
    assert s.count(">LB<") >= 2                   # both an L1 and an L2 loosing are marked
    assert 'font-weight="800"' in s              # the deep L1 loosing is uniquely heaviest
    assert 'stroke-width="2.2"' in s             # its heavier dashed line vs the L2 loosing's
    assert 'stroke-dasharray="4 4"' in s         # a succedent accent bar (two-colour dotted vs solid peak)
    assert 'stroke-width="2.4"' in s             # the current-period outline
    assert 'stroke-width="2"' in s               # the age-marker line


def test_requires_releasing_block():
    with pytest.raises(ValueError):
        render_zodiacal_releasing_svg({"bodies": {}})


def test_max_age_clips():
    # a short horizon drops the second L1 period (Gemini, age 30+). Every sign glyph now also
    # appears once in the legend, so compare counts: Gemini (♊) shows in a band + the legend at
    # a full horizon, but only in the legend once clipped.
    assert render_zodiacal_releasing_svg(_chart(), max_age=90).count("♊") \
        > render_zodiacal_releasing_svg(_chart(), max_age=20).count("♊")


def test_deterministic():
    a = render_zodiacal_releasing_svg(_chart(), theme="infrared")
    assert a == render_zodiacal_releasing_svg(_chart(), theme="infrared")
