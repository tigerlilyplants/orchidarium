#!/usr/bin/env python3
import math
import os
import random
import shutil
import subprocess


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT_DIR, "outputs")
SIZE = 120.0
BASE_THICKNESS = 4.0
BASE_TOP = BASE_THICKNESS
SEED = 223607


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


def smoothstep(edge0, edge1, x):
    if x <= edge0:
        return 0.0
    if x >= edge1:
        return 1.0
    t = (x - edge0) / (edge1 - edge0)
    return t * t * (3.0 - 2.0 * t)


def tri_normal(a, b, c):
    return vnorm(vcross(vsub(b, a), vsub(c, a)))


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

    mesh.add_quad(p001, p101, p111, p011)  # top
    mesh.add_quad(p000, p010, p110, p100)  # bottom
    mesh.add_quad(p000, p100, p101, p001)
    mesh.add_quad(p100, p110, p111, p101)
    mesh.add_quad(p110, p010, p011, p111)
    mesh.add_quad(p010, p000, p001, p011)


def local_to_world(cx, cy, angle, lx, ly, z):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return (cx + ca * lx - sa * ly, cy + sa * lx + ca * ly, z)


def add_coral_cell(mesh, cell):
    cx, cy = cell["x"], cell["y"]
    a, b = cell["a"], cell["b"]
    angle = cell["angle"]
    height = cell["height"]
    ntheta = cell["segments"]
    nr = 10
    phase1 = cell["phase1"]
    phase2 = cell["phase2"]
    phase3 = cell["phase3"]
    skew = cell["skew"]

    top = []
    bottom = []
    for ri in range(nr + 1):
        r = ri / nr
        top_ring = []
        bottom_ring = []
        for ti in range(ntheta):
            t = 2.0 * math.pi * ti / ntheta
            organic = (
                1.0
                + 0.075 * math.sin(3.0 * t + phase1)
                + 0.045 * math.sin(5.0 * t + phase2)
                + 0.025 * math.cos(7.0 * t + phase3)
            )
            lx = a * r * organic * math.cos(t)
            ly = b * r * organic * math.sin(t)

            rim = math.exp(-((r - 0.70) / 0.185) ** 2)
            shoulder = 0.30 * math.exp(-((r - 0.48) / 0.34) ** 2)
            center_dip = 0.16 * math.exp(-(r / 0.33) ** 2)
            edge_fade = 1.0 - smoothstep(0.84, 1.0, r)
            uneven_lip = 1.0 + 0.055 * math.sin(2.0 * t + phase2) + 0.035 * math.cos(4.0 * t + phase1)
            profile = max(0.0, (0.20 + rim * uneven_lip + shoulder - center_dip) * edge_fade)
            z = BASE_TOP + height * profile

            # A tiny lateral lean keeps the field from reading as stamped petals.
            lean = skew * profile
            world = local_to_world(cx + lean * math.cos(angle + 1.3), cy + lean * math.sin(angle + 1.3), angle, lx, ly, z)
            top_ring.append(world)
            bottom_ring.append(local_to_world(cx, cy, angle, lx, ly, BASE_TOP))
        top.append(top_ring)
        bottom.append(bottom_ring)

    center_top = (cx, cy, BASE_TOP + height * 0.08)
    center_bottom = (cx, cy, BASE_TOP)
    for ti in range(ntheta):
        tn = (ti + 1) % ntheta
        mesh.add_tri(center_top, top[1][ti], top[1][tn])
        mesh.add_tri(center_bottom, bottom[1][tn], bottom[1][ti])

    for ri in range(1, nr):
        for ti in range(ntheta):
            tn = (ti + 1) % ntheta
            mesh.add_quad(top[ri][ti], top[ri + 1][ti], top[ri + 1][tn], top[ri][tn])
            mesh.add_quad(bottom[ri][tn], bottom[ri + 1][tn], bottom[ri + 1][ti], bottom[ri][ti])

    # A soft outer skirt closes the cell as a printable solid.
    for ti in range(ntheta):
        tn = (ti + 1) % ntheta
        mesh.add_quad(top[nr][ti], bottom[nr][ti], bottom[nr][tn], top[nr][tn])


def color_for_cell(x, y, radius, rng):
    nx = (x - SIZE / 2.0) / (SIZE / 2.0)
    ny = (y - SIZE / 2.0) / (SIZE / 2.0)
    corner_bias = max(abs(nx), abs(ny))
    white_islands = (
        math.exp(-(((x - 18) / 23) ** 2 + ((y - 103) / 19) ** 2))
        + math.exp(-(((x - 101) / 22) ** 2 + ((y - 21) / 18) ** 2))
        + 0.55 * math.exp(-(((x - 105) / 23) ** 2 + ((y - 96) / 22) ** 2))
        + 0.45 * math.exp(-(((x - 16) / 20) ** 2 + ((y - 15) / 20) ** 2))
    )
    orange_band = (
        math.exp(-(((x - 60) / 38) ** 2 + ((y - 54) / 54) ** 2))
        + 0.45 * math.exp(-(((x - 34) / 25) ** 2 + ((y - 47) / 25) ** 2))
        + 0.35 * math.exp(-(((x - 88) / 28) ** 2 + ((y - 69) / 25) ** 2))
    )
    if white_islands + (0.18 if corner_bias > 0.80 else 0.0) > 0.72 + rng.random() * 0.45:
        return "white"
    if orange_band > 0.58 + rng.random() * 0.40 or radius > 7.4:
        return "orange"
    return "beige"


def generate_cells():
    rng = random.Random(SEED)
    cells = []
    attempts = 0
    while len(cells) < 118 and attempts < 9000:
        attempts += 1
        x = rng.uniform(7.0, SIZE - 7.0)
        y = rng.uniform(7.0, SIZE - 7.0)
        center_dist = math.hypot(x - SIZE / 2.0, y - SIZE / 2.0)
        size_boost = 1.0 + 0.42 * max(0.0, 1.0 - center_dist / 62.0)
        r = rng.uniform(4.2, 8.5) * size_boost
        if rng.random() < 0.16:
            r *= rng.uniform(1.12, 1.36)
        a = r * rng.uniform(0.80, 1.23)
        b = r * rng.uniform(0.72, 1.12)
        max_extent = max(a, b) * 1.16
        if x - max_extent < 1.0 or x + max_extent > SIZE - 1.0:
            continue
        if y - max_extent < 1.0 or y + max_extent > SIZE - 1.0:
            continue
        min_sep = 0.70 * (a + b) / 2.0
        ok = True
        for c in cells:
            sep = math.hypot(x - c["x"], y - c["y"])
            other = 0.70 * (c["a"] + c["b"]) / 2.0
            if sep < min_sep + other:
                ok = False
                break
        if not ok:
            continue
        color = color_for_cell(x, y, (a + b) / 2.0, rng)
        height = rng.uniform(6.0, 15.5) * (1.0 + 0.35 * max(0.0, 1.0 - center_dist / 66.0))
        if color == "white":
            height *= rng.uniform(0.70, 0.96)
        elif color == "beige":
            height *= rng.uniform(0.82, 1.05)
        else:
            height *= rng.uniform(0.95, 1.18)
        cells.append(
            {
                "x": x,
                "y": y,
                "a": a,
                "b": b,
                "angle": rng.uniform(0, math.pi),
                "height": min(height, 20.0),
                "segments": 34 if r > 7.0 else 28,
                "phase1": rng.uniform(0, 2 * math.pi),
                "phase2": rng.uniform(0, 2 * math.pi),
                "phase3": rng.uniform(0, 2 * math.pi),
                "skew": rng.uniform(-1.15, 1.15),
                "color": color,
            }
        )
    return cells


def write_readme(path, cells):
    counts = {name: sum(1 for c in cells if c["color"] == name) for name in ("white", "beige", "orange")}
    with open(path, "w", encoding="utf-8") as f:
        f.write("Smooth coral relief STL set\n")
        f.write("===========================\n\n")
        f.write("Generated from the provided surface reference as a stylized smooth-coral relief, not a direct scan.\n")
        f.write("The model is 120 mm x 120 mm, with a 4 mm beige base and raised smooth coral cups.\n\n")
        f.write("Color/STL handling:\n")
        f.write("- STL files do not reliably preserve color.\n")
        f.write("- Import the three color STLs together into your slicer without moving them.\n")
        f.write("- Assign filaments/materials: white, beige, and orange.\n")
        f.write("- smooth_coral_combined_reference.stl is included only as a one-piece preview/reference.\n\n")
        f.write("Files:\n")
        f.write("- smooth_coral_white.stl: %d white coral cells\n" % counts["white"])
        f.write("- smooth_coral_beige.stl: beige base plus %d beige coral cells\n" % counts["beige"])
        f.write("- smooth_coral_orange.stl: %d orange coral cells\n" % counts["orange"])
        f.write("- smooth_coral_combined_reference.stl: all geometry merged\n")


def write_svg_preview(path, cells):
    palette = {
        "white": "#f7f3e8",
        "beige": "#d9b895",
        "orange": "#e7652f",
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 128 128" width="1024" height="1024">\n')
        f.write('<rect x="0" y="0" width="120" height="120" fill="#d9b895"/>\n')
        ordered = sorted(cells, key=lambda c: c["height"])
        for c in ordered:
            rx = c["a"]
            ry = c["b"]
            fill = palette[c["color"]]
            transform = 'translate(%.3f %.3f) rotate(%.3f)' % (c["x"], 120.0 - c["y"], -math.degrees(c["angle"]))
            f.write('<g transform="%s">\n' % transform)
            f.write('<ellipse cx="0" cy="0" rx="%.3f" ry="%.3f" fill="%s" stroke="#5b3a2d" stroke-opacity="0.18" stroke-width="0.45"/>\n' % (rx, ry, fill))
            f.write('<ellipse cx="0" cy="0" rx="%.3f" ry="%.3f" fill="#3b241d" fill-opacity="0.16"/>\n' % (rx * 0.38, ry * 0.38))
            f.write("</g>\n")
        f.write("</svg>\n")


def write_png_for_svg(svg_path, width=2400):
    converter = shutil.which("rsvg-convert")
    if not converter:
        print("Skipping PNG preview; rsvg-convert was not found")
        return
    png_path = os.path.splitext(svg_path)[0] + ".png"
    subprocess.run([converter, "-w", str(width), svg_path, "-o", png_path], check=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cells = generate_cells()
    meshes = {"white": Mesh(), "beige": Mesh(), "orange": Mesh()}

    # The base belongs to the beige part so multicolor slicers get a stable foundation.
    add_box(meshes["beige"], 0.0, SIZE, 0.0, SIZE, 0.0, BASE_THICKNESS)

    for cell in cells:
        add_coral_cell(meshes[cell["color"]], cell)

    combined = Mesh()
    for mesh in meshes.values():
        combined.extend(mesh)

    outputs = {
        "white": "smooth_coral_white.stl",
        "beige": "smooth_coral_beige.stl",
        "orange": "smooth_coral_orange.stl",
    }
    for color, filename in outputs.items():
        meshes[color].write_ascii_stl(os.path.join(OUT_DIR, filename), f"smooth_coral_{color}")
    combined.write_ascii_stl(os.path.join(OUT_DIR, "smooth_coral_combined_reference.stl"), "smooth_coral_combined_reference")
    write_readme(os.path.join(OUT_DIR, "smooth_coral_README.txt"), cells)
    svg_path = os.path.join(OUT_DIR, "smooth_coral_top_preview.svg")
    write_svg_preview(svg_path, cells)
    write_png_for_svg(svg_path)
    print("Generated %d coral cells" % len(cells))
    for color in ("white", "beige", "orange"):
        print("%s: %d triangles" % (color, len(meshes[color].tris)))
    print("combined: %d triangles" % len(combined.tris))


if __name__ == "__main__":
    main()
