import json
import threading
import tkinter as tk
from http.server import ThreadingHTTPServer
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.error import HTTPError, URLError

from .config import (
    DEFAULT_JSON_FILE,
    DEFAULT_LAT,
    DEFAULT_LON,
    DEFAULT_RADIUS,
    LOCALHOST_HOST,
    LOCALHOST_PORT,
    MAP_FILE,
)
from .osm import build_map_payload, element_category, element_details, element_name, fetch_osm_data, load_osm_json
from .web import LocalApiHandler, find_free_port, open_browser_url, open_html_file, write_leaflet_map

class OsmInfoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OSINT OpenStreetMap Explorer")
        self.geometry("1180x760")
        self.minsize(980, 620)

        self.osm_data: dict = {"elements": []}
        self.map_payload_cache: dict | None = None
        self.server: ThreadingHTTPServer | None = None
        self.server_url = ""
        self.elements_by_tree_id: dict[str, dict] = {}

        self.lat_var = tk.StringVar(value=DEFAULT_LAT)
        self.lon_var = tk.StringVar(value=DEFAULT_LON)
        self.radius_var = tk.StringVar(value=DEFAULT_RADIUS)
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="No data loaded")
        self.server_var = tk.StringVar(value="Local site: starting...")
        self.filter_var = tk.StringVar()

        self._build_ui()
        self.start_local_server()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self, padding=10)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(10, weight=1)

        ttk.Label(controls, text="Latitude").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(controls, textvariable=self.lat_var, width=12).grid(row=0, column=1, padx=(0, 12))

        ttk.Label(controls, text="Longitude").grid(row=0, column=2, padx=(0, 4))
        ttk.Entry(controls, textvariable=self.lon_var, width=12).grid(row=0, column=3, padx=(0, 12))

        ttk.Label(controls, text="Radius (m)").grid(row=0, column=4, padx=(0, 4))
        ttk.Entry(controls, textvariable=self.radius_var, width=9).grid(row=0, column=5, padx=(0, 12))

        self.fetch_button = ttk.Button(controls, text="Fetch OSM data", command=self.fetch_data)
        self.fetch_button.grid(row=0, column=6, padx=(0, 8))

        ttk.Button(controls, text="Load OSM JSON", command=self.load_json).grid(row=0, column=7, padx=(0, 8))
        ttk.Button(controls, text="Save JSON", command=self.save_json).grid(row=0, column=8, padx=(0, 8))
        ttk.Button(controls, text="Open Map", command=self.open_map).grid(row=0, column=9, padx=(0, 8))
        ttk.Button(controls, text="Export HTML Map", command=self.export_html_map).grid(row=0, column=10, padx=(0, 12))

        ttk.Label(controls, text="Filter").grid(row=0, column=11, padx=(0, 4))
        filter_entry = ttk.Entry(controls, textvariable=self.filter_var, width=28)
        filter_entry.grid(row=0, column=12, sticky="e")
        self.filter_var.trace_add("write", lambda *_: self.populate_table())

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        table_frame = ttk.Frame(body)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        body.add(table_frame, weight=3)

        columns = ("type", "id", "name", "category", "tags")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("type", text="Type")
        self.tree.heading("id", text="OSM ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("tags", text="Tags")
        self.tree.column("type", width=80, anchor="w")
        self.tree.column("id", width=110, anchor="w")
        self.tree.column("name", width=240, anchor="w")
        self.tree.column("category", width=190, anchor="w")
        self.tree.column("tags", width=70, anchor="e")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.show_selected_element)

        table_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        table_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=table_scroll.set)

        details_frame = ttk.Frame(body)
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(1, weight=1)
        body.add(details_frame, weight=2)

        ttk.Label(details_frame, textvariable=self.summary_var).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.details = tk.Text(details_frame, wrap="word", height=20)
        self.details.grid(row=1, column=0, sticky="nsew")
        details_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details.yview)
        details_scroll.grid(row=1, column=1, sticky="ns")
        self.details.configure(yscrollcommand=details_scroll.set)

        footer = ttk.Frame(self, padding=(10, 0, 10, 8))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(footer, textvariable=self.server_var).grid(row=0, column=1, sticky="e")

    def start_local_server(self) -> None:
        try:
            port = find_free_port(LOCALHOST_HOST, LOCALHOST_PORT)
            LocalApiHandler.app = self
            self.server = ThreadingHTTPServer((LOCALHOST_HOST, port), LocalApiHandler)
        except OSError as exc:
            self.server_var.set("Local site: failed")
            messagebox.showerror("Local server failed", str(exc))
            return

        self.server_url = f"http://{LOCALHOST_HOST}:{port}/"
        self.server_var.set(f"Local site: {self.server_url}")
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.after(500, self.open_map)

    def on_close(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.destroy()

    def get_or_build_map_payload(self) -> dict:
        if self.map_payload_cache is not None:
            return self.map_payload_cache

        if self.osm_data.get("elements"):
            data = self.osm_data
        elif Path(DEFAULT_JSON_FILE).exists():
            data = load_osm_json(DEFAULT_JSON_FILE)
            self.osm_data = data
            self.after(0, lambda: self.summary_var.set(f"{len(data.get('elements', []))} OSM elements available from {DEFAULT_JSON_FILE}"))
        else:
            raise FileNotFoundError("No OSM data loaded and osm_data.json was not found.")

        self.map_payload_cache = build_map_payload(data)
        return self.map_payload_cache

    def invalidate_map_cache(self) -> None:
        self.map_payload_cache = None

    def fetch_data(self) -> None:
        try:
            lat = float(self.lat_var.get().strip())
            lon = float(self.lon_var.get().strip())
            radius = int(self.radius_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Latitude, longitude and radius must be valid numbers.")
            return

        if not 1 <= radius <= 50000:
            messagebox.showerror("Invalid radius", "Use a radius between 1 and 50000 meters.")
            return

        self.fetch_button.configure(state=tk.DISABLED)
        self.status_var.set("Fetching data from OpenStreetMap via Overpass...")
        self.summary_var.set("Loading...")
        self.details.delete("1.0", tk.END)

        thread = threading.Thread(target=self._fetch_worker, args=(lat, lon, radius), daemon=True)
        thread.start()

    def _fetch_worker(self, lat: float, lon: float, radius: int) -> None:
        try:
            data = fetch_osm_data(lat, lon, radius)
        except (HTTPError, URLError, TimeoutError) as exc:
            self.after(0, lambda: self._fetch_failed(str(exc)))
            return
        except json.JSONDecodeError:
            self.after(0, lambda: self._fetch_failed("The Overpass response was not valid JSON."))
            return

        self.after(0, lambda: self._fetch_succeeded(data))

    def _fetch_succeeded(self, data: dict) -> None:
        self.osm_data = data
        self.invalidate_map_cache()
        self.populate_table()
        self.fetch_button.configure(state=tk.NORMAL)
        self.status_var.set("Data loaded")

    def _fetch_failed(self, message: str) -> None:
        self.fetch_button.configure(state=tk.NORMAL)
        self.status_var.set("Fetch failed")
        self.summary_var.set("No data loaded")
        messagebox.showerror("OpenStreetMap request failed", message)

    def load_json(self) -> None:
        initial_file = DEFAULT_JSON_FILE if Path(DEFAULT_JSON_FILE).exists() else ""
        filename = filedialog.askopenfilename(
            title="Load OSM JSON",
            initialfile=initial_file,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not filename:
            return

        self.status_var.set(f"Loading {filename}...")
        thread = threading.Thread(target=self._load_json_worker, args=(filename,), daemon=True)
        thread.start()

    def _load_json_worker(self, filename: str) -> None:
        try:
            data = load_osm_json(filename)
        except (OSError, json.JSONDecodeError) as exc:
            self.after(0, lambda: self._load_failed(str(exc)))
            return

        self.after(0, lambda: self._load_succeeded(data, filename))

    def _load_succeeded(self, data: dict, filename: str) -> None:
        self.osm_data = data
        self.invalidate_map_cache()
        self.populate_table()
        self.status_var.set(f"Loaded {filename}")

    def _load_failed(self, message: str) -> None:
        self.status_var.set("Load failed")
        messagebox.showerror("Could not load OSM JSON", message)

    def populate_table(self) -> None:
        filter_text = self.filter_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.elements_by_tree_id.clear()

        elements = self.osm_data.get("elements", [])
        tagged_elements = [element for element in elements if element.get("tags")]

        for element in tagged_elements:
            serialized = json.dumps(element, ensure_ascii=False).lower()
            if filter_text and filter_text not in serialized:
                continue

            tags = element.get("tags") or {}
            item_id = self.tree.insert(
                "",
                tk.END,
                values=(
                    element.get("type", ""),
                    element.get("id", ""),
                    element_name(element),
                    element_category(element),
                    len(tags),
                ),
            )
            self.elements_by_tree_id[item_id] = element

        visible_count = len(self.elements_by_tree_id)
        self.summary_var.set(
            f"{visible_count} tagged elements shown / {len(tagged_elements)} tagged / {len(elements)} total OSM elements"
        )

    def show_selected_element(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        element = self.elements_by_tree_id.get(selection[0])
        if not element:
            return

        details = element_details(element) + "\n\nRaw JSON:\n" + json.dumps(element, ensure_ascii=False, indent=2, sort_keys=True)

        self.details.delete("1.0", tk.END)
        self.details.insert(tk.END, details)

    def save_json(self) -> None:
        if not self.osm_data.get("elements"):
            messagebox.showinfo("Nothing to save", "Fetch OSM data before saving.")
            return

        default_path = Path.cwd() / "osm_data.json"
        filename = filedialog.asksaveasfilename(
            title="Save OSM JSON",
            initialfile=default_path.name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not filename:
            return

        with open(filename, "w", encoding="utf-8") as file:
            json.dump(self.osm_data, file, ensure_ascii=False, indent=2)
        self.status_var.set(f"Saved {filename}")

    def open_map(self) -> None:
        if not self.server_url:
            messagebox.showinfo("Local site not ready", "The local server is not running.")
            return

        try:
            opened = open_browser_url(self.server_url)
        except OSError as exc:
            opened = False
            open_error = str(exc)
        else:
            open_error = ""

        self.clipboard_clear()
        self.clipboard_append(self.server_url)
        if opened:
            self.status_var.set(f"Localhost map opened: {self.server_url}")
            return

        self.status_var.set(f"Localhost map ready: {self.server_url}")
        messagebox.showinfo(
            "Localhost map ready",
            "The local site is running, but no browser could be opened automatically.\n\n"
            f"URL copied to clipboard:\n{self.server_url}\n\n"
            "Open this URL manually in a browser."
            + (f"\n\nError: {open_error}" if open_error else ""),
        )

    def export_html_map(self) -> None:
        if not self.osm_data.get("elements"):
            messagebox.showinfo("No OSM data", "Load OSM JSON or fetch OSM data before exporting the HTML map.")
            return

        self.status_var.set("Building HTML map...")
        thread = threading.Thread(target=self._export_html_map_worker, args=(self.osm_data,), daemon=True)
        thread.start()

    def _export_html_map_worker(self, data: dict) -> None:
        try:
            map_path = write_leaflet_map(data, Path.cwd() / MAP_FILE)
        except OSError as exc:
            self.after(0, lambda: messagebox.showerror("Could not build map", str(exc)))
            return

        self.after(0, lambda: self._html_map_ready(map_path))
    def _html_map_ready(self, map_path: Path) -> None:
        self.status_var.set(f"HTML map created: {map_path}")
        try:
            opened = open_html_file(map_path)
        except OSError as exc:
            opened = False
            open_error = str(exc)
        else:
            open_error = ""

        if not opened:
            map_uri = map_path.resolve().as_uri()
            self.clipboard_clear()
            self.clipboard_append(map_uri)
            messagebox.showwarning(
                "Map created, browser not found",
                "The map was created, but no browser could be opened automatically.\n\n"
                f"Map file:\n{map_path.resolve()}\n\n"
                f"URL copied to clipboard:\n{map_uri}\n\n"
                "Install or configure a default browser, then open this file manually."
                + (f"\n\nError: {open_error}" if open_error else ""),
            )
