# ST12 electrical: devices, circuits, conduit, wire

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
  - **the user's rules:**
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
