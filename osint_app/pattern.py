import math
from collections import defaultdict


def _bearing(a: list[float], b: list[float]) -> float:
    lat1 = math.radians(a[0])
    lat2 = math.radians(b[0])
    delta_lon = math.radians(b[1] - a[1])
    y = math.sin(delta_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _canvas_angle(center: dict, point: dict) -> float:
    dx = point["x"] - center["x"]
    dy = center["y"] - point["y"]
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360


def _angle_delta(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _relative_gaps(angles: list[float]) -> list[float]:
    normalized = sorted(angle % 360 for angle in angles)
    return [
        (normalized[(index + 1) % len(normalized)] - angle) % 360
        for index, angle in enumerate(normalized)
    ]


def _gap_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 180

    best = 180.0
    size = len(left)
    for offset in range(size):
        shifted = right[offset:] + right[:offset]
        score = sum(_angle_delta(left[index], shifted[index]) for index in range(size)) / size
        best = min(best, score)
    return best


def _absolute_angle_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 180
    remaining = sorted(right)
    total = 0.0
    for angle in sorted(left):
        best = min(range(len(remaining)), key=lambda index: _angle_delta(angle, remaining[index]))
        total += _angle_delta(angle, remaining.pop(best))
    return total / len(left)


def build_road_pattern_index(data: dict) -> dict:
    elements = data.get("elements", [])
    nodes = {
        element["id"]: [element["lat"], element["lon"]]
        for element in elements
        if element.get("type") == "node" and "lat" in element and "lon" in element
    }
    neighbors: dict[int, set[int]] = defaultdict(set)
    road_types: dict[int, set[str]] = defaultdict(set)

    for element in elements:
        tags = element.get("tags") or {}
        if element.get("type") != "way" or not tags.get("highway"):
            continue

        way_nodes = [node_id for node_id in element.get("nodes", []) if node_id in nodes]
        for first, second in zip(way_nodes, way_nodes[1:]):
            neighbors[first].add(second)
            neighbors[second].add(first)
            road_types[first].add(tags["highway"])
            road_types[second].add(tags["highway"])

    intersections = []
    for node_id, linked_nodes in neighbors.items():
        if len(linked_nodes) < 2:
            continue

        center = nodes[node_id]
        angles = [_bearing(center, nodes[neighbor_id]) for neighbor_id in linked_nodes]
        intersections.append(
            {
                "id": node_id,
                "coords": center,
                "degree": len(angles),
                "angles": angles,
                "gaps": _relative_gaps(angles),
                "roadTypes": sorted(road_types[node_id]),
            }
        )

    return {"intersections": intersections}


def _pattern_anchor(pattern: dict) -> tuple[dict, list[dict]]:
    points = pattern.get("points") or []
    edges = pattern.get("edges") or []
    by_id = {point["id"]: point for point in points}
    linked: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        start = edge.get("from")
        end = edge.get("to")
        if start in by_id and end in by_id:
            linked[start].add(end)
            linked[end].add(start)

    anchors = [(len(neighbors), point_id) for point_id, neighbors in linked.items()]
    if not anchors:
        raise ValueError("Draw at least two connected road segments.")

    degree, point_id = max(anchors)
    if degree < 2:
        raise ValueError("Draw an intersection with at least two branches.")

    return by_id[point_id], [by_id[neighbor_id] for neighbor_id in linked[point_id]]


def search_road_pattern(index: dict, pattern: dict, *, rotation_invariant: bool = True, limit: int = 50) -> dict:
    center, neighbors = _pattern_anchor(pattern)
    pattern_angles = [_canvas_angle(center, point) for point in neighbors]
    pattern_gaps = _relative_gaps(pattern_angles)
    pattern_degree = len(pattern_angles)

    candidates = []
    for item in index["intersections"]:
        degree_penalty = abs(item["degree"] - pattern_degree) * 35
        if item["degree"] < pattern_degree:
            degree_penalty += 40

        if rotation_invariant:
            angle_penalty = _gap_distance(pattern_gaps, item["gaps"]) if item["degree"] == pattern_degree else 70
        else:
            angle_penalty = _absolute_angle_distance(pattern_angles, item["angles"]) if item["degree"] == pattern_degree else 70

        score = max(0.0, 100.0 - degree_penalty - angle_penalty)
        if score < 20:
            continue

        candidates.append(
            {
                "id": item["id"],
                "coords": item["coords"],
                "degree": item["degree"],
                "score": round(score, 1),
                "roadTypes": item["roadTypes"],
                "angles": [round(angle, 1) for angle in sorted(item["angles"])],
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return {
        "pattern": {
            "degree": pattern_degree,
            "angles": [round(angle, 1) for angle in sorted(pattern_angles)],
            "rotationInvariant": rotation_invariant,
        },
        "matches": candidates[:limit],
    }
