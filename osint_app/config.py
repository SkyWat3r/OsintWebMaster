OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_LAT = "43.2153"
DEFAULT_LON = "5.5389"
DEFAULT_RADIUS = "3000"
DEFAULT_JSON_FILE = "osm_data.json"
MAP_FILE = "osm_map.html"
LOCALHOST_HOST = "127.0.0.1"
LOCALHOST_PORT = 8765

ROAD_COLORS = {
    "motorway": "#d73027",
    "trunk": "#fc8d59",
    "primary": "#fdae61",
    "secondary": "#fee08b",
    "tertiary": "#91bfdb",
    "residential": "#4575b4",
    "service": "#74add1",
    "footway": "#66bd63",
    "path": "#1a9850",
    "cycleway": "#3288bd",
    "track": "#a6d96a",
}

POINT_KINDS = {
    "gate": {"label": "Gates", "icon": "▥", "color": "#7c3aed", "default": True},
    "barrier": {"label": "Barriers", "icon": "▤", "color": "#6b7280", "default": True},
    "crossing": {"label": "Crossings", "icon": "X", "color": "#dc2626", "default": True},
    "give_way": {"label": "Give way", "icon": "Y", "color": "#f97316", "default": True},
    "stop": {"label": "Stop signs", "icon": "S", "color": "#b91c1c", "default": True},
    "traffic_signals": {"label": "Traffic lights", "icon": "L", "color": "#16a34a", "default": True},
    "turning_circle": {"label": "Turning circles", "icon": "U", "color": "#475569", "default": True},
    "traffic_sign": {"label": "Traffic signs", "icon": "!", "color": "#eab308", "default": True},
    "transport": {"label": "Transport", "icon": "T", "color": "#2563eb", "default": True},
    "parking": {"label": "Parking", "icon": "P", "color": "#0284c7", "default": True},
    "food": {"label": "Food", "icon": "F", "color": "#ea580c", "default": True},
    "surveillance": {"label": "Surveillance", "icon": "C", "color": "#111827", "default": True},
    "tourism": {"label": "Tourism / info", "icon": "i", "color": "#0891b2", "default": True},
    "amenity": {"label": "Amenities", "icon": "+", "color": "#16a34a", "default": True},
    "nature": {"label": "Nature", "icon": "N", "color": "#15803d", "default": True},
    "water": {"label": "Water", "icon": "W", "color": "#0ea5e9", "default": True},
    "entrance": {"label": "Entrances", "icon": "E", "color": "#a855f7", "default": True},
    "emergency": {"label": "Emergency", "icon": "!", "color": "#ef4444", "default": True},
    "boundary": {"label": "Boundaries", "icon": "B", "color": "#64748b", "default": True},
    "structure": {"label": "Structures", "icon": "S", "color": "#78716c", "default": True},
    "address": {"label": "Addresses", "icon": "#", "color": "#9333ea", "default": False},
    "road_node": {"label": "Road nodes", "icon": "R", "color": "#4b5563", "default": False},
    "other": {"label": "Other points", "icon": "•", "color": "#ca8a04", "default": False},
}
