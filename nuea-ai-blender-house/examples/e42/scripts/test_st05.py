import bpy
E42_UPTO = "e42_struct.py"
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
print("GRID", build_grid(), "FOOTINGS", build_footings(), "STUBS", build_stubs(), "GB", build_ground_beams(),
      "COL", build_columns(), "SLAB", build_ground_slab())
for cn in STAGES:
    print(report(cn))
print(selfcheck())
again = build_columns()   # re-run must replace, not duplicate
assert len(_coll(C_COL).objects) == again * 4, len(_coll(C_COL).objects)
assert not [d.name for d in (*bpy.data.meshes, *bpy.data.curves) if d.name.startswith("C1_") and "." in d.name]
print("column data:", sorted({o.data.name for o in _coll(C_COL).objects if o.data}))
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


must_fail("column lifted 2 cm", "C1_D2", "z", 0.02)
must_fail("column slid 3 cm", "C1_E3", "x", 0.03)
must_fail("secondary beam slid 2 cm", "GB1_C1-C2", "x", 0.02)
must_fail("joint without stub raised 1 cm", "J1_C1", "z", 0.01)
must_fail("house slab lifted 1 cm", "GS1_House", "z", 0.01)
print(selfcheck())
print("NOT SAVED (test only)")
