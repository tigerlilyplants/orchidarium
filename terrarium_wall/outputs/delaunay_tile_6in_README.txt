Delaunay eroded-boundary tube tile
==================================

Alternate procedural approach: jittered periodic point field, pure-Python Delaunay triangulation, then eroded/smoothed triangle boundaries form the tube lips.
Dimensions: 152.4 mm x 152.4 mm base tile, 6.35 mm base, 38.1 mm max height.
The physical plate is exactly the same width as the periodic Delaunay domain; edge cells use wider inward-shifted bases and lean outward to their original top loops.
Top loops stay inside eroded Delaunay triangles, so neighboring tube tops are separated by construction.
Color placement is randomized with fixed weighted probabilities, independent of tube height and geometry.
Audit: 0 top-loop overlap pairs; estimated top coverage 65.1%.

Files:
- delaunay_tile_6in_white.stl: 35 white tubes
- delaunay_tile_6in_beige.stl: beige base plus 62 beige tubes
- delaunay_tile_6in_orange.stl: 62 orange tubes
- delaunay_tile_6in_combined_reference.stl: all tile geometry merged
- delaunay_tile_6in_top_preview.svg: single-tile top view
- delaunay_tile_6in_tessellation_preview.svg: 3x3 repeated top view
- delaunay_tile_box_corner_post.stl: 6 inch tall post with connector studs on two adjacent sides and a 45 degree inside chamfer
