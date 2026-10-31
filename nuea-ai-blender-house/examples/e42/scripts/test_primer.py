import bpy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
build_ceilings(); print(build_primer()); print(report(C_PAINT)); print(selfcheck_primer())
def expect(name, fn):
    try:
        fn(); selfcheck_primer(); print("MISSED", name)
    except AssertionError as e:
        print("caught", name, "|", str(e)[:90])
    build_primer()
def raise_film():
    o = bpy.data.objects["PR_Walls_in"]; o.location.z += 0.05; bpy.context.view_layer.update()
expect("inside primer 5 cm above the ceilings", raise_film)
def out_up():
    o = bpy.data.objects["PR_Walls_out"]; o.location.z += 0.05; bpy.context.view_layer.update()
expect("outside primer above the soffit", out_up)
def wrong_qty():
    bpy.data.objects["PR_Walls_Qty"].data["area"] *= 0.9
expect("wall primer not the plastered area", wrong_qty)
def ceil_rate():
    bpy.data.objects["PR_Ceilings"].data["per_bucket"] = 100.0
expect("ceiling rate not 87.5", ceil_rate)
def ceil_area():
    bpy.data.objects["PR_Ceilings"].data["area"] -= 1.0
expect("ceiling primer short 1 m²", ceil_area)
print(selfcheck_primer()); print("TESTS DONE")
