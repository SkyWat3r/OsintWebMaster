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
    if tags.get("highway") == "stop":
        return "stop"
    if tags.get("highway") == "give_way":
        return "give_way"
    if tags.get("highway") == "crossing":
        return "crossing"
    if tags.get("highway") == "traffic_signals":
        return "traffic_signals"
    if tags.get("highway") == "turning_circle":
        return "turning_circle"
    if tags.get("highway") == "speed_camera" or tags.get("enforcement") in {"maxspeed", "traffic_signals"}:
        return "speed_camera"
    if tags.get("traffic_calming"):
        return "traffic_calming"
    if tags.get("traffic_sign"):
        return "traffic_sign"
    if barrier in {"gate", "lift_gate", "swing_gate", "kissing_gate", "sliding_gate"}:
        return "gate"
    if barrier:
        return "barrier"
    if tags.get("man_made") == "surveillance" or tags.get("surveillance"):
        return "surveillance"
    if tags.get("amenity") in {"parking", "parking_entrance", "bicycle_parking", "motorcycle_parking"}:
        return "parking"
    if tags.get("amenity") in {"restaurant", "cafe", "bar", "fast_food", "pub"}:
        return "food"
    if tags.get("highway") in {"bus_stop", "platform"} or tags.get("public_transport") or tags.get("railway"):
        return "transport"
    if tags.get("tourism") or tags.get("historic"):
        return "tourism"
    if tags.get("emergency"):
        return "emergency"
    if tags.get("entrance"):
        return "entrance"
    if tags.get("waterway"):
        return "water"
    if tags.get("boundary"):
        return "boundary"
    if tags.get("man_made") or tags.get("building"):
        return "structure"
    if tags.get("natural") or tags.get("leisure") in {"park", "pitch", "swimming_pool", "garden"}:
        return "nature"
    if tags.get("addr:housenumber") or tags.get("addr:street"):
        return "address"
    if tags.get("highway"):
        return "road_node"
    if tags.get("amenity") or tags.get("shop") or tags.get("office") or tags.get("craft"):
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
    }
