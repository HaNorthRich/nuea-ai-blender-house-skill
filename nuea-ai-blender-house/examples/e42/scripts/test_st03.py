import bpy
E42_UPTO = "e42_struct.py"
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
print("GRID", build_grid(), "FOOTINGS", build_footings(), "STUBS", build_stubs(), "GB", build_ground_beams())
for cn in (C_FOOT, C_STUB, C_GB):
    print(report(cn))
print(selfcheck())
n0 = len(_coll(C_GB).objects)   # joints below GL now carry a trench too (lowered beams round the bath)
again = build_ground_beams()   # re-run must replace, not duplicate
assert len(_coll(C_GB).objects) == n0, (len(_coll(C_GB).objects), n0)
assert not [d.name for d in (*bpy.data.meshes, *bpy.data.curves) if d.name.startswith(("GB1_", "J1_")) and "." in d.name]
print("joint data:", sorted({o.data.name for o in _coll(C_GB).objects if o.name.startswith("J1_") and o.data}))
print("lean pieces:", {o.name: len(o.data.vertices) // 8 for o in _coll(C_GB).objects if o.name.endswith("_Lean")})
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


must_fail("beam slid 2 cm into a joint", "GB1_C1-C2", "x", 0.02)
must_fail("joint raised 1 cm", "J1_C1", "z", 0.01)
must_fail("stub sunk 5 cm", "P1_D1", "z", -0.05)
print(selfcheck())
print("NOT SAVED (test only)")
