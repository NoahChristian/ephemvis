import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pytest

from ephemvis import render_decennials_svg
from ephemvis.wheel import PALETTES

CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
MINOR = {"Saturn": 30, "Jupiter": 12, "Mars": 15, "Sun": 19,
         "Venus": 8, "Mercury": 20, "Moon": 25}
MONTH = 365.2425 / 12.0


def _chart(as_of="2055-06-01"):
    # a minimal decennials block (openephem's shape): start Saturn, Chaldean succession,
    # each 129-month decennial sub-divided into minor-years-as-months.
    birth = date(2000, 1, 1)
    t = birth
    tl = []
    for k in range(7):
        gen = CHALDEAN[k % 7]
        major_start = t
        subs = []
        c = t
        for j in range(7):
            sub = CHALDEAN[(k + j) % 7]
            e = c + timedelta(days=MINOR[sub] * MONTH)
            subs.append({"ruler": sub, "start": c.isoformat(), "end": e.isoformat()})
            c = e
        tl.append({"ruler": gen, "start": major_start.isoformat(), "end": c.isoformat(),
                   "age_start": round((major_start - birth).days / 365.2425, 2),
                   "age_end": round((c - birth).days / 365.2425, 2), "subs": subs})
        t = c
    return {"decennials": {"start": "Saturn", "age": 55, "as_of": as_of,
                           "current": {"major": "Mercury", "sub": "Moon",
                                       "major_start": tl[5]["start"], "major_end": tl[5]["end"],
                                       "sub_start": "x", "sub_end": "y"},
                           "timeline": tl}}


@pytest.mark.parametrize("theme", list(PALETTES) + ["auto"])
def test_wellformed_all_themes(theme):
    s = render_decennials_svg(_chart(), theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and s.rstrip().endswith("</svg>")


def test_title_and_subtitle():
    s = render_decennials_svg(_chart())
    assert ">Decennials<" in s
    assert "From Saturn" in s and "age 55" in s and "Mercury / Moon" in s
    assert ">Time Lords<" in render_decennials_svg(_chart(), title="Time Lords")


def test_planet_glyphs_and_legend():
    s = render_decennials_svg(_chart())
    for g in ("☉", "☽", "☿", "♀", "♂", "♃", "♄"):        # all seven classical glyphs
        assert g in s
    for planet in CHALDEAN:                                # legend labels: "Name (glyph)"
        assert f">{planet} (" in s


def test_current_major_and_age_marker():
    s = render_decennials_svg(_chart())
    assert 'stroke-width="2.4"' in s          # the current major/sub outline
    assert 'stroke-width="2"' in s            # the age-marker line


def test_requires_decennials_block():
    with pytest.raises(ValueError):
        render_decennials_svg({"bodies": {}})


def test_max_age_clips():
    # a short horizon drops the later decennials; the last (Moon, age ~64+) vanishes
    full = render_decennials_svg(_chart(), max_age=76)
    clipped = render_decennials_svg(_chart(), max_age=20)
    # the Moon *major* glyph (large) shows at full horizon but not when clipped to age 20
    assert full.count("☽") > clipped.count("☽")


def test_deterministic():
    a = render_decennials_svg(_chart(), theme="infrared")
    assert a == render_decennials_svg(_chart(), theme="infrared")


# --------------------------------------------------------------------------- #
# chart style (the AP wheel with the decennials rolled onto the annuli)
# --------------------------------------------------------------------------- #

def _wheel_chart():
    c = _chart()
    c["angles"] = {"asc": 15.0}                     # Aries rising (synthetic)
    c["bodies"] = {"Sun": {"lon": 10.0}, "Moon": {"lon": 200.0}, "Mercury": {"lon": 25.0},
                   "Venus": {"lon": 340.0}, "Mars": {"lon": 130.0}, "Jupiter": {"lon": 75.0},
                   "Saturn": {"lon": 260.0}}
    c["profections"] = {"age": 40, "ruler": "Mars"}       # the wheel draws on the AP annuli
    return c


@pytest.mark.parametrize("theme", ["meadow", "infrared", "light", "dark", "auto"])
def test_chart_style_wellformed(theme):
    s = render_decennials_svg(_wheel_chart(), style="chart", theme=theme)
    ET.fromstring(s)
    assert s.lstrip().startswith("<svg") and s.rstrip().endswith("</svg>")
    assert ">Decennials<" in s


def test_chart_style_needs_profections():
    c = _wheel_chart()
    del c["profections"]
    with pytest.raises(ValueError):
        render_decennials_svg(c, style="chart")


@pytest.mark.parametrize("sub_style", ["ticks", "gradient"])
def test_chart_style_sub_styles(sub_style):
    s = render_decennials_svg(_wheel_chart(), style="chart", sub_style=sub_style)
    ET.fromstring(s)


def test_bad_style_raises():
    with pytest.raises(ValueError):
        render_decennials_svg(_chart(), style="bogus")


def test_theme_lord_colors_distinct():
    from ephemvis.profection_wheel import theme_lord_colors
    cols = theme_lord_colors("meadow", CHALDEAN)
    assert len(cols) == 7 and len(set(cols.values())) == 7   # 7 distinct lord colours


def test_timeline_legend_has_glyphs_and_date():
    s = render_decennials_svg(_chart(as_of="2055-04-20"))
    assert "April 20, 2055" in s                     # the as-of date by the marker
    for planet in CHALDEAN:
        assert f">{planet} (" in s                   # "Name (glyph)" legend


def test_glyphs_by_year_keeps_short_subs():
    # every sub-period must surface in at least one age cell — sampling the sub at each
    # birthday used to drop a sub that opened and closed between two birthdays (a Venus sub
    # is ~8 months). The only permitted miss is a sliver clipped at the horizon.
    from ephemvis.decennials import _glyphs_by_year, _sub_segments
    dec = _chart()["decennials"]
    n = 84
    segs = _sub_segments(dec, n)
    glyphs = _glyphs_by_year(segs, n)
    assert len(glyphs) == n and all(g is not None for g in glyphs)   # every cell filled
    for a0, a1, ruler in segs:
        if a1 >= n - 0.5:                            # skip a fragment clipped at the horizon
            continue
        cells = [int(y) for y in range(int(a0), min(int(a1) + 1, n))]
        assert any(glyphs[y] == ruler for y in cells), f"{ruler} sub {a0:.2f}-{a1:.2f} dropped"
    # Venus (8-month subs) is the case that regressed — make sure several survive
    assert glyphs.count("Venus") >= 6
