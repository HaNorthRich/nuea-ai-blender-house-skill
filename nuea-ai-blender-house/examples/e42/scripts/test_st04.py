import bpy
E42_UPTO = "e42_struct.py"
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
print("GRID", build_grid(), "FOOTINGS", build_footings(), "STUBS", build_stubs(), "GB", build_ground_beams(),
      "SLAB", build_ground_slab())
for cn in (C_GB, C_SLAB):
    print(report(cn))
print(selfcheck())
again = build_ground_slab()   # re-run must replace, not duplicate
assert len(_coll(C_SLAB).objects) == again * 4 + sum(o.name.endswith("_Curb") for o in _coll(C_SLAB).objects), len(_coll(C_SLAB).objects)
assert not [d.name for d in (*bpy.data.meshes, *bpy.data.curves) if d.name.startswith("GS1_") and "." in d.name]
print({o.name: len(o.data.splines) for o in _coll(C_SLAB).objects if o.name.endswith("_Mesh")})
print(selfcheck())


def must_fail(what, obj, attr, delta):
    o = bpy.data.objects[obj]
    v = getattr(o.location, attr)
    setattr(o.location, attr, v + delta)
    bpy.context.view_layer.update()
    try:
        selfcheck()
        raise SystemExit(f"not caught: {what}")
    except AssertionError as e:
        print(f"caught {what}:", str(e)[:90])
    setattr(o.location, attr, v)
    bpy.context.view_layer.update()


must_fail("house slab lifted 1 cm", "GS1_House", "z", 0.01)
must_fail("porch slab slid 5 cm", "GS1_Porch", "x", 0.05)
must_fail("beam slid 2 cm into a joint", "GB1_C1-C2", "x", 0.02)
bpy.data.objects["GS1_House_Curb"].data["element"] = "fill"   # soil compacted over the lowered beams
try:
    selfcheck(); raise SystemExit("not caught: no curb")
except AssertionError as e:
    print("caught no curb over the lowered beams:", str(e)[:90])
build_ground_slab()
print(selfcheck())
print("NOT SAVED (test only)")
