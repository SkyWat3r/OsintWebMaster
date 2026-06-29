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
    "bollard": {"label": "Bollards", "group": "Access / security", "icon": "BO", "maki": "barrier", "color": "#52525b", "default": True},
    "gate": {"label": "Gates", "group": "Access / security", "icon": "G", "maki": "gate", "color": "#7c3aed", "default": True},
    "entrance": {"label": "Entrances", "group": "Access / security", "icon": "E", "maki": "entrance", "color": "#a855f7", "default": True},
    "surveillance": {"label": "Surveillance cameras", "group": "Access / security", "icon": "CAM", "maki": "caution", "color": "#111827", "default": True},
    "barrier": {"label": "Barriers", "group": "Access / security", "icon": "B", "maki": "barrier", "color": "#6b7280", "default": True},

    "atm": {"label": "ATMs", "group": "Amenities", "icon": "ATM", "maki": "bank", "color": "#0f766e", "default": True},
    "bank": {"label": "Banks", "group": "Amenities", "icon": "BK", "maki": "bank", "color": "#047857", "default": True},
    "bakery": {"label": "Bakeries", "group": "Amenities", "icon": "BA", "maki": "bakery", "color": "#d97706", "default": True},
    "butcher": {"label": "Butchers", "group": "Amenities", "icon": "BU", "maki": "grocery", "color": "#b91c1c", "default": True},
    "cafe": {"label": "Cafes / bars", "group": "Amenities", "icon": "CF", "maki": "cafe", "color": "#92400e", "default": True},
    "fast_food": {"label": "Fast-food", "group": "Amenities", "icon": "FF", "maki": "fast-food", "color": "#ea580c", "default": True},
    "pharmacy": {"label": "Pharmacies", "group": "Amenities", "icon": "PH", "maki": "pharmacy", "color": "#16a34a", "default": True},
    "post_office": {"label": "Post offices", "group": "Amenities", "icon": "PO", "maki": "post", "color": "#2563eb", "default": True},
    "restaurant": {"label": "Restaurants", "group": "Amenities", "icon": "RE", "maki": "restaurant", "color": "#c2410c", "default": True},
    "school": {"label": "Schools", "group": "Amenities", "icon": "SC", "maki": "school", "color": "#7c2d12", "default": True},
    "townhall": {"label": "Town halls", "group": "Amenities", "icon": "TH", "maki": "town-hall", "color": "#4338ca", "default": True},
    "toilets": {"label": "Public toilets", "group": "Amenities", "icon": "WC", "maki": "toilet", "color": "#0891b2", "default": True},
    "amenity": {"label": "Other amenities", "group": "Amenities", "icon": "+", "maki": "circle", "color": "#16a34a", "default": True},

    "defibrillator": {"label": "Defibrillators", "group": "Civic / emergency", "icon": "AED", "maki": "doctor", "color": "#dc2626", "default": True},
    "emergency_phone": {"label": "Emergency phones", "group": "Civic / emergency", "icon": "SOS", "maki": "emergency-phone", "color": "#ef4444", "default": True},
    "fire_station": {"label": "Fire stations", "group": "Civic / emergency", "icon": "FIR", "maki": "fire-station", "color": "#b91c1c", "default": True},
    "hospital": {"label": "Hospitals / clinics", "group": "Civic / emergency", "icon": "H", "maki": "hospital", "color": "#dc2626", "default": True},
    "police": {"label": "Police", "group": "Civic / emergency", "icon": "POL", "maki": "police", "color": "#1d4ed8", "default": True},
    "emergency": {"label": "Other emergency points", "group": "Civic / emergency", "icon": "!", "maki": "emergency-phone", "color": "#ef4444", "default": True},
    "boundary": {"label": "Boundaries", "group": "Civic / emergency", "icon": "BD", "maki": "circle", "color": "#64748b", "default": True},

    "beach": {"label": "Beaches", "group": "Land / water", "icon": "BE", "maki": "beach", "color": "#0ea5e9", "default": True},
    "garden": {"label": "Gardens", "group": "Land / water", "icon": "GA", "maki": "garden", "color": "#15803d", "default": True},
    "park": {"label": "Parks", "group": "Land / water", "icon": "PK", "maki": "park", "color": "#16a34a", "default": True},
    "playground": {"label": "Playgrounds", "group": "Land / water", "icon": "PG", "maki": "playground", "color": "#65a30d", "default": True},
    "sports_pitch": {"label": "Sports fields", "group": "Land / water", "icon": "SP", "maki": "soccer", "color": "#22c55e", "default": True},
    "swimming_pool": {"label": "Swimming pools", "group": "Land / water", "icon": "SW", "maki": "swimming", "color": "#0284c7", "default": True},
    "water": {"label": "Water", "group": "Land / water", "icon": "W", "maki": "water", "color": "#0ea5e9", "default": True},
    "nature": {"label": "Other nature", "group": "Land / water", "icon": "N", "maki": "garden", "color": "#15803d", "default": True},

    "turning_circle": {"label": "Turning circles", "group": "Road nodes", "icon": "U", "maki": "circle-stroked", "color": "#475569", "default": True},
    "road_node": {"label": "Other road nodes", "group": "Road nodes", "icon": "R", "maki": "circle", "color": "#4b5563", "default": False},

    "books": {"label": "Bookshops", "group": "Shops", "icon": "BK", "maki": "library", "color": "#7c3aed", "default": True},
    "clothes": {"label": "Clothes shops", "group": "Shops", "icon": "CL", "maki": "clothing-store", "color": "#db2777", "default": True},
    "convenience": {"label": "Convenience stores", "group": "Shops", "icon": "CV", "maki": "grocery", "color": "#65a30d", "default": True},
    "fishmonger": {"label": "Fishmongers", "group": "Shops", "icon": "FI", "maki": "grocery", "color": "#0891b2", "default": True},
    "kiosk": {"label": "Kiosks / newsstands", "group": "Shops", "icon": "KI", "maki": "shop", "color": "#ca8a04", "default": True},
    "supermarket": {"label": "Supermarkets", "group": "Shops", "icon": "SM", "maki": "grocery", "color": "#16a34a", "default": True},
    "tobacco": {"label": "Tobacco shops", "group": "Shops", "icon": "TB", "maki": "shop", "color": "#854d0e", "default": True},
    "shop": {"label": "Other shops", "group": "Shops", "icon": "SH", "maki": "shop", "color": "#ca8a04", "default": True},

    "crossing": {"label": "Crossings", "group": "Signs", "icon": "X", "maki": "cross", "color": "#dc2626", "default": True},
    "give_way": {"label": "Give way", "group": "Signs", "icon": "Y", "maki": "caution", "color": "#f97316", "default": True},
    "speed_camera": {"label": "Speed cameras", "group": "Signs", "icon": "CAM", "maki": "caution", "color": "#7f1d1d", "default": True},
    "stop": {"label": "Stop signs", "group": "Signs", "icon": "STOP", "maki": "caution", "color": "#b91c1c", "default": True},
    "traffic_calming": {"label": "Traffic calming", "group": "Signs", "icon": "TC", "maki": "caution", "color": "#fb923c", "default": True},
    "traffic_sign": {"label": "Traffic signs", "group": "Signs", "icon": "!", "maki": "caution", "color": "#eab308", "default": True},
    "traffic_signals": {"label": "Traffic lights", "group": "Signs", "icon": "TL", "maki": "caution", "color": "#16a34a", "default": True},

    "bridge": {"label": "Bridges", "group": "Structures", "icon": "BR", "maki": "bridge", "color": "#78716c", "default": True},
    "garage": {"label": "Garages", "group": "Structures", "icon": "GR", "maki": "car", "color": "#57534e", "default": True},
    "parking_structure": {"label": "Covered parking", "group": "Structures", "icon": "CP", "maki": "parking", "color": "#0284c7", "default": True},
    "place_of_worship": {"label": "Places of worship", "group": "Structures", "icon": "PW", "maki": "religious-christian", "color": "#6d28d9", "default": True},
    "public_building": {"label": "Public buildings", "group": "Structures", "icon": "PB", "maki": "building", "color": "#4f46e5", "default": True},
    "residential_building": {"label": "Residential buildings", "group": "Structures", "icon": "RB", "maki": "home", "color": "#9333ea", "default": True},
    "tunnel": {"label": "Tunnels", "group": "Structures", "icon": "TU", "maki": "tunnel", "color": "#44403c", "default": True},
    "structure": {"label": "Other structures", "group": "Structures", "icon": "S", "maki": "building", "color": "#78716c", "default": True},
    "address": {"label": "Addresses", "group": "Structures", "icon": "#", "maki": "home", "color": "#9333ea", "default": False},

    "hotel": {"label": "Hotels", "group": "Tourism / info", "icon": "HO", "maki": "lodging", "color": "#0f766e", "default": True},
    "information": {"label": "Information boards", "group": "Tourism / info", "icon": "i", "maki": "information", "color": "#0891b2", "default": True},
    "monument": {"label": "Monuments / memorials", "group": "Tourism / info", "icon": "MO", "maki": "monument", "color": "#a16207", "default": True},
    "museum": {"label": "Museums", "group": "Tourism / info", "icon": "MU", "maki": "museum", "color": "#7c2d12", "default": True},
    "viewpoint": {"label": "Viewpoints", "group": "Tourism / info", "icon": "VP", "maki": "viewpoint", "color": "#0284c7", "default": True},
    "tourism": {"label": "Other tourism / historic", "group": "Tourism / info", "icon": "i", "maki": "attraction", "color": "#0891b2", "default": True},

    "bicycle_parking": {"label": "Bicycle parking", "group": "Transport", "icon": "BP", "maki": "bicycle", "color": "#0d9488", "default": True},
    "bus_stop": {"label": "Bus stops", "group": "Transport", "icon": "BUS", "maki": "bus", "color": "#2563eb", "default": True},
    "fuel": {"label": "Fuel stations", "group": "Transport", "icon": "F", "maki": "fuel", "color": "#dc2626", "default": True},
    "metro": {"label": "Metro stations / entrances", "group": "Transport", "icon": "M", "maki": "rail-metro", "color": "#7c3aed", "default": True},
    "parking": {"label": "Car parking", "group": "Transport", "icon": "P", "maki": "parking", "color": "#0284c7", "default": True},
    "rail_station": {"label": "Train stations", "group": "Transport", "icon": "TR", "maki": "rail", "color": "#1d4ed8", "default": True},
    "taxi": {"label": "Taxi stands", "group": "Transport", "icon": "TX", "maki": "car", "color": "#ca8a04", "default": True},
    "tram_stop": {"label": "Tram stops", "group": "Transport", "icon": "TM", "maki": "rail-light", "color": "#059669", "default": True},
    "transport": {"label": "Other transport", "group": "Transport", "icon": "T", "maki": "bus", "color": "#2563eb", "default": True},

    "other": {"label": "Other points", "group": "Other", "icon": "*", "maki": "circle", "color": "#ca8a04", "default": False},
}
