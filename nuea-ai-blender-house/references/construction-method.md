# Construction model: the method

Read before the first stage of a construction (take-off) model, and again when a check fails in a way you do not understand. Each stage's own rules are in `stage-*.md`.

## Stages, objects, rows

- One collection per stage `<PROJ> STnn <name>`. Build one stage, report it, then **stop for the user's check** before
  the next. Show only the built stages (`hide_viewport` on the other layer collections).
- Upgrading an old model: move its merged `Str_*` objects into an excluded `<PROJ> Structure OLD` until every stage
  is rebuilt (on a re-run merge into it: a second rename gives an unexcluded `... OLD.001`). Excluded collections are
  outside `view_layer.objects`, so a take-off script skips them. Delete it only when the user says.
- One element = an empty `<type>_<grid>` at its bottom centre, parenting one object per work item: `_Exc` (pit:
  WIRE, `hide_render`, take-off only), `_Sand`, `_Lean`, `_Conc`, `_Rebar`. Equal elements share mesh/curve data
  (a type is defined once; later one SketchUp component). The spec sits on the **data** as custom props (`element`,
  `th` = Thai BOQ label, `type`, `grade`, `bar`, `dia_mm`, `spacing`). Measuring code reads those props, never
  hand-typed lengths (the old `e42_boq.py` typed wall lengths).
- Rebar = curve, one POLY spline per bar on its centreline, sharp bends, round bevel d/2 with fill caps; length =
  sum of segments. Assert the hooks fit: bottom cover + 2d + hook ≤ T − top cover.
- Solids = `bmesh.ops.create_cube` with its vertices moved (closed, outward normals), scale 1. The measurer asserts
  scale 1 and `matrix_world.determinant() > 0` (a mirrored object measures negative).
- Rows per (element, type), so two footing sizes never mix. Pits 0.30 m wider than a 1.00 m footing on a 1.50 m grid
  overlap (E42: 5 pairs counted twice otherwise): net excavation = union of the pit boxes, reported as a trench.
- Meshes made of several disjoint boxes: 8 vertices per box in creation order, read back by chunks with a volume
  check. Formwork = vertical faces minus faces poured against other concrete of the stage: a formwork mismatch then
  also catches a beam slid into a joint or a joint lifted off its stub.
- Rebar count = first-fit decreasing with offcuts reused, not one stock bar per length group (E42 footing 23 → 22,
  ground beams 27 → 22 bars).
- Backfill = union of everything dug (pits + trenches) − solids inside it; cross-check by box subtraction
  (inclusion–exclusion breaks once a trench crosses two overlapping pits). Report the soil left over: the slab
  stage needs fill.

## Construction order

- **Construction order = modelling order** (spec 29 ต.ค.):
  1. Roof frame.
  2. ไม้เชิงชาย.
  3. Roof covering.
  4. Ceiling (ฝ้า).
  5. Primer.
  6. Finish paint, 1 coat on the walls and 2 coats on the ceilings.
  7. Floor tiling.
  8. Lights and electrical fittings.
  9. Second finish coat.

## Checks that can fail

- selfcheck must not take expected values from the builder's own functions: such a check cannot fail (a reviewer on
  ST02). Read the model back and test the spec (tie z of first/last, max gap ≤ s, min gap > 0, tie size from column
  size and cover). Also: every solid is a box, no two solids share volume (pairwise box intersection > 1 cm³ fails;
  touching faces differ by float32 noise), each stub's bottom = its footing top, top = beam bottom, centre = its grid
  point. Prove each check with a mutation in the headless test (stub sunk 5 cm, moved 5 cm sideways → must fail).
- Each stage ends with `selfcheck()`: every quantity against its hand formula at relative tolerance 1e-5 (vertex
  coordinates are float32; 0.7865012 vs 0.7865 failed an absolute test) plus a closed-mesh check. Test headless on
  the saved file first (`Blender -b --factory-startup --python-exit-code 1 -P test.py`, never saved), including a
  re-run (no duplicate objects, no `.001` data), then run it live and save.
  10. Doors, windows and aluminium.
- **Mutation tests judge against the spec:** build with the wrong value, put the spec back, then check. A check
- **Never read `collection.all_objects` in a build or check.** It is a stale cache after objects are rebuilt in the
  same script, and it hid a real tile clash. Use `.objects` (walk the children if there are any).
- **Clash checks:**
  - shrink one side's boxes by 0.1 mm, so a frame standing on a floor is contact, not a clash;
  - include CURVE objects (conduit and flex, evaluated with their bevel);
  - BVH overlap misses containment, so also test vertices inside the boxes.
- **Don't measure "on the floor" with a ray** that starts inside the unit. The ray meets the unit's own face lying
  on the tile face. Read the tile boxes under the footprint.
- **Mutation design:** change the build but keep the spec for the check. A build that sizes from the opening
  instead of the product can never fail a size check.

## Code gotchas

- **Shared exec namespace:** every module is exec'd into one namespace, so a later module's same-named function silently replaces an earlier one (`_minus` in walls vs ceiling broke build_walls; `_inset`, `_inside`, `SPEC` too). After adding a module, list duplicate `def`/global names across all modules.
- **OPENINGS c0/c1 are absolute along the wall axis.** Adding the line start moved two thresholds 3 m outside the house.
- **Inside/outside tests:** ray parity can flip when a ray grazes a 1 mm sliver's edge. Vote with 3 rays.
- **Floor-level rays from a later stage:** they must pass through the finishes (tiles) to reach the slab.

## Report and look

- Read the cut list against 10 m stock: a length just over 10/4 = 2.50, 3.33 or 5.00 m wastes a bar's tail (E42
  starters 2.535 m → 3 per bar, 17 bars; 2.50 m → 4 per bar, 13). Tell the user and let them choose.
- Report per stage in Thai: ready-mix rounded up to 0.5 m³, formwork = vertical face area, rebar as cut lengths →
  number of 10 m bars.
- SketchUp export waits until the modelling skill is finished (the user, 28 ต.ค.).
  that reads the mutated constant passes the wrong model (7 of 13 "missed" on the first E42 run).
- **Look at it:** structure shot with tiles hidden, close-up of a member end, then tiles + caps, then the other
  covering. The `look` tool's `angles` mode with a small distance clips inside the geometry; set the viewport's
  `region_3d` (location, rotation, distance) and use `mode="viewport"` instead.

## Modules, loader, tests (31 ต.ค.)

- **One loader in the project** (`scripts/e42_load.py`): the module list in build order and `E42_UPTO` to stop early.
  It refuses a function or class defined twice across `house_helpers` and the modules: the conduit's `_arc`
  shadowed the helpers' `_arc` and broke `build_walls` in the full namespace.
- **Tests live in the project and load through it,** with the path taken from `bpy.data.filepath`. A loader path in
  the scratchpad dies with the session.
- **Split a module past 800 lines by role,** keeping the code as it is. Conduit was split into settings + geometry,
  tables + entry, and the router. The loader order is the only coupling.
- **After a change to shared code, rebuild and rerun every suite** (four headless Blenders in parallel). A changed
  wall cut moved the porch tile grid. A stricter check found a real tile clash. A renamed object broke an old test.

- **Keep a bmesh referenced while you read it.** `max(v.co.z for v in _world_bm(o).verts)` lets the temporary bmesh
  be freed mid-iteration, and Blender crashes, both the live session and headless. Bind it, read it, then `free()`.
- **Prove the model rebuilds from nothing:** `build_all.py` builds every stage in an empty Blender (`--factory-startup`)
  and runs each stage's selfcheck. A hidden dependency on the old file shows up there, not in the working .blend:
  a skill script read from a fixed home path, or a test that expects the massing model's collections.

