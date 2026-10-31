# E42 ST12 conduit, part 2 of 3: the routing tables (XS, ROUTES), the entry _routes_wall and its hub loop.
# Spec: ../ST12_conduit_spec.md. After e42_conduit_geom.py; e42_conduit_route.py holds _route_once.
import bisect
import math
import re
from mathutils import Vector


# How a run gets from the living room into another room (the user: through a wall at a room corner; the CU circuits
# go counter-clockwise round the living room and tee off into each room on the way):
# (to, corner, kind, travel in the living room, travel on into the room)
#   offset: straight on through the wall past the corner column, with an offset bend each side (4 × 30°)
#   bend:   off the living room's west wall, out, a 90° bend into the wall, straight on along the room's wall
XS = {("Living", "Bed1", 1): ("E2", "offset", (-1, 0)),   # (from, to, way round the living room): corner, kind, travel
      ("Living", "Bath", 1): ("C2", "bend", (0, -1)),
      ("Living", "Bath", -1): ("C2", "bend", (0, 1)),
      ("Living", "Bed2", -1): ("C2", "bend", (0, 1)),
      ("Bed1", "Bath", 1): ("D1", "offset", (0, -1)),
      ("Bath", "Bed2", 1): ("C1", "straight", (0, -1))}
# spec 30 ต.ค.: the route of every conduit, as a designer lays it (rooms in order with the points each serves). The
# bedroom-1 conduits go counter-clockwise round the living room to E2; most bath / bedroom-2 ones clockwise to C2; a
# circuit with points in several rooms leaves the CU once per room (no branch boxes). "A1+S1": two circuits share one
# conduit where a wall band is too full (spec 30 ต.ค.: bedroom 1 holds two conduits, not three; the bath entry, with
# the heater box just inside it, one; bedroom 2, one; fill ≤ 40 %, see CD["fill"]). The first circuit sets the conduit size.
ROUTES = [
    ("A1+S1+L1-Bed1", "A1+S1+L1", 1, [("Living", []), ("Bed1", ["SO_Bed1_1", "SO_Bed1_2", "AC_Bed1", "SW_Bed1", "DL_Bed1_1", "DL_Bed1_2"])]),
    ("L1+H1-Bath", "L1+H1", 1, [("Living", ["SW_Bath"]), ("Bath", ["DL_Bath", "HT_Bath"])]),
    ("S2+S3+L2-ccw", "S2+S3+L2", 1, [("Living", ["SO_Fridge", "SO_Living_2", "SO_Kitchen_1", "SO_Kitchen_2", "SW_Kitchen",
                                                  "DL_Kitchen_1", "DL_Kitchen_2", "DL_Back"])]),   # (DL_Back: its flex through the east wall)
    ("L1+S1+L2-Bed2", "L1+S1+L2", -1, [("Living", ["DL_Porch_2", "DL_Porch_1", "SW_Porch"]),   # (porch lights: boxes on the
                                       ("Bed2", ["SW_Bed2", "DL_Bed2_1", "DL_Bed2_2", "SO_Bed2_1", "SO_Bed2_2"])]),   # south wall, flex through it)
    ("S2+L2-cw", "S2+L2", -1, [("Living", ["SO_Living_1", "SW_Living", "DL_Living_1", "DL_Living_2"])]),
]
XO = {("Living", "Bed1")}   # crossings taken over the top of the wall plate when the run is up on the plate band
KO = 0.028   # a 4×4's two knockouts per end, either side of its centre: a tee's child leaves 2·KO above its parent


def _side_line(line, d, near):
    """The straight stretch of a room's run line running along d nearest the point near: (its across coordinate,
    [(along, s)] of its points). d is (±1, 0) or (0, ±1)."""
    ax = 0 if d[0] else 1   # along
    best = {}
    for i in range(len(line.pts)):
        a, b = line.pts[i], line.pts[(i + 1) % len(line.pts)]
        if abs(a[1 - ax] - b[1 - ax]) < 1e-7 and abs(a[ax] - b[ax]) > 1e-4:
            best.setdefault(round(a[1 - ax], 6), []).append((a[ax], line.cum[i]))
            best[round(a[1 - ax], 6)].append((b[ax], line.cum[i + 1] % line.L))
    k = min(best, key=lambda c: abs(c - near[1 - ax]))
    return k, best[k]


def _xing(lines, X, Y, way=1):
    """The plan path from room X's run line into room Y's: (s where it leaves X's line, going sg there, the sharp
    polyline [(x, y)] from there to Y's line, s where it joins Y's line, sg on Y's line after)."""
    corner, kind, d = XS[(X, Y, way)]
    G = (GX[corner[1]], GY[corner[0]])
    Lv, Ly = lines[X], lines[Y]
    r, rc, dc, th = CD["rmin"]["3/4"], EL["conduit"]["3/4"] / 2, CD["dc"], math.radians(CD["off_deg"])
    t30 = r * math.tan(th / 2)
    if kind == "offset":   # along the living room's wall, straight on through the wall at the corner, into Y
        ax = 0 if d[0] else 1
        a, pts_v = _side_line(Lv, d, G)
        _, pts_y = _side_line(Ly, d, (G[0], G[1]) if ax else (G[0], a))
        span_v = sorted(u * d[ax] for u, s_ in pts_v)   # the straights (in travel terms)
        span_y = sorted(u * d[ax] for u, s_ in pts_y)
        # the column(s) at the corner: their reach across the run, along the run
        cols = [b for room in (X, Y) for b in _voids()[room][1]
                if b[0] - 0.12 <= G[0] <= b[3] + 0.12 and b[1] - 0.12 <= G[1] <= b[4] + 0.12]   # either side of the crossed wall
        rc_ = _voids()[X][0]
        inward = 1 if (rc_[1 - ax] + rc_[3 - ax]) / 2 > a else -1   # from the wall towards the room interior (across)
        face = lambda b: (b[4] if inward > 0 else b[1]) if ax == 0 else (b[3] if inward > 0 else b[0])   # its face into the room
        o = max(abs(face(b) - a) for b in cols) + rc + CD["clear"]   # out past the column face
        col_u = sorted(v for b in cols for v in ((b[0], b[3]) if ax == 0 else (b[1], b[4])))
        u_in, u_out = (col_u[0], col_u[-1]) if d[ax] > 0 else (col_u[-1], col_u[0])
        run = o / math.tan(th)
        u2 = u_in - d[ax] * (CD["clear"] + t30)
        u1 = u2 - d[ax] * run
        u3 = u_out + d[ax] * (CD["clear"] + t30)
        u4 = u3 + d[ax] * run
        def P(u, off):
            q = [0.0, 0.0]
            q[ax], q[1 - ax] = u, a + inward * off
            return tuple(q)
        u_leave = u1 - d[ax] * (t30 + 0.01)   # off the living room's straight just before the offset starts
        u_join = u4 + d[ax] * (t30 + 0.01)    # onto Y's straight just after it ends
        assert span_v[0] - 1e-6 <= u_leave * d[ax] <= span_v[-1] + 1e-6 and span_y[0] - 1e-6 <= u_join * d[ax] <= span_y[-1] + 1e-6, \
            f"{Y}: the offset past the {corner} column does not start and end on straights"
        poly = [P(u_leave, 0), P(u1, 0), P(u2, o), P(u3, o), P(u4, 0), P(u_join, 0)]
    elif kind == "straight":   # along the wall, straight on through the crossed wall at the corner (no column there)
        ax = 0 if d[0] else 1
        a, pts_v = _side_line(Lv, d, G)
        _, pts_y = _side_line(Ly, d, G if ax else (G[0], a))
        u_leave = max(u * d[ax] for u, s_ in pts_v) * d[ax]
        u_join = min(u * d[ax] for u, s_ in pts_y) * d[ax]
        def P(u):
            q = [0.0, 0.0]
            q[ax], q[1 - ax] = u, a
            return tuple(q)
        poly = [P(u_leave), P(u_join)]
    else:   # bend: down the living room's west wall, out, 90° into the wall, on along Y's wall
        a, pts_v = _side_line(Lv, d, G)          # the west wall's run line: x = a
        yh, pts_y = _side_line(Ly, (-1, 0), G)   # Y's wall along x, nearest the corner: its run line y = yh
        u_join = max(u for u, s_ in pts_y)       # where Y's straight starts, nearest the living room
        o = r - dc + CD["clear"]                 # out far enough that the 90° bend clears the wall face
        cl = rc + 0.005   # the user: holes through brick only — off a concrete tie (C2: the bedroom-2 door jamb's)
        ties = [b for (n_, _), b in _solids([C_WALL]).items() if bpy.data.objects[n_].data.get("element") == "concrete"
                and b[0] < max(a, u_join) and b[3] > min(a, u_join) and b[1] - cl < yh < b[4] + cl]
        y3 = yh if not ties else (min(b[1] for b in ties) - cl if d[1] > 0 else max(b[4] for b in ties) + cl)
        y2 = y3 - d[1] * (r + t30)
        y1 = y2 - d[1] * o / math.tan(th)
        y0 = y1 - d[1] * (t30 + 0.01)
        poly = [(a, y0), (a, y1), (a + o, y2), (a + o, y3)]
        if not ties:
            poly.append((u_join, y3))
        else:   # through the brick beside the tie, then 2 × 30° over onto Y's wall line
            w = 1 if u_join > a else -1
            xf, _ = _side_line(Ly, (0, 1), G)   # Y's run line along the crossed wall: its face is dc behind
            xa = xf - w * dc + w * (t30 + 0.005)
            assert abs(yh - y3) / math.sin(th) >= 2 * t30 + 0.01 and (y3 - yh) * d[1] < 0, \
                f"{X} → {Y}: the hole beside the tie at {corner} leaves no room for its offset"   # (back from the corner)
            xb = xa + w * abs(yh - y3) / math.tan(th)
            xe = xb + w * (t30 + 0.01)
            poly += [(xa, y3), (xb, yh), ((min if w < 0 else max)(u_join, xe), yh)]
    s_leave, s_join = Lv.s_of(poly[0]), Ly.s_of(poly[-1])
    def sg_of(line, s, d_):   # which way round a line runs where it travels along d_
        p0, p1 = line.at(s), line.at(s + 0.01)
        return 1 if (p1[0] - p0[0]) * d_[0] + (p1[1] - p0[1]) * d_[1] > 0 else -1
    d_out = (poly[-1][0] - poly[-2][0], poly[-1][1] - poly[-2][1])
    return s_leave, sg_of(Lv, s_leave, d), poly, s_join, sg_of(Ly, s_join, d_out)


def _conductors(members, S, pts, what):
    """A piece's conductors from the points S beyond it: each circuit's own (_lead) for its points there, plus one
    earth sized for the largest circuit — none to switches only (no earth terminal)."""
    ms = [M for M in members if set(S) & set(M["pts"])]
    assert ms, f"{what}: no circuit beyond this piece"
    G = [w for M in ms for w in M["wires"] if w[0].startswith("G")]
    G = [max(G, key=lambda w: float(w[0][1:]))] if G and any(pts[x]["kind"] != "sw" for x in S) else []
    return [w for M in ms for w in _lead(M, set(S) & set(M["pts"]), pts)] + G


def _straight_at(line, s, half):
    """True when the run line is one straight from s − half to s + half (a box sits there flat on the wall)."""
    a, m, b = line.at(s - half), line.at(s), line.at(s + half)
    return abs(math.dist(a, b) - 2 * half) < 1e-4 and abs((m[0] - a[0]) * (b[1] - a[1]) - (m[1] - a[1]) * (b[0] - a[0])) < 1e-7


def _routes_wall(pts, rounds=6):
    """Route; then (spec 30 ต.ค.: ≤ 360° of bends between boxes) put a shared TOP 4×4 pull box — every conduit
    passing it goes through, each circuit on its own — where a piece would pass 360°, and route again with those boxes
    booked, until no piece does. Junction boxes at the wall devices (spec 31 ต.ค.) where they fit: a room where the
    routing finds no height, or whose pieces end up clashing, keeps its devices looped, and everything is routed again."""
    CD["jb_off"], CD["jb_off_why"] = set(), {}
    room_of_error = lambda e: _jb_room(str(e), pts, _voids(), CD["jb_off"])
    while True:
        try:
            R = _routes_hubs(pts, rounds)
            break
        except AssertionError as e:
            room = room_of_error(e)
            if room is None:
                raise
            CD["jb_off"].add(room)
            CD["jb_off_why"][room] = str(e)[:200]
    last_ok = True
    for room in sorted(CD["jb_off"]):   # a room turned off early (before another) may fit its boxes now: try each again
        CD["jb_off"].discard(room)
        try:
            R, last_ok = _routes_hubs(pts, rounds), True
        except AssertionError:
            CD["jb_off"].add(room)
            last_ok = False
    CD["jb_off_why"] = {r: w for r, w in CD["jb_off_why"].items() if r in CD["jb_off"]}   # (a room boxed again: no reason)
    return R if last_ok else _routes_hubs(pts, rounds)   # (after a failed try, route the kept set again: CD back in step)


def _jb_room(msg, pts, V_, off):
    """The room to give up its junction boxes for an error, or None: the rooms it names — "<circuit> in <room>:", a
    piece's device or J@device, a room in its band list — then the rooms round a clash point "at x, y, z (" (±0.15 m);
    the first not yet off."""
    rooms = [m.group(1) for m in re.finditer(r"\S+ in (\w+): ", msg)]
    rooms += [{"Soffit": "Eave"}.get(pts[p]["room"], pts[p]["room"]) for p in re.findall(r"(?:J@)?(\b[A-Z]{2}_\w+)", msg) if p in pts]
    rooms += [r for r in re.findall(r"\b([A-Z][a-z]\w*) (?:run|box|drop|loop) \(", msg) if r in V_]
    m = re.search(r" at (-?[\d.]+), (-?[\d.]+), (-?[\d.]+) \(", msg)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        rooms += [r for r, (rc, *_) in V_.items() if rc[0] - 0.15 <= x <= rc[2] + 0.15 and rc[1] - 0.15 <= y <= rc[3] + 0.15]
    return next((r for r in rooms if r in V_ and r not in off), None)


def _routes_hubs(pts, rounds):
    CD["hubs"] = []
    for _ in range(rounds):
        R = _route_once(pts)
        need = _hubs_needed(R, CD["hubs"])
        if not need:
            idle = [h for h in CD["hubs"] if h not in R["hubs"]]
            assert not idle, f"pull boxes no conduit goes through: {idle}"
            _check_clear([(cid, to, P, EL["conduit"][sz] / 2) for sz, rs in R["runs"].items() for cid, to, P in rs])   # (e42_conduit_check.py)
            R["meter"] = _main_run(R, pts)   # e42_conduit_main.py: the service, overhead (spec 31 ต.ค.)
            return R
        CD["hubs"] += need
    raise AssertionError(f"pull boxes still wanted after {rounds} rounds: {need}")


def _hubs_needed(R, have, lim=360.5):   # (≤ 360°: four 90° bends, read back from sampled arcs)
    """[(room, band | plate, s)] — for each piece past lim° of bends, a hub 0.30 m short of the end of the last straight (≥ 0.40 m)
    before it (on the plaster band or up on the plate above it), on the room's plaster band (s on its run line); one
    hub for pieces whose straights are on the same line within 0.5 m (the first one's place). A straight near a hub
    already there (have) that the piece did not go through is passed over."""
    need = []
    def near(c, hs):
        ref = R["lines"][c[0]] if c[1] == "band" else R["plk"][c[0]][0]
        return any(h[:2] == c[:2] and min((h[2] - c[2]) % ref.L, (c[2] - h[2]) % ref.L) < 0.5 for h in hs)
    for route, cid, to, P, size, ws in R["pieces"]:
        acc, cand = 0.0, None
        for i in range(1, len(P)):
            a, b = P[i - 1], P[i]
            turn = math.degrees((b - a).angle(P[i + 1] - b)) if i < len(P) - 1 and (b - a).length > 1e-6 and (P[i + 1] - b).length > 1e-6 else 0.0
            if (b - a).length >= 0.40 and abs(a.z - b.z) < 1e-6 and 3.28 < a.z < 3.57:   # on the band, or up on the plate:
                for room, lns in R["plk"].items():                                          # a hub on the band below it
                    for ln in [R["lines"][room]] + lns:
                        sa, sb = ln.s_of((a.x, a.y)), ln.s_of((b.x, b.y))
                        if all(math.dist(ln.at(s_), (q.x, q.y)) < 0.003 for s_, q in ((sa, a), (sb, b))):
                            up = a.z > CD["top"]   # up on the plate (by height: in plan a plate line can lie within mm of the plaster's): a 2×4 of its own
                            kind, ref = ("plate", R["plk"][room][0]) if up else ("band", R["lines"][room])
                            L_ = (b - a).length
                            for d_ in [0.30 + 0.10 * k for k in range(int((L_ - 0.30) / 0.10) + 1)]:   # from near its far end back:
                                q_ = b - (b - a).normalized() * d_                                      # the most bends behind it
                                sm = ref.s_of((q_.x, q_.y))
                                clear = up or all(min((sm - f) % ref.L, (f - sm) % ref.L) > k_ for f, k_ in R["fixed"][room])
                                if clear and _straight_at(ref, sm, 0.25) and not near((room, kind, sm), have):
                                    cand = (room, kind, sm, route) if up else (room, kind, sm)
                                    break
            acc += turn
            if acc > lim:
                assert cand is not None, f"{route} → {to}: {acc:.0f}° of bends and no straight on the wall for a pull box"
                if not near(cand, need):
                    need.append(cand)
                break
    return need


def _over(lines_p, X, Y):
    """Over the top of the crossed wall's plate (spec 30 ต.ค.: a passing conduit may cross there, no hole): the
    run along X's wall-plate line heading d at the corner carries straight on over the plate into Y's plate line
    (the exterior plates run on in line). → (lateral, d, along-axis, X straight's far end u, Y straight's near end u,
    crossed plate's near face u, far face u)."""
    corner, kind, d = XS[(X, Y, 1)]
    G = (GX[corner[1]], GY[corner[0]])
    ax = 0 if d[0] else 1
    a, pts_x = _side_line(lines_p[X], d, G)
    a2, pts_y = _side_line(lines_p[Y], d, G)
    assert abs(a - a2) < 1e-3, f"{X} → {Y}: the wall plates do not run on in line ({a:.3f} / {a2:.3f})"
    ux_end = max(u * d[ax] for u, _ in pts_x) * d[ax]
    uy_start = min(u * d[ax] for u, _ in pts_y) * d[ax]
    face = None
    for o in bpy.data.objects:   # the plate of the wall crossed: square to d, at the corner
        if not o.name.startswith("AS_") or o.type != "MESH":
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = [min(v[k] for v in bb) for k in range(3)]
        hi = [max(v[k] for v in bb) for k in range(3)]
        long_ax = 0 if hi[0] - lo[0] > hi[1] - lo[1] else 1
        if long_ax != ax and lo[1 - ax] - 0.08 <= G[1 - ax] <= hi[1 - ax] + 0.08 and lo[ax] - 0.01 <= G[ax] <= hi[ax] + 0.01:
            face = (lo[ax], hi[ax]) if d[ax] > 0 else (hi[ax], lo[ax])
    assert face, f"{X} → {Y}: no wall plate at {corner}"
    return a, d, ax, ux_end, uy_start, face[0], face[1]
