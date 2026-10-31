import bpy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
build_ceilings(); build_primer(); print(selfcheck_primer()); build_finish(); print(selfcheck_finish())
def expect(name, fn):
    try:
        fn(); selfcheck_finish(); print("MISSED", name)
    except AssertionError as e:
        print("caught", name, "|", str(e)[:90])
    build_finish()
def setp(n, k, v):
    def f():
        bpy.data.objects[n].data[k] = v
    return f
expect("Jotashield rate 43.75 (TOA)", setp("PF_Walls_out", "per_bucket", 43.75))
expect("Easy Ceiling rate 35", setp("PF_Ceilings", "per_bucket", 35.0))
expect("outside walls short 5 m²", lambda: bpy.data.objects["PF_Walls_out"].data.__setitem__("area", bpy.data.objects["PF_Walls_out"].data["area"] - 5))
def lift():
    o = bpy.data.objects["PF_Ceilings"]; o.location.z += 0.01; bpy.context.view_layer.update()
expect("ceiling coat above its primer", lift)
def fewer():
    old = FINISH["cover"]; FINISH["cover"] = 35.0; FINISH["per_bucket"] = 35.0 * 2.5 / 2; build_finish(); FINISH["cover"] = old; FINISH["per_bucket"] = 35.0
expect("coverage from the TOA sheet", fewer)
expect("wall coat one step into the plaster", lambda: build_finish(-1.0))
def in_jotashield():   # the old spec: Jotashield inside too (Jotun: exterior only)
    old = FINISH["per_bucket_in"]; FINISH["per_bucket_in"] = 35.0; build_finish(); FINISH["per_bucket_in"] = old
expect("inside walls at the Jotashield rate", in_jotashield)
def paint_splash():
    t0 = tiled_wall_boxes; globals()["tiled_wall_boxes"] = lambda: []; build_finish(); globals()["tiled_wall_boxes"] = t0
expect("paint on the kitchen splash", paint_splash)
print(selfcheck_finish()); print("TESTS DONE")
