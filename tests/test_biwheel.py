import xml.etree.ElementTree as ET

import pytest

from ephemvis import PALETTES, render_biwheel_svg, render_synastry_grid_svg


def _inner():
    # Placidus-like inner (radix): unequal cusps, Ascendant at Leo 16°44' (136.727°).
    return {
        "house_system": "Placidus",
        "angles": {"asc": 136.727, "mc": 36.08},
        "cusps": [136.727, 157.59, 183.62, 216.08, 252.77, 287.40,
                  316.727, 337.59, 3.62, 36.08, 72.77, 107.40],
        "bodies": {
            "Sun": {"lon": 10.0, "retro": False},
            "Moon": {"lon": 200.0, "retro": False},
            "Mercury": {"lon": 15.0, "retro": True},
            "Venus": {"lon": 340.0, "retro": False},
            "Mars": {"lon": 120.0, "retro": False},
            "Jupiter": {"lon": 250.0, "retro": False},
            "Saturn": {"lon": 300.0, "retro": False},
        },
        "aspects": [
            {"a": "Sun", "b": "Mercury", "aspect": "conjunction", "orb": 5.0},
            {"a": "Mars", "b": "Jupiter", "aspect": "trine", "orb": 2.0},
        ],
    }


def _outer():
    # An untimed transit chart: bodies only, NO angles / cusps (must be tolerated).
    return {
        "angles": None,
        "cusps": None,
        "bodies": {
            "Sun": {"lon": 190.0, "retro": False},
            "Moon": {"lon": 40.0, "retro": False},
            "Mars": {"lon": 12.0, "retro": False},
            "Venus": {"lon": 100.0, "retro": True},
            "Jupiter": {"lon": 60.0, "retro": False},
        },
        "aspects": [
            {"a": "Sun", "b": "Venus", "aspect": "square", "orb": 3.0},
        ],
    }


def _cross():
    # a = inner body, b = outer body (the shape openephem's cross_aspects returns).
    return [
        {"a": "Sun", "b": "Mars", "aspect": "conjunction", "orb": 2.0,
         "chart_a": "inner", "chart_b": "outer"},
        {"a": "Moon", "b": "Sun", "aspect": "conjunction", "orb": 4.0,
         "chart_a": "inner", "chart_b": "outer"},
        {"a": "Mars", "b": "Venus", "aspect": "opposition", "orb": 2.0,
         "chart_a": "inner", "chart_b": "outer"},
    ]


def _aspect_lines(svg):
    return svg.count('class="aspect"')


# ---- bi-wheel -------------------------------------------------------------

@pytest.mark.parametrize("theme", [*PALETTES, "auto"])
def test_biwheel_wellformed_every_theme(theme):
    svg = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross(), theme=theme)
    ET.fromstring(svg)                          # parses as XML -> well-formed


def test_biwheel_deterministic():
    a = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross(), theme="prism")
    b = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross(), theme="prism")
    assert a == b


def test_biwheel_default_draws_cross_only():
    svg = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross())
    assert _aspect_lines(svg) == 3          # three drawable cross-aspects, no intra layers


def test_biwheel_inner_layer_toggle():
    svg = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross(),
                             show_inner_aspects=True)
    assert _aspect_lines(svg) == 3 + 2      # cross + the inner chart's two intra-aspects


def test_biwheel_outer_layer_toggle():
    svg = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross(),
                             show_outer_aspects=True)
    assert _aspect_lines(svg) == 3 + 1      # cross + the outer chart's one intra-aspect


def test_biwheel_cross_can_be_disabled():
    svg = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross(),
                             show_cross_aspects=False,
                             show_inner_aspects=True, show_outer_aspects=True)
    assert _aspect_lines(svg) == 2 + 1      # only the two charts' own intra-aspects


def test_biwheel_both_rings_have_glyphs():
    svg = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross())
    # inner-only Saturn and outer-only Moon both appear -> both rings are drawn
    assert "♄" in svg and "☽" in svg
    assert svg.count('class="planet"') == 7 + 5


def test_biwheel_tolerates_untimed_outer():
    # outer has angles=None/cusps=None; must not raise
    render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross())


def test_biwheel_requires_inner_bodies():
    with pytest.raises(ValueError):
        render_biwheel_svg({"bodies": {}}, _outer(), cross_aspects=_cross())


def test_biwheel_optional_key():
    plain = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross())
    keyed = render_biwheel_svg(_inner(), _outer(), cross_aspects=_cross(),
                               key=True, labels=("Natal", "Transit"))
    assert "Natal" not in plain
    assert "Natal" in keyed and "Transit" in keyed


# ---- synastry grid --------------------------------------------------------

@pytest.mark.parametrize("theme", [*PALETTES, "auto"])
def test_synastry_grid_wellformed_every_theme(theme):
    svg = render_synastry_grid_svg(_inner(), _outer(), _cross(), theme=theme)
    ET.fromstring(svg)


def test_synastry_grid_deterministic():
    a = render_synastry_grid_svg(_inner(), _outer(), _cross(), theme="light")
    b = render_synastry_grid_svg(_inner(), _outer(), _cross(), theme="light")
    assert a == b


def test_synastry_grid_shows_aspect_symbols_and_labels():
    svg = render_synastry_grid_svg(_inner(), _outer(), _cross(),
                                   labels=("Natal", "Transit"))
    assert "☌" in svg and "☍" in svg        # conjunction + opposition from the cross list
    assert "Natal" in svg and "Transit" in svg


def test_synastry_grid_empty_cross_is_wellformed():
    svg = render_synastry_grid_svg(_inner(), _outer(), [])
    ET.fromstring(svg)
