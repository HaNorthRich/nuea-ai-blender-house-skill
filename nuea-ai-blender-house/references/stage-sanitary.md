# ST16–ST18 sanitary pipes, sanitary ware, counters, and the BOQ leftovers

*SS-02's code is not in this repo; its file names (`ss02_*.py`) are from that job.*

Read when you model water supply, soil, waste and vent pipes, septic tanks, grease traps, manholes, water tanks, pumps, sanitary ware, counters, termite pipes, skirting, flashing or ceiling hatches.
Worked out on SS-02 (4 พ.ย. 69). Code lives in `scripts/ss02_sanitary*.py`, `ss02_fixtures*.py` and `ss02_extras*.py`, with suites in `test_st16/17/18.py`.

## Read the drawings first

- **Plumbing sheets**
  - SN-27 gives the pipe classes: water PVC 13.5, soil/waste/vent PVC 8.5.
  - SN-28 is the water plan, SN-29 the drainage plan.
  - SN-30/31 give tank and pit details. They are NTS: take sizes from the maker or the 1:20 details.
- **Bath sheets**
  - A-12 lists the fittings in 13 items and says "Stop Valve ทุกจุด".
  - A-13 gives the real x of every fixture along the wall, and the heights. Prefer A-13 over the plumbing plan's vector points: it is dimensioned.
- **Read pipe lines from vectors.** A plumbing sheet shares the architectural plan's scale.
  - The pipes are the segments that are in SN-28/29 but not in the base plan (E-25).
  - Calibrate each sheet's origin on the grid lines.
  - Dash-dot lines (sw 9) are water. Dashed lines are waste. Solid lines are soil.
- **The schematic plan conflicts with itself and with the structure.** Expect it, and list every move in the spec. On SS-02:
  - The drawn drain lines pass through the septic tank.
  - The grease trap sits on the effluent line, but it has 2" nozzles on a 4" line.
  - Floor drains land on the bath slab's ledge beams.
  - The 1" main runs 7–12 cm outside the plot.
  - The kitchen branch runs through a stub.
  - The two WC outlets are drawn at different distances from the wall.
- **Check the template.** The BOQ template lists: soil 4" + fittings + flexible joint + FCO · waste 2" + P-trap · vent 2" + AAV · water 1", 3/4", 1/2" + gate valves · kitchen waste 2" · septic · water tank · pump · asbestos-cement pipe · garden tap. Each must come from the model or go to the owner as a question.

## Route and level

- **Bury horizontal runs, even under a suspended floor.** Ground beams often sit on a brick plinth (SS-02 PB_Brick, 0–0.20), so a pipe hung under the slab (A-12's hanger detail) would have to cut a beam or the brick.
  - Buried runs pass under the plinth.
  - Risers come up through the crawl space and the floor.
  - Water: centre at −0.30. Every buried pipe has ≥ 0.10 cover.
- **Design drain levels from the outlet upstream.** Fix the public outlet's level, then manhole floors at their outlet's invert, then each run's z from where it joins (`_sn_graded(plan, z_end, slope)`).
  - A long kitchen line (SS-02: 20.8 m at 1:100) sets how deep the grease trap must sit. Grade it before you choose tank levels.
  - Slopes: 4" and 8" at 1:200 (SN-31); 2" at 1:100 (assumed).
- **A tee is a vertex of the run it joins.** Split the main at every branch point, or the read-back sees a pipe end on another pipe's middle.
- **Bath supply over the ceiling, drops in the wall.**
  - Run a header in the void above the bath ceilings, over the ceiling insulation, which reaches 3.306 on SS-02.
  - From each fixture x, a short jog into a chase in the shared wall, down to the fixture height, then a stub out through the tile, 2 cm proud of it.
  - Wall plaster is 17.5 mm and a 1/2" pipe is 18 mm. Centre the chase in the plaster: the pipe then just touches the brick (and its concrete bands) and the ceiling's edge.
  - A 0.5 mm-short tube in the check treats that contact as contact, not a clash.
- **WC outlet = finished wall + rough-in.** SS-02 uses 305 mm. With that, lay the bath waste line clear of the WC riser and of the ledge beam under the slab edge.
- **Measure wall faces from the model, never from the bbox printout.** Faces sit at .x175 (6.2175 / 6.3175). A 0.5 mm rounding error put a chase into a wall's tie band.
- **The vent:**
  - It stands just outside the eave, 0.15 off it.
  - Its top clears every roof point within 0.5 m by 0.15. Ray-cast a 5 cm grid on the roof; vertex maxima under-read.
  - Nothing may be above it.
- **Valves and parts:** gate valves and check valves where the water plan draws them, a P-trap at each basin/sink riser top, an AAV over it under the counter, an FCO at the soil corner up to grade, a flexible joint where each soil line leaves the house line.

## Structures

- **Tanks and pits:**
  - Place each at its symbol centre, ±1 cm.
  - Take sizes from the drawing symbol, or from the maker when the symbol is a block.
  - Septic: tank top below grade, lid riser to grade.
  - Manholes: base, four walls, cover at grade.
  - Grease trap: buried deep enough for the kitchen line's fall.
- **Pads must not cut the house.** A square 1.10 pad under a Ø0.99 tank cut the NW wall corner by 2 cm. A round pad cleared it. Only an exact overlap check found it.
- **Keep effluent and grey water separate into the manhole.** A 2" grease trap can't sit on a 4" line. SS-02 moved the trap 0.27 m west so the effluent passes beside it, and each enters MH1 on its own.

## Build

- One mesh per (system, size). Each straight segment is a closed 12-sided tube: 24 vertices, 14 faces.
  - Assert every segment is longer than its OD, so the read-back finds the axis from the longest extent.
- Fittings are boxes at the nodes, by degree and turn:
  - 2 and turning: an elbow. 3: a tee.
  - 2, straight, two sizes: a reducer. 2, straight, one size: refused.
  - A node with two sizes is keyed by both, e.g. `CW_34x12_elbow`, "ข้อโค้ง 90° ลด 3/4 × 1/2".
- Devices are boxes centred on their pipe point, with names and counts in mesh props.

## Check (read back, never trust the tables)

- **Read the pipes back.** Rings are 12 + 12 vertices; their means are the ends and the radius gives the bore. Merge ends within 1 mm into nodes. Refuse any end lying on another pipe's middle.
- **Free ends:**
  - The set and count per system must equal the drawings' (`DIM_SN_END_COUNT`).
  - An end on a structure must sit on its surface (BVH `find_nearest` ≤ 2 mm). A bbox label accepts ends that stop in the soil.
  - A manhole end must also open into the pit's inner plan.
- **Grading:**
  - Walk each drain network from its outlet (a priority list per system: downstream structure first).
  - No segment runs uphill. Level segments meet the size's minimum slope.
  - Return in/out roles per structure for the nozzle checks: septic in on the inflow side and higher than out; trap heights by role; manhole outlet invert on the floor, no inlet below it.
- **Clashes by exact BVH overlap, not point sampling.**
  - Build slim tubes (r − 0.5 mm) from the read-back segments.
  - Overlap them with three solid groups:
    - hard: structure, carport slab, units, trim, roof, ceilings, devices, steps, plinth, wall concrete;
    - walls: brick, plaster, wall tile, paint. Allowed only for a riser in the chase window, or a level segment ≤ 0.25 m (a sleeve);
    - floors: allowed for risers only.
  - Point sampling at 3 cm on the skin missed thin crossings and let a corner sink 2 cm into an 8" pipe.
- **Into a structure:** a pipe may only enter at its own free end labelled with it, no deeper than the wall (manhole 0.10). An exemption measured from both ends of every segment silently exempted every short segment.
- **Pipe to pipe:** surface gap ≥ 1.5 cm, except segments sharing a node. A short jog between two parallel runs can make neighbours 1.2 cm apart; lengthen the jog.
- **Structures:**
  - Site boundary first.
  - Then the mesh-tree overlap with the house, and no two overlapping (except each on its pad).
  - Then symbols and sizes, on both axes for pits.
- **Devices:** one per drawn place, ±1 cm, on its system's pipe (`DIM_SN_DEV_AT`).
- **Give every assert message a unique `[tag]`.** Let `must_fail` match the tag. Duplicate messages made the named-reason count and the coverage count lie.

## Sanitary ware and counters (ST17)

- Plain boxes are enough: the BOQ counts sets. Place bath pieces by (x along the wall, out from the tile face, height over the floor).
- **Check each piece against what it serves:**
  - the WC outlet on its soil riser;
  - the basin on its counter, with exactly one waste riser under it;
  - each CW stub held by exactly one piece of A-12's kind (back face on the stub end);
  - grates on floor-drain risers.
- Kitchen counter:
  - Snap it to the tile faces: E-25's walls are drawn 2 cm off the model's.
  - Notch it round a corner column.
  - Keep the top under the window sill.
- **Clearance by exact overlap** of each box shrunk 0.5 mm. A 3×3×3 point grid missed a towel rail pushed into a door frame.
- **BOQ lines the template lacks** (floor tap, soap dish, sink) go to the owner, with counts.

## The leftovers (ST18)

- **Insulation:** check ST08 before calling it a gap. SS-02's ceilings already carried wool. "Foil under the battens" is a template line the drawings didn't ask for.
- **Termite (A-02 piped system, no layout):**
  - Lay a ring in each crawl-space cell, from the cells' clear plans between beam faces. A slab outline includes the beam, and a ring there cuts the plinth.
  - The BOQ line is the area: the beam outline plus the porch.
- **Skirting:**
  - Lay a strip on every bottom edge, at the house floor, of the last interior paint film. It then stops by itself at doors, tile and counters.
  - Check every painted foot along its length, and every strip on paint. A room-rect ray sweep false-alarmed through a protruding column.
- **Flashing where a lean-to roof meets a wall:**
  - Use straight L pieces. Lift the lap over every crest under its whole footprint, and compare the lap to the crest at the same point.
  - The upstand goes on the outermost finish found by ray: no paint above the carport ceiling, so plaster there.
  - Its top stays under the wall band.
- **Ceiling hatch:** under a board, with a box-to-box gap ≥ 0.40 to every light. The first spot by LP1 was 6 cm from a light.
