import bpy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
build_grid(); build_footings(); build_stubs(); build_ground_beams(); build_columns(); build_ground_slab(); build_walls(); build_ceilings()
build_steps(); build_tiles(); print(selfcheck_tiles())
def expect(name, fn, rebuild=True):
    try:
        fn(); selfcheck_tiles(); print("MISSED", name)
    except AssertionError as e:
        print("caught", name, "|", str(e)[:100])
    build_steps(); build_tiles()
def param(d, k, v):
    def f():
        old = d[k]; d[k] = v; build_steps(); build_tiles(); d[k] = old
    return f
def sub(d, k, kk, v):
    def f():
        old = d[k][kk]; d[k][kk] = v; build_steps(); build_tiles(); d[k][kk] = old
    return f
expect("floor joints 3 mm drawn, spec 2", lambda: (FT["floor"].__setitem__("joint", 0.003), build_tiles(), FT["floor"].__setitem__("joint", 0.002)))
expect("tiles 80 x 80 drawn", lambda: (FT["floor"].__setitem__("size", (0.80, 0.80, 0.0095)), build_tiles(), FT["floor"].__setitem__("size", (0.60, 0.60, 0.0095))))
expect("splash 60 cm", param(KITCHEN, "splash", 0.60))
expect("shower waterproofing 1.20", param(WP, "shower", 1.20))
expect("walls 30 cm short of the ceiling", lambda: (CEIL.__setitem__("h_bath", 2.30), build_tiles(), CEIL.__setitem__("h_bath", 2.60)))
expect("4 risers of 10 cm drawn", lambda: (STEPS.__setitem__("rise", 4), build_steps(), build_tiles(), STEPS.__setitem__("rise", 3)))
def no_spare():
    global SPARE
    old = SPARE; SPARE = 0.0; build_tiles(); SPARE = old
expect("count without the 3 % spare", no_spare)
def skirt_door():   # one more run, as if laid across the bath door
    me = bpy.data.objects["FT_Skirting"].data; me["lens"] = list(me["lens"]) + [0.77]
expect("skirting across a door", skirt_door)
def tiles_up():
    o = bpy.data.objects["FT_floor_Tiles"]; o.location.z += 0.003; bpy.context.view_layer.update()
expect("house tiles 3 mm high", tiles_up)
def drop_tile():
    import bmesh
    o = bpy.data.objects["FT_bath_Tiles"]; bm = bmesh.new(); bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table(); bmesh.ops.delete(bm, geom=bm.verts[:8], context="VERTS"); bm.to_mesh(o.data); bm.free()
expect("a bath floor tile missing", drop_tile)
def wall_tile_missing():
    import bmesh
    o = bpy.data.objects["FT_wall_Tiles"]; bm = bmesh.new(); bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table(); bmesh.ops.delete(bm, geom=bm.verts[80:88], context="VERTS"); bm.to_mesh(o.data); bm.free()
expect("a wall tile missing", wall_tile_missing)
def ledge_back():   # spec 29 ต.ค.: the old bath ledge — bath floor zone back between the beams
    ZONES["Bath"] = ([(0.10, 3.10, 2.90, 4.40)], 0.25); build_ground_slab(); build_tiles()
expect("bath floor between the beams only (old ledge)", ledge_back)
ZONES["Bath"] = ([(-0.025, 3.045, 3.025, 4.455)], 0.25); build_ground_slab(); build_tiles()
import bmesh
def edit(name, fn):
    o = bpy.data.objects[name]; bm = bmesh.new(); bm.from_mesh(o.data); fn(bm); bm.to_mesh(o.data); bm.free(); o.data.update()
def porch_under_nose(bm):   # a porch tile run on under the nosing
    for v in bmesh.ops.create_cube(bm, size=1.0)["verts"]:
        v.co = (4.0 if v.co.x < 0 else 4.3, -0.10 if v.co.y < 0 else -0.0647, 0.3903 if v.co.z < 0 else 0.40)
expect("porch tile under the nosing", lambda: edit("FT_porch_Tiles", porch_under_nose))
def wp_long_face_low(bm):   # a long face given 0.30 inside the shower
    for v in bm.verts:
        if v.co.z > FL_BATH + 1.0 and abs(v.co.y - 3.045) < 0.003:
            v.co.z = FL_BATH + WP["up"]
def wp_short_zone():   # the long faces built with 0.30 in the shower (built with a narrower zone)
    global SHOWER
    s0 = SHOWER; SHOWER = (2.95, 3.10); build_tiles(); SHOWER = s0
expect("shower long walls coated 0.30 only", wp_short_zone)
def d4_gap(bm):   # the threshold stops at the plaster, 12 mm short over the riser tiles
    for v in bm.verts:
        if abs(v.co.x - (3.025 - 0.012)) < 1e-5 and 3.35 < v.co.y < 4.15:
            v.co.x = 3.025
expect("bath door threshold short of the riser", lambda: edit("FT_floor_Tiles", d4_gap))
def nose_moved():
    o = bpy.data.objects["FT_Nosing"]; o.location.y -= 0.02; bpy.context.view_layer.update()
expect("nosing off its nose", nose_moved)
def riser_in_concrete():
    o = bpy.data.objects["FT_porch_Steps"]; o.location.y += 0.01; bpy.context.view_layer.update()
expect("step tiles into the step concrete", riser_in_concrete)
build_tiles()
print(selfcheck_tiles()); print("TESTS DONE")
