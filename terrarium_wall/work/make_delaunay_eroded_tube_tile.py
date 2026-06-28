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

GRID = 9
JITTER = 0.34
MIN_AREA = 55.0
MAX_AREA = 720.0
BASE_SCALE = 0.44
TOP_SCALE = 0.96
WALL = 1.05
NZ = 8
POST_WIDTH = 18.0
POST_INSIDE_CHAMFER = 8.0
BASE_MARGIN = 0.35


def dist2(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


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


def jittered_periodic_points():
    rng = random.Random(SEED)
    spacing = TILE / GRID
    central = []
    for iy in range(GRID):
        for ix in range(GRID):
            x = (ix + 0.5 + rng.uniform(-JITTER, JITTER)) * spacing
            y = (iy + 0.5 + rng.uniform(-JITTER, JITTER)) * spacing
            central.append((x % TILE, y % TILE))

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


def eroded_loop(tri, centroid, scale):
    pts = [(centroid[0] + (p[0] - centroid[0]) * scale, centroid[1] + (p[1] - centroid[1]) * scale) for p in tri]
    if signed_area(pts) < 0:
        pts.reverse()
    return chaikin(pts, 4)


def loop_radius(loop, centroid):
    return sum(math.hypot(p[0] - centroid[0], p[1] - centroid[1]) for p in loop) / len(loop)


def loop_bounds(loop):
    xs = [p[0] for p in loop]
    ys = [p[1] for p in loop]
    return min(xs), max(xs), min(ys), max(ys)


def offset_loop(loop, dx, dy):
    return [(p[0] + dx, p[1] + dy) for p in loop]


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
        return "white"
    if pick < 0.58:
        return "orange"
    return "beige"


def make_cells():
    rng = random.Random(SEED + 9)
    points = jittered_periodic_points()
    tris = delaunay(points)
    cells = []
    seen = set()
    for tri_ids in tris:
        tri = [points[i] for i in tri_ids]
        area = triangle_area(tri)
        if area < MIN_AREA or area > MAX_AREA:
            continue
        cx = sum(p[0] for p in tri) / 3.0
        cy = sum(p[1] for p in tri) / 3.0
        if not (0.0 <= cx < TILE and 0.0 <= cy < TILE):
            continue
        key = (round(cx, 3), round(cy, 3))
        if key in seen:
            continue
        seen.add(key)
        centroid = (cx, cy)
        base_loop, base_shift = fit_loop_inside_tile(eroded_loop(tri, centroid, BASE_SCALE))
        if base_loop is None:
            continue
        top_loop = eroded_loop(tri, centroid, TOP_SCALE)
        base_center = (centroid[0] + base_shift[0], centroid[1] + base_shift[1])
        radius = loop_radius(top_loop, centroid)
        height = min(TUBE_MAX_HEIGHT * 0.99, rng.uniform(14.0, 27.5) * (0.82 + min(1.0, radius / 16.0) * 0.28))
        color = color_for_cell(cx % TILE, cy % TILE, rng)
        cells.append(
            {
                "tri": tri,
                "centroid": centroid,
                "base_center": base_center,
                "base_loop": base_loop,
                "top_loop": top_loop,
                "height": min(TUBE_MAX_HEIGHT * 0.99, height),
                "color": color,
            }
        )
    return cells


def scaled_loop(loop, centroid, factor):
    return [(centroid[0] + (p[0] - centroid[0]) * factor, centroid[1] + (p[1] - centroid[1]) * factor) for p in loop]


def add_eroded_triangle_tube(mesh, cell):
    centroid = cell["centroid"]
    base_center = cell["base_center"]
    height = cell["height"]
    outer = []
    inner = []
    for zi in range(NZ + 1):
        t = zi / NZ
        mix = base.smoothstep(0.0, 1.0, t)
        loop = lerp_loop(cell["base_loop"], cell["top_loop"], mix)
        center = lerp_point(base_center, centroid, mix)
        radius = max(1.0, loop_radius(loop, center))
        inner_factor = max(0.18, (radius - WALL) / radius)
        inner_loop = scaled_loop(loop, center, inner_factor)
        z = BASE + height * t
        outer.append([(p[0], p[1], z) for p in loop])
        inner.append([(p[0], p[1], z) for p in inner_loop])

    n = len(outer[0])
    for zi in range(NZ):
        for i in range(n):
            j = (i + 1) % n
            mesh.add_quad(outer[zi][i], outer[zi + 1][i], outer[zi + 1][j], outer[zi][j])
            mesh.add_quad(inner[zi][j], inner[zi + 1][j], inner[zi + 1][i], inner[zi][i])
    for i in range(n):
        j = (i + 1) % n
        mesh.add_quad(outer[NZ][i], outer[NZ][j], inner[NZ][j], inner[NZ][i])
        mesh.add_quad(outer[0][j], outer[0][i], inner[0][i], inner[0][j])


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


def coverage_estimate(cells, samples=25000):
    rng = random.Random(42)
    top_loops = [c["top_loop"] for c in cells]
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
    palette = {"white": "#f7f3e8", "beige": "#d8b692", "orange": "#e8662e"}
    tiles = 3 if tiled else 1
    margin = 12.0
    span = TILE * tiles
    with open(path, "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.3f %.3f %.3f %.3f" width="1600" height="1600">\n' % (-margin, -margin, span + margin * 2, span + margin * 2))
        f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#f1eadf"/>\n' % (-margin, -margin, span + margin * 2, span + margin * 2))
        for ty in range(tiles):
            for tx in range(tiles):
                f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#d8b692" stroke="#6e5a48" stroke-width="0.45" stroke-opacity="0.55"/>\n' % (tx * TILE, ty * TILE, TILE, TILE))
        if tiled:
            f.write('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="none" stroke="#2e251f" stroke-width="1.25"/>\n' % (TILE, TILE, TILE, TILE))
        for ty in range(tiles):
            for tx in range(tiles):
                for c in sorted(cells, key=lambda item: item["height"]):
                    loop = c["top_loop"]
                    inner = scaled_loop(loop, c["centroid"], max(0.2, (loop_radius(loop, c["centroid"]) - WALL) / max(1.0, loop_radius(loop, c["centroid"]))))
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
    x1 = x0 + base.STUD_HEIGHT
    base.add_box(mesh, x0, x1, y0 - s, y0 + s, z0 - s, z0 + s)
    rib = 0.45
    base.add_box(mesh, x0 + base.STUD_HEIGHT * 0.45, x1 - 0.25, y0 - s - rib, y0 + s + rib, z0 - 1.05, z0 + 1.05)


def add_face_stud_y(mesh, x0, y0, z0):
    s = base.STUD_SIZE / 2.0
    y1 = y0 + base.STUD_HEIGHT
    base.add_box(mesh, x0 - s, x0 + s, y0, y1, z0 - s, z0 + s)
    rib = 0.45
    base.add_box(mesh, x0 - 1.05, x0 + 1.05, y0 + base.STUD_HEIGHT * 0.45, y1 - 0.25, z0 - s - rib, z0 + s + rib)


def make_box_corner_post():
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
    add_extruded_polygon(mesh, body, 0.0, TILE)
    for z in base.SOCKET_POS:
        add_face_stud_x(mesh, half, 0.0, z)
        add_face_stud_y(mesh, 0.0, half, z)
    return mesh


def write_readme(path, cells, overlaps, coverage):
    counts = {name: sum(1 for c in cells if c["color"] == name) for name in ("white", "beige", "orange")}
    with open(path, "w", encoding="utf-8") as f:
        f.write("Delaunay eroded-boundary tube tile\n")
        f.write("==================================\n\n")
        f.write("Alternate procedural approach: jittered periodic point field, pure-Python Delaunay triangulation, then eroded/smoothed triangle boundaries form the tube lips.\n")
        f.write("Dimensions: 152.4 mm x 152.4 mm base tile, 6.35 mm base, 38.1 mm max height.\n")
        f.write("The physical plate is exactly the same width as the periodic Delaunay domain; edge cells use wider inward-shifted bases and lean outward to their original top loops.\n")
        f.write("Top loops stay inside eroded Delaunay triangles, so neighboring tube tops are separated by construction.\n")
        f.write("Color placement is randomized with fixed weighted probabilities, independent of tube height and geometry.\n")
        f.write("Audit: %d top-loop overlap pairs; estimated top coverage %.1f%%.\n\n" % (overlaps, coverage * 100.0))
        f.write("Files:\n")
        f.write("- delaunay_tile_6in_white.stl: %d white tubes\n" % counts["white"])
        f.write("- delaunay_tile_6in_beige.stl: beige base plus %d beige tubes\n" % counts["beige"])
        f.write("- delaunay_tile_6in_orange.stl: %d orange tubes\n" % counts["orange"])
        f.write("- delaunay_tile_6in_combined_reference.stl: all tile geometry merged\n")
        f.write("- delaunay_tile_6in_top_preview.svg: single-tile top view\n")
        f.write("- delaunay_tile_6in_tessellation_preview.svg: 3x3 repeated top view\n")
        f.write("- delaunay_tile_box_corner_post.stl: 6 inch tall post with connector studs on two adjacent sides and a 45 degree inside chamfer\n")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cells = make_cells()
    meshes = {"white": base.Mesh(), "beige": base.Mesh(), "orange": base.Mesh()}
    base.add_base_with_bottom_ports(meshes["beige"])
    for cell in cells:
        add_eroded_triangle_tube(meshes[cell["color"]], cell)

    combined = base.Mesh()
    for mesh in meshes.values():
        combined.extend(mesh)

    for color in ("white", "beige", "orange"):
        meshes[color].write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_6in_%s.stl" % color), "delaunay_tile_6in_" + color)
    combined.write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_6in_combined_reference.stl"), "delaunay_tile_6in_combined_reference")
    base.make_straight_connector().write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_straight_snap_connector.stl"), "delaunay_tile_straight_snap_connector")
    base.make_corner_connector().write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_corner_snap_connector.stl"), "delaunay_tile_corner_snap_connector")
    make_box_corner_post().write_ascii_stl(os.path.join(OUT_DIR, "delaunay_tile_box_corner_post.stl"), "delaunay_tile_box_corner_post")

    overlaps = overlap_audit(cells)
    coverage = coverage_estimate(cells)
    top_svg = os.path.join(OUT_DIR, "delaunay_tile_6in_top_preview.svg")
    tess_svg = os.path.join(OUT_DIR, "delaunay_tile_6in_tessellation_preview.svg")
    write_preview(top_svg, cells, tiled=False)
    write_preview(tess_svg, cells, tiled=True)
    write_png_for_svg(top_svg)
    write_png_for_svg(tess_svg)
    write_readme(os.path.join(OUT_DIR, "delaunay_tile_6in_README.txt"), cells, overlaps, coverage)
    print("Generated %d Delaunay eroded tube cells" % len(cells))
    print("top-loop overlap pairs: %d" % overlaps)
    print("estimated top coverage: %.1f%%" % (coverage * 100.0))
    for color in ("white", "beige", "orange"):
        print("%s triangles: %d" % (color, len(meshes[color].tris)))
    print("combined triangles: %d" % len(combined.tris))


if __name__ == "__main__":
    main()
