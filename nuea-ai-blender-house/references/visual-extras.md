# Sales model extras

Read for furniture/plant/car assets, landscape, CAD drawings, SketchUp hand-off or placing the house on a site plan.

## 6b. Asset library (furniture, plants, cars)
- Revit families (.rfa) do not open in Blender; IKEA and 3D Warehouse models are not licensed for ads.
  Use **Sketchfab via the MCP add-on** (the user's free account → API Token, entered in the add-on preferences or
  saved to `~/.config/blender-mcp/sketchfab_token` with chmod 600 — never pasted in chat). Accept only CC0 / CC-BY.
- Load `assets.py` into a text block `house_assets` and exec it after `house_helpers`. Choose models with
  `search_assets(source="sketchfab", previews=…)` (short queries work; long ones return nothing), then
  `folder = sf_fetch(uid, "<category>")` and `place_asset(folder, "Name", (x, y, FL), rot_z, ("z", height))`.
  Size by the axis you know (height for sofas/fridges, length for beds/cars) — `"max"` gave a 56 cm tall sofa (CM3).
  Sketchfab glTFs face **−y**: back to a wall on −x → `rot_z=90`, on +x → `-90`, on +y → 0, on −y → 180.
  Poly Haven models: `place_collection(bpy.data.collections["<id>"], …)` then exclude that collection.
  Plant sets (anthurium, fern, pachira, periwinkle) import every variant side by side around the origin — move each
  variant (pachira: its bark + leaves pair) into its own `SRC_<v>` collection under one excluded `SRC_Plants`, then
  `place_collection(SRC_<v>, …, ("z", h))` per plant (H2B: 34 plants from 12 variants, linked mesh data).
  Some Poly Haven models carry Displace modifiers whose image sits in a temp folder that macOS later deletes —
  `pack_all` then fails with "source path … not found" (H2B anthurium): `pack_all` right after importing, or remove
  those modifiers (`bpy.data.user_map` on the missing image finds them). Sketchfab, like Poly Haven, is a per-scene
  toggle: `scene.blendermcp_use_sketchfab = True`.
  The RAV4 in the library runs along x: `rot_z=90` makes it run along y with the nose to −y (out to the road, H2B).
  The search API's licence field has only a label ("CC Attribution"); `assets.py` maps exact labels and refuses the rest.
  Before sharing a .blend, check the add-on did not store the token as a scene property.
  After downloads run `catalog()` → `~/3d-assets/CATALOG.md` (model · licence · credit line per item).
  CM3 library: modern sofa, queen bed, dining set, TV console, toilet, vanity, Italian cypress, Toyota RAV4 (all CC-BY).
  Check each placement with a 640x360 / 48-sample Cycles render (≈ 6 s) — the car model ran along x and came in
  rear-first, the first bedroom-3 camera stood against a wall. A low-poly appliance (fridge) read as a toy: build
  simple appliances from boxes in brushed steel instead.
- `render_cycles.py` hides point/spot/area lamps from camera and transmission rays (they showed as glowing balls
  through windows; camera rays alone are not enough behind glass).
- Interior shots: hide the soft-glow curtains that give windows their warm look from outside
  (`render_cycles.py --hide Curtain_…`); never hang sheers over a door (CM3 living room went white).
- Keep every download in `~/3d-assets/<category>/<source>-<slug>-<uid>/` with the model, `SOURCE.json`
  (source, uid, url, author, licence, date) and `ATTRIBUTION.txt` (CC-BY needs "<model> by <author>, CC BY x.x,
  Sketchfab <url>" wherever the image is used). Re-use the library before downloading again; the local copy is the source of truth.

## 6c. Landscape
- Poly Haven has no clipped hedges, palms or cypress. `hedge(name, path, w, h)` sweeps a rounded-rectangle section
  (a full-round bevel read as rolled turf); flowers and ground cover = `scatter()` (hair particles sit at the root,
  sunk in the soil). Cypress = stretched UV sphere + Subsurf + Displace (Clouds) with a dark `leaf_mat`.
- After placing trees, project each one into every camera (`world_to_camera_view`) — a copy left in the road
  showed up as branches across the aerial shot twice in CM3.
- `hedge()` as built is a smooth green box (H2B side yard read as a turf wall): convert it to a mesh
  (`bpy.data.meshes.new_from_object`), then Remesh voxel 0.04 → Displace (Clouds 0.12, strength 0.07, GLOBAL) →
  Smooth ×2 → a clipped but leafy hedge (~33 k faces for 17 m). A hedge right behind breeze-block fence panels shows
  green through the holes from the street — the strongest garden cue in the front shots.
- Thai tropical garden kit that worked (H2B): date palm feature tree in a round bed with a concrete edging ring
  (Sketchfab "Realistic Palm Tree Free", CC-BY; its fronds read dry brown — Hue/Sat 0.56 / 1.25 / 0.9 on the leaf
  materials), anthurium + fern underplanting, low beds either side of the path in front of the porch step (≤ 0.4 m,
  keep the step visible), periwinkle in front of the hedge, pachira as tall accents, stepping-stone slabs on the lawn
  (0.40 deep, 0.14 grass gaps) instead of a concrete strip, a side-yard slab path to the back door.

## 7b. CAD drawings (.dxf → .dwg)
- The user asked for "plot เป็น .dwg" (CM3). DWG is closed: write **DXF R12** with `scripts/drawings.py` (AutoCAD opens
  it directly; `SAVEAS` → DWG there). Only if the user wants .dwg files from here: ODA File Converter (free, the user
  installs it) — with no converter installed, LibreDWG's DWG writer is not reliable.
  `Blender -b <file> -P scripts/drawings.py -- --out <project>/drawings --name <code> [--section-y Y --section-x X]`
  (~2 s; `--skip "a*,b"` adds to the default skips). It writes `<out>/<code>_<view>.dxf` + `.svg` per view and
  `<code>_00_ALL_VIEWS.dxf`; turn each `.svg` into PNG with headless Chrome and look at every one before reporting.
  Put section planes through rooms, not along a wall line. It prints objects skipped as render-hidden: unhide what a
  cutaway render hid before drawing.
- How it works: model edges, hidden-line removal by ray casting, an edge kept only where the surface changes across it
  (outline, depth step, fold > 8°; caps 40° so bevel facets don't draw), section planes cut with `bisect_plane`.
- Gotchas found in CM3: use `view_layer.objects` (Poly Haven source models parked at the origin in an excluded
  collection showed in the elevation); match skips with fnmatch (a prefix test made "Car" drop "Carport");
  fence only in the top view; a wing roof 2 mm under the main roof needs occlusion tolerance 1 mm and the
  wing part under the main roof trimmed (`trim_roofs`) or the section shows the unbuilt half; drop partial
  visible pieces < 6 cm but keep whole short edges (arcs vanished otherwise); tile meshes and battens skipped.
- Validate with ezdxf in a scratch venv (`recover.readfile` + strict `readfile`: 0 errors) — never add it to the skill.
- Limits to state: no dimensions/hatching/annotation beyond the title, lines only; curves are segmented; hip caps
  show as short dashes at 1:100.

## 7c. Hand-off to SketchUp (.skp)
- The user asked for the whole model as .skp (CM3). Blender cannot write .skp (closed; SketchUp C SDK only) and Blender 5
  removed COLLADA. SketchUp Pro/Studio imports **GLB** with materials and textures (help.sketchup.com "Working with
  GLTF files"; STL works in every plan but loses materials). So: `Blender -b <file> --python-exit-code 1 -P scripts/export_sketchup.py --
  --out <project>/sketchup/<code>.glb` → the user does File > Import in SketchUp and saves .skp.
- Default leaves out library assets, roof tiles + battens and helpers: CM3 went from ~6.2 M faces to 59 k (29 MB).
  Library furniture/trees/cars are 100–600 k faces each and choke SketchUp — tell the user to use SketchUp components
  (3D Warehouse) there, or export them separately with `--with-assets`.
- Procedural base colours are flattened to the viewport colour (`diffuse_color`), so keep those colours meaningful.
- Check: re-import the GLB in an empty Blender (object/face counts, key objects present) and render one view.

## 7d. Put the house on a site plan
- The user's live Blender may hold another file with unsaved changes (`bpy.data.is_dirty`; CM3 was open, dirty, while
  the job was in the site file). Never open a file over it: do the whole job headless (`Blender -b`) and check with
  `render_cycles.py` stills; tell the user at the end.
- Read the site .blend first (headless print script): P1 turns the whole plan 8° through an empty `P1_ROOT`, plots are
  meshes in its local frame (`Plot_04` = x 24.82..37.23, y 0 rear .. 14.49 front, surface z 0.02), and the 2-bed
  houses are collection instances of an excluded `LIB_House_2Bed_Exterior`. Follow the file's own pattern.
- **Plot numbers differ between sheets.** The architect's "ผังบริเวณแปลง 4" drew its setbacks on the plot the deed
  calls 3 (its neighbours: the rear boundary kinks over the 8/9 boundary; deed 4 kinks over 9/10 where plot 10 starts).
  Identify a plot by geometry against the deed subdivision plan (`ผังที่ดินแบ่งขาย`), use the deed number (what
  customers see), and tell the user about the mismatch. Plots 2–5 are the same size, so moving is one `--loc` change.
- Setbacks from the architect's site sheet are to the wall faces (1.00 + 10.40 + 1.03 ≈ the 12.41–12.51 plot). Map the house
  frame to the plot's local frame: front −y → plot front +y = `--rot 180`; origin = (west edge + D-face x + setback,
  front edge + front-fence y of the house file). Print every gap and compare with the sheet before placing.
- `site_place.py` appends `<proj>, Walls, Openings, Site, Landscape` (no Interior: invisible from outside, heavy),
  drops cameras, lights, the house file's own ground/road/background trees and the hidden roof steel, decides
  keep/drop for every object **before** removing any (a removed parent orphans its children, which would then pass
  the name test as loose parts, e.g. a background tree's 8 meshes), and excludes the LIB collection in every view
  layer. Next plot = same call, new `--inst/--loc` (the LIB is reused; `--house/--drop` are then ignored).
  Try on a copy first (`--out` in the scratchpad), render, then run on the real file. Saving in place first copies
  the file once to `<name>.pre_site_place.blend` — `.blend1` holds one version only, a second run would lose the
  original.
- `site_place.py` only appends and places. The fence and the lawn below are per-job code kept with the project:
  CM3's `refit_fence` / `yard_lawn` are in the project's placing script — adapt them.
- The house file's fence follows the architect's slightly skewed survey; the deed rectangle differs by 0.05–0.15 m.
  CM3: rebuilt `Fence_Walls` as boxes on the deed lines (side/rear 0.12, front 0.15, corner rule) and moved each
  post island perpendicular onto its line (44 posts). Plots 2–5 share that rectangle, so the P1 LIB fits them all;
  a plot of another shape (corner plots 1, 6, 7) needs its own fence → its own `--lib` name.
- z: the plot surface is at 0.02 and the house file's paving/driveway sit at 0..0.03 → instance z = 0.02 and a lawn
  plane at house z 0.01 (the site's `M_Lawn` is a different, flat material) so nothing is coplanar.
- Cameras: a plot hero from the road side (front × 26 + side × 16, 14 m up, lens 32), an eye-level front across the
  road (level camera, `shift_y` 0.10) and an ortho top turned by the root's rotation. Wide existing cameras that see
  the rear (SW/SE aerials) still show the house; check them for trees in front.
- Size: the site file went 51 → 128 MB (roof tiles, car, packed Poly Haven textures). Purge orphans before saving
  (`site_place.py` does): the dropped objects' materials and packed images were saved too and added 24 MB.
- One house on many plots of different shapes (P1 plots 1–14, 21 ต.ค.; a project script):
  a fence inside the LIB doubles every shared wall between neighbours. Drop the LIB's fence/lawn and build one site
  fence mesh from the plot lines (each boundary once, gaps from the house's driveway/gate x) plus one lawn mesh.
  Landscape that overflows a narrow or slanted plot: chop big meshes into 1.2 m cells (small loose parts go whole into
  their centre's cell; splitting flower beds by loose part made 2,700 objects), test each piece against every plot
  polygon (trees by trunk centre ≥ 0.3 m inside, paving may reach the line, the rest ≤ 7 cm past it = inside the fence
  wall), and link each distinct keep-set into its own collection. An object can sit in many collections, so no copies.
- Plot drawn mirrored on the site plan (A-03 plot 7): a negative-determinant `matrix_basis` is stored as scale
  (−1,−1,−1) + 180° about x. Set `scale = (−1, 1, 1)` and the z rotation instead. Check the carport and eaves against a
  slanted plot line before placing: `carport_classic` projects 2.1 m past the front wall. The user wanted plot 7's carport
  anyway: shorten a copy by cut-and-slide (bisect at two y planes, delete the band, slide the front assembly back,
  weld, assert no open seam edges), so columns, fillets and cornice stay as on the other plots
  (a project script). Copy with `o.copy()` + new `.data`: `objects.new(name, me)` dropped the
  sheet's Solidify modifier.
