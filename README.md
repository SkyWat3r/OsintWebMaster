# OSINT OpenStreetMap Explorer

Local OpenStreetMap OSINT explorer with a Tkinter control window and a Leaflet web map served on localhost.

## Run

```bash
python main.py
```

The app starts a local server on `127.0.0.1:8765` or the next available port, then opens the interactive map in a browser.

## Pattern search

The web map includes a first road-pattern search mode:

- drag in the pattern canvas to draw roads like a paint tool;
- start a stroke on an existing point to connect it to the current drawing;
- use intermediate points to trace bends and curved roads;
- use `Angle points` for cleaner polylines, then drag vertices to adjust them or `Delete point` to remove a selected vertex;
- use `Add midpoint`, `Smooth curve`, and `Straight corners` to refine rounded roads before searching;
- optionally import a photo as the canvas background and trace the road shape manually;
- use `Search` to find similar road intersections in the loaded OSM data.

Stroke drawings first use a `road-layer-window` matcher against the same OSM highway ways displayed as road lines on the map, including sliding windows on long routes. It then falls back to `network-patch`, which compares the whole traced shape against normalized local OSM road-network patches with optional rotation. Smoothed curves are sampled into denser strokes before matching. Older point/edge drawings still fall back to `linear-trace` or intersection matching. Points with two connected segments are treated as bends. Points with three or more connected segments are treated as intersections. `Free rotation` keeps the search independent from absolute north/south orientation.

Map layers start unchecked. Use `Check all` / `Uncheck all` to quickly toggle roads, areas, and point layers. Use `Full map` to hide the control panel and inspect the map with the full browser viewport. Use `Large drawing` to expand the pattern canvas for more precise tracing.

## Data

The app can:

- fetch OSM data from Overpass with the `Fetch OSM data` button;
- load a local OSM JSON export with `Load OSM JSON`;
- auto-load `osm_data.json` if that file exists next to `main.py`.

Large generated files such as `osm_data.json` and `osm_map.html` are ignored by Git.
