import json
import os
import shutil
import socket
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from .config import DEFAULT_JSON_FILE
from .osm import build_map_payload

def write_leaflet_map(data: dict, output_path: str | Path) -> Path:
    payload = build_map_payload(data)
    payload_json = json.dumps(payload, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OSM OSINT Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    body {{ font-family: Arial, sans-serif; }}
    #panel {{
      position: absolute;
      z-index: 1000;
      top: 12px;
      right: 12px;
      width: 320px;
      max-height: calc(100% - 24px);
      overflow: auto;
      background: white;
      border: 1px solid #c8c8c8;
      box-shadow: 0 2px 12px rgba(0,0,0,.2);
      padding: 10px;
    }}
    #panel h1 {{ font-size: 16px; margin: 0 0 8px; }}
    #filter {{ width: 100%; box-sizing: border-box; margin: 8px 0; padding: 7px; }}
    .stat {{ color: #444; font-size: 13px; line-height: 1.4; }}
    .leaflet-popup-content {{ max-height: 360px; overflow: auto; }}
    .leaflet-popup-content table {{ border-collapse: collapse; font-size: 12px; }}
    .leaflet-popup-content th {{
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid #ddd;
      padding: 3px 8px 3px 0;
      white-space: nowrap;
    }}
    .leaflet-popup-content td {{ border-bottom: 1px solid #ddd; padding: 3px 0; }}
    .meta {{ margin: 4px 0 8px; color: #555; font-size: 12px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="panel">
    <h1>OSM Pattern Explorer</h1>
    <div class="stat" id="stats"></div>
    <input id="filter" placeholder="Filter roads, POIs, tags...">
    <div class="stat">Road colors follow the OSM highway type. Click a line or point to inspect all tags.</div>
  </div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const data = {payload_json};
    const map = L.map('map');
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const roadLayer = L.layerGroup().addTo(map);
    const areaLayer = L.layerGroup().addTo(map);
    const pointLayer = L.layerGroup().addTo(map);
    const allItems = [];

    function searchable(item) {{
      return `${{item.name}} ${{item.category}} ${{item.popup}}`.toLowerCase();
    }}

    function draw(filterText = '') {{
      roadLayer.clearLayers();
      areaLayer.clearLayers();
      pointLayer.clearLayers();
      const filter = filterText.toLowerCase();

      for (const road of data.roads) {{
        if (filter && !searchable(road).includes(filter)) continue;
        L.polyline(road.coords, {{ color: road.color, weight: 4, opacity: 0.9 }}).bindPopup(road.popup).addTo(roadLayer);
      }}
      for (const area of data.areas) {{
        if (filter && !searchable(area).includes(filter)) continue;
        L.polygon(area.coords, {{ color: '#666', weight: 1, fillColor: '#9ecae1', fillOpacity: 0.2 }}).bindPopup(area.popup).addTo(areaLayer);
      }}
      for (const point of data.points) {{
        if (filter && !searchable(point).includes(filter)) continue;
        L.circleMarker(point.coords, {{ radius: 4, color: '#222', fillColor: '#ffcc00', fillOpacity: 0.8, weight: 1 }}).bindPopup(point.popup).addTo(pointLayer);
      }}
    }}

    L.control.layers({{}}, {{
      Roads: roadLayer,
      Areas: areaLayer,
      Points: pointLayer
    }}).addTo(map);

    if (data.bounds.length) {{
      map.fitBounds(data.bounds, {{ padding: [24, 24] }});
    }} else {{
      map.setView([0, 0], 2);
    }}

    document.getElementById('stats').innerHTML =
      `${{data.stats.elements.toLocaleString()}} OSM elements<br>` +
      `${{data.stats.roads.toLocaleString()}} road ways, ` +
      `${{data.stats.areas.toLocaleString()}} areas, ` +
      `${{data.stats.points.toLocaleString()}} points`;
    document.getElementById('filter').addEventListener('input', (event) => draw(event.target.value));
    draw();
  </script>
</body>
</html>
"""
    output_path = Path(output_path)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def open_html_file(path: Path) -> bool:
    path = path.resolve()
    uri = path.as_uri()

    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
        return True

    if sys.platform == "darwin":
        return subprocess.run(["open", str(path)], check=False).returncode == 0

    for browser in (
        "firefox",
        "firefox-esr",
        "google-chrome",
        "chromium",
        "chromium-browser",
        "brave-browser",
        "microsoft-edge",
    ):
        executable = shutil.which(browser)
        if executable:
            subprocess.Popen([executable, uri])
            return True

    if sys.platform.startswith("linux"):
        return False

    return webbrowser.open_new_tab(uri)


def open_browser_url(url: str) -> bool:
    if sys.platform.startswith("win"):
        os.startfile(url)  # type: ignore[attr-defined]
        return True

    if sys.platform == "darwin":
        return subprocess.run(["open", url], check=False).returncode == 0

    for browser in (
        "firefox",
        "firefox-esr",
        "google-chrome",
        "chromium",
        "chromium-browser",
        "brave-browser",
        "microsoft-edge",
    ):
        executable = shutil.which(browser)
        if executable:
            subprocess.Popen([executable, url])
            return True

    if sys.platform.startswith("linux"):
        return False

    return webbrowser.open_new_tab(url)


WEB_APP_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OSM OSINT Local Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    html, body, #map {
      height: 100%;
      margin: 0;
    }
    body {
      font-family: Arial, sans-serif;
      color: #1f2933;
    }
    #mapFocusToggle {
      position: absolute;
      top: 12px;
      left: 50px;
      z-index: 1001;
    }
    #map {
      --map-rotation: 0deg;
    }
    #mapRotationControls {
      display: none;
      flex-basis: 100%;
      gap: 8px;
      align-items: center;
    }
    #mapRotationControls.active {
      display: flex;
    }
    #mapRotation {
      width: 150px;
    }
    #map.rotate-drag-enabled {
      cursor: crosshair;
    }
    #panel {
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 1000;
      width: 370px;
      max-height: calc(100% - 24px);
      box-sizing: border-box;
      overflow: auto;
      background: rgba(255, 255, 255, 0.96);
      border: 1px solid #c8c8c8;
      box-shadow: 0 2px 14px rgba(0,0,0,.18);
      padding: 12px;
    }
    h1 {
      font-size: 17px;
      margin: 0 0 8px;
    }
    button, input, label {
      font-size: 13px;
    }
    button {
      padding: 6px 9px;
      border: 1px solid #aaa;
      background: #f8f8f8;
      cursor: pointer;
    }
    body.map-focus #panel {
      display: none;
    }
    body.pattern-focus #panel {
      left: 24px;
      right: 24px;
      top: 24px;
      width: auto;
      max-height: calc(100% - 48px);
    }
    body.pattern-focus #mapToolsSection,
    body.pattern-focus #filtersSection,
    body.pattern-focus #detailsSection,
    body.pattern-focus #status {
      display: none;
    }
    input[type="text"] {
      width: 100%;
      box-sizing: border-box;
      padding: 8px;
      border: 1px solid #b8b8b8;
      margin: 8px 0;
    }
    .row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin: 8px 0;
    }
    .control-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 8px;
      margin: 8px 0;
    }
    .control-grid label,
    .tool-row label,
    .option-row label {
      display: inline-flex;
      gap: 5px;
      align-items: center;
    }
    .tool-row,
    .option-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin: 8px 0;
    }
    .panel-section {
      border-top: 1px solid #d8dde6;
      padding-top: 8px;
      margin-top: 8px;
    }
    .panel-section summary {
      cursor: pointer;
      font-size: 13px;
      font-weight: 700;
      color: #111827;
      list-style-position: outside;
      padding: 4px 0;
    }
    .panel-section[open] summary {
      margin-bottom: 6px;
    }
    .stat {
      font-size: 13px;
      line-height: 1.45;
      color: #3f4650;
    }
    #details {
      overflow-wrap: anywhere;
      max-height: 360px;
      overflow: auto;
      font-size: 12px;
      line-height: 1.35;
      border-top: 1px solid #ddd;
      margin-top: 10px;
      padding-top: 10px;
    }
    #details pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: Consolas, monospace;
      font-size: 12px;
      margin: 8px 0 0;
    }
    .maps-link {
      display: inline-block;
      margin: 0 0 8px;
      padding: 6px 9px;
      border: 1px solid #999;
      background: #f8f8f8;
      color: #111827;
      text-decoration: none;
    }
    .maps-link:hover {
      background: #ededed;
    }
    .leaflet-popup-content {
      max-height: 340px;
      overflow: auto;
    }
    #pointFilters {
      margin: 8px 0;
      padding: 8px 0;
      border-top: 1px solid #ddd;
      border-bottom: 1px solid #ddd;
    }
    .point-filter-group {
      margin: 6px 0;
    }
    .point-filter-group summary {
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;
      color: #334155;
      padding: 3px 0;
    }
    .point-filter-options {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5px 8px;
      padding: 5px 0 3px;
    }
    .point-filter-options label {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      min-width: 0;
    }
    .filter-icon,
    .maki-icon {
      display: inline-block;
      width: 16px;
      height: 16px;
      flex: 0 0 16px;
      background: currentColor;
      vertical-align: -3px;
    }
    .maki-icon {
      -webkit-mask: var(--maki-url) center / contain no-repeat;
      mask: var(--maki-url) center / contain no-repeat;
    }
    .poi-icon {
      width: 20px;
      height: 20px;
      line-height: 20px;
      border-radius: 50%;
      border: 2px solid #111;
      color: #fff;
      font-size: 12px;
      font-weight: 700;
      text-align: center;
      box-shadow: 0 1px 4px rgba(0,0,0,.35);
      user-select: none;
    }
    .poi-icon .maki-icon {
      width: 13px;
      height: 13px;
      margin-top: 3px;
      color: #fff;
    }
    #patternCanvas {
      width: 100%;
      height: 230px;
      display: block;
      box-sizing: border-box;
      border: 1px solid #9aa4b2;
      background: #f9fafb;
      margin: 8px 0;
      touch-action: none;
    }
    body.pattern-focus #patternCanvas {
      height: min(68vh, 720px);
    }
    .pattern-layout {
      display: block;
    }
    body.pattern-focus .pattern-layout {
      display: grid;
      grid-template-columns: 310px minmax(360px, 1fr);
      gap: 12px;
      align-items: start;
    }
    .pattern-results-panel {
      display: none;
    }
    body.pattern-focus .pattern-results-panel,
    .pattern-results-panel.has-results {
      display: block;
    }
    #patternResults {
      display: grid;
      gap: 6px;
      max-height: 58vh;
      overflow: auto;
      margin-top: 8px;
    }
    .pattern-result {
      width: 100%;
      text-align: left;
      border: 1px solid #cbd5e1;
      background: #fff;
      border-radius: 4px;
      padding: 8px;
    }
    .pattern-result.selected {
      border-color: #2563eb;
      background: #eff6ff;
    }
    .road-group-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5px 8px;
      margin: 8px 0;
    }
    #patternMapsBar {
      position: absolute;
      left: 50%;
      bottom: 14px;
      transform: translateX(-50%);
      z-index: 1001;
      display: none;
      max-width: min(720px, calc(100% - 28px));
      box-sizing: border-box;
      padding: 9px 12px;
      border: 1px solid #94a3b8;
      background: rgba(255, 255, 255, 0.97);
      box-shadow: 0 2px 12px rgba(0,0,0,.18);
      font-size: 13px;
    }
    #patternMapsBar a {
      color: #1d4ed8;
      font-weight: 700;
    }
    #photoInput {
      width: 100%;
      box-sizing: border-box;
    }
    .section {
      margin-top: 10px;
    }
    .result-icon {
      width: 26px;
      height: 26px;
      line-height: 26px;
      border-radius: 50%;
      border: 2px solid #111827;
      color: white;
      background: #dc2626;
      font-size: 12px;
      font-weight: 700;
      text-align: center;
      box-shadow: 0 1px 6px rgba(0,0,0,.35);
      user-select: none;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <button id="mapFocusToggle">Full map</button>
  <div id="panel">
    <h1>OSM Pattern Explorer</h1>
    <div id="status" class="stat">Loading local API data...</div>
    <details class="panel-section" id="mapToolsSection" open>
      <summary>Map tools</summary>
      <div class="tool-row">
        <button id="fit">Fit</button>
        <button id="focusMap">Full map</button>
        <button id="toggleMapRotation">Rotate map</button>
      </div>
      <div id="mapRotationControls">
        <input id="mapRotation" type="range" min="0" max="359" step="1" value="0">
        <input id="mapRotationNumber" type="number" min="0" max="359" step="1" value="0">
        <label><input id="dragMapRotation" type="checkbox"> Drag rotate</label>
        <button id="resetMapRotation">Reset rotation</button>
      </div>
    </details>
    <details class="panel-section" id="filtersSection" open>
      <summary>Filters</summary>
      <input id="filter" type="text" placeholder="Filter names, tags, road types">
      <div class="tool-row">
        <button id="uncheckAllLayers">Uncheck all</button>
        <button id="checkAllLayers">Check all</button>
      </div>
      <div class="control-grid">
        <label><input id="roads" type="checkbox"> Roads</label>
        <label><input id="areas" type="checkbox"> Areas</label>
      </div>
      <div class="stat">Point layers</div>
      <div id="pointFilters"></div>
    </details>
    <details class="panel-section section" id="roadSearchSection" open>
      <summary>Road search</summary>
      <div class="road-group-grid">
        <label><input type="checkbox" data-road-group="roads" checked> Roads</label>
        <label><input type="checkbox" data-road-group="highways" checked> Highways</label>
        <label><input type="checkbox" data-road-group="paths" checked> Paths / tracks</label>
        <label><input type="checkbox" data-road-group="service" checked> Service roads</label>
      </div>
      <div class="pattern-layout">
        <div class="pattern-results-panel" id="patternResultsPanel">
          <div class="stat"><strong>Best matches</strong></div>
          <div id="patternResults" class="stat">Launch a search to rank matches.</div>
        </div>
        <div class="pattern-drawing-panel">
          <input id="photoInput" type="file" accept="image/*">
          <canvas id="patternCanvas"></canvas>
          <div class="tool-row">
            <button id="searchPattern">Search</button>
            <button id="exportPatternSearch">Export search</button>
            <button id="focusPattern">Large drawing</button>
            <button id="clearPattern">Clear</button>
          </div>
          <div class="tool-row">
            <button id="undoPattern">Undo stroke</button>
            <button id="finishAngleStroke">Finish line</button>
            <button id="deletePatternPoint">Delete point</button>
            <button id="addPatternMidpoint">Add midpoint</button>
            <button id="smoothPatternStroke">Smooth curve</button>
            <button id="straightPatternStroke">Straight corners</button>
          </div>
          <div class="option-row">
            <label><input id="anglePointMode" type="checkbox"> Angle points</label>
            <label><input id="freeRotation" type="checkbox" checked> Free rotation</label>
            <label><input id="preciseRotation" type="checkbox"> 10 deg rotation (slow)</label>
          </div>
          <div class="tool-row">
            <button id="compareSelectedRoad">Compare selected road</button>
            <button id="exportSelectedRoad">Export selected road</button>
            <label><input id="devRoadSelect" type="checkbox"> Dev select road</label>
          </div>
          <div id="patternStatus" class="stat">Draw road shapes freely. Add more strokes if the first search is too vague.</div>
        </div>
      </div>
    </details>
    <details class="panel-section" id="detailsSection">
      <summary>Selection details</summary>
      <div id="details">Click a road, area, or point to inspect tags.</div>
    </details>
  </div>
  <div id="patternMapsBar"></div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map', { preferCanvas: true });
    const renderer = L.canvas({ padding: 2.5 });
    const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      keepBuffer: 14,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const statusEl = document.getElementById('status');
    const detailsEl = document.getElementById('details');
    const filterEl = document.getElementById('filter');
    const roadsEl = document.getElementById('roads');
    const areasEl = document.getElementById('areas');
    const mapEl = document.getElementById('map');
    const mapRotationControlsEl = document.getElementById('mapRotationControls');
    const mapRotationEl = document.getElementById('mapRotation');
    const mapRotationNumberEl = document.getElementById('mapRotationNumber');
    const dragMapRotationEl = document.getElementById('dragMapRotation');
    const pointFiltersEl = document.getElementById('pointFilters');
    const patternCanvas = document.getElementById('patternCanvas');
    const patternCtx = patternCanvas.getContext('2d');
    const patternStatusEl = document.getElementById('patternStatus');
    const freeRotationEl = document.getElementById('freeRotation');
    const preciseRotationEl = document.getElementById('preciseRotation');
    const mapFocusToggleEl = document.getElementById('mapFocusToggle');
    const patternResultsEl = document.getElementById('patternResults');
    const patternResultsPanelEl = document.getElementById('patternResultsPanel');
    const patternMapsBarEl = document.getElementById('patternMapsBar');
    const anglePointModeEl = document.getElementById('anglePointMode');
    const devRoadSelectEl = document.getElementById('devRoadSelect');
    const roadGroupInputs = Array.from(document.querySelectorAll('input[data-road-group]'));

    const roadsLayer = L.layerGroup().addTo(map);
    const areasLayer = L.layerGroup().addTo(map);
    const pointsLayer = L.layerGroup().addTo(map);
    const patternResultsLayer = L.layerGroup().addTo(map);
    const devRoadSelectionLayer = L.layerGroup().addTo(map);
    let payload = null;
    let drawingVersion = 0;
    let patternImage = null;
    let isPaintingPattern = false;
    let activePatternStroke = null;
    let activeAngleStroke = null;
    let selectedPatternPoint = null;
    let draggedPatternPoint = null;
    let patternMatches = [];
    let selectedPatternMatchIndex = -1;
    let lastPatternSearchExport = null;
    let selectedDevRoad = null;
    let lastRoadCompareExport = null;
    let isDraggingMapRotation = false;
    let mapRotationDragOffset = 0;
    const leafletSetTransform = L.DomUtil.setTransform;
    L.DomUtil.setTransform = function patchedSetTransform(element, offset, scale) {
      leafletSetTransform.call(this, element, offset, scale);
      if (element === map._mapPane) {
        applyMapPaneRotation();
      }
    };
    const enabledPointKinds = new Set();
    const patternStrokes = [];
    const smoothPatternStrokes = new WeakSet();

    function matchesFilter(item) {
      const filter = filterEl.value.trim().toLowerCase();
      if (!filter) return true;
      return `${item.name} ${item.category} ${item.details}`.toLowerCase().includes(filter);
    }

    function bindFeature(layer, item, type) {
      layer.on('click', () => {
        if (type === 'road' && devRoadSelectEl.checked) {
          selectDevRoad(item);
          return;
        }
        showDetails(item);
      });
      const mapsUrl = googleMapsUrl(item);
      layer.bindPopup(
        `<strong>${escapeHtml(item.name || '(no name)')}</strong><br>` +
        `${escapeHtml(item.category || '')}<br>` +
        `<a href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>`
      );
      return layer;
    }

    function selectDevRoad(road) {
      if (!roadsEl.checked) {
        patternStatusEl.textContent = 'Enable Roads before selecting a dev reference road.';
        return;
      }
      selectedDevRoad = road;
      devRoadSelectionLayer.clearLayers();
      L.polyline(road.coords, {
        renderer,
        color: '#f97316',
        weight: 8,
        opacity: 0.95
      }).addTo(devRoadSelectionLayer);
      showDetails(road);
      patternStatusEl.textContent = `Selected dev road ${road.osmId || '(no id)'}. Draw the same shape, then compare or export.`;
    }

    function representativeCoord(item) {
      if (!item.coords) return null;
      if (typeof item.coords[0] === 'number') return item.coords;
      if (!item.coords.length) return null;
      let lat = 0;
      let lon = 0;
      for (const coord of item.coords) {
        lat += coord[0];
        lon += coord[1];
      }
      return [lat / item.coords.length, lon / item.coords.length];
    }

    function googleMapsUrl(item) {
      const coord = representativeCoord(item);
      if (!coord) return 'https://www.google.com/maps';
      return `https://www.google.com/maps?q=${coord[0]},${coord[1]}`;
    }

    function showDetails(item) {
      const coord = representativeCoord(item);
      const mapsUrl = googleMapsUrl(item);
      const coordText = coord ? `\n\nGoogle Maps coordinates: ${coord[0].toFixed(6)}, ${coord[1].toFixed(6)}` : '';
      detailsEl.innerHTML =
        `<a class="maps-link" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Open this place in Google Maps</a>` +
        `<pre>${escapeHtml((item.details || 'No details') + coordText)}</pre>`;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      })[char]);
    }

    function makiIconUrl(name) {
      if (!name) return '';
      return `https://raw.githubusercontent.com/mapbox/maki/main/icons/${encodeURIComponent(name)}.svg`;
    }

    function layerIconHtml(meta, className = 'filter-icon') {
      const color = escapeHtml(meta.color || '#334155');
      const makiName = meta.maki || meta.iconUrl;
      const maki = makiName ? makiIconUrl(makiName) : '';
      if (maki) {
        return `<span class="${className} maki-icon" style="color:${color}; --maki-url:url('${escapeHtml(maki)}')"></span>`;
      }
      return `<span style="color:${color}; font-weight:700">${escapeHtml(meta.icon || '•')}</span>`;
    }

    function pointMarkerIconHtml(item) {
      const maki = item.iconUrl ? makiIconUrl(item.iconUrl) : '';
      if (maki) {
        return `<span class="maki-icon" style="color:#fff; --maki-url:url('${escapeHtml(maki)}')"></span>`;
      }
      return escapeHtml(item.icon || '•');
    }

    function clearLayers() {
      roadsLayer.clearLayers();
      areasLayer.clearLayers();
      pointsLayer.clearLayers();
    }

    function resizePatternCanvas() {
      const rect = patternCanvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      const width = Math.max(1, Math.round(rect.width * ratio));
      const height = Math.max(1, Math.round(rect.height * ratio));
      if (patternCanvas.width !== width || patternCanvas.height !== height) {
        patternCanvas.width = width;
        patternCanvas.height = height;
      }
      patternCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function canvasSize() {
      const rect = patternCanvas.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    }

    function patternViewport() {
      const size = canvasSize();
      const aspect = 340 / 230;
      let width = size.width;
      let height = width / aspect;
      if (height > size.height) {
        height = size.height;
        width = height * aspect;
      }
      return {
        x: (size.width - width) / 2,
        y: (size.height - height) / 2,
        width,
        height
      };
    }

    function canvasPoint(event) {
      const rect = patternCanvas.getBoundingClientRect();
      const viewport = patternViewport();
      const rawX = event.clientX - rect.left - viewport.x;
      const rawY = event.clientY - rect.top - viewport.y;
      return {
        x: Math.min(1, Math.max(0, rawX / viewport.width)),
        y: Math.min(1, Math.max(0, rawY / viewport.height))
      };
    }

    function pointDistancePx(left, right) {
      const viewport = patternViewport();
      return Math.hypot((right.x - left.x) * viewport.width, (right.y - left.y) * viewport.height);
    }

    function nearestPatternPoint(point, maxDistancePx = 12) {
      let nearest = null;
      let nearestDistance = maxDistancePx;
      for (const stroke of patternStrokes) {
        for (let index = 0; index < stroke.length; index++) {
          const distance = pointDistancePx(point, stroke[index]);
          if (distance <= nearestDistance) {
            nearest = { stroke, index, point: stroke[index] };
            nearestDistance = distance;
          }
        }
      }
      return nearest;
    }

    function selectedPointMatches(stroke, index) {
      return selectedPatternPoint && selectedPatternPoint.stroke === stroke && selectedPatternPoint.index === index;
    }

    function segmentLengthPercent(first, second) {
      return Math.round(Math.hypot(second.x - first.x, second.y - first.y) * 100);
    }

    function segmentAngle(first, second) {
      const degrees = Math.atan2(first.y - second.y, second.x - first.x) * 180 / Math.PI;
      return Math.round((degrees + 360) % 360);
    }

    function selectedPointSummary() {
      if (!selectedPatternPoint) return '';
      const stroke = selectedPatternPoint.stroke;
      const index = selectedPatternPoint.index;
      const parts = [`point ${index + 1}/${stroke.length}`, smoothPatternStrokes.has(stroke) ? 'smooth' : 'corners'];
      if (index > 0) {
        const previous = stroke[index - 1];
        const current = stroke[index];
        parts.push(`prev ${segmentLengthPercent(previous, current)}%, ${segmentAngle(previous, current)}deg`);
      }
      if (index < stroke.length - 1) {
        const current = stroke[index];
        const next = stroke[index + 1];
        parts.push(`next ${segmentLengthPercent(current, next)}%, ${segmentAngle(current, next)}deg`);
      }
      return parts.join(' | ');
    }

    function activeEditableStroke() {
      if (selectedPatternPoint) return selectedPatternPoint.stroke;
      if (activeAngleStroke) return activeAngleStroke;
      if (patternStrokes.length) return patternStrokes[patternStrokes.length - 1];
      return null;
    }

    function drawSmoothStroke(stroke, viewport) {
      if (stroke.length < 2) return;
      patternCtx.beginPath();
      patternCtx.moveTo(viewport.x + stroke[0].x * viewport.width, viewport.y + stroke[0].y * viewport.height);
      for (let index = 1; index < stroke.length - 1; index++) {
        const current = stroke[index];
        const next = stroke[index + 1];
        const controlX = viewport.x + current.x * viewport.width;
        const controlY = viewport.y + current.y * viewport.height;
        const endX = viewport.x + ((current.x + next.x) / 2) * viewport.width;
        const endY = viewport.y + ((current.y + next.y) / 2) * viewport.height;
        patternCtx.quadraticCurveTo(controlX, controlY, endX, endY);
      }
      const last = stroke[stroke.length - 1];
      patternCtx.lineTo(viewport.x + last.x * viewport.width, viewport.y + last.y * viewport.height);
      patternCtx.stroke();
    }

    function smoothStrokePoints(stroke) {
      if (!smoothPatternStrokes.has(stroke) || stroke.length < 3) {
        return stroke.map((point) => ({ x: point.x, y: point.y }));
      }
      const sampled = [{ x: stroke[0].x, y: stroke[0].y }];
      for (let index = 1; index < stroke.length - 1; index++) {
        const start = sampled[sampled.length - 1];
        const control = stroke[index];
        const next = stroke[index + 1];
        const end = { x: (control.x + next.x) / 2, y: (control.y + next.y) / 2 };
        for (let step = 1; step <= 6; step++) {
          const t = step / 6;
          const inv = 1 - t;
          sampled.push({
            x: inv * inv * start.x + 2 * inv * t * control.x + t * t * end.x,
            y: inv * inv * start.y + 2 * inv * t * control.y + t * t * end.y
          });
        }
      }
      sampled.push({ x: stroke[stroke.length - 1].x, y: stroke[stroke.length - 1].y });
      return sampled;
    }

    function drawPatternCanvas() {
      resizePatternCanvas();
      const size = canvasSize();
      const viewport = patternViewport();
      patternCtx.clearRect(0, 0, size.width, size.height);
      patternCtx.fillStyle = '#f1f5f9';
      patternCtx.fillRect(0, 0, size.width, size.height);
      patternCtx.fillStyle = '#f9fafb';
      patternCtx.fillRect(viewport.x, viewport.y, viewport.width, viewport.height);
      if (patternImage) {
        const scale = Math.min(viewport.width / patternImage.width, viewport.height / patternImage.height);
        const width = patternImage.width * scale;
        const height = patternImage.height * scale;
        patternCtx.globalAlpha = 0.58;
        patternCtx.drawImage(
          patternImage,
          viewport.x + (viewport.width - width) / 2,
          viewport.y + (viewport.height - height) / 2,
          width,
          height
        );
        patternCtx.globalAlpha = 1;
      }
      patternCtx.lineWidth = 4;
      patternCtx.strokeStyle = '#dc2626';
      patternCtx.lineCap = 'round';
      patternCtx.lineJoin = 'round';
      for (const stroke of patternStrokes) {
        if (stroke.length < 2) continue;
        if (smoothPatternStrokes.has(stroke)) {
          drawSmoothStroke(stroke, viewport);
        } else {
          patternCtx.beginPath();
          patternCtx.moveTo(viewport.x + stroke[0].x * viewport.width, viewport.y + stroke[0].y * viewport.height);
          for (const point of stroke.slice(1)) {
            patternCtx.lineTo(viewport.x + point.x * viewport.width, viewport.y + point.y * viewport.height);
          }
          patternCtx.stroke();
        }
      }
      if (anglePointModeEl.checked) {
        patternCtx.lineWidth = 2;
        for (const stroke of patternStrokes) {
          for (let index = 0; index < stroke.length; index++) {
            const point = stroke[index];
            const selected = selectedPointMatches(stroke, index);
            patternCtx.beginPath();
            patternCtx.arc(
              viewport.x + point.x * viewport.width,
              viewport.y + point.y * viewport.height,
              selected ? 8 : (stroke === activeAngleStroke ? 5 : 4),
              0,
              Math.PI * 2
            );
            patternCtx.fillStyle = selected ? '#f97316' : (stroke === activeAngleStroke ? '#2563eb' : '#111827');
            patternCtx.fill();
            patternCtx.strokeStyle = '#fff';
            patternCtx.stroke();
          }
        }
      }
      const segments = patternStrokes.reduce((total, stroke) => total + Math.max(0, stroke.length - 1), 0);
      const selection = selectedPointSummary();
      patternStatusEl.textContent = `${patternStrokes.length} strokes, ${segments} trace segments${selection ? ` | ${selection}` : ''}`;
    }

    function clearPattern() {
      patternStrokes.length = 0;
      patternMatches = [];
      lastPatternSearchExport = null;
      selectedPatternMatchIndex = -1;
      isPaintingPattern = false;
      activePatternStroke = null;
      activeAngleStroke = null;
      selectedPatternPoint = null;
      draggedPatternPoint = null;
      patternResultsLayer.clearLayers();
      patternResultsPanelEl.classList.remove('has-results');
      patternResultsEl.textContent = 'Launch a search to rank matches.';
      patternMapsBarEl.style.display = 'none';
      drawPatternCanvas();
    }

    function undoPattern() {
      if (anglePointModeEl.checked && activeAngleStroke) {
        activeAngleStroke.pop();
        if (!activeAngleStroke.length) {
          patternStrokes.pop();
          activeAngleStroke = null;
        }
        drawPatternCanvas();
        return;
      }
      if (patternStrokes.length) {
        patternStrokes.pop();
      }
      if (activeAngleStroke && !patternStrokes.includes(activeAngleStroke)) {
        activeAngleStroke = null;
      }
      selectedPatternPoint = null;
      drawPatternCanvas();
    }

    function deleteSelectedPatternPoint() {
      if (!selectedPatternPoint) {
        patternStatusEl.textContent = 'Select a point in Angle points mode before deleting.';
        return;
      }
      const stroke = selectedPatternPoint.stroke;
      stroke.splice(selectedPatternPoint.index, 1);
      if (stroke.length < 2) {
        const strokeIndex = patternStrokes.indexOf(stroke);
        if (strokeIndex >= 0) {
          patternStrokes.splice(strokeIndex, 1);
        }
      }
      if (activeAngleStroke === stroke && !patternStrokes.includes(stroke)) {
        activeAngleStroke = null;
      }
      selectedPatternPoint = null;
      draggedPatternPoint = null;
      drawPatternCanvas();
    }

    function addPatternMidpoint() {
      const stroke = activeEditableStroke();
      if (!stroke || stroke.length < 2) {
        patternStatusEl.textContent = 'Select or draw a line before adding a midpoint.';
        return;
      }
      let insertAfter = selectedPatternPoint ? selectedPatternPoint.index : stroke.length - 2;
      if (insertAfter >= stroke.length - 1) {
        insertAfter = stroke.length - 2;
      }
      const first = stroke[insertAfter];
      const second = stroke[insertAfter + 1];
      const midpoint = { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 };
      stroke.splice(insertAfter + 1, 0, midpoint);
      selectedPatternPoint = { stroke, index: insertAfter + 1, point: midpoint };
      activeAngleStroke = stroke;
      drawPatternCanvas();
    }

    function setStrokeSmooth(enabled) {
      const stroke = activeEditableStroke();
      if (!stroke) {
        patternStatusEl.textContent = 'Select or draw a line before changing curve mode.';
        return;
      }
      if (enabled) {
        smoothPatternStrokes.add(stroke);
      } else {
        smoothPatternStrokes.delete(stroke);
      }
      activeAngleStroke = stroke;
      drawPatternCanvas();
    }

    function finishAngleStroke() {
      activeAngleStroke = null;
      drawPatternCanvas();
    }

    function selectedRoadGroups() {
      return roadGroupInputs.filter((input) => input.checked).map((input) => input.dataset.roadGroup);
    }

    function searchPayloadStrokes() {
      return patternStrokes.map(smoothStrokePoints);
    }

    function exportPatternSearch() {
      if (!lastPatternSearchExport) {
        patternStatusEl.textContent = 'Run a search before exporting.';
        return;
      }
      lastPatternSearchExport.selectedMatchIndex = selectedPatternMatchIndex;
      lastPatternSearchExport.selectedMatch = patternMatches[selectedPatternMatchIndex] || null;
      const body = JSON.stringify(lastPatternSearchExport, null, 2);
      const blob = new Blob([body], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      link.href = url;
      link.download = `pattern-search-${timestamp}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      patternStatusEl.textContent = 'Pattern search exported. Tell Codex which result is correct.';
    }

    function downloadJson(filenamePrefix, data) {
      const body = JSON.stringify(data, null, 2);
      const blob = new Blob([body], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      link.href = url;
      link.download = `${filenamePrefix}-${timestamp}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function normalizePolylines(polylines) {
      const points = polylines.flat();
      if (!points.length) return [];
      const minX = Math.min(...points.map((point) => point[0]));
      const maxX = Math.max(...points.map((point) => point[0]));
      const minY = Math.min(...points.map((point) => point[1]));
      const maxY = Math.max(...points.map((point) => point[1]));
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const scale = Math.max(maxX - minX, maxY - minY, 1e-9);
      return polylines.map((polyline) => polyline.map((point) => [
        (point[0] - centerX) / scale,
        (point[1] - centerY) / scale
      ]));
    }

    function drawingCompareGeometry(strokes) {
      return normalizePolylines(strokes
        .filter((stroke) => stroke.length >= 2)
        .map((stroke) => stroke.map((point) => [point.x, point.y])));
    }

    function roadCompareGeometry(road) {
      if (!road || !road.coords || road.coords.length < 2) return [];
      const centerLat = road.coords.reduce((sum, coord) => sum + coord[0], 0) / road.coords.length;
      const latScale = 111320;
      const lonScale = 111320 * Math.cos(centerLat * Math.PI / 180);
      return normalizePolylines([
        road.coords.map((coord) => [coord[1] * lonScale, coord[0] * latScale])
      ]);
    }

    function polylineLength(polyline) {
      let length = 0;
      for (let index = 1; index < polyline.length; index++) {
        length += Math.hypot(polyline[index][0] - polyline[index - 1][0], polyline[index][1] - polyline[index - 1][1]);
      }
      return length;
    }

    function samplePolylines(polylines, sampleCount = 12) {
      const lengths = polylines.map(polylineLength);
      const totalLength = lengths.reduce((sum, length) => sum + length, 0);
      if (totalLength <= 0) return polylines.flat();
      const samples = [];
      polylines.forEach((polyline, polylineIndex) => {
        const length = lengths[polylineIndex];
        if (length <= 0 || polyline.length < 2) return;
        const count = Math.max(2, Math.round(sampleCount * length / totalLength));
        const segmentLengths = [];
        for (let index = 1; index < polyline.length; index++) {
          segmentLengths.push(Math.hypot(polyline[index][0] - polyline[index - 1][0], polyline[index][1] - polyline[index - 1][1]));
        }
        for (let sampleIndex = 0; sampleIndex < count; sampleIndex++) {
          const target = (sampleIndex / Math.max(1, count - 1)) * length;
          let covered = 0;
          for (let segmentIndex = 0; segmentIndex < segmentLengths.length; segmentIndex++) {
            const segmentLength = segmentLengths[segmentIndex];
            if (covered + segmentLength >= target || segmentIndex === segmentLengths.length - 1) {
              const first = polyline[segmentIndex];
              const second = polyline[segmentIndex + 1];
              const ratio = segmentLength <= 0 ? 0 : (target - covered) / segmentLength;
              samples.push([
                first[0] + (second[0] - first[0]) * ratio,
                first[1] + (second[1] - first[1]) * ratio
              ]);
              break;
            }
            covered += segmentLength;
          }
        }
      });
      return samples;
    }

    function xySegments(polylines) {
      const segments = [];
      for (const polyline of polylines) {
        for (let index = 1; index < polyline.length; index++) {
          segments.push([polyline[index - 1], polyline[index]]);
        }
      }
      return segments;
    }

    function pointToSegmentDistance(point, segment) {
      const [first, second] = segment;
      const dx = second[0] - first[0];
      const dy = second[1] - first[1];
      const lengthSq = dx * dx + dy * dy;
      if (lengthSq <= 0) return Math.hypot(point[0] - first[0], point[1] - first[1]);
      const ratio = Math.max(0, Math.min(1, ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy) / lengthSq));
      const projected = [first[0] + dx * ratio, first[1] + dy * ratio];
      return Math.hypot(point[0] - projected[0], point[1] - projected[1]);
    }

    function averageNearestSegmentDistance(points, segments) {
      if (!points.length || !segments.length) return 1;
      return points.reduce((sum, point) => (
        sum + Math.min(...segments.map((segment) => pointToSegmentDistance(point, segment)))
      ), 0) / points.length;
    }

    function rotatePolylines(polylines, degrees) {
      if (!degrees) return polylines;
      const radians = degrees * Math.PI / 180;
      const cosValue = Math.cos(radians);
      const sinValue = Math.sin(radians);
      return polylines.map((polyline) => polyline.map((point) => [
        point[0] * cosValue - point[1] * sinValue,
        point[0] * sinValue + point[1] * cosValue
      ]));
    }

    function patchDistance(queryPolylines, candidatePolylines) {
      const queryPoints = samplePolylines(queryPolylines);
      const candidatePoints = samplePolylines(candidatePolylines);
      const querySegments = xySegments(queryPolylines);
      const candidateSegments = xySegments(candidatePolylines);
      const queryToCandidate = averageNearestSegmentDistance(queryPoints, candidateSegments);
      const candidateToQuery = averageNearestSegmentDistance(candidatePoints, querySegments);
      return (queryToCandidate * 0.65) + (candidateToQuery * 0.35);
    }

    function polylineParts(points, yAxisUp) {
      const bearings = [];
      const lengths = [];
      for (let index = 1; index < points.length; index++) {
        const first = points[index - 1];
        const second = points[index];
        const dx = second[0] - first[0];
        const dy = yAxisUp ? second[1] - first[1] : first[1] - second[1];
        const length = Math.hypot(dx, second[1] - first[1]);
        if (length <= 0) continue;
        bearings.push((Math.atan2(dx, dy) * 180 / Math.PI + 360) % 360);
        lengths.push(length);
      }
      return { bearings, lengths, totalLength: lengths.reduce((sum, length) => sum + length, 0) };
    }

    function sampleBearings(parts, sampleCount = 14) {
      if (!parts.bearings.length || parts.totalLength <= 0) return [];
      const samples = [];
      let currentLength = 0;
      let segmentIndex = 0;
      for (let sampleIndex = 0; sampleIndex < sampleCount; sampleIndex++) {
        const target = (sampleIndex / Math.max(1, sampleCount - 1)) * parts.totalLength;
        while (segmentIndex < parts.lengths.length - 1 && currentLength + parts.lengths[segmentIndex] < target) {
          currentLength += parts.lengths[segmentIndex];
          segmentIndex += 1;
        }
        samples.push(parts.bearings[segmentIndex]);
      }
      return samples;
    }

    function angleDelta(left, right) {
      return Math.abs((left - right + 180) % 360 - 180);
    }

    function bearingTracePenalty(queryStroke, roadCoords, rotation) {
      if (!queryStroke || queryStroke.length < 2 || !roadCoords || roadCoords.length < 2) return null;
      const queryPoints = queryStroke.map((point) => [point.x, point.y]);
      const querySamples = sampleBearings(polylineParts(queryPoints, false));
      if (!querySamples.length) return null;
      const centerLat = roadCoords.reduce((sum, coord) => sum + coord[0], 0) / roadCoords.length;
      const latScale = 111320;
      const lonScale = 111320 * Math.cos(centerLat * Math.PI / 180);
      const roadPoints = roadCoords.map((coord) => [coord[1] * lonScale, coord[0] * latScale]);
      let best = 180;
      const rotatedQuery = querySamples.map((angle) => (angle + rotation) % 360);
      for (const candidatePoints of [roadPoints, [...roadPoints].reverse()]) {
        const candidateSamples = sampleBearings(polylineParts(candidatePoints, true));
        if (!candidateSamples.length || candidateSamples.length !== rotatedQuery.length) continue;
        const penalty = rotatedQuery.reduce((sum, angle, index) => (
          sum + angleDelta(angle, candidateSamples[index])
        ), 0) / rotatedQuery.length;
        best = Math.min(best, penalty);
      }
      return best / 2;
    }

    function compareSelectedRoad() {
      if (!selectedDevRoad) {
        patternStatusEl.textContent = 'Enable Dev select road, then click a visible road first.';
        return;
      }
      const payloadStrokes = searchPayloadStrokes();
      const drawingGeometry = drawingCompareGeometry(payloadStrokes);
      const roadGeometry = roadCompareGeometry(selectedDevRoad);
      if (!drawingGeometry.length || !roadGeometry.length) {
        patternStatusEl.textContent = 'Draw a pattern and select a road before comparing.';
        return;
      }
      const rotationStep = preciseRotationEl.checked ? 10 : 90;
      const rotations = freeRotationEl.checked ? Array.from({ length: 360 / rotationStep }, (_value, index) => index * rotationStep) : [0];
      const comparisons = rotations.map((rotation) => {
        const distance = patchDistance(rotatePolylines(drawingGeometry, rotation), roadGeometry);
        const patchPenalty = distance * 180;
        const tracePenalty = payloadStrokes.length === 1 ? bearingTracePenalty(payloadStrokes[0], selectedDevRoad.coords, rotation) : null;
        const shapePenalty = tracePenalty === null ? patchPenalty : Math.min(patchPenalty, tracePenalty);
        return {
          rotation,
          patchPenalty: Number(patchPenalty.toFixed(3)),
          bearingTracePenalty: tracePenalty === null ? null : Number(tracePenalty.toFixed(3)),
          shapePenalty: Number(shapePenalty.toFixed(3)),
          score: Number(Math.max(0, 100 - shapePenalty).toFixed(1))
        };
      });
      comparisons.sort((left, right) => right.score - left.score);
      lastRoadCompareExport = {
        exportedAt: new Date().toISOString(),
        appMode: 'OSM Pattern Explorer dev road compare',
        request: {
          strokes: payloadStrokes,
          rawStrokes: patternStrokes,
          rotationInvariant: freeRotationEl.checked,
          rotationStep,
          roadGroups: selectedRoadGroups()
        },
        selectedRoad: selectedDevRoad,
        normalized: {
          drawing: drawingGeometry,
          road: roadGeometry
        },
        comparison: {
          best: comparisons[0],
          rotations: comparisons
        },
        annotation: {
          notes: ''
        }
      };
      patternStatusEl.textContent = `Selected road compare: ${comparisons[0].score}% at ${comparisons[0].rotation} deg. Export it if this route is the target.`;
      return lastRoadCompareExport;
    }

    function exportSelectedRoad() {
      if (!selectedDevRoad) {
        patternStatusEl.textContent = 'Enable Dev select road, then click a visible road first.';
        return;
      }
      const exportData = lastRoadCompareExport || compareSelectedRoad() || {
        exportedAt: new Date().toISOString(),
        appMode: 'OSM Pattern Explorer dev road export',
        selectedRoad: selectedDevRoad,
        normalized: {
          road: roadCompareGeometry(selectedDevRoad)
        },
        annotation: {
          notes: ''
        }
      };
      downloadJson('selected-road-compare', exportData);
      patternStatusEl.textContent = 'Selected road JSON exported.';
    }

    function renderPatternResults() {
      patternResultsLayer.clearLayers();
      patternResultsEl.innerHTML = '';

      if (!patternMatches.length) {
        patternResultsEl.textContent = 'No matches found.';
        patternMapsBarEl.style.display = 'none';
        return;
      }

      patternMatches.forEach((match, index) => {
        const selected = index === selectedPatternMatchIndex;
        for (const path of match.paths || []) {
          L.polyline(path, {
            color: selected ? '#2563eb' : '#dc2626',
            weight: selected ? 7 : 3,
            opacity: selected ? 0.92 : 0.35
          }).addTo(patternResultsLayer);
        }
        const icon = L.divIcon({
          className: '',
          html: `<div class="result-icon">${escapeHtml(match.score)}</div>`,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
          popupAnchor: [0, -14]
        });
        const marker = L.marker(match.coords, { icon }).addTo(patternResultsLayer);
        marker.on('click', () => selectPatternMatch(index));
        marker.bindPopup(
          `<strong>Pattern match ${escapeHtml(match.score)}%</strong><br>` +
          `OSM node ${escapeHtml(match.id)}<br>` +
          `${escapeHtml(match.degree)} branches<br>` +
          `${escapeHtml(match.roadTypes.join(', ') || 'road')}`
        );

        const button = document.createElement('button');
        button.className = `pattern-result${selected ? ' selected' : ''}`;
        button.innerHTML =
          `<strong>#${index + 1} - ${escapeHtml(match.score)}%</strong><br>` +
          `${escapeHtml(match.degree)} branches<br>` +
          `${escapeHtml(match.roadTypes.join(', ') || 'road')}`;
        button.addEventListener('click', () => selectPatternMatch(index));
        patternResultsEl.appendChild(button);
      });
    }

    function selectPatternMatch(index) {
      selectedPatternMatchIndex = index;
      const match = patternMatches[index];
      if (!match) return;
      renderPatternResults();
      const bounds = [];
      for (const path of match.paths || []) {
        bounds.push(...path);
      }
      if (bounds.length) {
        map.fitBounds(bounds, { padding: [42, 42], maxZoom: 18 });
      } else {
        map.setView(match.coords, 17);
      }
      const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${match.coords[0]},${match.coords[1]}`;
      patternMapsBarEl.innerHTML =
        `<strong>Match #${index + 1}: ${escapeHtml(match.score)}%</strong> ` +
        `${escapeHtml(match.coords[0].toFixed(6))}, ${escapeHtml(match.coords[1].toFixed(6))} - ` +
        `<a href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>`;
      patternMapsBarEl.style.display = 'block';
    }

    function showPatternResults(results) {
      patternMatches = results.matches || [];
      selectedPatternMatchIndex = -1;
      patternResultsPanelEl.classList.add('has-results');
      renderPatternResults();
      if (results.pattern.mode === 'road-layer-window') {
        patternStatusEl.textContent = `${results.matches.length} matches. Compared the drawing against visible OSM road lines first, then network patches.`;
      } else if (results.pattern.mode === 'network-patch') {
        patternStatusEl.textContent = `${results.matches.length} matches. Compared ${results.pattern.degree} drawn stroke(s) against local road-network patches.`;
      } else if (results.pattern.mode === 'free-trace') {
        patternStatusEl.textContent = `${results.matches.length} matches. Compared ${results.pattern.degree} drawn stroke(s) as full traces.`;
      } else {
        patternStatusEl.textContent =
          `${results.matches.length} matches. Pattern: ${results.pattern.degree} branches, angles ${results.pattern.angles.join(', ')}, turns ${results.pattern.branchTurns.join(', ')}.`;
      }
      if (patternMatches.length) {
        selectPatternMatch(0);
      }
    }

    function setMapFocus(enabled) {
      if (enabled) {
        setPatternFocus(false);
      }
      document.body.classList.toggle('map-focus', enabled);
      mapFocusToggleEl.textContent = enabled ? 'Show panel' : 'Full map';
      setTimeout(() => map.invalidateSize(), 0);
    }

    function normalizeRotation(value) {
      const parsed = Number.parseInt(value, 10);
      if (Number.isNaN(parsed)) return 0;
      return ((parsed % 360) + 360) % 360;
    }

    function baseMapPaneTransform() {
      const transform = map._mapPane.style.transform || '';
      return transform.replace(/\s*rotate\([^)]*\)/g, '').trim();
    }

    function applyMapPaneRotation() {
      if (!map._mapPane) return;
      const rotation = currentMapRotation();
      const baseTransform = baseMapPaneTransform();
      const panePosition = map._getMapPanePos ? map._getMapPanePos() : L.DomUtil.getPosition(map._mapPane);
      const size = map.getSize();
      const originX = size.x / 2 - panePosition.x;
      const originY = size.y / 2 - panePosition.y;

      map._mapPane.style.transformOrigin = `${originX}px ${originY}px`;
      map._mapPane.style.transform = rotation
        ? `${baseTransform} rotate(${rotation}deg)`.trim()
        : baseTransform;
      mapEl.classList.toggle('map-rotated', rotation !== 0);
    }

    function refreshRotationTiles() {
      map.invalidateSize({ pan: false });
      tileLayer.redraw();
      const size = map.getSize();
      const overscan = Math.ceil(Math.max(size.x, size.y) * 0.25);
      map.panBy([overscan, 0], { animate: false });
      map.panBy([-overscan, 0], { animate: false });
      map.panBy([0, overscan], { animate: false });
      map.panBy([0, -overscan], { animate: false });
      applyMapPaneRotation();
    }

    function setMapRotation(degrees, refreshTiles = true) {
      const normalized = normalizeRotation(degrees);
      mapRotationEl.value = String(normalized);
      mapRotationNumberEl.value = String(normalized);
      mapEl.style.setProperty('--map-rotation', `${normalized}deg`);
      applyMapPaneRotation();
      if (refreshTiles) {
        setTimeout(() => {
          refreshRotationTiles();
        }, 0);
      }
    }

    function setMapRotationControls(enabled) {
      mapRotationControlsEl.classList.toggle('active', enabled);
      document.getElementById('toggleMapRotation').textContent = enabled ? 'Hide rotation' : 'Rotate map';
      if (enabled) {
        setTimeout(refreshRotationTiles, 0);
      }
      if (!enabled) {
        dragMapRotationEl.checked = false;
        setDragMapRotation(false);
        setMapRotation(0);
      }
    }

    function mapPointerAngle(event) {
      const rect = mapEl.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      return (Math.atan2(event.clientY - centerY, event.clientX - centerX) * 180 / Math.PI + 360) % 360;
    }

    function currentMapRotation() {
      return normalizeRotation(mapRotationEl.value);
    }

    function setDragMapRotation(enabled) {
      mapEl.classList.toggle('rotate-drag-enabled', enabled);
      if (enabled) {
        map.dragging.disable();
      } else {
        isDraggingMapRotation = false;
        map.dragging.enable();
      }
    }

    function startMapRotationDrag(event) {
      if (!dragMapRotationEl.checked) return;
      event.preventDefault();
      isDraggingMapRotation = true;
      mapRotationDragOffset = currentMapRotation() - mapPointerAngle(event);
    }

    function continueMapRotationDrag(event) {
      if (!isDraggingMapRotation) return;
      event.preventDefault();
      setMapRotation(mapPointerAngle(event) + mapRotationDragOffset, false);
    }

    function stopMapRotationDrag() {
      if (isDraggingMapRotation) {
        setMapRotation(currentMapRotation(), true);
      }
      isDraggingMapRotation = false;
    }

    function setPatternFocus(enabled) {
      document.body.classList.toggle('pattern-focus', enabled);
      document.getElementById('focusPattern').textContent = enabled ? 'Small drawing' : 'Large drawing';
      setTimeout(drawPatternCanvas, 0);
      setTimeout(() => map.invalidateSize(), 0);
    }

    function startPatternPaint(event) {
      event.preventDefault();
      const point = canvasPoint(event);
      if (anglePointModeEl.checked) {
        const existing = nearestPatternPoint(point);
        if (existing) {
          selectedPatternPoint = existing;
          draggedPatternPoint = existing;
          activeAngleStroke = existing.stroke;
          patternCanvas.setPointerCapture(event.pointerId);
          drawPatternCanvas();
          return;
        }
        if (!activeAngleStroke) {
          activeAngleStroke = [point];
          patternStrokes.push(activeAngleStroke);
        } else if (pointDistancePx(activeAngleStroke[activeAngleStroke.length - 1], point) >= 4) {
          activeAngleStroke.push(point);
          selectedPatternPoint = {
            stroke: activeAngleStroke,
            index: activeAngleStroke.length - 1,
            point: activeAngleStroke[activeAngleStroke.length - 1]
          };
        }
        drawPatternCanvas();
        return;
      }
      activePatternStroke = [point];
      patternStrokes.push(activePatternStroke);
      isPaintingPattern = true;
      patternCanvas.setPointerCapture(event.pointerId);
      drawPatternCanvas();
    }

    function continuePatternPaint(event) {
      if (draggedPatternPoint) {
        event.preventDefault();
        const point = canvasPoint(event);
        draggedPatternPoint.stroke[draggedPatternPoint.index].x = point.x;
        draggedPatternPoint.stroke[draggedPatternPoint.index].y = point.y;
        draggedPatternPoint.point = draggedPatternPoint.stroke[draggedPatternPoint.index];
        selectedPatternPoint = draggedPatternPoint;
        drawPatternCanvas();
        return;
      }
      if (!isPaintingPattern) return;
      event.preventDefault();
      const point = canvasPoint(event);
      const last = activePatternStroke ? activePatternStroke[activePatternStroke.length - 1] : null;
      if (!last || pointDistancePx(last, point) >= 8) {
        if (!activePatternStroke) return;
        activePatternStroke.push(point);
        drawPatternCanvas();
      }
    }

    function stopPatternPaint(event) {
      if (draggedPatternPoint) {
        event.preventDefault();
        draggedPatternPoint = null;
        if (patternCanvas.hasPointerCapture(event.pointerId)) {
          patternCanvas.releasePointerCapture(event.pointerId);
        }
        drawPatternCanvas();
        return;
      }
      if (!isPaintingPattern) return;
      event.preventDefault();
      isPaintingPattern = false;
      activePatternStroke = null;
      if (patternCanvas.hasPointerCapture(event.pointerId)) {
        patternCanvas.releasePointerCapture(event.pointerId);
      }
    }

    async function searchPattern() {
      const segments = patternStrokes.reduce((total, stroke) => total + Math.max(0, stroke.length - 1), 0);
      if (segments < 2) {
        patternStatusEl.textContent = 'Draw at least two road segments before searching.';
        return;
      }
      const roadGroups = selectedRoadGroups();
      if (!roadGroups.length) {
        patternStatusEl.textContent = 'Select at least one road type before searching.';
        return;
      }
      const payloadStrokes = searchPayloadStrokes();
      const rotationStep = preciseRotationEl.checked ? 10 : 90;
      patternStatusEl.textContent = preciseRotationEl.checked
        ? 'Searching similar road patterns with 10 deg rotation. This can take about a minute...'
        : 'Searching similar road patterns...';
      const response = await fetch('/api/pattern-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strokes: payloadStrokes,
          rotationInvariant: freeRotationEl.checked,
          rotationStep,
          roadGroups
        })
      });
      if (!response.ok) {
        patternStatusEl.textContent = await response.text();
        return;
      }
      const results = await response.json();
      lastPatternSearchExport = {
        exportedAt: new Date().toISOString(),
        appMode: 'OSM Pattern Explorer',
        request: {
          strokes: payloadStrokes,
          rawStrokes: patternStrokes,
          smoothStrokeIndexes: patternStrokes.map((stroke, index) => smoothPatternStrokes.has(stroke) ? index : null).filter((index) => index !== null),
          rotationInvariant: freeRotationEl.checked,
          rotationStep,
          roadGroups
        },
        response: results,
        selectedMatchIndex: -1,
        selectedMatch: null,
        annotation: {
          correctMatchIndex: null,
          notes: ''
        }
      };
      showPatternResults(results);
    }

    function buildPointFilters() {
      pointFiltersEl.innerHTML = '';
      enabledPointKinds.clear();
      const groups = {};
      for (const [kind, meta] of Object.entries(payload.pointKinds || {})) {
        const count = payload.stats.pointKinds[kind] || 0;
        if (!count) continue;
        const group = meta.group || 'Other';
        if (!groups[group]) {
          groups[group] = [];
        }
        groups[group].push([kind, meta, count]);
      }

      for (const [group, entries] of Object.entries(groups)) {
        const section = document.createElement('details');
        section.className = 'point-filter-group';
        section.open = group === 'Signs';
        const total = entries.reduce((sum, entry) => sum + entry[2], 0);
        const summary = document.createElement('summary');
        summary.textContent = `${group} (${total.toLocaleString()})`;
        section.appendChild(summary);
        const options = document.createElement('div');
        options.className = 'point-filter-options';

        for (const [kind, meta, count] of entries) {
          const label = document.createElement('label');
          label.title = `${meta.label}: ${count.toLocaleString()} points`;
          label.innerHTML = `<input type="checkbox" data-kind="${escapeHtml(kind)}"> `
            + layerIconHtml(meta)
            + `${escapeHtml(meta.label)} (${count.toLocaleString()})`;
          label.querySelector('input').addEventListener('change', (event) => {
            if (event.target.checked) enabledPointKinds.add(kind);
            else enabledPointKinds.delete(kind);
            redraw();
          });
          options.appendChild(label);
        }
        section.appendChild(options);
        pointFiltersEl.appendChild(section);
      }
    }

    function setAllLayers(checked) {
      roadsEl.checked = checked;
      areasEl.checked = checked;
      enabledPointKinds.clear();
      for (const input of pointFiltersEl.querySelectorAll('input[data-kind]')) {
        input.checked = checked;
        if (checked) {
          enabledPointKinds.add(input.dataset.kind);
        }
      }
      redraw();
    }

    function drawChunk(items, start, batchSize, drawItem, done, version) {
      if (version !== drawingVersion) return;
      const end = Math.min(start + batchSize, items.length);
      for (let i = start; i < end; i++) {
        drawItem(items[i]);
      }
      if (end < items.length) {
        statusEl.innerHTML = `${payload.stats.elements.toLocaleString()} OSM elements<br>Drawing ${end.toLocaleString()} / ${items.length.toLocaleString()} visible features...`;
        setTimeout(() => drawChunk(items, end, batchSize, drawItem, done, version), 0);
      } else {
        done();
      }
    }

    function redraw() {
      if (!payload) return;
      drawingVersion += 1;
      const version = drawingVersion;
      clearLayers();

      const visibleRoads = roadsEl.checked ? payload.roads.filter(matchesFilter) : [];
      const visibleAreas = areasEl.checked ? payload.areas.filter(matchesFilter) : [];
      const visiblePoints = payload.points.filter((point) => enabledPointKinds.has(point.kind) && matchesFilter(point));
      const allVisible = [
        ...visibleAreas.map((item) => ['area', item]),
        ...visibleRoads.map((item) => ['road', item]),
        ...visiblePoints.map((item) => ['point', item])
      ];

      function drawEntry(entry) {
        const [type, item] = entry;
        if (type === 'area') {
          bindFeature(L.polygon(item.coords, {
            renderer,
            color: '#777',
            weight: 1,
            fillColor: '#9ecae1',
            fillOpacity: 0.22
          }), item, type).addTo(areasLayer);
          return;
        }
        if (type === 'road') {
          bindFeature(L.polyline(item.coords, {
            renderer,
            color: item.color || '#555',
            weight: 4,
            opacity: 0.92
          }), item, type).addTo(roadsLayer);
          return;
        }
        const icon = L.divIcon({
          className: '',
          html: `<div class="poi-icon" style="background:${escapeHtml(item.color || '#ca8a04')}">${pointMarkerIconHtml(item)}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
          popupAnchor: [0, -12]
        });
        bindFeature(L.marker(item.coords, { icon }), item, type).addTo(pointsLayer);
      }

      drawChunk(allVisible, 0, 300, drawEntry, () => {
        if (version !== drawingVersion) return;
        statusEl.innerHTML =
          `${payload.stats.elements.toLocaleString()} OSM elements<br>` +
          `${visibleRoads.length.toLocaleString()} roads, ` +
          `${visibleAreas.length.toLocaleString()} areas, ` +
          `${visiblePoints.length.toLocaleString()} points visible`;
      }, version);
    }

    function fitMap() {
      if (payload && payload.bounds.length) {
        map.fitBounds(payload.bounds, { padding: [24, 24] });
      }
    }

    async function loadData() {
      const response = await fetch('/api/map-data');
      if (!response.ok) throw new Error(await response.text());
      payload = await response.json();
      buildPointFilters();
      statusEl.innerHTML =
        `${payload.stats.elements.toLocaleString()} OSM elements<br>` +
        `${payload.stats.roads.toLocaleString()} roads, ` +
        `${payload.stats.areas.toLocaleString()} areas, ` +
        `${payload.stats.points.toLocaleString()} points`;
      fitMap();
      redraw();
    }

    document.getElementById('fit').addEventListener('click', fitMap);
    document.getElementById('focusMap').addEventListener('click', () => setMapFocus(true));
    document.getElementById('toggleMapRotation').addEventListener('click', () => {
      setMapRotationControls(!mapRotationControlsEl.classList.contains('active'));
    });
    mapRotationEl.addEventListener('input', () => setMapRotation(mapRotationEl.value));
    mapRotationNumberEl.addEventListener('change', () => setMapRotation(mapRotationNumberEl.value));
    dragMapRotationEl.addEventListener('change', () => setDragMapRotation(dragMapRotationEl.checked));
    document.getElementById('resetMapRotation').addEventListener('click', () => setMapRotation(0));
    mapEl.addEventListener('pointerdown', startMapRotationDrag);
    window.addEventListener('pointermove', continueMapRotationDrag);
    window.addEventListener('pointerup', stopMapRotationDrag);
    window.addEventListener('pointercancel', stopMapRotationDrag);
    map.on('move zoom zoomend moveend resize', applyMapPaneRotation);
    document.getElementById('uncheckAllLayers').addEventListener('click', () => setAllLayers(false));
    document.getElementById('checkAllLayers').addEventListener('click', () => setAllLayers(true));
    mapFocusToggleEl.addEventListener('click', () => setMapFocus(!document.body.classList.contains('map-focus')));
    document.getElementById('focusPattern').addEventListener('click', () => {
      setPatternFocus(!document.body.classList.contains('pattern-focus'));
    });
    document.getElementById('undoPattern').addEventListener('click', undoPattern);
    document.getElementById('clearPattern').addEventListener('click', clearPattern);
    document.getElementById('finishAngleStroke').addEventListener('click', finishAngleStroke);
    document.getElementById('addPatternMidpoint').addEventListener('click', addPatternMidpoint);
    document.getElementById('smoothPatternStroke').addEventListener('click', () => setStrokeSmooth(true));
    document.getElementById('straightPatternStroke').addEventListener('click', () => setStrokeSmooth(false));
    anglePointModeEl.addEventListener('change', () => {
      activeAngleStroke = null;
      selectedPatternPoint = null;
      draggedPatternPoint = null;
      patternStatusEl.textContent = anglePointModeEl.checked
        ? 'Angle points: click to add vertices, drag existing points to edit, Finish line starts a new stroke.'
        : 'Free draw: drag to draw road shapes freely.';
      drawPatternCanvas();
    });
    document.getElementById('deletePatternPoint').addEventListener('click', deleteSelectedPatternPoint);
    document.getElementById('searchPattern').addEventListener('click', () => {
      searchPattern().catch((error) => {
        patternStatusEl.textContent = 'Pattern search failed: ' + error.message;
      });
    });
    document.getElementById('exportPatternSearch').addEventListener('click', exportPatternSearch);
    document.getElementById('compareSelectedRoad').addEventListener('click', compareSelectedRoad);
    document.getElementById('exportSelectedRoad').addEventListener('click', exportSelectedRoad);
    devRoadSelectEl.addEventListener('change', () => {
      patternStatusEl.textContent = devRoadSelectEl.checked
        ? 'Dev road selection enabled. Keep Roads checked, then click a visible road.'
        : 'Dev road selection disabled.';
    });
    document.getElementById('photoInput').addEventListener('change', (event) => {
      const file = event.target.files[0];
      if (!file) return;
      const image = new Image();
      image.onload = () => {
        patternImage = image;
        drawPatternCanvas();
      };
      image.src = URL.createObjectURL(file);
    });
    patternCanvas.addEventListener('pointerdown', startPatternPaint);
    patternCanvas.addEventListener('pointermove', continuePatternPaint);
    patternCanvas.addEventListener('pointerup', stopPatternPaint);
    patternCanvas.addEventListener('pointercancel', stopPatternPaint);
    new ResizeObserver(drawPatternCanvas).observe(patternCanvas);
    filterEl.addEventListener('input', redraw);
    roadsEl.addEventListener('change', () => {
      if (!roadsEl.checked) {
        selectedDevRoad = null;
        lastRoadCompareExport = null;
        devRoadSelectionLayer.clearLayers();
      }
      redraw();
    });
    areasEl.addEventListener('change', redraw);
    drawPatternCanvas();

    loadData().catch((error) => {
      statusEl.textContent = 'Failed to load local API data: ' + error.message;
      map.setView([43.2153, 5.5389], 13);
    });
  </script>
</body>
</html>
"""


class LocalApiHandler(BaseHTTPRequestHandler):
    app: "OsmInfoApp"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_bytes(body, "application/json; charset=utf-8", status)

    def send_error_text(self, message: str, status: int = 500) -> None:
        self.send_bytes(message.encode("utf-8"), "text/plain; charset=utf-8", status)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_bytes(WEB_APP_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/api/status":
            self.send_json(
                {
                    "ready": bool(self.app.osm_data.get("elements")) or Path(DEFAULT_JSON_FILE).exists(),
                    "elements": len(self.app.osm_data.get("elements", [])),
                }
            )
            return

        if path == "/api/map-data":
            try:
                payload = self.app.get_or_build_map_payload()
            except Exception as exc:
                self.send_error_text(str(exc), 500)
                return
            self.send_json(payload)
            return

        self.send_error_text("Not found", 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/pattern-search":
            self.send_error_text("Not found", 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            request_body = self.rfile.read(content_length)
            request_json = json.loads(request_body.decode("utf-8"))
            result = self.app.search_pattern(
                {
                    "points": request_json.get("points", []),
                    "edges": request_json.get("edges", []),
                    "strokes": request_json.get("strokes", []),
                },
                rotation_invariant=bool(request_json.get("rotationInvariant", True)),
                rotation_step_degrees=int(request_json.get("rotationStep", 90)),
                allowed_road_groups=request_json.get("roadGroups", []),
            )
        except Exception as exc:
            self.send_error_text(str(exc), 400)
            return

        self.send_json(result)


def find_free_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError("No available localhost port found.")
