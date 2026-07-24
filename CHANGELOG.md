# Changelog

All notable changes to **ephemvis** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-07-24

Initial public release — themeable SVG rendering for openephem chart data.

### Rendering
- `render_svg` — the natal chart wheel: zodiac ring, house cusps & numbers, planet
  glyphs with radial de-collision + dotted leader lines, and aspect lines.
- `render_aspect_grid_svg` — the triangular aspectarian: a clean square grid with a
  themed gradient on the frame and separators.
- 12 selectable themes, including the **infrared / ultraviolet** spectral pair, each
  with a per-theme prism-halo sweep.
- Hover tooltips via SVG `<title>`: body name / sign / degree, aspect significance,
  sign → house (rising-aware), and Asc / MC.

### Design & quality
- **Zero runtime dependencies**; engine-agnostic — renders any dict with the
  openephem `ChartResult` shape. The optional `[compute]` extra pulls openephem so
  you can compute and render in one line.
- MIT-licensed.
- CI gates: pytest + **SVG snapshot tests** (byte-stable across Linux/Windows) +
  ruff + mypy, on Python 3.10–3.13.

[0.1.0]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.1.0
