#!/usr/bin/env python3
import math
import os
import random
import shutil
import subprocess

import make_delaunay_eroded_tube_tile as tile
import make_delaunay_eroded_tube_tile_low_profile as low
import make_tessellating_tube_tile as base


INCH = 25.4
BOX_SHORT_IN = 14.75
BOX_LONG_IN = 26.75
BOX_HEIGHT_IN = 12.0
BOX_BASE_ALLOWANCE_IN = low.LOW_BASE / INCH
PANEL_HEIGHT_IN = 4.0
SHORT_COLUMNS = 3
LONG_COLUMNS = 6
WALL_ROWS = 3
BOX_PANEL_TOP_SCALE = 0.96
BOX_PANEL_FOOT_TO_TOP_SCALE = 0.35
BOX_TUBE_WALL = 1.55
WHITE_FREQUENCY = 0.18
ORANGE_FREQUENCY = 0.225
PERF_HOLE_SIZE = 2.6
PERF_SPACING = 4.8
PERF_EDGE_MARGIN = 6.0
PERF_SOCKET_CLEARANCE = 3.0
PERF_TUBE_FOOT_CLEARANCE = 0.4
FACE_EDGE_OVERHANG = 5.0
VORONOI_NEIGHBOR_RADIUS = 58.0
LABEL_HOLE_STROKE = 0.55
LABEL_CHAR_WIDTH = 3.0
LABEL_CHAR_HEIGHT = 5.0
LABEL_CHAR_GAP = 0.85
LABEL_X = 5.0
LABEL_Y = 5.0
LABEL_RECESS_DEPTH = 0.75
POST_STACK_CONNECTOR_OFFSET = 5.5
POST_STACK_CONNECTOR_CHAMFER = 2.4
CORNER_FILLER_REACH = low.LOW_BASE
CORNER_FILLER_EMBED = 0.05
PREFIX = "box_wall"


def configure_box_profile():
    low.configure_low_profile()
    tile.POINT_REJECTION_RADIUS = low.LOW_POINT_REJECTION_RADIUS
    tile.WALL = BOX_TUBE_WALL


def panel_specs():
    short_w = (BOX_SHORT_IN - 2.0 * BOX_BASE_ALLOWANCE_IN) / SHORT_COLUMNS
    long_w = (BOX_LONG_IN - 2.0 * BOX_BASE_ALLOWANCE_IN) / LONG_COLUMNS
    return [
        {
            "name": "short_panel_4p805x4",
            "label": "short face panel",
            "width": short_w * INCH,
            "height": PANEL_HEIGHT_IN * INCH,
            "columns": SHORT_COLUMNS,
            "rows": WALL_ROWS,
            "faces": 2,
            "seed": tile.SEED + 140,
        },
        {
            "name": "long_panel_4p403x4",
            "label": "long face panel",
            "width": long_w * INCH,
            "height": PANEL_HEIGHT_IN * INCH,
            "columns": LONG_COLUMNS,
            "rows": WALL_ROWS,
            "faces": 2,
            "seed": tile.SEED + 260,
        },
    ]


def face_specs():
    short_w = (BOX_SHORT_IN - 2.0 * BOX_BASE_ALLOWANCE_IN) * INCH
    long_w = (BOX_LONG_IN - 2.0 * BOX_BASE_ALLOWANCE_IN) * INCH
    height = BOX_HEIGHT_IN * INCH
    return [
        {
            "name": "short",
            "label": "short face",
            "code": "S",
            "width": short_w,
            "height": height,
            "columns": SHORT_COLUMNS,
            "rows": WALL_ROWS,
            "seed": tile.SEED + 140,
        },
        {
            "name": "long",
            "label": "long face",
            "code": "L",
            "width": long_w,
            "height": height,
            "columns": LONG_COLUMNS,
            "rows": WALL_ROWS,
            "seed": tile.SEED + 260,
        },
    ]


def socket_positions(length):
    return (length / 3.0, length * 2.0 / 3.0)


def rect_socket_rects(width, height):
    rects = []
    for y in socket_positions(height):
        rects.append((base.SOCKET_INSET - base.SOCKET_SIZE / 2.0, base.SOCKET_INSET + base.SOCKET_SIZE / 2.0, y - base.SOCKET_SIZE / 2.0, y + base.SOCKET_SIZE / 2.0))
        rects.append((width - base.SOCKET_INSET - base.SOCKET_SIZE / 2.0, width - base.SOCKET_INSET + base.SOCKET_SIZE / 2.0, y - base.SOCKET_SIZE / 2.0, y + base.SOCKET_SIZE / 2.0))
    for x in socket_positions(width):
        rects.append((x - base.SOCKET_SIZE / 2.0, x + base.SOCKET_SIZE / 2.0, base.SOCKET_INSET - base.SOCKET_SIZE / 2.0, base.SOCKET_INSET + base.SOCKET_SIZE / 2.0))
        rects.append((x - base.SOCKET_SIZE / 2.0, x + base.SOCKET_SIZE / 2.0, height - base.SOCKET_INSET - base.SOCKET_SIZE / 2.0, height - base.SOCKET_INSET + base.SOCKET_SIZE / 2.0))
    return rects


def rect_inside_any_socket(x0, x1, y0, y1, rects):
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return any(base.point_in_rect(cx, cy, rect) for rect in rects)


def rect_expanded(rect, amount):
    xmin, xmax, ymin, ymax = rect
    return (xmin - amount, xmax + amount, ymin - amount, ymax + amount)


def rects_overlap(a, b):
    ax0, ax1, ay0, ay1 = a
    bx0, bx1, by0, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def rect_poly(rect):
    xmin, xmax, ymin, ymax = rect
    return [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]


def rect_overlaps_loop(rect, loop):
    poly = rect_poly(rect)
    return (
        tile.polygons_overlap(poly, loop)
        or any(tile.point_inside_polygon(loop, point) for point in poly)
        or any(tile.point_inside_polygon(poly, point) for point in loop)
    )


def expanded_loop(loop, clearance):
    center = tile.loop_center(loop)
    distances = [math.hypot(point[0] - center[0], point[1] - center[1]) for point in loop]
    radius = max(distances) if distances else 1.0
    return tile.scaled_loop(loop, center, (radius + clearance) / max(radius, 1e-6))


def perforation_rects(width, height, socket_rects, cells, label_rects=None):
    holes = []
    protected_sockets = [rect_expanded(rect, PERF_SOCKET_CLEARANCE) for rect in socket_rects]
    protected_feet = [expanded_loop(cell["base_loop"], PERF_TUBE_FOOT_CLEARANCE) for cell in cells]
    protected_labels = [rect_expanded(rect, PERF_SOCKET_CLEARANCE) for rect in (label_rects or [])]
    half = PERF_HOLE_SIZE / 2.0
    x = PERF_EDGE_MARGIN + half
    while x <= width - PERF_EDGE_MARGIN - half:
        y = PERF_EDGE_MARGIN + half
        while y <= height - PERF_EDGE_MARGIN - half:
            rect = (x - half, x + half, y - half, y + half)
            if not any(rects_overlap(rect, protected) for protected in protected_sockets):
                if not any(rects_overlap(rect, protected) for protected in protected_labels):
                    if not any(rect_overlaps_loop(rect, loop) for loop in protected_feet):
                        holes.append(rect)
            y += PERF_SPACING
        x += PERF_SPACING
    return holes


def label_segment_rects(label):
    segments = {
        "0": "abcedf",
        "1": "bc",
        "2": "abged",
        "3": "abgcd",
        "4": "fgbc",
        "5": "afgcd",
        "6": "afgecd",
        "7": "abc",
        "8": "abcdefg",
        "9": "abfgcd",
        "S": "afgcd",
        "L": "fed",
    }
    w = LABEL_CHAR_WIDTH
    h = LABEL_CHAR_HEIGHT
    s = LABEL_HOLE_STROKE
    g = min(0.12, s * 0.25)
    rects = []

    def add_segment(x, y, name):
        if name == "a":
            rects.append((x + s + g, x + w - s - g, y + h - s, y + h))
        elif name == "b":
            rects.append((x + w - s, x + w, y + h / 2.0 + s / 2.0 + g, y + h - s - g))
        elif name == "c":
            rects.append((x + w - s, x + w, y + s + g, y + h / 2.0 - s / 2.0 - g))
        elif name == "d":
            rects.append((x + s + g, x + w - s - g, y, y + s))
        elif name == "e":
            rects.append((x, x + s, y + s + g, y + h / 2.0 - s / 2.0 - g))
        elif name == "f":
            rects.append((x, x + s, y + h / 2.0 + s / 2.0 + g, y + h - s - g))
        elif name == "g":
            rects.append((x + s + g, x + w - s - g, y + h / 2.0 - s / 2.0, y + h / 2.0 + s / 2.0))

    for index, char in enumerate(label.upper()):
        x = LABEL_X + index * (w + LABEL_CHAR_GAP)
        y = LABEL_Y
        for segment in segments.get(char, ""):
            add_segment(x, y, segment)
    return rects


def rect_inside_any(x0, x1, y0, y1, rects):
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return any(base.point_in_rect(cx, cy, rect) for rect in rects)


def segment_values(values, lower, upper):
    return sorted(set([lower, upper] + [value for value in values if lower < value < upper]))


def add_rect_ceiling(mesh, rect, z, xs, ys):
    xmin, xmax, ymin, ymax = rect
    xparts = segment_values(xs, xmin, xmax)
    yparts = segment_values(ys, ymin, ymax)
    for xi in range(len(xparts) - 1):
        for yi in range(len(yparts) - 1):
            x0, x1 = xparts[xi], xparts[xi + 1]
            y0, y1 = yparts[yi], yparts[yi + 1]
            mesh.add_quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))


def add_rect_walls(mesh, rect, z, xs, ys):
    xmin, xmax, ymin, ymax = rect
    xparts = segment_values(xs, xmin, xmax)
    yparts = segment_values(ys, ymin, ymax)
    for xi in range(len(xparts) - 1):
        x0, x1 = xparts[xi], xparts[xi + 1]
        mesh.add_quad((x0, ymin, 0.0), (x1, ymin, 0.0), (x1, ymin, z), (x0, ymin, z))
        mesh.add_quad((x1, ymax, 0.0), (x0, ymax, 0.0), (x0, ymax, z), (x1, ymax, z))
    for yi in range(len(yparts) - 1):
        y0, y1 = yparts[yi], yparts[yi + 1]
        mesh.add_quad((xmax, y0, 0.0), (xmax, y1, 0.0), (xmax, y1, z), (xmax, y0, z))
        mesh.add_quad((xmin, y1, 0.0), (xmin, y0, 0.0), (xmin, y0, z), (xmin, y1, z))


def add_corner_filler(mesh, width, height, side):
    if side not in ("left", "right"):
        return
    reach = CORNER_FILLER_REACH
    embed = CORNER_FILLER_EMBED
    if side == "left":
        x0 = embed
        x1 = -reach
    else:
        x0 = width - embed
        x1 = width + reach
    bottom_a = (x0, 0.0, 0.0)
    top_a = (x0, 0.0, base.BASE)
    outer_a = (x1, 0.0, base.BASE)
    bottom_b = (x0, height, 0.0)
    top_b = (x0, height, base.BASE)
    outer_b = (x1, height, base.BASE)
    mesh.add_quad(bottom_a, bottom_b, top_b, top_a)
    mesh.add_quad(bottom_b, bottom_a, outer_a, outer_b)
    mesh.add_quad(top_a, top_b, outer_b, outer_a)
    mesh.add_tri(bottom_a, top_a, outer_a)
    mesh.add_tri(bottom_b, outer_b, top_b)


def add_rect_base_with_bottom_ports(mesh, width, height, cells=None, perforated=False, label=None, corner_filler=None):
    socket_rects = rect_socket_rects(width, height)
    label_rects = label_segment_rects(label) if label else []
    perf_rects = perforation_rects(width, height, socket_rects, cells or [], label_rects) if perforated else []
    through_rects = perf_rects
    bottom_recess_rects = socket_rects + label_rects
    all_rects = socket_rects + through_rects + label_rects
    xs = sorted(set([0.0, width] + [value for rect in all_rects for value in (rect[0], rect[1])]))
    ys = sorted(set([0.0, height] + [value for rect in all_rects for value in (rect[2], rect[3])]))
    for xi in range(len(xs) - 1):
        for yi in range(len(ys) - 1):
            x0, x1 = xs[xi], xs[xi + 1]
            y0, y1 = ys[yi], ys[yi + 1]
            inside_through = rect_inside_any(x0, x1, y0, y1, through_rects)
            inside_bottom_recess = rect_inside_any(x0, x1, y0, y1, bottom_recess_rects)
            if not inside_through:
                mesh.add_quad((x0, y0, base.BASE), (x1, y0, base.BASE), (x1, y1, base.BASE), (x0, y1, base.BASE))
            if inside_through or inside_bottom_recess:
                continue
            mesh.add_quad((x0, y1, 0.0), (x1, y1, 0.0), (x1, y0, 0.0), (x0, y0, 0.0))

    for xi in range(len(xs) - 1):
        x0, x1 = xs[xi], xs[xi + 1]
        mesh.add_quad((x0, 0.0, 0.0), (x1, 0.0, 0.0), (x1, 0.0, base.BASE), (x0, 0.0, base.BASE))
        mesh.add_quad((x1, height, 0.0), (x0, height, 0.0), (x0, height, base.BASE), (x1, height, base.BASE))
    for yi in range(len(ys) - 1):
        y0, y1 = ys[yi], ys[yi + 1]
        mesh.add_quad((width, y0, 0.0), (width, y1, 0.0), (width, y1, base.BASE), (width, y0, base.BASE))
        mesh.add_quad((0.0, y1, 0.0), (0.0, y0, 0.0), (0.0, y0, base.BASE), (0.0, y1, base.BASE))

    for xmin, xmax, ymin, ymax in socket_rects:
        z = base.SOCKET_DEPTH
        add_rect_ceiling(mesh, (xmin, xmax, ymin, ymax), z, xs, ys)
        add_rect_walls(mesh, (xmin, xmax, ymin, ymax), z, xs, ys)

    for xmin, xmax, ymin, ymax in through_rects:
        add_rect_walls(mesh, (xmin, xmax, ymin, ymax), base.BASE, xs, ys)

    for xmin, xmax, ymin, ymax in label_rects:
        z = min(LABEL_RECESS_DEPTH, base.BASE - 0.25)
        add_rect_ceiling(mesh, (xmin, xmax, ymin, ymax), z, xs, ys)
        add_rect_walls(mesh, (xmin, xmax, ymin, ymax), z, xs, ys)

    add_corner_filler(mesh, width, height, corner_filler)
    return len(perf_rects)


def torus_distance(point_a, point_b, width, height):
    dx = abs(point_a[0] - point_b[0])
    dy = abs(point_a[1] - point_b[1])
    return math.hypot(min(dx, width - dx), min(dy, height - dy))


def rejection_periodic_points(width, height, count, radius, seed):
    rng = random.Random(seed)
    central = []
    for _ in range(tile.POINT_REJECTION_ATTEMPTS):
        candidate = (rng.random() * width, rng.random() * height)
        if all(torus_distance(candidate, point, width, height) >= radius for point in central):
            central.append(candidate)
            if len(central) >= count:
                break
    if len(central) != count:
        raise ValueError("Could not place %d points in %.1f x %.1f panel" % (count, width, height))

    points = []
    for sx in (-1, 0, 1):
        for sy in (-1, 0, 1):
            for x, y in central:
                points.append((x + sx * width, y + sy * height))
    return points


def rejection_points(width, height, count, radius, seed):
    rng = random.Random(seed)
    points = []
    for _ in range(tile.POINT_REJECTION_ATTEMPTS):
        candidate = (rng.random() * width, rng.random() * height)
        if all(math.hypot(candidate[0] - point[0], candidate[1] - point[1]) >= radius for point in points):
            points.append(candidate)
            if len(points) >= count:
                break
    if len(points) != count:
        raise ValueError("Could not place %d points in %.1f x %.1f face" % (count, width, height))
    return points


def spatial_bins(points, cell_size):
    bins = {}
    for index, point in enumerate(points):
        key = (int(point[0] // cell_size), int(point[1] // cell_size))
        bins.setdefault(key, []).append(index)
    return bins


def nearby_point_indices(points, bins, point, radius, cell_size):
    bx = int(point[0] // cell_size)
    by = int(point[1] // cell_size)
    reach = int(math.ceil(radius / cell_size))
    result = []
    r2 = radius * radius
    for gx in range(bx - reach, bx + reach + 1):
        for gy in range(by - reach, by + reach + 1):
            for index in bins.get((gx, gy), []):
                other = points[index]
                dx = other[0] - point[0]
                dy = other[1] - point[1]
                if dx * dx + dy * dy <= r2:
                    result.append(index)
    return result


def clip_polygon_halfplane(poly, a, b, c):
    if not poly:
        return []

    def inside(point):
        return a * point[0] + b * point[1] <= c + 1e-8

    def intersect(p, q):
        vp = a * p[0] + b * p[1] - c
        vq = a * q[0] + b * q[1] - c
        denom = vp - vq
        if abs(denom) < 1e-12:
            return p
        t = vp / denom
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    output = []
    prev = poly[-1]
    prev_inside = inside(prev)
    for current in poly:
        current_inside = inside(current)
        if current_inside:
            if not prev_inside:
                output.append(intersect(prev, current))
            output.append(current)
        elif prev_inside:
            output.append(intersect(prev, current))
        prev = current
        prev_inside = current_inside
    return output


def face_voronoi_polygons(width, height, count, radius, seed):
    points = rejection_points(width, height, count, radius, seed)
    bins = spatial_bins(points, radius)
    bound = FACE_EDGE_OVERHANG
    bounds_poly = [
        (-bound, -bound),
        (width + bound, -bound),
        (width + bound, height + bound),
        (-bound, height + bound),
    ]
    polygons = []
    for index, site in enumerate(points):
        poly = bounds_poly[:]
        for other_index in nearby_point_indices(points, bins, site, VORONOI_NEIGHBOR_RADIUS, radius):
            if other_index == index:
                continue
            other = points[other_index]
            a = 2.0 * (other[0] - site[0])
            b = 2.0 * (other[1] - site[1])
            c = other[0] * other[0] + other[1] * other[1] - site[0] * site[0] - site[1] * site[1]
            poly = clip_polygon_halfplane(poly, a, b, c)
            if len(poly) < 3:
                break
        if len(poly) < 3:
            continue
        if tile.signed_area(poly) < 0.0:
            poly.reverse()
        polygons.append((site, poly))
    return polygons


def rejection_periodic_point_cloud(width, height, count, radius, seed):
    rng = random.Random(seed)
    central = []
    for _ in range(tile.POINT_REJECTION_ATTEMPTS):
        candidate = (rng.random() * width, rng.random() * height)
        if all(torus_distance(candidate, point, width, height) >= radius for point in central):
            central.append(candidate)
            if len(central) >= count:
                break
    if len(central) != count:
        raise ValueError("Could not place %d points in %.1f x %.1f panel" % (count, width, height))

    points = []
    central_ids = []
    for sx in (-1, 0, 1):
        for sy in (-1, 0, 1):
            for index, (x, y) in enumerate(central):
                point_id = len(points)
                points.append((x + sx * width, y + sy * height))
                if sx == 0 and sy == 0:
                    central_ids.append((index, point_id))
    return central, points, central_ids


def localize_point_rect(point, center, width, height):
    x, y = point
    while x - center[0] > width / 2.0:
        x -= width
    while x - center[0] < -width / 2.0:
        x += width
    while y - center[1] > height / 2.0:
        y -= height
    while y - center[1] < -height / 2.0:
        y += height
    return (x, y)


def fit_loop_inside_rect(loop, width, height, margin=tile.BASE_MARGIN):
    xmin, xmax, ymin, ymax = tile.loop_bounds(loop)
    if xmax - xmin > width - 2.0 * margin or ymax - ymin > height - 2.0 * margin:
        return None, (0.0, 0.0)
    dx = 0.0
    dy = 0.0
    if xmin < margin:
        dx = margin - xmin
    if xmax + dx > width - margin:
        dx += (width - margin) - (xmax + dx)
    if ymin < margin:
        dy = margin - ymin
    if ymax + dy > height - margin:
        dy += (height - margin) - (ymax + dy)
    return tile.offset_loop(loop, dx, dy), (dx, dy)


def clip_polygon_edge(poly, inside_fn, intersect_fn):
    if not poly:
        return []
    output = []
    prev = poly[-1]
    prev_inside = inside_fn(prev)
    for current in poly:
        current_inside = inside_fn(current)
        if current_inside:
            if not prev_inside:
                output.append(intersect_fn(prev, current))
            output.append(current)
        elif prev_inside:
            output.append(intersect_fn(prev, current))
        prev = current
        prev_inside = current_inside
    return output


def clip_polygon_to_rect(poly, width, height):
    def ix_at_x(x):
        def intersect(a, b):
            dx = b[0] - a[0]
            if abs(dx) < 1e-9:
                return (x, a[1])
            t = (x - a[0]) / dx
            return (x, a[1] + (b[1] - a[1]) * t)

        return intersect

    def ix_at_y(y):
        def intersect(a, b):
            dy = b[1] - a[1]
            if abs(dy) < 1e-9:
                return (a[0], y)
            t = (y - a[1]) / dy
            return (a[0] + (b[0] - a[0]) * t, y)

        return intersect

    clipped = poly[:]
    clipped = clip_polygon_edge(clipped, lambda p: p[0] >= 0.0, ix_at_x(0.0))
    clipped = clip_polygon_edge(clipped, lambda p: p[0] <= width, ix_at_x(width))
    clipped = clip_polygon_edge(clipped, lambda p: p[1] >= 0.0, ix_at_y(0.0))
    clipped = clip_polygon_edge(clipped, lambda p: p[1] <= height, ix_at_y(height))
    deduped = []
    for point in clipped:
        if not deduped or math.hypot(point[0] - deduped[-1][0], point[1] - deduped[-1][1]) > 1e-5:
            deduped.append(point)
    if len(deduped) > 1 and math.hypot(deduped[0][0] - deduped[-1][0], deduped[0][1] - deduped[-1][1]) <= 1e-5:
        deduped.pop()
    return deduped


def clip_loop_min_y(loop, min_y=0.0):
    clipped = clip_polygon_edge(
        loop,
        lambda p: p[1] >= min_y,
        lambda a, b: (
            a[0] + (b[0] - a[0]) * ((min_y - a[1]) / (b[1] - a[1])) if abs(b[1] - a[1]) > 1e-9 else a[0],
            min_y,
        ),
    )
    deduped = []
    for point in clipped:
        if not deduped or math.hypot(point[0] - deduped[-1][0], point[1] - deduped[-1][1]) > 1e-5:
            deduped.append(point)
    if len(deduped) > 1 and math.hypot(deduped[0][0] - deduped[-1][0], deduped[0][1] - deduped[-1][1]) <= 1e-5:
        deduped.pop()
    if len(deduped) < 3 or abs(tile.signed_area(deduped)) < tile.MIN_AREA:
        return loop
    if tile.signed_area(deduped) < 0.0:
        deduped.reverse()
    return deduped


def circumcenter(points, tri):
    ax, ay = points[tri[0]]
    bx, by = points[tri[1]]
    cx, cy = points[tri[2]]
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy)


def voronoi_cells_from_points(width, height, count, radius, seed):
    central, points, central_ids = rejection_periodic_point_cloud(width, height, count, radius, seed)
    triangles = tile.delaunay(points)
    incident = {point_id: [] for _index, point_id in central_ids}
    for tri in triangles:
        center = circumcenter(points, tri)
        if center is None:
            continue
        for point_id in tri:
            if point_id in incident:
                incident[point_id].append(center)

    polygons = []
    for central_index, point_id in central_ids:
        site = central[central_index]
        centers = []
        seen = set()
        for center in incident[point_id]:
            localized = localize_point_rect(center, site, width, height)
            key = (round(localized[0], 5), round(localized[1], 5))
            if key in seen:
                continue
            seen.add(key)
            centers.append(localized)
        if len(centers) < 3:
            continue
        centers.sort(key=lambda point: math.atan2(point[1] - site[1], point[0] - site[0]))
        if tile.signed_area(centers) < 0.0:
            centers.reverse()
        if tile.polygon_self_intersects(centers):
            continue
        polygons.append((site, centers))
    return polygons


def color_for_cell(rng):
    roll = rng.random()
    if roll < ORANGE_FREQUENCY:
        return 4
    if roll < ORANGE_FREQUENCY + WHITE_FREQUENCY:
        return 3
    return 2


def materialized_voronoi_pieces(width, height, polygons):
    del width, height
    pieces = []
    for site, polygon in polygons:
        pieces.append((site, polygon))
    return pieces


def point_count_for_panel(width, height):
    low_area = (4.0 * INCH) * (4.0 * INCH)
    return max(24, int(round(low.LOW_POINT_COUNT * width * height / low_area)))


def point_count_for_face(width, height):
    low_area = (4.0 * INCH) * (4.0 * INCH)
    return max(24, int(round(low.LOW_POINT_COUNT * width * height / low_area)))


def constrain_loop_to_rect(loop, width, height, margin=tile.BASE_MARGIN):
    center = tile.loop_center(loop)
    scale = 1.0
    for x, y in loop:
        dx = x - center[0]
        dy = y - center[1]
        if dx < -1e-9:
            scale = min(scale, (margin - center[0]) / dx)
        elif dx > 1e-9:
            scale = min(scale, (width - margin - center[0]) / dx)
        if dy < -1e-9:
            scale = min(scale, (margin - center[1]) / dy)
        elif dy > 1e-9:
            scale = min(scale, (height - margin - center[1]) / dy)
    scale = max(0.12, min(1.0, scale))
    return tile.scaled_loop(loop, center, scale)


def translate_loop_into_rect(loop, width, height, margin=tile.BASE_MARGIN):
    xmin, xmax, ymin, ymax = tile.loop_bounds(loop)
    dx = 0.0
    dy = 0.0
    if xmin < margin:
        dx = margin - xmin
    if xmax + dx > width - margin:
        dx += (width - margin) - (xmax + dx)
    if ymin < margin:
        dy = margin - ymin
    if ymax + dy > height - margin:
        dy += (height - margin) - (ymax + dy)
    return tile.offset_loop(loop, dx, dy)


def constrain_base_loop_to_rect(loop, width, height, margin=tile.BASE_MARGIN):
    xmin, xmax, ymin, ymax = tile.loop_bounds(loop)
    usable_w = width - 2.0 * margin
    usable_h = height - 2.0 * margin
    loop_w = xmax - xmin
    loop_h = ymax - ymin
    if loop_w <= usable_w and loop_h <= usable_h:
        return translate_loop_into_rect(loop, width, height, margin)

    center = tile.loop_center(loop)
    scale = min(usable_w / max(loop_w, 1e-6), usable_h / max(loop_h, 1e-6)) * 0.98
    scaled = tile.scaled_loop(loop, center, max(0.12, min(1.0, scale)))
    return translate_loop_into_rect(scaled, width, height, margin)


def make_face_cells(face):
    width = face["width"]
    height = face["height"]
    count = point_count_for_face(width, height)
    rng = random.Random(face["seed"] + 91)
    polygons = face_voronoi_polygons(width, height, count, low.LOW_POINT_REJECTION_RADIUS, face["seed"])
    cells = []
    for site, polygon in polygons:
        area = abs(tile.signed_area(polygon))
        if area < tile.MIN_AREA:
            continue

        centroid = tile.loop_center(polygon)
        base_loop = tile.eroded_loop(polygon, centroid, tile.OUTER_BASE_SCALE, tile.BASE_SMOOTHING)
        top_loop = tile.eroded_loop(polygon, centroid, tile.BOUNDARY_SCALE, tile.TOP_SMOOTHING)
        top_loop = tile.smooth_loop(top_loop, tile.TOP_SMOOTHING)
        center = tile.loop_center(top_loop)
        low_top_loop = tile.scaled_loop(top_loop, center, BOX_PANEL_TOP_SCALE)
        low_top_loop = clip_loop_min_y(low_top_loop, 0.0)
        center = tile.loop_center(low_top_loop)
        low_foot_loop = tile.scaled_loop(low_top_loop, center, BOX_PANEL_FOOT_TO_TOP_SCALE)
        cells.append(
            {
                "tri": polygon,
                "site": site,
                "centroid": centroid,
                "base_center": tile.loop_center(low_foot_loop),
                "base_loop": base_loop,
                "top_loop": low_top_loop,
                "low_foot_loop": low_foot_loop,
                "low_top_loop": low_top_loop,
                "height": low.LOW_TUBE_HEIGHT * (1.0 + rng.uniform(-low.LOW_HEIGHT_STAGGER, low.LOW_HEIGHT_STAGGER)),
                "color": color_for_cell(rng),
                "rim_phase": rng.uniform(0.0, 2.0 * math.pi),
                "rim_phase2": rng.uniform(0.0, 2.0 * math.pi),
            }
        )
    return cells


def offset_cell_to_panel(cell, x0, y0, panel_width, panel_height):
    def shifted(loop):
        return [(x - x0, y - y0) for x, y in loop]

    top_loop = shifted(cell["top_loop"])
    base_loop = shifted(cell["low_foot_loop"])
    base_loop = constrain_base_loop_to_rect(base_loop, panel_width, panel_height)
    base_center = tile.loop_center(base_loop)
    return {
        "tri": shifted(cell["tri"]),
        "site": (cell["site"][0] - x0, cell["site"][1] - y0),
        "centroid": (cell["centroid"][0] - x0, cell["centroid"][1] - y0),
        "base_center": base_center,
        "base_loop": base_loop,
        "top_loop": top_loop,
        "low_foot_loop": base_loop,
        "low_top_loop": top_loop,
        "height": cell["height"],
        "color": cell["color"],
        "rim_phase": cell["rim_phase"],
        "rim_phase2": cell["rim_phase2"],
    }


def cells_for_panel(face_cells, x0, y0, panel_width, panel_height):
    cells = []
    x1 = x0 + panel_width
    y1 = y0 + panel_height
    for cell in face_cells:
        x, y = cell["site"]
        if x0 <= x < x1 and y0 <= y < y1:
            cells.append(offset_cell_to_panel(cell, x0, y0, panel_width, panel_height))
    return cells


def make_panel_cells(spec):
    width = spec["width"]
    height = spec["height"]
    count = point_count_for_panel(width, height)
    rng = random.Random(spec["seed"] + 91)
    polygons = voronoi_cells_from_points(width, height, count, low.LOW_POINT_REJECTION_RADIUS, spec["seed"])
    pieces = materialized_voronoi_pieces(width, height, polygons)
    cells = []
    for site, polygon in pieces:
        area = abs(tile.signed_area(polygon))
        if area < tile.MIN_AREA:
            continue

        centroid = tile.loop_center(polygon)
        base_loop = tile.eroded_loop(polygon, centroid, tile.OUTER_BASE_SCALE, tile.BASE_SMOOTHING)
        top_loop = tile.eroded_loop(polygon, centroid, tile.BOUNDARY_SCALE, tile.TOP_SMOOTHING)
        base_loop, _base_shift = fit_loop_inside_rect(base_loop, width, height)
        if base_loop is None:
            continue
        top_loop = tile.smooth_loop(top_loop, tile.TOP_SMOOTHING)
        center = tile.loop_center(top_loop)
        low_top_loop = tile.scaled_loop(top_loop, center, BOX_PANEL_TOP_SCALE)
        low_foot_loop = tile.scaled_loop(low_top_loop, center, BOX_PANEL_FOOT_TO_TOP_SCALE)
        cells.append(
            {
                "tri": polygon,
                "site": site,
                "centroid": centroid,
                "base_center": tile.loop_center(low_foot_loop),
                "base_loop": low_foot_loop,
                "top_loop": low_top_loop,
                "low_foot_loop": low_foot_loop,
                "low_top_loop": low_top_loop,
                "height": low.LOW_TUBE_HEIGHT * (1.0 + rng.uniform(-low.LOW_HEIGHT_STAGGER, low.LOW_HEIGHT_STAGGER)),
                "color": color_for_cell(rng),
                "rim_phase": rng.uniform(0.0, 2.0 * math.pi),
                "rim_phase2": rng.uniform(0.0, 2.0 * math.pi),
            }
        )
    resolve_panel_overlaps(cells, width, height)
    return cells


def loops_overlap_rect(loop_a, loop_b, width, height):
    bounds_a = tile.loop_bounds(loop_a)
    bounds_b = tile.loop_bounds(loop_b)
    ax0, ax1, ay0, ay1 = bounds_a
    bx0_raw, bx1_raw, by0_raw, by1_raw = bounds_b
    for sx in (-width, 0.0, width):
        for sy in (-height, 0.0, height):
            bx0 = bx0_raw + sx
            bx1 = bx1_raw + sx
            by0 = by0_raw + sy
            by1 = by1_raw + sy
            if ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0:
                continue
            shifted = [(p[0] + sx, p[1] + sy) for p in loop_b]
            if tile.polygons_overlap(loop_a, shifted):
                return True
    return False


def top_overlap_pairs_rect(cells, width, height):
    pairs = []
    for i, cell_a in enumerate(cells):
        for j, cell_b in enumerate(cells[i + 1:], start=i + 1):
            if loops_overlap_rect(cell_a["top_loop"], cell_b["top_loop"], width, height):
                pairs.append((i, j))
    return pairs


def shrink_cell(cell, factor):
    center = tile.loop_center(cell["top_loop"])
    cell["top_loop"] = tile.scaled_loop(cell["top_loop"], center, factor)
    cell["low_top_loop"] = cell["top_loop"]
    cell["low_foot_loop"] = tile.scaled_loop(cell["top_loop"], center, BOX_PANEL_FOOT_TO_TOP_SCALE)
    cell["base_loop"] = cell["low_foot_loop"]
    cell["base_center"] = tile.loop_center(cell["base_loop"])


def resolve_panel_overlaps(cells, width, height):
    for _ in range(70):
        conflicted = set()
        for i, j in top_overlap_pairs_rect(cells, width, height):
            conflicted.add(i)
            conflicted.add(j)
        for i, j, _z in body_overlap_pairs_rect(cells, width, height):
            conflicted.add(i)
            conflicted.add(j)
        if not conflicted:
            return
        for index in conflicted:
            shrink_cell(cells[index], 0.982)


def overlap_audit_rect(cells, width, height):
    return len(top_overlap_pairs_rect(cells, width, height))


def loops_overlap_plain(loop_a, loop_b):
    ax0, ax1, ay0, ay1 = tile.loop_bounds(loop_a)
    bx0, bx1, by0, by1 = tile.loop_bounds(loop_b)
    if ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0:
        return False
    return tile.polygons_overlap(loop_a, loop_b)


def overlap_audit_plain(cells):
    overlaps = 0
    for i, cell_a in enumerate(cells):
        for cell_b in cells[i + 1:]:
            if loops_overlap_plain(cell_a["top_loop"], cell_b["top_loop"]):
                overlaps += 1
    return overlaps


def body_overlap_pairs_plain(cells):
    overlaps = []
    bottom_z = tile.BASE - tile.TUBE_BASE_EMBED
    max_top_z = max((tile.tube_top_z(cell) for cell in cells), default=bottom_z)
    sample_zs = [
        bottom_z + (max_top_z - bottom_z) * (sample + 0.5) / tile.BODY_COLLISION_SAMPLES
        for sample in range(tile.BODY_COLLISION_SAMPLES)
    ]
    sampled = []
    for cell in cells:
        rings = []
        for z in sample_zs:
            t = tile.profile_t_for_z(cell, z)
            if t < tile.BODY_COLLISION_MIN_T or t > tile.BODY_COLLISION_MAX_T or z > tile.tube_top_z(cell):
                rings.append(None)
                continue
            rings.append(tile.outer_loop_at_t(cell, t))
        sampled.append(rings)
    for i, _cell_a in enumerate(cells):
        for j, _cell_b in enumerate(cells[i + 1:], start=i + 1):
            for sample, z in enumerate(sample_zs):
                ring_a = sampled[i][sample]
                ring_b = sampled[j][sample]
                if ring_a is None or ring_b is None:
                    continue
                if loops_overlap_plain(ring_a, ring_b):
                    overlaps.append((i, j, z))
                    break
    return overlaps




def body_overlap_pairs_rect(cells, width, height):
    overlaps = []
    bottom_z = tile.BASE - tile.TUBE_BASE_EMBED
    max_top_z = max((tile.tube_top_z(cell) for cell in cells), default=bottom_z)
    sample_zs = [
        bottom_z + (max_top_z - bottom_z) * (sample + 0.5) / tile.BODY_COLLISION_SAMPLES
        for sample in range(tile.BODY_COLLISION_SAMPLES)
    ]
    sampled = []
    for cell in cells:
        rings = []
        for z in sample_zs:
            t = tile.profile_t_for_z(cell, z)
            if t < tile.BODY_COLLISION_MIN_T or t > tile.BODY_COLLISION_MAX_T or z > tile.tube_top_z(cell):
                rings.append(None)
                continue
            loop = tile.outer_loop_at_t(cell, t)
            rings.append(loop)
        sampled.append(rings)
    for i, _cell_a in enumerate(cells):
        for j, _cell_b in enumerate(cells[i + 1:], start=i + 1):
            for sample, z in enumerate(sample_zs):
                ring_a = sampled[i][sample]
                ring_b = sampled[j][sample]
                if ring_a is None or ring_b is None:
                    continue
                if loops_overlap_rect(ring_a, ring_b, width, height):
                    overlaps.append((i, j, z))
                    break
    return overlaps


def coverage_estimate_rect(cells, width, height, samples=1200):
    rng = random.Random(42)
    hits = 0
    loops = [cell["top_loop"] for cell in cells]
    for _ in range(samples):
        point = (rng.random() * width, rng.random() * height)
        if any(tile.point_inside_polygon(loop, point) for loop in loops):
            hits += 1
    return hits / samples


def write_panel_preview(path, spec, cells, tiled=False):
    palette = {1: "#111111", 2: "#d8b692", 3: "#f7f3e8", 4: "#e8662e"}
    width = spec["width"]
    height = spec["height"]
    cols = 3 if tiled else 1
    rows = 3 if tiled else 1
    margin = 8.0
    with open(path, "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.3f %.3f %.3f %.3f" width="1600" height="1600">\n' % (-margin, -margin, width * cols + margin * 2, height * rows + margin * 2))
        f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#f1eadf"/>\n' % (-margin, -margin, width * cols + margin * 2, height * rows + margin * 2))
        for row in range(rows):
            for col in range(cols):
                ox = col * width
                oy = row * height
                f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="%s" stroke="#6e5a48" stroke-width="0.45" stroke-opacity="0.55"/>\n' % (ox, oy, width, height, palette[1]))
                for cell in sorted(cells, key=lambda item: item["height"]):
                    loop = cell["top_loop"]
                    inner = tile.inner_loop_from_outer(loop)
                    if inner is None:
                        continue
                    points = " ".join("%.3f,%.3f" % (p[0] + ox, height - p[1] + oy) for p in loop)
                    inner_points = " ".join("%.3f,%.3f" % (p[0] + ox, height - p[1] + oy) for p in inner)
                    f.write('<polygon points="%s" fill="%s" stroke="#4d352b" stroke-width="0.35" stroke-opacity="0.18"/>\n' % (points, palette[cell["color"]]))
                    f.write('<polygon points="%s" fill="#2f201a" fill-opacity="0.22"/>\n' % inner_points)
        f.write("</svg>\n")


def write_png_for_svg(svg_path, width=2200):
    converter = shutil.which("rsvg-convert")
    if converter is None:
        print("Skipping PNG preview; rsvg-convert was not found")
        return
    subprocess.run([converter, "-w", str(width), svg_path, "-o", os.path.splitext(svg_path)[0] + ".png"], check=True)


def build_panel(spec, perforated=False):
    cells = make_panel_cells(spec)
    meshes = {1: base.Mesh(), 2: base.Mesh(), 3: base.Mesh(), 4: base.Mesh()}
    perforation_count = add_rect_base_with_bottom_ports(meshes[1], spec["width"], spec["height"], cells, perforated)
    for cell in cells:
        tile.add_eroded_triangle_tube(meshes[cell["color"]], cell)

    combined = base.Mesh()
    for mesh in meshes.values():
        combined.extend(mesh)

    stem = "%s_%s%s" % (PREFIX, spec["name"], "_perforated" if perforated else "")
    for color_number, label in ((1, "black"), (2, "beige"), (3, "white"), (4, "orange")):
        meshes[color_number].write_ascii_stl(os.path.join(base.OUT_DIR, "%s_color_%d_%s.stl" % (stem, color_number, label)), "%s_color_%d_%s" % (stem, color_number, label))
    combined.write_ascii_stl(os.path.join(base.OUT_DIR, "%s_combined_reference.stl" % stem), "%s_combined_reference" % stem)

    top_overlaps = overlap_audit_rect(cells, spec["width"], spec["height"])
    body_overlaps = len(body_overlap_pairs_rect(cells, spec["width"], spec["height"]))
    min_wall = tile.hollow_wall_audit(cells)
    coverage = coverage_estimate_rect(cells, spec["width"], spec["height"])
    top_svg = os.path.join(base.OUT_DIR, "%s_top_preview.svg" % stem)
    tess_svg = os.path.join(base.OUT_DIR, "%s_tessellation_preview.svg" % stem)
    write_panel_preview(top_svg, spec, cells, tiled=False)
    write_panel_preview(tess_svg, spec, cells, tiled=True)
    write_png_for_svg(top_svg)
    write_png_for_svg(tess_svg)
    return {
        "stem": stem,
        "label": stem,
        "cells": len(cells),
        "top_overlaps": top_overlaps,
        "body_overlaps": body_overlaps,
        "min_wall": min_wall,
        "coverage": coverage,
        "perforations": perforation_count,
        "triangles": len(combined.tris),
    }


def build_panel_from_cells(stem, cells, panel_width, panel_height, label=None, corner_filler=None):
    panel_dir = os.path.join(base.OUT_DIR, stem)
    os.makedirs(panel_dir, exist_ok=True)

    solid_base = base.Mesh()
    perforated_base = base.Mesh()
    tube_meshes = {2: base.Mesh(), 3: base.Mesh(), 4: base.Mesh()}
    add_rect_base_with_bottom_ports(solid_base, panel_width, panel_height, cells, perforated=False, label=label, corner_filler=corner_filler)
    perforation_count = add_rect_base_with_bottom_ports(perforated_base, panel_width, panel_height, cells, perforated=True, label=label, corner_filler=corner_filler)
    for cell in cells:
        tile.add_eroded_triangle_tube(tube_meshes[cell["color"]], cell)

    solid_base.write_ascii_stl(
        os.path.join(panel_dir, "%s_base_solid_color_1_black.stl" % stem),
        "%s_base_solid_color_1_black" % stem,
    )
    perforated_base.write_ascii_stl(
        os.path.join(panel_dir, "%s_base_perforated_color_1_black.stl" % stem),
        "%s_base_perforated_color_1_black" % stem,
    )
    for color_number, color_label in ((2, "beige"), (3, "white"), (4, "orange")):
        tube_meshes[color_number].write_ascii_stl(
            os.path.join(panel_dir, "%s_tubes_color_%d_%s.stl" % (stem, color_number, color_label)),
            "%s_tubes_color_%d_%s" % (stem, color_number, color_label),
        )

    top_overlaps = overlap_audit_plain(cells)
    body_overlaps = len(body_overlap_pairs_plain(cells))
    min_wall = tile.hollow_wall_audit(cells)
    coverage = coverage_estimate_rect(cells, panel_width, panel_height)
    return {
        "stem": stem,
        "label": label or stem,
        "cells": len(cells),
        "top_overlaps": top_overlaps,
        "body_overlaps": body_overlaps,
        "min_wall": min_wall,
        "coverage": coverage,
        "perforations": perforation_count,
        "triangles": len(solid_base.tris) + sum(len(mesh.tris) for mesh in tube_meshes.values()),
    }


def write_face_preview(path, face, cells):
    palette = {1: "#111111", 2: "#d8b692", 3: "#f7f3e8", 4: "#e8662e"}
    width = face["width"]
    height = face["height"]
    margin = 8.0
    pixel_width = 2600
    pixel_height = max(500, int(round(pixel_width * height / width)))
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.3f %.3f %.3f %.3f" width="%d" height="%d">\n'
            % (-margin, -margin, width + margin * 2.0, height + margin * 2.0, pixel_width, pixel_height)
        )
        f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#f4f0e7"/>\n' % (-margin, -margin, width + margin * 2.0, height + margin * 2.0))
        f.write('<rect x="0" y="0" width="%.3f" height="%.3f" fill="%s"/>\n' % (width, height, palette[1]))
        for cell in sorted(cells, key=lambda item: item["height"]):
            loop = cell["top_loop"]
            inner = tile.inner_loop_from_outer(loop)
            if inner is None:
                continue
            points = " ".join("%.3f,%.3f" % (p[0], height - p[1]) for p in loop)
            inner_points = " ".join("%.3f,%.3f" % (p[0], height - p[1]) for p in inner)
            f.write('<polygon points="%s" fill="%s" stroke="#4d352b" stroke-width="0.35" stroke-opacity="0.20"/>\n' % (points, palette[cell["color"]]))
            f.write('<polygon points="%s" fill="#2f201a" fill-opacity="0.24"/>\n' % inner_points)
        for col in range(1, face["columns"]):
            x = width * col / face["columns"]
            f.write('<line x1="%.3f" y1="0" x2="%.3f" y2="%.3f" stroke="#ffffff" stroke-width="1.0" stroke-opacity="0.65"/>\n' % (x, x, height))
        for row in range(1, face["rows"]):
            y = height * row / face["rows"]
            f.write('<line x1="0" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#ffffff" stroke-width="1.0" stroke-opacity="0.65"/>\n' % (height - y, width, height - y))
        f.write('<rect x="0" y="0" width="%.3f" height="%.3f" fill="none" stroke="#2b2621" stroke-width="1.1" stroke-opacity="0.65"/>\n' % (width, height))
        f.write("</svg>\n")


def build_face_panels(face):
    face_cells = make_face_cells(face)
    preview_dir = os.path.join(base.OUT_DIR, "previews")
    os.makedirs(preview_dir, exist_ok=True)
    preview_svg = os.path.join(preview_dir, "%s_%s_side_preview.svg" % (PREFIX, face["name"]))
    write_face_preview(preview_svg, face, face_cells)
    write_png_for_svg(preview_svg)

    panel_width = face["width"] / face["columns"]
    panel_height = face["height"] / face["rows"]
    summaries = []
    for row in range(face["rows"]):
        for col in range(face["columns"]):
            x0 = col * panel_width
            y0 = row * panel_height
            panel_cells = cells_for_panel(face_cells, x0, y0, panel_width, panel_height)
            label = "%s%d%d" % (face["code"], row + 1, col + 1)
            stem = "%s_%s_r%d_c%d" % (PREFIX, face["name"], row + 1, col + 1)
            corner_filler = "left" if col == 0 else "right" if col == face["columns"] - 1 else None
            summaries.append(build_panel_from_cells(stem, panel_cells, panel_width, panel_height, label=label, corner_filler=corner_filler))
    return summaries


def scaled_polygon(points, factor):
    return [(x * factor, y * factor) for x, y in points]


def make_stack_sleeve(height=25.0, clearance=0.65, wall=3.0):
    half = tile.POST_WIDTH / 2.0
    chamfer = min(tile.POST_INSIDE_CHAMFER, tile.POST_WIDTH - 2.0)
    body = [
        (-half + chamfer, -half),
        (half, -half),
        (half, half),
        (-half, half),
        (-half, -half + chamfer),
    ]
    inner_factor = (tile.POST_WIDTH + clearance * 2.0) / tile.POST_WIDTH
    outer_factor = (tile.POST_WIDTH + clearance * 2.0 + wall * 2.0) / tile.POST_WIDTH
    inner = scaled_polygon(body, inner_factor)
    outer = scaled_polygon(body, outer_factor)
    mesh = base.Mesh()
    for i in range(len(body)):
        j = (i + 1) % len(body)
        ob0 = (outer[i][0], outer[i][1], 0.0)
        ob1 = (outer[j][0], outer[j][1], 0.0)
        ot0 = (outer[i][0], outer[i][1], height)
        ot1 = (outer[j][0], outer[j][1], height)
        ib0 = (inner[i][0], inner[i][1], 0.0)
        ib1 = (inner[j][0], inner[j][1], 0.0)
        it0 = (inner[i][0], inner[i][1], height)
        it1 = (inner[j][0], inner[j][1], height)
        mesh.add_quad(ob0, ob1, ot1, ot0)
        mesh.add_quad(ib1, ib0, it0, it1)
        mesh.add_quad(ot0, ot1, it1, it0)
        mesh.add_quad(ob1, ob0, ib0, ib1)
    return mesh


def add_top_stack_tab(mesh, height, center=(0.0, 0.0)):
    z0 = height
    z1 = height + base.STUD_HEIGHT
    tile.add_extruded_polygon(mesh, stack_connector_polygon(center, base.STUD_SIZE), z0, z1)


def stack_connector_polygon(center, size):
    cx, cy = center
    s = size / 2.0
    return [
        (cx - s, cy - s),
        (cx + s, cy - s),
        (cx + s, cy + s),
        (cx - s, cy + s),
    ]


def clip_polygon_xmax(poly, xmax):
    return clip_polygon_edge(
        poly,
        lambda p: p[0] <= xmax,
        lambda a, b: (xmax, a[1] + (b[1] - a[1]) * ((xmax - a[0]) / (b[0] - a[0])) if abs(b[0] - a[0]) > 1e-9 else a[1]),
    )


def clip_polygon_xmin(poly, xmin):
    return clip_polygon_edge(
        poly,
        lambda p: p[0] >= xmin,
        lambda a, b: (xmin, a[1] + (b[1] - a[1]) * ((xmin - a[0]) / (b[0] - a[0])) if abs(b[0] - a[0]) > 1e-9 else a[1]),
    )


def clip_polygon_ymax(poly, ymax):
    return clip_polygon_edge(
        poly,
        lambda p: p[1] <= ymax,
        lambda a, b: (a[0] + (b[0] - a[0]) * ((ymax - a[1]) / (b[1] - a[1])) if abs(b[1] - a[1]) > 1e-9 else a[0], ymax),
    )


def clip_polygon_ymin(poly, ymin):
    return clip_polygon_edge(
        poly,
        lambda p: p[1] >= ymin,
        lambda a, b: (a[0] + (b[0] - a[0]) * ((ymin - a[1]) / (b[1] - a[1])) if abs(b[1] - a[1]) > 1e-9 else a[0], ymin),
    )


def add_clipped_post_socket_ring(mesh, body, socket_poly, depth):
    sx0, sx1, sy0, sy1 = tile.loop_bounds(socket_poly)
    overlap = 0.035
    pieces = [
        clip_polygon_xmax(body, sx0 + overlap),
        clip_polygon_xmin(body, sx1 - overlap),
        clip_polygon_ymax(clip_polygon_xmin(clip_polygon_xmax(body, sx1 + overlap), sx0 - overlap), sy0 + overlap),
        clip_polygon_ymin(clip_polygon_xmin(clip_polygon_xmax(body, sx1 + overlap), sx0 - overlap), sy1 - overlap),
    ]
    for piece in pieces:
        if len(piece) >= 3 and abs(tile.signed_area(piece)) >= tile.MIN_AREA:
            tile.add_extruded_polygon(mesh, piece, 0.0, depth)


def add_corner_post_face_stud_x(mesh, x0, y0, z0):
    s = base.STUD_SIZE / 2.0
    reach = base.STUD_HEIGHT
    x1 = x0 + reach
    base.add_box(mesh, x0, x1, y0 - s, y0 + s, z0 - s, z0 + s)
    rib = 0.45
    base.add_box(mesh, x0 + reach * 0.45, x1 - 0.25, y0 - s - rib, y0 + s + rib, z0 - 1.05, z0 + 1.05)


def add_corner_post_face_stud_y(mesh, x0, y0, z0):
    s = base.STUD_SIZE / 2.0
    reach = base.STUD_HEIGHT
    y1 = y0 + reach
    base.add_box(mesh, x0 - s, x0 + s, y0, y1, z0 - s, z0 + s)
    rib = 0.45
    base.add_box(mesh, x0 - 1.05, x0 + 1.05, y0 + reach * 0.45, y1 - 0.25, z0 - s - rib, z0 + s + rib)


def make_stackable_corner_post(height, socket_positions):
    mesh = base.Mesh()
    half = tile.POST_WIDTH / 2.0
    socket_half = base.SOCKET_SIZE / 2.0
    depth = base.SOCKET_DEPTH
    overlap = 0.04
    stack_center = (POST_STACK_CONNECTOR_OFFSET, POST_STACK_CONNECTOR_OFFSET)
    chamfer = min(tile.POST_INSIDE_CHAMFER, tile.POST_WIDTH - 2.0)
    body = [
        (-half + chamfer, -half),
        (half, -half),
        (half, half),
        (-half, half),
        (-half, -half + chamfer),
    ]
    sx, sy = stack_center
    # Bottom ring leaves an offset socket recess for the tab on the post below,
    # while preserving the chamfered-away inside corner of the post footprint.
    socket_poly = stack_connector_polygon(stack_center, base.SOCKET_SIZE)
    add_clipped_post_socket_ring(mesh, body, socket_poly, depth)
    tile.add_extruded_polygon(mesh, body, depth - overlap, height)
    for z in socket_positions:
        add_corner_post_face_stud_x(mesh, half, 0.0, z)
        add_corner_post_face_stud_y(mesh, 0.0, half, z)
    add_top_stack_tab(mesh, height, stack_center)
    return mesh


def write_readme(path, summaries):
    short_w = (BOX_SHORT_IN - 2.0 * BOX_BASE_ALLOWANCE_IN) / SHORT_COLUMNS
    long_w = (BOX_LONG_IN - 2.0 * BOX_BASE_ALLOWANCE_IN) / LONG_COLUMNS
    with open(path, "w", encoding="utf-8") as f:
        f.write("Box wall tile set\n")
        f.write("=================\n\n")
        f.write("Panel surface algorithm: one full-face Voronoi field for each box side length, subdivided into separate printable panels.\n")
        f.write("Each panel has a small shallow back-side label such as S11 or L36; labels are not visible from the front.\n")
        f.write("Outer column panels include a black 45-degree corner filler lip; bottom-edge tube loops are clipped so the box can sit flat.\n")
        f.write("Target box: %.2f in x %.2f in x %.2f in tall.\n" % (BOX_SHORT_IN, BOX_LONG_IN, BOX_HEIGHT_IN))
        f.write("Base-height allowance used in panel math: %.3f in per end.\n" % BOX_BASE_ALLOWANCE_IN)
        f.write("Short face clear span: %.2f in = %d panels at %.2f in wide.\n" % (BOX_SHORT_IN - 2.0 * BOX_BASE_ALLOWANCE_IN, SHORT_COLUMNS, short_w))
        f.write("Long face clear span: %.2f in = %d panels at %.2f in wide.\n" % (BOX_LONG_IN - 2.0 * BOX_BASE_ALLOWANCE_IN, LONG_COLUMNS, long_w))
        f.write("Wall height: %d rows at %.2f in high.\n\n" % (WALL_ROWS, PANEL_HEIGHT_IN))
        f.write("Panel counts for one short face: %d panels; one long face: %d panels. Print two copies of each face set for a full box.\n" % (SHORT_COLUMNS * WALL_ROWS, LONG_COLUMNS * WALL_ROWS))
        f.write("Corner posts: print %d four-inch post sections for four 12-inch corners; each post has a top tab and bottom socket for stacking.\n" % (4 * WALL_ROWS))
        horizontal_pairs = 2 * ((SHORT_COLUMNS - 1) * WALL_ROWS + (LONG_COLUMNS - 1) * WALL_ROWS)
        vertical_pairs = 2 * (SHORT_COLUMNS + LONG_COLUMNS) * (WALL_ROWS - 1)
        f.write("Straight seam connectors: about %d two-stud connectors for panel-to-panel seams if every socket pair is connected.\n\n" % ((horizontal_pairs + vertical_pairs) * 2))
        f.write("Each panel folder contains shared beige/white/orange tube STLs plus two black base choices: solid and perforated.\n")
        f.write("For a solid panel, import the solid black base and the three tube STLs. For an airflow panel, import the perforated black base and the same three tube STLs.\n")
        f.write("PNG previews for the full short and long side layouts are in outputs/previews.\n\n")
        for summary in summaries:
            f.write("%s: %d cells, %d airflow perforations, %d sampled body overlaps, %d top overlaps, %.2f mm minimum wall, %.1f%% top coverage.\n" % (summary["stem"], summary["cells"], summary["perforations"], summary["body_overlaps"], summary["top_overlaps"], summary["min_wall"], summary["coverage"] * 100.0))
        f.write("\nBambu colors: color 1 black base, color 2 beige tubes, color 3 white tubes, color 4 orange tubes.\n")
        f.write("Tube color frequencies: %.1f%% orange, %.1f%% white, %.1f%% beige.\n" % (ORANGE_FREQUENCY * 100.0, WHITE_FREQUENCY * 100.0, (1.0 - ORANGE_FREQUENCY - WHITE_FREQUENCY) * 100.0))


def main():
    configure_box_profile()
    os.makedirs(base.OUT_DIR, exist_ok=True)
    summaries = []
    for face in face_specs():
        summaries.extend(build_face_panels(face))

    post_height = PANEL_HEIGHT_IN * INCH
    post_socket_positions = socket_positions(post_height)
    post_dir = os.path.join(base.OUT_DIR, "%s_corner_post_4in" % PREFIX)
    os.makedirs(post_dir, exist_ok=True)
    make_stackable_corner_post(post_height, post_socket_positions).write_ascii_stl(
        os.path.join(post_dir, "%s_corner_post_4in.stl" % PREFIX),
        "%s_corner_post_4in" % PREFIX,
    )
    connector_dir = os.path.join(base.OUT_DIR, "%s_straight_snap_connector" % PREFIX)
    os.makedirs(connector_dir, exist_ok=True)
    base.make_straight_connector().write_ascii_stl(
        os.path.join(connector_dir, "%s_straight_snap_connector.stl" % PREFIX),
        "%s_straight_snap_connector" % PREFIX,
    )
    write_readme(os.path.join(base.OUT_DIR, "%s_README.txt" % PREFIX), summaries)

    for summary in summaries:
        print("%s [%s]: %d cells, perforations %d, body overlaps %d, top overlaps %d, coverage %.1f%%, triangles %d" % (
            summary["stem"],
            summary["label"],
            summary["cells"],
            summary["perforations"],
            summary["body_overlaps"],
            summary["top_overlaps"],
            summary["coverage"] * 100.0,
            summary["triangles"],
        ))
    print("Generated 4 inch corner post with top tab and bottom socket")


if __name__ == "__main__":
    main()
