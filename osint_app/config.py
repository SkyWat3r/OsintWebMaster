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
    "stop": {"label": "Stop signs", "group": "Signs", "icon": "STOP", "maki": "caution", "color": "#b91c1c", "default": True},
    "give_way": {"label": "Give way", "group": "Signs", "icon": "Y", "maki": "caution", "color": "#f97316", "default": True},
    "crossing": {"label": "Crossings", "group": "Signs", "icon": "X", "maki": "cross", "color": "#dc2626", "default": True},
    "traffic_signals": {"label": "Traffic lights", "group": "Signs", "icon": "TL", "maki": "caution", "color": "#16a34a", "default": True},
    "traffic_sign": {"label": "Traffic signs", "group": "Signs", "icon": "!", "maki": "caution", "color": "#eab308", "default": True},
    "speed_camera": {"label": "Speed cameras", "group": "Signs", "icon": "CAM", "maki": "caution", "color": "#7f1d1d", "default": True},
    "traffic_calming": {"label": "Traffic calming", "group": "Signs", "icon": "TC", "maki": "caution", "color": "#fb923c", "default": True},
    "turning_circle": {"label": "Turning circles", "group": "Road nodes", "icon": "U", "maki": "circle-stroked", "color": "#475569", "default": True},
    "gate": {"label": "Gates", "group": "Access / security", "icon": "G", "maki": "gate", "color": "#7c3aed", "default": True},
    "barrier": {"label": "Barriers", "group": "Access / security", "icon": "B", "maki": "barrier", "color": "#6b7280", "default": True},
    "surveillance": {"label": "Surveillance", "group": "Access / security", "icon": "C", "maki": "caution", "color": "#111827", "default": True},
    "entrance": {"label": "Entrances", "group": "Access / security", "icon": "E", "maki": "entrance", "color": "#a855f7", "default": True},
    "transport": {"label": "Transport", "group": "Transport", "icon": "T", "maki": "bus", "color": "#2563eb", "default": True},
    "parking": {"label": "Parking", "group": "Transport", "icon": "P", "maki": "parking", "color": "#0284c7", "default": True},
    "food": {"label": "Food", "group": "Amenities", "icon": "F", "maki": "cafe", "color": "#ea580c", "default": True},
    "tourism": {"label": "Tourism / info", "group": "Amenities", "icon": "i", "maki": "attraction", "color": "#0891b2", "default": True},
    "amenity": {"label": "Amenities", "group": "Amenities", "icon": "+", "maki": "circle", "color": "#16a34a", "default": True},
    "emergency": {"label": "Emergency", "group": "Civic / emergency", "icon": "!", "maki": "emergency-phone", "color": "#ef4444", "default": True},
    "boundary": {"label": "Boundaries", "group": "Civic / emergency", "icon": "B", "maki": "circle", "color": "#64748b", "default": True},
    "nature": {"label": "Nature", "group": "Land / water", "icon": "N", "maki": "garden", "color": "#15803d", "default": True},
    "water": {"label": "Water", "group": "Land / water", "icon": "W", "maki": "circle", "color": "#0ea5e9", "default": True},
    "structure": {"label": "Structures", "group": "Structures", "icon": "S", "maki": "building", "color": "#78716c", "default": True},
    "address": {"label": "Addresses", "group": "Structures", "icon": "#", "maki": "home", "color": "#9333ea", "default": False},
    "road_node": {"label": "Road nodes", "group": "Road nodes", "icon": "R", "maki": "circle", "color": "#4b5563", "default": False},
    "other": {"label": "Other points", "group": "Other", "icon": "•", "maki": "circle", "color": "#ca8a04", "default": False},
}
