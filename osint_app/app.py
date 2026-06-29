import threading
import json
from http.server import ThreadingHTTPServer
from pathlib import Path

from .config import DEFAULT_JSON_FILE, LOCALHOST_HOST, LOCALHOST_PORT
from .osm import build_map_payload, fetch_osm_data, load_osm_json
from .pattern import build_road_pattern_index, search_road_pattern
from .web import LocalApiHandler, find_free_port, open_browser_url


class OsmInfoApp:
    def __init__(self) -> None:
        self.osm_data: dict = {"elements": []}
        self.map_payload_cache: dict | None = None
        self.pattern_index_cache: dict | None = None
        self.server: ThreadingHTTPServer | None = None
        self.server_thread: threading.Thread | None = None
        self.server_url = ""

    def start_local_server(self) -> str:
        if self.server:
            return self.server_url

        port = find_free_port(LOCALHOST_HOST, LOCALHOST_PORT)
        LocalApiHandler.app = self
        self.server = ThreadingHTTPServer((LOCALHOST_HOST, port), LocalApiHandler)
        self.server_url = f"http://{LOCALHOST_HOST}:{port}/"
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        return self.server_url

    def stop_local_server(self) -> None:
        if not self.server:
            return
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self.server_thread = None

    def open_map(self) -> bool:
        if not self.server_url:
            self.start_local_server()
        return open_browser_url(self.server_url)

    def get_or_build_map_payload(self) -> dict:
        if self.map_payload_cache is not None:
            return self.map_payload_cache

        if self.osm_data.get("elements"):
            data = self.osm_data
        elif Path(DEFAULT_JSON_FILE).exists():
            data = load_osm_json(DEFAULT_JSON_FILE)
            self.osm_data = data
        else:
            raise FileNotFoundError("No OSM data loaded and osm_data.json was not found.")

        self.map_payload_cache = build_map_payload(data)
        return self.map_payload_cache

    def invalidate_map_cache(self) -> None:
        self.map_payload_cache = None
        self.pattern_index_cache = None

    def fetch_osm_area(self, lat: float, lon: float, radius: int) -> dict:
        if not -90 <= lat <= 90:
            raise ValueError("Latitude must be between -90 and 90.")
        if not -180 <= lon <= 180:
            raise ValueError("Longitude must be between -180 and 180.")
        if not 1 <= radius <= 50000:
            raise ValueError("Use a radius between 1 and 50000 meters.")

        data = fetch_osm_data(lat, lon, radius)
        data["_fetch_area"] = {"lat": lat, "lon": lon, "radius": radius}
        with open(DEFAULT_JSON_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        self.osm_data = data
        self.invalidate_map_cache()
        return self.get_or_build_map_payload()

    def search_pattern(
        self,
        pattern: dict,
        rotation_invariant: bool = True,
        rotation_step_degrees: int = 90,
        allowed_road_groups: list[str] | None = None,
    ) -> dict:
        if self.pattern_index_cache is None:
            data = self.osm_data if self.osm_data.get("elements") else load_osm_json(DEFAULT_JSON_FILE)
            self.pattern_index_cache = build_road_pattern_index(data)
        return search_road_pattern(
            self.pattern_index_cache,
            pattern,
            rotation_invariant=rotation_invariant,
            rotation_step_degrees=rotation_step_degrees,
            allowed_road_groups=allowed_road_groups,
        )
