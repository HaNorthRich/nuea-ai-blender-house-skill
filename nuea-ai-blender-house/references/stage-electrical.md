# ST12 electrical: devices, circuits, conduit, wire

*SS-02's code is not in this repo; its file names (`ss02_*.py`) are from that job.*

Read when modelling lights, switches, sockets, the consumer unit, conduit, wire or the service main.

## ไฟฟ้า + ดวงโคม (ST12, spec 30 ต.ค.; `examples/e42/scripts/e42_elec.py`)

- **Ask first:**
  - switch/socket grade (CHANG Y economy vs Panasonic Wide);
  - consumer unit;
  - AC count and rooms (start from TCL T-VoxIN13S 12,283 BTU);
  - wiring method;
  - meter location;
  - RCBO.
  - Wire by load (the user): THW 1.5 lights, 2.5 sockets, 4 heater + AC, 16 main.
- **Points from a table** placed against the rooms read from the model (faces x0/x1/y0/y1 + along; downlights by fractions).
  - Move downlights into the gap between the C-line runners. Read the runner lines from `CL_<room>_Runners`.
  - Wall devices on the finished face (on the tile face in the bath and the splash).
- **Conduit = the user's rules, read back from the model** (E42 `e42_conduit.py` router + `e42_conduit_check.py` +
  `e42_conduit_main.py`; spec `ST12_conduit_spec.md`, 30–31 ต.ค.). Lane rows, walk-order chains, CROSS points and
  "≤ 4 bends" were the rejected first design.
  - **The user's rules:**
    - Conduits are clipped on the wall faces over the ceiling, stacked by height. Measure the bands first: E42 plaster band 3.29–3.45, steel wall plate 3.45–3.55.
    - No circuit runs back alongside itself.
    - Boxes sit on the wall, lid to the room, nothing in front of a lid. Real TOP 2×4 / 4×4 products, never entered through the lid.
    - Rigid PVC is bent, never mitred: r ≥ 102 (1/2") / 114 (3/4") / 146 (1") mm, ≤ 360° of bends between boxes.
    - Walls are crossed near a corner, square, through **brick only**: never a tie column (เสาเอ็น at every jamb and junction), a column or the steel plate.
    - Drops to devices go down vertical chases, plastered over. A wall device is **looped**: the run turns into the wall, down to the box top, and back up beside itself (≈ 110° each way).
    - A circuit going both ways leaves the CU as two conduits; no box in front of the CU.
    - Flex (corrugated) into downlights, ≤ 1.8 m.
    - A designer's ROUTES table, one conduit per room visited.
  - **Geometry decides more than rules do:**
    - A 1" bend (146 mm) is wider than the 90 mm wall: it can't turn in a wall or chase. The user chose overhead with the drop down the outside wall into a TOP 4×4 there, straight through into the CU's back.
    - A loop needs straight wall ±LOOP (≈ 0.17 m at 114 mm) and must clear the tie of the nearest jamb. Corner columns chamfer the line about 0.28 m.
    - Loops on one run need ≥ 2·LOOP + 3 cm between them, unless they are linked in the wall at different heights.
    - A switch at a room corner (E42 SW_Living, 27 cm from it) can't carry on: it must end its conduit.
    - Two flush boxes back to back in a 9 cm wall fill it: keep switches either side ≥ 1 box apart.
    - **Check every device position against the jamb ties and openings before routing.** A move of a few cm landed a switch on column D2, in the Bed1 doorway, or at a window sill.
  - **When the band is full** (it was, at the E42 CU), the user's fixes in order:
    1. Two circuits share one conduit (fill ≤ 40 %, THW OD IEC 60227 max).
    2. Three share a 3/4". Bend every conduit at the largest radius so any size can take any route; book each conduit's own radius.
    3. Conduits that only pass a room ride the steel wall-plate band straight from the CU (`home_plate`).
    4. Pull boxes: a shared 4×4 on the plaster band (the run passes through each level). A run up on the plate never comes down to one: it gets its own 2×4 on the plate, booked full-height for that conduit only.
    - Keep downlight boxes off the CU's home-run zone and only on wall-parallel stretches. Pin a box to a face (`dl_face`) where the nearest wall is the wrong one.
    - A light outside a wall (porch, eave): its box on the inside face, the flex straight through the brick (one hole).
    - Ask the user before moving a switch: the porch got its own switch indoors at the SW corner, and the main went over and down the outside wall.
  - **Router debugging:**
    - The reported error is the "nearest miss". Read every attempt's error (`CD["_errs"]`) and the `_Levels.used` bands to see what really blocks.
    - Try height orders (`CD["order"]`) before changing geometry.
    - Moving an event-list merge later in a function leaves stale indices (`k_ex`): look items up by kind or identity.
  - **Keep work alive:**
    - Unsaved builds died twice: Blender crashed, then the file was reopened. Back up, then save the .blend after each reviewed milestone.
    - Keep work-in-progress copies in the project folder (e.g. `scripts/_wip/`, with its own loader), never only in the scratchpad.
    - Never write back an IDProperty array read before the property was replaced: Blender crashes. Copy it with `list()` first.
    - The test suite re-execs every module. Anything a check needs (e.g. MAIN's soffit holes) must come from parameters and the model, never from state set during the build.
    - Exempt a check only where the exemption is meant to apply. MAIN's soffit-board exemption covered its whole length until it was cut to a disc round each of its 2 holes.
- **Lighting conductors per piece come from who switches what** (a CTL table: light → switch, gang). Counting by the kind of the next point under-counted THW 1.5.
  - N if a light lies ahead, L if a switch lies ahead.
  - One per gang whose switch and light lie on opposite sides of the piece.
  - One earth sized for the largest circuit, none to switches only.
- **Count off the model:**
  - conduit per size (ตราช้าง 4 m pieces), clips only over the ceilings (`vlen`), no elbows;
  - wire = Σ pieces × conductors + 30 cm slack per end;
  - chase metres (a loop's down + up share one groove; each CU home run its own);
  - holes (flex holes too);
  - boxes, plates, breakers.
  - Under half a roll, buy THW by the metre.
- **The selfcheck reads the model, never the router's numbers.** The take-off rows themselves are checked too: `lens`, `vlen`, `bends`, chase `length` and `count`. Each check below was missing until a test exposed it.
  - box backs on a wall / plate / column; lid prism clear (grown by each run's radius);
  - in-wall stretches only in brick, by the true distance to tie boxes; holes level and square; a chase ends in a box, ≤ 0.30 m sideways;
  - steel / ceiling clearance for rigid runs and flex, except the flex's drop through its cut-out (skip it by plan distance; a height cut skipped the whole level leg);
  - bends: circumradius and a kink rule (turn > 1° with both legs > 3 cm = mitred);
  - on the wall ≤ 14 cm; never alongside itself (same id, opposite ways, in plan);
  - wire topology: box → the next piece of the same id → devices; every point reached once from the CU.
  - Mutation suite: each mutation must hit its own message. Undo is verified by a state hash. Synthetic runs go straight into one check, with controls that must pass. Rebuild cases run one per call.

## Seen from the room, measured right (31 ต.ค.)

- **A downlight's trim hangs under the ceiling.** Its top sits `below` (2 mm) under the board face, so it clears
  both paint coats (1.6 mm). It carries an emissive lens (no take-off row) and a body up through the 150 mm cut-out.
  The selfcheck reads the trim top against the ceiling face and finds a lens under every ring. A trim built upward
  from the board face sat inside the board and behind the paint, so the user saw no lights from inside.
- **Every CU home run bends level in its chase** (7–12 cm), not only the D3 set-out, and that level run is grooved
  too. Both sides measure it, independently:
  - The take-off: the router clips each level piece of its path at the wall's real plaster face (from `_wlines`,
    not the run line, which stands `dc` off it).
  - The check: it sums level samples inside the wall solids. The model is read back as float32, so "level" is
    |dz| < 2e-6, below a bend's last 2 mm rise of about 2e-5.
- **Rules the first suite let through** (R1–R6, closed with synthetic runs):
  - a kink right where an arc meets a straight: a tangent join turns at most chord/(2·rmin);
  - one circuit doubling back across conduit ids: group by circuit (`"L1"` and `"L1+S1"` both carry L1);
  - a hole that only grazes the plaster: a hole goes through the whole wall thickness;
  - the 10 cm tie radius;
  - the 14 cm limit, tested under the wall plate (the plate stands 7.5 cm proud: 15 cm off the plaster is 9 cm
    off the plate);
  - two conduits leaving the CU.

## Junction boxes at the drops (31 ต.ค.)

- **The rule** (the user's practice):
  - Every wall device gets a TOP 4×4 junction box on its run over the ceiling, just behind the device.
  - The run goes in one end and on out of the far end.
  - The drop leaves the far end's other knockout and dives into the wall the way a loop's down leg does, then goes
    straight down its chase onto the device box. It takes the upper knockout when the box fits under the wall
    plate, else the lower one.
  - The wires loop through, with no joints. Only the device's own circuits go down, and they come back up when
    their circuit goes on. A drop is 3/4" when 1/2" fills past 40 %.
- **Measure the void before promising a box.** The void from ceiling angle to wall plate was 17 cm. A box beside
  the wall can't take its drop out of its bottom: a gooseneck back into the chase needs ~13 cm of height. So the
  drop leaves the box's end.
- **A 4×4 is 11.5 cm tall in that 17 cm void, so it blocks circuits passing the same spot.**
  - The planner books each box and its drop as height bands.
  - A room where routing finds no height, or whose pieces clash, keeps its devices looped (`CD["jb_off"]`).
  - Everything is routed again, then each room is retried.
  - E42 result: Bed2 and the bath have boxes. The living room (9 devices, 5 home runs along its walls) and Bed1 (a
    360° pull box there forced a detour) stay looped.
- **The rooms that stay looped use their old clearances** (reach, downlight-box spacing, hub keep-off). Using the
  box clearances everywhere moved geometry in rooms that never got a box.

## SS-02 devices only (4 พ.ย.; `ss02_elec.py`)

- When the user has not chosen the wiring method, grade, CU or AC, build the devices from the plans and list those questions. Don't route conduit on assumptions.
- **Read the symbols from the sheet's vectors.** E-25 and E-26 are at A-04's scale (K 37.795 pt/m at 1:75). Only the origin moves, so find it from the grid lines. The sizes tell the symbols apart: a 0.22 square around a 0.132 one is the surface downlight, 0.16 rings are switches, 0.198 squares are sockets.
- **A symbol stands a few cm off its wall.** Put the device on the nearest finished face found by rays along ±x and ±y. Check the wall side against a table typed in the check, so a socket that jumps to the next wall fails.
- A plate goes on the last paint coat (primer + 2 coats = 3 coat steps out), or on the tile.
- **Helper names:** the skill's `cpac_caps.py`, exec'd inside `ss02_roof_cover.py`, defines `_plate`. The loader's duplicate guard can't see it, and a `_plate` of your own breaks the roof caps.

## SS-02 conduit (4 พ.ย.; `ss02_conduit_routes.py` tables, `ss02_conduit.py` build, `ss02_conduit_check.py` + `ss02_conduit_net.py` check, `test_st12b.py`)

A designer's table of pieces (sharp 3D paths between nodes), every corner filleted at the radius. No router: in a 95 m² house one was not worth writing.

- **Use the conduit the store sells, before routing.** Thai Watsadu's 1/2" is 20 mm (EAGLE EG20 / HACO EC20, wall 1.8, 2.90 m lengths), not
  16 mm; boxes HACO Deco W111A 12 × 7 × 3.5 cm; flex HACO FX-20; clips HACO CC20 every 0.9 m (NEC 352.30). Moving 16 → 20 mm after routing
  cost a full re-route (steps, lanes, humps, every test coordinate). The store's product pages first, with links; then the tables.
- **Measure the real void before planning lanes.**
  - The plaster stops at the ceiling, and the board, frame and wool stop at the plaster line.
  - So above the ceiling there is a 17.5 mm gap along the bare brick. A 20 mm conduit runs on saddles 11 mm off the brick, over the wool.
  - In the wall it is chased 3.5 mm into the brick (centre 6.5 mm off it) so the plaster still covers it; it steps from groove to saddle
    between 2 cm under and 2.5 cm over the plaster top (a 4.5 mm offset), through a notch in the ceiling's edge.
  - Lanes are 3.636 and 3.672 (36 mm apart) under the 3.70 wall top; humps over another run at ≥ 3.716.
  - A 25 mm does not fit the gap. Split circuits so every chase and run is 1/2" (20 mm).
- **Boxes on the band's top, their knockouts are lanes.**
  - TOP 2×4 at 3.62–3.69, knockouts at 3.636 and 3.672.
  - Traffic passes under a box at ≤ 3.60, or through it: two conduits share one box, one per knockout. Swap knockouts inside a box so the one that drops next is the lower one.
- **Ordering rules that decide everything at a load centre:**
  - A level run passing over a riser must be above that riser's whole bend. Risers turning one way take lanes that fall the further out they stand.
  - CU home runs run level in the chase from their slot to a riser by the corner. Riser order equals slot order, and level heights rise with it.
  - A device drop 4 cm from the CU blocks every home run (SW_B2). Move the device (say why in the spec) rather than fight it.
- **Over the top of a free-top wall:**
  - A riser bending over it must climb past the wall top first, or its bend cuts the band's corner.
  - Bends side by side at the same radius always cross. Nest them at a bigger radius round the same centre, or keep them in planes ≥ 2 cm apart.
- **A device near a room corner can't be looped after the corner bend.** It needs ≥ r + r + leg from the face; the sockets here needed 7–10 cm. Make it a run's end, or move it and flag it.
- **Wire per piece needs one tree per circuit.**
  - Shared conduits make the box graph cyclic.
  - Book each piece's circuits in the table. A circuit that splits at a junction box gets branch ids (L1k, L1b) on one breaker.
- **Flex:**
  - Leave the box's bottom 4 cm off the wall, in front of the conduits under it. Lie on the C-line under the wool.
  - Enter the light's top at a point clear of the frame (≤ 6 cm off centre).
  - In a bath, step out over the cold-water header first.
- **One breaker split into branches** (L1k, L1b, so each forms a tree) must share its L and N where the branches ride together.
  - Map branches to breakers in the builder and restate the map in the checker; else the trunk books two L/N sets and a checker copying the split can't see it (a code review caught it).
- **Checker lessons:**
  - A bend's radius from three samples: neither the chord nor the shorter leg works.
    - The chord misses a chamfer. The shorter leg reads two good bends 4 mm apart as R 0.05.
    - Use curvature over a window: the turns within 3 cm either side, over the length they own (each leg capped at 3 cm). It is exact on arcs, and a 2-mitre chamfer fails.
  - Under the ceiling a chased point must lie within the plaster depth of its wall: a run exposed in the room in front of the paint otherwise passes.
  - A stretch over the wall tops must actually cross a wall (its plan line hits brick or concrete), not only be short.
  - Read the take-off back from the meshes (grooves per end run, holes as back-to-back ends), and assert the build's numbers equal it.
  - A synthetic case's miss path must raise a tag the suite doesn't expect ([synthetic-miss]).
  - Clearance by distance only: the wall slices' normals don't all face out, and 1 cm samples can't enter a solid unseen.
  - An "on the wall" limit needs its search reach longer than the limit. A 5 cm reach let a run 30 cm out pass.
  - Tell bends from straights by segment length (arcs sampled at 1.5 cm). The point-next-to-a-bend test let a slanting chase pass.
  - Synthetic cases with controls: an angled box entry, a run through a box, a lid blocked, running back alongside itself.
- **Wire slack where a conductor ends or is spliced (15 cm), none where it passes a box unbroken (NEC 300.14).** E42's 30 cm at every piece end
  over-counted 15–20 %.
- **Outdoor and the lower carport roof (4 พ.ย.; the user: "วิเคราะห์และวางตำแหน่งให้เลย"):**
  - A carport roof below the house ceiling: cross the dividing wall with a chase down the room face and ONE bend through the brick into the
    carport's void (a hole). A box on the far face can't take it: the bend needs its radius (10.2 cm) of wall depth to come out square.
  - To a device on the outside face of the wall that carries the ceiling (pump on L1, carport socket on L2K): an S through the wall's top,
    two ~52° bends with 5 mm between, all of it inside the brick, into a chase down the outside face. Book it as a hole.
  - Over the carport ceiling there are no walls: fix the boxes to the steel (posts' and rafters' side faces at web height, each box at its
    own height) and keep runs within 0.20 m of the steel, clipped at each rafter. A spine along the posts' faces goes in at one end of each
    post's box and out the other. A box entered and left at the same end doubles the circuit back alongside itself.
  - The carport's walls stay plastered above its ceiling (they are the house's outside): check plaster in that void too.
  - A device whose chase would cut a ground beam (under the house floor, on the plinth) goes up onto the brick: SO_CARPORT +0.35 → +1.20.
  - A light right under its box (boxes beside the rafters over the lights): drop the flex straight down. Else move the drop within the
    light's top until it is two bend radii from the box.
  - The checker learns each of these as a rule plus a mutation: holes on bends only and as many as booked, steel supports, outside plaster.
  - Give the checker its own table of which wall each hole goes through, or it only echoes the count the builder booked.
  - Tie an exception to the sample next to the hole, not to "this piece has a hole": the second form quietly relaxed every chase on the piece.
- **Headless loop when the live Blender has another file open:**
  - Build a base once with `build_all.py` and its output set to `<scratchpad>/base.blend` (`E42_OUT` in the example's `build_all.py`).
  - Then each iteration runs only `build_elec(); build_conduit()` on it (≈ 30 s).
  - Look with a Workbench top render: an ortho camera whose clip start cuts at the void.
