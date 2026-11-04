# ST07 roof frame, covering, trims, fascia

*SS-02's code is not in this repo; its file names (`ss02_*.py`) are from that job.*

Read when modelling the roof steel, CPAC or metal-sheet covering, caps or fascia.

## โครงหลังคา (ST07, spec 29 ต.ค.; `examples/e42/scripts/e42_roof.py`)

- **Ask every house:** the roof covering (CPAC or metal sheet) and the eave width. The user's standing values: hip
  roof (ปั้นหยา) **30° always**, eave usually **70 cm** (taken from the finished wall face — say so).
- The user's specs:
  - Rafters (จันทัน): C 100×50×20×2.3 **@ 1.00 m** for both coverings.
  - Hips (ตะเข้สัน), ridge (อกไก่) and king posts (ดั้ง): **2C ประกบ, the same section as the wall plate**.
- **CPAC:**
  - Battens: แปอะลูซิงค์ PROFAST 0.50 mm × 4 m, spaced as the CPAC manual says (p.7-9): first course 34 cm up from
    the eave, the top pair 8 cm apart across the ridge (Dry Tech; 4-6 cm with mortar), the courses between split
    evenly at 32-34 cm (`_course_step`; E42 0.335). A fixed 0.32 with an odd last gap is wrong. Hat profile from the ไทวัสดุ drawing: 61 mm overall, 20 mm
    top, 27 mm high, one side at 60° and one vertical. Joints lap ≥ 5 cm on a rafter (`joint`; the cut list adds
    it per joint).
  - Tiles: SCG ซีแพค สมูทคูล 33 × 42 cm (5.5 cm high: wave 3.0 + 2.5 thick; tile solidify offset +1 so the tiles
    sit on the battens).
  - Counts follow a common take-off rule: tiles `ceil(A × 10.5 × 1.05)` to tens, caps length × 3.3 × 1.03.
- **Metal sheet:**
  - Purlins: box 50×50×2.0 TIS 107 @ 1.00 m. ไทวัสดุ gives 16.62 kg / 6 m; the TIS outer radius ≤ 3t makes 2.88
    kg/m, within the ±10 % mass tolerance.
  - Sheets: GIANT KINGKONG 0.3 mm + PU foam 1", 76 cm cover × 3 m, crests 192 c/c, 10 cm end lap.
  - The user had it built as a TEST in its own collection, to be deleted once approved: the lesson is the method.
- Geometry:
  - Rafter undersides pass through the perimeter wall plate's outer top edge.
  - Each plane in (u along the eave, v up the slope) spans u ∈ [v cos θ, L − v cos θ], v ≤ D / cos θ, where D is
    half the short eave span. Hips at 45° in plan; ridge = long − short eave length (E42 1.50 m, over the A2-E2
    plate, which carries the 2 king posts).
  - Roof surface = the lowest of the 4 planes.
  - Hips/ridge: top corners on the planes.
  - **The 2C hip is deeper than the plane is high over the plate corner (1.2 cm clash): seat it on the plate
    corner** (raise until clear). The hips then stand proud of the planes, so battens and purlins are trimmed at
    both ends against the hips: each end only against the obstacles on its own half. Trimming one end while the
    other still clashed returned nothing — 2 of 54 battens survived, and the first checks passed.
- **Steel that runs into steel is cut flush and welded** (spec 29 ต.ค.: the old trimmed-back ends left gaps at
  the ridge/king post). Build each member full length into what it meets, then `_cope`: exact boolean difference
  with the other member's outline box (temp cube objects, solver `EXACT`; read the enum, it is FLOAT/EXACT/MANIFOLD
  in 5.2), keep the island nearest the start, record `len`/`axis`/`p0` (a coped mesh's rings are out of order,
  so qto and the checks read these) and `cut_by` = only the boxes it really meets (a box overlapping just the C's
  hollow leaves no face). Weld beads (`_weld_obj`, bevelled curve r 3 mm, `length` → RW1 in the take-off) along
  the edges where a face on the box meets the member's walls; king posts all round both ends; rafters across the
  bottom flange at the plate edge. Order: ridge, posts, hips (cut to ridge + posts), rafters (cut to all of
  those); metal purlins cut to the สะพานหนู. Clash check for frame members: the later-built member has no vertex
  inside the earlier one's stored box (`box`, `order`); a cut end's box overlaps by design, and a nearest-face or
  ray-parity test inside a 2C fails (its two channels touch back to back, and the boolean merges them).
- The selfcheck reads everything from the model:
  - Pitch, rafter spacing, and the eave 70 cm out.
  - Rafter underside at the plate edge = plate top; hips seated on a plate corner.
  - Posts on a plate and touching the ridge underside.
  - Batten first course, spacing ≤ lap, top course near the ridge, both ends reaching a hip.
  - End faces of every member = the drawn section.
  - Tiled area = plan inside the eave / cos θ.
  - Mutations: 8, all caught.
- **CPAC trims** (spec 29 ต.ค.; `scripts/cpac_caps.py`, `examples/e42/scripts/e42_roof_trim.py`, CPAC installation
  manual Dec 2024 + catalogue p.4). The catalogue and manual print no cap sizes; the SCG dealer pages do (W×L×H
  cm): ครอบสันโค้ง 25×33×10 3.0 kg (3.3/m → 30.3 cm cover, 2.7 cm lap), ครอบโค้งหางมน 21×36×13, สามทาง
  37×41.5×14, สี่ทาง 36×36×14, ปิดจั่ว 22×33×22, ข้างปิดชาย 18×34.5×9.5 (ครอบข้าง: 3/m, size not published).
  Wall 13 mm from the ridge cap's weight; `selftest()` checks every piece's volume × 2,100 against its weight.
  - Hip roof = ครอบโค้งหางมน at each hip foot, ครอบสันโค้ง up the hip (each tail over the head below), ครอบโค้ง
    สามทาง where hips meet the ridge, ridge caps from both ends to the middle, ครอบโค้งสองทาง over the middle
    (Dry Tech). Gable pieces (ปิดจั่ว, ข้าง, ข้างปิดชาย) only on gables.
  - Dry Tech under the caps: brackets ≤ 1 m on the 2C member, cap rail (hat) whose top touches the cap's inner
    crown, underlay strip each side ending 2 cm inside the cap edge; tiles cut ~5 cm apart at hips and ridge
    (`_inset` makes a hidden cut bed for the tiles; the full bed keeps the take-off area). One screw per cap, 3 on
    the three-way.
  - Seat every cap on the tile crests: lower it by W/2 · tan(fall across the line) and bevel the skirt feet to
    that fall (`arch(fall=)`), or the inner foot sinks T · tan (7 mm). Narrower rings (the หางมน nose) sit higher.
  - **The three-/four-way is one continuous shell** (the user rejected arms round a ball: "ขาดๆออกจากกัน"): a height
    field = smooth max of the arms' arches and a centre dome (a groin vault), sampled on rays from the centre so
    the skirts follow the outline, thickness along the normal; on the roof each arm's feet read the tile height
    (`floor`). Compare against the product photo before installing.
  - `selfcheck_trims`: every piece's lowest point on the tiles (±2 mm, over the 4 crest planes), caps continuous
    foot → three-way and three-way → two-way with laps of 2.7 cm, one three-way per junction, two-way mid-ridge,
    rail under the crown, brackets ≤ 1 m and their feet on the member, strips 2 cm inside the cap edge.
- **Metal-sheet details** (METALUXE SSR760 guide; it gives no cap sizes — wing 20 cm, 0.35 mm, 2.40 m assumed):
  สะพานหนู each side of the hip 10 cm off its centreline, flush with the purlins; sheets cut 2.5 cm short of the
  hips; top purlins 15 cm apart across the ridge; an end lap must sit on a purlin; hip caps 10 cm past the eave
  corner with the nose folded shut, cap laps ≥ 20 cm, ridge cap over both hip caps. Screws: eave + end-lap purlins
  every rib, middle purlins centre + edge ribs (50 mm), ridge purlin + สะพานหนู every pan (16 mm), caps 5 mm in
  from the edge on every rib (22 mm). `selfcheck_metal` reads all of it back.
- **ไม้เชิงชาย** (spec 29 ต.ค.; SCG synthetic-wood manual §4.1 p.12, fascia catalogue; `examples/e42/scripts/e42_fascia.py`).
  It goes on after the frame and before the covering.
  - Plumb fascia ("จันทันดิ่ง"): rafter and hip ends cut plumb at the fascia back (`_plumb_cut`: bisect +
    `holes_fill`, both eave planes for a hip). Then เหล็กฉาก 5×5×0.23 cm welded to every rafter end (rafters
    ≤ 1.00 m apart; wider → steel ties), and an 8" board on the angles (45 mm drill-point screws, 2 per rafter).
  - Over the 8" board: ไม้ปิดกันนกลอนคู่ 6" for tiles, its top following the tile rolls 2.5 cm over the batten
    tops (CPAC p.7); or a 6" board under the sheets, 45 mm ×1 per rafter + 38 mm stitching @ 0.30 m.
  - Mitre the corners 45°. Joints fall on a rafter (or a 3" × 30 cm backer). The fascia must not carry the tiles.
  - Cut with a dust mask, as the SDS says (crystalline silica).
  - Catalogue sizes: 4/6/8" × 4 m × 1.6 cm, 0.25 /m; ผิวเรียบ 3 m; วันพีช 23 × 300 × 2.1 replaces the 2-board
    build-up.
  - **The eave (70 cm) is to the fascia's outer face.**
    - Tiles overhang it 5 cm under a trough. That figure is not printed: assumed, tell the user.
    - `cpac_tiles` lifts each tile off its bed along the normal, so the tile edge stands out ≈ h · sin θ past the
      bed edge (`_tile_edge`).
    - Metal sheets overhang 15 cm (SSR760 p.6). They ride the purlins + foam: start them (B + foam) · sin θ
      further up (`_sheet_v0`).
  - `selfcheck_fascia` reads it all back:
    - the 8" top flush with the rafter tops;
    - the bird-stop trough 2.5 cm over the bed;
    - the covering's overhang;
    - the 6" under the foam plane;
    - an angle at every rafter, welded;
    - the corners closing.
  - Constants that feed other constants must be functions (`_tile_edge()`). A module-level number computed at
    load ignored the mutation, and the test "missed".
  - Booleans on objects in an **excluded** collection are not evaluated: the cuts silently did nothing in a
    headless run. Link the object and cutters to the scene collection while evaluating (`_cope`).
- **Read the section before taking E42's rafter rule** (SS-02 1 พ.ย.; `scripts/ss02_roof.py`): its A-09 has the rafter underside on the eave soffit at the eave line, so a rafter passes 0.27 m over the wall plate on a stub post. Measure the layers off the section's vectors. The E42 rule would have dropped the ridge 19 cm.
- **An L plan is six skeleton faces:** the wing's outer plane is the main roof's, so that hip does not exist. Roof height = min(planes, with max of the two planes at the valley).
- **Without booleans:** cut each tube end on its own plane per vertex (`_cut_tube`). Faces stay closed and volume ÷ section still reads the centreline length.
- **Scan steel pairs with a BVH on the outer skin drawn in 1.5 mm** (`check_roof_clash`): it found 4 real clashes that vertex rules missed, because a tube only has vertices at its ends.
