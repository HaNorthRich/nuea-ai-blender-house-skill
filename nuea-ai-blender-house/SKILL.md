---
name: nuea-ai-blender-house
description: >-
  ปั้นบ้าน/อาคาร 3D ใน Blender ผ่าน Blender MCP จากแปลน · brochure · ภาพ SketchUp — โมเดลขาย (ผนัง ช่องเปิด หลังคา วัสดุ Poly Haven เฟอร์นิเจอร์ แสง ภาพ render ผังพื้น) หรือโมเดลก่อสร้างที่ปั้นทีละขั้นตามลำดับงานจริงไว้ถอดปริมาณ (ฐานราก เสา ผนัง หลังคา ฝ้า สี กระเบื้อง ไฟฟ้า ประตูหน้าต่าง) Triggers: 'ปั้น 3D', 'ทำโมเดลบ้านใน Blender', 'Blender MCP', 'ปั้นตามลำดับก่อสร้าง', 'render ภาพขายจาก Blender', 'ใส่ texture/วัสดุ Poly Haven', 'ใส่เฟอร์นิเจอร์ในโมเดล'
---

# nuea.ai Blender House (Blender MCP)

Distilled from real house jobs: hip-roof sales models with interiors and renders, an L-shaped two-roof house on a
site plan, a house corrected to its site photos, a 42 m² house (E42) modelled stage by stage in construction
order for quantity take-off (its full code is in `examples/e42/`), and a 95 m² single-storey house (SS-02) taken on to
sanitary, fixtures, the BOQ extras and every conduit. Every gotcha below cost at least one render or rebuild
round-trip. Reply in the user's language; code and object names in English.

Work in the live Blender MCP session itself: the session holds the scene, so keep the modelling in one conversation.

## Files

| File | What |
|---|---|
| `scripts/helpers.py` | shell: `wall_x/wall_y` with openings, `window`, `door`, `box`/`mesh_obj`, `prisms` (2D outline → solid), `spandrels` (rounded opening corners), `arch_window`, `trim_rect` (architrave + sill for rectangular openings), `cornice` (mouldings, gutters) · materials: `mat`, `fix_textures`, `tile_mat`, `lawn_mat`, `leaf_mat` · landscape: `hedge`, `scatter` · `setup_light`, `setup_render`, `cam`, `shoot` · checks: `inward_meshes`, `selftest` |
| `scripts/roof.py` | `hip_roof` (soffit slab + roof + metre UVs; square footprint = pyramid), `soffit_ring` (flat soffit = eave rectangles minus the building outline, for eaves below the wall top), `cpac_tiles` (wave or flat tiles with per-tile joints; `others=`/`give_way=` for L/T roofs), `roof_caps`, `valley_lines` + `roof_valleys` (ตะเฆ่ราง + metal valley gutter), `roof_frame` (steel: rafters, battens, hips, ridge, valleys, king posts), `carport_metal` (mono-pitch metal-sheet carport), `carport_classic` (same, dressed for a classic house: fascia, cornice, soffit, columns, fillets) |
| `scripts/drawings.py` | CAD line drawings for AutoCAD: 4 elevations, top view, 2 sections → DXF R12 (mm, layers A-ELEV/A-SECT/A-GLAZ/A-ROOF/A-SITE/A-GRND/A-TEXT) + SVG preview, run headless on the saved .blend |
| `scripts/render_cycles.py` | final renders in Cycles from the saved .blend, outside MCP (Metal GPU, denoised) — site-plan files too |
| `scripts/export_sketchup.py` | exterior → GLB for SketchUp import (7c) |
| `scripts/site_place.py` | finished house → plot of a site-plan .blend, headless: one excluded LIB collection + one collection-instance empty per plot (7d) |
| `scripts/cpac_caps.py` | the 8 SCG CPAC trim pieces as solids (sizes from SCG dealer pages, 13 mm wall, `selftest()` against catalogue weights); `arch(fall=)` seats skirts on the tile fall; `junction()` = the three-/four-way as one shell (Workflow B) |
| `scripts/steel_sections.py` | cold-formed steel to the real profile: `lipped_c` (inner radius = t), `box_tube` + `tube` (TIS 107 square tube), `strip` (thin formed sections such as hat battens, from the centreline), `prism` (closed sweep, quad caps), `frame` (place along any axis), `obb` + `obb_overlap` (clash test for sloped members), `TIS` kg/m + `selftest()` (Workflow B). `roof.py`'s `roof_frame` is solid boxes — fine for renders, not for take-off (use the E42 ST07 way) |
| `scripts/beam_wsd.py` | RC beam check by the engineer's WSD method (from a licensed engineer's calculation sheet): design criteria, slab → beam loads, continuous beams with live-load patterns, moment/minimum-steel/shear checks; `selftest()` reproduces the engineer's numbers (Workflow B) |
| `scripts/checks.py` | `each(items, fn, what)`: run a check on every item and raise one error listing every failure with its [tag] (`CHECK_FIRST=1` stops at the first) — one run, every fault (Workflow B) |
| `scripts/probe.py` | headless measuring in compact tables: `objects_in(lo, hi)` what is in a box of space, `parts(name)` an object's loose parts (ties, lintels), `near(p)` nearest surface of each object (Workflow B) |
| `scripts/assets.py` | asset library: `sf_search` (CC0/CC-BY only), `sf_fetch` (download once into `~/3d-assets` + licence files), `place_asset` / `place_collection` (scaled, bottom-centre placement; also for Poly Haven model collections) |
| `examples/e42/scripts/` | the construction model built stage by stage (Workflow B): `build_all.py` (the whole house from an empty Blender, every stage checked, ~2 min), `e42_load.py` (loads every module in build order, refuses a name defined twice; `SKILL_SCRIPTS` points at this skill's `scripts/`), `e42_struct.py` … `e42_units.py` one module per stage, `test_*.py` one mutation suite per stage — the reference implementation for every `references/stage-*.md` |

References (read when the pointer's condition holds):

| File | Read when |
|---|---|
| `references/working-economy.md` | **before a construction model, and whenever a stage passes ~30 runs**: what a detailed model's token bill is made of (measured) and the rules that keep full detail at a fraction of it |
| `references/construction-method.md` | before the first stage of a construction model; when a check fails in a way you don't understand |
| `references/stage-structure.md` | grid, footings, stubs, ground beams, slab, columns; choosing a ground-beam type |
| `references/stage-walls.md` | walls, plaster, beads, wall plate, door/window openings |
| `references/stage-roof.md` | roof steel, CPAC or metal-sheet covering, caps, fascia |
| `references/stage-ceiling.md` | ceilings, soffits, ceiling frames, hangers |
| `references/stage-paint.md` | primer and paint coats, buckets |
| `references/stage-tiles.md` | steps, waterproofing, screed, floor/wall tiles, skirting |
| `references/stage-electrical.md` | lights, switches, sockets, consumer unit, conduit, wire, the service main |
| `references/stage-sanitary.md` | water supply, soil/waste/vent pipes, septic tank, grease trap, manholes, water tank, pump; sanitary ware, counters, bath accessories |
| `references/boq-coverage.md` | before the first stage and before a take-off script: which stage feeds each line of your BOQ template, and the lines a model tends to miss |
| `references/stage-openings.md` | door sets, aluminium windows/doors, glass, screens |
| `references/visual-extras.md` | furniture/plant/car assets, landscape, CAD drawings, SketchUp hand-off, a site plan |

Load both into text blocks once per .blend so the file stays self-contained:

```python
import bpy, os
S = os.path.expanduser("~/.claude/skills/nuea-ai-blender-house/scripts/")
for n, f in (("house_helpers", "helpers.py"), ("house_roof", "roof.py")):
    t = bpy.data.texts.get(n) or bpy.data.texts.new(n); t.from_string(open(S + f).read())
PROJ = "P-2389"   # collection prefix
exec(bpy.data.texts["house_helpers"].as_string()); print(selftest())
```

Every later call starts with `PROJ = "..."` + the `exec(...)` line(s). Override `FL` `WT` `TE` `TI` the same way.

## Two kinds of model

- **Sales model** (renders, plans for marketing): Workflow A.
- **Construction model** (every piece real, built in construction order, quantities read from it): Workflow B. It reuses
  Workflow A's preflight and project setup (steps 0–2).
Ask which one when the request does not say.

## Workflow A: sales model

### 0. Preflight
- `get_addon_status` then `get_scene_info`. A protocol mismatch → the user runs `! uvx mcp-for-blender install-addon`,
  re-enables the add-on and presses Start MCP Server. The first call right after a start can fail: retry once.
- Poly Haven is a **per-scene** setting (`scene.blendermcp_use_polyhaven`), so every new .blend — and an older file
  that never used it (H2B) — starts with it off. Set it to `True` in code right after creating/opening the file (CM3).
- Opening another file in the live session: if `bpy.data.is_dirty`, first `save_as_mainfile(filepath=<name>.unsaved-<date>.blend,
  copy=True)` next to it — `open_mainfile` drops unsaved work without asking (H2B). The MCP server survives the open.
- Editing an existing model: copy it to `<name>.pre_<job>_<date>.blend` before the first save (`.blend1` keeps one
  version). If the file carries its own build scripts as text blocks (H2B: `h_common.py`, `h_shell.py`,
  `h_openings.py`…), reuse them: `exec` each into its own dict (the skill's `mesh_obj`/`box` have other signatures),
  drop the lines that `clear_collection(...)` or `exec(open(<old scratchpad>))`, and call their builders with new
  numbers so new parts match the old ones.

### 1. Inputs → a coordinate table
- `.skp` cannot be read (SketchUp 2026 binary; only its thumbnails come out). Ask for a `.dae/.fbx/.obj` export
  or a dimensioned plan image.
- Fix the axes: x = left→right, y = front(−)→rear(+), z up, metres, front wall of the main block at y = 0.
- Before building, write the room table in the reply (room · x-range · y-range · openings) and state every assumed number.
  The user corrects a table faster than a render.
- **SketchUp top-view screenshots are perspective.** Dimension strings sit at wall-top level; the dark band next to a
  wall is its face seen in perspective. A wall's position is its *top outline*, not the dark band. Misreading this put the
  P-2389 kitchen wall 0.90 m out and the user had to send a correction.
- Brochure exteriors set roof type, pitch look, window shapes and colours; the plan sets positions. If they disagree,
  follow the plan and say so (CM3: the reference had the arches left of the porch, the plan right).
- PDF plans: `pdftoppm -r 300 -png plan.pdf out` then crop with `sips -c H W --cropOffset Y X` (on macOS without PIL).
  Measure px/m from two grid lines with a known dimension.
- A plan drawn without openings (all walls continuous, CM3 A-04): read doors/windows from the SketchUp views — the
  top view gives positions along each wall, the elevations give sill/head heights.
- Site plan from a CAD screenshot: take px/m from a labelled boundary, build unit vectors along the front boundary
  and its normal, then map every plot corner and one house corner into model coordinates. Check the four side
  lengths against the labels before building the fence.
- **Site photos of the house being built beat the permit drawings for what was built** (H2B): front and side
  windows went in 2.00 m wide instead of the 1.45 m W1 in the schedule, the kitchen got a back door the plan does not
  show, bedroom 2 got a portrait window, every opening has a plaster architrave and one wall an offset plaster panel.
  The plan still sets the grid, levels and roof. Read photos per facade: say which room each window belongs to
  (look through it: neighbour's wall = side wall, road = front) before resizing anything.
- Photo sets (60+ iPhone shots): contact sheets first, then 1400 px copies of the few that matter.
  `sips -Z 480 in.jpeg --out t.jpg; sips --padToHeightWidth 360 480 --padColor FFFFFF t.jpg` per photo, then
  `ffmpeg -pattern_type glob -i 'u/*.jpg' -vf "tile=4x3:padding=4:color=red" sheet_%d.jpg` — without the padding
  step ffmpeg stops at the first portrait photo, and this ffmpeg build has no `drawtext` (keep a name index).
- Height from a photo: scale from something of known height at the same depth (H2B: the 1.30 m fence next to the
  carport post gave the front beam top ≈ 2.74 m). Opening sizes: take a square-on photo, get px/m from a known
  horizontal run on the same wall (house corner → door trim), then read width *and* height — H2B's front window
  measured 2.00 × 1.00 (head 0.44 under the soffit), not the schedule's 1.20 tall. Crop the full-res photo
  (`sips -s format jpeg` reads iPhone HEIC; `-c H W --cropOffset Y X` at full scale) before measuring.
- Decorative frames (กรอบบัวซ้อน) and architraves: read their outer edges in the same photo (H2B panel 0.72–2.72 ×
  1.00–2.81, bands 0.12, from the house corner to mid-window); build them as `prisms` 25 mm proud.

### 2. Project setup
- Folder: `<project>/Blender/<code> <name>/` with the `.blend` and `renders/`. `bpy.ops.wm.save_as_mainfile` first,
  then save after **every** step (`bpy.ops.wm.save_mainfile()`).
- Collections: `PROJ`, `PROJ Walls`, `PROJ Openings`, `PROJ Site`, `PROJ Interior`, `PROJ Landscape`.

### 3. Shell (build order)
1. Floor slab at `FL`, exterior walls `TE`, interior walls `TI`, using `wall_x`/`wall_y` with
   `openings=[(c0, c1, zb, zt)]` in absolute coordinates. Corner rule: exterior x-walls run the full length
   (±TE/2 past the corners), y-walls stop at the x-walls' faces — no coplanar overlaps, no z-fighting.
2. `window(...)`, `door(...)` in each opening. Arched window: cut a rectangular opening up to the apex, then
   `arch_window(..., trim=)` adds spandrels, frame with glazing bars, glass, outside architrave and sill.
   Porch with rounded corners: `prisms(name, spandrels(c0, c1, beam_bottom, R), axis, w0, w1)` under the beam.
3. Roof: `hip_roof(x0, y0, x1, y1, ze, pitch)` with the outer eave line (wall face + overhang ≈ 0.6 m), then
   `cpac_tiles()` and `roof_caps()` for concrete wave tiles. `Roof_Eave` is the exterior soffit (ฝ้าชายคา) + fascia:
   keep it visible; hide it only in plan/cutaway shots. L-shaped house: one `hip_roof(..., name="Roof_Wing2")` per wing,
   **Wing ridge perpendicular to the main roof** (standard L hip, SCG has a valley spec for it): give the wing a
   footprint long enough in the direction away from the main block that its ridge runs *into* the main roof and its
   far hip end is buried. A wing beside the main block with its ridge parallel makes a level internal valley
   (M-roof + box gutter) — the user spotted it as "weird" in CM3; it ponds and leaks, don't build it.
   Then: wing `ze`/`soffit_z` 2 mm lower; rebuild the wing's `_Eave` box to the part outside the main roof;
   `cpac_tiles(main, others=[wing])`, `cpac_tiles(wing, others=[main], give_way=True)` (the merged rear plane keeps
   only the main roof's tiles); `roof_caps` both ways with `others=`; `roof_valleys(main, wing)` (SCG valley gutter:
   bed 12 cm, ≤ 6 m long, ≤ 36 m² catchment); `roof_frame` for both with the same `others`/`give_way` and
   `valleys_with=`.
   Wing whose ridge meets the main roof's hip (pyramid main + terrace wing, H2B): the merged plane is split along the
   main's old hip, part main tiles and part wing tiles. Use `give_way=False` for the wing there — its tiles stay 2 mm
   under the main's with the same courses (cpac_tiles counts u from the object origin and v from each face's eave,
   so keep the wing `ze` exactly 2 mm lower — equal `ze` gives coincident tiles — and never move the `*_Hip`
   objects) — `give_way=True` cut them in a zig-zag seam along the old hip. `roof_valleys(..., lift=0.07)` for wave tiles: the 0.03 default is for flat tiles
   and let the wave tips poke through as a dotted line (H2B).
   Long overhang (H2B 1.10 m at 30° → eave +2.99, walls to +3.60): `hip_roof`'s `_Eave` box would cut the walls and
   show as a low ceiling indoors — delete it, keep a separate fascia and build the soffit with `soffit_ring`.
   Carport against such an eave (H2B, site photos 20 ต.ค.): one **flush steel grid** (C100x50 front beam, rafters, rear
   beam; C75 purlins) whose rear beam is fixed on the fascia face, crossing its lower half — rafters stop at that beam
   and **never run under the soffit** (the user corrected both wrong versions: a sheet at "eave level" 3.02–3.06 cut the
   tiles; rafters run back to a wall beam under the soffit did not exist). Sheet back edge butts the fascia face under
   the tile lip: its top must stay ≥ 1.5 cm under the underlay rim (`ze + 0.03·tan − 0.06/cos` at the fascia face;
   H2B 2.92 vs 2.94). Front height from a photo against the fence (H2B front beam top 2.74 → 2.2° fall, clear 2.65 m).
   Posts on the front fence line double as fence pillars. Assert both limits and `max steel y ≤ fascia face` in the build call.
   Flat tiles like the CM3 reference (CPAC Neustile): `cpac_tiles(base, wave=0.0, step=0.02, lap=0.28)`.
   Steel frame (Thai practice for CPAC tiles, research CM3): `roof_frame(base, lap=<same lap>)` = จันทัน C100x50
   @ 1.00 m, ระแนง every lap (CT 0.32–0.34, Neustile 0.27–0.29), ตะเฆ่สัน/อกไก่/ตะเฆ่ราง 100x125, ดั้ง every
   1.5 m. It sits inside the `_Hip` underlay; for a structure shot hide tiles, `_Hip`, `_Eave`, caps, valleys,
   gutter and ceiling. Pitch 25° clears every CPAC minimum (CT 17°, Neustile 22.5°).
   Openings: `trim_rect` on every exterior rectangular window (sill) and door (`sill=False`) — the user flagged plain
   rear windows next to the trimmed front arches (CM3).
   Classic eaves: `cornice()` along the outside faces (bands under the soffit) and a dark `cornice()` gutter on the eave line.
   `cornice()` corners: extend exactly one of the two meeting segments (ext0/ext1), or overlapping coplanar faces
   render black — the same rule for any two boxes meeting at a corner (fascias, gutters).
   Cornice vs window trims: a band may never cross an architrave. Keep the upper bands above the highest trim top
   (arch trims reach apex + 0.12 m) and stop lower bands at each trim with `cuts=[(axis, face, u0, u1, z_top)]`
   (u0..u1 = ring half-width at the band's top edge) — the user spotted the bands running through the arches (CM3).
   Ridge caps of two roofs that meet run on under the other roof (handled in `roof_caps`); valleys get the V-shaped
   metal of `roof_valleys`, never ridge caps — the user asked for a "cap" there, explain why it is metal.
   Every builder (walls, boxes, roof parts) replaces an object of the same name, so re-run a step to fix it —
   don't delete by hand. A rebuild keeps the materials already on the object; to change one, set
   `obj.data.materials[0]` directly (the `m=` argument only seeds new objects).
   Lean-to (เพิงหมาแหงน, 4 พ.ย.): one sloped soffit plane `zr(y)` over the whole roof rectangle, walls up to
   `zr − soffit`. A wall along x with a flat top at its low face leaves a wedge gap on the high face (front wall:
   1.6 cm) — add a triangle prism on top; assert per vertex `v.z <= zr(v.y) − soffit` over walls + decor.
   Slat (ไม้ระแนง) facade: the user rejected a sparse slat grid round the window; they want ONE tight full-height panel
   (SCG/Shera 7.5 × 300 × 0.8 cm, 1 cm joint, dark backing) beside the window by the entrance, wrapped round the
   corner, plus a thin flat double frame round the black window and a black wall lamp. Keep the panel ≤ 3 m (one plank).
4. Carport: for a classic house use `carport_classic(...)` (default 3° click-lock sheet, purlins on rafters flush
   with the edge beams): sheet + steel hidden behind a white fascia with cornice bands, flat soffit with downlights,
   columns with base/capital, rounded fillets between the street-side columns — the user found the bare steel version
   did not match (CM3). Fascia height = roof rise + steel depth + ~0.1 m; 6° + stacked steel gave 0.76 m, which the user
   called far too heavy next to a 0.25 m porch beam — aim for ≤ 0.45 m. Place the street columns so the printed
   fascia overhang is equal at both ends (CM3: columns at xf + 0.20 and x_high − 0.20) and centre the car between
   them. For a buildable answer give a dimensioned section: `carport_classic` returns `levels`; CM3's generator
   drew it as SVG and exported PNG with headless Chrome (`--headless=new --screenshot`) — qlmanage crops to a square.
   Plain version: `carport_metal(name, x_low, x_high, y0, y1, z_high, posts, slope_deg=7)` — slope toward the side
   boundary with the gutter + downpipes on the low side (ป.พ.พ. 1341), high edge tucked under the main soffit,
   free-standing posts 0.2–0.3 m off the house + flashing strip. Check its printed clear height ≥ 2.5 m; 1 car
   ≈ 2.8–3.0 × 5.5 m. Cut a gate in the front fence and pave a driveway. Legal points (setback, permit for > 5 m²)
   are raw research only: have a local lawyer or the district office confirm them before building.
   Ground (make it ≥ 150 m across, or the aerial shows its edge), road, fence. Front fence ≤ 0.5 m or the
   eye-level hero shot loses the garden; when lowering one stretch of a long fence box, split the box — moving only
   its front vertices makes the whole run slope (CM3).
5. `look` (top + three_quarter) and compare with the plan **before** any materials.

### 4. Materials
- Poly Haven: `import_asset(..., apply_to=[obj])` makes a **separate copy per object** (`<id>_material_<obj>`).
  Edit the copies, never the base. Then `fix_textures("<id>", size=<metres per tile>)` on every copy prefix:
  - code-built boxes have no UVs → it wires TexCoord Object → Mapping → image `projection='BOX'`;
  - Poly Haven ships displacement BOTH at scale 0.1 → grass climbs over paving and walls show seams;
    it switches to BUMP at `disp_scale=0.02` (pass `disp_scale=0.003` for plaster).
- To give many objects one Poly Haven material, `apply_to` a single object and assign that material to the rest
  in code — `apply_to` with a list makes one copy per object.
- Plaster walls: `fix_textures(id, 2.23, disp_scale=0.003, normal_strength=0.15)`, or walls show vertical streaks.
- Stone cladding หินกาบ (ledger panel, H2B): Poly Haven has no ledger stone — `stacked_stone_wall` reads as rounded
  river stones. Build the slabs with a Brick texture (u = x, v = z via Separate/Combine XYZ for a wall along x; row
  0.058, brick width 0.36, mortar 0.004, squash 0.65/3, offset 0.5/2, charcoal 0.04 / warm grey 0.115), multiply by the
  Poly Haven colour desaturated (Hue/Sat sat 0.12) for surface detail, bump from 1 − brick Fac over its normal map.
  Cladding = frame interior minus the window architrave, 15 mm proud behind 25 mm bands; give the bands a smooth white
  a touch brighter than the wall (`M_Trim_White` 0.93) or they vanish into the plaster.
- Delete base materials nobody uses.
- Veined stone textures can read orange/rusty; for tiled floors a procedural brick-texture tile (60×60 granito)
  looked cleaner than any Poly Haven floor.
- Colours go on shader inputs; `diffuse_color` is the viewport only. `mat()` is get-or-create: a colour changed in a
  script does not reach a .blend that already has that material — delete the material first or set its node inputs.
- Lawn: `lawn_mat()` — Poly Haven grass is leafy/dry. Paving and floors: `tile_mat()`.
- Realism audit (ask it of every job): image-based PBR for walls, wood (`natural_walnut_veneer` doors,
  `black_walnut_veneer_02` furniture frames), fabric (`rough_linen`, recoloured cream with Hue/Sat → Multiply);
  flat colours are fine only for paint (trims, soffit, steel). The weakest part is procedural vegetation — use
  library models (6b).
- Dark roof tiles render pale grey at eye level (grazing sky reflection): CM3 needed albedo ≈ 0.03–0.045 and
  `Specular IOR Level` 0. `M_Roof_CPAC` from roof.py now ships with these values; a lighter roof colour still needs
  specular 0.
- EEVEE glass with transmission shows grey, not the room behind it. For lit interiors seen from outside use alpha
  glass (`Alpha` ≈ 0.2, `surface_render_method = 'BLENDED'`) plus a softly emissive curtain (0.45) — gives the warm
  window glow of sales references.

### 5. Light
- `setup_light()`: Sun lamp with a known direction + HDRI at 0.6 with `sun_threshold = 1000`. Don't rotate the HDRI to
  aim its sun; two guesses at it wasted two renders. Print the sun's travel vector
  (`matrix_world.to_3x3() @ (0, 0, -1)`): for a front at −y it needs a **positive y**, or the facade is in shadow.
- Pure-sky HDRIs look deep blue to the camera. Mix a brighter copy for camera rays only (Light Path → Is Camera Ray →
  Mix Shader with a second Background at ~1.3) so the sky reads light without changing the lighting.
- Interiors: ceiling slightly emissive (0.12) + downlights + bedside point lights; `setup_render()` turns on
  raytracing + fast GI so rooms aren't black.

### 6. Interior
- Poly Haven furniture is mostly vintage. For a modern Thai house build beds/sofas/cabinets from boxes with
  Poly Haven fabric/veneer textures and import only modern pieces: `side_table_01`, `dining_chair_02`,
  `modern_coffee_table_01`, `modern_ceiling_lamp_01`, ceramic vases, `potted_plant_02`.
- Imported models arrive at arbitrary scale: size them from the reported `world_bounding_box` and put them on `FL`.
- Copying an imported asset (`obj.copy()`) leaves the original at the world origin — delete it or hide the source
  variants, or it shows up in the carport.
- Check every piece against walls, curtains and doors in a top `look`; clashes show up only in renders otherwise.

Assets (6b) and landscape (6c): `references/visual-extras.md`.

### 7. Cameras and renders
- Marketing set for an image-to-image step (ChatGPT, H2B): hero 3/4 from across the road at eye **1.8–1.85 m**
  (sees the garden over a 1.3 m front fence; from beside the plot a solid side fence hides it), straight front,
  carport 3/4 with the car nose out, terrace close-up from inside the gate (not under the palm canopy), side garden,
  drone 3/4, 4:5 portrait with the house in the lower half and sky left for the headline, and an ortho top with
  roofs, soffit, fascia, carport roof, ceilings and lamp discs hidden = 3D floor plan with the garden (1440×1600).
  Check every camera at 960×540 / 32 samples (5–10 s on Metal) before the 192-sample set (1920×1080: 26–64 s each).
  The Bash tool runs zsh: in a batch-render shell function `${5:+--hide "$5"}` stays one word, `render_cycles.py`
  rejects it and the loop carries on — count the `RENDERED` lines against the shot list (H2B lost the plan shot).
- Black patches in shaded corners (Cycles): two objects with coplanar faces (columns flush with the wall faces)
  shadow each other — inset the hidden one 3 mm (H2B `Columns_House`). Find the object by `scene.ray_cast` through
  the camera frame point.
- `setup_render()` (EEVEE, raytracing, 128 samples, AgX Medium High Contrast). Exposure 0; dark roofs need a dark
  material, not less exposure.
- `cam(name, loc, target, lens)`: exteriors at eye level 1.45–1.6 m, lens 24–26, `shift_y` ≈ 0.04–0.12 to keep verticals
  straight; interiors lens 15–16 from a doorway corner — check a wall isn't between camera and room.
- Top plan: `cam("Cam_TopPlan", (cx, cy, 30), (cx, cy, 0), ortho_scale=<house size + 1 m>)` and hide
  `Roof_Hip, Roof_CPAC_Tiles, Roof_Caps, Roof_Eave` (+ each wing's), `<carport roof>, Ceiling, <pendants>, <downlight objects>`.
  `shoot` stops on a misspelt hide name and on an unsaved .blend.
- `shoot(cam, "01_ภายนอก_หน้าบ้าน.png", hide=[...], subdir="renders/sales")`. An MCP call over 120 s moves to the
  background. Interiors/plain exteriors take ~30–55 s per 1920×1080 frame (2 shots per call); a landscaped exterior
  with alpha glass and displaced trees took 60–107 s (CM3) → **one shot per call**.
- Floor plan readable as a drawing: dark caps on the wall pieces that run floor-to-top (skip the pieces above and
  below openings so doors and windows show as gaps), hide the roofs, ceiling, porch beams and the sun for that shot.
- Open every saved image (`Read` the PNG) before reporting it.
- Save the .blend **after** creating cameras — `render_cycles.py` reads the file on disk and stops on a missing camera.
- Final set in **Cycles**: save, then `Bash` (run_in_background for full size)
  `Blender -b <file> -P scripts/render_cycles.py -- --cam <cam> --out <png> [--hide a,b] [--show c]`.
  On an Apple-silicon Mac (Metal GPU) 960x540 @128 samples took 6–8 s — real glass, GI and soft shadows for free compared
  with EEVEE's alpha-glass hack. Set `M_Glass` back to transmission 1.0 / alpha 1.0 for Cycles.
- Cutaway sets (structure/foundation/rebar/roof steel, E42 27 ต.ค.): a per-job wrapper (your project's own script) that sets `hide_render` per
  preset, then `exec`s `render_cycles.py`. Hiding a whole collection: loop over
  `list(coll.all_objects)` — `all_objects` is rebuilt on each visibility change, so a live loop stopped after 2 objects
  and the walls, furniture and trees stayed in the structure shot. Put a soil plane just under the lean concrete
  (`Ground_Dig`, Poly Haven `raked_dirt`), shown only in those presets, or the foundation floats over the sky.

CAD drawings (7b), SketchUp (7c), a site plan (7d): `references/visual-extras.md`.

### 8. Done
- [ ] `print(inward_meshes())` is empty (P-2389's old box helper built every box inside-out; fixed in helpers.py)
- [ ] every render viewed; sales set named `NN_<ภายนอก|ภายใน|ผังพื้น>_<มุม>.png`
- [ ] `bpy.ops.file.pack_all()` then save, so textures travel with the `.blend`
- [ ] reply lists file paths, what was assumed (dimensions read from images, fence/plot, tile profile) and limits
  (no cars, box furniture); sales images need the label "ภาพจำลองเพื่อการโฆษณา"
- [ ] BOQ from this model: measure the saved .blend headless (keep the object names above); the companion skill
  `nuea-ai-boq-takeoff`, when the user has it, does this and builds the workbook

## Workflow B: construction model, stage by stage

The model is the job site in miniature: every piece to its product's drawing, built in construction order, so what
is read from it is what gets ordered (a take-off script measures it headless). Reference implementation: E42 บ้านทรงประหยัด 42 ตร.ม.
(28–31 ต.ค. 69). Read `references/working-economy.md` and `references/construction-method.md` before the first stage.

**Hand-over to a BOQ.** The companion skill `nuea-ai-boq-takeoff` turns this model into a priced workbook. It reads
each stage's quantity table first and the saved `.blend` second, so keep three things fixed: collections named
`<PROJ> STnn <name>`; one `STnn_<name>_spec.md` per stage beside the `.blend`; and at the end of every spec a table
headed `## ปริมาณ` with the columns รายการ · ปริมาณ · หน่วย · นับจากอะไร (one row per thing that is bought or
paid for: concrete by pour, rebar by bar size in metres and in 10 m bars, bricks, tiles, pipes by size, points by
type). Quantities that changed in a later stage are corrected in the stage that owns them, not only in the later spec.

**Cost control without losing detail** (SS-02 measured 3,139 turns and 1.7 B cache-read tokens in one session): one stage per
session with its spec as the handoff · drawings read once into `FACTS.md` · real product sizes before any route · `probe.py`
and formulas instead of reasoning numbers out · `checks.each` so one run lists every fault · iterate on a base file, filtered
output · only the touched mutations until the stage closes · stop after three runs on the same assert and change the design.

Order: ST00 grid · ST01 footings · ST02 stubs · ST03 ground beams · ST04 slab · ST05 columns · ST06 walls + wall
plate · ST07 roof frame → fascia → covering · ST08 ceilings · ST09 primer · ST10 paint coat 1 · ST11 tiles · ST12
electrical · ST13 paint coat 2 · ST14 doors, windows, aluminium · ST15 exterior mouldings (when the drawings have
them) · ST16 sanitary pipes and tanks · ST17 sanitary ware, counters, bath accessories · ST18 the rest of the BOQ
(termite system, skirting, flashing, service hatch; roof insulation is ST08's wool unless the drawings ask for foil).
ST16–ST18 all read `references/stage-sanitary.md`; the other stages read their own `references/stage-*.md`;
`references/boq-coverage.md` says which BOQ lines each one feeds. Build order may differ from site order (SS-02 built
ST09 → ST14 → ST15 → ST11 → ST10 → ST12 → ST13): say so in each spec, and keep the site order in its "ส่งต่อ".

Per stage:

1. **Spec.** Ask the stage's products, sizes, colours and positions before modelling; when the model and an existing
   BOQ disagree, ask which wins. Done when every input is the user's answer or an assumption written as *assumed* in the
   stage's spec file (`STnn_<name>_spec.md` in the project).
2. **Build.** One module and one collection per stage: real pieces at product size, openings from the maker's rough
   opening, every span another stage depends on derived (never typed twice). Done when the build runs from the saved
   file headless and live with no duplicate objects.
3. **Selfcheck, read back from the model.** Each quantity against an independent measure, nothing inside another
   stage's piece (meshes and curves), take-off rows against what they count. Done when this stage's selfcheck and
   every earlier stage's pass on the rebuilt model.
4. **Mutations.** One per rule, each caught by its own message, clean controls passing, undo verified. Done when the
   suite reports nothing missed, and every suite whose module you touched still passes (whole suites once, at the close).
5. **Close.** Review the diff, back up the scripts (an old .blend is rebuilt from them, don't keep copies), save, log the
   stage in its spec file with its `## ปริมาณ` table and a handoff for the next session, report in Thai with the quantities and what was assumed,
   then stop for the user's check and start the next stage in a fresh session.

## Blender shortcuts
- Move `G` (`G X/Y/Z` locks an axis), rotate `R`, scale `S`, hide `H` / unhide `Alt+H`, camera view `Numpad 0`,
  top view `Numpad 7`. `H` hides in the viewport only — renders still show the object (that is how the soffit
  "disappeared" in P-2389).

## New lessons
Add each new gotcha where its branch lives — `SKILL.md` for Workflow A, the matching `references/` file for a stage or the method — with the job it came from, not to memory.
