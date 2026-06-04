import math
from collections import defaultdict


MAX_TRACE_STEPS = 18
MIN_SCORE = 25


def _distance_meters(a: list[float], b: list[float]) -> float:
    lat_scale = 111_320
    lon_scale = 111_320 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((b[0] - a[0]) * lat_scale, (b[1] - a[1]) * lon_scale)


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


def _canvas_distance(a: dict, b: dict) -> float:
    return math.hypot(b["x"] - a["x"], b["y"] - a["y"])


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


def _degree_groups(linked: dict) -> dict:
    counts: dict[int, int] = defaultdict(int)
    for neighbors in linked.values():
        counts[len(neighbors)] += 1
    return dict(counts)


def _normalized_lengths(branches: list[dict]) -> list[float]:
    longest = max((branch["length"] for branch in branches), default=1)
    if longest <= 0:
        return [1 for _branch in branches]
    return [branch["length"] / longest for branch in branches]


def _branch_turn(angles: list[float]) -> float:
    if len(angles) < 2:
        return 0.0
    total = 0.0
    for first, second in zip(angles, angles[1:]):
        delta = (second - first + 180) % 360 - 180
        total += delta
    return total


def _ordered_branch_indexes(branches: list[dict]) -> list[int]:
    return sorted(range(len(branches)), key=lambda index: branches[index]["angle"])


def _branch_order_distance(pattern: list[dict], candidate: list[dict], rotation_invariant: bool) -> float:
    if len(pattern) != len(candidate):
        return 100.0

    pattern_order = _ordered_branch_indexes(pattern)
    candidate_order = _ordered_branch_indexes(candidate)
    pattern_lengths = _normalized_lengths(pattern)
    candidate_lengths = _normalized_lengths(candidate)
    pattern_angles = [pattern[index]["angle"] for index in pattern_order]
    candidate_angles = [candidate[index]["angle"] for index in candidate_order]
    pattern_gaps = _relative_gaps(pattern_angles)
    candidate_gaps = _relative_gaps(candidate_angles)

    best = 100.0
    offsets = range(len(pattern)) if rotation_invariant else range(1)
    for offset in offsets:
        total = 0.0
        for order_index, pattern_index in enumerate(pattern_order):
            candidate_index = candidate_order[(order_index + offset) % len(candidate_order)]
            angle_cost = (
                _angle_delta(pattern_gaps[order_index], candidate_gaps[(order_index + offset) % len(candidate_gaps)]) / 3
                if rotation_invariant
                else _angle_delta(pattern[pattern_index]["angle"], candidate[candidate_index]["angle"]) / 3
            )
            turn_cost = _angle_delta(pattern[pattern_index]["turn"], candidate[candidate_index]["turn"]) / 3
            length_cost = abs(pattern_lengths[pattern_index] - candidate_lengths[candidate_index]) * 35
            total += angle_cost + turn_cost + length_cost
        best = min(best, total / len(pattern))
    return best


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

    candidates = []
    for node_id, linked_nodes in neighbors.items():
        if len(linked_nodes) < 2:
            continue

        center = nodes[node_id]
        branches = [
            _trace_osm_branch(node_id, neighbor_id, nodes, neighbors)
            for neighbor_id in linked_nodes
        ]
        angles = [branch["angle"] for branch in branches]
        candidates.append(
            {
                "id": node_id,
                "coords": center,
                "degree": len(angles),
                "branches": branches,
                "angles": angles,
                "gaps": _relative_gaps(angles),
                "roadTypes": sorted(road_types[node_id]),
            }
        )

    return {"intersections": candidates}


def _trace_osm_branch(start_id: int, next_id: int, nodes: dict, neighbors: dict) -> dict:
    previous_id = start_id
    current_id = next_id
    coords = [nodes[start_id], nodes[next_id]]
    angles = [_bearing(nodes[start_id], nodes[next_id])]
    length = _distance_meters(nodes[start_id], nodes[next_id])

    for _step in range(MAX_TRACE_STEPS):
        next_options = [node_id for node_id in neighbors[current_id] if node_id != previous_id]
        if len(neighbors[current_id]) != 2 or len(next_options) != 1:
            break
        following_id = next_options[0]
        length += _distance_meters(nodes[current_id], nodes[following_id])
        angles.append(_bearing(nodes[current_id], nodes[following_id]))
        coords.append(nodes[following_id])
        previous_id = current_id
        current_id = following_id

    return {
        "angle": angles[0],
        "turn": _branch_turn(angles),
        "length": length,
        "coords": coords,
    }


def _pattern_anchor(pattern: dict) -> tuple[dict, list[dict], dict]:
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

    anchors = [(len(neighbors), point_id) for point_id, neighbors in linked.items() if len(neighbors) != 2]
    if not anchors:
        anchors = [(len(neighbors), point_id) for point_id, neighbors in linked.items()]
    if not anchors:
        raise ValueError("Draw at least two connected road segments.")

    degree, point_id = max(anchors)
    if degree < 2:
        linear_points = [point_id for point_id, neighbors in linked.items() if len(neighbors) == 2]
        if not linear_points:
            raise ValueError("Draw at least two connected road segments.")
        point_id = linear_points[len(linear_points) // 2]

    branches = [
        _trace_pattern_branch(point_id, neighbor_id, by_id, linked)
        for neighbor_id in linked[point_id]
    ]
    return by_id[point_id], branches, _degree_groups(linked)


def _trace_pattern_branch(start_id: str, next_id: str, points: dict, linked: dict) -> dict:
    previous_id = start_id
    current_id = next_id
    angles = [_canvas_angle(points[start_id], points[next_id])]
    length = _canvas_distance(points[start_id], points[next_id])

    for _step in range(MAX_TRACE_STEPS):
        next_options = [point_id for point_id in linked[current_id] if point_id != previous_id]
        if len(linked[current_id]) != 2 or len(next_options) != 1:
            break
        following_id = next_options[0]
        length += _canvas_distance(points[current_id], points[following_id])
        angles.append(_canvas_angle(points[current_id], points[following_id]))
        previous_id = current_id
        current_id = following_id

    return {
        "angle": angles[0],
        "turn": _branch_turn(angles),
        "length": length,
    }


def search_road_pattern(index: dict, pattern: dict, *, rotation_invariant: bool = True, limit: int = 50) -> dict:
    _center, pattern_branches, pattern_degrees = _pattern_anchor(pattern)
    pattern_angles = [branch["angle"] for branch in pattern_branches]
    pattern_gaps = _relative_gaps(pattern_angles)
    pattern_degree = len(pattern_angles)

    candidates = []
    for item in index["intersections"]:
        degree_penalty = abs(item["degree"] - pattern_degree) * 35
        if item["degree"] < pattern_degree:
            degree_penalty += 40

        if item["degree"] == pattern_degree:
            angle_penalty = (
                _gap_distance(pattern_gaps, item["gaps"])
                if rotation_invariant
                else _absolute_angle_distance(pattern_angles, item["angles"])
            )
            shape_penalty = _branch_order_distance(pattern_branches, item["branches"], rotation_invariant)
        else:
            angle_penalty = 70
            shape_penalty = 40

        degree_shape_penalty = abs(pattern_degrees.get(1, 0) - item["degree"]) * 2
        score = max(0.0, 100.0 - degree_penalty - angle_penalty - shape_penalty - degree_shape_penalty)
        if score < MIN_SCORE:
            continue

        candidates.append(
            {
                "id": item["id"],
                "coords": item["coords"],
                "degree": item["degree"],
                "score": round(score, 1),
                "roadTypes": item["roadTypes"],
                "angles": [round(angle, 1) for angle in sorted(item["angles"])],
                "branchTurns": [round(branch["turn"], 1) for branch in item["branches"]],
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return {
        "pattern": {
            "degree": pattern_degree,
            "angles": [round(angle, 1) for angle in sorted(pattern_angles)],
            "branchTurns": [round(branch["turn"], 1) for branch in pattern_branches],
            "rotationInvariant": rotation_invariant,
        },
        "matches": candidates[:limit],
    }
