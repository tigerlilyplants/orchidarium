#!/usr/bin/env python3
import math
import os
import random
import shutil
import subprocess


OUT_DIR = "/Users/willow/Documents/Codex/2026-06-27/mak/outputs"
INCH = 25.4
TILE = 6.0 * INCH
BASE = 0.25 * INCH
MAX_Z = 1.5 * INCH
TUBE_MAX_HEIGHT = MAX_Z - BASE
SEED = 60627
TUBE_CLEARANCE = 0.02
PROFILE_LEVELS = (0.0, 0.35, 0.7, 1.0)
PROFILE_SEGMENTS = 18

SOCKET_SIZE = 10.2
SOCKET_DEPTH = 4.3
SOCKET_INSET = 12.7
SOCKET_POS = (TILE / 3.0, TILE * 2.0 / 3.0)
STUD_SIZE = 9.55
STUD_HEIGHT = 4.0
BRIDGE_THICKNESS = 3.0


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vcross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vnorm(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-9:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def tri_normal(a, b, c):
    return vnorm(vcross(vsub(b, a), vsub(c, a)))


def smoothstep(edge0, edge1, x):
    if x <= edge0:
        return 0.0
    if x >= edge1:
        return 1.0
    t = (x - edge0) / (edge1 - edge0)
    return t * t * (3.0 - 2.0 * t)


def tube_outer_scale(t):
    canopy = smoothstep(0.50, 1.0, t)
    lip = smoothstep(0.76, 1.0, t)
    flare = 1.0 + 0.58 * canopy + 0.24 * lip - 0.030 * math.sin(math.pi * t)
    taper = 1.0 - 0.035 * t
    return flare * taper * 1.075


class Mesh:
    def __init__(self):
        self.tris = []

    def add_tri(self, a, b, c):
        self.tris.append((a, b, c))

    def add_quad(self, a, b, c, d):
        self.add_tri(a, b, c)
        self.add_tri(a, c, d)

    def extend(self, other):
        self.tris.extend(other.tris)

    def write_ascii_stl(self, path, name):
        with open(path, "w", encoding="ascii") as f:
            f.write(f"solid {name}\n")
            for a, b, c in self.tris:
                n = tri_normal(a, b, c)
                f.write("  facet normal %.6f %.6f %.6f\n" % n)
                f.write("    outer loop\n")
                f.write("      vertex %.6f %.6f %.6f\n" % a)
                f.write("      vertex %.6f %.6f %.6f\n" % b)
                f.write("      vertex %.6f %.6f %.6f\n" % c)
                f.write("    endloop\n")
                f.write("  endfacet\n")
            f.write(f"endsolid {name}\n")


def add_box(mesh, xmin, xmax, ymin, ymax, zmin, zmax):
    p000 = (xmin, ymin, zmin)
    p100 = (xmax, ymin, zmin)
    p110 = (xmax, ymax, zmin)
    p010 = (xmin, ymax, zmin)
    p001 = (xmin, ymin, zmax)
    p101 = (xmax, ymin, zmax)
    p111 = (xmax, ymax, zmax)
    p011 = (xmin, ymax, zmax)
    mesh.add_quad(p001, p101, p111, p011)
    mesh.add_quad(p000, p010, p110, p100)
    mesh.add_quad(p000, p100, p101, p001)
    mesh.add_quad(p100, p110, p111, p101)
    mesh.add_quad(p110, p010, p011, p111)
    mesh.add_quad(p010, p000, p001, p011)


def socket_rects():
    rects = []
    for y in SOCKET_POS:
        rects.append((SOCKET_INSET - SOCKET_SIZE / 2.0, SOCKET_INSET + SOCKET_SIZE / 2.0, y - SOCKET_SIZE / 2.0, y + SOCKET_SIZE / 2.0))
        rects.append((TILE - SOCKET_INSET - SOCKET_SIZE / 2.0, TILE - SOCKET_INSET + SOCKET_SIZE / 2.0, y - SOCKET_SIZE / 2.0, y + SOCKET_SIZE / 2.0))
    for x in SOCKET_POS:
        rects.append((x - SOCKET_SIZE / 2.0, x + SOCKET_SIZE / 2.0, SOCKET_INSET - SOCKET_SIZE / 2.0, SOCKET_INSET + SOCKET_SIZE / 2.0))
        rects.append((x - SOCKET_SIZE / 2.0, x + SOCKET_SIZE / 2.0, TILE - SOCKET_INSET - SOCKET_SIZE / 2.0, TILE - SOCKET_INSET + SOCKET_SIZE / 2.0))
    return rects


def point_in_rect(x, y, rect):
    xmin, xmax, ymin, ymax = rect
    return xmin < x < xmax and ymin < y < ymax


def rect_inside_any_socket(x0, x1, y0, y1, rects):
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return any(point_in_rect(cx, cy, r) for r in rects)


def add_base_with_bottom_ports(mesh):
    rects = socket_rects()
    mesh.add_quad((0, 0, BASE), (TILE, 0, BASE), (TILE, TILE, BASE), (0, TILE, BASE))
    mesh.add_quad((0, 0, 0), (TILE, 0, 0), (TILE, 0, BASE), (0, 0, BASE))
    mesh.add_quad((TILE, 0, 0), (TILE, TILE, 0), (TILE, TILE, BASE), (TILE, 0, BASE))
    mesh.add_quad((TILE, TILE, 0), (0, TILE, 0), (0, TILE, BASE), (TILE, TILE, BASE))
    mesh.add_quad((0, TILE, 0), (0, 0, 0), (0, 0, BASE), (0, TILE, BASE))

    xs = sorted(set([0.0, TILE] + [v for r in rects for v in (r[0], r[1])]))
    ys = sorted(set([0.0, TILE] + [v for r in rects for v in (r[2], r[3])]))
    for xi in range(len(xs) - 1):
        for yi in range(len(ys) - 1):
            x0, x1 = xs[xi], xs[xi + 1]
            y0, y1 = ys[yi], ys[yi + 1]
            if rect_inside_any_socket(x0, x1, y0, y1, rects):
                continue
            mesh.add_quad((x0, y1, 0), (x1, y1, 0), (x1, y0, 0), (x0, y0, 0))

    for xmin, xmax, ymin, ymax in rects:
        z = SOCKET_DEPTH
        mesh.add_quad((xmin, ymin, z), (xmax, ymin, z), (xmax, ymax, z), (xmin, ymax, z))
        mesh.add_quad((xmin, ymin, 0), (xmax, ymin, 0), (xmax, ymin, z), (xmin, ymin, z))
        mesh.add_quad((xmax, ymin, 0), (xmax, ymax, 0), (xmax, ymax, z), (xmax, ymin, z))
        mesh.add_quad((xmax, ymax, 0), (xmin, ymax, 0), (xmin, ymax, z), (xmax, ymax, z))
        mesh.add_quad((xmin, ymax, 0), (xmin, ymin, 0), (xmin, ymin, z), (xmin, ymax, z))


def local_to_world(cx, cy, angle, lx, ly, z):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return (cx + ca * lx - sa * ly, cy + sa * lx + ca * ly, z)


def add_tube(mesh, tube):
    cx, cy = tube["x"], tube["y"]
    angle = tube["angle"]
    rx = tube["rx"]
    ry = tube["ry"]
    wall = tube["wall"]
    height = tube["height"]
    phase1 = tube["phase1"]
    phase2 = tube["phase2"]
    ntheta = 40
    nz = 12

    outer = []
    inner = []
    for zi in range(nz + 1):
        t = zi / nz
        z = BASE + height * t
        canopy = smoothstep(0.50, 1.0, t)
        lip = smoothstep(0.76, 1.0, t)
        flare = 1.0 + 0.58 * canopy + 0.24 * lip - 0.030 * math.sin(math.pi * t)
        taper = 1.0 - 0.035 * t
        top_roll = 1.0 + 0.13 * lip
        outer_ring = []
        inner_ring = []
        for ai in range(ntheta):
            a = 2.0 * math.pi * ai / ntheta
            wobble = 1.0 + 0.045 * math.sin(3.0 * a + phase1) + 0.025 * math.cos(5.0 * a + phase2)
            lean_x = tube["lean_dx"] * t
            lean_y = tube["lean_dy"] * t
            ox = rx * taper * flare * wobble * math.cos(a)
            oy = ry * taper * flare * wobble * math.sin(a)
            irx = max(1.2, rx * taper * flare * top_roll - wall)
            iry = max(1.2, ry * taper * flare * top_roll - wall)
            ix = irx * (1.0 + 0.025 * math.sin(3.0 * a + phase1)) * math.cos(a)
            iy = iry * (1.0 + 0.025 * math.cos(4.0 * a + phase2)) * math.sin(a)
            ow = local_to_world(cx, cy, angle, ox, oy, z)
            iw = local_to_world(cx, cy, angle, ix, iy, z)
            outer_ring.append((ow[0] + lean_x, ow[1] + lean_y, ow[2]))
            inner_ring.append((iw[0] + lean_x, iw[1] + lean_y, iw[2]))
        outer.append(outer_ring)
        inner.append(inner_ring)

    for zi in range(nz):
        for ai in range(ntheta):
            an = (ai + 1) % ntheta
            mesh.add_quad(outer[zi][ai], outer[zi + 1][ai], outer[zi + 1][an], outer[zi][an])
            mesh.add_quad(inner[zi][an], inner[zi + 1][an], inner[zi + 1][ai], inner[zi][ai])

    for ai in range(ntheta):
        an = (ai + 1) % ntheta
        mesh.add_quad(outer[nz][ai], outer[nz][an], inner[nz][an], inner[nz][ai])
        mesh.add_quad(outer[0][an], outer[0][ai], inner[0][ai], inner[0][an])


def tube_color(x, y, rng):
    nx = x / TILE
    ny = y / TILE
    white_score = (
        math.exp(-(((nx - 0.18) / 0.18) ** 2 + ((ny - 0.78) / 0.16) ** 2))
        + math.exp(-(((nx - 0.82) / 0.17) ** 2 + ((ny - 0.22) / 0.17) ** 2))
        + 0.65 * math.exp(-(((nx - 0.84) / 0.15) ** 2 + ((ny - 0.82) / 0.15) ** 2))
    )
    orange_score = (
        math.exp(-(((nx - 0.52) / 0.28) ** 2 + ((ny - 0.54) / 0.33) ** 2))
        + 0.55 * math.exp(-(((nx - 0.28) / 0.20) ** 2 + ((ny - 0.30) / 0.20) ** 2))
    )
    if white_score > 0.58 + rng.random() * 0.35:
        return "white"
    if orange_score > 0.52 + rng.random() * 0.33:
        return "orange"
    return "beige"


def periodic_delta(a, b):
    d = abs(a - b)
    return min(d, TILE - d)


def tube_collision_radius(rx, ry, lean=1.0):
    # A near-touch spacing envelope: wide enough to keep bases separate, tight enough
    # to make the field read as packed coral.
    return max(rx, ry) * tube_outer_scale(1.0) + abs(lean) + TUBE_CLEARANCE


def tube_base_margin(rx, ry):
    return max(rx, ry) * 1.05 + 0.25


def base_fits_on_tile(x, y, rx, ry):
    margin = tube_base_margin(rx, ry)
    return margin <= x <= TILE - margin and margin <= y <= TILE - margin


def growth_vector(x, y, rng):
    edge_band = 22.0
    dx = 0.0
    dy = 0.0
    if x < edge_band:
        dx -= (edge_band - x) / edge_band
    elif x > TILE - edge_band:
        dx += (x - (TILE - edge_band)) / edge_band
    if y < edge_band:
        dy -= (edge_band - y) / edge_band
    elif y > TILE - edge_band:
        dy += (y - (TILE - edge_band)) / edge_band

    if abs(dx) + abs(dy) > 0:
        length = math.hypot(dx, dy)
        dx /= length
        dy /= length
        mag = rng.uniform(1.8, 4.6)
        dx = dx * mag + rng.uniform(-1.0, 1.0)
        dy = dy * mag + rng.uniform(-1.0, 1.0)
    else:
        angle = rng.uniform(0, 2.0 * math.pi)
        mag = rng.uniform(0.0, 1.8)
        dx = math.cos(angle) * mag
        dy = math.sin(angle) * mag
    return dx, dy


def candidate_overlaps_existing(candidate, tubes):
    cr = candidate["collision_radius"]
    for tube in tubes:
        dx = periodic_delta(candidate["x"], tube["x"])
        dy = periodic_delta(candidate["y"], tube["y"])
        if math.hypot(dx, dy) < cr + tube["collision_radius"]:
            if tubes_overlap(candidate, tube):
                return True
    return False


def ellipse_polygon(tube, level, shift_x=0.0, shift_y=0.0):
    scale = tube_outer_scale(level)
    cx = tube["x"] + tube["lean_dx"] * level + shift_x
    cy = tube["y"] + tube["lean_dy"] * level + shift_y
    rx = tube["rx"] * scale + TUBE_CLEARANCE
    ry = tube["ry"] * scale + TUBE_CLEARANCE
    ca = math.cos(tube["angle"])
    sa = math.sin(tube["angle"])
    pts = []
    for i in range(PROFILE_SEGMENTS):
        a = 2.0 * math.pi * i / PROFILE_SEGMENTS
        lx = rx * math.cos(a)
        ly = ry * math.sin(a)
        pts.append((cx + ca * lx - sa * ly, cy + sa * lx + ca * ly))
    return pts


def project_polygon(poly, axis):
    vals = [p[0] * axis[0] + p[1] * axis[1] for p in poly]
    return min(vals), max(vals)


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
            amin, amax = project_polygon(poly_a, axis)
            bmin, bmax = project_polygon(poly_b, axis)
            if amax <= bmin or bmax <= amin:
                return False
    return True


def tubes_overlap(a, b):
    for level in PROFILE_LEVELS:
        poly_a = ellipse_polygon(a, level)
        for sx in (-TILE, 0.0, TILE):
            for sy in (-TILE, 0.0, TILE):
                poly_b = ellipse_polygon(b, level, sx, sy)
                if polygons_overlap(poly_a, poly_b):
                    return True
    return False


def generate_tubes():
    rng = random.Random(SEED)
    tubes = []
    cols = 16
    rows = 16
    sx = TILE / cols
    sy = TILE / rows

    for row in range(rows):
        for col in range(cols):
            base_x = (col + (0.5 if row % 2 else 0.0)) * sx
            base_y = row * sy
            rx = rng.uniform(2.5, 4.0)
            ry = rng.uniform(2.4, 3.9)
            if rng.random() < 0.16:
                rx *= rng.uniform(1.10, 1.22)
                ry *= rng.uniform(1.08, 1.18)
            margin = tube_base_margin(rx, ry)
            x = min(max(base_x + rng.uniform(-3.4, 3.4), margin), TILE - margin)
            y = min(max(base_y + rng.uniform(-3.4, 3.4), margin), TILE - margin)
            if not base_fits_on_tile(x, y, rx, ry):
                continue
            lean_dx, lean_dy = growth_vector(x, y, rng)
            lean_mag = math.hypot(lean_dx, lean_dy)
            cx = (x - TILE / 2.0) / (TILE / 2.0)
            cy = (y - TILE / 2.0) / (TILE / 2.0)
            center_bias = max(0.0, 1.0 - math.hypot(cx, cy))
            height = rng.uniform(15.0, 27.0) * (0.82 + 0.25 * center_bias)
            height = min(TUBE_MAX_HEIGHT, height)
            color = tube_color(x, y, rng)
            if color == "white":
                height *= rng.uniform(0.72, 0.88)
            elif color == "orange":
                height *= rng.uniform(0.95, 1.08)
            candidate = {
                "x": x,
                "y": y,
                "rx": rx,
                "ry": ry,
                "wall": rng.uniform(0.85, 1.30),
                "height": min(TUBE_MAX_HEIGHT, height),
                "angle": rng.uniform(0, math.pi),
                "phase1": rng.uniform(0, 2 * math.pi),
                "phase2": rng.uniform(0, 2 * math.pi),
                "lean_dx": lean_dx,
                "lean_dy": lean_dy,
                "color": color,
                "collision_radius": tube_collision_radius(rx, ry, lean_mag),
            }
            if not candidate_overlaps_existing(candidate, tubes):
                tubes.append(candidate)

    # Fill remaining gaps, including along the wrapped edges, without allowing overlaps.
    misses = 0
    while len(tubes) < 175 and misses < 18000:
        misses += 1
        x = rng.uniform(0.0, TILE)
        y = rng.uniform(0.0, TILE)
        rx = rng.uniform(2.1, 3.5)
        ry = rng.uniform(2.0, 3.4)
        if not base_fits_on_tile(x, y, rx, ry):
            continue
        lean_dx, lean_dy = growth_vector(x, y, rng)
        lean_mag = math.hypot(lean_dx, lean_dy)
        cx = (x - TILE / 2.0) / (TILE / 2.0)
        cy = (y - TILE / 2.0) / (TILE / 2.0)
        center_bias = max(0.0, 1.0 - math.hypot(cx, cy))
        height = rng.uniform(13.0, 23.0) * (0.82 + 0.22 * center_bias)
        color = tube_color(x, y, rng)
        if color == "white":
            height *= rng.uniform(0.72, 0.88)
        elif color == "orange":
            height *= rng.uniform(0.95, 1.08)
        candidate = {
            "x": x,
            "y": y,
            "rx": rx,
            "ry": ry,
            "wall": rng.uniform(0.80, 1.20),
            "height": min(TUBE_MAX_HEIGHT, height),
            "angle": rng.uniform(0, math.pi),
            "phase1": rng.uniform(0, 2 * math.pi),
            "phase2": rng.uniform(0, 2 * math.pi),
            "lean_dx": lean_dx,
            "lean_dy": lean_dy,
            "color": color,
            "collision_radius": tube_collision_radius(rx, ry, lean_mag),
        }
        if not candidate_overlaps_existing(candidate, tubes):
            tubes.append(candidate)
            misses = 0

    tallest = max(t["height"] for t in tubes)
    target = TUBE_MAX_HEIGHT * 0.99
    if tallest > 0:
        factor = target / tallest
        for tube in tubes:
            tube["height"] = min(TUBE_MAX_HEIGHT, tube["height"] * factor)
    return tubes


def add_connector_stud(mesh, cx, cy):
    s = STUD_SIZE / 2.0
    z0 = BRIDGE_THICKNESS
    z1 = BRIDGE_THICKNESS + STUD_HEIGHT
    add_box(mesh, cx - s, cx + s, cy - s, cy + s, z0, z1)
    rib = 0.45
    add_box(mesh, cx - s - rib, cx + s + rib, cy - 1.05, cy + 1.05, z0 + STUD_HEIGHT * 0.58, z1 - 0.35)


def make_straight_connector():
    mesh = Mesh()
    half_spacing = SOCKET_INSET
    add_box(mesh, -half_spacing - 10.5, half_spacing + 10.5, -7.0, 7.0, 0.0, BRIDGE_THICKNESS)
    add_connector_stud(mesh, -half_spacing, 0.0)
    add_connector_stud(mesh, half_spacing, 0.0)
    return mesh


def make_corner_connector():
    mesh = Mesh()
    centers = [(-SOCKET_INSET, -SOCKET_INSET), (SOCKET_INSET, -SOCKET_INSET), (-SOCKET_INSET, SOCKET_INSET), (SOCKET_INSET, SOCKET_INSET)]
    add_box(mesh, -SOCKET_INSET - 10.5, SOCKET_INSET + 10.5, -SOCKET_INSET - 10.5, SOCKET_INSET + 10.5, 0.0, BRIDGE_THICKNESS)
    for cx, cy in centers:
        add_connector_stud(mesh, cx, cy)
    return mesh


def write_svg_preview(path, tubes):
    palette = {"white": "#f7f3e8", "beige": "#d8b692", "orange": "#e8662e"}
    with open(path, "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 160.4 160.4" width="1200" height="1200">\n')
        f.write('<rect x="0" y="0" width="152.4" height="152.4" fill="#d8b692"/>\n')
        for t in sorted(tubes, key=lambda item: item["height"]):
            transform = 'translate(%.3f %.3f) rotate(%.3f)' % (t["x"] + t["lean_dx"], TILE - (t["y"] + t["lean_dy"]), -math.degrees(t["angle"]))
            top_scale = 1.78
            f.write('<g transform="%s">\n' % transform)
            f.write('<ellipse cx="0" cy="0" rx="%.3f" ry="%.3f" fill="%s" stroke="#4d352b" stroke-opacity="0.20" stroke-width="0.45"/>\n' % (t["rx"] * top_scale, t["ry"] * top_scale, palette[t["color"]]))
            f.write('<ellipse cx="0" cy="0" rx="%.3f" ry="%.3f" fill="#2f201a" fill-opacity="0.24"/>\n' % (max(1.0, t["rx"] * top_scale - t["wall"] * 1.3), max(1.0, t["ry"] * top_scale - t["wall"] * 1.3)))
            f.write("</g>\n")
        f.write("</svg>\n")


def write_tessellation_preview(path, tubes):
    palette = {"white": "#f7f3e8", "beige": "#d8b692", "orange": "#e8662e"}
    canvas = TILE * 3.0
    margin = 14.0
    top_scale = tube_outer_scale(1.0)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.3f %.3f %.3f %.3f" width="1600" height="1600">\n' % (-margin, -margin, canvas + 2 * margin, canvas + 2 * margin))
        f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#f1eadf"/>\n' % (-margin, -margin, canvas + 2 * margin, canvas + 2 * margin))
        for ty in range(3):
            for tx in range(3):
                x = tx * TILE
                y = ty * TILE
                f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#d8b692" stroke="#6e5a48" stroke-width="0.45" stroke-opacity="0.55"/>\n' % (x, y, TILE, TILE))
        f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="none" stroke="#2e251f" stroke-width="1.25"/>\n' % (TILE, TILE, TILE, TILE))
        for ty in range(3):
            for tx in range(3):
                ox = tx * TILE
                oy = ty * TILE
                for t in sorted(tubes, key=lambda item: item["height"]):
                    cx = ox + t["x"] + t["lean_dx"]
                    cy = oy + TILE - (t["y"] + t["lean_dy"])
                    transform = 'translate(%.3f %.3f) rotate(%.3f)' % (cx, cy, -math.degrees(t["angle"]))
                    f.write('<g transform="%s">\n' % transform)
                    f.write('<ellipse cx="0" cy="0" rx="%.3f" ry="%.3f" fill="%s" stroke="#4d352b" stroke-opacity="0.18" stroke-width="0.38"/>\n' % (t["rx"] * top_scale, t["ry"] * top_scale, palette[t["color"]]))
                    f.write('<ellipse cx="0" cy="0" rx="%.3f" ry="%.3f" fill="#2f201a" fill-opacity="0.22"/>\n' % (max(1.0, t["rx"] * top_scale - t["wall"] * 1.3), max(1.0, t["ry"] * top_scale - t["wall"] * 1.3)))
                    f.write("</g>\n")
        f.write("</svg>\n")


def write_png_for_svg(svg_path, width=2400):
    converter = shutil.which("rsvg-convert")
    if not converter:
        print("Skipping PNG preview; rsvg-convert was not found")
        return
    png_path = os.path.splitext(svg_path)[0] + ".png"
    subprocess.run([converter, "-w", str(width), svg_path, "-o", png_path], check=True)


def write_readme(path, tubes):
    counts = {name: sum(1 for t in tubes if t["color"] == name) for name in ("white", "beige", "orange")}
    with open(path, "w", encoding="utf-8") as f:
        f.write("6 inch tessellating smooth tube coral tile\n")
        f.write("==========================================\n\n")
        f.write("Dimensions: 152.4 mm x 152.4 mm base tile, 6.35 mm base, 38.1 mm max height.\n")
        f.write("Tube bases are constrained to the plate; only the upper growth leans/flares past edges.\n")
        f.write("Some upper tube geometry intentionally overhangs the base edges so repeated tiles do not leave an empty border.\n")
        f.write("This version uses crowded flared tube tops to hide most of the plate in top view.\n")
        f.write("The underside has eight 10.2 mm square blind ports, 4.3 mm deep.\n")
        f.write("Use the straight connector under side-by-side seams and the corner connector where four tiles meet.\n\n")
        f.write("Color/STL handling: STL does not reliably store color. Import the three tile color STLs together without moving them, then assign white, beige, and orange materials.\n\n")
        f.write("Files:\n")
        f.write("- tube_tile_6in_white.stl: %d white tubes\n" % counts["white"])
        f.write("- tube_tile_6in_beige.stl: beige base plus %d beige tubes\n" % counts["beige"])
        f.write("- tube_tile_6in_orange.stl: %d orange tubes\n" % counts["orange"])
        f.write("- tube_tile_6in_combined_reference.stl: all tile geometry merged for preview\n")
        f.write("- tube_tile_straight_snap_connector.stl: two-stud seam connector\n")
        f.write("- tube_tile_corner_snap_connector.stl: four-stud corner connector\n")
        f.write("- tube_tile_6in_tessellation_preview.svg: 3x3 repeated top-view layout\n")
        f.write("\nConnector fit note: studs are 9.55 mm for 10.2 mm ports, with a small retention rib. Scale connectors down 1-2% if your printer runs tight.\n")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tubes = generate_tubes()
    meshes = {"white": Mesh(), "beige": Mesh(), "orange": Mesh()}
    add_base_with_bottom_ports(meshes["beige"])
    for tube in tubes:
        add_tube(meshes[tube["color"]], tube)

    combined = Mesh()
    for mesh in meshes.values():
        combined.extend(mesh)

    names = {
        "white": "tube_tile_6in_white.stl",
        "beige": "tube_tile_6in_beige.stl",
        "orange": "tube_tile_6in_orange.stl",
    }
    for color, filename in names.items():
        meshes[color].write_ascii_stl(os.path.join(OUT_DIR, filename), "tube_tile_6in_" + color)
    combined.write_ascii_stl(os.path.join(OUT_DIR, "tube_tile_6in_combined_reference.stl"), "tube_tile_6in_combined_reference")
    make_straight_connector().write_ascii_stl(os.path.join(OUT_DIR, "tube_tile_straight_snap_connector.stl"), "tube_tile_straight_snap_connector")
    make_corner_connector().write_ascii_stl(os.path.join(OUT_DIR, "tube_tile_corner_snap_connector.stl"), "tube_tile_corner_snap_connector")
    top_svg = os.path.join(OUT_DIR, "tube_tile_6in_top_preview.svg")
    tess_svg = os.path.join(OUT_DIR, "tube_tile_6in_tessellation_preview.svg")
    write_svg_preview(top_svg, tubes)
    write_tessellation_preview(tess_svg, tubes)
    write_png_for_svg(top_svg)
    write_png_for_svg(tess_svg)
    write_readme(os.path.join(OUT_DIR, "tube_tile_6in_README.txt"), tubes)
    print("Generated %d smooth tube cells" % len(tubes))
    for color in ("white", "beige", "orange"):
        print("%s triangles: %d" % (color, len(meshes[color].tris)))
    print("combined triangles: %d" % len(combined.tris))


if __name__ == "__main__":
    main()
