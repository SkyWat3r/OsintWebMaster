# OSINT OpenStreetMap Explorer

Local OpenStreetMap OSINT explorer with a Tkinter control window and a Leaflet web map served on localhost.

## Run

```bash
python main.py
```

The app starts a local server on `127.0.0.1:8765` or the next available port, then opens the interactive map in a browser.

## Data

The app can:

- fetch OSM data from Overpass with the `Fetch OSM data` button;
- load a local OSM JSON export with `Load OSM JSON`;
- auto-load `osm_data.json` if that file exists next to `main.py`.

Large generated files such as `osm_data.json` and `osm_map.html` are ignored by Git.
