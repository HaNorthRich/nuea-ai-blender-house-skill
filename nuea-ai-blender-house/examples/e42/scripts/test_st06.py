import bpy
E42_UPTO = "e42_walls.py"
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
D = E42_DIR + "/"
print(build_grid(), build_footings(), build_stubs(), build_ground_beams(), build_columns(), build_ground_slab())
print(selfcheck())
print("WALLS", build_walls())
print(report(C_WALL))
print(selfcheck_walls())
again = build_walls()
assert not [d.name for d in bpy.data.meshes if d.name.startswith(("WL_", "AS_")) and "." in d.name]
print(selfcheck_walls())

def must_fail(what, obj, attr, delta):
    o = bpy.data.objects[obj]; v = getattr(o.location, attr)
    setattr(o.location, attr, v + delta); bpy.context.view_layer.update()
    try:
        selfcheck_walls(); raise SystemExit(f"not caught: {what}")
    except AssertionError as e:
        print(f"caught {what}:", str(e)[:100])
    setattr(o.location, attr, v); bpy.context.view_layer.update()

must_fail("wall line slid 3 cm", "WL_A2-E2", "y", 0.03)
must_fail("wall plate dropped 2 cm", "AS_A1-A3", "z", -0.02)
must_fail("beads slid 5 mm", "SM_Beads", "x", 0.005)
must_fail("opening beads moved off the wall", "SM_Beads_Openings", "z", 5.0)
print(selftest())

def must_fail_build(what, patch, undo):
    patch(); build_walls()
    try:
        selfcheck_walls(); raise SystemExit(f"not caught: {what}")
    except AssertionError as e:
        print(f"caught {what}:", str(e)[:100])
    undo(); build_walls()

c0 = PLATE["c"]
must_fail_build("C 2.0 mm thick instead of 2.3", lambda: PLATE.update(c=(*c0[:3], 0.0020)), lambda: PLATE.update(c=c0))
must_fail_build("C without lips", lambda: PLATE.update(c=(*c0[:2], 0.0047, c0[3])), lambda: PLATE.update(c=c0))
lc = lipped_c
must_fail_build("sharp bends (ri 0)", lambda: globals().update(lipped_c=lambda *a: lc(*a, ri=1e-6)),
                lambda: globals().update(lipped_c=lc))
pr = prism
def filled_caps(bm, poly, u0, u1, place):   # the old build: concave n-gon caps triangulated
    import bmesh
    rings = [[bm.verts.new(place(u, s, z)) for s, z in poly] for u in (u0, u1)]
    n = len(poly)
    caps = [bm.faces.new(rings[0][::-1]), bm.faces.new(rings[1])]
    for i in range(n):
        bm.faces.new((rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]))
    bmesh.ops.triangulate(bm, faces=caps)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
must_fail_build("filled end caps", lambda: globals().update(prism=filled_caps), lambda: globals().update(prism=pr))
bd = _bead
must_fail_build("bead on top of the plaster", lambda: globals().update(
    _bead=lambda run, a0, a1, at: [tuple(v + 0.0 for v in b) for b in bd(run, a0, a1, {k: (p, -s) for k, (p, s) in at.items()})]),
    lambda: globals().update(_bead=bd))
op0 = list(OPENINGS)
def old_bath_door():   # spec 29 ต.ค.: the bath door was 0.70 wide
    OPENINGS[:] = [(n, l, 3.40, 4.10, z0, z1) if n == "D4_Bath" else (n, l, c0_, c1_, z0, z1) for n, l, c0_, c1_, z0, z1 in op0]
must_fail_build("bath door 0.70 (old)", old_bath_door, lambda: OPENINGS.__setitem__(slice(None), op0))
must_fail_build("bedroom door 2.10 high", lambda: OPENINGS.__setitem__(slice(None), [(n, l, a_, b_, z0, 2.55 if n == "D2_Bed1" else z1) for n, l, a_, b_, z0, z1 in op0]),
                lambda: OPENINGS.__setitem__(slice(None), op0))
print(selfcheck_walls())
print("NOT SAVED (test only)")
