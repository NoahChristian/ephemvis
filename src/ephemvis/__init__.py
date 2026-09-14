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

__version__ = "0.2.5"

from . import (  # noqa: F401
    aspectgrid,
    decennials,
    firdaria,
    profection_wheel,
    vedic_chart,
    vimshottari,
    wheel,
    zodiacal_releasing,
)
from .aspectgrid import render_aspect_grid_svg  # noqa: F401
from .decennials import render_decennials_svg  # noqa: F401
from .firdaria import render_firdaria_svg  # noqa: F401
from .profection_wheel import render_profection_wheel_svg  # noqa: F401
from .vedic_chart import render_vedic_square_svg  # noqa: F401
from .vimshottari import render_vimshottari_svg  # noqa: F401
from .wheel import PALETTES, render_svg  # noqa: F401
from .zodiacal_releasing import render_zodiacal_releasing_svg  # noqa: F401

__all__ = [
    "__version__", "render_svg", "render_aspect_grid_svg",
    "render_profection_wheel_svg", "render_firdaria_svg",
    "render_zodiacal_releasing_svg", "render_decennials_svg",
    "render_vimshottari_svg", "render_vedic_square_svg", "PALETTES",
    "wheel", "aspectgrid", "profection_wheel", "firdaria", "zodiacal_releasing",
    "decennials", "vimshottari", "vedic_chart",
]
