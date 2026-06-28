Delaunay eroded-boundary tube tile
==================================

Alternate procedural approach: jittered periodic point field, pure-Python Delaunay triangulation, then eroded/smoothed triangle boundaries form the tube lips.
Dimensions: 101.6 mm x 101.6 mm base tile, 6.35 mm base, 38.1 mm max height.
The physical plate is exactly the same width as the periodic Delaunay domain; edge cells use wider inward-shifted bases and lean outward to their original top loops.
Top loops expand past the eroded Delaunay boundaries for a denser packed canopy; taller tubes may overhang shorter neighbors.
The tube body uses a horn-flare curve: wider bases, slower lower growth, then a later outward flare near the top.
Tube tops include a subtle uneven raised rim and lower inner edge, so the lip has an organic beveled curve instead of a flat cut.
Bambu Studio material mapping: color 1 = black base, color 2 = white tubes, color 3 = beige tubes, color 4 = orange tubes.
Color placement for tube colors 2-4 is randomized with fixed weighted probabilities, independent of tube height and geometry.
Audit: 243 allowed top-overhang pairs; estimated top coverage 79.1%.

Files:
- delaunay_tile_4in_color_1_black.stl: black base
- delaunay_tile_4in_color_2_white.stl: 44 white tubes
- delaunay_tile_4in_color_3_beige.stl: 63 beige tubes
- delaunay_tile_4in_color_4_orange.stl: 55 orange tubes
- delaunay_tile_4in_combined_reference.stl: all tile geometry merged
- delaunay_tile_4in_top_preview.svg: single-tile top view
- delaunay_tile_4in_tessellation_preview.svg: 3x3 repeated top view
- delaunay_tile_box_corner_post.stl: 101.6 mm tall post with connector studs on two adjacent sides and a 45 degree inside chamfer
