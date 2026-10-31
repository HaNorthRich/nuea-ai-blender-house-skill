import bpy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
print(selfcheck_finish()); print(build_coat2()); print(selfcheck_coat2())
def expect(name, fn):
    try:
        fn(); selfcheck_coat2(); print("MISSED", name)
    except AssertionError as e:
        print("caught", name, "|", str(e)[:100])
    build_coat2()
D = lambda n: bpy.data.objects[n].data
expect("coat 2 one step into the wall", lambda: build_coat2(-1.0))
expect("coat 2 under coat 1, on the primer", lambda: build_coat2(0.0))
expect("coat 2 on top of coat 1 (no step)", lambda: build_coat2(0.5))
expect("coat 2 two steps out", lambda: build_coat2(1.5))
expect("outside coat 2 short 5 m²", lambda: D("PC2_Walls_out").__setitem__("area", D("PC2_Walls_out")["area"] - 5))
expect("coat 2 adds a take-off row", lambda: D("PC2_Walls_in").__setitem__("element", "paint"))
def splash():
    t0 = tiled_wall_boxes; globals()["tiled_wall_boxes"] = lambda: []; build_coat2(); globals()["tiled_wall_boxes"] = t0
expect("coat 2 on the kitchen splash", splash)
def drop_face():   # one wall face left unpainted, its area put back by hand
    f0 = _faces; globals()["_faces"] = lambda: f0()[1:]; build_coat2(); globals()["_faces"] = f0
    for s in ("in", "out"):
        D(f"PC2_Walls_{s}")["area"] = D(f"PF_Walls_{s}")["area"]
expect("one wall face missing coat 2", drop_face)
def extra():
    bpy.data.collections[C_COAT2].objects.link(bpy.data.objects.new("PC2_Stray", None))
def twice():   # one face painted twice, another of the same size and side left bare
    f0 = _faces; L = list(f0())
    j, i = next((j, i) for j in range(len(L)) for i in range(j + 1, len(L)) if L[j][2] == L[i][2]
                and abs(_poly_area(L[j][0]) - _poly_area(L[i][0])) < 1e-9 and (sum(L[j][0], Vector()) - sum(L[i][0], Vector())).length > 0.1)
    globals()["_faces"] = lambda: L[:i] + [L[j]] + L[i + 1:]; build_coat2(); globals()["_faces"] = f0
expect("one face painted twice, its twin bare", twice)
expect("a stray object in coat 2", extra)
for o in [o for o in bpy.data.objects if o.name == "PC2_Stray"]:
    bpy.data.objects.remove(o)
print(selfcheck_coat2())
# hangers: the ceiling check still passes with coat 2 standing
print(selfcheck_ceilings() if "selfcheck_ceilings" in globals() else "no ceiling check")
print("TESTS DONE")
