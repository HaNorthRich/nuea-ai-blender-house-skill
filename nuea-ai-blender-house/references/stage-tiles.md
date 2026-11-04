# ST11 steps, waterproofing, screed, tiles, skirting

*SS-02's code is not in this repo; its file names (`ss02_*.py`) are from that job.*

Read when modelling floor or wall tiles, steps, waterproofing or skirting.

## ปูกระเบื้อง (ST11, spec 29 ต.ค.; `examples/e42/scripts/e42_tiles.py`)

- **Ask first:**
  - tile or SPC 6 mm;
  - sizes per room, and bath wall tile size;
  - porch tile;
  - steps (build them RC if the structure stages had none) with nosing;
  - kitchen splash height;
  - shower zone;
  - door leaf + frame products.
- **Order of work:** RC steps → bath waterproofing (Jorakay Flex Shield 2 coats: whole floor, walls 30 cm, 1.80 m in the shower, fibreglass mesh at the corners) → screed → adhesive + tiles + grout → nosing → skirting.
- **Bath floor drop:** lower the ground beams round the bath across their whole section, and cast a curb with the slab over them outside the bath. Do not leave a beam ledge in the bath. Do not rebate only the shoulder: the part left under the wall can be 7.5 cm, too narrow for two top bars. Splitting a line at a column loses continuity, so re-run the beam design (A2–D2 failed GB4 split, passed whole).
- **Door openings:**
  - Size the opening after plaster and beads from the frame maker's opening (ECO DOOR TVWG: ระยะเปิดช่องปูน 88 × 205).
  - Brick opening = that + plaster each side and over the head.
  - When the maker publishes none (BATHIC FU1), assume and flag it.
  - Check it in selfcheck_walls from the built brick, with a mutation for the old size.
- **Tile count:** count tiles off the layout. Each cell a tile touches is one tile; two offcuts of ≤ 45 % come from one tile. Add 3 % breakage, then whole boxes. Print area × 1.10 beside it. 60 × 60 in 3 m rooms wastes far more than 10 %.
- **One grid for the rooms of the same tile:** run the house tiles through the door thresholds, wall face to wall face. Into a lower room the threshold reaches over the riser's wall tiles. Onto a lower outside floor, put a riser tile in front.
- **Selfcheck by reading the model back:**
  - Tiles + joints = net floor area exactly, and no overlaps.
  - Joints = spec width.
  - Sample the tiled walls every 5 cm: no point bare.
  - Wall tiles reach the ceiling.
  - Finishes never inside concrete (the old ledge shows here).
  - Skirting = outlines − doors − counter.

## Room seeds

- **Seed points:** a room seed on a column grid line makes the rect scan stop at the column (E42 living room 14 cm short: ceiling, paint and floor all wrong). Seed between grid lines, and keep anything placed "at the room centre" (the hatch) at a fixed point.

## SS-02 (4 พ.ย.; `ss02_tiles.py`)

- **A riser is a tile on a bed**, the tread tile reaching over it. The top riser of a stair into a porch is covered by the porch tiles: a tile-only strip past the porch bed (`nosing`), else a 2 cm lip runs the stair's width.
- **A door frame that stands proud of the wall** (SS-02 D3, 1.25 cm) over a lower floor leaves a gap under its foot. Put the riser in front of the frame, its bed back to the wall, and run the upper floor's tile over it.
- **A door in a room's corner** leaves the side wall's 15 mm corner strip bare below the head: tile it as its own face, a joint short of the wall's tiles.
- **Cut a floor by every obstacle over its own span** (bed bottom to tile top), not at one height.
- **Checks a reviewer found missing:**
  - Coverage grown by the joint passes joints of 0 to 4 mm. Check each tile side instead: it ends its bed, meets another piece of the same grid cell (union ≤ tile size), or faces the next tile exactly one joint on, or the bed ends there (a perimeter joint at a wall).
  - No two finish boxes (tiles, beds, risers, steps, screed) share volume.
  - Read the step risers from the model: under each nosing, from the tread below to top − t, covered above, no gap along the width.
  - Check a wall's bottom row at every sample, not as one minimum per face.
- **Bed area:** a standing bed (behind a riser) counts by its face. Tell standing from lying by height (> 2 cm), not by the smallest side: a lying bed narrower than 1 cm would otherwise count its 1 cm edge.
- **A reviewer's second round:**
  - Test "a tile over each riser top" every 5 cm. One point per riser passes a nosing that covers only half.
  - The joint rule's "same tile, two pieces" exemption must bound both axes. Otherwise a strip laid on its own grid passes as part of the next tile.
  - A riser's bed runs up to the tile above it, except under a jamb's foot.
  - All faces of one bath share one tile row origin (the lowest floor), so the joints run on round the corners.
