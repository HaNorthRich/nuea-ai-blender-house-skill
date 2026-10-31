"""E42 ST09 ทาสีรองพื้น (spec 29 ต.ค.), after the ceilings: one film per painted face, its area for the take-off.
  walls inside and out (new plaster): JOTUN Jotaplast Primer 18 L — every plaster face not against brick or concrete,
    inside from the room's floor up to its ceiling, outside up to the soffit (nothing above a ceiling is painted);
  ceilings (gypsum, Smartboard soffit + porch): JOTUN Essence Easy Ceiling 18 L — the boards' undersides;
  fascia (ไม้เชิงชาย): primer on its exposed faces (product not given by the user: Jotaplast Primer assumed).
Quantities (spec 29 ต.ค.): wall primer = the plastered wall area of every floor (พื้นที่ผนังฉาบเรียบรวมทุกชั้น, the
ST06 plaster take-off; the films drawn on the faces seen are for the picture); ceilings: area ÷ 87.5 m² a bucket
(35 m² / gallon × 5 gallons ÷ 2 coats); fascia: its painted area.

    exec(<e42_struct>) … exec(<e42_ceiling>); exec(<this>)
    build_primer(); print(report(C_PAINT)); print(selfcheck_primer())
"""
import math
import bmesh
from mathutils import Vector

C_PAINT = "E42 ST09 Primer"
# exposure probes out along a face's normal: just off it, where the primer and coat-1 films sit, past a 1 mm sliver
PROBES = (0.0005, 0.00065, 0.00145, 0.0015, 0.003)
PAINT = dict(film=0.0003, gap=0.0005, per_bucket=35.0 * 5 / 2,   # gap: off the surface / between coats (display)
             wall="สีรองพื้นปูนใหม่ JOTUN JOTAPLAST PRIMER 18 ลิตร (ภายนอก + ภายใน)",
             ceil="สีทาฝ้า JOTUN Essence Easy Ceiling 18 ลิตร สีขาวหมอก (รองพื้นฝ้ายิปซัมภายใน)",
             ceil_out="สีรองพื้นปูนใหม่ JOTUN JOTAPLAST PRIMER 18 ลิตร (ฝ้าสมาร์ทบอร์ดภายนอก: ชายคา + เฉลียง)",
             fascia="สีรองพื้น JOTUN JOTAPLAST PRIMER 18 ลิตร (ไม้เชิงชาย — รุ่นยังไม่ยืนยัน)")


def _backing():
    """Plan boxes of what plaster sits on: brick, tie beams, wall plates, columns (x0, y0, z0, x1, y1, z1)."""
    return [b for n, b in _solids([C_WALL, C_COL]).items()
            if bpy.data.objects[n[0]].data.get("element") in ("masonry", "concrete", "steel")]


def _solid_trees(objs):
    """One BVH per closed piece of each object (ray parity needs pieces that don't share faces)."""
    from mathutils.bvhtree import BVHTree
    trees = []
    for o in objs:
        bm = _world_bm(o)
        bm.verts.ensure_lookup_table()
        left = set(bm.faces)
        while left:
            f0 = left.pop()
            grp, stack = [f0], [f0]
            while stack:
                for e in stack.pop().edges:
                    for g in e.link_faces:
                        if g in left:
                            left.discard(g)
                            grp.append(g)
                            stack.append(g)
            vs = sorted({v.index for f in grp for v in f.verts})
            idx = {k: i for i, k in enumerate(vs)}
            lo = Vector((min(bm.verts[k].co.x for k in vs), min(bm.verts[k].co.y for k in vs), min(bm.verts[k].co.z for k in vs)))
            hi = Vector((max(bm.verts[k].co.x for k in vs), max(bm.verts[k].co.y for k in vs), max(bm.verts[k].co.z for k in vs)))
            trees.append((lo, hi, BVHTree.FromPolygons([bm.verts[k].co.copy() for k in vs],
                                                       [[idx[v.index] for v in f.verts] for f in grp])))
        bm.free()
    return trees


def _in_solid(p, trees):
    """Is p inside any of the pieces (ray parity, the real shapes — not their bounding boxes)? Three rays vote: one
    ray grazing an edge of a 1 mm bead sliver counted a hit twice and flipped the answer (E42 kitchen door jamb)."""
    rays = [Vector(r).normalized() for r in ((0.123, 0.456, 0.881), (-0.613, 0.271, 0.742), (0.377, -0.719, 0.583))]
    for lo, hi, t in trees:
        if not (lo.x <= p.x <= hi.x and lo.y <= p.y <= hi.y and lo.z <= p.z <= hi.z):
            continue
        odd = 0
        for ray in rays:
            n, q = 0, p
            for _ in range(64):
                hit = t.ray_cast(q, ray)
                if hit[0] is None:
                    break
                n, q = n + 1, hit[0] + ray * 1e-6
            odd += n % 2
        if odd >= 2:
            return True
    return False


def _rooms():
    """{room: ((x0, y0, x1, y1), floor z, ceiling z)} from the ceiling stage and the walls."""
    out = {}
    for room, (seed, kind) in ROOMS.items():
        f0 = _floor_z(seed)   # read from the slab, as the ceiling check does
        zc = f0 + (CEIL["h_bath"] if kind == "mr" else CEIL["h"])
        out[room] = (_room_rect(seed, zc + 0.05), f0, zc)
    return out


def _clip_axis(poly, k, val, keep_below):
    """Polygon (3D points) cut by the plane coordinate k = val, keeping the side below (or above) it."""
    out = []
    ins = lambda p: p[k] <= val + 1e-9 if keep_below else p[k] >= val - 1e-9
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        if ins(p):
            out.append(p)
        if ins(p) != ins(q):
            t = (val - p[k]) / (q[k] - p[k])
            out.append(p + (q - p) * t)
    return out


def _minus_box(poly, b):
    """A convex polygon (3D points) less an axis box: the parts outside it."""
    out, rest = [], poly
    for k in range(3):
        for val, below in ((b[k], True), (b[k + 3], False)):
            if len(rest) < 3:
                return out
            part = _clip_axis(rest, k, val, below)
            if len(part) >= 3 and _poly_area(part) > 1e-9:
                out.append(part)
            rest = _clip_axis(rest, k, val, not below)
    return out


def _poly_area(poly):
    return sum(((poly[i] - poly[0]).cross(poly[i + 1] - poly[0])).length / 2 for i in range(1, len(poly) - 1))


def _faces():
    """Every plaster face seen, from the plaster meshes' own faces: [(polygon, normal, 'in'/'out', room)].
    A face whose front (0.5 mm and 3 mm out along its normal) is inside brick, concrete, a plate, a bead or more
    plaster (real shapes) is not seen. Inside faces are cut to the room's floor → ceiling, outside ones to below the
    soffit; a reveal (front inside the wall's depth) is cut at mid-depth, each half to the room or outside on its
    side."""
    rooms = _rooms()
    zs = _soffit_z()
    solids = _solid_trees([o for o in bpy.data.collections[C_WALL].objects if o.type == "MESH" and o.data.get("element") in
                           ("masonry", "concrete", "steel", "plaster", "bead")] +
                          [o for cn in (C_COL, C_SLAB, C_GB, C_STUB, C_FOOT) for o in bpy.data.collections[cn].objects
                           if o.type == "MESH" and o.data.get("element") == "concrete"])   # slab + beams: plaster sits on them
    where = lambda p: next((r for r, (rc, f0, f1) in rooms.items()
                            if rc[0] - 1e-3 <= p.x <= rc[2] + 1e-3 and rc[1] - 1e-3 <= p.y <= rc[3] + 1e-3), None)
    out, tiled = [], globals().get("tiled_wall_boxes", lambda: [])()   # tiled over (ST11): bath to the ceiling, splash
    for o in bpy.data.collections[C_WALL].objects:
        if not (o.type == "MESH" and o.data.get("element") == "plaster"):
            continue
        bm = _world_bm(o)
        for f in bm.faces:
            n = f.normal.copy()
            if not (abs(n.z) < 1e-3 or abs(n.z) > 0.999):
                continue
            c = f.calc_center_median()
            if any(_in_solid(c + n * d_, solids) for d_ in PROBES):   # 1 mm slivers by the beads
                continue
            poly = [v.co.copy() for v in f.verts]
            r0 = where(c + n * 0.0005)
            parts = [(poly, r0)]
            if r0 is None:   # in the wall's depth (or outside): a reveal splits at mid-depth between its sides
                vs = poly
                if abs(n.z) > 0.999:
                    k = 0 if max(v.x for v in vs) - min(v.x for v in vs) < max(v.y for v in vs) - min(v.y for v in vs) else 1
                else:
                    k = 1 if abs(n.x) > 0.5 else 0
                lo, hi = min(v[k] for v in vs), max(v[k] for v in vs)
                pa, pb = c.copy(), c.copy()
                pa[k], pb[k] = lo - 0.05, hi + 0.05
                ra, rb = where(pa + n * 0.0005), where(pb + n * 0.0005)
                if ra != rb:
                    m = (lo + hi) / 2
                    parts = [(_clip_axis(poly, k, m, True), ra), (_clip_axis(poly, k, m, False), rb)]
            for pp, room in parts:
                if room == "Bath":
                    continue
                z0, z1 = (rooms[room][1], rooms[room][2]) if room else (-1e9, zs)
                if abs(n.z) > 0.999:   # a head / sill: kept whole where its level is seen
                    if not (z0 - 1e-4 <= c.z <= z1 + 1e-4):
                        continue
                else:
                    pp = _clip_axis(_clip_axis(pp, 2, z1, True), 2, z0, False) if len(pp) >= 3 else pp
                pcs = [pp] if len(pp) >= 3 else []
                for b in tiled:
                    pcs = [q for x in pcs for q in _minus_box(x, b)]
                for pp in pcs:
                    if _poly_area(pp) <= 1e-6:
                        continue
                    cp = sum(pp, Vector()) / len(pp)   # this part's own centre: a covered half is not painted
                    if any(_in_solid(cp + n * d_, solids) for d_ in PROBES):
                        continue
                    out.append((pp, n, "in" if room else "out", room))
        bm.free()
    return out


def _poly_film(bm, poly, n, off=0.0):
    """A paint film on a face polygon, PAINT["gap"] + off out along its normal, PAINT["film"] thick; its area."""
    lo = [bm.verts.new(p + n * (PAINT["gap"] + off)) for p in poly]
    hi = [bm.verts.new(p + n * (PAINT["gap"] + off + PAINT["film"])) for p in poly]
    bm.faces.new(lo)
    bm.faces.new(hi[::-1])
    for i in range(len(poly)):
        bm.faces.new((lo[i], lo[(i + 1) % len(poly)], hi[(i + 1) % len(poly)], hi[i]))
    return _poly_area(poly)


def _film(bm, k, val, sg, span, zr, off=0.0):
    """A paint film on a vertical face (axis k at val, facing sg), span along the other axis, z range zr; `off`
    stands it over the coats already on (primer 0, the next coat one film out). k = 2: a flat face (head/sill),
    span = its plan rect (x0, y0, x1, y1)."""
    if k == 2:
        x0, y0, x1, y1 = span
        za, zb = sorted((val + sg * (PAINT["gap"] + off), val + sg * (PAINT["gap"] + off + PAINT["film"])))   # bottom faces: sg < 0
        _slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], za, zb)
        return (x1 - x0) * (y1 - y0)
    j = 1 - k
    t = PAINT["film"]
    p0 = [0.0, 0.0, 0.0]
    corners = []
    for a, z in ((span[0], zr[0]), (span[1], zr[0]), (span[1], zr[1]), (span[0], zr[1])):
        q = [0.0, 0.0, z]
        q[k], q[j] = val + sg * (PAINT["gap"] + off), a
        corners.append(q)
    lo = [bm.verts.new(q) for q in corners]
    hi = []
    for q in corners:
        q2 = list(q)
        q2[k] += sg * t
        hi.append(bm.verts.new(q2))
    for f in ((0, 1, 2, 3),):
        bm.faces.new([lo[i] for i in f])
        bm.faces.new([hi[i] for i in f[::-1]])
    for i in range(4):
        bm.faces.new((lo[i], lo[(i + 1) % 4], hi[(i + 1) % 4], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return (span[1] - span[0]) * (zr[1] - zr[0])


def _underside_film(bm, o, off=0.0):
    """Films under a board object's downward faces (ceilings), `off` below the coats already on; their area."""
    wb = _world_bm(o)
    area = 0.0
    for f in wb.faces:
        if f.normal.z < -0.99:
            pts = [v.co.copy() for v in f.verts]
            lo = [bm.verts.new((p.x, p.y, p.z - PAINT["gap"] - off)) for p in pts]
            hi = [bm.verts.new((p.x, p.y, p.z - PAINT["gap"] - off - PAINT["film"])) for p in pts]
            bm.faces.new(lo)
            bm.faces.new(hi[::-1])
            for i in range(len(pts)):
                bm.faces.new((lo[i], lo[(i + 1) % len(pts)], hi[(i + 1) % len(pts)], hi[i]))
            area += f.calc_area()
    wb.free()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return area


def _ceiling_objs(inside):
    """The ceiling stage's board objects (and the hatch) inside the house (gypsum) or outside (Smartboard)."""
    return [o for o in bpy.data.collections[C_CEIL].objects
            if (o.name.endswith("_Boards") or o.name.endswith("_Hatch"))
            and (o.data.get("type") in ("CB3", "CB4")) != inside]


def _clip_z(poly, zmax):
    """Polygon (3D points) cut to z ≤ zmax."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        if p.z <= zmax + 1e-9:
            out.append(p)
        if (p.z <= zmax) != (q.z <= zmax):
            t = (zmax - p.z) / (q.z - p.z)
            out.append(p + (q - p) * t)
    return out


def _plaster_area():
    """The plastered wall area of the take-off (ST06): every plaster row's (volume + bead room) / thickness."""
    return sum((x["vol"] + x["void"]) / x["t"] for (el, tn), x in qto(C_WALL).items() if el == "plaster")


def _fascia_film(bm, off=0.0):
    """Films on the fascia faces seen: the outer layer's face and bottom, the 8" face below it and its bottom."""
    area = 0.0
    E, sides, D, ze = _geom()
    for k, s in enumerate(sides):
        out = -s["w"]
        b8, bird = bpy.data.objects[f"FA_B8_{k + 1}"], bpy.data.objects[f"FA_BIRD_{k + 1}"]
        z_bird = min(v.z for v in _verts(bird))
        for o, zmax in ((bird, 1e9), (b8, z_bird)):
            wb = _world_bm(o)
            for f in wb.faces:
                if f.normal.dot(out) > 0.99 or f.normal.z < -0.99:
                    poly = _clip_z([v.co.copy() for v in f.verts], zmax) if f.normal.z > -0.99 else [v.co.copy() for v in f.verts]
                    if len(poly) < 3:
                        continue
                    nrm = f.normal.copy()
                    lo = [bm.verts.new(p + nrm * (PAINT["gap"] + off)) for p in poly]
                    hi = [bm.verts.new(p + nrm * (PAINT["gap"] + off + PAINT["film"])) for p in poly]
                    bm.faces.new(lo)
                    bm.faces.new(hi[::-1])
                    for i in range(len(poly)):
                        bm.faces.new((lo[i], lo[(i + 1) % len(poly)], hi[(i + 1) % len(poly)], hi[i]))
                    area += sum(((poly[i] - poly[0]).cross(poly[i + 1] - poly[0])).length / 2 for i in range(1, len(poly) - 1))
            wb.free()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return area


def build_primer():
    """Primer films on the walls (inside, outside), the ceilings and the fascia, each carrying its area."""
    c = _clear(C_PAINT)
    prim = mat("M_Primer_White", (0.94, 0.94, 0.93), 0.9)
    res = {}
    for side in ("in", "out"):   # the films on the faces seen (picture; seen area kept for reference)
        bm, area = bmesh.new(), 0.0
        for poly, n, where, room in _faces():
            if where == side:
                area += _poly_film(bm, poly, n)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        _obj(c, f"PR_Walls_{side}", bm, prim, seen=area)
        res[side] = round(area, 2)
    pl = _plaster_area()
    q = _obj(c, "PR_Walls_Qty", bmesh.new(), prim, element="paint", type="PR1", th=PAINT["wall"] + " · ผนังฉาบเรียบรวมทุกชั้น",
             area=pl)
    q.hide_viewport = q.hide_render = True
    res["plaster"] = round(pl, 2)
    for tag, inside, typ, th, rate in (("PR_Ceilings", True, "PR3", PAINT["ceil"], PAINT["per_bucket"]),
                                      ("PR_CeilingsOut", False, "PR5", PAINT["ceil_out"], None)):
        bm, area = bmesh.new(), 0.0   # the user: inside ceilings Easy Ceiling, outside ones an exterior primer
        for o in _ceiling_objs(inside):
            area += _underside_film(bm, o)
        props = dict(element="paint", type=typ, th=th, area=area)
        if rate:
            props["per_bucket"] = rate
        _obj(c, tag, bm, prim, **props)
        res[tag] = round(area, 2)
    bm = bmesh.new()
    area = _fascia_film(bm)
    _obj(c, "PR_Fascia", bm, prim, element="paint", type="PR4", th=PAINT["fascia"], area=area)
    res["fascia"] = round(area, 2)
    return res


def selfcheck_primer():
    """Primer against the user's spec, read from the model: inside films only between each room's floor and its
    ceiling, outside films only below the soffit, every film on a plaster face, the ceiling film = the boards'
    undersides, the bucket count from the user's rate."""
    rooms = _rooms()
    zs = _soffit_z()
    films = {o.name: o for o in bpy.data.collections[C_PAINT].objects}
    for vs, _ in _islands(films["PR_Walls_in"]):
        cx, cy = sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs)
        near = [r for r, (rc, f0, f1) in rooms.items()   # a reveal's inner half lies in the wall's depth
                if rc[0] - 0.20 <= cx <= rc[2] + 0.20 and rc[1] - 0.20 <= cy <= rc[3] + 0.20]
        assert near, f"an inside film outside every room at {cx:.2f}, {cy:.2f}"
        assert any(max(v.z for v in vs) <= rooms[r][2] + 1e-4 and min(v.z for v in vs) >= rooms[r][1] - 1e-4 for r in near), \
            f"primer at {cx:.2f}, {cy:.2f} outside floor → ceiling of {near}"
    for vs, _ in _islands(films["PR_Walls_out"]):
        assert max(v.z for v in vs) <= zs + 1e-4, "outside primer above the soffit"
    plaster = [b for n, b in _solids([C_WALL]).items() if bpy.data.objects[n[0]].data.get("element") == "plaster"]
    for name in ("PR_Walls_in", "PR_Walls_out"):   # each film touches a plaster solid's bounding box face
        for vs, _ in _islands(films[name]):
            c = sum(vs, Vector()) / len(vs)
            assert any(b[0] - 0.002 <= c.x <= b[3] + 0.002 and b[1] - 0.002 <= c.y <= b[4] + 0.002 and b[2] - 1e-3 <= c.z <= b[5] + 1e-3
                       for b in plaster), f"{name}: a film off the plaster at {c.x:.2f}, {c.y:.2f}, {c.z:.2f}"
    ceil = 0.0
    for o in bpy.data.collections[C_CEIL].objects:   # hold each bmesh while reading it (a dropped one crashed Blender)
        if o.name.endswith(("_Boards", "_Hatch")):
            wb = _world_bm(o)
            ceil += sum(f.calc_area() for f in wb.faces if f.normal.z < -0.99)
            wb.free()
    got = films["PR_Ceilings"].data["area"] + films["PR_CeilingsOut"].data["area"]
    assert abs(got - ceil) < 0.01, "ceiling primer ≠ the boards' undersides"
    assert all(o.data["type"] in ("CB3", "CB4") for o in _ceiling_objs(False)) and \
        not any(o.data.get("type") in ("CB3", "CB4") for o in _ceiling_objs(True)), "inside/outside ceilings mixed"
    cb = [o for o in bpy.data.collections[C_CEIL].objects if str(o.data.get("type", "")).startswith("CB")]
    lid = 0.0
    if f"CL_{HATCH_ROOM}_Hatch" in bpy.data.objects:   # the hatch lid + frame seen from below, measured
        hv = _verts(bpy.data.objects[f"CL_{HATCH_ROOM}_Hatch"])
        lid = (max(v.x for v in hv) - min(v.x for v in hv)) * (max(v.y for v in hv) - min(v.y for v in hv))
    expected = sum(o.data["area"] for o in cb) - bpy.data.objects["CL_Soffit_Boards"].data["slots"] + lid
    assert abs(got - expected) < 0.01, f"ceiling primer {got:.2f} m², the ceiling stage's boards {expected:.2f}"
    assert abs(films["PR_Ceilings"].data["per_bucket"] - 87.5) < 1e-9, "ceiling rate is the user's 87.5 m² a bucket"
    pl = sum((x["vol"] + x["void"]) / x["t"] for (el, tn), x in qto(C_WALL).items() if el == "plaster")
    assert abs(films["PR_Walls_Qty"].data["area"] - pl) < 1e-6, "wall primer ≠ the plastered wall area (the user)"
    seen = films["PR_Walls_in"].data["seen"] + films["PR_Walls_out"].data["seen"]
    # hidden: inside above the ceilings (~12.5 m² on E42), outside above the soffit (~9.5), below the floor (~1.8);
    # tiled (ST11, no paint): the bath walls floor → ceiling (openings not taken off: rough) and the kitchen splash
    (bx, f0, f1) = _rooms()["Bath"]
    tiled = 2 * (bx[2] - bx[0] + bx[3] - bx[1]) * (f1 - f0) + sum((b[3] - b[0]) * (b[5] - b[2]) for b in tiled_wall_boxes())
    assert 0 < pl - seen - 0.8 * tiled < 0.15 * pl, f"primer seen {seen:.2f} m² against {pl:.2f} plastered, {tiled:.2f} tiled"
    return (f"primer ok: walls {pl:.2f} m² (plastered; {seen:.2f} seen below the ceilings/soffit) · ceilings inside "
            f"{films['PR_Ceilings'].data['area']:.2f} m², outside {films['PR_CeilingsOut'].data['area']:.2f} m² · "
            f"fascia {films['PR_Fascia'].data['area']:.2f} m²")


# --- ST10 ทาสีจริง รอบที่ 1 (spec 29 ต.ค.): walls inside and out JOTUN Jotashield Antifade Colours กึ่งเงา (usable
# inside and out: concrete, fibre-cement, gypsum) — 28 m² / gal a coat, 2 coats, 2.5 gal a bucket; inside ceilings
# Essence Easy Ceiling 2 coats (area ÷ 87.5); outside ceilings (soffit + porch) and the fascia: Jotashield white (the
# ceilings' colour). Buckets: painted area ÷ (m² / gal × gal ÷ 2 coats) — the user's formula (TOA example ÷ 43.75).
# The walls get their first coat now (the second after the electrics), the ceilings both; the take-off counts the
# full 2-coat system here.
C_FINISH = "E42 ST10 Paint Coat 1"
# inside walls (spec 29 ต.ค.): JOTUN Essence Cover Plus 9 L — Jotun's TDS has Jotashield Antifade for exterior only;
# ไทวัสดุ: about 10 m² / L a coat, 2 coats → 9 × 10 / 2 = 45 m² a bucket
FINISH = dict(cover=28.0, gal=2.5, coats=2, cover_in=10.0, litres_in=9.0,
              wall_out="สีน้ำกึ่งเงา JOTUN Jotashield Antifade Colours 2.5 แกลลอน · ผนังภายนอก (รหัสสียังไม่ระบุ)",
              wall_in="สีน้ำภายในกึ่งเงา JOTUN Essence Cover Plus 9 ลิตร · ผนังภายใน (รหัสสียังไม่ระบุ)",
              ceil_in="สีทาฝ้า JOTUN Essence Easy Ceiling 18 ลิตร สีขาวหมอก · ฝ้าภายใน 2 รอบ",
              ceil_out="สีน้ำกึ่งเงา JOTUN Jotashield Antifade Colours 2.5 แกลลอน สีขาว · ฝ้าภายนอก + ไม้เชิงชาย")
FINISH["per_bucket"] = FINISH["cover"] * FINISH["gal"] / FINISH["coats"]   # 35 m² a bucket
FINISH["per_bucket_in"] = FINISH["cover_in"] * FINISH["litres_in"] / FINISH["coats"]   # 45 m² a bucket


def build_finish(sign=1.0):
    """Coat 1 films, one film out over the primer: walls (first coat), ceilings and fascia; take-off rows."""
    c = _clear(C_FINISH)
    wall = mat("M_Paint_Wall", (0.90, 0.88, 0.84), 0.45)   # colour code not given yet
    white = mat("M_Paint_White", (0.95, 0.95, 0.95), 0.45)
    off = sign * (PAINT["film"] + PAINT["gap"])   # sign = -1 only in the tests (a coat one step into the wall)
    res = {}
    for side, typ in (("out", "PF1"), ("in", "PF2")):
        bm, area = bmesh.new(), 0.0
        for poly, n, where, room in _faces():
            if where == side:
                area += _poly_film(bm, poly, n, off)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        _obj(c, f"PF_Walls_{side}", bm, wall, element="paint", type=typ, th=FINISH[f"wall_{side}"], area=area,
             per_bucket=FINISH["per_bucket_in" if side == "in" else "per_bucket"])
        res[side] = round(area, 2)
    bm, area = bmesh.new(), 0.0
    for o in _ceiling_objs(True):
        area += _underside_film(bm, o, off)
    _obj(c, "PF_Ceilings", bm, white, element="paint", type="PF3", th=FINISH["ceil_in"], area=area,
         per_bucket=PAINT["per_bucket"])
    res["ceil_in"] = round(area, 2)
    bm, area = bmesh.new(), 0.0
    for o in _ceiling_objs(False):
        area += _underside_film(bm, o, off)
    area += _fascia_film(bm, off)
    _obj(c, "PF_CeilingsOut_Fascia", bm, white, element="paint", type="PF4", th=FINISH["ceil_out"], area=area,
         per_bucket=FINISH["per_bucket"])
    res["ceil_out_fascia"] = round(area, 2)
    return res


def _check_untiled(o):
    """Nothing painted where ST11 tiles: the bath, the kitchen splash."""
    bx = _rooms()["Bath"][0]
    for vs, _ in _islands(o):
        cc = sum(vs, Vector()) / len(vs)
        assert not (bx[0] - 1e-3 < cc.x < bx[2] + 1e-3 and bx[1] - 1e-3 < cc.y < bx[3] + 1e-3), f"{o.name}: paint in the bath at {cc.x:.2f}, {cc.y:.2f}"
        assert not any(b[0] + 1e-4 < cc.x < b[3] - 1e-4 and b[1] - 0.005 < cc.y < b[4] and b[2] + 1e-4 < cc.z < b[5] - 1e-4
                       for b in tiled_wall_boxes()), f"{o.name}: paint on the kitchen splash at {cc.x:.2f}, {cc.z:.2f}"   # films sit off the plaster


def _plaster_trees():
    return _solid_trees([o for o in bpy.data.collections[C_WALL].objects if o.type == "MESH" and o.data.get("element") == "plaster"])


def _check_steps(front, back, plaster, k=1):
    """Each film of `front` stands exactly k films + gaps off a film of `back` (k coats under it), and a rectangular
    one is not inside the plaster; → [(its centre, that back film's centre, its index)]."""
    from mathutils.kdtree import KDTree
    prim = [sum(vs, Vector()) / len(vs) for vs, _ in _islands(back)]
    kd = KDTree(len(prim))
    for i, p in enumerate(prim):
        kd.insert(p, i)
    kd.balance()
    step = PAINT["film"] + PAINT["gap"]
    out = []
    for vs, _ar in _islands(front):
        cc = sum(vs, Vector()) / len(vs)
        near = [i_ for q, i_, d_ in kd.find_range(cc, (k + 1) * step) if abs(d_ - k * step) < 1e-4]
        assert near, f"{front.name}: no {back.name} film {k} coat(s) behind the film at {cc.x:.2f}, {cc.y:.2f}, {cc.z:.2f}"
        if len(vs) == 8:   # a rectangular film (most of them): its centre lies on it (a concave one may not)
            assert not _in_solid(cc, plaster), f"{front.name}: a coat inside the plaster at {cc.x:.2f}, {cc.y:.2f}, {cc.z:.2f}"
        out.append((cc, prim[near[0]], near[0]))
    return out


def selfcheck_finish():
    """Coat 1 against the user's spec, read from the model: each finish area = the primer stage's matching area (the
    same faces, painted again), every film standing out over its primer film, the bucket rates from the product
    sheet (28 m² / gal, 2.5 gal, 2 coats → 35 m²) and the ceiling rule (87.5 m²)."""
    pr = {o.name: o for o in bpy.data.collections[C_PAINT].objects}
    fi = {o.name: o for o in bpy.data.collections[C_FINISH].objects}
    for side in ("in", "out"):
        assert abs(fi[f"PF_Walls_{side}"].data["area"] - pr[f"PR_Walls_{side}"].data["seen"]) < 1e-6, f"walls {side} ≠ the primed faces"
    assert abs(fi["PF_Ceilings"].data["area"] - pr["PR_Ceilings"].data["area"]) < 1e-6, "inside ceilings ≠ primed"
    out_ = pr["PR_CeilingsOut"].data["area"] + pr["PR_Fascia"].data["area"]
    assert abs(fi["PF_CeilingsOut_Fascia"].data["area"] - out_) < 1e-6, "outside ceilings + fascia ≠ primed"
    assert abs(FINISH["per_bucket"] - 35.0) < 1e-9 and fi["PF_Walls_out"].data["per_bucket"] == FINISH["per_bucket"], "Jotashield rate"
    assert abs(fi["PF_Ceilings"].data["per_bucket"] - 87.5) < 1e-9, "Easy Ceiling rate"
    assert abs(fi["PF_Walls_in"].data["per_bucket"] - 45.0) < 1e-9, "Essence Cover Plus rate"
    _check_untiled(fi["PF_Walls_in"])
    plaster = _plaster_trees()
    for a, b in (("PF_Walls_in", "PR_Walls_in"), ("PF_Walls_out", "PR_Walls_out"), ("PF_Ceilings", "PR_Ceilings")):
        for cc, back, _i in _check_steps(fi[a], pr[b], plaster):   # each coat film stands one film off its own primer film
            if a == "PF_Ceilings":
                assert cc.z < back.z, "ceiling coat not under its primer"
    names_out = {o.name for o in _ceiling_objs(False)}   # the split, by name against the ceiling stage
    assert names_out == {"CL_Soffit_Boards", "CL_Porch_Boards"}, f"outside ceilings: {names_out}"
    names_in = {o.name for o in _ceiling_objs(True)}
    assert names_in == {f"CL_{r}_Boards" for r in ROOMS} | {f"CL_{HATCH_ROOM}_Hatch"}, f"inside ceilings: {names_in}"
    so, po = (bpy.data.objects[n].data for n in ("CL_Soffit_Boards", "CL_Porch_Boards"))
    assert abs(pr["PR_CeilingsOut"].data["area"] - (so["area"] - so["slots"] + po["area"])) < 0.01, "outside ceiling area"
    rows = {o.data["type"]: o.data for o in fi.values()}
    return " · ".join(f"{t} {d['area']:.2f} m² → {math.ceil(d['area'] / d['per_bucket'] - 1e-9)} ถัง" for t, d in sorted(rows.items()))


# --- ST13 ทาสีจริง รอบที่ 2 (spec 31 ต.ค.): the walls' second coat, after the electrics; the same faces as coat 1
# (none where ST11 tiles), one film out over it. No take-off: coat 1's rows already count both coats (no `element`
# on these objects, so qto skips them). Colours not given yet: assumed defaults, off-white inside, light grey outside.
C_COAT2 = "E42 ST13 Paint Coat 2"
COAT2 = dict(in_=(0.93, 0.92, 0.88), out=(0.78, 0.79, 0.80))   # (assumed, until the user gives the colour codes)


def build_coat2(sign=1.0):
    """Coat 2 films on the walls, inside and out, one film out over coat 1; → their areas."""
    c = _clear(C_COAT2)
    off = sign * 2 * (PAINT["film"] + PAINT["gap"])   # sign = -1 only in the tests
    res = {}
    for side in ("out", "in"):
        m = mat(f"M_Paint2_{side.capitalize()}", COAT2["in_" if side == "in" else side], 0.45)
        bm, area = bmesh.new(), 0.0
        for poly, n, where, room in _faces():
            if where == side:
                area += _poly_film(bm, poly, n, off)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        _obj(c, f"PC2_Walls_{side}", bm, m, coat=2, area=area, colour="assumed")
        res[side] = round(area, 2)
    return res


def selfcheck_coat2():
    """Coat 2 from the model: the same wall area as coat 1, every film one film off a coat-1 film (outside the
    plaster), none on tiled faces, and no take-off row (coat 1 counts both coats)."""
    pr = {o.name: o for o in bpy.data.collections[C_PAINT].objects}
    fi = {o.name: o for o in bpy.data.collections[C_FINISH].objects}
    c2 = {o.name: o for o in bpy.data.collections[C_COAT2].objects}
    assert set(c2) == {"PC2_Walls_in", "PC2_Walls_out"}, f"coat 2 objects: {sorted(c2)}"
    assert not any(o.data.get("element") for o in c2.values()), "coat 2 would add a take-off row"
    _check_untiled(c2["PC2_Walls_in"])
    plaster = _plaster_trees()
    for side in ("in", "out"):
        a, b = c2[f"PC2_Walls_{side}"], fi[f"PF_Walls_{side}"]
        assert abs(a.data["area"] - b.data["area"]) < 1e-4, f"coat 2 {side} ≠ coat 1"   # (1 cm²: a coat rebuilt in another session sums its faces ~3 mm² apart)
        hit = {i for _cc, _b, i in _check_steps(a, b, plaster)}   # one coat-2 film on each coat-1 film, none twice
        assert len(hit) == len(_islands(a)) == len(_islands(b)), f"coat 2 {side}: films not one on each coat-1 film"
        _check_steps(a, pr[f"PR_Walls_{side}"], plaster, k=2)   # and in front of coat 1, not under it (on the primer)
    return f"coat 2 ok: walls in {c2['PC2_Walls_in'].data['area']:.2f} m² · out {c2['PC2_Walls_out'].data['area']:.2f} m² (no new quantity; colours assumed)"
