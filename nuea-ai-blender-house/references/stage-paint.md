# ST09, ST10, ST13 primer and paint

*SS-02's code is not in this repo; its file names (`ss02_*.py`) are from that job.*

Read when modelling primer or paint coats, or counting buckets.

## ทาสีรองพื้น (ST09, spec 29 ต.ค.; `examples/e42/scripts/e42_paint.py`)

- Products: walls inside and out JOTUN Jotaplast Primer 18 L; ceilings (gypsum + Smartboard) JOTUN Essence
  Easy Ceiling 18 L; fascia primed too (product not given: ask).
- **Quantities follow the contractor's formula, not the paint seen:**
  - Wall primer = พื้นที่ผนังฉาบเรียบรวมทุกชั้น, the ST06 plaster take-off. The user corrected an area ÷ 87.5 at
    first.
  - Ceilings: area ÷ 87.5 m² a bucket (35 m² / gal × 5 gal ÷ 2 coats).
  - Draw films on the faces seen, for the picture only:
    - inside: floor → the room's ceiling;
    - outside: up to the soffit;
    - a face whose front is brick, concrete or more plaster is not seen;
    - a reveal splits at mid-depth to the rooms on its two sides.
- Outside ceilings (soffit, porch) take the exterior primer (the user): split the ceiling rows by board type.

- **SS-02 (1 พ.ย.):**
  - Ray parity steps must clear float32: 1e-6 at x 10 returned the same face and flipped the answer. Use 1e-5.
  - Sight lines at fixed heights cannot see how far a film runs: sample near floor and ceiling, near the plinth too.
  - Drop up-facing skin tops at ceiling level before splitting reveals, or hidden strips land in the outside film.
  - Pick the reveal's split axis from the wall depth; a crown face's normal does not show it.
  - Rust paint includes the wall plates: count them with the roof steel.
  - A carport slab sits above the ground: column skins there start at the slab, not the house floor.

## ทาสีจริงรอบที่ 1 (ST10, spec 29 ต.ค.; E42 `build_finish` in `e42_paint.py`)

- **Paints:**
  - Walls inside and out: JOTUN Jotashield Antifade Colours, semi-gloss. The sheet says it is for inside and
    out, on cement, fibre cement and gypsum: 28 m² / gal a coat, 2 coats, 2.5 gal buckets.
  - Inside ceilings: Essence Easy Ceiling, 2 coats.
  - Outside ceilings and the fascia: Jotashield white, the ceilings' colour.
- **Buckets: painted area ÷ (m² / gal × gal ÷ 2 coats)**, the user's formula. His TOA example is ÷ 43.75; Jotashield
  gives ÷ 35. Easy Ceiling is ÷ 87.5.
- The walls get coat 1 now and coat 2 after the electrics; the ceilings get both now. Count the whole 2-coat
  system in this stage's row.
- Each coat is a film one film-thickness out over the last.
- Check against the primer stage's areas (the same faces).
- Ask the colour codes.
- **Seen faces need the real shapes.** `_obj_boxes` gives each piece's bounding box, and that is wrong in two
  ways:
  - an L-shaped plaster piece's box covers the space in front of its neighbours;
  - the box of a brick wall with openings covers the openings, so jamb faces were dropped.
  - Fix: one BVH per closed piece with ray parity (`_solid_trees`, `_in_solid`), probing 0.5 mm and 3 mm in front
    of each face, so a 1 mm bead slot is not a seen face. On E42 the seen wall area went from 206 to 195.5 m².
- Films stand 0.5 mm off the surface and off each other. At 0.1 mm the viewport z-fought them into blotches
  (the user's screenshot).
- Eave soffit = vented all round, the porch's eave and the outer corner too. Only the porch ceiling inside the eave
  line is flat (spec 29 ต.ค.). Turning the porch-side eave strips flat lost the corner vents: the user's "ร่อง" over
  the porch meant the 5 mm open joints, not vent slots. When a complaint could mean two things, ask before you
  rebuild.
- A flat Smartboard ceiling meant to look like the inside one has butt joints filled smooth (gap 0, tape +
  compound row), not 5 mm open joints; open joints read as grooves in the viewport.
- Hanger rays pass through ceiling and paint objects, so a later stage cannot hide the roof steel.
- **Never iterate a temporary bmesh you hold no reference to** (`for f in _world_bm(o).faces` in a generator).
  Python frees it mid-loop and Blender segfaults. That crash took down the user's live session and the MCP link.
  Bind it, read it, `free()` it.

## Paint and tiles

- **Paint stops where tiles go.** Skip the room tiled to the ceiling. Cut the splash band out of the faces, only up to the wall's centre line, or it eats the outside face.
- **Jotun:** the TDS says Jotashield Antifade is for exterior only. Check the maker's TDS before using one paint inside and out. Inside walls: Essence Cover Plus, 10 m²/L/coat → 45 m² per 9 L bucket.

## ทาสีจริงรอบที่ 2 (ST13, spec 31 ต.ค.; E42 `build_coat2` in `e42_paint.py`)

- Walls only, the same faces as coat 1, at two films out. No take-off row: coat 1 already counts both coats.
  Leave out the `element` key so `qto` skips the objects, and have the selfcheck assert that it is absent.
- Use assumed default colours until the user gives the codes: off-white inside, light grey outside.
- **Coat checks need three properties.**
  - Direction: a film is k steps from the primer, not only one step from the coat under it. A distance-only
    check passes a coat laid on the primer behind coat 1, so always mutate with offset 0.
  - One-to-one: the set of matched back films has the same size as both island counts.
  - Area: the area matches coat 1.
- **The one-to-one check found a hidden ST06 bug.** `_box_minus` cut against a cutter that touched by float noise
  (~1e-15) and sliced the other axes at that ε range. The result was 0-thick boxes (float32) in 5 column plasters.
  Each one doubled a real face, so paint was over by ~1.6 m². Plaster (vol ÷ t) was unaffected.
  - Fix: ignore any overlap under 1 µm, and have `_boxes_data` assert that no box is under 1 µm thick.
  - After changing a shared geometry helper, rebuild every stage that uses it and diff its `report()` byte for byte.
- Rebuilding walls needs the modules loaded only up to tiles. The conduit module's `_arc` shadows the one in
  `lipped_c`.

## SS-02 laps and coat 1 (4 พ.ย.; `ss02_paint.py` `_unlapped`, `ss02_coat1.py`)

- **Plaster skins lap.** A column's plaster lies over the end of a wall's skin; a sill's or head's plaster over the ends of a reveal skin. A centre probe misses it, so the primer ran 1.84 m² into solid. Cut every seen face by each plain 8-vertex box piece that stands on it (material in front, starting within the probe reach), and check 5 mm in from each film corner. Test pieces one by one: an object can mix box and sloped pieces.
- **Coat 1 = the primer above the floor, less what tile, steps, risers, the floor finish and mouldings cover.** Check the inside walls geometrically against the primer, with the tile faces as typed in the tile stage's check (each face less its opening, plus the tile's depth at each end where it butts the next face). A hand total minus a hand total hid three errors that cancelled.
- **Grout is a cover.** Pad tile boxes by the joint, but a floor's in plan only: padding up eats a 2 mm band of wall paint all round (0.24 m²).
- **Coat 2 one-to-one:** match the films with a KD-tree under 0.01 mm. Rounded centre keys fail at rounding edges.
- **Covers are convex pieces, not bounding boxes.** Cut a face by each cover piece's own face planes, oriented away from the piece's centre (face winding can be flipped). Skip a wedge's collapsed faces: a zero normal makes every point look like it lies on that face, and the cut gives up. Push the cover's faces that look back at the painted face (dot < −0.5, so sloped reveals too) back by the brush reach.
- **Cut a moulding face by its own object's other pieces**, never by "everything except this object". Skipping the whole object and probing the centroid left every ledge under an upper tier bare (2.5 m² of SS-02's mouldings). Also cut it by the wall and plaster pieces, sloped ones included.
- **Dense sample checks need care, or they flag good work:**
  - Step 5 mm in along each axis of the face. On a long face the diagonal step lands on the edge.
  - Drop a sample that isn't at least 2 mm inside every edge (acute mitres, sloped arch edges). Keep the grid and edge samples off round numbers, because cover edges sit on them.
  - Count a sample as covered when a solid lies 0.3 mm in front (a curved moulding's wedge can be thinner than 1 mm), or 1.5–2.5 mm beside it (joints, edges).
  - When the film ray misses, retry it 0.3 mm aside: a ray on the seam of two films slips between them.
- **Horizontal sight lines never see sills, heads or ledges.** Check those by sampling the primer itself: wherever no cover stands within reach, coat 1 must lie on it. Add an area cap on the outside walls (coat ≤ primer).
- **Reach back only with the faces that lie over the painted face** (dot < −0.9). Pushing a more oblique face out along its own normal widens the cover sideways and cuts a neighbouring slice's face; the plane shift is not the swept volume. Probe offsets for "covered beside" must lie in the face's own plane (`n.orthogonal()`), not along world axes, or every sample on a sloped face dips into its own solid and is skipped.
- **A "no film laid twice" rule must ignore where a ring starts and which way it runs.** Two source faces cut to the same region give the same outline from different start corners. Copies added before the cover cut also come out identical wherever mouldings box a region in, so a mutation for an area cap has to add its extra films after the cut (patch `_film_mesh`).
