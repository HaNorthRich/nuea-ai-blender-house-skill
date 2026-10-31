# ST11 steps, waterproofing, screed, tiles, skirting

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
