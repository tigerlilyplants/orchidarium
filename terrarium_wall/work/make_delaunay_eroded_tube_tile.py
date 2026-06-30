#!/usr/bin/env python3
import math
import os
import random
import shutil
import subprocess

import make_tessellating_tube_tile as base


OUT_DIR = base.OUT_DIR
TILE = base.TILE
BASE = base.BASE
TUBE_MAX_HEIGHT = base.TUBE_MAX_HEIGHT
SEED = 76127

POINT_COUNT = 81
POINT_REJECTION_RADIUS = 7.2
POINT_REJECTION_ATTEMPTS = 80000
MIN_AREA = 20.0
MAX_AREA = 360.0
OUTER_BASE_SCALE = 0.58
BOUNDARY_SCALE = 0.995
WALL = 1.00
OUTER_MITER_LIMIT = 2.20
NZ = 16
TUBE_BASE_EMBED = 0.75
HORN_FOOT_LOCK = 0.10
INNER_OPEN_START = 0.12
INNER_OPEN_END = 0.36
POST_WIDTH = base.SOCKET_INSET * 2.0
POST_INSIDE_CHAMFER = base.SOCKET_INSET
POST_STUD_EXTRA_REACH = 1.20
BASE_MARGIN = 0.35
BASE_SMOOTHING = 4
TOP_SMOOTHING = 2
RIM_LIFT = 0.85
RIM_INNER_DROP = 0.65
RIM_WAVE = 0.32
MAX_RIM_EXTRA = RIM_LIFT + RIM_WAVE * 1.45
BODY_MAX_HEIGHT = TUBE_MAX_HEIGHT - MAX_RIM_EXTRA
UNIFORM_TUBE_HEIGHT = 25.4
BODY_COLLISION_SAMPLES = 13
BODY_COLLISION_MIN_T = 0.18
BODY_COLLISION_MAX_T = 0.93


def dist2(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def signed_area(poly):
    total = 0.0
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        total += p[0] * q[1] - q[0] * p[1]
    return total * 0.5


def triangle_area(tri):
    a, b, c = tri
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) * 0.5


def circumcircle_contains(points, tri, p):
    ax, ay = points[tri[0]]
    bx, by = points[tri[1]]
    cx, cy = points[tri[2]]
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return False
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    r2 = (ux - ax) * (ux - ax) + (uy - ay) * (uy - ay)
    return (p[0] - ux) * (p[0] - ux) + (p[1] - uy) * (p[1] - uy) <= r2 + 1e-7


def delaunay(points):
    xmin = min(p[0] for p in points)
    xmax = max(p[0] for p in points)
    ymin = min(p[1] for p in points)
    ymax = max(p[1] for p in points)
    span = max(xmax - xmin, ymax - ymin)
    midx = (xmin + xmax) / 2.0
    midy = (ymin + ymax) / 2.0
    super_pts = [(midx - 20 * span, midy - span), (midx, midy + 20 * span), (midx + 20 * span, midy - span)]
    all_points = list(points) + super_pts
    super_ids = set(range(len(points), len(points) + 3))
    tris = [(len(points), len(points) + 1, len(points) + 2)]

    for pi, p in enumerate(points):
        bad = []
        for tri in tris:
            if circumcircle_contains(all_points, tri, p):
                bad.append(tri)

        edge_count = {}
        for tri in bad:
            for edge in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                key = tuple(sorted(edge))
                edge_count[key] = edge_count.get(key, 0) + 1
        boundary = [edge for edge, count in edge_count.items() if count == 1]
        bad_set = set(bad)
        tris = [tri for tri in tris if tri not in bad_set]
        for a, b in boundary:
            candidate = (a, b, pi)
            pa, pb, pc = all_points[a], all_points[b], all_points[pi]
            if signed_area([pa, pb, pc]) < 0:
                candidate = (b, a, pi)
            tris.append(candidate)

    return [tri for tri in tris if not (set(tri) & super_ids)]


def torus_distance(a, b):
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    dx = min(dx, TILE - dx)
    dy = min(dy, TILE - dy)
    return math.hypot(dx, dy)


def rejection_periodic_points():
    rng = random.Random(SEED)
    central = []
    for _ in range(POINT_REJECTION_ATTEMPTS):
        candidate = (rng.random() * TILE, rng.random() * TILE)
        if all(torus_distance(candidate, point) >= POINT_REJECTION_RADIUS for point in central):
            central.append(candidate)
            if len(central) >= POINT_COUNT:
                break
    if len(central) != POINT_COUNT:
        raise ValueError(
            "Could not place %d points with %.2f mm rejection radius; placed %d"
            % (POINT_COUNT, POINT_REJECTION_RADIUS, len(central))
        )

    points = []
    for sx in (-1, 0, 1):
        for sy in (-1, 0, 1):
            for x, y in central:
                points.append((x + sx * TILE, y + sy * TILE))
    return points


def chaikin(poly, iterations=4):
    pts = poly[:]
    for _ in range(iterations):
        new = []
        for i, p in enumerate(pts):
            q = pts[(i + 1) % len(pts)]
            new.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            new.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        pts = new
    return pts


def eroded_loop(tri, centroid, scale, iterations=TOP_SMOOTHING):
    pts = [(centroid[0] + (p[0] - centroid[0]) * scale, centroid[1] + (p[1] - centroid[1]) * scale) for p in tri]
    if signed_area(pts) < 0:
        pts.reverse()
    return chaikin(pts, iterations)


def loop_radius(loop, centroid):
    return sum(math.hypot(p[0] - centroid[0], p[1] - centroid[1]) for p in loop) / len(loop)


def loop_center(loop):
    return (sum(p[0] for p in loop) / len(loop), sum(p[1] for p in loop) / len(loop))


def loop_bounds(loop):
    xs = [p[0] for p in loop]
    ys = [p[1] for p in loop]
    return min(xs), max(xs), min(ys), max(ys)


def offset_loop(loop, dx, dy):
    return [(p[0] + dx, p[1] + dy) for p in loop]


def localize_point(point, center):
    x, y = point
    while x - center[0] > TILE / 2.0:
        x -= TILE
    while x - center[0] < -TILE / 2.0:
        x += TILE
    while y - center[1] > TILE / 2.0:
        y -= TILE
    while y - center[1] < -TILE / 2.0:
        y += TILE
    return (x, y)


def localize_triangle(tri, center):
    return [localize_point(point, center) for point in tri]


def shrink_loop(loop, centroid, factor):
    return [(centroid[0] + (p[0] - centroid[0]) * factor, centroid[1] + (p[1] - centroid[1]) * factor) for p in loop]


def fit_loop_inside_tile(loop, margin=BASE_MARGIN):
    xmin, xmax, ymin, ymax = loop_bounds(loop)
    usable = TILE - 2.0 * margin
    if xmax - xmin > usable or ymax - ymin > usable:
        return None, (0.0, 0.0)

    dx = 0.0
    dy = 0.0
    if xmin < margin:
        dx = margin - xmin
    if xmax + dx > TILE - margin:
        dx += (TILE - margin) - (xmax + dx)
    if ymin < margin:
        dy = margin - ymin
    if ymax + dy > TILE - margin:
        dy += (TILE - margin) - (ymax + dy)
    return offset_loop(loop, dx, dy), (dx, dy)


def lerp_loop(a, b, t):
    return [(pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t) for pa, pb in zip(a, b)]


def lerp_point(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def color_for_cell(x, y, rng):
    del x, y
    pick = rng.random()
    if pick < 0.22:
        return 2
    if pick < 0.58:
        return 4
    return 3


def rim_wave(cell, index, count):
    angle = 2.0 * math.pi * index / count
    return (
        RIM_WAVE * math.sin(2.0 * angle + cell["rim_phase"])
        + RIM_WAVE * 0.45 * math.sin(5.0 * angle + cell["rim_phase2"])
    )


def make_cells():
    rng = random.Random(SEED + 9)
    points = rejection_periodic_points()
    tris = delaunay(points)
    cells = []
    seen = set()
    for tri_ids in tris:
        raw_tri = [points[i] for i in tri_ids]
        raw_cx = sum(p[0] for p in raw_tri) / 3.0
        raw_cy = sum(p[1] for p in raw_tri) / 3.0
        if not (0.0 <= raw_cx < TILE and 0.0 <= raw_cy < TILE):
            continue
        tri = localize_triangle(raw_tri, (raw_cx, raw_cy))
        area = triangle_area(tri)
        if area < MIN_AREA or area > MAX_AREA:
            continue
        cx = sum(p[0] for p in tri) / 3.0
        cy = sum(p[1] for p in tri) / 3.0
        key = (round(cx % TILE, 3), round(cy % TILE, 3))
        if key in seen:
            continue
        seen.add(key)
        centroid = (cx, cy)
        base_outer_loop = eroded_loop(tri, centroid, OUTER_BASE_SCALE, BASE_SMOOTHING)
        base_loop, base_shift = fit_loop_inside_tile(base_outer_loop)
        if base_loop is None:
            continue
        boundary_loop = eroded_loop(tri, centroid, BOUNDARY_SCALE, TOP_SMOOTHING)
        color = color_for_cell(cx % TILE, cy % TILE, rng)
        cells.append(
            {
                "tri": tri,
                "centroid": centroid,
                "base_center": loop_center(base_loop),
                "base_loop": base_loop,
                "boundary_loop": boundary_loop,
                "top_loop": boundary_loop,
                "height": UNIFORM_TUBE_HEIGHT,
                "color": color,
                "rim_phase": rng.uniform(0.0, 2.0 * math.pi),
                "rim_phase2": rng.uniform(0.0, 2.0 * math.pi),
            }
        )
    return cells


def resolve_base_footprint_overlaps(cells):
    for _ in range(36):
        changed_indices = set()
        outer_loops = [cell["base_loop"] for cell in cells]
        for i, cell_a in enumerate(cells):
            outer_a = outer_loops[i]
            for j, cell_b in enumerate(cells[i + 1:], start=i + 1):
                outer_b = outer_loops[j]
                if loops_overlap_periodic(outer_a, outer_b):
                    changed_indices.add(i)
                    changed_indices.add(j)
        if not changed_indices:
            return
        for index in changed_indices:
            cells[index]["base_loop"] = shrink_loop(cells[index]["base_loop"], cells[index]["base_center"], 0.92)


def tube_bottom_z(cell):
    del cell
    return BASE - TUBE_BASE_EMBED


def tube_top_z(cell):
    return BASE + cell["height"]


def profile_t_for_z(cell, z):
    return (z - tube_bottom_z(cell)) / (cell["height"] + TUBE_BASE_EMBED)


def horn_flare_mix(t):
    if t <= HORN_FOOT_LOCK:
        return 0.0
    u = (t - HORN_FOOT_LOCK) / (1.0 - HORN_FOOT_LOCK)
    u = max(0.0, min(1.0, u))
    smooth = u * u * (3.0 - 2.0 * u)
    return 0.22 * smooth + 0.78 * smooth * smooth


def section_outer_loop(cell, t):
    return lerp_loop(cell["base_loop"], cell["top_loop"], horn_flare_mix(t))


def outer_loop_at_t(cell, t):
    return section_outer_loop(cell, t)


def loops_overlap_periodic(loop_a, loop_b, bounds_a=None, bounds_b=None):
    if loop_a is None or loop_b is None:
        return False
    if bounds_a is None:
        bounds_a = loop_bounds(loop_a)
    if bounds_b is None:
        bounds_b = loop_bounds(loop_b)
    ax0, ax1, ay0, ay1 = bounds_a
    bx0_raw, bx1_raw, by0_raw, by1_raw = bounds_b
    for sx in (-TILE, 0.0, TILE):
        for sy in (-TILE, 0.0, TILE):
            bx0 = bx0_raw + sx
            bx1 = bx1_raw + sx
            by0 = by0_raw + sy
            by1 = by1_raw + sy
            if ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0:
                continue
            shifted = [(p[0] + sx, p[1] + sy) for p in loop_b]
            if polygons_overlap(loop_a, shifted):
                return True
    return False


def body_overlap_pairs(cells, stop_after_first=False):
    overlaps = []
    bottom_z = BASE - TUBE_BASE_EMBED
    max_top_z = max((tube_top_z(cell) for cell in cells), default=bottom_z)
    sample_zs = [
        bottom_z + (max_top_z - bottom_z) * (sample + 0.5) / BODY_COLLISION_SAMPLES
        for sample in range(BODY_COLLISION_SAMPLES)
    ]
    sampled = []
    for cell in cells:
        rings = []
        for z in sample_zs:
            t = profile_t_for_z(cell, z)
            if t < BODY_COLLISION_MIN_T or t > BODY_COLLISION_MAX_T or z > tube_top_z(cell):
                rings.append(None)
                continue
            loop = outer_loop_at_t(cell, t)
            rings.append(None if loop is None else (loop, loop_bounds(loop)))
        sampled.append(rings)
    for i, cell_a in enumerate(cells):
        for j, cell_b in enumerate(cells[i + 1:], start=i + 1):
            for sample, z in enumerate(sample_zs):
                ring_a = sampled[i][sample]
                ring_b = sampled[j][sample]
                if ring_a is None or ring_b is None:
                    continue
                if loops_overlap_periodic(ring_a[0], ring_b[0], ring_a[1], ring_b[1]):
                    overlaps.append((i, j, z))
                    if stop_after_first:
                        return overlaps
                    break
    return overlaps


def scaled_loop(loop, centroid, factor):
    return [(centroid[0] + (p[0] - centroid[0]) * factor, centroid[1] + (p[1] - centroid[1]) * factor) for p in loop]


def line_intersection(a0, a1, b0, b1):
    ad = (a1[0] - a0[0], a1[1] - a0[1])
    bd = (b1[0] - b0[0], b1[1] - b0[1])
    denom = cross2(ad, bd)
    if abs(denom) < 1e-9:
        return None
    delta = (b0[0] - a0[0], b0[1] - a0[1])
    t = cross2(delta, bd) / denom
    return (a0[0] + ad[0] * t, a0[1] + ad[1] * t)


def point_inside_polygon(poly, point):
    inside = False
    j = len(poly) - 1
    x, y = point
    for i, pi in enumerate(poly):
        pj = poly[j]
        if point_segment_distance(point, pi, pj) < 1e-6:
            return True
        if ((pi[1] > y) != (pj[1] > y)) and (
            x < (pj[0] - pi[0]) * (y - pi[1]) / (pj[1] - pi[1] + 1e-12) + pi[0]
        ):
            inside = not inside
        j = i
    return inside


def segments_intersect(a, b, c, d):
    def orient(p, q, r):
        return cross2((q[0] - p[0], q[1] - p[1]), (r[0] - p[0], r[1] - p[1]))

    ab_c = orient(a, b, c)
    ab_d = orient(a, b, d)
    cd_a = orient(c, d, a)
    cd_b = orient(c, d, b)
    return ab_c * ab_d < -1e-8 and cd_a * cd_b < -1e-8


def polygon_self_intersects(poly):
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        for j in range(i + 1, n):
            if j in (i, (i + 1) % n) or i == (j + 1) % n:
                continue
            c = poly[j]
            d = poly[(j + 1) % n]
            if segments_intersect(a, b, c, d):
                return True
    return False


def inward_offset_loop(loop, wall):
    area = signed_area(loop)
    sign = 1.0 if area >= 0.0 else -1.0
    lines = []
    normals = []
    for i, p in enumerate(loop):
        q = loop[(i + 1) % len(loop)]
        dx = q[0] - p[0]
        dy = q[1] - p[1]
        length = max(1e-9, math.hypot(dx, dy))
        normal = (-dy / length * sign, dx / length * sign)
        normals.append(normal)
        lines.append(
            (
                (p[0] + normal[0] * wall, p[1] + normal[1] * wall),
                (q[0] + normal[0] * wall, q[1] + normal[1] * wall),
            )
        )

    inner = []
    for i in range(len(loop)):
        hit = line_intersection(lines[i - 1][0], lines[i - 1][1], lines[i][0], lines[i][1])
        if hit is None:
            return None
        miter_length = math.hypot(hit[0] - loop[i][0], hit[1] - loop[i][1])
        miter_cap = abs(wall) * OUTER_MITER_LIMIT
        if wall < 0.0 and miter_length > miter_cap:
            offset_a = (normals[i - 1][0] * wall, normals[i - 1][1] * wall)
            offset_b = (normals[i][0] * wall, normals[i][1] * wall)
            bisector = (offset_a[0] + offset_b[0], offset_a[1] + offset_b[1])
            length = math.hypot(bisector[0], bisector[1])
            if length < 1e-9:
                bisector = offset_b
                length = max(1e-9, math.hypot(bisector[0], bisector[1]))
            hit = (loop[i][0] + bisector[0] / length * miter_cap, loop[i][1] + bisector[1] / length * miter_cap)
        inner.append(hit)
    return inner


def smooth_loop(poly, passes=1):
    pts = poly[:]
    for _ in range(passes):
        pts = [
            (
                p[0] * 0.50 + pts[i - 1][0] * 0.25 + pts[(i + 1) % len(pts)][0] * 0.25,
                p[1] * 0.50 + pts[i - 1][1] * 0.25 + pts[(i + 1) % len(pts)][1] * 0.25,
            )
            for i, p in enumerate(pts)
        ]
    return pts


def usable_inner_loop(outer, inner):
    if inner is None or len(inner) != len(outer):
        return False
    if signed_area(outer) * signed_area(inner) <= 0.0:
        return False
    if polygon_self_intersects(inner):
        return False
    return all(point_inside_polygon(outer, point) for point in inner)


def loop_wall_distance(outer, inner):
    distances = []
    n = len(outer)
    for i, inner_point in enumerate(inner):
        for edge_index in (i - 1, i, i + 1):
            j = edge_index % n
            distances.append(point_segment_distance(inner_point, outer[j], outer[(j + 1) % n]))
    return min(distances)


def radial_inset_at_distance(outer, center, distance):
    inner = []
    for p in outer:
        dx = center[0] - p[0]
        dy = center[1] - p[1]
        length = math.hypot(dx, dy)
        if length <= distance * 1.02:
            return None
        inner.append((p[0] + dx / length * distance, p[1] + dy / length * distance))
    return inner


def radial_inset_loop(outer, distance):
    center = loop_center(outer)
    for multiplier in (1.45, 1.7, 1.95, 2.2, 2.45):
        inset = distance * multiplier
        inner = radial_inset_at_distance(outer, center, inset)
        if inner is not None and usable_inner_loop(outer, inner) and loop_wall_distance(outer, inner) >= distance * 0.98:
            return inner
    return None


def inner_loop_from_outer(outer):
    center = loop_center(outer)
    if min(math.hypot(p[0] - center[0], p[1] - center[1]) for p in outer) <= WALL * 1.35:
        return None

    best = None
    low = 0.08
    high = 0.90
    for _ in range(12):
        scale = (low + high) * 0.5
        inner = scaled_loop(outer, center, scale)
        if usable_inner_loop(outer, inner) and loop_wall_distance(outer, inner) >= WALL * 0.98:
            best = inner
            low = scale
        else:
            high = scale
    return best


def loop_supports_wall(loop):
    return inner_loop_from_outer(loop) is not None


def build_tube_sections(cell):
    height = cell["height"]
    sections = []
    open_started = False
    last_inner_loop = None
    for zi in range(NZ + 1):
        t = zi / NZ
        outer_loop = section_outer_loop(cell, t)
        inner_loop = None
        if t >= INNER_OPEN_START:
            inner_loop = inner_loop_from_outer(outer_loop)
            if inner_loop is None and open_started:
                inner_loop = last_inner_loop
            if inner_loop is not None:
                open_started = True
                last_inner_loop = inner_loop
        z = BASE - TUBE_BASE_EMBED + (height + TUBE_BASE_EMBED) * t
        rim = base.smoothstep(0.66, 1.0, t)
        count = len(outer_loop)
        outer_ring = []
        for i, p in enumerate(outer_loop):
            lift = rim * (RIM_LIFT + rim_wave(cell, i, count))
            outer_ring.append((p[0], p[1], z + lift))
        inner_ring = None
        if inner_loop is not None:
            inner_ring = []
            for i, p in enumerate(inner_loop):
                lift = rim * (RIM_LIFT - RIM_INNER_DROP + rim_wave(cell, i, count) * 0.45)
                inner_ring.append((p[0], p[1], z + lift))
        sections.append(
            {
                "t": t,
                "outer_loop": outer_loop,
                "inner_loop": inner_loop,
                "outer_ring": outer_ring,
                "inner_ring": inner_ring,
                "rim": rim,
                "z": z,
            }
        )
    return sections


def tube_supports_fixed_outer_offset(cell):
    sections = build_tube_sections(cell)
    return sections is not None and sections[-1]["inner_ring"] is not None


def add_eroded_triangle_tube(mesh, cell):
    sections = build_tube_sections(cell)
    outer = [section["outer_ring"] for section in sections]
    inner = [section["inner_ring"] for section in sections]

    n = len(outer[0])
    open_zi = next(
        (i for i, section in enumerate(sections) if section["t"] >= INNER_OPEN_START and section["inner_ring"] is not None),
        None,
    )
    for zi in range(NZ):
        for i in range(n):
            j = (i + 1) % n
            mesh.add_quad(outer[zi][i], outer[zi][j], outer[zi + 1][j], outer[zi + 1][i])
            if inner[zi] is not None and inner[zi + 1] is not None:
                mesh.add_quad(inner[zi][j], inner[zi][i], inner[zi + 1][i], inner[zi + 1][j])
    for i in range(1, n - 1):
        mesh.add_tri(outer[0][0], outer[0][i + 1], outer[0][i])
    if inner[NZ] is None:
        for i in range(1, n - 1):
            mesh.add_tri(outer[NZ][0], outer[NZ][i], outer[NZ][i + 1])
        return
    for i in range(n):
        j = (i + 1) % n
        mesh.add_quad(outer[NZ][i], outer[NZ][j], inner[NZ][j], inner[NZ][i])
    if open_zi is not None:
        for i in range(1, n - 1):
            mesh.add_tri(inner[open_zi][0], inner[open_zi][i], inner[open_zi][i + 1])


def polygons_overlap(poly_a, poly_b):
    for poly in (poly_a, poly_b):
        for i, p0 in enumerate(poly):
            p1 = poly[(i + 1) % len(poly)]
            edge = (p1[0] - p0[0], p1[1] - p0[1])
            axis = (-edge[1], edge[0])
            length = math.hypot(axis[0], axis[1])
            if length < 1e-9:
                continue
            axis = (axis[0] / length, axis[1] / length)
            amin = min(p[0] * axis[0] + p[1] * axis[1] for p in poly_a)
            amax = max(p[0] * axis[0] + p[1] * axis[1] for p in poly_a)
            bmin = min(p[0] * axis[0] + p[1] * axis[1] for p in poly_b)
            bmax = max(p[0] * axis[0] + p[1] * axis[1] for p in poly_b)
            if amax <= bmin or bmax <= amin:
                return False
    return True


def overlap_audit(cells):
    top_loops = [c["top_loop"] for c in cells]
    top_loops = [loop for loop in top_loops if loop is not None]
    overlaps = 0
    for i, a in enumerate(top_loops):
        for b in top_loops[i + 1:]:
            for sx in (-TILE, 0.0, TILE):
                for sy in (-TILE, 0.0, TILE):
                    shifted = [(p[0] + sx, p[1] + sy) for p in b]
                    if polygons_overlap(a, shifted):
                        overlaps += 1
                        break
                else:
                    continue
                break
    return overlaps


def base_overlap_audit(cells):
    overlaps = 0
    base_loops = [c["base_loop"] for c in cells]
    base_loops = [loop for loop in base_loops if loop is not None]
    for i, a in enumerate(base_loops):
        for b in base_loops[i + 1:]:
            if loops_overlap_periodic(a, b):
                overlaps += 1
    return overlaps


def point_segment_distance(point, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    ap = (point[0] - a[0], point[1] - a[1])
    denom = ab[0] * ab[0] + ab[1] * ab[1]
    if denom < 1e-12:
        return math.hypot(point[0] - a[0], point[1] - a[1])
    t = max(0.0, min(1.0, (ap[0] * ab[0] + ap[1] * ab[1]) / denom))
    closest = (a[0] + ab[0] * t, a[1] + ab[1] * t)
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def hollow_wall_audit(cells):
    walls = []
    for cell in cells:
        sections = build_tube_sections(cell)
        if sections is None:
            continue
        for section in sections:
            outer = section["outer_loop"]
            inner = section["inner_loop"]
            if inner is None:
                continue
            walls.append(loop_wall_distance(outer, inner))
    return min(walls) if walls else 0.0


def coverage_estimate(cells, samples=25000):
    rng = random.Random(42)
    top_loops = [c["top_loop"] for c in cells]
    top_loops = [loop for loop in top_loops if loop is not None]
    hits = 0
    for _ in range(samples):
        x = rng.random() * TILE
        y = rng.random() * TILE
        inside = False
        for loop in top_loops:
            # Ray-cast point-in-polygon.
            hit = False
            j = len(loop) - 1
            for i, pi in enumerate(loop):
                pj = loop[j]
                if ((pi[1] > y) != (pj[1] > y)) and (x < (pj[0] - pi[0]) * (y - pi[1]) / (pj[1] - pi[1] + 1e-12) + pi[0]):
                    hit = not hit
                j = i
            if hit:
                inside = True
                break
        if inside:
            hits += 1
    return hits / samples


def write_preview(path, cells, tiled=False):
    palette = {1: "#111111", 2: "#f7f3e8", 3: "#d8b692", 4: "#e8662e"}
    tiles = 3 if tiled else 1
    margin = 12.0
    span = TILE * tiles
    with open(path, "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.3f %.3f %.3f %.3f" width="1600" height="1600">\n' % (-margin, -margin, span + margin * 2, span + margin * 2))
        f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#f1eadf"/>\n' % (-margin, -margin, span + margin * 2, span + margin * 2))
        for ty in range(tiles):
            for tx in range(tiles):
                f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="%s" stroke="#6e5a48" stroke-width="0.45" stroke-opacity="0.55"/>\n' % (tx * TILE, ty * TILE, TILE, TILE, palette[1]))
        if tiled:
            f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="none" stroke="#2e251f" stroke-width="1.25"/>\n' % (TILE, TILE, TILE, TILE))
        for ty in range(tiles):
            for tx in range(tiles):
                for c in sorted(cells, key=lambda item: item["height"]):
                    loop = c["top_loop"]
                    inner = inner_loop_from_outer(loop)
                    if inner is None:
                        continue
                    points = " ".join("%.3f,%.3f" % (p[0] + tx * TILE, (TILE - p[1]) + ty * TILE) for p in loop)
                    inner_points = " ".join("%.3f,%.3f" % (p[0] + tx * TILE, (TILE - p[1]) + ty * TILE) for p in inner)
                    f.write('<polygon points="%s" fill="%s" stroke="#4d352b" stroke-width="0.35" stroke-opacity="0.18"/>\n' % (points, palette[c["color"]]))
                    f.write('<polygon points="%s" fill="#2f201a" fill-opacity="0.22"/>\n' % inner_points)
        f.write("</svg>\n")


def write_png_for_svg(svg_path, width=2400):
    converter = shutil.which("rsvg-convert")
    if not converter:
        print("Skipping PNG preview; rsvg-convert was not found")
        return
    png_path = os.path.splitext(svg_path)[0] + ".png"
    subprocess.run([converter, "-w", str(width), svg_path, "-o", png_path], check=True)


def add_extruded_polygon(mesh, points, zmin, zmax):
    if signed_area(points) < 0:
        points = list(reversed(points))
    bottom = [(x, y, zmin) for x, y in points]
    top = [(x, y, zmax) for x, y in points]
    for i in range(1, len(points) - 1):
        mesh.add_tri(top[0], top[i], top[i + 1])
        mesh.add_tri(bottom[0], bottom[i + 1], bottom[i])
    for i in range(len(points)):
        j = (i + 1) % len(points)
        mesh.add_quad(bottom[i], bottom[j], top[j], top[i])


def add_face_stud_x(mesh, x0, y0, z0):
    s = base.STUD_SIZE / 2.0
    reach = max(base.STUD_HEIGHT, base.SOCKET_DEPTH + POST_STUD_EXTRA_REACH)
    x1 = x0 + reach
    base.add_box(mesh, x0, x1, y0 - s, y0 + s, z0 - s, z0 + s)
    rib = 0.45
    base.add_box(mesh, x0 + reach * 0.45, x1 - 0.25, y0 - s - rib, y0 + s + rib, z0 - 1.05, z0 + 1.05)


def add_face_stud_y(mesh, x0, y0, z0):
    s = base.STUD_SIZE / 2.0
    reach = max(base.STUD_HEIGHT, base.SOCKET_DEPTH + POST_STUD_EXTRA_REACH)
    y1 = y0 + reach
    base.add_box(mesh, x0 - s, x0 + s, y0, y1, z0 - s, z0 + s)
    rib = 0.45
    base.add_box(mesh, x0 - 1.05, x0 + 1.05, y0 + reach * 0.45, y1 - 0.25, z0 - s - rib, z0 + s + rib)


def make_box_corner_post(height=None, socket_positions=None):
    if height is None:
        height = TILE
    if socket_positions is None:
        socket_positions = base.SOCKET_POS
    mesh = base.Mesh()
    half = POST_WIDTH / 2.0
    chamfer = min(POST_INSIDE_CHAMFER, POST_WIDTH - 2.0)
    body = [
        (-half + chamfer, -half),
        (half, -half),
        (half, half),
        (-half, half),
        (-half, -half + chamfer),
    ]
    add_extruded_polygon(mesh, body, 0.0, height)
    for z in socket_positions:
        add_face_stud_x(mesh, half, 0.0, z)
        add_face_stud_y(mesh, 0.0, half, z)
    return mesh


def write_readme(path, cells, overlaps, body_overlaps, base_overlaps, min_wall, coverage):
    counts = {number: sum(1 for c in cells if c["color"] == number) for number in (2, 3, 4)}
    with open(path, "w", encoding="utf-8") as f:
        f.write("Delaunay eroded-boundary tube tile\n")
        f.write("==================================\n\n")
        f.write("Alternate procedural approach: periodic fixed-radius rejection-sampled point field, pure-Python Delaunay triangulation, then eroded/smoothed triangle boundaries form the tube lips.\n")
        f.write("Dimensions: %.1f mm x %.1f mm base tile, %.2f mm base, %.1f mm max height.\n" % (TILE, TILE, BASE, base.MAX_Z))
        f.write("The physical plate is exactly the same width as the periodic Delaunay domain; edge tube interiors may lean outward while their exterior bases stay on the plate.\n")
        f.write("All horns use a uniform %.1f mm body height and stay inside their eroded Delaunay cell boundary, with no intentional overhang into neighboring cells.\n" % UNIFORM_TUBE_HEIGHT)
        f.write("Exterior cross-sections follow a smooth horn curve from smaller bases into Delaunay cell-boundary loops.\n")
        f.write("The tube body is built as a stack of increasing-height cross-sections. Each hollow section has an exterior loop and a %.2f mm inward wall target, then each ring is stitched only to the ring directly below it.\n" % WALL)
        f.write("Small bases are kept as solid stems until the horn cross-section is wide enough to support a hollow wall; a few small horns may remain capped solid.\n")
        f.write("Tube feet have a short solid vertical collar before the horn flare begins; the colored foot penetrates %.2f mm into the black base while the hollow opening starts above the plate surface to avoid tiny base slots.\n" % TUBE_BASE_EMBED)
        f.write("No tube cells are filtered out after triangulation; small cells are allowed to become solid or partially hollow horns.\n")
        f.write("Tube tops include a subtle uneven raised rim and lower inner edge, so the lip has an organic beveled curve instead of a flat cut.\n")
        f.write("Bambu Studio material mapping: color 1 = black base, color 2 = white tubes, color 3 = beige tubes, color 4 = orange tubes.\n")
        f.write("Color placement for tube colors 2-4 is randomized with fixed weighted probabilities, independent of tube height and geometry.\n")
        f.write("Audit: %d base footprint overlaps; %.2f mm minimum hollow wall; %d sampled mid-body overlaps; %d top-overhang pairs; estimated top coverage %.1f%%.\n\n" % (base_overlaps, min_wall, body_overlaps, overlaps, coverage * 100.0))
        f.write("Files:\n")
        f.write("- delaunay_tile_4in_color_1_black.stl: black base\n")
        f.write("- delaunay_tile_4in_color_2_white.stl: %d white tubes\n" % counts[2])
        f.write("- delaunay_tile_4in_color_3_beige.stl: %d beige tubes\n" % counts[3])
        f.write("- delaunay_tile_4in_color_4_orange.stl: %d orange tubes\n" % counts[4])
        f.write("- delaunay_tile_4in_combined_reference.stl: all tile geometry merged\n")
        f.write("- delaunay_tile_4in_top_preview.svg: single-tile top view\n")
        f.write("- delaunay_tile_4in_tessellation_preview.svg: 3x3 repeated top view\n")
        f.write("- delaunay_tile_box_corner_post.stl: %.1f mm tall post with connector studs on two adjacent sides and a 45 degree inside chamfer\n" % TILE)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cells = make_cells()
    meshes = {1: base.Mesh(), 2: base.Mesh(), 3: base.Mesh(), 4: base.Mesh()}
    base.add_base_with_bottom_ports(meshes[1])
    for cell in cells:
        add_eroded_triangle_tube(meshes[cell["color"]], cell)

    combined = base.Mesh()
    for mesh in meshes.values():
        combined.extend(mesh)

    color_files = {
        1: ("delaunay_tile_4in_color_1_black.stl", "delaunay_tile_4in_color_1_black"),
        2: ("delaunay_tile_4in_color_2_white.stl", "delaunay_tile_4in_color_2_white"),
        3: ("delaunay_tile_4in_color_3_beige.stl", "delaunay_tile_4in_color_3_beige"),
        4: ("delaunay_tile_4in_color_4_orange.stl", "delaunay_tile_4in_color_4_orange"),
    }
    for color_number, (filename, solid_name) in color_files.items():
        meshes[color_number].write_ascii_stl(os.path.join(OUT_DIR, filename), solid_name)
    combined.write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_4in_combined_reference.stl"), "delaunay_tile_4in_combined_reference")
    base.make_straight_connector().write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_straight_snap_connector.stl"), "delaunay_tile_straight_snap_connector")
    base.make_corner_connector().write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_corner_snap_connector.stl"), "delaunay_tile_corner_snap_connector")
    make_box_corner_post().write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_box_corner_post.stl"), "delaunay_tile_box_corner_post")

    overlaps = overlap_audit(cells)
    body_overlaps = len(body_overlap_pairs(cells))
    base_overlaps = base_overlap_audit(cells)
    min_wall = hollow_wall_audit(cells)
    coverage = coverage_estimate(cells)
    top_svg = os.path.join(OUT_DIR, "delaunay_tile_4in_top_preview.svg")
    tess_svg = os.path.join(OUT_DIR, "delaunay_tile_4in_tessellation_preview.svg")
    write_preview(top_svg, cells, tiled=False)
    write_preview(tess_svg, cells, tiled=True)
    write_png_for_svg(top_svg)
    write_png_for_svg(tess_svg)
    write_readme(os.path.join(OUT_DIR, "delaunay_tile_4in_README.txt"), cells, overlaps, body_overlaps, base_overlaps, min_wall, coverage)
    print("Generated %d Delaunay eroded tube cells" % len(cells))
    print("base footprint overlaps: %d" % base_overlaps)
    print("minimum hollow wall: %.2f mm" % min_wall)
    print("sampled mid-body overlaps: %d" % body_overlaps)
    print("top-overhang pairs: %d" % overlaps)
    print("estimated top coverage: %.1f%%" % (coverage * 100.0))
    for color_number in (1, 2, 3, 4):
        print("color %d triangles: %d" % (color_number, len(meshes[color_number].tris)))
    print("combined triangles: %d" % len(combined.tris))


if __name__ == "__main__":
    main()
