# ephemvis

Themeable **SVG rendering** for astrological chart data — the display layer that
pairs with [openephem](../oracle) (the calculation core). ephemvis turns a chart
dict into a self-contained chart **wheel** and a triangular **aspect grid**.

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
