#!/usr/bin/env python3
import os
import random

import make_delaunay_eroded_tube_tile as tile
import make_tessellating_tube_tile as base


LOW_SOCKET_DEPTH = 3.60
LOW_STUD_HEIGHT = 3.30
LOW_BASE_ROOF = 0.65
LOW_BASE = LOW_SOCKET_DEPTH + LOW_BASE_ROOF
LOW_PROFILE_START_T = 0.72
LOW_TUBE_EMBED = 0.05
LOW_TUBE_HEIGHT = tile.UNIFORM_TUBE_HEIGHT * (1.0 - LOW_PROFILE_START_T)
LOW_POINT_COUNT = 56
LOW_POINT_REJECTION_RADIUS = 7.8
LOW_FOOT_TO_TOP_SCALE = 0.35
LOW_TOP_SCALE = 1.00
LOW_HEIGHT_STAGGER = 0.08
PREFIX = "delaunay_tile_4in_low_profile"


def low_source_t(t):
    return LOW_PROFILE_START_T + (1.0 - LOW_PROFILE_START_T) * t


def low_outer_loop_at_t(cell, t):
    foot_loop = cell.get("low_foot_loop")
    top_loop = cell.get("low_top_loop")
    if foot_loop is None or top_loop is None:
        return tile.section_outer_loop(cell, low_source_t(t))
    u = base.smoothstep(0.0, 1.0, t)
    flare = 0.18 * u + 0.82 * u * u
    return tile.lerp_loop(foot_loop, top_loop, flare)


def low_build_tube_sections(cell):
    height = cell["height"]
    sections = []
    open_started = False
    last_inner_loop = None
    for zi in range(tile.NZ + 1):
        t = zi / tile.NZ
        source_t = low_source_t(t)
        outer_loop = low_outer_loop_at_t(cell, t)
        inner_loop = None
        if t >= tile.INNER_OPEN_START:
            inner_loop = tile.inner_loop_from_outer(outer_loop)
            if inner_loop is None and open_started:
                inner_loop = last_inner_loop
            if inner_loop is not None:
                open_started = True
                last_inner_loop = inner_loop

        z = tile.BASE - tile.TUBE_BASE_EMBED + (height + tile.TUBE_BASE_EMBED) * t
        rim = base.smoothstep(0.66, 1.0, source_t)
        count = len(outer_loop)
        outer_ring = []
        for i, p in enumerate(outer_loop):
            lift = rim * (tile.RIM_LIFT + tile.rim_wave(cell, i, count))
            outer_ring.append((p[0], p[1], z + lift))

        inner_ring = None
        if inner_loop is not None:
            inner_ring = []
            for i, p in enumerate(inner_loop):
                lift = rim * (tile.RIM_LIFT - tile.RIM_INNER_DROP + tile.rim_wave(cell, i, count) * 0.45)
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


def configure_low_profile():
    base.SOCKET_DEPTH = LOW_SOCKET_DEPTH
    base.STUD_HEIGHT = LOW_STUD_HEIGHT
    base.BASE = LOW_BASE
    base.MAX_Z = LOW_BASE + LOW_TUBE_HEIGHT * (1.0 + LOW_HEIGHT_STAGGER) + tile.MAX_RIM_EXTRA
    base.TUBE_MAX_HEIGHT = base.MAX_Z - base.BASE

    tile.BASE = LOW_BASE
    tile.TUBE_MAX_HEIGHT = base.TUBE_MAX_HEIGHT
    tile.BODY_MAX_HEIGHT = base.TUBE_MAX_HEIGHT - tile.MAX_RIM_EXTRA
    tile.UNIFORM_TUBE_HEIGHT = LOW_TUBE_HEIGHT
    tile.TUBE_BASE_EMBED = LOW_TUBE_EMBED
    tile.POINT_COUNT = LOW_POINT_COUNT
    tile.POINT_REJECTION_RADIUS = LOW_POINT_REJECTION_RADIUS
    tile.build_tube_sections = low_build_tube_sections
    tile.outer_loop_at_t = low_outer_loop_at_t


def write_low_profile_readme(path, cells, overlaps, body_overlaps, base_overlaps, min_wall, coverage):
    counts = {number: sum(1 for c in cells if c["color"] == number) for number in (2, 3, 4)}
    with open(path, "w", encoding="utf-8") as f:
        f.write("Delaunay eroded-boundary low-profile tube tile\n")
        f.write("==============================================\n\n")
        f.write("This is a separate low-profile variant of the 4 inch Delaunay tube tile.\n")
        f.write("Base height: %.2f mm, using %.2f mm socket depth plus %.2f mm roof.\n" % (LOW_BASE, LOW_SOCKET_DEPTH, LOW_BASE_ROOF))
        f.write("Low-profile connectors use %.2f mm socket depth and %.2f mm stud tabs.\n" % (LOW_SOCKET_DEPTH, LOW_STUD_HEIGHT))
        f.write("Point field: %d rejection-sampled seeds at %.1f mm minimum spacing, producing larger petal cells than the normal tile.\n" % (LOW_POINT_COUNT, LOW_POINT_REJECTION_RADIUS))
        f.write("Tube geometry keeps the upper %.0f%% of the normal horn curve and removes most of the spindly lower stems.\n" % ((1.0 - LOW_PROFILE_START_T) * 100.0))
        f.write("Tube body height: %.2f mm with %.0f%% stagger; tube/base embed: %.2f mm.\n" % (LOW_TUBE_HEIGHT, LOW_HEIGHT_STAGGER * 100.0, LOW_TUBE_EMBED))
        f.write("Petal flare uses a top scale of %.2f and foot-to-top scale of %.2f, producing roughly %.1fx linear flare.\n" % (LOW_TOP_SCALE, LOW_FOOT_TO_TOP_SCALE, 1.0 / LOW_FOOT_TO_TOP_SCALE))
        f.write("Bambu Studio material mapping: color 1 = black base, color 2 = white tubes, color 3 = beige tubes, color 4 = orange tubes.\n")
        f.write("Audit: %d base footprint overlaps; %.2f mm minimum hollow wall; %d sampled mid-body overlaps; %d top-overhang pairs; estimated top coverage %.1f%%.\n\n" % (base_overlaps, min_wall, body_overlaps, overlaps, coverage * 100.0))
        f.write("Files:\n")
        f.write("- %s_color_1_black.stl: black low-profile base\n" % PREFIX)
        f.write("- %s_color_2_white.stl: %d white tube tops\n" % (PREFIX, counts[2]))
        f.write("- %s_color_3_beige.stl: %d beige tube tops\n" % (PREFIX, counts[3]))
        f.write("- %s_color_4_orange.stl: %d orange tube tops\n" % (PREFIX, counts[4]))
        f.write("- %s_combined_reference.stl: all low-profile tile geometry merged\n" % PREFIX)
        f.write("- %s_straight_snap_connector.stl: low-profile two-stud seam connector\n" % PREFIX)
        f.write("- %s_corner_snap_connector.stl: low-profile four-stud corner connector\n" % PREFIX)
        f.write("- %s_box_corner_post.stl: low-profile wall-corner post with longer side-facing plugs\n" % PREFIX)
        f.write("- %s_top_preview.svg: single-tile top view\n" % PREFIX)
        f.write("- %s_tessellation_preview.svg: 3x3 repeated top view\n" % PREFIX)


def main():
    configure_low_profile()
    os.makedirs(tile.OUT_DIR, exist_ok=True)
    cells = tile.make_cells()
    rng = random.Random(tile.SEED + 411)
    for cell in cells:
        center = tile.loop_center(cell["top_loop"])
        cell["low_top_loop"] = tile.scaled_loop(cell["top_loop"], center, LOW_TOP_SCALE)
        cell["low_foot_loop"] = tile.scaled_loop(cell["low_top_loop"], center, LOW_FOOT_TO_TOP_SCALE)
        cell["top_loop"] = cell["low_top_loop"]
        cell["base_loop"] = cell["low_foot_loop"]
        cell["base_center"] = tile.loop_center(cell["low_foot_loop"])
        cell["height"] = LOW_TUBE_HEIGHT * (1.0 + rng.uniform(-LOW_HEIGHT_STAGGER, LOW_HEIGHT_STAGGER))
    meshes = {1: base.Mesh(), 2: base.Mesh(), 3: base.Mesh(), 4: base.Mesh()}
    base.add_base_with_bottom_ports(meshes[1])
    for cell in cells:
        tile.add_eroded_triangle_tube(meshes[cell["color"]], cell)

    combined = base.Mesh()
    for mesh in meshes.values():
        combined.extend(mesh)

    color_files = {
        1: ("%s_color_1_black.stl" % PREFIX, "%s_color_1_black" % PREFIX),
        2: ("%s_color_2_white.stl" % PREFIX, "%s_color_2_white" % PREFIX),
        3: ("%s_color_3_beige.stl" % PREFIX, "%s_color_3_beige" % PREFIX),
        4: ("%s_color_4_orange.stl" % PREFIX, "%s_color_4_orange" % PREFIX),
    }
    for color_number, (filename, solid_name) in color_files.items():
        meshes[color_number].write_ascii_stl(os.path.join(tile.OUT_DIR, filename), solid_name)
    combined.write_ascii_stl(os.path.join(tile.OUT_DIR, "%s_combined_reference.stl" % PREFIX), "%s_combined_reference" % PREFIX)
    base.make_straight_connector().write_ascii_stl(os.path.join(tile.OUT_DIR, "%s_straight_snap_connector.stl" % PREFIX), "%s_straight_snap_connector" % PREFIX)
    base.make_corner_connector().write_ascii_stl(os.path.join(tile.OUT_DIR, "%s_corner_snap_connector.stl" % PREFIX), "%s_corner_snap_connector" % PREFIX)
    tile.make_box_corner_post().write_ascii_stl(os.path.join(tile.OUT_DIR, "%s_box_corner_post.stl" % PREFIX), "%s_box_corner_post" % PREFIX)

    overlaps = tile.overlap_audit(cells)
    body_overlaps = len(tile.body_overlap_pairs(cells))
    base_overlaps = tile.base_overlap_audit(cells)
    min_wall = tile.hollow_wall_audit(cells)
    coverage = tile.coverage_estimate(cells)
    top_svg = os.path.join(tile.OUT_DIR, "%s_top_preview.svg" % PREFIX)
    tess_svg = os.path.join(tile.OUT_DIR, "%s_tessellation_preview.svg" % PREFIX)
    tile.write_preview(top_svg, cells, tiled=False)
    tile.write_preview(tess_svg, cells, tiled=True)
    tile.write_png_for_svg(top_svg)
    tile.write_png_for_svg(tess_svg)
    write_low_profile_readme(os.path.join(tile.OUT_DIR, "%s_README.txt" % PREFIX), cells, overlaps, body_overlaps, base_overlaps, min_wall, coverage)

    print("Generated %d low-profile Delaunay eroded tube cells" % len(cells))
    print("low-profile base height: %.2f mm" % LOW_BASE)
    print("low-profile connector socket/stud: %.2f mm / %.2f mm" % (LOW_SOCKET_DEPTH, LOW_STUD_HEIGHT))
    print("low-profile point seeds: %d at %.1f mm minimum spacing" % (LOW_POINT_COUNT, LOW_POINT_REJECTION_RADIUS))
    print("low-profile tube body height: %.2f mm" % LOW_TUBE_HEIGHT)
    print("tube/base embed: %.2f mm" % LOW_TUBE_EMBED)
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
