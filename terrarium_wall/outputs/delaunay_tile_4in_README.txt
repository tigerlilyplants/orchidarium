Delaunay eroded-boundary tube tile
==================================

Alternate procedural approach: periodic fixed-radius rejection-sampled point field, pure-Python Delaunay triangulation, then eroded/smoothed triangle boundaries form the tube lips.
Dimensions: 101.6 mm x 101.6 mm base tile, 6.35 mm base, 38.1 mm max height.
The physical plate is exactly the same width as the periodic Delaunay domain; edge tube interiors may lean outward while their exterior bases stay on the plate.
All horns use a uniform 25.4 mm body height and stay inside their eroded Delaunay cell boundary, with no intentional overhang into neighboring cells.
Exterior cross-sections follow a smooth horn curve from smaller bases into Delaunay cell-boundary loops.
The tube body is built as a stack of increasing-height cross-sections. Each hollow section has an exterior loop and a 1.00 mm inward wall target, then each ring is stitched only to the ring directly below it.
Small bases are kept as solid stems until the horn cross-section is wide enough to support a hollow wall; a few small horns may remain capped solid.
Tube feet have a short solid vertical collar before the horn flare begins; the colored foot penetrates 0.75 mm into the black base while the hollow opening starts above the plate surface to avoid tiny base slots.
No tube cells are filtered out after triangulation; small cells are allowed to become solid or partially hollow horns.
Tube tops include a subtle uneven raised rim and lower inner edge, so the lip has an organic beveled curve instead of a flat cut.
Bambu Studio material mapping: color 1 = black base, color 2 = white tubes, color 3 = beige tubes, color 4 = orange tubes.
Color placement for tube colors 2-4 is randomized with fixed weighted probabilities, independent of tube height and geometry.
Audit: 0 base footprint overlaps; 0.98 mm minimum hollow wall; 0 sampled mid-body overlaps; 0 top-overhang pairs; estimated top coverage 72.9%.

Files:
- delaunay_tile_4in_color_1_black.stl: black base
- delaunay_tile_4in_color_2_white.stl: 39 white tubes
- delaunay_tile_4in_color_3_beige.stl: 58 beige tubes
- delaunay_tile_4in_color_4_orange.stl: 65 orange tubes
- delaunay_tile_4in_combined_reference.stl: all tile geometry merged
- delaunay_tile_4in_top_preview.svg: single-tile top view
- delaunay_tile_4in_tessellation_preview.svg: 3x3 repeated top view
- delaunay_tile_box_corner_post.stl: 101.6 mm tall post with connector studs on two adjacent sides and a 45 degree inside chamfer
