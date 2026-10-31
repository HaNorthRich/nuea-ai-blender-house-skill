# ST00–ST05 grid, footings, stubs, ground beams, slab, columns

Read when modelling the structure below the walls, or choosing a ground-beam type.

## Grid, footings, stubs (ST00–ST02)

- Grid first: loose-edge lines at GL plus FONT labels with a yellow material (default grey text vanished on the grey
  viewport grid), all `hide_render`. Number = line along x, letter = line along y, point = `A1`.
- **The input is the excavation level the user gives, not the footing bottom** (E42: dig to −1.50; the old model had the
  footing bottom at −1.20). Store it as `exc`, derive footing bottom = exc + sand + lean, and let every level above
  (stub height, starter length) follow. selfcheck: pit volume against GL − exc, every pit bottom at exc.
- ตอม่อ (stub): footing top → the **lowest** ground-beam bottom over that grid point (a beam can pass over a point
  mid-span, not only end there); the beam pour takes the joint. Where a lower beam meets (E42 porch beams top 0.39 vs
  0.44 at A2, A3, B3) the stub stops under the lower one, or beam end and stub share 5 cm (the old model counted it
  twice). Keep the beam lines (grid pairs + top level) in the script from this stage on.
- Starter bars stand where the column above needs them (E42 column 0.15, cover 2.5 cm), the stub ties wrap them
  tight, so a 0.20 stub gets 5 cm cover; assert it is ≥ 4 cm (in soil). L-foot 0.20 on the mat's top layer, top =
  highest beam top + lap 0.60 (50d). Ties RB6 @ 0.15: first/last 5 cm from the stub ends, count rounded up so the
  spacing never exceeds s, 135° hooks 75 mm (เชียงใหม่ is a seismic zone). Stubs of equal height and bar top share
  data, named by levels in cm (`P1_H119_T219_Conc`); never a `.` in a data name (it reads as a Blender duplicate).

## Ground beams (ST03)

- คานคอดิน (ST03): beams are clear spans between joint faces, one multi-box mesh per grid line; the joints J1
  (stub footprint, lowest beam bottom → highest beam top) are their own objects, cast with the beams, so beams,
  joints and stubs never share volume and the BOQ can see joint concrete apart. Lean strips under two perpendicular
  lines overlap pad × pad at every joint: lines along x keep theirs, lines along y give way (box subtraction); the
  check is the cell-count union of the full strips. Bars run the whole line with 90° hooks into the end joints
  (assert ≤ 10 m, no laps), stirrups per clear span.

## Slab on ground (ST04) and columns (ST05)

- พื้นหล่อบนดิน (ST04, the user's spec): per zone, compacted fill GL → beam top cut around beams and joints, wire mesh
  4 mm @0.20×0.20 (the user), slab 7 cm out to the beams' outer faces; tiles 3 cm go with the finishes. **Bathrooms
  10 cm lower** (the user): the bath is its own zone between the beam faces (fill and slab 10 cm lower, beams stay),
  listed after the house zone and cut out of it. A wet-room drop is easy to forget — ask if the plan doesn't say.
  - Mesh cover is held against the zone's true outline (zone minus the outside grown by the cover), so an L-shaped
    slab or a hole keeps 5 cm at a step or a bath edge; per-rect insetting put a wire 2 mm from the porch step.
    House and porch meshes stop at the 5 cm step (the user: no lap, no dowels).
  - Formwork: a face cast against concrete of an earlier stage needs no form either (bath and porch slabs against
    the beams); the house slab's edge round the bath and over the porch step does.
  - Cutters read back from meshes are float32 (beam top 0.34999999): round them to 5 dp before cutting, or the fill
    keeps micron slivers. A level check (slab at beam top, fill from GL) caught it, and a slab lifted 1 cm.
  - Soil balance: fill − soil left from digging = soil to buy, before any shrink factor on either side; say so.
- เสา (ST05, spec 28 ต.ค.):
  - **Ask the column and wall height every house**, like the floor type. The user's usual: column 3.00 m from the
    finished floor to the underside of the steel wall plate (อะเส) — most of these houses have no roof beam.
  - Column and stub the same section (0.20 × 0.20); the column bars are **one piece** from the L-foot in the footing
    to the column top, set at the stub stage (no lap), cover 4 cm on both (the stub in soil sets it).
  - Column top: steel plate 160 × 160 × 6 mm, its top at the wall-plate underside; bars bent 90° under it like a
    pinwheel (not crossed in an X), bend ≤ the gap to the next corner bar. Bend length is a cost lever: E42 bars
    5.033 m → one per 10 m stock (52 bars); bend 0.06 → 4.993 m → two per stock bar (the user chose it).
  - Ties run from the stub top through the ground-beam joint up to the plate (the user: count them through the joint).
  - Cast order is columns before the slab on ground: the slab is cut round the columns, its edges there need no
    form, the columns keep full-height formwork (`STAGES` order ≠ stage numbers).
  - A 6 mm plate at z ≈ 3 m: float32 gives ~3e-5 of its thickness — check plates by count and a looser volume.
  - Beams that lose columns get heavier at once: E42 A1–E1 / A2–E2 at 4.50 m with secondary reactions needed GB4
    0.20 × 0.50 (2 + 2 continuous + 2 specials per place); per-line types in `BEAM_TYPES` / `LINE_TYPE`, the stubs
    under a deeper beam come out shorter by themselves. Still to check: the moment where the special bars stop
    (only the continuous bars there).

## Which beam type goes on which line

- **Which beam type goes on which line** (the user, 28 ต.ค.: the 3 types of a drawing, e.g. SS-02 S-22 GB1/GB2/GB3, all
  0.20×0.40 DB12, RB6@0.15): `beam_wsd.py` with the engineer's criteria (fc' 173, fc 65, fs 1,700 SD40, n 10.26,
  wall 180 kg/m², finish 120, LL 200, RC 2,400). Per span: beam self-weight + wall (180 × height from beam top to
  ring-beam bottom) + slab share. The engineer's coefficients (`slab_to_beams`: two-way when S/L ≥ 0.5, short edge
  wS/3, long edge wS/3·(3 − m²)/2) hold for a beam the full length of the panel edge only; a span between stubs
  along an edge takes `edge_load()` (45° strip → equal mid-span moment; full edge = the coefficients, the middle of
  a long edge up to wS/2: a reviewer caught 8 % missing on E42 C2–D2). Roof load reaches the footings through the
  columns, not the ground beams. Then `continuous()` over the stubs (every live-load pattern; outer ends at least
  wL²/16 hogging, ACI 6.5.2 beam cast with its column), and per line the first type whose tension bars pass
  `bars_ok` for M+ (bottom, mid-span) and M− (top, support); a shear failure gives no type. The runner asserts
  every wall and every panel edge lands on beam spans for its full length (a missed match would drop load
  silently). Per-job runner: `examples/e42/scripts/e42_gb_design.py` (panels, walls, the type table).
  - **Ask the user the floor type before modelling the ground beams, every house** (the user, 28 ต.ค.): พื้นหล่อในที่
    or แผ่นพื้นสำเร็จ. Cast in place = soil filled to the beam top, wire mesh 4 mm, slab 7 cm + tiles 3 cm, so beam
    top = finished floor − 0.10 (E42 kept FL +0.45 → beams +0.35, porch +0.30; the old model's 0.44 was wrong) and
    the slab load goes to the soil, not the beams (`SLAB_ON_BEAMS = False`). Precast planks load the beams they
    bear on: ask the plank spec and span direction.
  - **Columns at most 4.50 m centre to centre along a beam line** (the user, 28 ต.ค.: closer is wasteful — E42 dropped
    B2, B3, C1, C2 with their footings and stubs). A beam whose end lost its column rests on another beam (คานฝาก):
    the joint stays (lean and trench under it too), the runner treats collinear beams joined there as one
    continuous beam and passes the secondary beam's reaction to the primary as a point load (`beam_loads`).
    Check the primary right away: E42's 4.50 m spans with two secondary reactions went past what GB1 carries.
  - **Ask the roof steel spec every house** (the user, 29 ต.ค.): wall plate (อะเส) section, and later rafters,
    purlins, ridge — E42 wall plate 100 × 50 × 2.3 mm tube on every wall/beam line.
  - **Every masonry wall line needs a ground beam under it** (the user). Check the walls in the live model (tall,
    thin meshes), not only the build script; the runner's wall assert stops on a wall without a beam.
  - Use d = h − the model's cover − stirrup − bar/2 (35.8 cm for 0.40 at 3 cm cover). The engineer's sheet uses
    d = h − 2.5, which overstates capacity by ~8 %.
  - Minimum steel 14/fy·b·d = 2.54 cm² is more than 2-DB12 (2.26) in a 0.20×0.40 beam: 2 bars are enough only
    while they are ≥ 4/3 of the steel the moment needs (M ≤ ~935 kg·m at d 35.8). Say so when a line sits near it.
  - Read the bar dots in the drawing's sections, not only the labels: S-22 draws GB1/GB2's "special" bar on the
    compression face (top at mid-span, bottom at the support). The user: put special bars on the tension side —
    bottom at mid-span, top over the columns. Lengths when the drawing gives none (the user): bottom 0.8 L centred,
    top L/4 from each column centre into every adjacent span, hooked into the joint at a line end (L =
    column-centre span). GB1 = 2 + 2 continuous + those two specials. GB2/GB3 mix labels the same way and are not
    confirmed: a line that needs more than GB1 is reported, not guessed.
  - The floor type moves the answer: E42 with a 10 cm slab carried by the beams → GB1 ×2, GB2 ×7, GB3 ×1; slab on
    ground (built) → every line GB1 (walls 180 × 2.60 m + self-weight: M ≤ 742 kg·m).
  - Beam bottoms below GL (slab on ground lowers the beams): dig a trench under the lean (lean footprint, lean
    bottom → GL), give way where house and porch strips at other levels overlap in plan, count it net of the
    footing pits, and backfill pits + trenches to GL. Filling from GL to the beam top belongs to the slab stage.
  - This picks among drawn types for modelling and BOQ; a licensed engineer (ภย./สย.) signs the real design.
