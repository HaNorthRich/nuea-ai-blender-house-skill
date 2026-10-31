import bpy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
lc = bpy.context.view_layer.layer_collection.children
build_ceilings(); print(selfcheck_ceilings())
def expect(name, fn):
    try:
        fn(); selfcheck_ceilings(); print("MISSED", name)
    except AssertionError as e:
        print("caught", name, "|", str(e)[:90])
    build_ceilings()
def param(d, k, v):
    def f():
        old = d[k]; d[k] = v; build_ceilings(); d[k] = old   # build wrong, judge against the spec
    return f
def rooms(room, kind):
    def f():
        old = ROOMS[room]; ROOMS[room] = (old[0], kind); build_ceilings(); ROOMS[room] = old
    return f
def move(n, dz):
    def f():
        bpy.data.objects[n].location.z += dz; bpy.context.view_layer.update()
    return f
expect("ceiling h 2.70", param(CEIL, "h", 2.70))
expect("bath h 2.80", param(CEIL, "h_bath", 2.80))
expect("cross @ 0.60", param(CEIL, "cross", 0.60))
expect("main @ 1.20", param(CEIL, "main", 1.20))
expect("soffit at fascia bottom", param(CEIL, "above_fascia", 0.0))
expect("bath ordinary gypsum", rooms("Bath", "gyp"))
expect("hangers dropped 5 mm", move("CL_Living_Hangers", -0.005))
expect("boards 1.20 x 4.80", param(CEIL, "board", (1.20, 4.80, 0.009)))
expect("porch hangers dropped 5 mm", move("CL_Porch_Hangers", -0.005))
expect("soffit boards 1 cm short", move("CL_Soffit_Boards", 0.0) if False else (lambda: (bpy.data.objects["CL_Soffit_Boards"].location.__setitem__(0, 0.01), bpy.context.view_layer.update())))
expect("soffit runners shifted 10 cm", lambda: (bpy.data.objects["CL_Soffit_Runners"].location.__setitem__(0, -0.10), bpy.context.view_layer.update()))
def old_bug():   # put back: a wall-line runner along the whole eave, from u = 0 into the next eave
    o = bpy.data.objects["CL_Soffit_Runners"]
    bm = bmesh.new(); bm.from_mesh(o.data)
    a, e, w, depth, L = _soffit_frame()[0]
    _cline(bm, tuple(a + w * (depth - 0.0175)), tuple(a + e * (L - depth) + w * (depth - 0.0175)), _soffit_z() + CEIL["soffit"][2])
    bm.to_mesh(o.data); bm.free()
expect("soffit runner past the corner (old bug 001)", old_bug)
def porch_vent():
    bpy.data.objects["CL_Porch_Boards"].data["type"] = "CB3"
expect("porch vented board", porch_vent)
def no_hatch():
    global HATCH_ROOM
    old = HATCH_ROOM; HATCH_ROOM = "none"; build_ceilings(); HATCH_ROOM = old
expect("no service hatch", no_hatch)
def porch_open_joints():   # spec 29 ต.ค.: the porch had 5 mm open joints (grooves)
    g0 = _grid
    def g(c, tag, rect, cut, zc, board, gap, *a, **k):
        return g0(c, tag, rect, cut, zc, board, CEIL["gap"] if tag == "Porch" else gap, *a, **k)
    globals()["_grid"] = g; build_ceilings(); globals()["_grid"] = g0
expect("porch open joints", porch_open_joints)
def no_vents():   # spec 29 ต.ค.: the outer corner lost its vents
    m0 = _minus
    globals()["_minus"] = lambda r, boxes: [r] if boxes and abs(boxes[0][4] - boxes[0][1] - 0.006) < 1e-6 else m0(r, boxes)
    build_ceilings(); globals()["_minus"] = m0
expect("soffit without vents", no_vents)
def one_end_flat():   # the first board of every eave flat, so each corner keeps one vented eave only
    m0 = _minus
    globals()["_minus"] = lambda r, boxes: [r] if boxes and abs(boxes[0][4] - boxes[0][1] - 0.006) < 1e-6 and r[0] == 0.0 else m0(r, boxes)
    build_ceilings(); globals()["_minus"] = m0
expect("one eave flat at each corner", one_end_flat)
def drop_spring():
    o = bpy.data.objects["CL_Living_Springs"]; o.data["count"] = o.data["count"] - 1
expect("a spring joiner short", drop_spring)
print(selfcheck_ceilings()); print("TESTS DONE")
