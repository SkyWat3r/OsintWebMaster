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
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5px 8px;
      margin: 8px 0;
      padding: 8px 0;
      border-top: 1px solid #ddd;
      border-bottom: 1px solid #ddd;
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
    #photoInput {
      width: 100%;
      box-sizing: border-box;
    }
    .section {
      border-top: 1px solid #ddd;
      margin-top: 10px;
      padding-top: 10px;
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
    <input id="filter" type="text" placeholder="Filter names, tags, road types">
    <div class="row">
      <button id="fit">Fit</button>
      <button id="focusMap">Full map</button>
      <label><input id="roads" type="checkbox" checked> Roads</label>
      <label><input id="areas" type="checkbox" checked> Areas</label>
    </div>
    <div class="stat">Point layers</div>
    <div id="pointFilters"></div>
    <div class="section">
      <div class="stat"><strong>Pattern search</strong></div>
      <input id="photoInput" type="file" accept="image/*">
      <canvas id="patternCanvas" width="340" height="230"></canvas>
      <div class="row">
        <button id="undoPattern">Undo</button>
        <button id="clearPattern">Clear</button>
        <button id="searchPattern">Search</button>
      </div>
      <label><input id="freeRotation" type="checkbox" checked> Free rotation</label>
      <div id="patternStatus" class="stat">Click to trace roads. Two-segment points are treated as bends; 3+ segment points are intersections.</div>
    </div>
    <div id="details">Click a road, area, or point to inspect tags.</div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map', { preferCanvas: true });
    const renderer = L.canvas({ padding: 0.5 });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const statusEl = document.getElementById('status');
    const detailsEl = document.getElementById('details');
    const filterEl = document.getElementById('filter');
    const roadsEl = document.getElementById('roads');
    const areasEl = document.getElementById('areas');
    const pointFiltersEl = document.getElementById('pointFilters');
    const patternCanvas = document.getElementById('patternCanvas');
    const patternCtx = patternCanvas.getContext('2d');
    const patternStatusEl = document.getElementById('patternStatus');
    const freeRotationEl = document.getElementById('freeRotation');
    const mapFocusToggleEl = document.getElementById('mapFocusToggle');

    const roadsLayer = L.layerGroup().addTo(map);
    const areasLayer = L.layerGroup().addTo(map);
    const pointsLayer = L.layerGroup().addTo(map);
    const patternResultsLayer = L.layerGroup().addTo(map);
    let payload = null;
    let drawingVersion = 0;
    let selectedPatternPointId = null;
    let patternImage = null;
    const enabledPointKinds = new Set();
    const patternPoints = [];
    const patternEdges = [];

    function matchesFilter(item) {
      const filter = filterEl.value.trim().toLowerCase();
      if (!filter) return true;
      return `${item.name} ${item.category} ${item.details}`.toLowerCase().includes(filter);
    }

    function bindFeature(layer, item) {
      layer.on('click', () => {
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

    function clearLayers() {
      roadsLayer.clearLayers();
      areasLayer.clearLayers();
      pointsLayer.clearLayers();
    }

    function canvasPoint(event) {
      const rect = patternCanvas.getBoundingClientRect();
      return {
        x: (event.clientX - rect.left) * (patternCanvas.width / rect.width),
        y: (event.clientY - rect.top) * (patternCanvas.height / rect.height)
      };
    }

    function nearestPatternPoint(point) {
      let nearest = null;
      let nearestDistance = 14;
      for (const existing of patternPoints) {
        const distance = Math.hypot(existing.x - point.x, existing.y - point.y);
        if (distance < nearestDistance) {
          nearest = existing;
          nearestDistance = distance;
        }
      }
      return nearest;
    }

    function edgeExists(from, to) {
      return patternEdges.some((edge) => (edge.from === from && edge.to === to) || (edge.from === to && edge.to === from));
    }

    function addPatternPoint(point) {
      const newPoint = { id: `p${Date.now()}${patternPoints.length}`, x: point.x, y: point.y };
      patternPoints.push(newPoint);
      if (selectedPatternPointId && selectedPatternPointId !== newPoint.id) {
        patternEdges.push({ from: selectedPatternPointId, to: newPoint.id });
      }
      selectedPatternPointId = newPoint.id;
      drawPatternCanvas();
    }

    function selectOrConnectPatternPoint(point) {
      const existing = nearestPatternPoint(point);
      if (!existing) {
        addPatternPoint(point);
        return;
      }
      if (selectedPatternPointId && selectedPatternPointId !== existing.id && !edgeExists(selectedPatternPointId, existing.id)) {
        patternEdges.push({ from: selectedPatternPointId, to: existing.id });
      }
      selectedPatternPointId = existing.id;
      drawPatternCanvas();
    }

    function drawPatternCanvas() {
      patternCtx.clearRect(0, 0, patternCanvas.width, patternCanvas.height);
      if (patternImage) {
        const scale = Math.min(patternCanvas.width / patternImage.width, patternCanvas.height / patternImage.height);
        const width = patternImage.width * scale;
        const height = patternImage.height * scale;
        patternCtx.globalAlpha = 0.58;
        patternCtx.drawImage(patternImage, (patternCanvas.width - width) / 2, (patternCanvas.height - height) / 2, width, height);
        patternCtx.globalAlpha = 1;
      }
      patternCtx.lineWidth = 4;
      patternCtx.strokeStyle = '#dc2626';
      patternCtx.lineCap = 'round';
      const byId = Object.fromEntries(patternPoints.map((point) => [point.id, point]));
      for (const edge of patternEdges) {
        const from = byId[edge.from];
        const to = byId[edge.to];
        if (!from || !to) continue;
        patternCtx.beginPath();
        patternCtx.moveTo(from.x, from.y);
        patternCtx.lineTo(to.x, to.y);
        patternCtx.stroke();
      }
      for (const point of patternPoints) {
        patternCtx.beginPath();
        patternCtx.arc(point.x, point.y, point.id === selectedPatternPointId ? 7 : 5, 0, Math.PI * 2);
        patternCtx.fillStyle = point.id === selectedPatternPointId ? '#2563eb' : '#111827';
        patternCtx.fill();
        patternCtx.strokeStyle = '#fff';
        patternCtx.lineWidth = 2;
        patternCtx.stroke();
      }
      patternStatusEl.textContent = `${patternPoints.length} points, ${patternEdges.length} segments`;
    }

    function clearPattern() {
      patternPoints.length = 0;
      patternEdges.length = 0;
      selectedPatternPointId = null;
      patternResultsLayer.clearLayers();
      drawPatternCanvas();
    }

    function undoPattern() {
      if (patternEdges.length) {
        patternEdges.pop();
      } else if (patternPoints.length) {
        const removed = patternPoints.pop();
        for (let index = patternEdges.length - 1; index >= 0; index--) {
          if (patternEdges[index].from === removed.id || patternEdges[index].to === removed.id) {
            patternEdges.splice(index, 1);
          }
        }
        selectedPatternPointId = patternPoints.length ? patternPoints[patternPoints.length - 1].id : null;
      }
      drawPatternCanvas();
    }

    function showPatternResults(results) {
      patternResultsLayer.clearLayers();
      for (const match of results.matches) {
        const icon = L.divIcon({
          className: '',
          html: `<div class="result-icon">${escapeHtml(match.score)}</div>`,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
          popupAnchor: [0, -14]
        });
        const marker = L.marker(match.coords, { icon }).addTo(patternResultsLayer);
        marker.bindPopup(
          `<strong>Pattern match ${escapeHtml(match.score)}%</strong><br>` +
          `OSM node ${escapeHtml(match.id)}<br>` +
          `${escapeHtml(match.degree)} branches<br>` +
          `${escapeHtml(match.roadTypes.join(', ') || 'road')}`
        );
      }
      if (results.matches.length) {
        map.fitBounds(results.matches.map((match) => match.coords), { padding: [32, 32] });
      }
      patternStatusEl.textContent =
        `${results.matches.length} matches. Pattern: ${results.pattern.degree} branches, angles ${results.pattern.angles.join(', ')}, turns ${results.pattern.branchTurns.join(', ')}.`;
    }

    function setMapFocus(enabled) {
      document.body.classList.toggle('map-focus', enabled);
      mapFocusToggleEl.textContent = enabled ? 'Show panel' : 'Full map';
      setTimeout(() => map.invalidateSize(), 0);
    }

    async function searchPattern() {
      if (patternEdges.length < 2) {
        patternStatusEl.textContent = 'Draw at least two connected road segments before searching.';
        return;
      }
      patternStatusEl.textContent = 'Searching similar road patterns...';
      const response = await fetch('/api/pattern-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          points: patternPoints,
          edges: patternEdges,
          rotationInvariant: freeRotationEl.checked
        })
      });
      if (!response.ok) {
        patternStatusEl.textContent = await response.text();
        return;
      }
      showPatternResults(await response.json());
    }

    function buildPointFilters() {
      pointFiltersEl.innerHTML = '';
      enabledPointKinds.clear();
      for (const [kind, meta] of Object.entries(payload.pointKinds || {})) {
        const count = payload.stats.pointKinds[kind] || 0;
        if (!count) continue;
        const checked = meta.default !== false;
        if (checked) enabledPointKinds.add(kind);
        const label = document.createElement('label');
        label.title = `${meta.label}: ${count.toLocaleString()} points`;
        label.innerHTML = `<input type="checkbox" ${checked ? 'checked' : ''} data-kind="${escapeHtml(kind)}"> `
          + `<span style="color:${escapeHtml(meta.color)}; font-weight:700">${escapeHtml(meta.icon)}</span> `
          + `${escapeHtml(meta.label)} (${count.toLocaleString()})`;
        label.querySelector('input').addEventListener('change', (event) => {
          if (event.target.checked) enabledPointKinds.add(kind);
          else enabledPointKinds.delete(kind);
          redraw();
        });
        pointFiltersEl.appendChild(label);
      }
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
          }), item).addTo(areasLayer);
          return;
        }
        if (type === 'road') {
          bindFeature(L.polyline(item.coords, {
            renderer,
            color: item.color || '#555',
            weight: 4,
            opacity: 0.92
          }), item).addTo(roadsLayer);
          return;
        }
        const icon = L.divIcon({
          className: '',
          html: `<div class="poi-icon" style="background:${escapeHtml(item.color || '#ca8a04')}">${escapeHtml(item.icon || '•')}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
          popupAnchor: [0, -12]
        });
        bindFeature(L.marker(item.coords, { icon }), item).addTo(pointsLayer);
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
    mapFocusToggleEl.addEventListener('click', () => setMapFocus(!document.body.classList.contains('map-focus')));
    document.getElementById('undoPattern').addEventListener('click', undoPattern);
    document.getElementById('clearPattern').addEventListener('click', clearPattern);
    document.getElementById('searchPattern').addEventListener('click', () => {
      searchPattern().catch((error) => {
        patternStatusEl.textContent = 'Pattern search failed: ' + error.message;
      });
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
    patternCanvas.addEventListener('click', (event) => {
      selectOrConnectPatternPoint(canvasPoint(event));
    });
    filterEl.addEventListener('input', redraw);
    roadsEl.addEventListener('change', redraw);
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
                },
                rotation_invariant=bool(request_json.get("rotationInvariant", True)),
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
