import json
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import OVERPASS_URL, POINT_KINDS, ROAD_COLORS

def build_overpass_query(lat: float, lon: float, radius: int) -> str:
    return f"""
[out:json][timeout:60];
(
  node(around:{radius},{lat},{lon});
  way(around:{radius},{lat},{lon});
  relation(around:{radius},{lat},{lon});
);
out body center;
>;
out skel qt;
"""


def fetch_osm_data(lat: float, lon: float, radius: int) -> dict:
    query = build_overpass_query(lat, lon, radius)
    payload = urlencode({"data": query}).encode("utf-8")
    request = Request(OVERPASS_URL, data=payload, method="POST")
    request.add_header("Accept", "application/json")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    request.add_header("User-Agent", "osint-osm-explorer/1.0")

    with urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def element_name(element: dict) -> str:
    tags = element.get("tags") or {}
    for key in ("name", "official_name", "brand", "operator", "addr:street"):
        if tags.get(key):
            return tags[key]
    return "(no name)"


def element_category(element: dict) -> str:
    tags = element.get("tags") or {}
    preferred_keys = (
        "amenity",
        "shop",
        "tourism",
        "historic",
        "leisure",
        "building",
        "highway",
        "natural",
        "landuse",
        "public_transport",
        "railway",
        "waterway",
        "boundary",
        "place",
        "barrier",
        "entrance",
        "man_made",
        "emergency",
    )
    for key in preferred_keys:
        if tags.get(key):
            return f"{key}={tags[key]}"
    return "untagged"


def point_kind(tags: dict) -> str:
    barrier = tags.get("barrier")
    amenity = tags.get("amenity")
    building = tags.get("building")
    highway = tags.get("highway")
    historic = tags.get("historic")
    leisure = tags.get("leisure")
    natural = tags.get("natural")
    public_transport = tags.get("public_transport")
    railway = tags.get("railway")
    shop = tags.get("shop")
    tourism = tags.get("tourism")

    if barrier in {"bollard", "block", "cycle_barrier", "jersey_barrier"}:
        return "bollard"
    if barrier in {"gate", "lift_gate", "swing_gate", "kissing_gate", "sliding_gate"}:
        return "gate"
    if tags.get("entrance"):
        return "entrance"
    if tags.get("man_made") == "surveillance" or tags.get("surveillance"):
        return "surveillance"
    if barrier:
        return "barrier"

    if amenity == "atm":
        return "atm"
    if amenity == "bank":
        return "bank"
    if shop == "bakery":
        return "bakery"
    if shop == "butcher":
        return "butcher"
    if amenity in {"cafe", "bar", "pub"}:
        return "cafe"
    if amenity == "fast_food":
        return "fast_food"
    if amenity == "pharmacy":
        return "pharmacy"
    if amenity == "post_office":
        return "post_office"
    if amenity == "restaurant":
        return "restaurant"
    if amenity in {"school", "kindergarten", "college", "university"}:
        return "school"
    if amenity == "townhall" or tags.get("office") == "government":
        return "townhall"
    if amenity == "toilets":
        return "toilets"

    if emergency := tags.get("emergency"):
        if emergency == "defibrillator":
            return "defibrillator"
        if emergency in {"phone", "emergency_phone"}:
            return "emergency_phone"
        return "emergency"
    if amenity == "fire_station":
        return "fire_station"
    if amenity in {"hospital", "clinic", "doctors"}:
        return "hospital"
    if amenity == "police":
        return "police"
    if tags.get("boundary"):
        return "boundary"

    if natural == "beach":
        return "beach"
    if leisure == "garden":
        return "garden"
    if leisure == "park":
        return "park"
    if leisure == "playground":
        return "playground"
    if leisure in {"pitch", "sports_centre", "stadium"}:
        return "sports_pitch"
    if leisure == "swimming_pool":
        return "swimming_pool"
    if tags.get("waterway") or natural in {"water", "bay", "strait", "spring"}:
        return "water"
    if natural or leisure in {"common", "dog_park", "nature_reserve"}:
        return "nature"

    if highway == "turning_circle":
        return "turning_circle"

    if shop in {"books", "bookmaker"}:
        return "books"
    if shop in {"clothes", "fashion", "shoes"}:
        return "clothes"
    if shop in {"convenience", "deli", "greengrocer"}:
        return "convenience"
    if shop in {"fishmonger", "seafood"}:
        return "fishmonger"
    if shop in {"kiosk", "newsagent"}:
        return "kiosk"
    if shop in {"supermarket", "grocery"}:
        return "supermarket"
    if shop == "tobacco":
        return "tobacco"
    if shop:
        return "shop"

    if highway == "stop":
        return "stop"
    if highway == "give_way":
        return "give_way"
    if highway == "crossing":
        return "crossing"
    if highway == "traffic_signals":
        return "traffic_signals"
    if highway == "speed_camera" or tags.get("enforcement") in {"maxspeed", "traffic_signals"}:
        return "speed_camera"
    if tags.get("traffic_calming"):
        return "traffic_calming"
    if tags.get("traffic_sign"):
        return "traffic_sign"

    if tags.get("bridge"):
        return "bridge"
    if building in {"garage", "garages"}:
        return "garage"
    if amenity in {"parking", "parking_entrance"} and building:
        return "parking_structure"
    if amenity == "place_of_worship":
        return "place_of_worship"
    if building in {"civic", "public", "government", "school", "university", "college", "hospital"}:
        return "public_building"
    if building in {"apartments", "detached", "dormitory", "house", "residential", "semidetached_house", "terrace"}:
        return "residential_building"
    if tags.get("tunnel"):
        return "tunnel"

    if tourism in {"hotel", "hostel", "guest_house", "apartment"}:
        return "hotel"
    if tourism == "information":
        return "information"
    if historic in {"monument", "memorial"}:
        return "monument"
    if tourism == "museum":
        return "museum"
    if tourism == "viewpoint":
        return "viewpoint"
    if tourism or historic:
        return "tourism"

    if amenity in {"bicycle_parking", "motorcycle_parking"}:
        return "bicycle_parking"
    if highway == "bus_stop" or (public_transport == "platform" and tags.get("bus") == "yes"):
        return "bus_stop"
    if amenity == "fuel":
        return "fuel"
    if railway == "subway_entrance" or tags.get("station") == "subway" or tags.get("subway") == "yes":
        return "metro"
    if amenity in {"parking", "parking_entrance"}:
        return "parking"
    if railway in {"station", "halt"} or public_transport == "station":
        return "rail_station"
    if amenity == "taxi":
        return "taxi"
    if railway == "tram_stop" or tags.get("tram") == "yes":
        return "tram_stop"
    if highway == "platform" or public_transport or railway:
        return "transport"

    if tags.get("man_made") or building:
        return "structure"
    if tags.get("addr:housenumber") or tags.get("addr:street"):
        return "address"
    if highway:
        return "road_node"
    if amenity or tags.get("office") or tags.get("craft"):
        return "amenity"
    return "other"


def load_osm_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def popup_html(element: dict) -> str:
    tags = element.get("tags") or {}
    rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in sorted(tags.items())
    )
    osm_type = escape(str(element.get("type", "")))
    osm_id = escape(str(element.get("id", "")))
    title = escape(element_name(element))
    return (
        f"<strong>{title}</strong>"
        f"<div class='meta'>{osm_type} {osm_id} - {escape(element_category(element))}</div>"
        f"<table>{rows}</table>"
    )


def element_details(element: dict) -> str:
    tags = element.get("tags") or {}
    kind = point_kind(tags) if tags else ""
    lines = [
        f"Type: {element.get('type')}",
        f"OSM ID: {element.get('id')}",
        f"Name: {element_name(element)}",
        f"Category: {element_category(element)}",
    ]
    if kind in POINT_KINDS:
        lines.append(f"OSINT layer: {POINT_KINDS[kind]['label']}")
    lines.extend(["", "Tags:"])
    if tags:
        lines.extend(f"  {key}: {value}" for key, value in sorted(tags.items()))
    else:
        lines.append("  No tags")
    return "\n".join(lines)


def build_map_payload(data: dict) -> dict:
    elements = data.get("elements", [])
    node_index = {
        element["id"]: [element["lat"], element["lon"]]
        for element in elements
        if element.get("type") == "node" and "lat" in element and "lon" in element
    }

    roads = []
    areas = []
    points = []
    bounds = []
    point_kind_counts = {kind: 0 for kind in POINT_KINDS}
    skipped = {"roads": 0, "areas": 0, "points": 0}

    for element in elements:
        tags = element.get("tags") or {}
        element_type = element.get("type")

        if element_type == "way" and tags.get("highway"):
            coords = [node_index[node_id] for node_id in element.get("nodes", []) if node_id in node_index]
            if len(coords) < 2:
                skipped["roads"] += 1
                continue
            roads.append(
                {
                    "osmType": element_type,
                    "osmId": element.get("id"),
                    "highway": tags.get("highway"),
                    "tags": tags,
                    "coords": coords,
                    "name": element_name(element),
                    "category": element_category(element),
                    "color": ROAD_COLORS.get(tags.get("highway"), "#555555"),
                    "details": element_details(element),
                    "popup": popup_html(element),
                }
            )
            bounds.extend(coords)
            continue

        if element_type == "way" and any(
            key in tags for key in ("building", "landuse", "natural", "amenity", "tourism", "leisure", "shop", "historic")
        ):
            coords = [node_index[node_id] for node_id in element.get("nodes", []) if node_id in node_index]
            if len(coords) < 3:
                skipped["areas"] += 1
                continue
            if len(areas) < 12000:
                areas.append(
                    {
                        "coords": coords,
                        "name": element_name(element),
                        "category": element_category(element),
                        "details": element_details(element),
                        "popup": popup_html(element),
                    }
                )
                bounds.extend(coords)
            else:
                skipped["areas"] += 1
            continue

        lat_lon = None
        if element_type == "node" and tags and "lat" in element and "lon" in element:
            lat_lon = [element["lat"], element["lon"]]
        elif tags and element.get("center"):
            center = element["center"]
            lat_lon = [center["lat"], center["lon"]]

        if lat_lon:
            kind = point_kind(tags)
            point_kind_counts[kind] += 1
            style = POINT_KINDS[kind]
            points.append(
                {
                    "osmType": element_type,
                    "osmId": element.get("id"),
                    "coords": lat_lon,
                    "name": element_name(element),
                    "category": element_category(element),
                    "kind": kind,
                    "kindLabel": style["label"],
                    "icon": style["icon"],
                    "iconUrl": style.get("maki"),
                    "color": style["color"],
                    "details": element_details(element),
                    "popup": popup_html(element),
                }
            )
            bounds.append(lat_lon)

    return {
        "roads": roads,
        "areas": areas,
        "points": points,
        "bounds": bounds,
        "stats": {
            "elements": len(elements),
            "roads": len(roads),
            "areas": len(areas),
            "points": len(points),
            "pointKinds": point_kind_counts,
            "skipped": skipped,
        },
        "pointKinds": POINT_KINDS,
        "fetchArea": data.get("_fetch_area"),
    }
