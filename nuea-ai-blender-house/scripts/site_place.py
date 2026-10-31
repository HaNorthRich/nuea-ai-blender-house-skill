"""Put a house built with this skill on a plot of a site-plan .blend, headless.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<site>.blend" --python-exit-code 1 -P site_place.py -- \
        --house "<house>.blend" --proj CM3 --lib LIB_House_CM3_Exterior --inst House_CM3_P04 \
        --parent P1_ROOT --into P1_Houses_3Bed_CM3 --loc 36.145,11.67,0.02 --rot 180 [--out trial.blend]

The first run appends the house exterior (<proj>, Walls, Openings, Site, Landscape; no Interior) into
one LIB collection excluded from the view layer; every run adds one collection-instance empty, so the
next plot is the same call with another --inst/--loc (LIB is reused, not appended again).
--loc/--rot are in the parent's local frame (the site root carries the plan's rotation). Cameras and
lights are always dropped; --drop takes fnmatch patterns on the top-level object name. An existing
--inst of the same LIB is replaced (= re-place that plot); any other object with that name stops the run.
Only appending + placing: a fence refit to the deed lines or a yard lawn is per-job code (SKILL.md 7d).
Without --out it saves the opened file, after copying the file on disk once to <name>.pre_site_place.blend
(.blend1 keeps one version only, so a second run would lose the original).
"""
import argparse
import fnmatch
import math
import os
import re
import shutil
import sys

import bpy
from mathutils import Matrix

DROP = ("Plan_WallCaps,Roof*_Frame,Roof*_Battens,Ground,Road,Road_Curb,"
        "island_tree_*,Tree_TreeLine_*,Tree_Cypress_BG_*")   # CM3: helpers, hidden steel, its own site/background

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
for k in ("--house", "--proj", "--lib", "--inst", "--parent", "--into", "--loc"):
    ap.add_argument(k, required=True)
ap.add_argument("--rot", type=float, default=0.0, help="degrees about z")
ap.add_argument("--drop", default=DROP)
ap.add_argument("--out", default="")
a = ap.parse_args(argv)


def base(n):   # name without the .001 that append adds on a clash
    return re.sub(r"\.\d{3}$", "", n)


def append_lib():
    cols = [a.proj] + [f"{a.proj} {s}" for s in ("Walls", "Openings", "Site", "Landscape")]
    with bpy.data.libraries.load(a.house, link=False) as (src, dst):
        missing = [c for c in cols if c not in src.collections]
        assert not missing, f"not in the house file: {missing}"
        dst.collections = cols
    pats = [p for p in a.drop.split(",") if p]
    objs = {o for c in dst.collections for o in c.objects}

    def keep(o):
        top = o
        while top.parent:
            top = top.parent
        if "CAMERA" in (o.type, top.type) or "LIGHT" in (o.type, top.type):
            return False
        return not any(fnmatch.fnmatchcase(base(top.name), p) for p in pats)

    decide = {o: keep(o) for o in objs}   # decide first: removing a parent orphans its kids
    lib = bpy.data.collections.new(a.lib)
    bpy.context.scene.collection.children.link(lib)
    for o in (o for o, k in decide.items() if k):
        lib.objects.link(o)
    for o in (o for o, k in decide.items() if not k):
        bpy.data.objects.remove(o)
    for c in dst.collections:
        bpy.data.collections.remove(c)
    for vl in bpy.context.scene.view_layers:   # an included LIB renders the house again at the origin
        next(l for l in vl.layer_collection.children if l.name == a.lib).exclude = True
    print(f"LIB {a.lib}: kept {sum(decide.values())}, dropped {len(decide) - sum(decide.values())}")
    return lib


if not a.out:
    bak = bpy.data.filepath[:-len(".blend")] + ".pre_site_place.blend"
    if not os.path.exists(bak):
        shutil.copy2(bpy.data.filepath, bak)
        print("BACKUP", bak)
lib = bpy.data.collections.get(a.lib)
if lib:
    assert lib.objects, f"{a.lib} exists but is empty"
    print(f"LIB {a.lib} reused ({len(lib.objects)} objects) - --house/--proj/--drop ignored")
else:
    lib = append_lib()
old = bpy.data.objects.get(a.inst)
if old:
    if not (old.type == "EMPTY" and old.instance_type == "COLLECTION" and old.instance_collection == lib):
        raise SystemExit(f"{a.inst} exists and is not an instance of {a.lib}; pick another --inst")
    bpy.data.objects.remove(old)
parent = bpy.data.objects[a.parent]
into = bpy.data.collections.get(a.into)
if not into:
    into = bpy.data.collections.new(a.into)
    (parent.users_collection[0] if parent.users_collection else bpy.context.scene.collection).children.link(into)
inst = bpy.data.objects.new(a.inst, None)
inst.instance_type, inst.instance_collection, inst.empty_display_size = "COLLECTION", lib, 2
into.objects.link(inst)
inst.parent = parent
inst.matrix_parent_inverse = Matrix.Identity(4)
inst.location = tuple(float(v) for v in a.loc.split(","))
inst.rotation_euler = (0, 0, math.radians(a.rot))
print(f"PLACED {a.inst} at {tuple(inst.location)} rot {a.rot} in {a.parent} frame")

# dropped objects leave 0-user meshes that still count as users of their materials, so those
# materials and their packed images get saved (CM3: +7 materials, ~24 MB); a later normal save drops them
bpy.data.orphans_purge(do_recursive=True)
if a.out:
    bpy.ops.wm.save_as_mainfile(filepath=a.out, copy=True)
else:
    bpy.ops.wm.save_mainfile()
print("SAVED", a.out or bpy.data.filepath)
