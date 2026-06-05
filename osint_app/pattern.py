import math
from collections import defaultdict


MAX_TRACE_STEPS = 18
MIN_SCORE = 25
LINEAR_MIN_SCORE = 60
FREE_TRACE_MIN_SCORE = 45
PATCH_TRACE_MIN_SCORE = 55
LINEAR_SAMPLES = 14
PATCH_ROTATION_STEP_DEGREES = 90
PATCH_SAMPLE_POINTS = 24
PATCH_CANDIDATE_LIMIT = 300
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


def _geo_to_xy(point: list[float], center: list[float]) -> tuple[float, float]:
    lat_scale = 111_320
    lon_scale = 111_320 * math.cos(math.radians(center[0]))
    return ((point[1] - center[1]) * lon_scale, (point[0] - center[0]) * lat_scale)


def _normalize_xy_polylines(polylines: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    points = [point for polyline in polylines for point in polyline]
    if not points:
        return []

    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    scale = max(max_x - min_x, max_y - min_y, 1e-9)

    return [
        [((point[0] - center_x) / scale, (point[1] - center_y) / scale) for point in polyline]
        for polyline in polylines
    ]


def _stroke_patch_geometry(strokes: list[list[dict]]) -> list[list[tuple[float, float]]]:
    polylines = [
        [(point["x"], point["y"]) for point in stroke]
        for stroke in strokes
        if len(stroke) >= 2
    ]
    return _normalize_xy_polylines(polylines)


def _stroke_overall_angles(strokes: list[list[dict]]) -> list[float]:
    return [
        _canvas_polyline_angle(stroke[0], stroke[-1])
        for stroke in strokes
        if len(stroke) >= 2
    ]


def _cheap_stroke_candidate_priority(stroke_angles: list[float], item: dict, rotation_invariant: bool) -> float:
    degree_cost = abs(item["degree"] - len(stroke_angles)) * 18
    if not stroke_angles or not item.get("angles"):
        return degree_cost + 180

    if rotation_invariant and len(stroke_angles) == len(item["angles"]):
        angle_cost = _gap_distance(_relative_gaps(stroke_angles), item["gaps"])
    else:
        remaining = list(item["angles"])
        total = 0.0
        for angle in stroke_angles:
            best = min(range(len(remaining)), key=lambda index: _angle_delta(angle, remaining[index]))
            total += _angle_delta(angle, remaining.pop(best))
            if not remaining:
                break
        angle_cost = total / len(stroke_angles)
    return degree_cost + angle_cost


def _candidate_patch_geometry(item: dict) -> list[list[tuple[float, float]]]:
    center = item["coords"]
    polylines = []
    for branch in item.get("branches", []):
        coords = branch.get("coords", [])
        if len(coords) >= 2:
            polylines.append([_geo_to_xy(point, center) for point in coords])
    return _normalize_xy_polylines(polylines)


def _polyline_length_xy(polyline: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(second[0] - first[0], second[1] - first[1])
        for first, second in zip(polyline, polyline[1:])
    )


def _sample_xy_polylines(polylines: list[list[tuple[float, float]]], sample_count: int) -> list[tuple[float, float]]:
    lengths = [_polyline_length_xy(polyline) for polyline in polylines]
    total_length = sum(lengths)
    if total_length <= 0:
        return [point for polyline in polylines for point in polyline]

    samples = []
    for polyline, length in zip(polylines, lengths):
        if length <= 0:
            continue
        count = max(2, round(sample_count * length / total_length))
        segment_lengths = [
            math.hypot(second[0] - first[0], second[1] - first[1])
            for first, second in zip(polyline, polyline[1:])
        ]
        for sample_index in range(count):
            target = (sample_index / max(1, count - 1)) * length
            covered = 0.0
            for segment_index, segment_length in enumerate(segment_lengths):
                if covered + segment_length >= target or segment_index == len(segment_lengths) - 1:
                    first = polyline[segment_index]
                    second = polyline[segment_index + 1]
                    ratio = 0.0 if segment_length <= 0 else (target - covered) / segment_length
                    samples.append(
                        (
                            first[0] + (second[0] - first[0]) * ratio,
                            first[1] + (second[1] - first[1]) * ratio,
                        )
                    )
                    break
                covered += segment_length
    return samples


def _xy_segments(polylines: list[list[tuple[float, float]]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    return [
        (first, second)
        for polyline in polylines
        for first, second in zip(polyline, polyline[1:])
    ]


def _rotate_point(point: tuple[float, float], degrees: float) -> tuple[float, float]:
    radians = math.radians(degrees)
    cos_value = math.cos(radians)
    sin_value = math.sin(radians)
    return (
        point[0] * cos_value - point[1] * sin_value,
        point[0] * sin_value + point[1] * cos_value,
    )


def _rotate_polylines(polylines: list[list[tuple[float, float]]], degrees: float) -> list[list[tuple[float, float]]]:
    if not degrees:
        return polylines
    return [[_rotate_point(point, degrees) for point in polyline] for polyline in polylines]


def _point_to_segment_distance(
    point: tuple[float, float],
    segment: tuple[tuple[float, float], tuple[float, float]],
) -> float:
    first, second = segment
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= 0:
        return math.hypot(point[0] - first[0], point[1] - first[1])
    ratio = max(0.0, min(1.0, ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy) / length_sq))
    projected = (first[0] + dx * ratio, first[1] + dy * ratio)
    return math.hypot(point[0] - projected[0], point[1] - projected[1])


def _average_nearest_segment_distance(
    points: list[tuple[float, float]],
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> float:
    if not points or not segments:
        return 1.0
    return sum(min(_point_to_segment_distance(point, segment) for segment in segments) for point in points) / len(points)


def _patch_distance(query_polylines: list[list[tuple[float, float]]], candidate_polylines: list[list[tuple[float, float]]]) -> float:
    query_points = _sample_xy_polylines(query_polylines, PATCH_SAMPLE_POINTS)
    candidate_points = _sample_xy_polylines(candidate_polylines, PATCH_SAMPLE_POINTS)
    query_segments = _xy_segments(query_polylines)
    candidate_segments = _xy_segments(candidate_polylines)
    query_to_candidate = _average_nearest_segment_distance(query_points, candidate_segments)
    candidate_to_query = _average_nearest_segment_distance(candidate_points, query_segments)
    return (query_to_candidate * 0.65) + (candidate_to_query * 0.35)


def _best_patch_distance(
    query_polylines: list[list[tuple[float, float]]],
    candidate_polylines: list[list[tuple[float, float]]],
    rotation_invariant: bool,
) -> float:
    rotations = range(0, 360, PATCH_ROTATION_STEP_DEGREES) if rotation_invariant else (0,)
    return min(_patch_distance(_rotate_polylines(query_polylines, rotation), candidate_polylines) for rotation in rotations)


def _prepared_patch(polylines: list[list[tuple[float, float]]]) -> dict:
    return {
        "polylines": polylines,
        "samples": _sample_xy_polylines(polylines, PATCH_SAMPLE_POINTS),
        "segments": _xy_segments(polylines),
    }


def _prepared_query_rotations(
    query_polylines: list[list[tuple[float, float]]],
    rotation_invariant: bool,
) -> list[dict]:
    rotations = range(0, 360, PATCH_ROTATION_STEP_DEGREES) if rotation_invariant else (0,)
    return [_prepared_patch(_rotate_polylines(query_polylines, rotation)) for rotation in rotations]


def _patch_distance_prepared(query_patch: dict, candidate_patch: dict) -> float:
    query_to_candidate = _average_nearest_segment_distance(query_patch["samples"], candidate_patch["segments"])
    candidate_to_query = _average_nearest_segment_distance(candidate_patch["samples"], query_patch["segments"])
    return (query_to_candidate * 0.65) + (candidate_to_query * 0.35)


def _best_prepared_patch_distance(query_patches: list[dict], candidate_patch: dict) -> float:
    return min(_patch_distance_prepared(query_patch, candidate_patch) for query_patch in query_patches)


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
        candidate = {
            "id": node_id,
            "coords": center,
            "degree": len(angles),
            "branches": branches,
            "angles": angles,
            "gaps": _relative_gaps(angles),
            "roadTypes": sorted(road_types[node_id]),
        }
        candidates.append(candidate)

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
    query_patch = _stroke_patch_geometry(stroke_patterns)
    if not query_patch:
        return {
            "pattern": {
                "degree": 0,
                "angles": [],
                "branchTurns": [],
                "mode": "network-patch",
                "rotationInvariant": rotation_invariant,
            },
            "matches": [],
        }

    query_patches = _prepared_query_rotations(query_patch, rotation_invariant)
    stroke_angles = _stroke_overall_angles(stroke_patterns)
    candidates = []
    candidate_items = [
        item
        for item in index["intersections"]
        if _candidate_allowed(item, allowed_groups) and item["degree"] <= max(6, len(stroke_patterns) + 4)
    ]
    candidate_items.sort(key=lambda item: _cheap_stroke_candidate_priority(stroke_angles, item, rotation_invariant))

    for item in candidate_items[:PATCH_CANDIDATE_LIMIT]:

        candidate_patch = item.get("preparedPatch")
        if not candidate_patch:
            raw_patch = item.get("patch") or _candidate_patch_geometry(item)
            candidate_patch = _prepared_patch(raw_patch)
        if not candidate_patch:
            continue

        patch_penalty = _best_prepared_patch_distance(query_patches, candidate_patch) * 180
        stroke_count_penalty = abs(len(stroke_patterns) - item["degree"]) * 2.5
        score = max(0.0, 100.0 - patch_penalty - stroke_count_penalty)
        if score < PATCH_TRACE_MIN_SCORE:
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
                "paths": [branch["coords"] for branch in item["branches"] if len(branch.get("coords", [])) >= 2],
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return {
        "pattern": {
            "degree": len(stroke_patterns),
            "angles": [],
            "branchTurns": [],
            "mode": "network-patch",
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
