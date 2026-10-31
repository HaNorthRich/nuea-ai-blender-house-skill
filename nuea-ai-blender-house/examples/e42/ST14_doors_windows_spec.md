# ST14 doors · windows · aluminium (E42)

Construction order: last stage (after paint coat 2). Read before resuming ST14.

## the user's spec (31 ต.ค. 69)

| Item | Opening (plaster clear) | Spec |
|---|---|---|
| D2 ×2 bedrooms | 88 × 205 | MASTERWOOD uPVC 80×200 (ไทวัสดุ #60438471) in a KASSA WPC T1 80×200 frame (#60452484), lever handle |
| D3 kitchen (back door) | 88 × 205 | same as the bedrooms (uPVC 80×200 + KASSA WPC frame) |
| D4 bath | 78 × 205 | ECO DOOR uPVC W2 70×200 (#60416405) in an ECO DOOR WPC TVWG-100 70×200 frame (#60290220), bath knob |
| D1 porch | 260 × 205 | aluminium sliding, 4 panels (2 sliding + 2 fixed) + screen, **black frame**, clear 5 mm glass |
| W1 ×3 | 120 × 110 | aluminium sliding 2 panels + screen, black, clear 5 mm |
| W2 ×2 | 60 × 110 | aluminium awning (บานกระทุ้ง), black, clear 5 mm |
| W3 kitchen | 120 × 90 | aluminium sliding 2 panels + screen, black, clear 5 mm |
| W4 bath | 60 × 50 | aluminium louvres, black, **frosted** glass |

No burglar bars. The model and BOQ named different bath doors and bedroom frames; the user chose the BOQ's (above).

## Sources

- ECO DOOR WPC frame TVWG-100 (2″×4″): the 700×2000 frame needs a 780 × 2050 masonry opening; the 800×2000 frame needs 880 × 2050.
  https://www.eco-door.net/product/wpc-frame-tvwg-100/ (read 31 ต.ค. 69)
- KASSA WPC frame 80×200: 10 cm jamb, shipping size 205 × 88. It publishes no rough opening.
  - **88 × 205**, the same as ECO DOOR's frame of that size (assumed; the user confirmed 31 ต.ค.).
  - https://www.thaiwatsadu.com/th/product/…-60297352

## Step 1: openings (done in the trial run, 31 ต.ค.)

`e42_walls.py`, `DOOR_CLEAR`:
- D4 changed from 77 × 183.5 to 78 × 205. Its west edge stays at 3.35: the brick pier to D2_Bed2 must stay `min_panel` (20 cm) wide, because the heater run crosses the wall there. Centred, the pier went concrete and the run hit it.
- D3 changed from a bare 0.80 × 2.00 brick opening to 88 × 205 + plaster. Its east edge stays at 6.55; centred, the SW_Kitchen run hit the new jamb tie.

Every selfcheck passes after the rebuild of walls → tiles → primer → coat 1 → coat 2, with ceilings, electrical and conduit checked too. Changes:
- brick 3801 → 3781;
- paint walls in 97.29 m², out 63.89 m² (buckets unchanged);
- skirting 32.48 m;
- electrical and conduit quantities unchanged.

## Step 2: units (done 31 ต.ค., `scripts/e42_units.py`, tests `scripts/test_units.py`)

- **Windows and D1 openings from the unit size.** The listings' 120 × 110 etc. is the overall frame size, so the old brick openings left only 1.17 × 1.07 clear. Now: brick = unit + 5 mm gap + plaster each side (`UNIT`, `UNIT_GAP`, `_win`), centres kept. D1 is 2.64 brick wide and stands on the floor.
- **Front steps span = D1's plaster clear.** It was hard-coded to the old D1 edges, and the porch tile grid (centred on D1) left a 2 mm sliver at the nosing.
- **No tile returns in window reveals.** The 10 cm frame (`UNIT_DEPTH`) fills the 9 cm wall (bath W4, kitchen splash at W3). Wall tiles 22.44 → 22.15 m².
- **`all_objects` → `.objects`.** all_objects is a stale cache after a rebuild in the same script, and it had hidden the tile clash. Changed in e42_ceiling and e42_walls.
- **Units:**
  - door frames 32 mm jambs, 10 cm deep, snug in the clear;
  - leaves 3 mm off the jambs, 10 mm over the floor;
  - 3 hinges a door, bought for the house as ceil(12 ÷ 2) = 6 packs (the BOQ had 8);
  - lever (bedrooms, kitchen) or knob (bath);
  - aluminium black at the product size, centred;
  - sliding panes on 2 tracks (D1: F-S-S-F, fixed outside, sliders butt);
  - awning W2; louvres W4 with frosted glass;
  - screens on the room side (not on W4).
- **Hinge/swing (the user confirmed 31 ต.ค.):** every door opens into its room; latch beside the room's switch. Bed2 hinged north; Bed1, bath and kitchen hinged south.
- **Selfcheck, read from the model:**
  - one unit per opening;
  - frame snug in the clear measured in the wall;
  - no clash with walls, tiles, paint, electrical or ceiling (unit boxes 0.1 mm in, so contact is not a clash);
  - latch on the switch side; swing clear of walls and devices;
  - panes, glass type and screens; take-off counts vs openings;
  - massing openings hidden.
- **Take-off:** DR1 3 · DR2 1 · DF1 3 · DF2 1 · DH1 3 · DH2 1 · DH3 6 packs · AL1 3 · AL2 2 · AL3 1 · AL4 1 · AL5 1.
- **Other quantities after the rebuild:** brick 3761; paint in 96.74 / out 63.25 m² (buckets unchanged); electrical unchanged.

### Step 2 plan (as written before)

- Frames, leaves, glass, screens and handles as real pieces at the opening, all inside the plaster clear. A leaf is closed, with a hinge side and swing that clear the switches and the furniture.
- Take-off rows by count, from the model: door sets, frames, handles and knobs, hinges (packs for the house), and aluminium units by size.
- A selfcheck from the model: every opening has one unit; each frame fits its opening; nothing clashes with the walls, the conduit or the boxes.
- The old massing `*_leaf` objects (from `e42_build.py`, used by `e42_render.py`) are replaced.

## Confirmed by the user on 31 ต.ค. (were assumed)

- KASSA's rough opening (88 × 205).
- Hinge side and swing for each door.
- D1: which panels slide.
