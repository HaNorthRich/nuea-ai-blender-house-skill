import bpy
E42_UPTO = "e42_struct.py"
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
print("GRID", build_grid())
print("FOOTINGS", build_footings())
print(report())
print(selfcheck())
again = build_footings()   # re-run must replace, not duplicate
assert len(_coll(C_FOOT).objects) == again * 6, len(_coll(C_FOOT).objects)
assert not [m.name for m in bpy.data.meshes if m.name.startswith("F1_") and "." in m.name]
print(selfcheck())
lc = _find_lc(bpy.context.view_layer.layer_collection, C_OLD)
if lc:   # (only a file that grew from a massing model has its old structure)
    print("OLD excluded:", lc.exclude, [o.name for o in bpy.data.collections[C_OLD].objects][:10])
print("NOT SAVED (test only)")
