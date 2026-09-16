"""Snapshot tests — lock the exact SVG output so rendering can't silently regress.

ephemvis is engine-agnostic (it renders a plain chart dict), so these run fully
offline with a fixed fixture — no ephemeris, no network — which is what lets them
live in CI. The snapshot captures the whole SVG, including every <title> tooltip,
so body_label / sign_label / angle_label and the theme gradients/halo are all
covered.

Regenerate after an *intended* rendering change:

    UPDATE_SNAPSHOTS=1 python -m pytest ephemvis/tests/test_snapshots.py

then review the diff before committing the updated snapshots.
"""
import os
import pathlib
import re

import pytest

from ephemvis import (
    render_aspect_grid_svg,
    render_biwheel_svg,
    render_svg,
    render_synastry_grid_svg,
)
from ephemvis.wheel import PALETTES

SNAP = pathlib.Path(__file__).parent / "snapshots"
# baseline (no halo) / halo+gradient / dark + halo-rotation + grid-reverse:
SNAP_THEMES = ["light", "prism", "infrared"]

# A deterministic, hand-built ChartResult (no ephemeris needed). Bodies are placed
# to exercise the tricky paths: Chiron sits next to the Moon (radial de-collision),
# several retrogrades, a fixed star (the ✦ marker), whole-sign cusps + angles (so
# the sign→house and Asc/MC tooltips resolve), and a spread of aspect natures.
SAMPLE_CHART = {
    "zodiac": "tropical",
    "angles": {"asc": 95.4, "mc": 5.2, "vertex": 250.1, "east_point": 100.3, "coasc": 280.6},
    "cusps": [90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0],
    "bodies": {
        "Sun":      {"lon": 145.32, "sign": "Leo", "deg_in_sign": 25.32, "retro": False, "speed": 0.96},
        "Moon":     {"lon": 5.51, "sign": "Aries", "deg_in_sign": 5.51, "retro": False, "speed": 13.1},
        "Mercury":  {"lon": 160.20, "sign": "Virgo", "deg_in_sign": 10.20, "retro": True, "speed": -0.4},
        "Venus":    {"lon": 130.85, "sign": "Leo", "deg_in_sign": 10.85, "retro": False, "speed": 1.1},
        "Mars":     {"lon": 200.44, "sign": "Libra", "deg_in_sign": 20.44, "retro": False, "speed": 0.6},
        "Jupiter":  {"lon": 285.11, "sign": "Capricorn", "deg_in_sign": 15.11, "retro": True, "speed": -0.08},
        "Saturn":   {"lon": 310.73, "sign": "Aquarius", "deg_in_sign": 10.73, "retro": False, "speed": 0.11},
        "Uranus":   {"lon": 35.20, "sign": "Taurus", "deg_in_sign": 5.20, "retro": False, "speed": 0.05},
        "Neptune":  {"lon": 350.92, "sign": "Pisces", "deg_in_sign": 20.92, "retro": True, "speed": -0.02},
        "Pluto":    {"lon": 275.63, "sign": "Capricorn", "deg_in_sign": 5.63, "retro": True, "speed": -0.01},
        "TrueNode": {"lon": 55.00, "sign": "Taurus", "deg_in_sign": 25.00, "retro": True, "speed": -0.05},
        "Chiron":   {"lon": 8.10, "sign": "Aries", "deg_in_sign": 8.10, "retro": False, "speed": 0.03},
        "Regulus":  {"lon": 149.90, "sign": "Leo", "deg_in_sign": 29.90, "kind": "star"},
    },
    "aspects": [
        {"a": "Sun", "b": "Venus", "aspect": "conjunction", "angle": 0.0, "orb": -1.53, "applying": True},
        {"a": "Sun", "b": "Saturn", "aspect": "sextile", "angle": 60.0, "orb": 0.59, "applying": False},
        {"a": "Moon", "b": "Mars", "aspect": "quincunx", "angle": 150.0, "orb": -0.07, "applying": True},
        {"a": "Mercury", "b": "Neptune", "aspect": "opposition", "angle": 180.0, "orb": 1.28, "applying": False},
        {"a": "Venus", "b": "Jupiter", "aspect": "trine", "angle": 120.0, "orb": -1.74, "applying": True},
        {"a": "Mars", "b": "Pluto", "aspect": "square", "angle": 90.0, "orb": 0.81, "applying": False},
        {"a": "Jupiter", "b": "Saturn", "aspect": "semisextile", "angle": 30.0, "orb": -0.62, "applying": True},
        {"a": "Sun", "b": "Moon", "aspect": "trine", "angle": 120.0, "orb": 0.19, "applying": True},
    ],
    "warnings": [],
}


# A second chart for the bi-wheel / synastry snapshots: an UNTIMED transit
# (angles=None, cusps=None — must be tolerated), placed against SAMPLE_CHART's houses.
SAMPLE_OUTER = {
    "zodiac": "tropical",
    "angles": None,
    "cusps": None,
    "bodies": {
        "Sun":      {"lon": 172.6, "sign": "Virgo", "deg_in_sign": 22.6, "retro": False},
        "Moon":     {"lon": 44.2, "sign": "Taurus", "deg_in_sign": 14.2, "retro": False},
        "Mercury":  {"lon": 158.0, "sign": "Virgo", "deg_in_sign": 8.0, "retro": True},
        "Venus":    {"lon": 100.4, "sign": "Cancer", "deg_in_sign": 10.4, "retro": False},
        "Mars":     {"lon": 12.9, "sign": "Aries", "deg_in_sign": 12.9, "retro": False},
        "Jupiter":  {"lon": 62.1, "sign": "Gemini", "deg_in_sign": 2.1, "retro": False},
        "Saturn":   {"lon": 4.6, "sign": "Aries", "deg_in_sign": 4.6, "retro": False},
        "Uranus":   {"lon": 65.3, "sign": "Gemini", "deg_in_sign": 5.3, "retro": True},
        "Neptune":  {"lon": 2.5, "sign": "Aries", "deg_in_sign": 2.5, "retro": True},
        "Pluto":    {"lon": 303.1, "sign": "Aquarius", "deg_in_sign": 3.1, "retro": True},
    },
    "aspects": [
        {"a": "Sun", "b": "Mercury", "aspect": "conjunction", "angle": 0.0, "orb": -0.6, "applying": True},
        {"a": "Mars", "b": "Uranus", "aspect": "opposition", "angle": 180.0, "orb": -0.4, "applying": False},
    ],
    "warnings": [],
}

# Hand-written cross-aspects (a = SAMPLE_CHART body, b = SAMPLE_OUTER body), a spread
# of natures so the aspect-line / cell colouring is all exercised.
SAMPLE_CROSS = [
    {"a": "Sun", "b": "Mercury", "aspect": "trine", "orb": 1.7, "chart_a": "inner", "chart_b": "outer"},
    {"a": "Moon", "b": "Mars", "aspect": "conjunction", "orb": 2.6, "chart_a": "inner", "chart_b": "outer"},
    {"a": "Venus", "b": "Venus", "aspect": "square", "orb": 0.5, "chart_a": "inner", "chart_b": "outer"},
    {"a": "Mars", "b": "Pluto", "aspect": "opposition", "orb": 2.7, "chart_a": "inner", "chart_b": "outer"},
    {"a": "Saturn", "b": "Uranus", "aspect": "sextile", "orb": 4.6, "chart_a": "inner", "chart_b": "outer"},
]


# Every renderer now embeds the OFL fonts as `@font-face` rules carrying big constant base64
# woff2 blobs (from _fontdata, via astroglyphs_2K). Baking those into the snapshots would bloat
# them and couple every snapshot to the font binary, so we strip the `@font-face` rules — and any
# `<style>` left empty by that — before both writing and comparing. The family *references* on
# the elements (and the theme-class `<style>`) stay, so a font-routing regression still shows up.
_FONTFACE = re.compile(r"@font-face\{[^}]*\}")


def _strip_fonts(s):
    return _FONTFACE.sub("", s).replace("<style></style>", "")


def _check(name, content):
    content = _strip_fonts(content)
    f = SNAP / name
    if os.environ.get("UPDATE_SNAPSHOTS"):
        SNAP.mkdir(exist_ok=True)
        f.write_text(content, encoding="utf-8", newline="\n")
        pytest.skip(f"updated snapshot {name}")
    assert f.exists(), f"missing snapshot {name} — run `UPDATE_SNAPSHOTS=1 pytest` to create it"
    assert content == _strip_fonts(f.read_text(encoding="utf-8")), (
        f"{name} differs from its snapshot. If the rendering change is intended, "
        f"regenerate with `UPDATE_SNAPSHOTS=1 pytest` and review the diff.")


@pytest.mark.parametrize("theme", SNAP_THEMES)
def test_wheel_snapshot(theme):
    _check("wheel_%s.svg" % theme,
           render_svg(SAMPLE_CHART, size=760, theme=theme, title="Sample"))


@pytest.mark.parametrize("theme", SNAP_THEMES)
def test_grid_snapshot(theme):
    _check("grid_%s.svg" % theme,
           render_aspect_grid_svg(SAMPLE_CHART, theme=theme, cell=30))


@pytest.mark.parametrize("theme", SNAP_THEMES)
def test_biwheel_snapshot(theme):
    # all three aspect layers + key, to lock every draw path in one file
    _check("biwheel_%s.svg" % theme,
           render_biwheel_svg(SAMPLE_CHART, SAMPLE_OUTER, cross_aspects=SAMPLE_CROSS,
                              size=760, theme=theme, title="Sample", key=True,
                              labels=("Natal", "Transit"),
                              show_inner_aspects=True, show_outer_aspects=True))


@pytest.mark.parametrize("theme", SNAP_THEMES)
def test_synastry_grid_snapshot(theme):
    _check("synastry_%s.svg" % theme,
           render_synastry_grid_svg(SAMPLE_CHART, SAMPLE_OUTER, SAMPLE_CROSS,
                                    theme=theme, labels=("Natal", "Transit")))


def test_every_theme_renders():
    """Guard against a new/renamed palette breaking either renderer."""
    for theme in PALETTES:
        assert render_svg(SAMPLE_CHART, theme=theme).startswith("<svg")
        assert render_aspect_grid_svg(SAMPLE_CHART, theme=theme).startswith("<svg")


def test_snapshot_is_stable():
    """Two renders of the same input must be byte-identical (determinism)."""
    a = render_svg(SAMPLE_CHART, theme="prism")
    b = render_svg(SAMPLE_CHART, theme="prism")
    assert a == b
    assert render_aspect_grid_svg(SAMPLE_CHART, theme="prism") == \
        render_aspect_grid_svg(SAMPLE_CHART, theme="prism")
