# Changelog

All notable changes to **ephemvis** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **`render_svg(..., show_aspects=True)`** - the single wheel's aspect lines can now be
  switched off, matching `show_profection` beside it and the bi-wheel's three
  `show_*_aspects` switches. The single wheel was the only renderer whose aspect layer
  could not be suppressed, which left callers emptying `chart["aspects"]` to get an
  uncluttered wheel - a workaround that conflates "no aspects were computed" with "do
  not draw them", and misinforms anything else reading that key off the same dict.
  Defaults to `True`, so existing output is unchanged.

## [0.5.0] — 2026-09-15

### Added
- **Embedded OFL glyph fonts — deterministic rendering everywhere.** Every SVG now inlines
  its astrology glyphs *and* numerals/labels as `@font-face` data URIs, so a chart renders
  pixel-identical on any device instead of falling back to whatever symbol font the viewer
  has. The glyphs are a curated subset of the OFL **Noto** fonts, packaged by the new sibling
  toolkit [`astroglyphs_2K`](https://github.com/NoahChristian/astroglyphs_2K) and vendored into
  `ephemvis/_fontdata.py` at build time — ephemvis keeps **zero runtime dependencies**. Font
  data is SIL Open Font License 1.1 (`NOTICE`, `LICENSES/OFL.txt`); the code stays MIT. Toggle
  with `ephemvis.wheel.EMBED_FONTS`.
- **Bi-wheel (double wheel)** — `render_biwheel_svg(inner, outer, …)` overlays two charts
  on one wheel for comparison (natal + transit, two transits, synastry, returns,
  progressions). The inner chart (radix) owns the zodiac ring, house cusps and
  orientation; the outer chart's planets are placed against it on a second band, with a
  shared divider ring between the two bands (the bands sit symmetric about it and every
  planet's short true-position tick points to it). Both rings carry the full readout
  (glyph · degree · sign · minute) in the same order; house dividers run out through both
  rings. Three switchable aspect layers cross the hub — cross-aspects (inner × outer,
  bold, on by default) plus each chart's own internal aspects (faint, off by default).
  The outer chart may be an untimed transit (no houses of its own). The renderer only
  draws: cross-aspects are supplied as data (openephem 0.3.0's `cross_aspects()`).
- **Synastry grid** — `render_synastry_grid_svg(inner, outer, cross, …)`, a rectangular
  cross-aspect matrix (inner bodies down, outer across), coloured by aspect nature, with
  a gradient folded inward from both corners — two triangular aspectarians folded into
  one rectangle. The companion tabular view to the bi-wheel.
- **Bi-wheel spacing from real glyph metrics.** The bi-wheel's per-glyph readout clearance
  and token widths now come from the embedded font's measured ink bounding boxes and advance
  widths (`_fontdata.GLYPH_METRICS`) instead of hand-tuned heuristics, so tall glyphs
  (Saturn/Uranus) reserve exactly the room they need and short ones (the lunar nodes) don't
  waste it — closing the glyph-vs-readout overlap on the crowded double wheel.

## [0.3.2] — 2026-09-14

### Added
- **Intercepted signs shown on unequal house wheels.** In a quadrant/unequal chart (Placidus,
  Koch, Campanus, Regiomontanus, Porphyry) a sign can hold no house cusp — it falls entirely
  inside one house while its opposite sign holds two. `render_svg` now draws each such
  intercepted sign faded at its zodiacal midpoint, between its two neighbouring cusp signs (no
  degree readout, since it owns no cusp), with an "…intercepted (no house cusp)" tooltip.
  Detected from the cusp data, not a house-system name list, so whole-sign and equal charts —
  which always place exactly one cusp per sign — are unaffected.

## [0.3.1] — 2026-09-14

### Fixed
- **`render_vedic_square_svg` now refuses a tropical chart.** The rāśi square is a sidereal
  form and the renderer uses each longitude exactly as given, so passing a tropical chart
  produced a perfectly well-formed square that was wrong by the ayanamsa — ~24° in this era,
  nearly a whole sign, putting the Lagna and every graha in the neighbouring rāśi. The
  precondition was documented in the docstring but never checked; it now raises `ValueError`,
  consistent with the module's existing guards for a missing Ascendant and an unknown style.
  Charts carrying no `zodiac` key at all (another engine emitting the `ChartResult` shape)
  still render — only an explicitly non-sidereal chart is refused.

## [0.3.0] — 2026-09-14

**Jyotiṣa (Vedic) chart renderers** — the recognizably-Indian square rāśi charts and a
Vimśottarī daśā view — plus a **whole-sign natal wheel** reworked to traditional
orientation. Additive: the western renderers keep their APIs; the whole-sign changes affect
`render_svg`'s output for whole-sign and non-whole-sign house systems (see Changed).

### Added
- **Vedic square charts** — `render_vedic_square_svg(chart, style="south"|"north"|"east")`
  draws the classical rāśi square in all three regional styles (South Indian fixed-sign
  grid, North Indian fixed-house diamond, East Indian / Bengali fixed-house). Grahas placed
  by sidereal rāśi (Rāhu/Ketu included), Lagna marked, per-house adaptive scaling so dense
  stelliums stay inside their cells. Needs a sidereal chart (`assemble(zodiac="sidereal")`);
  renders any vārga (divisional) chart the same way when the chart carries a `varga` block.
- **Vimśottarī daśā** — `render_vimshottari_svg(chart, style="timeline"|"chart",
  layout="annulus"|"spiral")` draws the Moon-nakṣatra daśā as a dated timeline (Mahā + Antar
  rows, balance at birth, as-of marker) or projected onto the shared wheel core (band = Mahā,
  glyph = Antar) as concentric rings or an expanding coil. Nine grahas — the seven classical
  lords share the firdaria/decennials theme colours, Rāhu/Ketu their own. Needs a
  `vimshottari` block (openephem ≥ 0.2.0).

### Changed
- **Whole-sign natal wheel** (`render_svg`) now uses traditional orientation: the wheel is
  rotated to the house-1 cusp so the 12/1 division sits straight across the horizon, the
  Ascendant degree falling in its true place inside the first house. The equal outer-ring
  dividers are removed and each sign glyph sits on its house cusp; the Asc/MC move inside the
  planet band (keeping their label style) with a degree/sign/minute readout. Quadrant and
  equal charts are unaffected (their house-1 cusp already equals the Ascendant).
- **Non-whole-sign house systems** (Placidus, Koch, Campanus, Regiomontanus, Porphyry, Equal)
  now label each house cusp on the outer ring — the sign glyph on the cusp axis with the
  cusp's rounded degree / minute / second — instead of the equal whole-sign ring; the Asc/MC
  remain as outside guides. Detected from the cusp data, not a house-system name list.
- **Planet position readouts** on `render_svg` reworked: a radial degree / sign-glyph / minute
  block reading outward-to-inward along each spoke, retrograde shown in red, with rubber-band
  angular de-collision for crowded clusters. Degree/minute/second displays round (not
  truncate). Whole-sign wheel snapshots regenerated accordingly.

## [0.2.5] — 2026-09-11

An **expanding-spiral layout** for the time-lord charts, and **chart (wheel) projections
for firdaria and zodiacal releasing** — completing the set so every time-lord technique
draws on the one shared natal-chart core. Purely additive: every 0.2.0 call still works,
and the default `layout="annulus"` output is byte-for-byte unchanged.

### Added
- **Spiral layout** — `render_profection_wheel_svg(chart, layout="spiral")`, and the same
  `layout=` on the decennials / firdaria / zodiacal-releasing chart styles. Instead of
  concentric age rings, the years unroll into one continuous coil that winds outward from
  the centre, each 12-year cycle making one full turn so successive turns abut seamlessly.
  Because profections are exactly 12-periodic, each sign keeps the same angle on every turn,
  so the recurrence reads as aligned radial wedges of one colour. `layout="annulus"` (the
  concentric rings) stays the default and is byte-for-byte identical to before.
- **Firdaria chart style** — `render_firdaria_svg(chart, style="chart")` projects the
  firdaria sequence onto the annual-profection wheel (band = major lord, glyph = sub lord),
  the two nodes carried through with their own colours and glyphs. Needs a `profections`
  block alongside the `firdaria` one.
- **Zodiacal-releasing chart style** — `render_zodiacal_releasing_svg(chart, style="chart")`
  projects releasing onto the wheel, each cell coloured by its L1 sign's **element** and
  glyphed by its L2 sign. (Angularity, peak and loosing-of-the-bond markers remain on the
  horizontal timeline.) Needs a `profections` block alongside the `zodiacal_releasing` one.
- **Lord of the Year on the profection wheel** — the plain `render_profection_wheel_svg`
  now fills each sign's outer-ring arc with its Lord of the Year (domicile-ruler) colour and
  carries two stacked legends (the lord colours, then the age-heatmap gradient), while the
  coil/rings keep the age heatmap. Only the plain wheel is affected; time-lord overlays keep
  their neutral rim.

### Changed
- The time-lord footer legend now wraps to as many rows as the width needs, so the nine
  firdaria lords (with the node names) fit instead of running off the edge; a seven-lord
  legend still occupies one row unchanged.
- `glyphs_by_year` (the "one sub-lord glyph per year cell, no short sub dropped" helper) is
  now a shared function in `ephemvis.profection_wheel`, used by all three chart projections
  (previously private to decennials).

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

[0.5.0]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.5.0
[0.3.2]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.3.2
[0.3.1]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.3.1
[0.3.0]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.3.0
[0.2.5]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.2.5
[0.2.0]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.2.0
[0.1.0]: https://github.com/NoahChristian/ephemvis/releases/tag/v0.1.0
