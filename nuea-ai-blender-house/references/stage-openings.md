# ST14 doors, windows, aluminium

Read when modelling door sets, aluminium windows or doors, glass or screens.

## ประตู หน้าต่าง อลูมิเนียม (ST14, spec 31 ต.ค.; `examples/e42/scripts/e42_units.py`, spec `ST14_doors_windows_spec.md`)

- **Size openings from the product.** Use the maker's ระยะช่องปูน for doors. Aluminium is sold by its overall frame
  size (ขนาดรวมวงกบ), so clear = unit + 5 mm sealant each side and brick = clear + plaster. A brick opening of the
  nominal size leaves no room.
- **Before modelling units, reconcile the model with the BOQ.** E42's model and BOQ named different door products;
  ask the user which one.
- **Widening an opening breaks whatever was hard-coded to the old size.**
  - Front steps span, and the porch tile grid centred on the door, left a 2 mm sliver.
  - A pier fell under `min_panel` and turned concrete, so a conduit hit it. Pin an edge that keeps the pier.
  - A switch next to a door clashed with the new jamb tie.
  - Derive spans from OPENINGS, and rerun every stage's selfcheck after the change.
- **A frame deeper than the finished wall fills the reveal.** Tile returns there are impossible: the tiles stop at
  the frame.
- **Doors:**
  - latch beside the room's switch; swing checked in plan, including the leaf face and the handle tip, against
    walls, wall tiles and devices (exact quarter-disc test);
  - hinges bought per house in packs (`ceil(total ÷ pack)`), not rounded per door.
- **Aluminium:**
  - check across the wall: fixed panes outside, sliders and screens on the room side;
  - panes that meet lap only when on different tracks; screens exactly over the sliders.

## Lessons from SS-02 (ST14, 1 พ.ย.)

- Read the schedule rows one by one: the D3 hinge row held the leaf text, and the leaf size in the text disagreed with the
  drawn dimension. Report both.
- ST06 may slide an opening away from a column: take frame positions from the real opening, not the plan table.
- A frame can stand inside its opening's bbox and still miss a member: count frame and sash pieces. A bbox never sees a
  door head between its jambs or a divider.
- Turn each leaf on its real pin up to its stop, with the lever tip, and test the frame too. A pin at the leaf corner lets
  a door pass 170° through its own jamb. A butt hinge pin stands proud of the frame.
- The stop must be reached first: a short stop lets the lever hit the wall.
- Bound glass on all six sides and tie each pane to its sash plane; for an arch use the arch limit.
- `drop_piece` removes the last piece appended: name the mutation after that piece.

## Glass and screens (31 ต.ค.)

- **Glass is a thin refracting slab.** Principled with Transmission 1, IOR 1.52, roughness 0 (clear) or 0.30
  (frosted); `use_raytrace_refraction` on; `thickness_mode = "SLAB"`; scene `eevee.use_raytracing` on. Without ray
  tracing EEVEE shows a dull probe image and the glass reads opaque. Set `diffuse_color` alpha 0.25 so it is
  see-through in solid view too.
- **Insect screens are see-through:** dark, alpha 0.35. An opaque screen made half of every sliding window look
  like a grey panel.
- **Set these properties on every build.** `mat()` returns an existing material unchanged, so new values never
  reach a file that already has the material. The selfcheck reads them back (transmission, IOR, roughness,
  refraction, slab, screen alpha).
