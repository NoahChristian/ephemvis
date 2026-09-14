# ephemvis

[![CI](https://github.com/NoahChristian/ephemvis/actions/workflows/ci.yml/badge.svg)](https://github.com/NoahChristian/ephemvis/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ephemvis.svg)](https://pypi.org/project/ephemvis/)
[![Python](https://img.shields.io/pypi/pyversions/ephemvis.svg)](https://pypi.org/project/ephemvis/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Themeable **SVG rendering** for astrological chart data — the display layer that
pairs with [openephem](https://github.com/NoahChristian/openephem) (the calculation
core). ephemvis turns a chart dict into a self-contained chart **wheel** and a
triangular **aspect grid**.

The split is deliberate: **openephem computes, ephemvis draws.** The math core
stays small and auditable; the visuals can be forked and restyled freely without
touching (or destabilising) the calculations.

## Install

```bash
pip install ephemvis            # pure renderer, zero runtime deps
pip install ephemvis[compute]   # also pulls openephem to compute charts
```

## Use

```python
from openephem import resolve, assemble          # needs ephemvis[compute]
from ephemvis import render_svg, render_aspect_grid_svg

chart = assemble(resolve(date=(1990, 5, 15), time=(14, 30),
                         place="New York, NY"))
open("wheel.svg", "w", encoding="utf-8").write(render_svg(chart, theme="prism"))
open("grid.svg",  "w", encoding="utf-8").write(render_aspect_grid_svg(chart, theme="prism"))
```

`render_svg` and `render_aspect_grid_svg` accept any dict with the openephem
`ChartResult` shape (`angles`, `cusps`, `bodies`, `aspects`), so **any engine that
emits that shape can be rendered** — ephemvis has no dependency on how the chart
was computed.

## Profections

Two ways to show profections, both from a chart dict carrying a `profections` block
(openephem's `assemble()` adds one for a given age/date):

**A dedicated wheel** — `render_profection_wheel_svg(chart, theme=…)` draws the
whole-sign profection wheel: twelve house wedges
(ASC..12th) with the natal planets in their houses, the signs on the rim, and
concentric **age rings** (each house lists the ages that profect there — 0,12,24… in
the 1st, 1,13,25… in the 2nd, …). The profected house + sign are highlighted for the
chart's age, and the age cells are a **heatmap** keyed to age along the theme's ramp
(a thermal map of life in `infrared`, black-light in `ultraviolet`). Options:

```python
from ephemvis import render_profection_wheel_svg
svg = render_profection_wheel_svg(chart, theme="infrared", max_age=83,
                                  title="Annual Profections", planets="classical")
```

`max_age` sets the final year (the outer ring is always completed: 83 → seven rings
0–83, 84 → eight rings 0–95). `planets` is `"classical"` (default), `"all"`, or a
list of body names. `title` sets the top-left heading. Each sign's outer-ring arc is
tinted with its **Lord of the Year** (domicile-ruler) colour, with two stacked legends
below (the lord colours, then the age gradient).

Pass **`layout="spiral"`** to unroll the age rings into one continuous expanding coil
(birth at the centre, one 12-year turn per loop). Because profections are exactly
12-periodic, each sign holds the same angle on every turn, so the recurrence reads as
aligned radial wedges. `layout="annulus"` (concentric rings) is the default.

**An overlay on the natal wheel** — `render_svg` also marks the profection on the
ordinary chart in the theme accent: a filled **band** on the annual profected sign and
a ring tagged **TL** on the **Lord of the Year** glyph, each with a hover tooltip. A
bottom-left **key** names the annual lord and rising sign (`Lord: Mars · Aries rising`)
and, when the chart carries an as-of date, tags each part of that date with the sign it
profects to (`June ♊ · 3rd ♐ · 2030 ♒` — month → Lord of the Month's sign, day →
Lord of the Day's, year → the annual sign). Pass `show_profection=False` to suppress it.
All whole-sign, counted from the Ascendant.

## Firdaria

`render_firdaria_svg(chart, theme=…)` draws the Persian firdaria time-lords as a
horizontal **timeline** (they're a temporal sequence, not a wheel): a top row of major
planetary periods and a bottom row of their sub-periods, each segment coloured and
glyphed by its ruling planet, with the current major/sub outlined and a marker at the
current age. Needs a `firdaria` block (openephem's `assemble(..., firdaria_as_of=)`).

```python
from ephemvis import render_firdaria_svg
svg = render_firdaria_svg(chart, theme="dark", max_age=84, title="Firdaria")
```

`max_age` is the right edge (years). A companion table is trivially built from the same
`firdaria` block. Planet identity is carried by the glyph (nine categories can't all be
maximally distinct); colour is a supporting cue.

**Chart style** — `render_firdaria_svg(chart, style="chart")` projects the sequence onto
the profection wheel instead (band = major lord, glyph = sub lord; the two nodes carried
through), sharing the natal core with every other chart. Add `layout="spiral"` for the
coil. Needs a `profections` block alongside the `firdaria` one.

## Zodiacal Releasing

`render_zodiacal_releasing_svg(chart, theme=…)` draws Valens' zodiacal releasing as a
horizontal **timeline** of nested periods: a top row of level-1 (L1) periods and a bottom
row of their level-2 (L2) sub-periods. Each band is coloured by the **element** of its
sign (Fire/Earth/Air/Water — four categories separate cleanly for colour-vision
deficiency) and carries the sign's glyph as the primary identifier. Peak periods (angular
from the Lot of Fortune) get an ink accent bar; a Loosing-of-the-Bond jump is marked where
it occurs; the current L1 period is outlined with a marker at the current age. Needs a
`zodiacal_releasing` block (openephem's `assemble(..., releasing_as_of=)`).

```python
from ephemvis import render_zodiacal_releasing_svg
svg = render_zodiacal_releasing_svg(chart, theme="dark", max_age=84,
                                    title="Zodiacal Releasing")
```

`max_age` is the right edge (years). The Lot released (Fortune by default, or any of the
seven Hermetic Lots) and the active L1→L4 path are named in the subtitle; a companion
table is trivially built from the same block.

**Chart style** — `render_zodiacal_releasing_svg(chart, style="chart")` projects releasing
onto the profection wheel, each cell coloured by its L1 sign's element and glyphed by its
L2 sign (the angularity / peak / loosing-of-the-bond markers stay on the timeline). Add
`layout="spiral"` for the coil. Needs a `profections` block alongside the
`zodiacal_releasing` one.

## Decennials

`render_decennials_svg(chart, theme=…)` draws Valens' decennial time-lords as a horizontal
**timeline**: a top row of the general decennial periods (each a fixed 10 years 9 months)
and a bottom row of their planetary sub-periods (unequal — each planet's minor years as
months), coloured and glyphed by ruling planet, with the current general/sub lord outlined
and a marker at the current age. Needs a `decennials` block (openephem's `assemble(...,
decennials_as_of=)`).

```python
from ephemvis import render_decennials_svg
svg = render_decennials_svg(chart, theme="dark", max_age=76, title="Decennials")
```

`max_age` is the right edge (years; a full cycle is ~75¼). The starting planet is named in
the subtitle; a companion table is trivially built from the same block. Planet identity is
carried by the glyph; colour is a supporting cue.

**Chart style** — `render_decennials_svg(chart, style="chart")` rolls the decennial Gantt
onto the profection wheel (band = major lord, glyph = sub lord, radial ticks at the real
sub-period boundaries, or `sub_style="gradient"` for sub-lord colour slices). Add
`layout="spiral"` for the coil. Needs a `profections` block alongside the `decennials` one.

## Jyotiṣa (Vedic) charts

`render_vedic_square_svg(chart, style=…)` draws the classical **rāśi square** in three
regional styles — `"south"` (South Indian fixed-sign grid), `"north"` (North Indian
fixed-house diamond), and `"east"` (East Indian / Bengali fixed-house). Grahas are placed by
their sidereal rāśi (Rāhu/Ketu included), the Lagna is marked, and each house scales its
contents so a dense stellium stays inside its cell. Needs a **sidereal** chart
(`assemble(zodiac="sidereal")`); the same function renders any **vārga** (divisional) chart
when the chart carries a `varga` block (openephem's `varga_chart()`).

```python
from ephemvis import render_vedic_square_svg
svg = render_vedic_square_svg(chart, style="south", theme="meadow", title="Rāśi")
```

`render_vimshottari_svg(chart, style=…, layout=…)` draws the **Vimśottarī daśā** — either a
horizontal **timeline** (Mahādaśā over Antardaśā, the balance at birth, an as-of marker) or,
with `style="chart"`, projected onto the shared wheel core (band = Mahādaśā, glyph =
Antardaśā) as concentric rings (`layout="annulus"`) or an expanding coil (`layout="spiral"`).
The seven classical lords share the firdaria/decennials theme colours; Rāhu/Ketu carry their
own. Needs a `vimshottari` block (openephem ≥ 0.2.0's `assemble(..., vimshottari_as_of=)`).

```python
from ephemvis import render_vimshottari_svg
svg = render_vimshottari_svg(chart, style="chart", layout="spiral", theme="meadow")
```

## Themes

`light`, `dark`, `auto`, and eight pastel "pretty" modes with a prism-halo ring:
`prism`, `twilight`, `aurora`, `opal`, `seafoam`, `meadow`, `dawn`, `blossom`.
See `ephemvis.PALETTES`.

## The data contract

ephemvis reads the chart dict openephem's `assemble()` returns:

```python
{
  "angles": {"asc": float, "mc": float, ...} | None,   # ecliptic longitude, degrees
  "cusps":  [float] (12) | None,                        # house cusp longitudes
  "bodies": {name: {"lon": float, "retro": bool}},      # ecliptic longitude, degrees
  "aspects": [{"a": name, "b": name, "aspect": str, "orb": float}],
  "warnings": [str],
}
```

MIT © 2026 Elizabeth Huston, Ph.D. and Noah Christian, Ph.D.  
Contact: elpisastrology@gmail.com · elpisastrology.com and noahchristian@gmail.com
