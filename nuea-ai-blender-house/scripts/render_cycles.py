"""Final-quality Cycles render outside the MCP session (no 120 s limit).

    /Applications/Blender.app/Contents/MacOS/Blender -b "<file>.blend" -P render_cycles.py -- \
        --cam EXT_01_Front_Hero --out "<dir>/01.png" [--w 1920 --h 1080 --samples 256] \
        [--hide "Roof_Hip,Roof_CPAC_Tiles"] [--show "Plan_WallCaps"] [--clay]

--clay: one matte grey material on every object (the file is not changed), same camera and light: a clay image of
the camera (a cover, a before/after, or product crops for an AI photoreal pass); samples default to 64. Glass and emissive
surfaces turn grey too, so interiors render darker and windows read as panels. Headless only: in the live MCP
session the override would stay on the scene and be saved with it.

Save the .blend in the live session first: this renders the file on disk. Run it with Bash
run_in_background and Read the PNG when it finishes. Uses the Apple GPU (Metal) when available.
"""
import argparse
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--cam", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--w", type=int, default=1920)
ap.add_argument("--h", type=int, default=1080)
ap.add_argument("--samples", type=int, default=None)   # 256, or 64 with --clay
ap.add_argument("--hide", default="")
ap.add_argument("--show", default="")
ap.add_argument("--clay", action="store_true")
a = ap.parse_args(argv)

s, O = bpy.context.scene, bpy.data.objects
names = [n for n in (a.hide + "," + a.show).split(",") if n]
missing = [n for n in names if n not in O]
assert not missing and a.cam in O, f"not in the file: {missing or a.cam}"
for n in filter(None, a.hide.split(",")):
    O[n].hide_render = True
for n in filter(None, a.show.split(",")):
    O[n].hide_render = False

s.render.engine = "CYCLES"
for o in bpy.data.objects:   # lamps with a radius render as glowing balls seen through windows (CM3 kitchen)
    if o.type == "LIGHT" and o.data.type in ("POINT", "SPOT", "AREA"):
        o.visible_camera = o.visible_transmission = False   # transmission: seen through window glass
dev = "CPU"
try:   # Apple Silicon: Metal GPU
    cp = bpy.context.preferences.addons["cycles"].preferences
    cp.compute_device_type = "METAL"
    cp.get_devices()
    for d in cp.devices:
        d.use = True
    dev = "GPU" if any(d.type == "METAL" for d in cp.devices) else "CPU"
except Exception as e:
    print("GPU setup failed, CPU render:", e)
s.cycles.device = dev
s.cycles.samples = a.samples or (64 if a.clay else 256)
s.cycles.use_adaptive_sampling = True
s.cycles.use_denoising = True
s.cycles.max_bounces, s.cycles.diffuse_bounces, s.cycles.glossy_bounces = 8, 3, 3
s.cycles.transmission_bounces, s.cycles.transparent_max_bounces = 8, 8
s.cycles.caustics_reflective = s.cycles.caustics_refractive = False   # glass stays clean, no fireflies
if a.clay:
    clay = bpy.data.materials.new("CLAY_OVERRIDE")
    clay.use_nodes = True
    bsdf = next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    for vl in s.view_layers:
        vl.material_override = clay
s.camera = O[a.cam]
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = a.w, a.h, 100
s.render.filepath = a.out
t = time.time()
bpy.ops.render.render(write_still=True)
print(f"RENDERED {a.out} on {dev} in {time.time() - t:.0f} s")
