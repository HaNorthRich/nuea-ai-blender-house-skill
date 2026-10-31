import bpy
E42_UPTO = "e42_struct.py"
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
print("GRID", build_grid(), "FOOTINGS", build_footings(), "STUBS", build_stubs())
print(report(C_FOOT))
print(report(C_STUB))
print(selfcheck())
for g, v in sorted(_stub_levels().items()):
    print(g, [round(x, 3) for x in v])
again = build_stubs()   # re-run must replace, not duplicate
assert len(_coll(C_STUB).objects) == again * 4, len(_coll(C_STUB).objects)
assert not [d.name for d in (*bpy.data.meshes, *bpy.data.curves) if d.name.startswith(("P1_", "F1_")) and "." in d.name]
print("shared data:", sorted({o.data.name for o in _coll(C_STUB).objects if o.data}))
print(selfcheck())
# a stub sunk into its footing must fail the overlap check
o = bpy.data.objects["P1_A1"]
o.location.z -= 0.05
bpy.context.view_layer.update()
try:
    selfcheck()
    raise SystemExit("overlap not caught")
except AssertionError as e:
    print("caught:", str(e)[:80])
o.location.z += 0.05
o.location.x += 0.05   # sideways: volume and formwork unchanged, must still fail
bpy.context.view_layer.update()
try:
    selfcheck()
    raise SystemExit("sideways move not caught")
except AssertionError as e:
    print("caught:", str(e)[:80])
print("NOT SAVED (test only)")
