# Changelog

All notable changes to **ephemvis** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-09-11

Time-lord renderers (annual profections, firdaria, zodiacal releasing, decennials)
and a natal-wheel profection overlay, plus a scaling fix that was latent since 0.1.0.
Purely additive to the public API — every 0.1.0 call still works.

### Fixed
- **Natal-wheel scaling (bug since 0.1.0).** `render_svg`'s glyph/label fonts and line
  weights were hardcoded in pixels while the wheel geometry (radii, the glyph de-collision
  offsets) scaled with `size` — so at any `size` below the ~760 they were tuned for, the
  glyphs bloated relative to the wheel and the size-scaled label offsets shrank. The fonts
  and stroke widths now scale with `size`, so the wheel keeps the same proportions at every
  size (the 760 line weights are unchanged; a chart rendered at 600 or 900 now looks like the
  same chart, not a differently-balanced one).
- **Degree-label / glyph collisions in the natal wheel.** As a consequence of the above (and
  slightly too-large font proportions), a wide retrograde degree label such as `2°℞` could
  overlap its own planet glyph on the flanks of the wheel — most visible for the lunar nodes.
  The font proportions were nudged down so wide `℞` labels clear their glyph at every size.
### Added
- **Decennials "chart" style** — `render_decennials_svg(chart, style="chart")` rolls the
  decennial timeline onto the annual-profection wheel: the age annuli become the decennial
  Gantt, each ring band coloured by its **major** lord with the **sub**-lord glyph per year
  and radial ticks at the real sub-period boundaries (`sub_style="ticks"` default, or
  `"gradient"` for sub-lord colour slices). Each year cell shows the sub-period that covers
  most of that year (every sub-period claims its peak-coverage year), so a short sub-period —
  a Venus sub is only ~8 months — always keeps its glyph instead of dropping out when no
  birthday happens to land inside it. Each cell's number+glyph also carries a knockout halo in
  its band colour, so a sub-period tick breaks cleanly around the text instead of merging with a
  white glyph on a dark band. A solitary age 6 or 9 is underlined, since a single digit is
  ambiguous under the cell rotation (a rotated 6 reads as a 9). Needs a `profections` block alongside the
  `decennials` one. Built on a reusable `timelord=` overlay added to
  `render_profection_wheel_svg` (which stays byte-for-byte the same by default), plus a
  shared `theme_lord_colors()` helper deriving the lord palette from each theme's ramp
  (hue farthest-point + lightness stagger) so wheel and timeline colour the lords
  identically per theme.
- **Timeline polish** — the horizontal `render_decennials_svg` timeline now uses the same
  theme-derived lord colours, tiles the ~75¼-year cycle across the whole axis, prints the
  as-of date by the current-age marker, shows "Name (glyph)" legends, and draws the
  current major/sub outlines as a top overlay so nothing clips them.
- **Consistent timeline chrome** — `render_firdaria_svg` and `render_zodiacal_releasing_svg`
  now match that decennials timeline spec: the as-of date printed by the current-age marker
  (which tracks the real fractional age), larger subtitle / age-axis / legend type, a clear gap
  before the legend, and "Name (glyph)" legends — the seven planets + two nodes for firdaria,
  and each element with its three sign glyphs (`Fire (♈ ♌ ♐)` …) for releasing. Both also take
  the shared theme-derived colours — firdaria's seven planets and releasing's four elements now
  come off each theme's ramp (via `theme_lord_colors`), so the whole suite recolours together per
  theme; the sign/planet glyph stays the primary identifier.

- **`render_decennials_svg()`** — Valens' decennial time-lords as a horizontal timeline:
  a top row of the general decennial periods (each a fixed 10 years 9 months) and a bottom
  row of their planetary sub-periods (unequal — each planet's minor years as months, so
  they are positioned by date), coloured and glyphed by ruling planet, with the current
  general/sub lord outlined and an age marker that tracks the actual as-of date. The
  starting planet is named in the subtitle. All palettes; `max_age`/`title` params. Needs a
  `decennials` block (openephem's `assemble(..., decennials_as_of=)`).
- **`render_zodiacal_releasing_svg()`** — Valens' zodiacal releasing as a horizontal
  timeline of nested periods: a top row of level-1 (L1) periods and a bottom row of their
  level-2 (L2) sub-periods. Each band is coloured by the **element** of its sign
  (Fire/Earth/Air/Water) in theme-derived colours off the palette's ramp, and carries the sign
  glyph as the primary identifier. Each period's **angularity** from the Lot shows as a top
  accent bar — a solid ink bar for *angular* (a peak), a two-colour *dotted* bar (ink + a light
  tone, legible on the dark Earth/Water bands) for *succedent*, nothing for *cadent* — and a
  **Loosing-of-the-Bond** jump is marked where it occurs, its weight tracking
  its depth: an L1 loosing is the deepest, rarest cut (a full L1 circuit ≈ 211 yr, so it shows
  only in extended horizons) and an L2 loosing (≈17½ yr into a long chapter) is the one that
  actually punctuates a life. The current L1 period is outlined with an age marker. The Lot
  released and the active L1→L4 path are named in the subtitle. Themed from the palettes;
  `max_age`/`title` params. Needs a `zodiacal_releasing` block (openephem's
  `assemble(..., releasing_as_of=)`).
- **`render_firdaria_svg()`** — the Persian firdaria time-lords as a horizontal timeline:
  a top row of major planetary periods and a bottom row of their sub-periods, coloured and
  glyphed by ruling planet, with the current major/sub outlined and an age marker. The seven
  classical planets take the shared **theme-derived** lord colours (`theme_lord_colors`, same
  Chaldean order as the decennials timeline/chart), so a planet reads the same colour across
  every renderer and the suite recolours together per theme; the two lunar nodes keep fixed
  identity colours. `max_age`/`title` params. (Planet identity is the glyph; colour is a
  supporting cue — nine categories can't all be maximally distinct.)
- **`render_profection_wheel_svg()`** — a dedicated whole-sign annual-profection wheel:
  twelve house wedges with the natal planets in their houses, the
  signs on the rim, and concentric age rings (each house lists the ages that profect
  there). The profected house + sign are highlighted for the chart's age; the age cells
  are a heatmap keyed to age along the theme's ramp (thermal in `infrared`, black-light
  in `ultraviolet`), with radial numbers (2nd–6th flipped upright). A solitary age 6 or 9 is
  underlined, since a single digit is ambiguous under the cell rotation (a rotated 6 reads as a
  9) — the same treatment the decennials chart uses, from a shared helper so the two wheels never
  diverge. Params: `theme` (all palettes), `max_age` (final year; the outer ring is always
  completed), `title`, `planets` (`'classical'` / `'all'` / a list), `size`.
- **Profection overlay** on the wheel: when the chart dict carries a `profections`
  block, `render_svg` draws a filled band on the annual profected sign and rings the
  Lord of the Year's glyph (tagged **TL**), then spells the cadences out in a
  bottom-left **key** — an eyebrow, `Lord: <lord> · <sign> rising` (as on the dedicated
  profection wheel), and the as-of date with each component tagged by the sign it
  profects to (`June ♊ · 3rd ♐ · 2030 ♒`: month→Lord of the Month's sign,
  day→Lord of the Day's, year→the annual sign). This replaces the earlier month/day
  **arcs**, which crossed straight through the sign glyphs and read as meaningless
  lines to anyone not already tracking the technique. All in the theme accent
  (light/dark + eight pastel themes, with a dark-mode override), with hover tooltips.
  The `show_profection=True` parameter suppresses the whole overlay. Snapshots
  regenerated (only the `.prof-*` CSS rules changed).

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

[0.2.0]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.2.0
[0.1.0]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.1.0
