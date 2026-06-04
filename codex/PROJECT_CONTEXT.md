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
6. Pattern search calls `/api/pattern-search` with drawn canvas points/edges.

Important behavior to preserve:
- Do not re-fetch Overpass data when `osm_data.json` is already usable.
- `Open Map` should open/copy the localhost URL, not generate a beige Tkinter canvas map.
- The web map must use real OSM tiles through Leaflet.
- Point filters are classified by OSM tags. Gates are `barrier=gate/lift_gate/swing_gate/...` and use the `▥` symbol.
- Google Maps links are generated client-side from feature coordinates.
- Pattern search compares drawn road/intersection shapes. Photo import is only a drawing background, not automatic image analysis.
- In pattern drawings, two-segment points are bends/tracing points; 3+ segment points are intersections.
- `Free rotation` compares relative branch angles so the pattern does not need to be north-aligned.
- The web UI has a `Full map` mode that hides the control panel until the user reopens it.
- The pattern canvas has a `Large drawing` mode for precise tracing without changing stored coordinates.

Known current dataset counts from `osm_data.json`:
- 976,812 OSM elements
- 2,696 roads
- 8,285 areas
- 3,893 points
- 401 gates
- 314 crossings
- 92 give-way signs
- 27 stop signs
- 28 turning circles
- 3 traffic signs
- 0 traffic lights in the current Cassis dataset

Development notes:
- Keep the app dependency-light: Python stdlib + Tkinter + browser-side Leaflet from CDN.
- For UI map changes, edit `WEB_APP_HTML` in `osint_app/web.py`.
- For new OSINT layers/categories, edit `POINT_KINDS` in `osint_app/config.py` and `point_kind()` in `osint_app/osm.py`.
- For pattern matching changes, edit `osint_app/pattern.py` and the Pattern Search UI/API in `osint_app/web.py`.
- After changing OSM classification, run `python -m py_compile main.py osint_app/*.py` and test `build_map_payload(load_osm_json("osm_data.json"))`.
- After changing pattern matching, also test `build_road_pattern_index(load_osm_json("osm_data.json"))` and `/api/pattern-search`.
