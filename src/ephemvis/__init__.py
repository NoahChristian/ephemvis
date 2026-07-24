"""ephemvis — SVG chart rendering for openephem chart data.

Turns a chart dict (the shape openephem's ``assemble()`` returns — ``angles``,
``cusps``, ``bodies``, ``aspects``) into self-contained, themeable SVG: a chart
wheel and a triangular aspect grid. The renderers take a plain dict and have no
runtime dependencies, so any engine that emits the same shape can be rendered.

Quick start:
    from openephem import resolve, assemble   # optional: `pip install ephemvis[compute]`
    from ephemvis import render_svg, render_aspect_grid_svg
    chart = assemble(resolve(date=(1990, 5, 15), time=(14, 30), place="New York, NY"))
    wheel_svg = render_svg(chart, theme="prism")
    grid_svg  = render_aspect_grid_svg(chart, theme="prism")

Themes: 'light', 'dark', 'auto', and the pastel modes 'prism', 'twilight',
'aurora', 'opal', 'seafoam', 'meadow', 'dawn', 'blossom' (see PALETTES).
"""

__version__ = "0.1.0"

from . import aspectgrid, wheel  # noqa: F401
from .aspectgrid import render_aspect_grid_svg  # noqa: F401
from .wheel import PALETTES, render_svg  # noqa: F401

__all__ = [
    "__version__", "render_svg", "render_aspect_grid_svg", "PALETTES",
    "wheel", "aspectgrid",
]
