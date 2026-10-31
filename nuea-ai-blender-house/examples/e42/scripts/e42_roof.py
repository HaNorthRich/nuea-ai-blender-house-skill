"""E42 ST07 โครงหลังคา (spec 29 ต.ค.): hip roof (ปั้นหยา) 30°, eave 70 cm out from the finished wall face, every
steel member to its real profile (ไทวัสดุ drawings, steel_sections):
  จันทัน C 100×50×20×2.3 @ 1.00 m · ตะเข้สัน / อกไก่ / ดั้ง 2C ประกบ as the wall plate (the user) ·
  CPAC: แป PROFAST 0.50 mm hat battens @ 0.32 m + SCG CPAC Smooth Cool tiles + ridge/hip caps ·
  metal-sheet TEST (to be deleted once the user approves): box purlins 50×50×2.0 @ 1.00 m + GIANT KINGKONG 0.3 mm
  sheets with 1" PU foam.
Rafter undersides rest on the outer top edge of the perimeter wall plates; the four planes meet in 45° hips and a
ridge over the A2-E2 plate, which carries the king posts.

    exec(open(<e42_struct>).read()); exec(open(<e42_walls>).read()); exec(open(<this file>).read())
    build_roof(); print(report(C_ROOF)); print(report(C_CPAC)); print(selfcheck_roof())
    build_metal_test(); show_cover("metal")      # the test roof; show_cover("cpac") back
"""
import math, os
from mathutils import Vector

exec(open(os.path.join(globals().get("SKILL_SCRIPTS") or os.path.expanduser("~/.claude/skills/nuea-ai-blender-house/scripts"), "roof.py")).read())   # cpac_tiles

C_ROOF, C_CPAC, C_MS = "E42 ST07 Roof Frame", "E42 ST07 Roof CPAC", "E42 ST07 Metal Sheet TEST"
ROOF = dict(pitch=30.0, eave=0.70, step=1.0, min_len=0.30, trim=0.005)   # the user: always 30°, eave asked (70 cm)
TAN, COS, SIN = (f(math.radians(ROOF["pitch"])) for f in (math.tan, math.cos, math.sin))
FACE = COL["b"] / 2 + WALL["pl"]                    # finished exterior face outside the perimeter grid (flush walls)
RAFTER = dict(c=PLATE["c"], kg_m=4.06, stock=6.0, spec="จันทัน C 100×50×20×2.3 มม. @ 1.00 ม.")
TWO_C = dict(c=PLATE["c"], kg_m=PLATE["kg_m"], pieces=2, stock=6.0)   # ตะเข้สัน อกไก่ ดั้ง: as the wall plate
# PROFAST batten (ไทวัสดุ drawing): 61 mm over the flanges, 20 mm top, 27 mm high, one side at 60°, one vertical,
# 0.50 mm, 4 m; joints lap ≥ 5 cm on a rafter. CPAC manual p.7-9: first course 34 cm up from the eave, the top pair
# 8 cm apart across the ridge (Dry Tech), the courses between spaced evenly at 32-34 cm
BATTEN = dict(h=0.027, t=0.0005, w=0.061, top=0.020, side=60.0, first=0.34, lap=0.32, lap_max=0.34, ridge_gap=0.08,
              stock=4.0, joint=0.05,
              spec="แปอะลูซิงค์ PROFAST 0.50 มม. × 4 ม. แบ่งระยะเท่ากัน 0.32-0.34 ม.")
TILE = dict(cover=0.30, lap=0.32, wave=0.030, t=0.025, per_m2=10.5, waste=0.05, hip_gap=0.05,   # Dry Tech: cut ~5 cm apart
            spec="กระเบื้องคอนกรีต SCG ซีแพค สมูทคูล สีชาโดว์ เกรย์ 33×42 ซม.")
# metal-sheet TEST: แป๊บโปร่ง 50×50×2.0 มอก.107 (16.62 kg / 6 m on ไทวัสดุ; corner radius ≤ 3t), GIANT KINGKONG
# 0.3 mm + PU foam 1" (76 cm cover, 3 m, crests 192 mm c/c: 20 top, 70 base, 24 high; end lap 10 cm; 0.51 /m²)
# ไม้เชิงชาย (SCG synthetic-wood manual §4.1 p.12, fascia catalogue; spec 29 ต.ค.): plumb fascia on เหล็กฉาก
# 5×5×0.23 cm at every rafter end, 8" board, then a ไม้ปิดกันนกลอนคู่ 6" (CPAC) or a 6" board (metal) over it. The
# eave (70 cm) is measured to the fascia's outer face; the rafters and hips are cut plumb at its back. Tiles overhang
# the fascia 5 cm (not printed by CPAC: assumed), sheets 15 cm (SSR760 p.6).
FASCIA = dict(angle=(0.05, 0.0023, 0.15), b8=(0.20, 0.016), b6=(0.15, 0.016), bird=(0.15, 0.008), tile_over=0.05,
              sheet_over=0.15, bird_rise=0.025)
BACK = FASCIA["angle"][1] + FASCIA["b8"][1] + FASCIA["b6"][1]   # rafter ends: this far in from the fascia face
# the tile bed's eave edge past the eave line, so the trough underside overhangs the bird-stop face (8 mm in from
# the eave line) by FASCIA["tile_over"]
# (cpac_tiles lifts a first-course trough ~0.029 off the bed along the normal: × sin θ further out in plan; where its
# courses fall moves the real trough by a few mm, so selfcheck_fascia allows ±6 mm on the assumed 5 cm)
_tile_edge = lambda: FASCIA["tile_over"] - FASCIA["b6"][1] + FASCIA["bird"][1] - (0.025 + 0.004) * SIN
MS = dict(tube=(0.050, 0.050, 0.002, 0.006), kg_m=16.62 / 6, stock=6.0, step=1.0, first=0.10,
          sheet_t=0.0003, cover=0.76, crest=0.192, c_top=0.020, c_base=0.070, c_h=0.024, length=3.0, end_lap=0.10,
          foam=0.0254, per_m2=0.51, ridge_gap=0.15, hip_batten=0.10, hip_gap=0.025, spec_p="แป๊บโปร่ง 50×50×2.0 มม. มอก.107 @ 1.00 ม.",
          spec_s="เมทัลชีท GIANT KINGKONG 0.3 มม. ติด PU foam 1 นิ้ว 76×300 ซม.")


def _batten_path():
    b, h, t = BATTEN, BATTEN["h"], BATTEN["t"]
    dx = (h - t) / math.tan(math.radians(b["side"]))
    fl = (b["w"] - b["top"] - dx) / 2
    s0, zb, zt = -b["w"] / 2, t / 2, h - t / 2
    return [(s0, zb), (s0 + fl, zb), (s0 + fl + dx, zt), (s0 + fl + dx + b["top"], zt), (s0 + fl + dx + b["top"], zb),
            (b["w"] / 2, zb)]


def _sheet_path():
    """Centreline of one sheet across its width: 4 crests per cover + the lapping crest, small ribs in the pans."""
    m, out = MS, []
    hb, ht = m["c_base"] / 2, m["c_top"] / 2
    for k in range(5):
        c = hb + k * m["crest"] * m["cover"] / (4 * m["crest"])   # 4 pitches span the cover exactly
        out += [(c - hb, 0.0), (c - ht, m["c_h"]), (c + ht, m["c_h"]), (c + hb, 0.0)]
        if k < 4:   # two stiffening ribs in the pan
            p0, p1 = c + hb, c + m["cover"] / 4 - hb
            for f in (1 / 3, 2 / 3):
                q = p0 + (p1 - p0) * f
                out += [(q - 0.008, 0.0), (q - 0.005, 0.004), (q + 0.005, 0.004), (q + 0.008, 0.0)]
    return out


def _geom():
    """Eave corners (ccw), the four rafter-top planes, half the short eave span D and the eave height."""
    xs, ys = sorted(GX.values()), sorted(GY.values())
    out, a = FACE + ROOF["eave"], PLATE["b"] / 2
    ze = WALL_TOP + PLATE["h"] + 0.10 / COS - (out - a) * TAN   # rafter underside through the plate's outer top edge
    E = [(xs[0] - out, ys[0] - out), (xs[-1] + out, ys[0] - out), (xs[-1] + out, ys[-1] + out), (xs[0] - out, ys[-1] + out)]
    sides = []
    for i in range(4):
        p, q = Vector((*E[i], ze)), Vector((*E[(i + 1) % 4], ze))
        e = (q - p).normalized()
        w = Vector((-e.y, e.x, 0.0))   # inward
        sides.append(dict(Q0=p, e=e, w=w, up=w * COS + Vector((0, 0, SIN)), n=-w * SIN + Vector((0, 0, COS)),
                          L=(q - p).length))
    D = min(s["L"] for s in sides) / 2
    return E, sides, D, ze


def _ridge(E, sides, D, ze):
    """Ridge ends (rafter-top level) and the ridge direction (+x or +y)."""
    long_ = max(sides, key=lambda s: s["L"])
    if long_["L"] - 2 * D < 1e-6:   # shortcut: a square plan is a pyramid with one apex, not built yet
        raise NotImplementedError("square plan: pyramid roof")
    ax = Vector((abs(long_["e"].x), abs(long_["e"].y), 0.0))
    R0 = Vector((E[0][0] + D, E[0][1] + D, ze + D * TAN))
    return R0, R0 + ax * (long_["L"] - 2 * D), ax


def _plate_boxes():
    return [(Vector(((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2)),
             [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))],
             [(b[3] - b[0]) / 2, (b[4] - b[1]) / 2, (b[5] - b[2]) / 2]) for n, b in _solids([C_WALL]).items()
            if n[0].endswith("_2C")]


def _top(xy, sides):
    """Rafter-top surface height over a plan point: the lowest of the four planes."""
    return min(s["Q0"].z + (Vector((*xy, 0)) - Vector((*s["Q0"].xy, 0))).dot(s["w"]) * TAN for s in sides)


def _box(p0, p1, side, up, w, h, s_off=0.0):
    """Oriented box (steel_sections.obb form) of a member whose section bottom-centre line runs p0 → p1."""
    d = p1 - p0
    return (p0 + d / 2 + up * (h / 2) + side * s_off, [d.normalized(), side, up], [d.length / 2, w / 2, h / 2])


def _sweep(bm, sec, p0, p1, side, up):
    """Member of section sec ("C", "2C", "tube", "hat") along its bottom-centre line p0 → p1 into bm."""
    d, L = (p1 - p0).normalized(), (p1 - p0).length
    if sec == "C":
        h, b = RAFTER["c"][0], RAFTER["c"][1]
        prism(bm, lipped_c(*RAFTER["c"]), 0.0, L, lambda u, s, z: tuple(p0 + d * u + side * (s - b / 2) + up * z))
    elif sec == "2C":
        b = TWO_C["c"][1]
        for sg in (-1, 1):
            prism(bm, lipped_c(*TWO_C["c"]), 0.0, L, lambda u, s, z, sg=sg: tuple(p0 + d * u + side * (sg * (b - s)) + up * z))
    elif sec == "tube":
        B, H, t, ro = MS["tube"]
        tube(bm, *box_tube(B, H, t, ro), 0.0, L, frame(p0, d, side, up))
    elif sec == "hat":
        prism(bm, strip(_batten_path(), BATTEN["t"]), 0.0, L, frame(p0, d, side, up))


def _obj(c, name, bm, m, **props):
    _drop(bpy.data.meshes, name)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    for k, v in props.items():
        me[k] = v
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    return o


def _fit(p0, p1, side, up, w, h, obst, min_len=None):
    """Pull the top end p1 back toward p0 until the member clears every obstacle box (None when nothing is left)."""
    d = (p1 - p0).normalized()
    while (p1 - p0).length > (ROOF["min_len"] if min_len is None else min_len):
        if all(obb_overlap(_box(p0, p1, side, up, w, h), o) <= 1e-4 for o in obst):
            return p1
        p1 = p1 - d * ROOF["trim"]
    return None


def _fit2(p0, p1, side, up, w, h, obst):
    """Both ends pulled back, each clear of the obstacles on its own half: (p0, p1) or None."""
    m, d = (p0 + p1) / 2, (p1 - p0).normalized()
    near1 = [o for o in obst if (o[0] - m).dot(d) > 0]
    near0 = [o for o in obst if (o[0] - m).dot(d) <= 0]
    p1 = _fit(m, p1, side, up, w, h, near1, 0.0)
    p0 = _fit(m, p0, side, up, w, h, near0, 0.0)
    if not (p0 and p1) or any(obb_overlap(_box(p0, p1, side, up, w, h), o) > 1e-4 for o in obst):
        return None
    return p0, p1


def _members():
    """Every frame member: [(kind, name, sec, p0, p1, side, up, w, h)], built in the order they are trimmed."""
    E, sides, D, ze = _geom()
    h2, h1 = TWO_C["c"][0], RAFTER["c"][0]
    R0, R1, ax = _ridge(E, sides, D, ze)
    X, Z = ax.cross(Vector((0, 0, 1))).normalized(), Vector((0, 0, 1))
    dr = (TWO_C["c"][1]) * TAN   # ridge top centre below the ridge line: its top corners on the two planes
    out = [("ridge", "RF_Ridge", "2C", R0 - ax * TWO_C["c"][1] - Z * (dr + h2), R1 + ax * TWO_C["c"][1] - Z * (dr + h2),
            X, Z, 2 * TWO_C["c"][1], h2)]
    z_plate = WALL_TOP + PLATE["h"]
    for i, R in enumerate((R0, R1)):   # king posts on the plate under the ridge ends
        q = R - ax * TWO_C["c"][1]
        out.append(("post", f"RF_Post{i + 1}", "2C", Vector((q.x, q.y, z_plate)), Vector((q.x, q.y, R.z - dr - h2)),
                    X, ax, 2 * TWO_C["c"][1], h2))
    for i, (ex, ey) in enumerate(E):   # hips: eave corner → nearer ridge end, top corners on the two planes
        R = min((R0, R1), key=lambda q: (q.xy - Vector((ex, ey))).length)
        a = Vector((ex, ey, ze))   # (the hip starts 15 cm beyond: build_roof cuts it plumb at the fascia back)
        d = (R - a).normalized()
        up = (Z - d * Z.dot(d)).normalized()
        side = d.cross(up).normalized()
        f = lambda dl: (a - up * dl + side * TWO_C["c"][1]).z - _top((a - up * dl + side * TWO_C["c"][1]).xy, sides)
        dl = -f(0.0) * 0.05 / (f(0.05) - f(0.0))
        for _ in range(300):   # 2C deeper than the plane is high over the plate corner: seat it there
            if all(obb_overlap(_box(a - up * (dl + h2), R - up * (dl + h2), side, up, 2 * TWO_C["c"][1], h2), p) <= 1e-4
                   for p in _plate_boxes()):
                break
            dl -= 0.001
        else:
            raise AssertionError(f"hip {i + 1}: cannot be seated within 0.30 m")
        out.append(("hip", f"RF_Hip{i + 1}", "2C", a - up * (dl + h2) - d * 0.15, R - up * (dl + h2), side, up, 2 * TWO_C["c"][1], h2))
    for k, s in enumerate(sides):   # rafters @ step, centred on each eave, from the eave line up to the hips/ridge
        nh = math.floor((s["L"] / 2 - 0.1) / ROOF["step"] + 1e-9)
        for j in range(-nh, nh + 1):
            u = s["L"] / 2 + j * ROOF["step"]
            v1 = min(min(u, s["L"] - u), D) / COS
            p = lambda v: s["Q0"] + s["e"] * u + s["up"] * v - s["n"] * h1
            out.append(("rafter", f"RF_Rafter_{k + 1}_{j + nh + 1:02d}", "C", p(-0.10), p(v1), s["e"], s["n"],
                        RAFTER["c"][1], h1))
    return out, sides, D, ze


def _course_step(D):
    """CPAC batten spacing (manual p.8-9): even steps from the first course to the top one at the ridge gap."""
    v_top = D / COS - BATTEN["ridge_gap"] / 2 / COS
    n = math.ceil((v_top - BATTEN["first"]) / BATTEN["lap_max"] - 1e-9)
    step = (v_top - BATTEN["first"]) / n
    assert BATTEN["lap"] - 1e-9 <= step <= BATTEN["lap_max"] + 1e-9, f"batten step {step:.4f} outside 0.32-0.34"
    return step, v_top


def _inset(V, n, keep, g):
    """Polygon V (plane normal n) with every edge except those indexed in keep pulled in by g within the plane."""
    m, c = len(V), sum(V, Vector()) / len(V)
    lines = []
    for i in range(m):
        a, e = V[i], (V[(i + 1) % m] - V[i]).normalized()
        w = n.cross(e)
        w = w if w.dot(c - a) > 0 else -w
        lines.append((a + w * (0.0 if i in keep else g), e))
    out = []
    for i in range(m):   # vertex i = edge i-1 ∩ edge i
        (p, e), (q, f) = lines[i - 1], lines[i]
        out.append(p + e * ((q - p).cross(f).dot(n) / e.cross(f).dot(n)))
    return out


def _battens(sides, D, step, first, w, top_gap, top_off):
    """[(side k, v, u0, u1)] courses parallel to the eave, ends kept on their own side of the hip line."""
    out = []
    for k, s in enumerate(sides):
        vt = D / COS
        vs = [first + i * step for i in range(int((vt - top_gap - first) / step + 1e-9) + 1)]
        if vt - top_off - vs[-1] > 0.10:
            vs.append(vt - top_off)
        for v in vs:
            u0 = (v + w / 2) * COS + 0.002
            u1 = s["L"] - u0
            if u1 - u0 > ROOF["min_len"]:
                out.append((k, v, u0, u1))
    return out


def _cuboid(bm, ctr, ax, h):
    """Box centred at ctr, axes ax (3 unit vectors), half sizes h, into bm (outward normals)."""
    vs = [bm.verts.new(ctr + ax[0] * (h[0] * i) + ax[1] * (h[1] * j) + ax[2] * (h[2] * k))
          for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


WELD = dict(r=0.003, spec="รอยเชื่อมเหล็ก (fillet ~3 มม.)")


def _on_box(p, n, box, tol=2e-4):
    """Is a face (centre p, normal n) on a face of the box (ctr, axes, half sizes)?"""
    ctr, ax, h = box
    q = p - ctr
    for k in range(3):
        if abs(abs(n.dot(ax[k])) - 1) < 1e-3 and abs(abs(q.dot(ax[k])) - h[k]) < tol:
            return all(abs(q.dot(ax[j])) <= h[j] + tol for j in range(3) if j != k)
    return False


def _edges_in_box(o, box, tol=5e-4):
    """Does any edge of o pass inside the box shrunk by tol (slab clipping; vertices alone miss a member that runs
    right through)?"""
    ctr, ax, h = box
    for e in o.data.edges:
        a, b = (o.matrix_world @ o.data.vertices[i].co for i in e.vertices)
        t0, t1 = 0.0, 1.0
        for k in range(3):
            pa, pb, lim = (a - ctr).dot(ax[k]), (b - ctr).dot(ax[k]), h[k] - tol
            if abs(pb - pa) < 1e-12:
                if abs(pa) >= lim:
                    t0, t1 = 1.0, 0.0
                    break
                continue
            u0, u1 = sorted(((-lim - pa) / (pb - pa), (lim - pa) / (pb - pa)))
            t0, t1 = max(t0, u0), min(t1, u1)
            if t0 >= t1:
                break
        if t0 < t1:
            return True
    return False


def _eave_plane(s):
    """(point, outward plan normal) of the fascia back on eave side s."""
    return s["Q0"] + s["w"] * BACK, Vector((-s["w"].x, -s["w"].y, 0)).normalized()   # w points inward


def _plumb_cut(bm, ks, sides):
    """Cut the member in bm by the fascia-back planes of sides ks, closing each cut with a face."""
    for k in ks:
        pc, pn = _eave_plane(sides[k])
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=pc, plane_no=pn, clear_outer=True)
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def _cope(o, d, cutters, keep):
    """Cut member o (closed solid along d) to the boxes it runs into, by an exact boolean difference, as the end is
    cut on site to sit flush against the other member's face (spec 29 ต.ค.: no gaps at steel joints). Pieces cut
    off beyond a box are dropped (the part nearest `keep` stays). Writes len (extent along d) and cut_by.
    Returns (weld edges [(a, b)] where a face lying on a box meets the member's own walls, indices of the boxes it
    really meets: a box whose overlap is only in the channel's hollow leaves no face)."""
    tmp = []
    for i, box in enumerate(cutters):
        bm = bmesh.new()
        _cuboid(bm, *box)
        me = bpy.data.meshes.new(f"_cut{i}")
        bm.to_mesh(me)
        bm.free()
        t = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(t)   # evaluated even when o's collection is excluded
        tmp.append(t)
        m = o.modifiers.new(f"cut{i}", "BOOLEAN")
        m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", t
    old = o.data
    sc = bpy.context.scene.collection
    linked = o.name not in sc.objects
    try:
        if linked:   # an excluded collection is not evaluated: the cut would silently not happen
            sc.objects.link(o)
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        new = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    finally:   # never leave the member in the scene collection or the cutters behind
        if linked and o.name in sc.objects:
            sc.objects.unlink(o)
        o.modifiers.clear()
        for t in tmp:
            me = t.data
            bpy.data.objects.remove(t)
            bpy.data.meshes.remove(me)
    for k in old.keys():
        new[k] = old[k]
    o.data = new
    bpy.data.meshes.remove(old)
    bm = bmesh.new()
    bm.from_mesh(new)
    left, isl = set(bm.faces), []
    while left:   # islands: keep the one nearest `keep`
        f0 = left.pop()
        grp, stack = {f0}, [f0]
        while stack:
            for e in stack.pop().edges:
                for g in e.link_faces:
                    if g in left:
                        left.discard(g)
                        grp.add(g)
                        stack.append(g)
        isl.append(grp)
    best = min(isl, key=lambda g: min((v.co - keep).length for f in g for v in f.verts))
    bmesh.ops.delete(bm, geom=[f for g in isl if g is not best for f in g], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    hit = {i: {f for f in bm.faces if _on_box(f.calc_center_median(), f.normal, b)} for i, b in enumerate(cutters)}
    on = set().union(*hit.values())
    welds = [(e.verts[0].co.copy(), e.verts[1].co.copy()) for e in bm.edges
             if len(e.link_faces) == 2 and (e.link_faces[0] in on) != (e.link_faces[1] in on)]
    us = [v.co.dot(d) for v in bm.verts]
    bm.to_mesh(new)
    bm.free()
    new["len"], new["axis"] = max(us) - min(us), tuple(d)
    return welds, [i for i, fs in hit.items() if fs]


def _end_welds(o, d):
    """Weld all round both end sections of a member that only butts (king post on the plate, under the ridge)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    end = {f for f in bm.faces if abs(f.normal.dot(d)) > 0.999}
    out = [(e.verts[0].co.copy(), e.verts[1].co.copy()) for e in bm.edges
           if len(e.link_faces) == 2 and (e.link_faces[0] in end) != (e.link_faces[1] in end)]
    bm.free()
    return out


def _weld_obj(c, name, segs):
    """Weld beads along segments [(a, b)] as one bevelled curve; length kept for the take-off."""
    _drop(bpy.data.curves, name)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", WELD["r"], 2
    for a, b in segs:
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co, sp.points[1].co = (*a, 1), (*b, 1)
    L = sum((b - a).length for a, b in segs)
    for k, v in dict(element="weld", type="RW1", th=WELD["spec"], length=L).items():
        cu[k] = v
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(mat("M_Weld", (0.12, 0.11, 0.10), 0.6, 0.8))
    c.objects.link(o)
    return o


def build_roof():
    """ST07: rafters, hips, ridge, king posts (C_ROOF); CPAC battens, tiles, caps (C_CPAC)."""
    for v in bpy.context.scene.view_layers:   # the old one-piece roof (e42_build) would double up
        lc = _find_lc(v.layer_collection, "E42")
        if lc:
            lc.exclude = True
    c, cc = _clear(C_ROOF), _clear(C_CPAC)
    steel = mat("M_Steel_C", (0.05, 0.05, 0.055), 0.35, 1.0)
    galv = mat("M_Steel_Galv", (0.62, 0.64, 0.66), 0.35, 0.9)
    mem, sides, D, ze = _members()
    built = []
    for kind, name, sec, p0, p1, side, up, w, h in mem:
        bm = bmesh.new()
        _sweep(bm, sec, p0, p1, side, up)
        if kind in ("rafter", "hip"):   # cut plumb at the fascia back: one eave plane for a rafter, both for a hip
            _plumb_cut(bm, [k for k, s in enumerate(sides) if (p0 - s["Q0"]).dot(s["w"]) < 0.05], sides)
        spec = dict(ridge=("RF1", "อกไก่ 2C ประกบ 100×50×20×2.3 มม."), post=("RF2", "ดั้ง 2C ประกบ 100×50×20×2.3 มม."),
                    hip=("RF3", "ตะเข้สัน 2C ประกบ 100×50×20×2.3 มม."), rafter=("RF4", RAFTER["spec"]))[kind]
        sp = RAFTER if kind == "rafter" else TWO_C
        o = _obj(c, name, bm, steel, element="steel", type=spec[0], th=spec[1], kg_m=sp["kg_m"], stock=sp["stock"],
                 pieces=sp.get("pieces", 1), swept=True, member=kind, p0=tuple(p0))
        d = (p1 - p0).normalized()
        o.data["len"], o.data["axis"] = (p1 - p0).length, tuple(d)
        welds = []
        if kind in ("hip", "rafter"):   # run into what is already there, then cut flush to it and welded
            hit = [(n, b) for n, b in built if obb_overlap(_box(p0, p1, side, up, w, h), b) > 1e-4]
            if hit:
                welds, used = _cope(o, d, [b for _, b in hit], p0)
                o.data["cut_by"], o.data["coped"] = ",".join(hit[i][0] for i in used), True
                if o.data["len"] < ROOF["min_len"]:   # nothing worth a piece left (a corner stub)
                    me = o.data
                    bpy.data.objects.remove(o)
                    bpy.data.meshes.remove(me)
                    continue
        if kind == "post":
            welds = _end_welds(o, d)
        if kind == "rafter":   # seat on the plate's outer top edge: a bead each side across the bottom flange
            ow = -Vector((d.x, d.y, 0)).normalized()
            grid = max(Vector((x, y, 0)).dot(ow) for x in GX.values() for y in GY.values())
            q = p0 + d * ((p0.dot(ow) - grid - PLATE["b"] / 2) / d.xy.length)   # underside over the plate edge
            for dd in (-0.004, 0.004):
                welds.append((q + d * dd - side * (w / 2), q + d * dd + side * (w / 2)))
        if welds:
            _weld_obj(c, f"WD_{name[3:]}", welds)
        us = [v.co.dot(d) - p0.dot(d) for v in o.data.vertices]   # the box of what is left (after the plumb cut)
        o.data["len"] = max(us) - min(us)
        built.append((name, _box(p0 + d * min(us), p0 + d * max(us), side, up, w, h)))
        ctr, ax_, hh = built[-1][1]   # the box later members were cut to, and the build order (selfcheck)
        o.data["box"], o.data["order"] = [*ctr, *ax_[0], *ax_[1], *ax_[2], *hh], len(built)
    obst = [b for n, b in built if not n.startswith("RF_Rafter")]
    step, v_top = _course_step(D)
    gap = D / COS - v_top - 1e-6
    for k, v, u0, u1 in _battens(sides, D, step, BATTEN["first"], BATTEN["w"], gap, gap):
        s = sides[k]
        q = _fit2(s["Q0"] + s["e"] * u0 + s["up"] * v, s["Q0"] + s["e"] * u1 + s["up"] * v, s["up"], s["n"],
                  BATTEN["w"], BATTEN["h"], obst)
        if not q:
            continue
        bm = bmesh.new()
        _sweep(bm, "hat", *q, s["up"], s["n"])
        _obj(cc, f"RF_Batten_{k + 1}_{v:.2f}", bm, galv, element="batten", type="RB1", th=BATTEN["spec"],
             stock=BATTEN["stock"], joint=BATTEN["joint"], swept=True)
    # tiles on the battens: the bed plane = rafter tops + batten height (hidden; carries the tiled area)
    zb = ze + BATTEN["h"] / COS
    E = _geom()[0]
    r0, r1, ax = _ridge(E, sides, D, ze)
    assert ax.y > 0.5, "bed faces below are ordered for a ridge along y"   # shortcut: E42's ridge runs along y
    bm = bmesh.new()
    o_ = _tile_edge()   # past the bird-stop face (8 mm thick)
    xs_, ys_ = sorted({x for x, _ in E}), sorted({y for _, y in E})
    cs = [bm.verts.new((x + (o_ if x == xs_[1] else -o_), y + (o_ if y == ys_[1] else -o_), zb - o_ * TAN)) for x, y in E]
    R0, R1 = [bm.verts.new((*p.xy, zb + D * TAN)) for p in (r0, r1)]
    for f in ((cs[0], cs[1], R0), (cs[1], cs[2], R1, R0), (cs[2], cs[3], R1), (cs[3], cs[0], R0, R1)):
        bm.faces.new(f)
    bm.normal_update()
    bed = _obj(cc, "RF_Bed_Hip", bm, mat("M_Roof_Underlay", (0.022, 0.025, 0.032), 0.9), element="tile", type="RT1",
               th=TILE["spec"], per_m2=TILE["per_m2"], waste=TILE["waste"])
    assert all(p.normal.z > 0 for p in bed.data.polygons), "bed faces point down"
    # the tiles stop TILE["hip_gap"] / 2 short of every hip and the ridge (Dry Tech, manual p.22); the full bed keeps
    # the take-off area (cut tiles are bought whole)
    bm = bmesh.new()
    for poly in bed.data.polygons:
        V = [bed.data.vertices[i].co.copy() for i in poly.vertices]
        z0 = min(q.z for q in V)
        keep = {i for i in range(len(V)) if abs(V[i].z - z0) < 1e-6 and abs(V[(i + 1) % len(V)].z - z0) < 1e-6}
        bm.faces.new([bm.verts.new(v) for v in _inset(V, poly.normal.copy(), keep, TILE["hip_gap"] / 2)])
    bm.normal_update()
    cut = _obj(cc, "RF_Cut_Hip", bm, bed.data.materials[0])
    tiles = cpac_tiles("RF_Cut_Hip", pitch_u=TILE["cover"], lap=step, wave=TILE["wave"], tile_w=TILE["cover"], c=C_CPAC)
    tiles.modifiers["Thick"].thickness, tiles.modifiers["Thick"].offset = TILE["t"], 1.0   # up off the battens
    bed.hide_viewport = bed.hide_render = cut.hide_viewport = cut.hide_render = True
    return len(built)


def build_metal_test():
    """The metal-sheet roof on the same rafters (TEST, spec 29 ต.ค.): box purlins + sheets with PU foam."""
    c = _clear(C_MS)
    tube_m = mat("M_Steel_C", (0.05, 0.05, 0.055), 0.35, 1.0)
    sheet_m = mat("M_MetalSheet", (0.72, 0.74, 0.76), 0.3, 0.9)
    foam_m = mat("M_PUFoam", (0.93, 0.93, 0.90), 0.8)
    mem, sides, D, _ = _members()
    built = {mm[1]: bpy.data.objects[mm[1]] for mm in mem if mm[1] in bpy.data.objects}
    obst = [(n, _box(Vector(o.data["p0"]), Vector(o.data["p0"]) + Vector(o.data["axis"]) * o.data["len"], *m[5:]))
            for m in mem if m[0] in ("hip", "ridge", "post") for n, o in [(m[1], built[m[1]])]]
    B = MS["tube"][0]
    # สะพานหนู (SSR760 p.8): a support each side of every hip, centred MS["hip_batten"] from the hip centreline in
    # plan, flush with the purlins; the purlins run into them and are cut and welded there (spec 29 ต.ค.)
    for name, q0, q1, side, up in _hip_battens(sides, D, mem):
        o, L = _tube_member(c, name, q0, q1, side, up, obst, q0, tube_m, element="steel", type="MP2",
                            th="สะพานหนูข้างตะเข้ " + MS["spec_p"].split(" @")[0], kg_m=MS["kg_m"], stock=MS["stock"])
        assert o, f"{name}: no room beside the hip"
        obst.append((name, _box(q0, q0 + (q1 - q0).normalized() * L, side, up, B, B)))
    top = MS["ridge_gap"] / 2 / COS   # SSR760 manual p.6: the top purlins 15 cm apart across the ridge
    courses = _battens(sides, D, MS["step"], MS["first"], B, top, top)
    purl_v = sorted({v for _, v, _, _ in courses})
    for k, v, u0, u1 in courses:
        s = sides[k]
        q0, q1 = s["Q0"] + s["e"] * u0 + s["up"] * v, s["Q0"] + s["e"] * u1 + s["up"] * v
        _tube_member(c, f"MS_Purlin_{k + 1}_{v:.2f}", q0, q1, s["up"], s["n"], obst, (q0 + q1) / 2, tube_m,
                     element="steel", type="MP1", th=MS["spec_p"], kg_m=MS["kg_m"], stock=MS["stock"])
    prof = strip(_sheet_path(), MS["sheet_t"])
    width = _sheet_path()[-1][0]
    foam = [(0.0, -MS["foam"]), (width, -MS["foam"]), (width, 0.0), (0.0, 0.0)]
    n_sheet = 0
    for k, s in enumerate(sides):
        vt, base = D / COS, s["n"] * (B + MS["foam"])
        cuts = _sheet_cuts(s, D)
        rows, v = [], _sheet_v0()   # from 15 cm past the fascia face
        while v < vt - 1e-6:   # eave → ridge in stock lengths, each end lap centred on a purlin (screwed there)
            v1 = vt if v + MS["length"] >= vt else max(q for q in purl_v if q + MS["end_lap"] / 2 <= v + MS["length"]) + MS["end_lap"] / 2
            assert v1 > v + 0.5, "sheet rows do not advance: purlins too far apart for the sheet length"
            rows.append((v, v1))
            v = rows[-1][1] - MS["end_lap"] if rows[-1][1] < vt - 1e-6 else vt
        j = 0
        while j * MS["cover"] < s["L"] - 1e-6:
            for r, (v0, v1) in enumerate(rows):
                o = s["Q0"] + s["e"] * (j * MS["cover"]) + base + s["n"] * (0.0012 * r + 0.0006 * (j % 2))   # laps on top
                pl = lambda u, a, z, o=o: tuple(o + s["up"] * u + s["e"] * a + s["n"] * z)
                parts = []
                for outline in (prof, foam):
                    bm = bmesh.new()
                    prism(bm, outline, v0, v1, pl)
                    for pc, pn in cuts:
                        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=pc,
                                               plane_no=Vector((pn.x, pn.y, 0)).normalized(), clear_inner=True)
                    parts.append(bm)
                if not parts[0].faces:
                    for bm in parts:
                        bm.free()
                    continue
                n_sheet += 1
                _obj(c, f"MS_Sheet_{k + 1}_{j:02d}_{r}", parts[0], sheet_m, element="sheet", type="MS1", th=MS["spec_s"])
                _obj(c, f"MS_Foam_{k + 1}_{j:02d}_{r}", parts[1], foam_m)
            j += 1
    return n_sheet


def _sheet_v0():
    """Sheet start up the slope: the pans 15 cm past the fascia face in plan (they ride B + foam off the rafters,
    which carries them out by that × sin)."""
    return -(FASCIA["sheet_over"] - (MS["tube"][1] + MS["foam"]) * SIN) / COS


def _tube_member(c, name, p0, p1, side, up, obst, keep, m, **props):
    """A box-tube member p0 → p1 cut flush to the named boxes it runs into, welded there: (object, length) or
    (None, 0) when less than ROOF["min_len"] is left."""
    B = MS["tube"][0]
    bm = bmesh.new()
    _sweep(bm, "tube", p0, p1, side, up)
    o = _obj(c, name, bm, m, swept=True, p0=tuple(p0), **props)
    d = (p1 - p0).normalized()
    o.data["len"], o.data["axis"] = (p1 - p0).length, tuple(d)
    hit = [(n, b) for n, b in obst if obb_overlap(_box(p0, p1, side, up, B, B), b) > 1e-4]
    if hit:
        welds, used = _cope(o, d, [b for _, b in hit], keep)
        o.data["cut_by"], o.data["coped"] = ",".join(hit[i][0] for i in used), True
        if o.data["len"] < ROOF["min_len"]:
            me = o.data
            bpy.data.objects.remove(o)
            bpy.data.meshes.remove(me)
            return None, 0.0
        vs = [v.co.dot(d) for v in o.data.vertices]
        o.data["p0"] = tuple(p0 + d * (min(vs) - p0.dot(d)))   # the kept piece's start (both ends may be cut)
        if welds:
            _weld_obj(c, f"WD_{name[3:]}", welds)
    return o, o.data["len"]


def _sheet_cuts(s, D):
    """Planes (point, plan normal into the sheet) that keep a plane's sheets MS["hip_gap"] inside both hips and
    the ridge (SSR760 p.8: cut about 2.5 cm short of the hip line)."""
    out = []
    for pc, pn in ((s["Q0"], s["e"] - s["w"]), (s["Q0"] + s["e"] * s["L"], -s["e"] - s["w"]), (s["Q0"] + s["w"] * D, -s["w"])):
        pn = Vector((pn.x, pn.y, 0)).normalized()
        out.append((pc + pn * MS["hip_gap"], pn))
    return out


def _hip_battens(sides, D, mem):
    """[(name, p0, p1, side, up)] สะพานหนู bottom-centre lines on the rafter tops, from the eave line to the ridge."""
    out = []
    for k, s in enumerate(sides):
        for end, sg in ((0.0, 1), (s["L"], -1)):   # the hip at each end of this eave
            h = (s["e"] * sg + s["w"]).normalized()   # hip in plan, up from the eave corner
            off = (h.cross(Vector((0, 0, 1))) * sg).normalized() * MS["hip_batten"]   # into this plane
            a = s["Q0"] + s["e"] * end + off
            # the line through `a` parallel to the hip, kept in this plane: run up-slope by the hip's plan direction
            t0 = (BACK + 0.005 - (a - s["Q0"]).dot(s["w"])) / h.dot(s["w"])   # back to the fascia back
            t1 = (D - (a - s["Q0"]).dot(s["w"])) / h.dot(s["w"])   # up to the ridge line
            p = lambda t: Vector(((a + h * t).x, (a + h * t).y, 0.0))
            z = lambda q: s["Q0"].z + (q - Vector((s["Q0"].x, s["Q0"].y, 0))).dot(s["w"]) * TAN
            p0, p1 = p(t0), p(t1 - MS["ridge_gap"] / 2 / h.dot(s["w"]))
            p0.z, p1.z = z(p0), z(p1)
            d = (p1 - p0).normalized()
            out.append((f"MS_HipBatten_{k + 1}_{'ab'[sg < 0]}", p0, p1, s["n"].cross(d).normalized() * -1, s["n"]))
    return out


def show_cover(which="cpac"):
    """Show one roof covering: "cpac" (the house's) or "metal" (the test)."""
    for v in bpy.context.scene.view_layers:
        for name, on in ((C_CPAC, which == "cpac"), (C_MS, which == "metal")):
            lc = _find_lc(v.layer_collection, name)
            if lc:
                lc.exclude = not on


def _read(o):
    """World vertices, axis and length of a swept member read from the model (first ring → second ring)."""
    bm = _world_bm(o)
    vs = [v.co.copy() for v in bm.verts]
    ends = [(f.calc_area(), f.normal.copy(), f.calc_center_median()) for f in bm.faces]
    bm.free()
    if "axis" in o.data:   # written at build (a coped member's rings are no longer in order)
        return vs, Vector(o.data["axis"]), o.data["len"], ends
    n = len(vs) // (2 * o.data.get("pieces", 1))
    return vs, (vs[n] - vs[0]).normalized(), (vs[n] - vs[0]).length, ends


def selfcheck_roof():
    """Roof frame + CPAC cover against the user's spec, read back from the model."""
    xs, ys = sorted(GX.values()), sorted(GY.values())
    out = FACE + ROOF["eave"]
    z_plate = WALL_TOP + PLATE["h"]
    objs = [o for cn in (C_ROOF, C_CPAC) for o in bpy.data.collections[cn].objects if o.type == "MESH"]
    mem = {o.name: (o, *_read(o)) for o in objs if o.data.get("swept") and o.data["element"] in ("steel", "batten")}
    kind = lambda k: [m for m in mem.values() if m[0].data.get("member") == k]
    # profiles: each end face is the section of the drawing (hollow, not a filled cap)
    b = BATTEN
    hat = b["t"] * (b["w"] - b["top"] - (b["h"] - b["t"]) / math.tan(math.radians(b["side"])) + b["top"] +
                    (b["h"] - b["t"]) + (b["h"] - b["t"]) / math.sin(math.radians(b["side"])))
    _, sides_, _, _ = _geom()
    for name, (o, vs, d, L, faces) in mem.items():
        lo = min(v.dot(d) for v in vs)
        exp = hat if o.data["element"] == "batten" else o.data.get("pieces", 1) * PLATE["c_kg_m"] / RHO
        if o.data.get("member") == "rafter":   # plumb cut at the fascia back: the section seen at cos(pitch)
            pc, pn = next(_eave_plane(s) for s in sides_ if abs(Vector((d.x, d.y, 0)).normalized().dot(s["w"]) - 1) < 1e-6)
            end = sum(a for a, nrm, cc in faces if nrm.dot(pn) > 0.999 and abs((cc - pc).dot(pn)) < 1e-4)
            exp /= abs(pn.dot(d))
        elif o.data.get("member") == "hip":   # cut by both fascia planes: some cut face on each
            cuts = [sum(a for a, nrm, cc in faces if nrm.dot(pn) > 0.999 and abs((cc - pc).dot(pn)) < 1e-4)
                    for pc, pn in (_eave_plane(s) for s in sides_)]
            assert sum(1 for x in cuts if x > 1e-5) == 2, f"{name}: not cut plumb by both fascia planes"
            continue
        else:
            end = sum(a for a, nrm, cc in faces if abs(nrm.dot(d)) > 0.99 and cc.dot(d) < lo + 1e-5)
        assert abs(end - exp) <= 0.02 * exp, f"{name}: end face {end * 1e6:.0f} mm², section {exp * 1e6:.0f} mm²"
    # rafters: 30°, @ step along each eave, tops reaching the eave line 70 cm out from the finished wall face
    raf = kind("rafter")
    assert raf, "no rafters"
    by_side = {}
    for o, vs, d, L, _ in raf:
        assert abs(math.degrees(math.asin(d.z)) - ROOF["pitch"]) < 0.01, f"{o.name}: {math.degrees(math.asin(d.z)):.3f}°"
        ow = -Vector((d.x, d.y, 0)).normalized()   # outward, toward the eave
        grid = max(Vector((x, y, 0)).dot(ow) for x in xs for y in ys)
        assert abs(max(v.dot(ow) for v in vs) - grid - (out - BACK)) < 1e-4, f"{o.name}: end not at the fascia back"
        along = Vector((-ow.y, ow.x, 0))
        by_side.setdefault(tuple(round(c, 3) for c in ow), []).append(Vector(o.data["p0"]).dot(along))
        # underside through the plate's outer top edge (rafters long enough to reach it)
        edge = grid + PLATE["b"] / 2
        dn = d.cross(Vector((0, 0, 1)).cross(d)).normalized()   # rafter's up, square to it in the vertical plane
        under = [v for v in vs if (v - vs[0]).dot(dn) < 0.002 + min((q - vs[0]).dot(dn) for q in vs)]
        if min(v.dot(ow) for v in vs) < edge - 0.01:
            p = min(under, key=lambda v: abs(v.dot(ow) - edge))
            z = p.z + (p.dot(ow) - edge) * TAN
            assert abs(z - z_plate) < 0.002, f"{o.name}: underside {z:.4f} at the plate edge, plate top {z_plate:.4f}"
    for ow, us in by_side.items():
        us = sorted(us)
        assert all(abs((b_ - a_) - ROOF["step"]) < 1e-4 for a_, b_ in zip(us, us[1:])), f"rafters off {ROOF['step']} m: {ow}"
    # hips: four, 45° in plan, from the eave corners
    hips = kind("hip")
    assert len(hips) == 4, f"{len(hips)} hips"
    corners = [(x, y) for x in (xs[0] - out, xs[-1] + out) for y in (ys[0] - out, ys[-1] + out)]
    for o, vs, d, L, _ in hips:
        assert abs(abs(d.x) - abs(d.y)) < 1e-4, f"{o.name}: not 45° in plan"
        low = min(vs, key=lambda v: v.z)
        assert min((low.xy - Vector(c)).length for c in corners) < 0.12, f"{o.name}: does not start at an eave corner"
        assert max(obb_overlap(obb(vs, d), p) for p in _plate_boxes()) > -0.002, f"{o.name}: not seated on a plate corner"
    # king posts stand on a wall plate and carry the ridge
    ridge = kind("ridge")
    assert len(ridge) == 1, "one ridge"
    rz = min(v.z for v in ridge[0][1])
    plates = [b for n, b in _solids([C_WALL]).items() if n[0].endswith("_2C")]
    for o, vs, d, L, _ in kind("post"):
        lo_, hi_ = min(v.z for v in vs), max(v.z for v in vs)
        cx, cy = sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs)
        assert abs(lo_ - z_plate) < 1e-4 and any(p[0] <= cx <= p[3] and p[1] <= cy <= p[4] for p in plates), \
            f"{o.name}: not on a wall plate"
        assert abs(hi_ - rz) < 1e-4, f"{o.name}: top {hi_:.4f}, ridge underside {rz:.4f}"
    # battens: first course, then at most the lap apart up each plane
    bat = [m for m in mem.values() if m[0].data["element"] == "batten"]
    rows = {}
    for o, vs, d, L, _ in bat:
        k = o.name.split("_")[2]
        rows.setdefault(k, []).append(min(v.z for v in vs))
    ze = z_plate + 0.10 / COS - (out - PLATE["b"] / 2) * TAN   # rafter top at the eave line
    vt = (min(xs[-1] - xs[0], ys[-1] - ys[0]) / 2 + out) / COS   # eave → ridge/apex up the slope
    assert len(rows) == 4, f"battens on {len(rows)} planes"
    v_top = vt - BATTEN["ridge_gap"] / 2 / COS   # the top pair 8 cm apart across the ridge (manual p.8)
    _, sides_, D_, _ = _geom()
    for k, zs in rows.items():   # bottom flange edge is w/2 below the course line
        vs_ = sorted({round((z - ze) / SIN + BATTEN["w"] / 2, 4) for z in zs})
        gaps = [b_ - a_ for a_, b_ in zip(vs_, vs_[1:])]
        assert abs(vs_[0] - BATTEN["first"]) < 0.01 and vs_[-1] > v_top - BATTEN["lap_max"] - 0.01, f"battens plane {k}: {vs_}"
        assert all(BATTEN["lap"] - 2e-3 <= g <= BATTEN["lap_max"] + 2e-3 for g in gaps) and max(gaps) - min(gaps) < 2e-3, \
            f"battens on plane {k} not even at 32-34 cm: {[round(g, 4) for g in gaps]}"
        if sides_[int(k) - 1]["L"] - 2 * D_ > 1e-6:   # the trapezoid planes reach the ridge pair
            assert abs(vs_[-1] - v_top) < 0.01, f"battens plane {k}: top course {vs_[-1]:.3f}, ridge pair at {v_top:.3f}"
    hip_lines = [(min(vs, key=lambda v: v.z).xy, d.xy.normalized()) for o, vs, d, L, _ in hips]
    for o, vs, d, L, _ in bat:   # every run reaches a hip at both ends (within the hip's half width + pull-back)
        for end in (min(vs, key=lambda v: v.dot(d)), max(vs, key=lambda v: v.dot(d))):
            gap = min(abs((end.xy - p).cross(q)) for p, q in hip_lines)
            assert gap < 0.15, f"{o.name}: ends {gap:.3f} m short of a hip"
    # nothing clashes: frame, battens, wall plates, walls and columns
    boxes = [(n, obb(vs, d)) for n, (o, vs, d, L, _) in mem.items()]
    boxes += [(n[0], (Vector(((b_[0] + b_[3]) / 2, (b_[1] + b_[4]) / 2, (b_[2] + b_[5]) / 2)),
                      [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))],
                      [(b_[3] - b_[0]) / 2, (b_[4] - b_[1]) / 2, (b_[5] - b_[2]) / 2])) for n, b_ in _solids([C_WALL, C_COL]).items()]
    reach = lambda B: Vector([sum(B[2][k] * abs(B[1][k][i]) for k in range(3)) for i in range(3)])   # half AABB
    aabb = [(n, B, B[0] - reach(B), B[0] + reach(B)) for n, B in boxes]
    clash = []
    for i, (na, A, la, ha) in enumerate(aabb):
        for nb, B, lb, hb in aabb[i + 1:]:
            if na == nb or any(la[k] > hb[k] or lb[k] > ha[k] for k in range(3)):
                continue
            if (na in mem or nb in mem) and obb_overlap(A, B) > 2e-4:
                if na in mem and nb in mem and "order" in mem[na][0].data and "order" in mem[nb][0].data:
                    # frame members: the later one was cut to the earlier one's box, so none of its points may lie
                    # inside that box (an angled cut leaves the boxes overlapping)
                    x, y = sorted((na, nb), key=lambda q: mem[q][0].data["order"])[::-1]
                    bx = list(mem[y][0].data["box"])
                    ctr, ax_, hh = Vector(bx[0:3]), [Vector(bx[3:6]), Vector(bx[6:9]), Vector(bx[9:12])], bx[12:15]
                    if _edges_in_box(mem[x][0], (ctr, ax_, hh)):
                        clash.append((x, y, "runs into it"))
                    continue
                clash.append((na, nb, round(obb_overlap(A, B), 4)))
    assert not clash, f"roof clashes: {clash[:4]}"
    # every coped end sits flush on what it was cut to, and is welded
    for n_, (o, vs, d, L, faces) in mem.items():
        for y in filter(None, o.data.get("cut_by", "").split(",")):
            Y = dict(boxes)[y]
            assert any(_on_box(cc, nrm, Y) for a_, nrm, cc in faces), f"{n_}: cut end not flush on {y}"
        if o.data.get("cut_by") or o.data.get("member") in ("post", "rafter"):
            w = bpy.data.objects.get("WD_" + n_[3:])
            assert w and w.data["length"] > 0.02, f"{n_}: no weld"
    # tiles: the bed's slope area = plan area inside the eave line / cos(pitch) (every plane has the same pitch)
    r = qto(C_CPAC)
    o_ = out + _tile_edge()   # tiles run past the fascia
    plan = (xs[-1] - xs[0] + 2 * o_) * (ys[-1] - ys[0] + 2 * o_)
    assert abs(r[("tile", "RT1")]["area"] - plan / COS) < 1e-4 * plan, "tile area"
    return (f"roof ok: {len(raf)} rafters @ {ROOF['step']} m · 4 hips · ridge · {len(kind('post'))} king posts · "
            f"{len(bat)} batten runs · tiled {plan / COS:.2f} m²")
