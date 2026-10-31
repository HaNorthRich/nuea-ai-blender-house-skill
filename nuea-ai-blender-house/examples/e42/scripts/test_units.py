import bpy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
print(build_units()); print(selfcheck_units())
G = globals()


def expect(name, fn, undo=None):
    try:
        fn(); selfcheck_units(); print("MISSED", name)
    except AssertionError as e:
        print("caught", name, "|", str(e)[:110])
    if undo:
        undo()
    build_units()


def patch(d, k, v):   # set d[k] = v, → undo
    old = d[k]
    d[k] = v
    return lambda: d.__setitem__(k, old)


def during_build(d, k, v):   # the build sees the change, the check the spec
    def f():
        u = patch(d, k, v); build_units(); u()
    return f


O = lambda n: bpy.data.objects[n]
expect("W1 one size up", during_build(UNIT, "W1", (1.21, 1.10)))
expect("no gap round the units", during_build(G, "UNIT_GAP", 0.0))
def lift():
    O("D2_Bed2_Frame").location.z = 0.01; bpy.context.view_layer.update()
expect("a door frame 1 cm off the floor", lift)
expect("W4 frosted → clear", lambda: setattr(O("W4_Bath_Glass").material_slots[0], "material", bpy.data.materials["M_Glass_Clear"]))
expect("D1 with 3 panes", during_build(ALUSET, "D1", {**ALUSET["D1"], "panes": 3, "fixed": (0, 2), "screens": (1,)}))
expect("hinges counted one by one", during_build(DOOR, "per_pack", 1))
expect("a unit missing", lambda: bpy.data.objects.remove(O("W2_Bed1_Side_Frame")))
if _u_layer(C_OLD_OPEN):   # (only a file that grew from a massing model has one)
    expect("massing openings showing", lambda: setattr(_u_layer(C_OLD_OPEN), "exclude", False))
expect("W1 screen dropped", during_build(ALUSET, "W1", {**ALUSET["W1"], "screens": ()}))
u_sw = {}
def hinge_by_switch():   # build and check both see Bed2 hung on its switch side
    u_sw["u"] = patch(SWING, "D2_Bed2", ("c0", -1, "SW_Bed2")); build_units()
expect("Bed2 hinged by its switch", hinge_by_switch, lambda: u_sw["u"]())
expect("Bed2 leaf on the wrong face", during_build(SWING, "D2_Bed2", ("c1", 1, "SW_Bed2")))
p0 = _points
def dev_in_swing():   # a switch where the Bed1 leaf sweeps
    pts = p0(); q = dict(pts["SW_Bed1"]); q["p"] = Vector((2.70, 4.95, 1.20)); pts["SW_X"] = q
    G["_points"] = lambda: pts
expect("a device in the Bed1 swing", dev_in_swing, lambda: G.__setitem__("_points", p0))
s0 = _solids
def wall_in_swing():   # a brick pier where the Bed2 leaf sweeps
    G["_solids"] = lambda cs: {**s0(cs), ("WL_A1-A2_Brick", 999): (2.60, 2.30, 0.42, 2.70, 2.50, 3.45)}
expect("a wall in the Bed2 swing", wall_in_swing, lambda: G.__setitem__("_solids", s0))
def into_paint():   # a stray piece of another stage inside a sash
    me = _boxes_data("TMP_Clash", [(4.40, 7.50, 1.90, 4.45, 7.62, 1.95)])
    bpy.data.collections[C_FINISH].objects.link(bpy.data.objects.new("TMP_Clash", me))
expect("a unit into another stage", into_paint, lambda: bpy.data.objects.remove(O("TMP_Clash")))
def conduit_through_w3():   # a conduit (a bevelled curve) across the kitchen window
    cv = bpy.data.curves.new("TMP_Cond", "CURVE"); cv.dimensions = "3D"; cv.bevel_depth = 0.01
    sp = cv.splines.new("POLY"); sp.points.add(1)
    sp.points[0].co = (4.20, 7.40, 2.00, 1); sp.points[1].co = (4.20, 7.75, 2.00, 1)
    bpy.data.collections[C_ELEC].objects.link(bpy.data.objects.new("TMP_Cond", cv))
expect("a conduit through W3", conduit_through_w3, lambda: bpy.data.objects.remove(O("TMP_Cond")))
def inside_jamb():   # a small piece wholly inside a door jamb
    b = _obj_boxes(_world_bm(O("D2_Bed2_Frame")), "D2_Bed2_Frame")[0]
    c_ = [(b[i] + b[i + 3]) / 2 for i in range(3)]
    me = _boxes_data("TMP_In", [(c_[0] - 0.005, c_[1] - 0.005, c_[2] - 0.005, c_[0] + 0.005, c_[1] + 0.005, c_[2] + 0.005)])
    bpy.data.collections[C_TILE].objects.link(bpy.data.objects.new("TMP_In", me))
expect("a piece wholly inside a jamb", inside_jamb, lambda: bpy.data.objects.remove(O("TMP_In")))
def floor_down():
    O("FT_floor_Tiles").location.z = -0.01; bpy.context.view_layer.update()
def floor_back():
    O("FT_floor_Tiles").location.z = 0.0; bpy.context.view_layer.update()
expect("the floor tiles 1 cm lower than the frames", floor_down, floor_back)
r0 = _u_room_side
def flip_room():
    G["_u_room_side"] = lambda ln, swing=None: -r0(ln, swing); build_units(); G["_u_room_side"] = r0
expect("screens on the outside", flip_room)
expect("pane tracks collapsed", during_build(ALU, "track", 0.0))
def wall_by_handle():   # a pier only the Bed2 handle reaches at 90°
    G["_solids"] = lambda cs: {**s0(cs), ("WL_A1-A2_Brick", 998): (2.25, 2.85, 0.42, 2.35, 2.90, 3.45)}
expect("a wall the Bed2 handle hits", wall_by_handle, lambda: G.__setitem__("_solids", s0))
def hinges_shift():   # every door's hinges 2 mm off their hinge-edge gap
    O("DR_Hinges").location.y = 0.002; bpy.context.view_layer.update()   # (into the leaf: only the per-door check sees it)
expect("hinges off their hinge edges", hinges_shift)
print(selfcheck_units())
print("TESTS DONE")
