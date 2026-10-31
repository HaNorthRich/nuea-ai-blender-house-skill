# ST12 conduit (spec ../ST12_conduit_spec.md): the user's rules read back from the built model (EL_Conduit_*, EL_box24,
# EL_Flex, EL_Chase) — run after build_elec(); exec after e42_conduit_route.py (e42_load.py keeps the order).
from mathutils import Vector, kdtree


def _conduit_runs():
    """[(circuit, to, points, radius)] of every rigid conduit piece in the model."""
    out = []
    for o in bpy.data.collections[C_ELEC].objects:
        if o.type == "CURVE" and o.name.startswith("EL_Conduit_"):
            for cid, to, sp in zip(o.data["circ"], o.data["to"], o.data.splines):
                out.append((cid, to, [o.matrix_world @ Vector(p.co[:3]) for p in sp.points], o.data.bevel_depth))
    return out


def _check_clear(runs):
    """No two conduit pieces closer than their radii, away from the box / CU knockout both enter (3 cm)."""
    samp = []
    for si, (_, _, P, r) in enumerate(runs):
        for a, b in zip(P, P[1:]):
            n = max(1, int((b - a).length / 0.004))
            samp += [(a.lerp(b, i / n), si) for i in range(n)]
    kd = kdtree.KDTree(len(samp))
    for i, (p, _) in enumerate(samp):
        kd.insert(p, i)
    kd.balance()
    rmax = max(r for *_, r in runs)
    for p, si in samp:
        for q, j, d in kd.find_range(p, 2 * rmax):
            sj = samp[j][1]
            if sj == si or d >= runs[si][3] + runs[sj][3] - 1e-4:
                continue
            if any((p - e).length < 0.03 for e in (runs[si][2][0], runs[si][2][-1], runs[sj][2][0], runs[sj][2][-1])):
                continue
            raise AssertionError(f"conduits clash: {runs[si][0]} → {runs[si][1]} × {runs[sj][0]} → {runs[sj][1]} at "
                                 f"{p.x:.3f}, {p.y:.3f}, {p.z:.3f} ({d * 1000:.1f} mm apart)")


def _check_bends(runs):
    """spec 30 ต.ค.: rigid PVC is bent, never mitred — every turn is an arc of radius ≥ rmin (the circle through each
    sampled point and its neighbours; skipped where two opposite bends meet, both checked on their own points), and
    between two boxes (or box ↔ CU) the bends total ≤ 360°."""
    for cid, to, P, r in runs:
        size = next(k for k, v in EL["conduit"].items() if abs(v / 2 - r) < 1e-6)
        P = [p for k, p in enumerate(P) if not k or (p - P[k - 1]).length > 1e-6]
        nrm = [(P[i] - P[i - 1]).cross(P[i + 1] - P[i]) if 0 < i < len(P) - 1 else Vector() for i in range(len(P))]
        total = 0.0
        for i in range(1, len(P) - 1):
            a, b, c = P[i - 1], P[i], P[i + 1]
            ang = (b - a).angle(c - b)
            total += ang
            short, long_ = sorted(((b - a).length, (c - b).length))
            kink = ang > math.radians(1.0) and short > 0.03   # (an arc: points ≤ 2.3 cm apart)
            # where an arc meets a straight, a tangent join turns half the last chord's arc (≤ chord / 2·rmin): more is a kink
            kink = kink or (long_ > 0.03 and ang > short / (2 * CD["rmin"][size]) * 1.25 + math.radians(0.25))
            arc = i - 1 if (b - a).length <= (c - b).length else i + 1   # the arc's side: a join turns its way, never back
            kink = kink or (long_ > 0.03 and ang > math.radians(1.0) and nrm[arc].length > 1e-12 and nrm[i].dot(nrm[arc]) < 0)
            assert ang <= math.radians(15.0) and not kink, \
                f"{cid} → {to}: a mitred corner ({math.degrees(ang):.0f}° at one point) at {b.x:.3f}, {b.y:.3f}, {b.z:.3f}"   # (arcs are sampled ≤ 1.5 cm: ~8° a point)
            if ang < math.radians(1.0) or any(nrm[i].dot(nrm[j]) < 0 for j in (i - 1, i + 1) if nrm[j].length > 1e-12):
                continue
            rad = (b - a).length * (c - b).length * (c - a).length / (2 * (b - a).cross(c - a).length)
            assert rad >= CD["rmin"][size] * 0.98, \
                f"{cid} → {to}: a bend of r {rad * 1000:.0f} mm at {b.x:.3f}, {b.y:.3f}, {b.z:.3f} (< {CD['rmin'][size] * 1000:.0f})"
        assert math.degrees(total) <= 360.5, f"{cid} → {to}: {math.degrees(total):.0f}° of bends between boxes"


def _check_boxes(runs):
    """A conduit inside a box — a TOP box (pull / downlight) or a wall device's flush 2×4 (read from the model) — ends
    there: nothing passes through a box it does not enter. → the box count."""
    boxes = []
    for name in ("EL_box24", "EL_box44", "EL_sw", "EL_so", "EL_heater", "EL_ac"):
        for vs, _ in _islands(bpy.data.objects[name]):
            lo = Vector([min(v[k] for v in vs) for k in range(3)])
            hi = Vector([max(v[k] for v in vs) for k in range(3)])
            if (name.startswith("EL_box") and min(hi - lo) > 0.03) or abs(hi.z - lo.z - EL["box"][1]) < 1e-4:   # (not a knockout
                boxes.append((lo, hi))                                                                         # disc / a plate / a unit)
    for cid, to, P, r in runs:
        for a, b in zip(P, P[1:]):
            n = max(1, int((b - a).length / 0.005))
            for i in range(n + 1):
                m = a.lerp(b, i / n)
                for lo, hi in boxes:
                    if all(lo[k] + 0.002 < m[k] < hi[k] - 0.002 for k in range(3)):
                        inside_end = any(all(lo[k] - 0.01 <= e[k] <= hi[k] + 0.01 for k in range(3)) for e in (P[0], P[-1]))
                        assert inside_end, f"{cid} → {to} passes through a box at {(lo.x + hi.x) / 2:.2f}, {(lo.y + hi.y) / 2:.2f}, {(lo.z + hi.z) / 2:.2f}"
    return len(boxes)


def _bvh(colls, keep=lambda o: True):
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    for cn in colls:
        for o in bpy.data.collections[cn].objects:
            if o.type == "MESH" and keep(o):
                m = o.data.copy()
                m.transform(o.matrix_world)
                bm.from_mesh(m)
                bpy.data.meshes.remove(m)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def _samples(P, step):
    out = []
    for a, b in zip(P, P[1:]):
        n = max(1, int((b - a).length / step))
        out += [a.lerp(b, i / n) for i in range(n)]
    return out + [P[-1]]


def _check_lids(runs):
    """spec 30 ต.ค.: every TOP box fixed to the wall (or plate / column) with its back, lid to the room, and no conduit
    or flex in front of the lid (its face out to 0.30 m)."""
    walls = _bvh([C_WALL, C_COL])
    flex = bpy.data.objects["EL_Flex"].data
    fw = bpy.data.objects["EL_Flex"].matrix_world
    every = [(P, r) for *_, P, r in runs] + [([fw @ Vector(p.co[:3]) for p in sp.points], EL["flex"]["od"] / 2) for sp in flex.splines]
    samp = [(m, r) for P, r in every for m in _samples(P, 0.005)]
    for name in ("EL_box24", "EL_box44"):
        for vs, _ in _islands(bpy.data.objects[name]):
            lo = Vector([min(v[k] for v in vs) for k in range(3)])
            hi = Vector([max(v[k] for v in vs) for k in range(3)])
            if min(hi - lo) < 0.03:
                continue   # a knockout disc
            k = 0 if hi.x - lo.x < hi.y - lo.y else 1   # its depth across the wall
            mid = (lo + hi) / 2
            gap = {}
            for sg, f in ((-1, lo[k]), (1, hi[k])):
                c = mid.copy()
                c[k] = f
                hit = walls.find_nearest(c, 0.05)
                gap[sg] = hit[3] if hit[0] is not None else 9.0
            back = min(gap, key=gap.get)
            assert gap[back] < 0.003, f"{name} at {mid.x:.2f}, {mid.y:.2f}, {mid.z:.2f}: not fixed to the wall ({gap[back] * 1000:.0f} mm off)"
            f0 = hi[k] if back < 0 else lo[k]   # the lid face, out into the room
            a, b = (f0, f0 + 0.30) if back < 0 else (f0 - 0.30, f0)
            for m, r in samp:   # (any part of the conduit over the lid's outline)
                if a < m[k] < b and all(lo[j] - r < m[j] < hi[j] + r for j in range(3) if j != k):
                    raise AssertionError(f"a conduit in front of the lid of {name} at {mid.x:.2f}, {mid.y:.2f}, {mid.z:.2f}")


def _check_walls(runs):
    """spec 30 ต.ค.: into a wall only through brick and its plaster — a hole straight through, square, below the steel
    wall plate, or a chase down (up) to the box / CU the piece ends in; nothing touches a concrete tie, a column (or its
    coat) or the steel plate. → (holes, groove lengths: a wall device's loop one, a link one, each CU home run one,
    the ground one)."""
    soft, hard = [], []
    for (n, _), b in _solids([C_WALL, C_COL]).items():
        e = bpy.data.objects[n].data.get("element")
        (soft if e in ("masonry", "bead") or (e == "plaster" and not n.startswith("CP_")) else hard).append((n, b))
    pts = _points()
    def dev_at(e):   # the wall device / CU whose box e is in
        for pid, p in pts.items():
            if p["kind"] in ("sw", "so", "heater", "ac", "cu"):
                hw = (EL["cu"]["size"] if p["kind"] == "cu" else EL["box"])[0] / 2 + 0.02
                if (e.xy - p["p"].xy).length < hw and abs(e.z - p["p"].z) < 0.40:
                    return pid
        return None
    near = lambda m, b, d: all(b[j] - d < m[j] < b[3 + j] + d for j in range(3))
    holes, grooves = 0, {}
    for cid, to, P, r in runs:
        lo = Vector([min(p[k] for p in P) - r for k in range(3)])
        hi = Vector([max(p[k] for p in P) + r for k in range(3)])
        box_near = lambda bs: [x for x in bs if all(x[1][j] < hi[j] and x[1][3 + j] > lo[j] for j in range(3))]
        sb, hb = box_near(soft), box_near(hard)
        S = _samples(P, 0.002)
        mine = [q for q in CD["tie_chase"] if q in (dev_at(P[0]), dev_at(P[-1]))]   # the user (ก): only its own chase
        for m in S[::3]:
            for n, b in hb:
                ok = n.endswith("_Ties") and any((m.xy - pts[q]["p"].xy).length < 0.10 and
                                                 pts[q]["p"].z - EL["box"][1] / 2 - 0.01 < m.z < CD["top"] for q in mine)
                gap_ = Vector([max(b[j] - m[j], 0.0, m[j] - b[3 + j]) for j in range(3)]).length   # (true distance: a box corner too)
                assert ok or gap_ >= r * 0.99, f"{cid} → {to}: touches {n} at {m.x:.3f}, {m.y:.3f}, {m.z:.3f}"
        inw = [any(near(m, b, 1e-5) for _, b in sb + hb) for m in S]   # (touching faces: no gap between two)
        i = 0
        while i < len(S):
            if not inw[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(S) and inw[j + 1]:
                j += 1
            st = S[i:j + 1]
            L = sum((q - p).length for p, q in zip(st, st[1:]))
            at0, at1 = i == 0, j == len(S) - 1
            if at0 and at1:   # box to box in the wall
                grooves[("link", cid, to)] = (0.0, L, 0.0)
            elif at0 or at1:
                side = sum((q - p).xy.length for p, q in zip(st, st[1:]))
                assert side <= 0.30, f"{cid} → {to}: {side:.2f} m sideways in the wall at {st[0].x:.2f}, {st[0].y:.2f} (a chase goes up/down)"
                pid = dev_at(P[0] if at0 else P[-1])
                assert pid, f"{cid} → {to}: into the wall at {st[0].x:.2f}, {st[0].y:.2f} towards no box"
                key = ("own", cid, to, at0) if pts[pid]["kind"] == "cu" else ("box", pid)
                z0, z1, lv = grooves.get(key, (9.0, -9.0, 0.0))   # its rise, + any level run in the wall (D3 set-out)
                lv += sum((q - p).xy.length for p, q in zip(st, st[1:]) if abs(q.z - p.z) < CD["level_dz"])   # (a bend's last 2 mm still rises ~2e-5)
                grooves[key] = (min(z0, min(m.z for m in st)), max(z1, max(m.z for m in st)), lv)
            else:   # a hole
                assert max(m.z for m in st) - min(m.z for m in st) < 1e-6, f"{cid} → {to}: a hole not level at {st[0].x:.2f}, {st[0].y:.2f}"
                assert L > WALL["t"] + 2 * WALL["pl"] - 0.005, f"{cid} → {to}: a stretch {L * 1000:.0f} mm into a wall at {st[0].x:.2f}, {st[0].y:.2f} (neither hole nor chase)"   # (a hole: through it all)
                d_ = (st[-1] - st[0]).normalized()
                assert max(abs(d_.x), abs(d_.y)) >= 0.999 and L <= WALL["t"] + 2 * WALL["pl"] + 0.01, \
                    f"{cid} → {to}: a hole not square through the wall at {st[0].x:.2f}, {st[0].y:.2f}"
                holes += 1
            i = j + 1
    return holes, sorted(z1 - z0 + lv for z0, z1, lv in grooves.values())


def _check_steel(runs, flex=()):
    """No conduit through the roof steel or the ceiling (frame, boards, wall angle, hanger rods): every point at least
    its radius off their surfaces. A flex too, but for its last drop through the board's cut-out into its light (within
    the cut-out's circle in plan, below 4 cm over the fitting's top)."""
    tree = _bvh([C_ROOF, C_CEIL])
    frame = _bvh([C_ROOF, C_CEIL], lambda o: not o.name.endswith("_Boards"))   # (MAIN's riser goes up through the soffit board)
    drop = lambda m, P, r: (m.xy - P[-1].xy).length <= EL["dl"]["cut"] / 2 + r and m.z <= P[-1].z + 0.04
    holes_ = _main_soffit_holes(_points())
    for cid, to, P, r in list(runs) + [(c, t, [m for m in _samples(P, 0.005) if not drop(m, P, r)], r) for c, t, P, r in flex]:
        for m in (_samples(P, 0.005) if len(P) > 1 else P):
            at_hole = cid == "MAIN" and any(math.hypot(m.x - hx, m.y - hy) < r + 0.02 for hx, hy in holes_)
            hit = (frame if at_hole else tree).find_nearest(m, r * 0.99)   # (MAIN passes the soffit board only at its 2 holes)
            assert hit[0] is None, f"{cid} → {to}: through the roof steel / ceiling at {m.x:.3f}, {m.y:.3f}, {m.z:.3f}"


def _check_wire(runs):
    """Wire read back from the model: what lies beyond each piece — the pieces of its conduit (same id) leaving the box
    it ends in, the wall devices whose box a piece ends in, the downlights a flex from a TOP box reaches — gives its
    conductors (_conductors); a drop from a junction box onto a wall device carries them loop-through (down with what
    the other pieces from that box feed, and back up); × (length + slack each end), + flex, + the ground = EL_Wire_*.
    Every point reached once."""
    pts = _points()
    byid = {C["id"]: C for C in CIRCUITS}
    boxes = []
    for name in ("EL_box24", "EL_box44", "EL_sw", "EL_so", "EL_heater", "EL_ac", "EL_cu"):
        for vs, _ in _islands(bpy.data.objects[name]):
            lo = Vector([min(v[k] for v in vs) for k in range(3)])
            hi = Vector([max(v[k] for v in vs) for k in range(3)])
            if (name.startswith("EL_box") and min(hi - lo) > 0.03) or name == "EL_cu" or abs(hi.z - lo.z - EL["box"][1]) < 1e-4:
                boxes.append((lo, hi, name))
    def box_of(e):
        got = [k for k, (lo, hi, n) in enumerate(boxes) if all(lo[j] - 0.03 <= e[j] <= hi[j] + 0.03 for j in range(3))]
        assert len(got) == 1, f"a conduit end at {e.x:.3f}, {e.y:.3f}, {e.z:.3f} in {len(got)} boxes"
        lo, hi, n = boxes[got[0]]
        out_ = Vector([max(lo[j] - e[j], 0.0, e[j] - hi[j]) for j in range(3)]).length
        depth = min(min(e[j] - lo[j], hi[j] - e[j]) for j in range(3))
        tol = 0.025 if n == "EL_cu" else 0.002   # (the CU's home runs come up its chase behind it)
        assert (out_ if out_ > 0 else depth) <= tol, f"a conduit end at {e.x:.3f}, {e.y:.3f}, {e.z:.3f} is not on its box ({n})"
        return got[0]
    def dev_in(k):
        lo, hi, n = boxes[k]
        c = (lo + hi) / 2
        return {pid for pid, p in pts.items() if p["kind"] in ("sw", "so", "heater", "ac") and (p["p"].xy - c.xy).length < 0.06
                and lo.z - 0.01 <= p["p"].z <= hi.z + 0.01} if not n.startswith("EL_box") else set()
    flex = bpy.data.objects["EL_Flex"].data
    dl_of = {}   # TOP box → the downlights its flex reaches
    wire = {}
    for sp in flex.splines:
        F = [bpy.data.objects["EL_Flex"].matrix_world @ Vector(p.co[:3]) for p in sp.points]
        pid = next((p for p, v in pts.items() if v["kind"] == "dl" and (v["p"].xy - F[-1].xy).length < 0.01), None)
        assert pid and abs(F[-1].z - pts[pid]["p"].z - EL["dl"]["h"]) < 1e-3, f"a flex ends on no downlight at {F[-1].x:.2f}, {F[-1].y:.2f}"
        assert _path_len(F) <= EL["flex"]["max"] + 1e-6, f"{pid}: flexible conduit {_path_len(F):.2f} m (> {EL['flex']['max']})"
        dl_of.setdefault(box_of(F[0]), set()).add(pid)
        M = next(M for M in CIRCUITS if pid in M["pts"])
        for w, k in [(M["wires"][0][0], 2)] + [w for w in M["wires"] if w[0].startswith("G")]:
            wire[w] = wire.get(w, 0.0) + k * (_path_len(F) + 2 * EL["slack"])
    cu = next(k for k, b in enumerate(boxes) if b[2] == "EL_cu")
    pcs = [(cid, box_of(P[0]), box_of(P[-1]), P) for cid, to, P, r in runs if cid not in ("GND", "MAIN")]
    jbox = {(cid, box_of(P[-1])) for cid, to, P, r in runs if to.startswith("J@")}   # (circuit, box) of every junction box
    def beyond(i, seen):
        cid, _, be, _ = pcs[i]
        assert (cid, be) not in seen, f"{cid}: into the box at {(boxes[be][0].x + boxes[be][1].x) / 2:.2f}, {(boxes[be][0].y + boxes[be][1].y) / 2:.2f} twice"
        seen.add((cid, be))
        out = dev_in(be) | dl_of.get(be, set())
        for j, (c2, bs2, _, _) in enumerate(pcs):
            if c2 == cid and bs2 == be:
                out |= beyond(j, seen)
        return out
    reached = {}
    for i, (cid, bs, be, P) in enumerate(pcs):
        S = beyond(i, set())
        ws = _conductors([byid[c] for c in cid.split("+")], S, pts, cid)
        if dev_in(be) and (cid, bs) in jbox:   # a drop from a junction box (its run in is named J@…): the device's own circuits
            Mp = [byid[c] for c in cid.split("+") if set(byid[c]["pts"]) & S]    # loop through it (the others pass the box)
            own = set().union(*[set(M["pts"]) for M in Mp])
            U = own & set().union(*[beyond(j, set()) for j, (c2, bs2, _, _) in enumerate(pcs) if c2 == cid and bs2 == bs and j != i])
            ws = _conductors(Mp, S | U, pts, cid) + (_conductors(Mp, U, pts, cid) if U else [])   # down with what they feed on, back up
        for w, k in ws:
            wire[w] = wire.get(w, 0.0) + k * (_path_len(P) + 2 * EL["slack"])
        if bs == cu:
            for p in S:
                reached[p] = reached.get(p, 0) + 1
    walked, todo_ = set(), [i for i, p in enumerate(pcs) if p[1] == cu]   # every piece hangs off the CU
    while todo_:
        i = todo_.pop()
        if i not in walked:
            walked.add(i)
            todo_ += [j for j, (c2, bs2, _, _) in enumerate(pcs) if c2 == pcs[i][0] and bs2 == pcs[i][2]]
    for i, (cid, bs, be, P) in enumerate(pcs):
        assert i in walked, f"{cid}: a piece from {P[0].x:.2f}, {P[0].y:.2f}, {P[0].z:.2f} not fed from the CU (its box is not its conduit's)"
    routed = {c for cid, *_ in pcs for c in cid.split("+")}
    for C in CIRCUITS:
        for p in [q for q in C["pts"] if q not in CD["pending"]] if C["id"] in routed else ():   # (not yet: in the summary)
            assert reached.get(p) == 1, f"{C['id']}: {p} reached {reached.get(p, 0)} times from the CU"
    for cid, to, P, r in runs:   # the service (meter → CU): its own conductors over each piece
        if cid == "MAIN":
            for w, k in MAIN["wires"]:
                wire[w] = wire.get(w, 0.0) + k * (_path_len(P) + 2 * EL["slack"])
    gnd = next(P for cid, to, P, r in runs if cid == "GND")
    wire["G10"] = _path_len(gnd) + 2 * EL["slack"]
    for o in bpy.data.collections[C_ELEC].objects:
        if o.name.startswith("EL_Wire_"):
            w = o.name[8:]
            got = wire.pop(w, 0.0)
            assert abs(o.data["length"] - got) < 1e-3, f"wire {w}: {o.data['length']:.2f} m taken off, the model says {got:.2f}"
    assert not wire, f"wire in the model with no EL_Wire_ row: {sorted(wire)}"
    return [C["id"] for C in CIRCUITS if C["id"] not in routed] + sorted(CD["pending"])


def _check_takeoff(runs):
    """The BOQ rows read back: each conduit object's lens = its splines' lengths (pieces, couplings, connectors), no
    elbows (the user: bent on site), clip length vlen = the part over the ceilings; flex lens = its splines, 2 connectors
    a flex; the chase row's length and count = its grooves."""
    zmin = min(v[2] for v in _voids().values()) + 0.01   # (over the lowest ceiling: clipped to the wall)
    O = bpy.data.objects
    for o in bpy.data.collections[C_ELEC].objects:
        if o.type == "CURVE":
            Ps = [[o.matrix_world @ Vector(p.co[:3]) for p in sp.points] for sp in o.data.splines]
            lens = list(o.data["lens"])
            assert len(lens) == len(Ps) and all(abs(l - _path_len(P)) < 1e-3 for l, P in zip(lens, Ps)), \
                f"{o.name}: conduit length taken off {sum(lens):.2f} m in {len(lens)} pieces, the model {sum(map(_path_len, Ps)):.2f} m in {len(Ps)}"
            assert o.data["bends"] == 0, f"{o.name}: {o.data['bends']} elbows taken off (the user: bent on site)"
            if o.name.startswith("EL_Conduit_"):   # (MAIN's piece out of doors: clipped all along)
                v = sum(_path_len(P) if c == "MAIN" and t == "MAIN_box" else sum((q - p).length for p, q in zip(P, P[1:]) if min(p.z, q.z) > zmin)
                        for c, t, P in zip(o.data["circ"], o.data["to"], Ps))
                assert abs(o.data["vlen"] - v) < 1e-3, f"{o.name}: clipped length {o.data['vlen']:.2f} m taken off, the model {v:.2f}"
    assert O["EL_FlexConn"].data["count"] == 2 * len(O["EL_Flex"].data.splines), "EL_FlexConn: not 2 a flex"
    zs, (ex0, ey0, ex1, ey1) = _voids()["Eave"][2], _voids()["Eave"][0]   # MAIN up / down through the eave's soffit board
    n_s = sum(1 for c, t, P, r in runs if c == "MAIN" for p, q in zip(P, P[1:])
              if (p.z - zs) * (q.z - zs) < 0 and ex0 - 0.2 < p.x < ex1 and ey0 - 0.8 < p.y < ey1)
    assert O["EL_SoffitHoles"].data["count"] == n_s, f"EL_SoffitHoles: {O['EL_SoffitHoles'].data['count']} taken off, the model goes through {n_s}"
    ch = O["EL_Chase"].data
    assert abs(ch["length"] - sum(ch["lens"])) < 1e-6, f"EL_Chase: chase length {ch['length']:.2f} ≠ its grooves {sum(ch['lens']):.2f}"
    assert ch["count"] == len(ch["lens"]), f"EL_Chase: chase count {ch['count']} ≠ {len(ch['lens'])} grooves"


def _check_on_walls(runs):
    """spec 30 ต.ค.: conduits are clipped onto the wall (plate, column) face over the ceiling — no run out in the room
    (the farthest the router goes: an offset leg past a proud column, 12 cm). And a circuit never runs back alongside
    itself: no two stretches of one conduit id within 9 cm in plan, opposite ways, for over 0.30 m (away from 0.3 m of the
    box ends), outside the walls (a loop's down and up legs share their chase)."""
    walls = _bvh([C_WALL, C_COL])
    zmin = min(v[2] for v in _voids().values()) + 0.01
    solid = [b for b in _solids([C_WALL, C_COL]).values()]
    inwall = lambda m: any(all(b[j] - 1e-5 < m[j] < b[3 + j] + 1e-5 for j in range(3)) for b in solid)
    by = {}
    for cid, to, P, r in runs:
        S = [m for m in _samples(P, 0.01) if m.z > zmin and not inwall(m)]
        for m in S:
            hit = walls.find_nearest(m, 0.14)
            assert hit[0] is not None, f"{cid} → {to}: a run off the wall at {m.x:.2f}, {m.y:.2f}, {m.z:.2f} (> 14 cm)"
        if cid != "GND":   # by circuit: "L1" and "L1+S1" both carry L1
            for c_ in cid.split("+"):
                by.setdefault(c_, []).append((to, P))
    for cid, ps in by.items():
        pts_ = []   # (point, unit direction, piece, along) — away from 0.3 m of the piece's ends
        for k, (to, P) in enumerate(ps):
            s_ = 0.0
            for a, b in zip(P, P[1:]):
                L = (b - a).length
                n = max(1, int(L / 0.02))
                for i in range(n):
                    m = a.lerp(b, i / n)
                    if 0.3 < s_ + L * i / n < _path_len(P) - 0.3 and m.z > zmin and not inwall(m):
                        pts_.append((m, (b - a).normalized(), k, s_ + L * i / n))
                s_ += L
        if not pts_:
            continue
        kd = kdtree.KDTree(len(pts_))
        for i, (m, *_) in enumerate(pts_):
            kd.insert(Vector((m.x, m.y, 0.0)), i)   # spacing in plan: a return on a level far up the wall still doubles back
        kd.balance()
        hits = {}
        for m, d, k, s_ in pts_:
            for q, j, _ in kd.find_range(Vector((m.x, m.y, 0.0)), 0.09):
                m2, d2, k2, s2 = pts_[j]
                if d.dot(d2) < -0.9 and (k2 != k or abs(s2 - s_) > 0.5):
                    hits.setdefault((k, k2), []).append(s_)
        for (k, k2), ss in hits.items():
            ss.sort()
            run_ = best = 0.0
            for a, b in zip(ss, ss[1:]):
                run_ = run_ + (b - a) if b - a < 0.05 else 0.0
                best = max(best, run_)
            assert best <= 0.30, f"{cid}: runs back alongside itself ({ps[k][0]} / {ps[k2][0]}) for {best:.2f} m"


def _check_cu():
    """spec 30 ต.ค.: a circuit going both ways leaves the CU as two conduits — no box in front of it (0.5 m)."""
    lo, hi = [Vector([f(v[k] for vs, _ in _islands(bpy.data.objects["EL_cu"]) for v in vs) for k in range(3)]) for f in (min, max)]
    cp = _points()["CU"]
    for name in ("EL_box24", "EL_box44"):
        for vs, _ in _islands(bpy.data.objects[name]):
            c = sum(vs, Vector()) / len(vs)
            if (c - cp["p"]).dot(cp["n"]) < 0:   # (behind its wall: MAIN's box outside)
                continue
            d = Vector([max(lo[k] - c[k], 0.0, c[k] - hi[k]) for k in range(3)]).length
            assert d > 0.5, f"{name}: a box {d:.2f} m from the CU (two conduits leave it, no branch box)"


def selfcheck_conduit():
    runs = _conduit_runs()
    fl = bpy.data.objects["EL_Flex"]   # (a flex to a light the other side of a wall goes through it: a hole too)
    flex = [(c, t, [fl.matrix_world @ Vector(p.co[:3]) for p in sp.points], EL["flex"]["od"] / 2)
            for c, t, sp in zip(fl.data["circ"], fl.data["to"], fl.data.splines)]
    _check_clear(runs + flex)   # (flex too: clear of the conduits, away from the box it leaves)
    _check_cu()
    _check_bends(runs)
    nb = _check_boxes(runs)
    _check_lids(runs)
    holes, grooves = _check_walls(runs + flex)   # (a flex through a wall to a light the other side: a hole too)
    o = bpy.data.objects
    assert holes == o["EL_WallHoles"].data["count"], f"{holes} holes through walls, take-off says {o['EL_WallHoles'].data['count']}"
    left = sorted(o["EL_Chase"].data["lens"])   # each groove in the model ↔ one taken off: taken off up to its run's
    for g in grooves:                            # height, the conduit enters the wall a little lower, in its bend
        k = next((i for i, w in enumerate(left) if -0.005 < w - g < 0.025), None)
        assert k is not None, f"a {g:.2f} m chase in the model is not in the take-off {[round(w, 2) for w in left]}"
        left.pop(k)
    assert not left, f"chases in the take-off not in the model: {[round(w, 2) for w in left]}"
    _check_steel(runs, flex)
    _check_on_walls(runs)
    todo = _check_wire(runs)
    _check_takeoff(runs)   # (last: a geometry fault reports its own rule first)
    return (f"conduit ok: {len(runs)} pieces · {nb} boxes · {holes} holes · {len(grooves)} chases {sum(grooves):.1f} m"
            + (f" · not routed yet: {', '.join(todo)}" if todo else ""))
