# ST12 conduit routing — rebuild spec (the user, 30 ต.ค. 69)

The current `scripts/e42_elec.py` was approved by a reviewer on 30 ต.ค. It routes each circuit as a tree with branch/tee boxes and corrugated flex. It still breaks the rules the user added later the same day. This file is the spec for the rebuild. Every rule here comes from the user's review of the 3D model.

## Rules (the user)
1. **No circuit runs back alongside itself.**
   - Branch box: a 4×4 where the run enters a room. The run comes into it and leaves both ways.
   - Tee box: a 4×4 where the run leaves for another room.
   - Status: done in the current file. Keep it.
2. **Flex into a downlight.**
   - Corrugated and bent smoothly, never a rigid elbow.
   - Status: done (`_fillet`, `EL_Flex_Ribs`). Keep it.
3. **Boxes are fixed to the wall (or the steel wall plate on top of it).**
   - The lid faces the room.
   - No conduit may pass in front of a lid: other runs go above or below the box.
   - Never floating on a lane.
4. **Conduits are clipped onto the wall face, stacked by height.**
   - They are not rows out in the room.
   - The user chose "ท่อเรียงซ้อนบนผนัง".
5. **The band continues up onto the wall plate where the plaster band is full.**
   - The user chose "กิ๊บต่อขึ้นไปบนโครงเหล็กหัวผนัง".
6. **Rigid PVC is bent on site, never mitred 90°.**
   - Every turn is an arc.
   - Minimum centreline radius (NEC Ch.9 Tab.2; no Thai figure found): 1/2" 102 mm, 1" 146 mm.
   - Bends are counted by angle: ≤ 360° between boxes (วสท.).
7. **Through a wall at a room corner.**
   - The run comes along the wall at right angles to the one it crosses and goes straight through near the corner, about 2.5 cm off the side wall. No bend.
   - On the far side there may be no wall to follow on. Then it bends (r ≥ 102 mm) onto that room's wall.
   - The user chose "ผ่านที่มุมห้อง".
   - Never drill the steel wall plate (holes through brick only, below z 3.45).
8. **A circuit that goes both ways from the CU leaves the CU as two conduits** (L1, L2, S2), joined at the breaker in the CU. No branch box in front of the CU. The user chose "ออกจากตู้ไฟ 2 ท่อ".

## Measured in the model
| Item | Value |
|---|---|
| Ceilings z (Bed2/Bed1/Living) | 3.25 |
| Bath ceiling z | 2.95 |
| Porch/eave soffit z | 3.069 |
| Ceiling wall angle / runners top | 3.279–3.281 |
| Wall (brick + plaster) top | 3.45 |
| Wall plate `AS_*_2C` (2 × C100×50×20×2.3) | z 3.45–3.55, on all 8 wall lines, 100 mm wide, centred on the grid line |
| Living east side (CU wall) | plaster face x 6.025; column D3 face 5.90; wall-plate face 5.95 (7.5 cm proud of the plaster) |
| Plaster band | 3.285–3.45 = 16.5 cm |
| Wall-plate band | 3.45–3.55 = 10 cm, on a different plane |
| 8 circuits stacked on the CU wall (7 × 1/2" + 1" main, 2 mm gaps) | ≈ 15 cm (fills the plaster band) |
| Boxes (TOP) | 2×4: 115 × 68, 50 deep; 4×4: 115 × 115, 55 deep |

A 4×4 fits only in the plaster band. A 2×4 fits in either band.

## Design (to build)
1. **Track = (plane, height) per circuit visit to a room.**
   - Conduit centreline 25 mm off its plane (on saddles), so a run enters a wall box's end knockout straight.
   - Plaster-band heights first; wall-plate heights when the plaster band is full along that stretch.
   - Where a column stands proud: pass it with offset bends (2 × 30°, counted in the 360°), or stay on the wall-plate plane, which has no columns.
2. **Box on the owner's track, back on its plane.**
   - Slide it along the track to where the tracks it blocks above and below are free of other runs. 2×4 blocks ±1 track at 22.5 mm spacing; 4×4 blocks ±2.
   - Two passes: route all runs first, then place boxes against the known occupancy.
   - Wall devices: the box sits straight above the device, and the drop goes straight down the chase from the box bottom (no bend).
   - Downlights: the box sits on a low track so the flex from its bottom crosses no track below.
3. **Route as arcs.** Store each conduit as a polyline sampled along the arcs.
   - Selfcheck reads the model: radius ≥ the minimum (from three consecutive points), Σ bend angle ≤ 360° between boxes, no mitre.
   - Bends in the take-off: field bends, so no elbow fittings. Count the bending spring as a tool, not a material row.
4. **Wall crossings at corners only** (CROSS table to be redone per corner); holes only below z 3.45.
5. **Keep from the current file:**
   - the circuit tree (`feed`, `kids`) and `_lead` conductors;
   - flex fillet and ribs;
   - the selfcheck tree check and the "never alongside itself" check;
   - box product data and `_top_box`;
   - device points and CTL.
6. **Selfcheck additions:**
   - every box touches its plane;
   - no conduit in front of a lid (the box's front prism up to 0.30 m out is clear);
   - every conduit segment lies within 30 mm of a wall/plate face, except at bends and through-wall legs;
   - bend radius and angle as above;
   - no hole through a wall plate.

## Decided after the spec (the user, 30 ต.ค.)
- A column standing proud of the wall by 7–12.5 cm is passed with **offset bends: 2 × 30° out, straight past, 2 × 30° back.**
  - That counts 120° of the 360°.
  - At r 102 mm, a 7 cm offset needs ≈ 0.18 m of run each way.

## Geometry worked out (bend radius changes the plan)
- **Corner column:** a single 90° arc that clears it while both straights stay at 25 mm needs a large R. For the E42 corner columns, which stand 14 cm proud, that is 0.44 m and bulges far off the walls.
  - So the code uses one 90° bend (R = r_min) only when the column is shallow enough. Otherwise it uses **2 × 45° bends**, with a short diagonal that passes the column corner by r + 1 cm.
  - Either way a room corner costs 90°.
- **No branch box at a room entry.**
  - A box on the wall that sends one branch back the way the run came needs a bend r ≥ 102 mm out of a 16.5 cm band. Not buildable.
  - Instead: enter each room at a corner and go round its walls **one way** (the loop reaches every point).
  - Tee off other rooms from a **4×4 that has 2 knockouts per end**: in at one end; out of the other end twice, at two heights, one on to the next devices and one to the next room on its own track.
- **Straight-through corner crossing works only where the wall the run follows carries on into the next room.**
  - Here: E1-E3 (north, Bed1↔Living), A1-E1 (west, Bed2↔Bath↔Bed1), A3-E3 (east, Living↔porch side).
  - Elsewhere the far room has no wall in line. After the hole, the run bends 90° onto the crossed wall's far face. That puts it ≈ 13 cm off the face, so it needs an offset back (90° + 60°).
  - Pick crossings that keep this rare. Living↔Bed2 has no in-line wall at all, so it goes via Bed1 (north wall) or via the bath.
- **Home runs:** they rise in the chase above the CU and turn along the wall in its plane (90°).
  - Order them so the arcs nest (the lowest track turns furthest from the CU) and no rise crosses another circuit's track.
  - The bend starts inside the chase, below the ceiling.
- **Chased drops (the user, 30 ต.ค.):** the vertical drop to a switch or socket is buried in a vertical chase cut in the wall (กรีดผนังฝังท่อ).
  - Conduit centre 15 mm behind the finished face (1/2", ~6 mm cover).
  - Model a chase strip in the wall for the take-off: chase length (m) per drop, plus re-plastering the chase.
  - The drop leaves the box bottom straight down into the chase (a box connector, no bend).
- **Drops to wall devices:** the box sits straight above the device and the drop runs straight down. The kick from 25 mm off the face into the chase is taken at the box (a connector), not as a bend.
- **Capacity on the CU wall:**
  - 11 home runs (8 circuits + L1, L2, S2 doubled) need 9 plaster-band tracks at 18 mm (1/2") plus room for the 1" main.
  - They split north and south of the CU, so ≤ 6 share any stretch. It fits without the wall plate.
  - The wall plate stays the overflow.

## Open (ask the user when reached)
- Clip spacing on the wall plate (steel): saddles with self-drilling screws?
- Review follow-ups still open on the current file (fold into the rebuild):
  - mutations must assert the message of the check they target;
  - a tee-box mutation;
  - guard against forced walks going the long way;
  - `_fillet` clamp;
  - docstring "4.2 cm".

## Build progress
- **Step 1 — done (30 ต.ค.).** `scripts/e42_conduit.py`, loaded after e42_elec.py (not yet in `load.py`).
  - `_round(poly, radii)`: a sharp polyline bent to true arcs, asserting each bend fits its legs.
  - `_track_path(room)`: the counter-clockwise plan line round each room, 25 mm off the plaster.
  - Corners: a 90° bend, or 2 × 45° past a deep corner column. The E42 corner columns stand 14 cm proud; a single arc there would need R 0.44 m.
  - D3 next to the CU is passed with a 4 × 30° offset.
  - Bend totals per loop: Living 480°, the other rooms 360°.
  - Checked by eye in Blender (D3 offset, Bed1 NE chamfer).
  - Testing tip: `_voids()` raycasts the slabs, so unhide before calling it.
- **Step 2 — done (30 ต.ค.).** In `e42_conduit.py`:
  - `_Line(room)` is a room's run line with arc length: `at(s)`, `s_of(P)`, `span`, `stretch(s0, s1, sg, z)` (3D points along the bends), and `bend_deg` (from the measured bends).
  - `_Levels(room, line)` hands out heights stacked up from the wall-angle top + 2 mm to the wall top 3.45, lowest first.
  - Two runs share a level only on stretches at least 3 cm apart. A full band asserts.
  - CU-wall test: 6 runs north + 5 south, including the 1" main, fit with the top at z 3.387, because the north and south runs share levels.
  - Checked by eye: the stack passes D3 together on the same offset bend.
  - The wall-plate overflow isn't needed so far.
- Step 3: home runs (split at the CU), corner crossings, boxes on the wall (2 passes), tees with 2 knockouts per end, straight drops, flex.
- Step 4: selfcheck (bend radius/angle from the model, box on its plane, lid clear, no hole through a wall plate), mutation tests, a reviewer.
- **Step 3 (in progress, 30 ต.ค.).** In `e42_conduit.py`:
  - `_Levels` now holds bands (z range × stretch). `take_joint` finds one height for a whole branch tree across rooms. If it fails, the error lists the free heights for each band.
  - `_round3` makes 3D field bends.
  - `XS` + `_xing` handle the crossings, all checked:
    - Bed1 via E2: offset 4 × 30° past the column; the run leaves the Living line early and joins the Bed1 line late, both on straights.
    - Bath and Bed2 via C2: bend 2 × 30° out + 90° in.
  - `_routes_wall` covers branches CCW/CW from the CU, home runs bending level in the chase, wall boxes, tees (child 2·KO up), drops in a chase and flex. MAIN/L2 (porch/eave) are skipped for now.
  - Box clearance below: flex 3 cm, chased drop 2 cm.
  - **Blocker found:** the Living plaster band (16.5 cm) can't carry L1 + S1 + H1 + A1 past each other's boxes. A 4×4 tee is 11.5 cm tall, which leaves room for ~2 passing conduits; a 2×4 box plus clearance takes ~9.5 cm. S1 finds no height even with its tees slid 1.5 m back. Waiting for the user's choice of fix.
- **the user's fix (30 ต.ค.): the wall-plate face carries the passing runs.**
  - A Living stretch over 2 m without a box goes up onto the plate band (3.45–3.55, 5 levels at 18 mm, no columns: a clean rectangle of plate faces per room, corners 90°).
  - It comes back down to the plaster band before its tee or crossing. The plaster band is for boxes and the runs into them.
  - Up and down depends on the plate:
    - proud plate (CU wall and north wall, +75 mm): first step out (2 × 30°), then rise in front of the band (2 × 30°);
    - set-back plate (west wall, −65 mm): first rise on the plaster face to above the wall top, then step back over it.
  - The whole plaster band over a transition stays clear of boxes: nothing passes in front of a lid.
  - Home runs cannot rise from the chase straight onto the plate (the bend radius doesn't fit under a proud plate). They start in the plaster band and step up later.
- **Step 3 status (30 ต.ค., later).** The wall-plate passing band is built in `_routes_wall`:
  - `_plate_rect`/`_plate_line` give the Living plate rectangle 3.05–5.95 × 1.55–7.45, z 3.45–3.55.
  - Below the plate: `plate_gaps` picks Living stretches over 2 m without a box and up/down spots where both lines are straight.
  - `climb()`: proud plate = out then up; set-back = up then back. 2 × 30° each, ≤ 0.75 m.
  - Band kinds run/box/front: a climb in front of a proud plate clashes only with boxes and other climbs.
  - Downlight boxes keep 0.3 m clear of every switch/socket box (`dl_s`).
  - Retries slide the tees back and the climbs in.
  - **Still failing at S1:** L1, S1, H1 and A1 all take the same Living path and tee off at the same E2 / C2 spots. The tees are 11.5 cm tall, and the climbs collide.
- **Next design move (decided, to build):**
  1. **Chain the bedroom side.** Living → E2 (offset) → Bed1 (north wall west, west wall south) → D1 (offset, column) → bath (west wall south) → C1 (straight, no column) → Bed2. Tees sit inside the rooms on the way, before the next crossing; devices past the crossing point are reached by the parent going on round. Only one Living exit for the bedroom side.
  2. **Climb bands use their real height range** [z − r, zp + r]. Allocate the plate height zp first (it doesn't depend on z), so climbs at different heights may share a stretch.
  3. Porch (B2) and eave (B3) for L2/MAIN after that.
- **Chain built (30 ต.ค., late).**
  - `XS` + `_xing(lines, X, Y)`: Living→Bed1 E2 offset, Bed1→bath D1 offset, bath→Bed2 C1 straight. All counter-clockwise; geometry checked.
  - `visit()` plans each room recursively; `walk_visit()` lays it.
  - A tee child goes up 2·KO, or down when already up, so heights don't climb room by room.
  - **L1 now routes.** S1 still fails: Bed1's north and west walls carry L1, S1, H1 and A1 with their tees (11.5 cm) and boxes (6.8 + 2–3 cm) in a 16.5 cm band.
  - Asked the user (options): shared branch boxes for several circuits / a device box doubling as a tee; runs on the ceiling framing for passing; or bigger band use.
- **Shared boxes (spec 30 ต.ค.: "กล่องแยกใช้ร่วมหลายวงจร").** Implemented:
  - A device box before a crossing doubles as the branch: a 4×4, with the child from its other far knockout, 2·KO up or down (`tee_dev`).
  - Living points past the Bed1 exit go on the clockwise conduit from the CU (no tee in Living).
  - The wall-plate passing band is now in every room (`PL[room]`, `plate_gaps(room, …)`, `climb(room, …)`).
  - L1 routes. **S1 still fails in Bed1:** its 4×4 branching socket box (13.6 cm with clearance) can't clear L1's run at the height L1 holds there.
  - Root cause: one height per circuit for its whole chain.
- **Next (proposed):** let a run change height inside a room with a vertical offset on the plaster face (2 × 30°, ~0.35 m along, the band clear between the two heights). Then each room visit takes its own height, allocated room by room, and the chain no longer forces one height everywhere.
- **Per-room heights (30 ต.ค., later still).**
  - `visit()` plans one room at its own height. A run arriving at `z_in` keeps it when free (`take_joint(prefer=z_in)`); otherwise it changes height with a 2 × 30° jog on the wall face just inside the room (`JMAX` 0.40 m, start staggered on retry).
  - `place()` allocates room by room (retries: tee up/down, tees back, climbs shifted 0.8 m, jog start).
  - Each booking has an owner, so a run doesn't clash with its own consecutive stretches.
  - A room checks that the height it hands on lands free in the next room (above that room's ceiling).
  - Climbs avoid every switch/socket position (their boxes are fixed above the device).
  - **No branch boxes at all now:** a circuit whose points lie past a room's way on leaves the CU as one more conduit (segments in `plans`).
  - **Result:** L1 routes Living → Bed1 → bath → Bed2. S1's conduit that passes Bed1 for the bath/Bed2 finds no height: L1's boxes block its jog, and Bed1 has no straight 0.75 m clear of switch/socket boxes for a climb onto the plate.
- **Idea to ask the user:** passing conduits could cross from room to room over the top of the wall plate in the roof space (z > 3.55, no hole). They would then never come down into the crowded plaster band of the rooms they only pass.
- **the user (30 ต.ค.): passing conduits may cross a wall over the top of its wall plate** (roof space, z > 3.55, no hole).
- **Design to build:**
  - A conduit only passes a room → it stays on the wall-plate band (plate line, 5 levels) through that room.
  - At the corner (E2 / D1 / C1) it rises along the plate face (2 × 30°) to its over-height (3.56 + k·18 mm: the conduits crossing there stack over the plate) and runs straight on over the crossed wall's plate. The plate lines of the exterior walls carry on in line from room to room.
  - Then it comes down (2 × 30°) onto the next room's plate band.
  - It goes down to the plaster band (climb) only in a room where it has boxes; Living points first, then up.
  - Check the roof steel: rafters sit on the exterior plates near the corners (the selfcheck has the roof-steel ray test).
- **Count before building the over-plate passing (30 ต.ค.).**
  - Without branch boxes, the bedroom side needs 7 conduits through Living's north wall to E2: L1 ×3 (Bed1 / bath / Bed2), S1 ×2, H1, A1. The north plate band holds 5 levels; the plaster band beside the kitchen socket boxes holds ~3.
  - A split that could work: Bed1-bound conduits go counter-clockwise (north wall → E2). Bath/Bed2-bound conduits go clockwise (south wall, west wall → A2-E2 at C2, a bend crossing at plaster height).
  - The greedy allocator meets a new limit at each circuit.
- **Proposed to the user:** a route table written per conduit (rooms, way round, plaster/plate per stretch, crossing type, box positions), drawn as a designer would. The code builds the geometry from it and checks every rule (bend radius/angle, lid clear, holes only in brick, clearances).
- Code state: `_over()` (the crossing over the plate) is written but not wired in. `_routes_wall` (recursive visits, per-room heights) routes L1 fully and fails at S1.
- **Route table (the user agreed, 30 ต.ค.): `ROUTES` in `e42_conduit.py`.**
  - 10 conduits:
    - L1-Bed1, S1-Bed1, A1 → counter-clockwise to E2;
    - L1-Bath (with SW_Bath) → counter-clockwise to C2;
    - S2-ccw, S3 → Living only;
    - H1, L1-Bed2, S1-Bed2 → clockwise to C2;
    - S2-cw.
  - L2 and MAIN are skipped for now (porch/eave set).
  - `XS` is keyed (from, to, way): adds Living→Bath/Bed2 clockwise (bend, travel north).
  - Plans come from `ROUTES`; the owner of a booking is the route name.
  - A room with a box inside its way in keeps the incoming height (`strict`); the room before books that room's bands too.
  - Living-only conduits stay on plaster.
  - Up and down climbs shift separately.
  - Climbs no longer avoid switch/socket positions outright: the height-aware front/box check decides. Routes owning Living boxes book first.
  - Test order with `CD["order"]` (circuit ids).
- **Status:** each route has placed in some order, but no single order routes all 10 yet.
  - `["S2","S3","A1","S1","H1","L1"]`: S2, S3, A1 OK; S1 fails in Living (climb windows on the east/north walls).
  - `["S3","S2","A1","S1","H1","L1"]`: S1 passes Living and fails in Bed1 (run 4.06→9.54 vs the AC box and SO_Bed1_1).
  - Failed attempts are kept in `CD["_errs"]`.
- **Next:**
  1. Let several passing conduits climb in one window: stagger the lateral offset of each climb's vertical (lat + k·20 mm), or share one climb window per wall.
  2. Then `build_elec` → `_routes_wall`.
  3. Step 4 selfcheck rewrite (bend radius/angle from the model, box on wall, lid clear, holes in brick only, chases) and test_elec.
  4. A reviewer.
  5. L2 / MAIN routes (porch B2 straight, eave B3) as step 3b.
- **30 ต.ค. (latest).**
  - Climbs in slots: k·22 mm out (`SLOT`); bookings `run:k` / `front:k` clash only within the same slot (`_Levels._clashes`).
  - Over-the-plate crossing wired in for Living→Bed1 (`XO`, `over_book`, `over_path`): on the plate to E2, over the A2-E2 plate at 3.56 + stack, down onto Bed1's plate, then down to plaster before the first box (`from_plate`, `down`).
  - Downlight boxes keep `TR + 0.75 + dlx` past the entry.
  - Every attempt books plaster + plate + over + the next room, and is undone if any part fails (`snap`).
  - A room entered over a plate may also put the stretches between its boxes on its plate.
  - **Best so far, order `["S2","S3","L1","A1","S1","H1"]`:** S2, S3, all three L1 conduits and A1 route; S1-Bed1 or A1 fails in Bed1. Bed1 is the crunch: three conduits come down near the NE entry, and the 14 cm NW corner column leaves < 0.75 m of straight before the AC box.
  - Ideas:
    - climb length from the actual (z, zp) instead of the fixed TR 0.75;
    - an over crossing straight into Bed1's west-wall plate for A1/S1 (descend near their boxes);
    - or A1 and S1-Bed1 as one route order with the AC first.
- **30 ต.ค. — all routes allocate (shared conduits).**
  - The user approved: two circuits may share one conduit only where the wall band is too full, fill ≤ 40 %.
  - ROUTES is now 8 conduits: L1-Bed1 · A1+S1-Bed1 · L1+H1-Bath · S2-ccw · S3 · L1+S1-Bed2 · S2-cw (+ GND). The first circuit in an id sets the size; `piece()` counts each member's conductors past that piece + one earth sized for the largest; it asserts fill against `CD["fill"]` (**assumed** THW OD = IEC 60227 max, 1/2" ID 15.8 mm: confirm against the ตราช้าง / มอก. figures). Max fill 35 % (A1+S1 at the AC).
  - Derating not coded. Hand check, 4 current-carrying conductors × 0.8: THW 4 ≈ 22 A (> 20 A), THW 2.5 ≈ 17 A (> 16 A), THW 1.5 ≈ 12 A (> 10 A). These are rough ampacities; confirm against the EIT table.
  - Why each merge: Bed1 had 3 conduits for one band. The bath's heater box sits just inside the entry, so H1's height = the box's, which clashed with L1-Bath. In Bed2, L1 and S1 entered strict at one height.
  - `climb()`: a plate only a few mm proud gets 2 shallower bends (angle bisected), not 2 × 30°.
  - `HOME` 0.55: no climb before the CU home run is on the wall face. Before this, the run wrapped a whole extra lap of the living room (+18 m). It now asserts against a wrap.
  - Box tangent flipped so the TOP lid faces the room. Default order `["S2","S3","A1+S1","L1+H1","L1+S1","L1"]`.
  - `build_elec` → `_routes_wall`; `load.py` execs e42_conduit.py. `EL_Chase` holds the chase length (27.4 m).
  - Result: 1/2" ≈ 106 m (incl. drops) · flex 4.8 m · 19 TOP 2×4 · 3 wall holes · wire 1.5 147.5 / G1.5 34.8 / 2.5 149.2 / G2.5 89.8 / 4 52.0 m (L2 porch/eave not routed yet).
  - **Next:** step 4 selfcheck rewrite + test_elec (the old selfcheck / mutations target `_routes`), then L2 / MAIN (3b), then save the .blend after a backup.
- **30 ต.ค. afternoon — the user: the ground conduit ran down the outside face (photo).**
  - Ground run is now: CU bottom → 2 bends into a chase → straight down in the wall → bent into the slab under the wall (below the slab top FL − 0.03) → down through the fill inside the GB1 ground beam → under the beam at −0.30 → rod 0.5 m outside (rod top −0.30). Laid before the pour. Checked: not through the beam / footings, not exposed in the room, nothing above ground outside.
  - Also found: the switch/socket drops kinked sharply (4.5 cm) from the box bottom into the chase. Bent properly, they need ~13 cm of band height under the box, and the 16 cm living band could not hold them. **the user chose "loop through the device box"** (no TOP box over the ceiling for wall devices).
    - The run turns a_l ≈ 21.7° into the wall, then bends 90° down while still heading into the wall, into a chase straight down to the device box top. When more follows, a second conduit comes back up beside it (±LK 12.5 mm) and out the same way. A loop reaches LOOP ≈ 0.155 m along the wall either side.
    - Two wall boxes closer than 2·LOOP (AC_Bed1 over SO_Bed1_1) are linked inside the wall: box bottom → 2 bends ≤ 30° → next box top (rear knockout).
    - Earth: a piece to switches only carries none.
    - SO_Fridge (assumed position) moved 5.60 → 5.53, clear of the NE corner column's run bend.
  - Plate band: a climb's window is now booked in the plate levels too (`climb_band`, `plate_take`); before, a climb crossed another conduit's plate run. `plate_gaps` no longer wraps when reaches overlap.
  - Plate-line corners: r = rmin + 3·slot, so a run in slot 3 still bends ≥ 102 mm (was 80 mm). `CD["slot"]`.
  - Result before the last change: 8 conduits route; 0 clashes; 1/2" ≈ 121 m; 5 TOP boxes (downlights only); chase ≈ 43 m.
  - New `e42_conduit_check.py` (step 4, started): `_check_clear` (conduit ↔ conduit) and `_check_bends` (r ≥ rmin from the model, ≤ 360° per piece). Loader execs it.
  - **Blender disconnected** while running the check after the plate-corner change (not yet verified). Next: reconnect → build → run the checks → finish step 4 (boxes on the wall / lid clear, holes in brick only, chases, roof steel, wire per piece) → test_elec → a reviewer → save the .blend (back up first).
- **30 ต.ค. evening — after Blender was reopened.**
  - Plate slots: each slot has its own inset run line `PLK[room][k]` with rmin corners. A wider corner radius blocked the E2 over-crossing.
  - Climbs: the straight check covers their lead-in (`LEAD`). One descent in Bed1 had started on the corner arc.
  - **≤ 360° between boxes, the user chose "shared pull boxes"**: TOP 4×4 hubs on the plaster band. Each conduit passing goes through at its own height; circuits are not joined.
    - `_routes_wall` iterates: `_route_once` (hubs booked first as kind `hub`; only a straight run of slot ≤ 1, fully inside the hub's height, may pass) → `_hubs_needed` (the last straight ≥ 0.40 m before 360.5°, searched back from its far end, clear of device loops and the CU home runs) → repeat. Hubs are visit events, so the run stays on the band there.
    - After building, each piece passing a hub is split there (+2·slack per conductor).
    - A hub in a room entered over the plate needs 2·TR from the entry. The from_plate descent must lie between the entry and the first event (it had wrapped a lap).
    - Result: 3 rounds, 8 hubs (Living 5 at s 0.94 / 7.60 / 11.05 / 12.60 / 15.61; Bed1 2 at 4.74 / 8.12; Bed2 1 at 0.90), 34 pieces.
  - `e42_conduit_check.py` `selfcheck_conduit()` passes:
    - no clash;
    - r ≥ 102 mm everywhere (circumradius; points where two opposite bends meet are skipped);
    - ≤ 360° per piece;
    - no conduit passes through a box it doesn't enter.
  - Quantities now: 1/2" 119.7 m · 5 TOP 2×4 (downlights) + 8 TOP 4×4 (hubs) · chase 43.6 m · wire 1.5 189.8 / G1.5 33.0 / 2.5 164.9 / G2.5 101.3 / 4 63.0 / G10 3.9 m.
  - Next: a reviewer (running) → rest of step 4 (holes in brick only, chases, roof steel, wire per piece from the model; replace the old selfcheck_elec routing part) → rewrite test_elec → a test reviewer → back up and save the .blend → L2 / MAIN. e42_conduit.py is 1254 lines: split it (router / hubs / geometry).
- **30 ต.ค. — review round 2 fixed, then APPROVE.**
  - Link out of a box top leaves at +LK.
  - `_check_boxes` also reads the wall device boxes.
  - Linking two boxes: `link_sharp` holds both the geometry and its fit test; the linked boxes must be apart in height with a straight wall between them, otherwise two loops.
  - Every hub must be used.
  - Chase: one groove per looped device, plus the up chase of a box fed in the wall.
  - Removed: the drop branch and below_drop.
  - Now: 1/2" 119.7 m · 5 TOP 2×4 + 8 TOP 4×4 · chase 31.4 m · `selfcheck_conduit` passes (34 pieces, 29 boxes).
  - A test reviewer waits for the test_elec rewrite.
- **30 ต.ค. — step 4 checks (`e42_conduit_check.py`), read back from the model.**
  - New checks:
    - `_check_lids`: every TOP box's back is on a wall, plate or column, and nothing runs in front of its lid (0.30 m).
    - `_check_walls`: conduits go into a wall only through brick and its plaster, and touch no concrete tie, column (or its coat) or steel plate. A hole must be level, square through the wall and below 3.45; a chase must end in a box or the CU. Holes = EL_WallHoles. Chases match EL_Chase one to one; the taken-off length may be 0–2.5 cm longer, because the conduit enters the wall in its bend.
    - `_check_steel`: conduits keep their radius off the roof steel and the ceiling (frame, boards, wall angle, rods).
    - `_check_wire`: each piece's conductors come from the topology read off the model (box → next piece of the same id → devices, flex → downlight). The resulting lengths must equal EL_Wire_*. Every point is reached once from the CU. An unrouted circuit (L2) is named in the summary.
  - Fixes these checks found:
    - The home runs going south nicked column D3 (they set out onto the line past it). They now level off in the chase, then set out at ≤ 45°. The CU moved 5.00 → 5.10 (assumed) to give the room.
    - The hole into Bed2 at C2 went through the door-jamb tie. It now goes through the brick beside the tie, with 2 × 30° back onto the wall line.
    - A loop on the lowest level nicked the ceiling's wall angle. The band now starts 12 mm over the wall angle (`over_angle`).
    - A ceiling hanger rod stood 2.5 cm off the Living north wall, in the conduit band. In `e42_ceiling.py`, no hanger now sits within 0.12 m of a main's end (`wall_clear`). The ceiling suite still catches 19/19.
    - The router counted wire through the hubs' width. Wire is now each piece's length plus slack at both ends.
    - The home runs' chases above the CU were missing from the take-off. Each now has its own groove.
    - SW_Bed1 moved 5.70 → 5.75 (its loop grazed a tie). The hub keep-off from loops is now 0.35.
  - **Open (ask the user):** SW_Bath's chase is cut into the door-jamb tie, because there is no brick between the bath door and column D2 (the Bed1 door follows). It is listed in `CD["tie_chase"]` (4.27; 4.30 grazed D2's coat).
  - `selfcheck_elec` keeps the device checks and calls `selfcheck_conduit()`. The old router in `e42_elec.py` is deleted (1174 → 445 lines).
  - Now: 1/2" 119.4 m · 5 TOP 2×4 + 9 TOP 4×4 · 2 holes · 23 chases 39.7 m (the take-off says 39.9) · wire 1.5 188.5 / G1.5 32.5 / 2.5 164.1 / G2.5 100.4 / 4 61.4 / G10 3.9 m.
  - Mutations: 8/8 caught. Not yet covered: the lid-front check, and a hole that is not square or goes into the plate.
  - The .blend is not saved. Blender crashed once in a test (an IDProperty array reused after it was replaced) and was reopened and rebuilt.
  - A reviewer: round 1 APPROVE with 10 findings, all fixed except as noted below; the re-review is APPROVE.
    - Every conduit end must lie on its box surface (±2 mm).
    - Every piece must hang off the CU.
    - A chase may travel ≤ 0.30 m sideways in the wall.
    - A hole must be square, ≥ 0.999 along x or y.
    - The tie exception covers only SW_Bath's own chase height.
    - The lid prism is grown by each conduit's radius.
    - The `_xing` offset and the D3 set-out loop are guarded.
    - Flex must be ≤ 1.80 m and end on the downlight top.
    Mutations now catch 10/10.
  - Still open:
    - The D3 set-out runs level in the chase for ~0.13 m on each of 2 runs (~0.3 m in all). This is not in EL_Chase, because grooves are measured by height.
    - The "never alongside itself" read-back (spec §5) has not been ported to the band geometry yet.
- **30 ต.ค. — the user chose (ก): SW_Bath's chase is cut into the door-jamb tie** (`CD["tie_chase"]`).
  - test_elec rewritten. Part "model": 17/17, edits undone in place. Part "rebuild": 4/4, one mutation per call (`ONLY`).
  - The bend check now also rejects a mitred corner (more than 15° at one point; a sampled arc turns ≤ ~11°). Before this, a mitre between two long straights passed the circumradius test.
  - `selfcheck_elec` checks that every circuit has an earth.
  - Backed up to `E42_house.pre_st12conduit_20261030.blend`, then saved `E42_house.blend` (ceilings with `wall_clear` + the new ST12).
- **30 ต.ค. — a test reviewer round 1 said NEEDS-TESTS. All of it is fixed; a test reviewer now says SUFFICIENT and a reviewer (round 3) APPROVE.**
  - New checks:
    - `_check_takeoff` (runs last): conduit/flex lens = splines, `bends == 0`, `vlen` = the length over the ceilings, FlexConn = 2 per flex, chase length/count = its grooves.
    - `_check_on_walls`: every run over the ceiling is within 14 cm of a wall or column (the farthest legit one is 12.3 cm, the D3 offset). "Never alongside itself": the same id going opposite ways within 9 cm in plan for more than 0.30 m.
    - `_check_cu`: no box within 0.5 m of the CU.
    - Kink rule: a turn over 1° with both legs longer than 3 cm.
    - The tie exception applies only to SW_Bath's own pieces, at its chase height.
    - World transforms are applied.
  - It found a real bug: `vlen` (clips) counted the hub widths. The router now subtracts them.
  - test_elec: group a 20/20, b 14/14, c 17/17 (synthetic + controls), rebuild 4/4. Each mutation's undo is checked by a state hash.
  - Saved again.
  - Open (non-blocking):
    - a kink right at an arc end (R1);
    - "two conduits leave the CU" read-back (R2);
    - the chase-shape asserts (towards no box / neither hole nor chase) have no mutation (R3);
    - the tie 10 cm radius test (R4);
    - alongside across shared ids such as "L1" vs "L1+S1" (R5);
    - the 14 cm limit applies on plain walls too (R6);
    - the D3 level run is missing from chase (~0.3 m).

## Step 3b — L2 and MAIN (spec 30 ต.ค.: "ตามนั้น" + MAIN overhead)
Decided:
- The meter is on porch column A3 (6.0, 0.0).
- MAIN is THW 16 in a 1" conduit (rmin 146 mm), run **overhead**: up the column face → into the porch void → over the B2-B3 plate → along the Living east wall over the ceiling → down a chase into the CU top.
- No RCBO.

Geometry read from the model:
- **Porch void:**
  - x 3.115–6.115, y −0.115–1.385, ceiling 3.069.
  - Walls: the B2-B3 porch face (brick only above 2.5) and the A2-E2 east face.
  - The south (A2–A3) and east (A3–B3) sides are open. Only the plates AS_A1-A3 / AS_A3-E3 (3.45–3.55) span them, so runs there ride the plate band.
- **Eave void:**
  - x 6.115–6.783, y 0–7.5, soffit 3.069.
  - The east wall's outer plaster face is x 6.115. The A3-E3 plate's outer face is x 6.05, recessed 6.5 cm behind it.
- **L2 points** (two conduits from the CU, rule 8):
  - L2 north: SW_Kitchen (x1 5.55) loop → DL_Kitchen_2 / _1 boxes → DL_Back (eave, y 6.29).
  - L2 south: SW_Living (x1 1.75) loop → DL_Living_2 / _1 boxes → DL_Porch_2 / _1 (y 0.49, flex from the south plate ≈ 0.45 m).
- Next to B3 the wall is all concrete (column B3 + ties x 5.8–6.1), so no hole can go there.

Plan:
- (a) **Porch and eave lines.** The porch gets its plate line only (devices: TOP 2×4 on the plate band; a 2×4 fits). The eave gets its outer-face line on the east wall.
- (b) **L2 south.** Climb to the Living plate band on the east wall, go over the B2-B3 plate top at B3 (in line: the A3-E3 plate runs on), and continue on the porch plate line round A3 to the porch boxes.
- (c) **L2 north.** Living band → climb at the north-east → over the A3-E3 plate top heading east at y ≈ 7.4 (E3) → down onto the east wall's outer face in the eave → box → flex to DL_Back.
- (d) **MAIN.** Meter box on A3 → up the column face (clipped) → through the porch ceiling edge → the porch plate band → over B2-B3 → the Living east plate band → down to the plaster band near the CU → into the CU top through its own knockout.
- (e) **Checks.** `_check_on_walls` must accept plate-band runs over open sides (the plates are in the BVH). New mutations go into test_elec.
- **30 ต.ค. — 3b blocked on Living band capacity at the CU (asked the user).**
  - L2's living-room / kitchen points were tried as routes in 9 combinations:
    - separate L2-ccw / L2-cw;
    - S3+L2 + S2+L2-cw;
    - S2+L2 both ways + S3;
    - several height orders;
    - SW_Kitchen moved to 6.10 / 6.30.
    Every one hits "the wall band is full" on the east wall right by the CU, where 5 home runs set out north.
  - A 3-circuit share in 1/2" fails the fill test: S2+S3+L2 = 44 % > 40 %.
  - Kept from the attempt:
    - `CD["pending"]`, for points whose porch / eave legs are not routed yet;
    - dl_s keeping downlight boxes ≥ HOME + 0.25 + box/2 off the CU.
  - Scripts restored to the passing version; the model is rebuilt and unchanged.
- **30 ต.ค. late — 3b with 3/4" (the user's choice) is still blocked (asked the user again).**
  - Built:
    - per-size geometry (`GEO`): every conduit bends at the 3/4" radius 114 mm, and each books its own radius;
    - room / plate lines at 114 mm corners;
    - S2+S3+L2 in a 3/4" north, S2+L2 in a 1/2" south;
    - Bed1 in one 3/4" (A1+S1+L1, fill ≈ 25 %);
    - hubs keep off plate-climb exits.
    Moving points (assumed: SW_Kitchen 5.90, SW_Living 1.95, SO_Fridge 5.45, SO_Kitchen 3.65 / 4.05) let round 1 route.
  - Round 2 adds the pull boxes the 360° rule asks for. A 4×4 hub on the Living north wall (11.5 of the 15 cm band) + the kitchen downlight box (the flex reaches only from y 6.0–6.36 on the east wall) + 3 north conduits leave no height for the Bed1 conduit ("run (3.84, 7.49) free []").
  - The scripts and point positions are restored to the passing version.
- **30 ต.ค. night — 3b WIP checkpoint** (the project scripts are back at the passing version; the model was rebuilt and passes, same quantities).
  - **the user's decisions (to keep):**
    - 3/4" for 3 circuits: S2+S3+L2 north, plus Bed1 as A1+S1+L1.
    - A conduit only passing the living room rides the wall-plate band straight from the CU (`home_plate`).
  - **In the WIP:**
    - `GEO`: one bend radius of 114 mm for all sizes; each conduit books its own radius (`RC_OF`); lines and plate lines have 114 mm corners.
    - `route_size`, `home_plate` (Bed1).
    - Hubs are skipped as events for home-plate runs.
    - 2×4 pull boxes on the plate band (hub kind "plate"; the splitter handles both kinds).
    - dl_s keeps downlight boxes off the CU zone.
    - Point moves (assumed): SW_Kitchen 6.75 (past back door D3 5.75–6.55 + its tie), SW_Living 1.95, SO_Fridge 5.45, SO_Kitchen 3.65 / 5.20 (either side of window W3 3.90–5.10).
  - **Got as far as:** a full route once (round 1 + plate pull boxes), which then failed on the openings (now fixed by the moves). After that, L1+H1 > 360° with no hub spot. With smaller hub keep-offs, the DL_Kitchen_1 box (on the east wall by the CU: the flex reaches only y 5.96–6.36) has no height.
  - **Root cause:** band hubs are events for every run that passes them, so a run up on the plate comes down to each one (+120°) and needs more hubs.
  - **Next design:**
    1. A run up on the plate passes band hubs without stopping and takes its own 2×4 plate pull boxes (`_hubs_needed`: a plate straight gives a "plate" candidate for any route).
    2. Apply `home_plate` to L1+H1 as well (the user said Bed1 and bath); it comes down before SW_Bath.
    3. Then the porch / eave legs and MAIN (plan above).
- **30 ต.ค. night — 3b part 1 done: L2's living-room / kitchen points routed (reviewer APPROVE after one fix round; promoted to `scripts/`; .blend saved after the backup `E42_house.pre_l2_20261030.blend`; the old scripts are in `scripts/_pre_l2_20261030/`).**
  - **Routes:**
    - S2+S3+L2 (3/4") north: SO_Fridge, SO_Living_2, SO_Kitchen_1/2, SW_Kitchen, DL_Kitchen_1/2.
    - S2+L2 (1/2") south: SO_Living_1, SW_Living, DL_Living_1/2.
    - Bed1: A1+S1+L1 (3/4") on the plate band from the CU (`home_plate`).
  - **What made it fit:**
    - Pull boxes for runs up on the plate are 2×4s on the plate, owned by one conduit (booked "pbox").
    - Band 4×4 hubs are events only where the run is on the plaster band.
    - In Living, only home-plate runs use the plate.
    - Downlight boxes keep off the CU zone and sit only on wall-parallel stretches.
    - `dl_face` pins DL_Living_1's box to the east face, so SW_Living (1.75, by the south-east corner) ends its conduit.
    - Chase tops are taken where the conduit really goes into the wall (interpolated).
  - **Points moved (assumed, tell the user):** SW_Kitchen 5.55 → 6.75 (past back door D3 + its tie), SO_Kitchen_1/2 3.35 / 3.70 → 3.65 / 5.30 (either side of window W3 + its tie), SO_Fridge 5.53 → 5.45.
  - **Now:** 3/4" 48.0 m + 1/2" 63.0 m, flex 9.1 m, 31 boxes, 2 holes, 24 chases 41.7 m. Wire: 1.5 313.8 / G1.5 32.0 / 2.5 192.2 / G2.5 95.3 / 4 60.6 / G10 3.9.
  - **Tests:** test_elec 52 (a 21, b 14, c 17) + rebuild 3. The runner mutation is now a model edit.
  - **Next (part 2):**
    - **Porch:** the porch lights are switched by SW_Living's gang 2. SW_Living must end its conduit (corner B3), so the porch needs a forced branch (`tee_dev` at DL_Living_1's box) and an "into" crossing (through the wall the run is on: B2-B3 brick x 3.2–5.8 above 2.5, about 300° of bends) or an over-plate crossing from a branch child.
    - **Eave:** DL_Back works the same way from DL_Kitchen_1's box past SW_Kitchen, through the east wall near E3 onto its outer face.
    - **New rooms:** Porch and Eave (lines / levels; porch DL boxes pinned to the B2-B3 porch face, DL_Back to the eave's x0 face).
    - **MAIN** after that.
- **31 ต.ค. — 3b part 2 done: porch + back-eave lights (reviewer APPROVE twice; promoted; old scripts in `scripts/_pre_l2p2_20261031/`; .blend saved after the backup `E42_house.pre_l2p2_20261031.blend`; test suite copied to `scripts/test_elec.py`).**
  - **the user's choices:**
    - Porch lights get their own switch SW_Porch; SW_Living is now 1 gang.
    - SW_Porch sits in the Living at its south-west corner: west wall 1.7825, between the straight its loop needs past the corner and the Bed2 door's jamb tie. (The porch's own west wall was too short for a 360° pull box.)
  - **How they're fed:**
    - The lights outside a wall (DL_Back in the eave, DL_Porch_1/2 in the porch) have their 2×4 box on the Living wall. The flex goes straight through the brick (one hole each), out over the soffit / ceiling, to the fitting.
    - DL_Back is on S2+S3+L2 (east wall).
    - The porch boxes are pinned to the Living south wall (`dl_face` 1) on the Bed2 conduit, now L1+S1+L2 (3/4"): porch boxes → SW_Porch → C2 into Bed2.
  - **Other changes:**
    - SW_Bed2 moved 1.80 → 1.62: it was back to back with SW_Porch in the 9 cm wall.
    - Hub keep-off from loops: margin 0.10.
  - **Checks:**
    - The tie test uses the true distance to the box.
    - Flex now goes into the walls check (holes), the clash check and the steel / ceiling check (all but the drop through its cut-out, by plan distance).
    - Through-wall flex asserts that it comes out over its own soffit.
  - **Tried and dropped:**
    - "into" (through the wall it runs along, about 300°) to an Eave / Porch room: the 4×4 tee was too tall for the busy east wall, and 300° plus a loop goes past 360° with no room for a pull box.
    - A forced branch along the same wall (LivingS): it crowded the south side.
  - **Now:** 35 pieces, 34 boxes (TOP 2×4 14 incl. 2 on the plate, 4×4 3), 5 holes, 25 chases 43.4 m. 3/4" 81.7 m + 1/2" 32.2 m, flex 11.7 m. Wire 1.5 341.1 / G1.5 36.3 / 2.5 202.9 / G2.5 100.2 / 4 60.6 / G10 3.9.
  - **Tests:** test_elec a 21, b 17, c 17, rebuild 3 — all caught.
  - **Next:** MAIN (meter on column A3 → overhead in 1" → CU top), per the 3b plan.
- **31 ต.ค. — 3b part 3 done: MAIN (the user: overhead, the drop down the outside wall). ST12 conduit COMPLETE.**
  - Reviewer APPROVE twice. Promoted, with the new `scripts/e42_conduit_main.py`. The old scripts are in `scripts/_pre_main_20261031/`. The .blend is saved after the backup `E42_house.pre_main_20261031.blend`.
  - **Route:** THW 16 L+N in 1" (r 146 mm, more than the 90 mm wall).
    - Meter board on column A3's east face (assumed).
    - Riser at (6.18, −0.03): past the soffit's edge runner, between two cross runners, through the soffit board (hole 1).
    - At z 3.42 north in the east eave void, along the east wall's outer face (under the plate, near it past the open porch side).
    - Down through the soffit board at the CU's y (hole 2). A shallow 2-bend offset onto the wall, then plumb into a TOP 4×4 on the outer face behind the CU.
    - A straight piece through the wall into the CU's back. The CU is surface-mounted; the GND comment calling it "flush" is stale.
  - **Take-off:** EC1 7.8 m (clips along all of its outdoor run), wire 16 = 18.1 m, EL_Meter 1, EL_SoffitHoles 2 (counted from the model), one more wall hole (6), one more 4×4 (4).
  - **Checks:**
    - The board exemption applies only within r + 2 cm of the 2 holes.
    - `_check_cu` skips boxes behind the CU's wall.
    - Wire 16 is read back.
    - Mutations: wire 16 short; riser tight on the column (soffit runner); MAIN through the board elsewhere.
    - test_elec: a 22, b 19, c 17, rebuild 3.
  - **ST12 final:**
    - Conduit 3/4" 81.7 m, 1/2" 32.2 m, 1" 7.8 m, flex 11.7 m.
    - Boxes: TOP 2×4 14 (2 on the plate) + 4×4 4; flush 2×4 17.
    - Holes 6 + soffit 2; chases 25, 43.4 m.
    - Wire 1.5 341.1 / G1.5 36.3 / 2.5 202.9 / G2.5 100.2 / 4 60.6 / 16 18.1 / G10 3.9.
  - **Points assumed or moved (to confirm with the user):** CU 5.10, SW_Kitchen 6.75, SO_Kitchen 3.65 / 5.30, SO_Fridge 5.45, SW_Porch 1.7825, SW_Bed2 1.62, SW_Bed1 5.75, the meter board on A3.
  - **Still open:**
    - The D3 level run is missing from chase (~0.3 m).
    - Test gaps R1–R6.
    - e42_conduit.py is >1300 lines (split it).

## 31 ต.ค. — open items closed

- **Level runs in the chase.** Every CU home run levels in its chase for 7–12 cm, not only D3. These runs are now in the take-off: the router clips them at the real plaster face, and the check sums its float32 read-back with "level" meaning |dz| < 2e-6. Chases total 25 runs, 43.9 m (was 43.4).
- **Test gaps R1–R6** are closed by synthetic tests in group c, which went from 17 to 27. Three of them found real holes in the checks, now fixed:
  - a kink where an arc meets a straight (R1);
  - one circuit doubling back across conduit ids (R5);
  - a graze into the plaster that counted as a hole (R3).
- **e42_conduit.py split** into `e42_conduit_geom.py` (CD + geometry), `e42_conduit.py` (tables + entry) and `e42_conduit_route.py` (`_route_once`). The code is unchanged, which a per-definition comparison confirms.
- **Loader name clash fixed.** The conduit's `_arc` is now `_arc_pts`. `scripts/e42_load.py` refuses any name defined twice.
- **Downlights** are visible from the rooms. The trim is 2 mm under the ceiling face with an emissive lens.

## 31 ต.ค. — junction boxes at the drops (the user's request)

- **the user's choices:** a junction box at every drop, wires looped through (no joints), and the drop into the end of a 4×4. A drop out of the box's bottom does not fit: the void is 17 cm and a gooseneck needs ~13 cm.
- **Where they fit.** Boxes go where the planner finds room (the user: "ใส่กล่องจุดที่มีที่ ที่เหลือวนท่อเดิม").
  - Boxed: Bed2 (SW_Bed2, SO_Bed2_1, SO_Bed2_2) and the bath (HT_Bath).
  - Looped: the living room (9 devices, 5 home runs along its walls) and Bed1, where a 360° plate pull box forced a detour that clashed.
- **Now:** 3/4" 76.7 m · 1/2" 31.2 m · TOP 2×4 13 · 4×4 6 · chases 25, 43.7 m · wire 1.5 308.4 / G1.5 33.1 / 2.5 205.5 / G2.5 101.4 / 4 60.4 / 16 18.1 / G10 3.9.
- **Open:**
  - Bed1 boxes need a smarter pull-box placement.
  - The living room could get boxes if its passing circuits moved up onto the wall plate.
- **Fixed: the spacing guard never fired.** Two wall devices' junction boxes must be ≥ JB + 1 cm apart along the run (JB 0.303 m), unless the second is fed from the first in the wall. The old exemption was "gap < 2·LOOP + 3 cm" (0.366 m), wider than JB + 1 cm, so every gap passed. The guard now exempts only a pair the router really links (`links()`, shared with walk_visit: < 2·LOOP + 3 cm, straight wall between, and the in-wall bend fits; a fed device links on to none). Tests in test_elec group c: a level pair 22 cm apart → "too close"; the same pair 90 cm apart in height passes (linked); SO_Bed2_2 50 cm toward the way in → "would start before". The old guard misses the first. The house routes as before (same rooms boxed, same lengths).
