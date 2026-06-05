import math
from collections import defaultdict


MAX_TRACE_STEPS = 18
MIN_SCORE = 25
LINEAR_MIN_SCORE = 60
FREE_TRACE_MIN_SCORE = 45
LINEAR_SAMPLES = 14
RESULT_DEDUPE_METERS = 90
STROKE_MERGE_DISTANCE = 0.015
RELATIVE_LENGTH_WEIGHT = 28

ROAD_TYPE_GROUPS = {
    "roads": {
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "residential",
        "unclassified",
        "living_street",
    },
    "highways": {"motorway", "motorway_link", "trunk", "trunk_link"},
    "paths": {"path", "track", "footway", "cycleway", "bridleway", "pedestrian", "steps"},
    "service": {"service"},
}


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


def _road_type_groups(road_types: list[str] | set[str]) -> set[str]:
    groups = set()
    for road_type in road_types:
        for group, values in ROAD_TYPE_GROUPS.items():
            if road_type in values:
                groups.add(group)
    return groups


def _candidate_allowed(item: dict, allowed_groups: set[str] | None) -> bool:
    if not allowed_groups:
        return True
    candidate_groups = _road_type_groups(item.get("roadTypes", []))
    return bool(candidate_groups & allowed_groups)


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


def _canvas_polyline_angle(a: dict, b: dict) -> float:
    return _canvas_angle(a, b)


def _polyline_parts(points: list, *, geo: bool) -> dict:
    bearings = []
    lengths = []
    for first, second in zip(points, points[1:]):
        length = _distance_meters(first, second) if geo else _canvas_distance(first, second)
        if length <= 0:
            continue
        bearings.append(_bearing(first, second) if geo else _canvas_polyline_angle(first, second))
        lengths.append(length)

    total_length = sum(lengths)
    turns = [
        (second - first + 180) % 360 - 180
        for first, second in zip(bearings, bearings[1:])
    ]
    return {
        "bearings": bearings,
        "lengths": lengths,
        "totalLength": total_length,
        "totalTurn": sum(turns),
    }


def _sample_polyline_bearings(parts: dict, rotation_invariant: bool) -> list[float]:
    bearings = parts["bearings"]
    lengths = parts["lengths"]
    total_length = parts["totalLength"]
    if not bearings or total_length <= 0:
        return []

    samples = []
    current_length = 0.0
    segment_index = 0
    for sample_index in range(LINEAR_SAMPLES):
        target = (sample_index / max(1, LINEAR_SAMPLES - 1)) * total_length
        while segment_index < len(lengths) - 1 and current_length + lengths[segment_index] < target:
            current_length += lengths[segment_index]
            segment_index += 1
        samples.append(bearings[segment_index])

    if rotation_invariant and samples:
        first = samples[0]
        samples = [(sample - first) % 360 for sample in samples]
    return samples


def _polyline_distance(pattern_points: list, candidate_points: list, rotation_invariant: bool) -> float:
    pattern_parts = _polyline_parts(pattern_points, geo=False)
    if len(pattern_parts["bearings"]) < 2:
        return 100.0

    best = 100.0
    for points in (candidate_points, list(reversed(candidate_points))):
        candidate_parts = _polyline_parts(points, geo=True)
        if len(candidate_parts["bearings"]) < 2:
            continue
        pattern_samples = _sample_polyline_bearings(pattern_parts, rotation_invariant)
        candidate_samples = _sample_polyline_bearings(candidate_parts, rotation_invariant)
        if len(pattern_samples) != len(candidate_samples):
            continue
        bearing_cost = sum(
            _angle_delta(pattern_samples[index], candidate_samples[index])
            for index in range(len(pattern_samples))
        ) / len(pattern_samples)
        turn_cost = _angle_delta(pattern_parts["totalTurn"], candidate_parts["totalTurn"]) / 2
        segment_cost = abs(len(pattern_parts["bearings"]) - len(candidate_parts["bearings"])) * 1.5
        best = min(best, bearing_cost + turn_cost + segment_cost)
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
    by_id, linked = _pattern_graph(pattern)

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


def _point_key_for_stroke(point: dict, by_id: dict) -> str:
    for point_id, existing in by_id.items():
        if _canvas_distance(point, existing) <= STROKE_MERGE_DISTANCE:
            return point_id
    point_id = f"p{len(by_id)}"
    by_id[point_id] = {"id": point_id, "x": point["x"], "y": point["y"]}
    return point_id


def _pattern_graph(pattern: dict) -> tuple[dict, dict]:
    points = pattern.get("points") or []
    edges = pattern.get("edges") or []
    by_id = {point["id"]: point for point in points}
    linked: dict[str, set[str]] = defaultdict(set)

    if not points and pattern.get("strokes"):
        for stroke in pattern.get("strokes") or []:
            previous_id = None
            for raw_point in stroke:
                if "x" not in raw_point or "y" not in raw_point:
                    continue
                point_id = _point_key_for_stroke({"x": raw_point["x"], "y": raw_point["y"]}, by_id)
                if previous_id and previous_id != point_id:
                    linked[previous_id].add(point_id)
                    linked[point_id].add(previous_id)
                previous_id = point_id
        return by_id, linked

    for edge in edges:
        start = edge.get("from")
        end = edge.get("to")
        if start in by_id and end in by_id:
            linked[start].add(end)
            linked[end].add(start)
    return by_id, linked


def _linear_pattern_path(pattern: dict) -> list[dict]:
    by_id, linked = _pattern_graph(pattern)
    if not linked:
        return []
    degrees = [len(neighbors) for neighbors in linked.values()]
    if any(degree > 2 for degree in degrees):
        return []
    endpoints = [point_id for point_id, neighbors in linked.items() if len(neighbors) == 1]
    if len(endpoints) != 2:
        return []

    ordered = []
    previous_id = None
    current_id = endpoints[0]
    while current_id is not None:
        ordered.append(by_id[current_id])
        next_options = [point_id for point_id in linked[current_id] if point_id != previous_id]
        previous_id = current_id
        current_id = next_options[0] if next_options else None
    return ordered


def _candidate_linear_path(item: dict) -> list[list[float]]:
    if item["degree"] != 2 or len(item["branches"]) != 2:
        return []
    first, second = item["branches"]
    return list(reversed(first["coords"])) + second["coords"][1:]


def _candidate_trace_paths(item: dict) -> list[list[list[float]]]:
    paths = []
    branches = item.get("branches", [])
    for branch in branches:
        if len(branch.get("coords", [])) >= 2:
            paths.append(branch["coords"])

    for first_index, first in enumerate(branches):
        for second in branches[first_index + 1:]:
            if len(first.get("coords", [])) < 2 or len(second.get("coords", [])) < 2:
                continue
            paths.append(list(reversed(first["coords"])) + second["coords"][1:])
    return paths


def _stroke_patterns(pattern: dict) -> list[list[dict]]:
    strokes = []
    for stroke in pattern.get("strokes") or []:
        clean = [
            {"x": float(point["x"]), "y": float(point["y"])}
            for point in stroke
            if "x" in point and "y" in point
        ]
        if len(clean) >= 2:
            strokes.append(clean)
    return strokes


def _relative_polyline_lengths(polylines: list, *, geo: bool) -> list[float]:
    lengths = [_polyline_parts(polyline, geo=geo)["totalLength"] for polyline in polylines]
    longest = max(lengths, default=0)
    if longest <= 0:
        return [1 for _length in lengths]
    return [length / longest for length in lengths]


def _relative_length_penalty(pattern_strokes: list[list[dict]], candidate_paths: list[list[list[float]]]) -> float:
    if len(pattern_strokes) < 2 or len(pattern_strokes) != len(candidate_paths):
        return 0.0

    pattern_lengths = _relative_polyline_lengths(pattern_strokes, geo=False)
    candidate_lengths = _relative_polyline_lengths(candidate_paths, geo=True)
    return (
        sum(abs(pattern_lengths[index] - candidate_lengths[index]) for index in range(len(pattern_lengths)))
        / len(pattern_lengths)
        * RELATIVE_LENGTH_WEIGHT
    )


def _dedupe_nearby_matches(matches: list[dict], limit: int) -> list[dict]:
    kept = []
    for match in matches:
        if any(_distance_meters(match["coords"], existing["coords"]) < RESULT_DEDUPE_METERS for existing in kept):
            continue
        kept.append(match)
        if len(kept) >= limit:
            break
    return kept


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


def search_road_pattern(
    index: dict,
    pattern: dict,
    *,
    rotation_invariant: bool = True,
    limit: int = 25,
    allowed_road_groups: list[str] | None = None,
) -> dict:
    allowed_groups = set(allowed_road_groups or [])
    stroke_patterns = _stroke_patterns(pattern)
    if stroke_patterns:
        return _search_stroke_patterns(
            index,
            stroke_patterns,
            rotation_invariant=rotation_invariant,
            limit=limit,
            allowed_groups=allowed_groups,
        )

    linear_path = _linear_pattern_path(pattern)
    if linear_path:
        return _search_linear_pattern(
            index,
            linear_path,
            rotation_invariant=rotation_invariant,
            limit=min(limit, 15),
            allowed_groups=allowed_groups,
        )

    _center, pattern_branches, pattern_degrees = _pattern_anchor(pattern)
    pattern_angles = [branch["angle"] for branch in pattern_branches]
    pattern_gaps = _relative_gaps(pattern_angles)
    pattern_degree = len(pattern_angles)

    candidates = []
    for item in index["intersections"]:
        if not _candidate_allowed(item, allowed_groups):
            continue
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
                "paths": [branch["coords"] for branch in item["branches"]],
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
        "matches": _dedupe_nearby_matches(candidates, limit),
    }


def _search_stroke_patterns(
    index: dict,
    stroke_patterns: list[list[dict]],
    *,
    rotation_invariant: bool,
    limit: int,
    allowed_groups: set[str] | None,
) -> dict:
    candidates = []
    for item in index["intersections"]:
        if not _candidate_allowed(item, allowed_groups):
            continue

        candidate_paths = _candidate_trace_paths(item)
        if not candidate_paths:
            continue

        total_penalty = 0.0
        matched_paths = []
        for stroke in stroke_patterns:
            best_path = None
            best_penalty = 100.0
            for candidate_path in candidate_paths:
                penalty = _polyline_distance(stroke, candidate_path, rotation_invariant)
                if penalty < best_penalty:
                    best_penalty = penalty
                    best_path = candidate_path
            total_penalty += best_penalty
            if best_path:
                matched_paths.append(best_path)

        average_penalty = total_penalty / len(stroke_patterns)
        length_penalty = _relative_length_penalty(stroke_patterns, matched_paths)
        complexity_penalty = max(0, len(stroke_patterns) - len(matched_paths)) * 15
        score = max(0.0, 100.0 - average_penalty - length_penalty - complexity_penalty)
        if score < FREE_TRACE_MIN_SCORE:
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
                "paths": matched_paths,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return {
        "pattern": {
            "degree": len(stroke_patterns),
            "angles": [],
            "branchTurns": [],
            "mode": "free-trace",
            "rotationInvariant": rotation_invariant,
        },
        "matches": _dedupe_nearby_matches(candidates, limit),
    }


def _search_linear_pattern(
    index: dict,
    linear_path: list[dict],
    *,
    rotation_invariant: bool,
    limit: int,
    allowed_groups: set[str] | None,
) -> dict:
    candidates = []
    for item in index["intersections"]:
        if not _candidate_allowed(item, allowed_groups):
            continue
        candidate_path = _candidate_linear_path(item)
        if not candidate_path:
            continue

        shape_penalty = _polyline_distance(linear_path, candidate_path, rotation_invariant)
        score = max(0.0, 100.0 - shape_penalty)
        if score < LINEAR_MIN_SCORE:
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
                "paths": [candidate_path],
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return {
        "pattern": {
            "degree": 2,
            "angles": [],
            "branchTurns": [],
            "mode": "linear-trace",
            "rotationInvariant": rotation_invariant,
        },
        "matches": _dedupe_nearby_matches(candidates, limit),
    }
