# ST06 walls and wall plate

*SS-02's code is not in this repo; its file names (`ss02_*.py`) are from that job.*

Read when modelling walls, plaster, beads, openings or the wall plate.

## ผนังและอะเส (ST06, spec 29 ต.ค.; `examples/e42/scripts/e42_walls.py`, its own file — e42_struct was past 800 lines)

- **Ask the wall spec every house**: brick type and size, lintel product, tie columns. E42: 3-hole clay brick
  6 × 10 × 20 cm laid 6 cm thick, 1 cm joints → 1/(0.21 × 0.11) = 43.3 bricks/m² + 5 % breakage; walls from the
  slab top over the beams up to the wall plate (3.03 m).
- Lintels are prefab ladder reinforcement in the bed joints (SHP 4 mm × 30 m rolls), not concrete: over every
  opening and under every window, 20 cm past each jamb, plus one run at mid-height when the wall is over 3 m
  (skip it where a head/sill run is within one course). Count metres → rolls. Tie columns stay concrete + 2-RB6:
  beside every opening, at wall junctions without a column, panels ≤ 2.50 m, slivers < 0.20 m filled with concrete.
- **Exterior walls flush with the column face** so the plaster runs flat over column and wall (the user spotted the
  5 cm step when walls sat on the grid line): wall centreline = grid ± (column/2 − brick/2). A line that faces
  outside on part of its length (porch) goes flush too. Find junctions on the grid, build from the real centreline.
- Plaster: both wall faces (cut where another wall meets), opening reveals (wall-deep), and the columns: a skin
  round each column cut by the wall solids — works for flush and centred walls and a free-standing porch column.
- **Corner beads (จับเซี้ยม)**: every outside vertical corner of the plastered plan (quadrant test on the union of
  plan rects: exactly one quadrant inside) plus round every opening on both faces, at the real plaster corner
  (face plaster meets reveal plaster). The user asked where they were, then for the product modelled: E42 KASSA PVC
  angle bead 1 cm legs × 2 m → an L of two thin boxes, counted in 2 m pieces (a 3 m corner = 2 pieces). Ask the
  bead product every house. **Beads go on before the plaster** (the user caught them sitting on top of it): the L
  lies inside the plaster, nose on the corner, outer faces flush with the plaster faces; cut the plaster round it
  and store the cut volume as `void` on the plaster mesh, because plaster is bought by face area: area =
  (vol + void) / t. Check: Σ void = Σ bead volume (every bead fully inside plaster) and, read from the model since
  void is a build-time number, every bead leg still touches plaster; corners are found on plaster + beads (cut
  plaster alone shows false notch corners).
- Wall plate: one continuous run per grid line (collinear beam lines merged), centred on the column cap plates,
  at junctions one line runs through; runs longer than the 6 m stock are cut and welded — report the weld count.
  E42 changed to 2C (lipped C 100×50×20×2.3 toe to toe = 100 × 100 box, 2 × 4.06 kg/m): count channels × 2.
- **Steel sections to the real profile** (spec 29 ต.ค., "แบบเป๊ะๆ"): `scripts/steel_sections.py` — `lipped_c(h, b,
  lip, t)` outline with inner bend radius = t, `prism()` sweeps it into a closed solid. **Read every new size off the
  ไทวัสดุ product page's enlarged dimension picture** (h × b × lip × t, 6 m) and kg/m from TIS 1228; with ri = t the
  profile area × 7850 matches the table to 3 decimals for six sizes (`TIS`, `selftest()`; ri 0 is 1.7 % heavy) —
  the selfcheck reads area = volume / length back from the model and compares with the table at 1 %. Material: dark
  metallic `M_Steel_C` (black channel as sold). A profile mesh is not boxes: mark it `swept`; qto reads its length
  as the distance between its two end rings (works sloped); an axis-aligned one (wall plate) gives `_solids` its
  outline box (nothing may enter it). Mutations: t 2.0, no lips, sharp bends all caught.
  **End caps are quads between the outer and inner contour** — triangulating the concave C n-gon filled the hollow
  (the user saw solid bars: caps 18,688 mm² vs 1,034) while the volume still matched, so the selfcheck also reads the
  end-face area from the model (= pieces × kg_m / 7850). Look at a free end close up before reporting a profile.
- Concrete cast against brick needs no formwork (tie column sides).
- **A wall with arches or many openings is sliced in its own (u, z) plane** (SS-02 1 พ.ย.; `scripts/ss02_walls.py`): cut at every opening edge, tie edge and arc sample, stack what each slice holds, keep what is left as boxes or sloped hexahedra. Sample each arc to its own centre, or the last chord jumps the crown (a closure check of wall area minus openings found it: 0.027 m²).
- **A selfcheck must demand the piece, not only judge the ones that exist.** SS-02 lost 35 of 294 whisker bars to a filter over the whole wall instead of the panel: 92 mutations passed and a pinned total froze the error. Type the expected rows per wall end, and read positions, not counts: a count can be right with the piece on the wrong corner.
- Doors against a column or wall: grow the rough opening the other way, so the finished width still takes the frame.
