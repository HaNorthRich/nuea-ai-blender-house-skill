# ST09, ST10, ST13 primer and paint

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
