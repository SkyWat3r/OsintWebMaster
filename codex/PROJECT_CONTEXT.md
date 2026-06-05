# OSINT OSM App Context

This project is a local OpenStreetMap OSINT explorer.

Current architecture:
- `main.py`: small entrypoint only.
- `osint_app/app.py`: Tkinter control window, loading/fetching data, local server lifecycle.
- `osint_app/osm.py`: Overpass query, OSM JSON loading, tag classification, map payload generation.
- `osint_app/pattern.py`: road graph indexing and drawn road-shape matching.
- `osint_app/web.py`: localhost HTTP server, embedded Leaflet frontend, browser helpers, HTML export.
- `osint_app/config.py`: constants, road colors, point-layer definitions.

Runtime flow:
1. `python main.py` starts the Tkinter controller.
2. The controller starts a local server on `127.0.0.1:8765` or nearby.
3. The web frontend calls `/api/map-data`.
4. The API uses already-loaded data or auto-loads `osm_data.json` if available.
5. Overpass is only called when the user clicks `Fetch OSM data`.
6. Pattern search calls `/api/pattern-search` with drawn strokes or explicit graph points/edges, road-type filters, and rotation options.

Important behavior to preserve:
- Do not re-fetch Overpass data when `osm_data.json` is already usable.
- `Open Map` should open/copy the localhost URL, not generate a beige Tkinter canvas map.
- The web map must use real OSM tiles through Leaflet.
- Point filters are classified by OSM tags. Gates are `barrier=gate/lift_gate/swing_gate/...` and use the `▥` symbol.
- Google Maps links are generated client-side from feature coordinates.
- Pattern search compares drawn road shapes. Photo import is only a drawing background, not automatic image analysis.
- The canvas supports freehand drawing and an `Angle points` mode similar to a pen/polyline tool.
- `Angle points` lets the user click route vertices manually, then `Finish line` starts a separate stroke.
- In `Angle points`, existing vertices can be selected/dragged, `Delete point` removes the selected vertex, and the status text shows adjacent segment length percentages and angles.
- `Add midpoint`, `Smooth curve`, and `Straight corners` provide a lightweight vector-editor workflow for rounded roads without changing the API payload shape.
- Smoothed strokes are rendered as quadratic curves and sampled into denser point lists before `/api/pattern-search`.
- The UI no longer shows old black graph points during normal freehand drawing. Points still exist internally to encode strokes.
- The pattern canvas stores normalized coordinates and uses a fixed internal 340:230 drawing viewport, so `Large drawing` should not stretch the trace.
- `/api/pattern-search` accepts `strokes`, `roadGroups`, `rotationInvariant`, and `rotationStep`.
- `/api/pattern-search` also accepts graph-style `points` + `edges`. The frontend `Intersection` option uses this to force intersection/branch-angle matching instead of stroke/road-window matching.
- Road group filters are available for pattern matching: roads, highways, paths/tracks, and service roads.
- Search results are ranked in a `Best matches` panel. Clicking a result zooms the map, highlights candidate paths, shows the score, and displays a Google Maps link with coordinates at the bottom of the window.
- `Export search` downloads a JSON payload with normalized/smoothed strokes, road-group filters, rotation mode, ranked matches, selected match, paths, and metrics. Use these exports for calibration when the user identifies the correct match.
- Current pattern engine has three modes:
  - `road-layer-window`: used first for current stroke-based UI input. Matches drawn strokes against the same OSM highway ways displayed in the Leaflet road layer, including sliding windows over long roads.
  - `network-patch`: used for current stroke-based UI input. Compares all drawn strokes globally against normalized local OSM road-network patches.
  - `linear-trace`: fallback for old single continuous point/edge drawings.
  - `intersection`: branch-angle matching for graph-style drawings. The web UI can now force this mode via the `Intersection` checkbox; it converts drawn strokes into branches around a detected center, then compares OSM intersection branch counts and angle gaps.
- `road-layer-window` results have `source: visible-road` and their `paths` are actual OSM road-line windows that can be highlighted on the map.
- `road-layer-window` metrics include `patchPenalty`, `bearingTracePenalty`, `shapePenalty`, `pathLengthMeters`, `windowPoints`, `querySegments`, and `matcher`.
- Calibration exports are kept locally under `tests/` and ignored by Git. Filenames can indicate the correct result rank, e.g. `number5.json`; `not_found.json` means the correct route was absent from the ranked list.
- Calibration from `tests/number5.json` and `tests/numer12.json` added visible-road result dedupe by OSM way id, long/short window length penalties, cheaper sampling, and reduced fallback priority.
- Measured calibration result after this pass: `number5` correct match moved from rank 5 to rank 3; `numer12` moved from rank 12 to rank 9; `not_found` remained not found.
- Calibration from `tests/pattern-search-didnt-found.json` plus `tests/selected-road-compare-2026-06-05T12-22-30-624Z.json` showed the correct route was present and tested but ranked too low because nearest-segment patch scoring was too permissive for simple curves.
- `road-layer-window` now adds a bearing trace comparison for single-stroke route drawings. It samples successive travel directions along the drawing and OSM road window, tests allowed rotations and reversed OSM direction, then uses the better of patch penalty and bearing-trace penalty as `shapePenalty`.
- Measured calibration result for that case: selected OSM way `1309093058` moved from absent in top results to rank 1 at 93.8%.
- `network-patch` metrics include `patchPenalty`, `strokeCountPenalty`, `candidateDegree`, and `matcher`.
- `network-patch` normalizes query and candidate patches by translation/scale, tests coarse rotations when `Free rotation` is enabled, then scores with bidirectional nearest-segment distance.
- Patch search is prefiltered by road group, branch count, and coarse stroke/candidate angles before running the heavier geometric score.
- `Free rotation` compares relative branch angles so the pattern does not need to be north-aligned.
- The web UI has a `Full map` mode that hides the control panel until the user reopens it.
- The web UI has a visual `Rotate map` mode with a 0-359 degree slider, numeric input, and `Drag rotate` toggle. It rotates Leaflet map panes around the center for visual alignment/tracing, but OSM coordinates and backend searches remain unrotated.
- Map rotation increases tile/canvas render buffer and runs a symmetric overscan pan refresh to reduce blank corners after rotating. It is still a visual Leaflet workaround, not a native rotated-map projection.
- Rotation must be applied to Leaflet's whole `mapPane` while preserving Leaflet's own translate transform; rotating individual panes made rotation originate from the top-left and caused bad zoom behavior.
- `Map tools` includes a GPS jump field accepting `lat, lon`, a `Go` button, and a marker popup with a Google Maps link.
- Fetching data stores `_fetch_area` (`lat`, `lon`, `radius`) in memory and in saved JSON if the user saves after fetch. `build_map_payload()` exposes this as `fetchArea`.
- `Show border` is a visual-only circle for `fetchArea`, not a data limiter. `Set border` lets the user manually set a visual circle from the GPS field plus radius input.
- The main `OSM Pattern Explorer` panel is organized into collapsible sections: `Map tools`, `Filters`, `Road search`, and `Selection details`. Keep future controls inside the relevant section instead of adding loose buttons at the top level.
- Point filters are grouped by `POINT_KINDS[*].group`; the first dedicated group is `Signs` for stop/give-way/crossing/traffic-sign/traffic-calming style OSM nodes. Filter and marker icons can use Mapbox Maki SVG names via the `maki` field.
- `Nearby match` finds clusters of selected point kinds and/or text searches within a radius. Text terms are split on comma, plus sign, or newline (for example `boucherie + presse`). The `At least` value counts all selected criteria; users should uncheck point-kind criteria if they want text-only matching.
- Nearby matching starts from the rarest criterion in each combination and uses a simple spatial grid plus OSM point IDs for dedupe.
- `build_map_payload()` no longer has the old 10000 point cap; do not reintroduce arbitrary point skipping without a measured performance reason.
- Map road/area/point layers start unchecked; `Check all` and `Uncheck all` toggle them together.
- The pattern canvas has a `Large drawing` mode for precise tracing without changing stored coordinates.

Current dataset:
- `osm_data.json` is now a Marseille dataset.
- Older Cassis counts are obsolete. Recompute counts from the local `osm_data.json` before relying on element/layer totals.

Current pattern-search status:
- A first backend rework now uses `network-patch` matching for strokes instead of independent per-stroke branch matching.
- This partially addresses the previous blocker by comparing the full local geometry around each candidate.
- Remaining limitation: candidates are still centered on OSM nodes/branches, not a full sliding-window over every road segment.

Previous pattern-search blocker:
- User ran 4 manual tests using exact route lines from the map.
- Even with exact drawn route lines, the system returns candidates that look somewhat similar but does not find/rank the correct location.
- This suggests the current candidate generation/scoring is structurally insufficient, not just a drawing UX issue.
- Likely weak points:
  - Candidate generation is still centered around OSM intersection nodes and branch paths, so the correct path may not be included or scored in the right context.
  - It may need a sliding-window search along roads, not only candidate paths derived from intersections.
- Next serious improvement should probably replace the candidate model with local road-network patch matching:
  1. Build normalized query geometry from all strokes.
  2. Extract OSM road-network patches around many candidate centers or along road segments.
  3. Normalize candidate patches by translation, scale, and optional rotation.
  4. Score by bidirectional nearest-segment distance plus angle and relative-length penalties.
  5. Return/highlight the actual matched patch, not just branches around one OSM node.
- Keep the current UI improvements, but treat the current `free-trace` backend as experimental and not reliable enough.

Alternative hypothesis: stronger vector-style drawing editor:
- It may be useful to make the drawing tool more explicit and editable, similar to Illustrator/Figma pen tools, but this should support better matching rather than replace the need for a stronger backend.
- Possible features:
  - draggable vertices/angle points after drawing;
  - insert/delete vertices on a line;
  - snap vertices to nearby strokes to explicitly mark intersections;
  - mark a vertex as an intersection, bend, endpoint, or "ignore";
  - apply a rounded curve to a straight polyline segment or smooth a selected section;
  - preserve hard angles when wanted and smooth curves when wanted;
  - show relative segment lengths and angle values visually;
  - optionally lock proportions such as "this branch is about 2x that one";
  - let the user trace a candidate, adjust it, then rerun search without redrawing.
- Why it could help:
  - User tests show exact freehand/angle traces still fail, so noisy input is not the only problem.
  - However, a vector editor could produce cleaner query geometry and explicit constraints, making a future patch-matching backend easier to score.
  - Explicit intersections and editable bends could prevent the system from guessing graph topology incorrectly.
- Risk:
  - This is probably not enough by itself. If candidate generation/scoring remains centered on intersection branches, a better drawing editor will still return wrong lookalikes.
  - Best path may be to combine this with local road-network patch matching: better query editor first, then stronger backend scoring.

Development notes:
- Keep the app dependency-light: Python stdlib + Tkinter + browser-side Leaflet from CDN.
- For UI map changes, edit `WEB_APP_HTML` in `osint_app/web.py`.
- For new OSINT layers/categories, edit `POINT_KINDS` in `osint_app/config.py` and `point_kind()` in `osint_app/osm.py`.
- For pattern matching changes, edit `osint_app/pattern.py` and the Pattern Search UI/API in `osint_app/web.py`.
- After changing OSM classification, run `python -m py_compile main.py osint_app\__init__.py osint_app\app.py osint_app\config.py osint_app\osm.py osint_app\pattern.py osint_app\web.py` on PowerShell and test `build_map_payload(load_osm_json("osm_data.json"))`.
- After changing pattern matching, also test `build_road_pattern_index(load_osm_json("osm_data.json"))` and `/api/pattern-search`.
