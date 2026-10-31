import bpy, time
E42_UPTO = "e42_walls.py"
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
D = E42_DIR + "/"
exec(open(D + "e42_roof.py").read())
build_walls()
print(selfcheck_walls())
t = time.time()
print("ROOF members", build_roof(), f"{time.time() - t:.1f}s")
print(report(C_ROOF)); print(report(C_CPAC))
t = time.time(); print(selfcheck_roof(), f"{time.time() - t:.1f}s")
print("metal sheets", build_metal_test()); print(report(C_MS))
print("NOT SAVED (test only)")

def must_fail(what, act, undo):
    act(); bpy.context.view_layer.update()
    try:
        selfcheck_roof(); raise SystemExit(f"not caught: {what}")
    except AssertionError as e:
        print(f"caught {what}:", str(e)[:110])
    undo(); bpy.context.view_layer.update()

def nudge(name, attr, dv):
    o = bpy.data.objects[name]
    return (lambda: setattr(o.location, attr, getattr(o.location, attr) + dv),
            lambda: setattr(o.location, attr, getattr(o.location, attr) - dv))

def batten(side, i):   # the i-th course up a roof side (names carry the course's distance up the slope)
    return sorted((o.name for o in bpy.data.objects if o.name.startswith(f"RF_Batten_{side}_")), key=lambda n: float(n.rsplit("_", 1)[1]))[i]

must_fail("rafter slid 5 cm", *nudge("RF_Rafter_2_04", "y", 0.05))
must_fail("king post dropped 2 cm", *nudge("RF_Post1", "z", -0.02))
must_fail("ridge lifted 2 cm", *nudge("RF_Ridge", "z", 0.02))
must_fail("batten into a hip", *nudge(batten(1, 3), "x", 0.30))
must_fail("batten course moved up 10 cm", *nudge(batten(2, 6), "z", 0.05))
o = bpy.data.objects[batten(3, 5)]; me = o.data
must_fail("batten course missing", lambda: bpy.data.collections[C_CPAC].objects.unlink(o),
          lambda: bpy.data.collections[C_CPAC].objects.link(o))
must_fail("hip lifted 30 cm", *nudge("RF_Hip1", "z", 0.30))
pr = prism
def filled(bm, poly, u0, u1, place):
    import bmesh
    rings = [[bm.verts.new(place(u, s, z)) for s, z in poly] for u in (u0, u1)]
    n = len(poly); caps = [bm.faces.new(rings[0][::-1]), bm.faces.new(rings[1])]
    for i in range(n):
        bm.faces.new((rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]))
    bmesh.ops.triangulate(bm, faces=caps); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
globals()["prism"] = filled
try:   # (since the coped ends, a filled section already stops the build: caught there, or by the check)
    build_roof(); selfcheck_roof(); raise SystemExit("not caught: filled caps")
except (AssertionError, ValueError) as e:   # only where a filled section fails: coping its ends, or the hollow check
    import traceback
    assert (isinstance(e, ValueError) and "_cope" in [f.name for f in traceback.extract_tb(e.__traceback__)]) or \
        (isinstance(e, AssertionError) and any(w in str(e) for w in ("hollow", "cap", "end face"))), f"filled caps failed elsewhere: {e!r}"
    print("caught filled caps:", type(e).__name__, str(e)[:100])
globals()["prism"] = pr; build_roof(); print(selfcheck_roof())
print("TESTS DONE")
