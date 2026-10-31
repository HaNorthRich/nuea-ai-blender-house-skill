import bpy, bmesh, hashlib
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
# ST12 mutation suite (rewritten 30 ต.ค. for e42_conduit.py; a test review folded in). Each mutation breaks one rule and
# selfcheck_elec (or the one check it targets) must fail with a message holding `want`; controls must pass.
# GROUP: "a" table/take-off · "b" model geometry · "c" synthetic runs into one check, three routing passes · "rebuild" (≈ 90 s each:
# one a call via ONLY). Run as: GROUP = "a"; ONLY = None; exec(this).
GROUP = globals().get("GROUP", "a")
ONLY = globals().get("ONLY")
O = bpy.data.objects
res = []

def state():   # what the mutations touch, hashed: an undo must give it back exactly
    h = hashlib.sha1()
    for o in bpy.data.collections[C_ELEC].objects:
        h.update(repr((o.name, tuple(o.location), {k: (list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v)
                                                   for k, v in o.data.items()} if o.data else None)).encode())
        if o.type == "CURVE":
            h.update(repr([tuple(p.co) for sp in o.data.splines for p in sp.points]).encode())
        elif o.type == "MESH":
            h.update(repr([tuple(v.co) for v in o.data.vertices]).encode())
    h.update(repr((tuple(O["CL_Living_Hangers"].location), sorted(CD["tie_chase"]), EL["flex"]["max"])).encode())
    return h.hexdigest()

def expect(name, fn, undo, want, check=None):
    if ONLY and ONLY not in name:
        return
    s0 = state() if GROUP != "rebuild" else None   # (a rebuild may reorder objects: its undo is a rebuild)
    try:
        fn()
        bpy.context.view_layer.update()
        try:
            (check or selfcheck_elec)()
            res.append(("MISSED", name, ""))
        except AssertionError as e:
            ok = any(w in str(e) for w in (want if isinstance(want, tuple) else (want,)))
            res.append(("caught" if ok else "WRONG", name, str(e)[:110]))
    except Exception as e:
        res.append(("ERROR", name, f"{type(e).__name__}: {e}"[:110]))
    finally:
        undo()
        bpy.context.view_layer.update()
        if s0 is not None and state() != s0:
            res.append(("NOT UNDONE", name, ""))

def control(name, fn):   # must pass
    if ONLY and ONLY not in name:
        return
    try:
        fn()
        res.append(("ok", name, ""))
    except Exception as e:
        res.append(("FALSE FAIL", name, f"{type(e).__name__}: {e}"[:110]))

def call(name, fn, want):   # a synthetic run into one check: nothing to undo
    expect(name, lambda: None, lambda: None, want, check=fn)

def shift(o, d):
    return (lambda: o.location.__setitem__(slice(0, 3), (o.location + d)[:]),
            lambda: o.location.__setitem__(slice(0, 3), (o.location - d)[:]))

def props(o, **fs):   # set data properties from their old values; a copy kept (an IDProperty array dies when replaced)
    old = {k: (o.data[k] if isinstance(o.data[k], (int, float)) else list(o.data[k])) for k in fs}
    return (lambda: [o.data.__setitem__(k, f(old[k])) for k, f in fs.items()],
            lambda: [o.data.__setitem__(k, v) for k, v in old.items()])

def points(sp, f):
    c0 = [tuple(p.co) for p in sp.points]
    def do():
        for i, p in enumerate(sp.points):
            p.co = f(i, c0[i])
    def undo():
        for p, c in zip(sp.points, c0):
            p.co = c
    return do, undo

def mesh(o, f):
    m0 = o.data.copy()
    def undo():
        m1 = o.data
        o.data = m0
        bpy.data.meshes.remove(m1)
    return (lambda: f(o)), undo

def V(*xyz):
    return Vector(xyz)

def bent(poly, radii, z=3.30):   # a sharp plan polyline bent to arcs as the router does, at height z
    pts, _ = _round(poly, radii, closed=False, step=CD["step"])
    return [V(x, y, z) for x, y in pts]

r12 = EL["conduit"]["1/2"] / 2
if GROUP != "c" and "EL_Conduit_1-2" not in O:
    build_elec()
cu = O["EL_Conduit_1-2"].data
to = list(cu["to"])

if GROUP == "a":   # table / take-off rows (selfcheck_elec end to end)
    expect("[a] downlights dropped 1 cm", *shift(O["EL_dl"], V(0, 0, -0.01)), ("mm off the", "not on the soffit"))   # (whichever fitting reads first)
    def one_box(o):   # one whole TOP 2×4 island (and its knockouts) taken out
        vs = max((vs for vs, _ in _islands(o)), key=lambda vs: max(v.z for v in vs) - min(v.z for v in vs))   # a body, not a disc
        lo = V(*[min(v[k] for v in vs) - 0.02 for k in range(3)]); hi = V(*[max(v[k] for v in vs) + 0.02 for k in range(3)])
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if all(lo[k] < (o.matrix_world @ v.co)[k] < hi[k] for k in range(3))], context="VERTS")
        bm.to_mesh(o.data); bm.free()
    expect("[a] a downlight box missing", *mesh(O["EL_box24"], one_box), "EL_box24: count")
    # the downlights slid along x until one sits right under a cross runner (the ring centred on the runner)
    rings = [sum((V(*v) for v in vs), V(0, 0, 0)) / len(vs) for vs, _ in _islands(O["EL_dl"]) if max(v[2] for v in vs) - min(v[2] for v in vs) < 0.006]
    dx = min(((l - c.x) for c in rings for r_, (rc, fl, zc) in _rooms_el().items() if rc[0] < c.x < rc[2] and rc[1] < c.y < rc[3]
              for l in _runner_gaps(r_, 0)), key=abs)
    expect("[a] a downlight under a runner", *shift(O["EL_dl"], V(dx, 0, 0)), "under a runner")
    expect("[a] downlights back up in the board (the trim hidden, 31 ต.ค.)", *shift(O["EL_dl"], V(0, 0, 0.006)), "mm off the")
    expect("[a] the lenses slid off their rings", *shift(O["EL_dl_lens"], V(0.05, 0, 0)), "no lens")
    expect("[a] a 4×4 counted that is not drawn", *props(O["EL_box44"], count=lambda v: v + 1), "EL_box44: count")
    expect("[a] a flush 2×4 counted that is not drawn", *props(O["EL_Box2x4"], count=lambda v: v + 1), "EL_Box2x4: count")
    expect("[a] THW 2.5 half a metre short", *props(O["EL_Wire_2.5"], length=lambda v: v - 0.5), "wire 2.5")
    expect("[a] the main THW 16 half a metre short", *props(O["EL_Wire_16"], length=lambda v: v - 0.5), "wire 16")
    expect("[a] conduit taken off 0.5 m long a piece", *props(O["EL_Conduit_1-2"], lens=lambda v: [x + 0.5 for x in v]), "conduit length")
    expect("[a] a conduit piece left out of the take-off", *props(O["EL_Conduit_1-2"], lens=lambda v: v[1:]), "conduit length")
    expect("[a] an elbow taken off", *props(O["EL_Conduit_1-2"], bends=lambda v: 1), "elbows")
    expect("[a] clips for 1 m more", *props(O["EL_Conduit_1-2"], vlen=lambda v: v + 1.0), "clipped length")
    expect("[a] flex taken off 0.3 m long", *props(O["EL_Flex"], lens=lambda v: [x + 0.3 for x in v]), "conduit length")
    expect("[a] a flex connector short", *props(O["EL_FlexConn"], count=lambda v: v - 1), "EL_FlexConn")
    expect("[a] chase row 1 m long", *props(O["EL_Chase"], length=lambda v: v + 1.0), "chase length")
    expect("[a] chase row a groove more", *props(O["EL_Chase"], count=lambda v: v + 1), "chase count")
    def chases_set(f):   # the groove list with the row's length / count kept in step (so only the model match can fail)
        do0, undo0 = props(O["EL_Chase"], lens=f, length=lambda v: v, count=lambda v: v)
        def do():
            do0()
            L = list(O["EL_Chase"].data["lens"])
            O["EL_Chase"].data["length"] = sum(L); O["EL_Chase"].data["count"] = len(L)
        return do, undo0
    expect("[a] a chase left out of the take-off", *chases_set(lambda v: v[1:]), "not in the take-off")
    expect("[a] chases 10 cm short", *chases_set(lambda v: [x - 0.10 for x in v]), "not in the take-off")
    expect("[a] chases 3 cm long", *chases_set(lambda v: [x + 0.03 for x in v]), "not in the take-off")
    expect("[a] a chase taken off that is not in the model", *chases_set(lambda v: v + [0.50]), "not in the model")
    do2, undo2 = chases_set(lambda v: [x + 0.01 for x in v])   # (a loop's groove is taken off ~1.2 cm long already)
    def plus2():
        do2()
        try:
            selfcheck_conduit()
        finally:
            undo2()
    control("[a] chases 1 cm long (in the window) pass", plus2)
    expect("[a] one hole more in the take-off", *props(O["EL_WallHoles"], count=lambda v: v + 1), "holes through walls")
    f0 = EL["flex"]["max"]
    expect("[a] flex limit 0.5 m", lambda: EL["flex"].__setitem__("max", 0.5), lambda: EL["flex"].__setitem__("max", f0), "flexible conduit")

elif GROUP == "b":   # model geometry
    expect("[b] switches slid 40 cm", *shift(O["EL_sw"], V(0, 0.40, 0)), "EL_sw at")
    k = next(i for i, t in enumerate(to) if t.startswith("HUB"))
    sp = cu.splines[k]
    e = V(*sp.points[-1].co[:3]); d2 = (V(*sp.points[-2].co[:3]) - e).normalized() * 0.02
    expect("[b] a conduit 2 cm short of its box", *points(sp, lambda i, c: (c[0] + d2.x, c[1] + d2.y, c[2] + d2.z, c[3]) if i == len(sp.points) - 1 else c),
           "not on its box")
    a_, b_ = 0, 1   # (any two pieces of one size)
    other = [tuple(p.co) for p in cu.splines[b_].points]
    expect("[b] two conduits in one place", *points(cu.splines[a_], lambda i, c: other[min(i, len(other) - 1)]), "clash")
    def mitre(sp):   # the last arc's points all moved onto its corner: a mitred bend, the same degrees
        from mathutils.geometry import intersect_line_line
        P = [V(*p.co[:3]) for p in sp.points]
        bt = [i for i in range(1, len(P) - 1) if (P[i] - P[i - 1]).angle(P[i + 1] - P[i]) > math.radians(0.5)]
        i1 = bt[-1]; i0 = i1
        while i0 - 1 in bt:
            i0 -= 1
        X = intersect_line_line(P[i0 - 1], P[i0], P[i1 + 1], P[i1])[0]
        return points(sp, lambda i, c: (X.x, X.y, X.z, c[3]) if i0 <= i <= i1 else c)
    expect("[b] a mitred bend (no arc)", *mitre(cu.splines[to.index("ROD")]), "mitred corner")   # (the ground run under the beam)
    expect("[b] the 4×4 pull boxes slid 20 cm along x", *shift(O["EL_box44"], V(0.20, 0, 0)),
           ("passes through a box", "not fixed to the wall"))   # (a hub on a wall along y slides off it)
    expect("[b] 4×4 boxes off the wall", *shift(O["EL_box44"], V(0.02, 0.02, 0)), "not fixed to the wall")
    cvs = _islands(O["EL_cu"])[0][0]
    cu_c = sum(cvs, Vector()) / len(cvs)
    b0 = _islands(O["EL_box24"])[0][0]
    expect("[b] a downlight box in front of the CU", *shift(O["EL_box24"], cu_c - sum(b0, Vector()) / len(b0) + V(-0.10, 0, 0.30)), "from the CU")
    fl = O["EL_Flex"].data.splines[0]
    expect("[b] a flex in front of a lid", *points(fl, lambda i, c: (c[0], c[1], c[2] + 0.06, c[3])), "in front of the lid")
    expect("[b] a flex short of its downlight", *points(fl, lambda i, c: (c[0] + 0.05, c[1], c[2], c[3]) if i == len(fl.points) - 1 else c),
           "ends on no downlight")
    # a flex point moved onto a hanger rod (flex is checked against the ceiling frame too)
    rv = max(_islands(O["CL_Living_Hangers"])[0][0], key=lambda v: v[2])
    rod = V(rv[0], rv[1], 3.33)
    fl2 = O["EL_Flex"].data.splines[1]
    mid = len(fl2.points) // 2
    call("[b] a flex through a hanger rod", lambda: _check_steel([], [("T", "X", [rod + V(0, 0, 0.08), rod, rod - V(0, 0, 0.20)], EL["flex"]["od"] / 2)]),
         "roof steel / ceiling")
    # a real flex shifted in plan so its level leg along the ceiling (zc + 5 cm) crosses a hanger rod
    def flex_on_rod():
        for sp_ in O["EL_Flex"].data.splines:   # (the first flex with a level leg of its own along the ceiling)
            F = [O["EL_Flex"].matrix_world @ V(*p.co[:3]) for p in sp_.points]
            lv_ = [m for m in _samples(F, 0.005) if abs(m.z - F[-1].z - 0.029) < 0.01 and (m.xy - F[-1].xy).length > 0.15]
            if len(lv_) > 20:
                break
        q = lv_[len(lv_) // 2]
        rods = [sum((V(*v) for v in vs), V(0, 0, 0)) / len(vs) for vs, _ in _islands(O["CL_Living_Hangers"])]
        rd = min(rods, key=lambda c: (c.xy - q.xy).length)
        dv = V(rd.x - q.x, rd.y - q.y, 0)
        return _check_steel([], [("T", "X", [m + dv for m in F], EL["flex"]["od"] / 2)])
    call("[b] a flex's level leg across a hanger rod", flex_on_rod, "roof steel / ceiling")
    # MAIN's riser tight on the column face: through the soffit's edge runner (its boards it may pass)
    mn = O["EL_Conduit_1"].data
    Pm = [O["EL_Conduit_1"].matrix_world @ V(*p.co[:3]) for p in mn.splines[list(mn["to"]).index("MAIN_box")].points]
    call("[b] the main's riser tight on the column (soffit runner)", lambda: _check_steel([("MAIN", "X", [V(6.1425, p.y, p.z) if p.x > 6.17 and p.y < 0.2 else p
                                                                                             for p in Pm], EL["conduit"]["1"] / 2)]), "roof steel / ceiling")
    call("[b] the main through the soffit board away from its 2 holes",   # (the board exemption is only at the holes)
         lambda: _check_steel([("MAIN", "X", [V(6.40, 3.00, 3.20), V(6.40, 3.00, 2.95)], EL["conduit"]["1"] / 2)]), "roof steel / ceiling")
    # a flex point moved onto a conduit (flex is clash-checked too)
    cpt = V(*cu.splines[0].points[len(cu.splines[0].points) // 2].co[:3])
    expect("[b] a flex through a conduit", *points(fl2, lambda i, c: (cpt.x, cpt.y, cpt.z, c[3]) if i == mid else c), "clash")
    t0_ = set(CD["tie_chase"])
    expect("[b] SW_Bath's tie chase without the user's (ก)", lambda: CD.__setitem__("tie_chase", set()), lambda: CD.__setitem__("tie_chase", t0_), "_Ties")
    hy = max(sum(v.y for v in vs) / len(vs) for vs, _ in _islands(O["CL_Living_Hangers"]))
    expect("[b] a hanger rod on the north wall's conduit line", *shift(O["CL_Living_Hangers"], V(0, 7.50 - hy, 0)), "roof steel / ceiling")
    # a piece re-labelled to another conduit: it hangs off no box its id went into
    circ = list(cu["circ"])
    j = next(i for i, sp_ in enumerate(cu.splines) if circ[i] != "GND"   # a piece that leaves a box its conduit went into
             and any((V(*sp_.points[0].co[:3]) - V(*cu.splines[h].points[-1].co[:3])).length < 0.15
                     for h in range(len(to)) if h != i and circ[h] == circ[i]))
    other_id = circ[j] + "+" + next(c for c in ("S3", "L1", "S2") if c not in circ[j].split("+"))   # (its points still beyond it)
    expect("[b] a piece under another conduit's id", *props(O["EL_Conduit_1-2"], circ=lambda v: v[:j] + [other_id] + v[j + 1:]), "no circuit beyond")
    # a piece out of a hub its conduit never went into, on to one of its sockets
    R_ = _conduit_runs()
    k_cid, k_end = next((cid, P[-1]) for cid, t, P, r in R_ if t == "SO_Kitchen_1")   # (S3, alone or in a shared conduit)
    hub_end = next(P[-1] for cid, t, P, r in R_ if t.startswith("HUB") and not set(cid.split("+")) & set(k_cid.split("+")))
    # (a second feed into a socket's box: caught as a box gone into twice — the "not fed from the CU" assert is a backstop
    # behind this and the conductors' "no circuit beyond", no single-fault mutation reaches it first)
    call("[b] a second feed from a box its conduit never entered", lambda: _check_wire(R_ + [(k_cid, "X", [hub_end, k_end], r12)]),
         ("twice", "not fed from the CU"))   # (which one fires first depends on the walk order)
    # conductors by hand from the CTL table, independent of the router
    P_ = _points(); L1 = next(C for C in CIRCUITS if C["id"] == "L1"); S1 = next(C for C in CIRCUITS if C["id"] == "S1")
    def leads():
        assert _lead(L1, set(L1["pts"]), P_) == [("1.5", 2)]                                  # all downstream: N + L
        assert _lead(L1, {"DL_Bed1_1"}, P_) == [("1.5", 2)]                                   # a light alone: N + switched line
        assert _lead(L1, {"SW_Bed1"}, P_) == [("1.5", 2)]                                     # its switch alone: L + switched line
        assert _lead(L1, {"DL_Bed1_1", "DL_Bed2_1"}, P_) == [("1.5", 3)]                      # two lights of two switches: N + 2
        assert _conductors([L1, S1], {"SW_Bed1"}, P_, "t") == [("1.5", 2)]                   # to a switch only: no earth
        assert ("G2.5", 1) in _conductors([L1, S1], {"DL_Bed1_1", "SO_Bed1_1"}, P_, "t")     # shared: one earth, the larger
    control("[b] conductor rules", leads)

    # R2: a branch box in front of the CU (a circuit both ways must leave it as two conduits)
    cpu = _points()["CU"]
    b44 = O["EL_box44"]
    cs = [sum(vs, Vector()) / len(vs) for vs, _ in _islands(b44)]
    near_c = min(cs, key=lambda c: (c - cpu["p"]).length)
    d_cu = cpu["p"] + cpu["n"] * 0.10 + Vector((0, 0, 0.30)) - near_c
    expect("R2 a pull box 0.3 m over the CU", *shift(b44, d_cu), "two conduits leave it", check=_check_cu)

elif GROUP == "c":   # synthetic runs straight into one check
    control("[c] r 102 bend passes", lambda: _check_bends([("T", "X", bent([(0, 0), (0.5, 0), (0.5, 0.5)], [0, 0.102, 0]), r12)]))
    call("[c] r 80 bend", lambda: _check_bends([("T", "X", bent([(0, 0), (0.5, 0), (0.5, 0.5)], [0, 0.08, 0]), r12)]), "a bend of r")   # (~11° a point: under the mitre limit)
    stair = [(0, 0), (0.5, 0), (0.5, 0.5), (1, 0.5), (1, 1), (1.5, 1), (1.5, 1.5)]
    control("[c] 360° between boxes passes", lambda: _check_bends([("T", "X", bent(stair[:6], [0] + [0.102] * 4 + [0]), r12)]))
    call("[c] 450° between boxes", lambda: _check_bends([("T", "X", bent(stair, [0] + [0.102] * 5 + [0]), r12)]), "of bends between boxes")
    call("[c] a 14° kink between long straights", lambda: _check_bends([("T", "X", [V(0, 0, 3), V(1, 0, 3), V(2, 0.25, 3)], r12)]), "mitred corner")
    # on the Living north wall (plaster face y 7.525), over the ceiling
    on = lambda y, x0=4.0, x1=5.0, z=3.40: [V(x0, y, z), V(x1, y, z)]
    control("[c] a run 25 mm off the wall passes", lambda: _check_on_walls([("T", "X", on(7.50), r12)]))
    call("[c] a run 22 cm out in the room", lambda: _check_on_walls([("T", "X", on(7.30), r12)]), "off the wall")
    call("[c] a circuit back alongside itself", lambda: _check_on_walls([("T", "X", on(7.50) + [V(5.2, 7.50, 3.40)], r12),
                                                                          ("T", "Y", list(reversed(on(7.47))), r12)]), "alongside itself")
    call("[c] a circuit back alongside itself 12 cm lower", lambda: _check_on_walls([("T", "X", on(7.50) + [V(5.2, 7.50, 3.40)], r12),
                                                                                   ("T", "Y", list(reversed(on(7.50, z=3.28))), r12)]), "alongside itself")
    control("[c] two circuits side by side pass",
            lambda: _check_on_walls([("T", "X", on(7.50), r12), ("U", "Y", list(reversed(on(7.47))), r12)]))
    # holes through the A2-E2 wall (brick x 3.04–3.10, plaster to 3.025 / 3.115) at y 1.0, over the bedroom-2 ceiling
    hole = lambda y0=1.0, y1=1.0, z0=3.30, z1=3.30: [V(2.90, y0, z0), V(3.30, y1, z1)]
    def square_ok():
        assert _check_walls([("T", "X", hole(), r12)])[0] == 1, "not one hole"
    control("[c] a square hole through brick passes", square_ok)
    tn = 0.2 * math.tan(math.radians(5))
    call("[c] a hole 5° off square", lambda: _check_walls([("T", "X", hole(1.0 - tn, 1.0 + tn), r12)]), "not square")
    call("[c] a hole not level", lambda: _check_walls([("T", "X", hole(z1=3.31), r12)]), "not level")
    call("[c] a hole into the wall plate", lambda: _check_walls([("T", "X", hole(z0=3.46, z1=3.46), r12)]), "touches AS_")
    sb = _points()["SW_Bath"]["p"]; cx, cy = sb.x - 0.02, sb.y + 0.0125; bb = sb.z - EL["box"][1] / 2
    call("[c] SW_Bath's chase 5 cm past its box bottom", lambda: _check_walls([("T", "SW_Bath", [V(cx, cy, 3.36), V(cx, cy, bb - 0.05)], r12)]), "_Ties")
    call("[c] a chase 12 cm along the tie from SW_Bath", lambda: _check_walls([("T", "X", [V(cx, cy - 0.12, 3.36), V(cx, cy - 0.12, bb)], r12)]), "_Ties")
    call("[c] a level run through the tie by SW_Bath", lambda: _check_walls([("T", "X", [V(2.9, sb.y, 3.36), V(3.3, sb.y, 3.36)], r12)]), "_Ties")
    # --- the gaps left open after ST12 (R1–R6), closed 31 ต.ค.
    def kinked(deg):   # a proper 90° bend whose straight leaves its arc's last point turned `deg` more (R1)
        P = bent([(0, 0), (0.5, 0), (0.5, 0.5)], [0, 0.102, 0])
        a, e = P[-2], P[-1]
        rot = __import__("mathutils").Matrix.Rotation(math.radians(deg), 3, "Z")
        return P[:-1] + [a + rot @ (e - a)]
    control("[c] R1 a tangent arc → straight passes", lambda: _check_bends([("T", "X", kinked(0.0), r12)]))
    call("[c] R1 a 6° kink right at an arc end", lambda: _check_bends([("T", "X", kinked(6.0), r12)]), "mitred corner")
    call("[c] R1 a 6° kink back against the arc", lambda: _check_bends([("T", "X", kinked(-6.0), r12)]), "mitred corner")
    control("[c] R6 a run 13 cm off a plain wall passes", lambda: _check_on_walls([("T", "X", on(7.525 - 0.13, z=3.10), r12)]))   # (under the plate: it stands proud)
    call("[c] R6 a run 15 cm off a plain wall", lambda: _check_on_walls([("T", "X", on(7.525 - 0.15, z=3.10), r12)]), "off the wall")
    call("[c] R5 L1 back alongside L1+S1", lambda: _check_on_walls([("L1", "X", on(7.50) + [V(5.2, 7.50, 3.40)], r12),
                                                                   ("L1+S1", "Y", list(reversed(on(7.47))), r12)]), "alongside itself")
    control("[c] R5 L1 beside S2 passes", lambda: _check_on_walls([("L1", "X", on(7.50), r12), ("S2", "Y", list(reversed(on(7.47))), r12)]))
    # SW_Bath's tie exception reaches 10 cm round its box (R4): a slanted chase into its box from 9.5 / 10.5 cm off
    slant = lambda off: [V(cx, sb.y - off, 3.36), V(cx, sb.y - off, 3.30), V(cx, cy, bb + 0.02), V(cx, cy, bb)]   # (off: plan distance ≈ from the switch)
    control("[c] R4 SW_Bath's chase from 9.7 cm along the tie passes", lambda: _check_walls([("T", "SW_Bath", slant(0.097), r12)]))
    call("[c] R4 SW_Bath's chase from 10.5 cm along the tie", lambda: _check_walls([("T", "SW_Bath", slant(0.105), r12)]), "_Ties")
    # chase shapes (R3), in the A2-E2 brick (x 3.04–3.10) at y 1.0
    call("[c] R3 a chase down to no box", lambda: _check_walls([("T", "X", [V(2.90, 1.0, 3.30), V(3.07, 1.0, 3.30), V(3.07, 1.0, 2.00)], r12)]), "towards no box")
    call("[c] R3 a graze 3 mm into the plaster", lambda: _check_walls([("T", "X", [V(3.13, 0.9, 3.30), V(3.112, 1.0, 3.30), V(3.13, 1.1, 3.30)], r12)]),
         "neither hole nor chase")

    # junction-box fallback (31 ต.ค.): the room an error names, else the pieces', else the clash point's — still boxed
    P_, V_ = _points(), _voids()
    def jb_rooms():
        assert _jb_room("L1+H1 in Living: the wall band is full", P_, V_, set()) == "Living"
        assert _jb_room("L1+H1 in Living: … Bath run (6.65, -0.35) …", P_, V_, {"Living"}) == "Bath", "the band's room once the first is off"
        assert _jb_room("conduits clash: A1+S1+L1 → J@SO_Bed1_2 × A1+S1+L1 → HUB3 at 9.0, 9.0, 3.4 (19 mm apart)", P_, V_, set()) == "Bed1"
        assert _jb_room("conduits clash: X → HUB3 × Y → HUB4 at 2.808, 7.425, 3.491 (19 mm apart)", P_, V_, set()) == "Bed1"
        assert _jb_room("conduits clash: X → HUB3 × Y → HUB4 at 3.05, 3.80, 3.4 (19 mm apart)", P_, V_, {"Bath"}) in ("Bed1", "Living", "Bed2"), "a point on a partition: a neighbour still boxed"
        assert _jb_room("L1+H1 in Living: no", P_, V_, {"Living"}) is None
    control("[c] junction-box fallback picks the room", jb_rooms)

    # junction-box spacing in one routing pass (≈ 7 s each), Bed2 boxed as built, SO_Bed2_2 moved
    def routed(pid, p, n=None):
        def f():
            q = dict(P_)
            q[pid] = dict(q[pid], p=p, n=n or q[pid]["n"])
            had, old = "jb_off" in CD, CD.get("jb_off")
            CD["jb_off"] = {"Bed1", "Living"}
            try:
                _route_once(q)
            finally:
                CD["jb_off"] = old
                if not had:
                    del CD["jb_off"]
        return f
    a2 = P_["SO_Bed2_1"]
    call("[c] two level boxes 22 cm apart on a wall", routed("SO_Bed2_2", a2["p"] + V(0, -0.22, 0), a2["n"]), "too close for two junction boxes")
    control("[c] a box 22 cm along, 90 cm above another passes (linked in the wall)", routed("SO_Bed2_2", a2["p"] + V(0, -0.22, 0.9), a2["n"]))
    call("[c] a junction box behind the way in", routed("SO_Bed2_2", P_["SO_Bed2_2"]["p"] + V(0.5, 0, 0)), "would start before the run is on the wall")

else:   # rebuild: one a call (ONLY)
    def rebuild_with(fn, undo):
        def f():
            fn(); build_elec()
        def u():
            undo(); build_elec()
        return f, u
    C0 = CIRCUITS[0]
    a0, w0 = C0["amp"], C0["wires"]
    expect("16 A on THW 1.5", *rebuild_with(lambda: C0.__setitem__("amp", 16), lambda: C0.__setitem__("amp", a0)), "breaker on THW")
    expect("a lighting circuit without its earth", *rebuild_with(lambda: C0.__setitem__("wires", [("1.5", 2)]),
                                                                 lambda: C0.__setitem__("wires", w0)), "no earth")
    P0 = list(POINTS)
    expect("a socket in the bedroom door", *rebuild_with(
        lambda: POINTS.__setitem__(slice(None), [(i, k, r, "x1", 5.10, g) if i == "SO_Bed1_1" else (i, k, r, f, a, g) for i, k, r, f, a, g in P0]),
        lambda: POINTS.__setitem__(slice(None), P0)), "in opening")

for r_ in res:
    print(*r_, sep=" | ")
bad = [r_ for r_ in res if r_[0] not in ("caught", "ok")]
print("TESTS DONE", GROUP, len(res) - len(bad), "/", len(res), "· problems:", len(bad))
