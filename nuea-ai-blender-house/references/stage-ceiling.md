# ST08 ceilings

Read when modelling gypsum or Smartboard ceilings, soffits, frames and hangers.

## ฝ้า (ST08, spec 29 ต.ค.; `examples/e42/scripts/e42_ceiling.py`, SCG Smartboard ceiling manual `ขั้นตอนการติดตั้งฝ้า.pdf`)

- **Ask every house:** board type and thickness, height from each floor, frame system, the bath board, and the
  soffit board and level.
- **the user's E42 spec:**
  - Inside: gypsum 9 mm (1.20 × 2.40) at FL + 2.80 on a C-line grid.
  - Bath: moisture-resistant gypsum at the bath floor + 2.60. The bath floor is 10 cm down, so that is +2.95.
  - Eave soffit: Smartboard vented at the fascia level.
- **The manual is for Smartboard:**
  - Wall angle screwed @ 30 cm, main runners ≤ 0.80, cross runners ≤ 0.40.
  - Screws 18 mm drill-point: 1.2 cm from the edges, 5 cm from the corners, then @ 0.20.
  - Joints: 5 mm open with PU sealant outside; flush joints (tape + 3 coats) inside.
  - Soffit face 1" above the fascia bottom.
  - Vented board 4 mm 0.60 × 1.20, 1.40 /m².
  - It has nothing gypsum-specific, and no hanger size or spacing. Hangers ≤ 1.00 m are assumed: say so.
- **Layout that lands every board edge on a runner:**
  - Boards 2.40 along y over cross runners along x @ 0.40 (2.40 = 6 × 0.40).
  - Mains along y @ ≤ 0.80 over them.
  - On a hip roof, the long-side rafters run along x every 1.00 m, so mains along y cross one every metre and the
    hangers find steel. Under a hip end the rafters run with the mains: shift the hanger sideways and count a link.
  - Hangers: scan each main every 2 cm (a rafter is 5 cm wide; 10 cm steps missed them) for the roof members
    crossing overhead and hang one at each crossing. Then fill gaps over 1.00 m, and ends over 0.75 m, with
    sideways hangers (≤ 0.5 m link, counted in the BOQ).
    - Allow the scan's 2 cm slack: 1.02 m between rafters set exactly 1.00 m apart is not a gap.
    - A main within 0.30 m of a wall angle gets none (assumed; ask the user).
    - A ray from inside a wall hits the wall: no hanger can be found there.
- **Room outlines come from the model:** ray-cast the plaster/column boxes from a seed point at ceiling height
  (`_room_rect`). Columns proud of the wall are cut out of the boards by rectangle splitting (`_minus`).
  - An EXACT boolean over boards that abut edge to edge left cutter faces behind (a board 4.6 cm low). Do not
    boolean coincident pieces.
- **Soffit:**
  - One trapezoid per eave, between the plaster face line and the fascia back, mitred 45° at the corners
    (`_clip`).
  - A full 0.60 board at the wall, a cut strip at the fascia.
  - Runners along the eave at the wall, at the 0.60 joint and at the fascia. At distance v from the fascia line
    the trapezoid spans u ∈ [v, L − v]; reversing that ran the wall runner into the next eave.
  - Cross pieces are cut in between those runners, on the same level on the boards' backs, under every board-end
    joint and ≤ 0.40 between. On top of the runners they floated 7 mm, and their screws held nothing.
  - The porch is ceiled at the same level, round its columns.
- **`selfcheck_ceilings`** reads it all back:
  - each ceiling's height from its own floor;
  - every piece within a sheet;
  - board area = plaster-face rectangle − columns;
  - runner spacing, measured per run (one object holds many runs; each prism has vertices only at its ends);
  - every hanger top on steel. Use a BVH of the steel alone: a ray from inside the rod hits the rod, and a
    sideways offset under a 30° rafter changes the height;
  - the soffit level against the fascia bottom.
- Joints: count the real board edges not on the outline, halved; include the 45° joints and the joint where the
  porch meets the soffit.
- Check each soffit runner whole inside one eave (an any-vertex OR across eaves let a runner spill into the next
  eave).
- Put the old bug back as a mutation.
- Mutations: 12 of 12 caught.
- **the user's E42 products (29 ต.ค.):**
  - Eave soffit: SCG Smartboard "เซาะร่องระบายอากาศครึ่งแผ่น" 60 × 120 × 0.4, cement colour, 5.1 kg. Draw 3 real
    slots 3" apart in the fascia-side half (slot sizes are not printed: 25 cm slots, 5 cm bridges, 6 mm).
  - Porch (เฉลียง): Smartboard flat, joints filled smooth like the gypsum inside; the eave round it stays vented.
  - C-Line 0.625 kg / 4 m (the TIS one is 1.125): lipped C 36 × 11 × 0.31, 3 mm lips.
  - The CS C-Line system:
    - a C-line clip at every main × cross crossing;
    - a spring joiner on each rod;
    - a steel angle + rod joiner at the top (steelbolt on concrete; on a steel roof it clamps the member);
    - wall angle round the room.
  - One 60 × 60 service hatch (aluminium frame + lid), handled as an opening: boards and runners trimmed, wall
    angle round it.
