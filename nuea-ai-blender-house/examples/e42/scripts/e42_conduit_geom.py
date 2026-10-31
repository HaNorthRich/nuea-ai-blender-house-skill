# E42 ST12 conduit, part 1 of 3: settings (CD) and the geometry kit — rounded paths, arcs, the wall-face lines,
# the height bands. Parts: e42_conduit_geom.py → e42_conduit.py (tables, entry) → e42_conduit_route.py (the router).
import bisect
import math
from mathutils import Vector

CD = dict(
    dc=0.025,                     # conduit centreline off its wall face (on saddles), = half a box's depth: straight into a knockout
    level_dz=2e-6,                # a piece counts as level under this rise (float32 read-back: ~8 ulps at z < 4 m)
    rmin={"1/2": 0.102, "3/4": 0.114, "1": 0.146},   # least centreline bend radius (NEC Ch.9 Tab.2; no Thai figure found)
    off_deg=30.0,                 # the user: a proud column is passed with 2 × 30° out + 2 × 30° back
    # conduit fill ≤ 40 % (shared conduits). shortcut: assumed sizes, no Thai table found: THW OD = IEC 60227 max
    # (1.5/2.5 solid, 4 stranded), conduit ID = 1/2" EMT-equivalent 15.8 mm; replace with the ตราช้าง / มอก. figures
    fill=dict(od={"1.5": 0.0033, "2.5": 0.0039, "4": 0.0046}, id={"1/2": 0.0158, "3/4": 0.0209, "1": 0.0266}),
    clear=0.01,                   # kept between a conduit and a column face / corner
    step=0.015,                   # arcs sampled every 1.5 cm
    gap=0.002,                    # between two conduits stacked on a wall
    over_angle=0.012,             # over the ceiling's wall angle: a loop bending down into the wall crosses its face ~1 cm lower
    gap_s=0.03,                   # along a level, kept between the ends of two runs that share it
    slot=0.022,                   # conduits sharing a climb window stand out from the face in slots this far apart (0–3)
    top=3.45,                     # wall (plaster) top: the band's ceiling — above is the steel wall plate (no holes)
    below_dl=0.03,                # kept clear under a downlight box: its flex drops 2.5 cm then turns out into the void
    pending=set(),   # (points on no route yet: named by the check)
    route_size={"S2+S3+L2-ccw": "3/4", "A1+S1+L1-Bed1": "3/4", "L1+S1+L2-Bed2": "3/4"},   # spec 30 ต.ค.: three circuits share a 3/4" (the 1/2" band was full)
    home_plate={"A1+S1+L1-Bed1"},   # spec 30 ต.ค.: a conduit only passing the living room climbs onto the plate band from the CU
    dl_face={"DL_Living_1": 2, "DL_Porch_1": 1, "DL_Porch_2": 1},   # a downlight box kept to one face of its room (0 x0, 1 y0,
    # 2 x1, 3 y1): DL_Living_1's so SW_Living ends its run; the porch lights' on the living room's south wall (flex through it)
    tie_chase={"SW_Bath"},        # spec 30 ต.ค. (ก): chased into the door-jamb tie (no brick between the bath door and D2)
    drop_lead=0.04, drop_deg=45.0,  # the ground run: straight down this far out of the CU, then 2 bends ≤ this steep into its chase
)


def _round(poly, radii, closed=True, step=None):
    """A sharp polyline with every corner bent to its radius (true arcs, sampled about every step m): how a rigid conduit
    is bent on site. radii[i] for vertex i; an end of an open line stays where it is. Asserts each leg holds both the
    bends at its ends. → (points, the turn at each vertex in degrees, measured)."""
    n = len(poly)
    turn, t = [0.0] * n, [0.0] * n
    for i in (range(n) if closed else range(1, n - 1)):
        A, B, C = poly[i - 1], poly[i], poly[(i + 1) % n]
        u1 = ((B[0] - A[0]) / math.dist(A, B), (B[1] - A[1]) / math.dist(A, B))
        u2 = ((C[0] - B[0]) / math.dist(B, C), (C[1] - B[1]) / math.dist(B, C))
        turn[i] = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
        t[i] = radii[i] * math.tan(turn[i] / 2)
    for i in range(1, n + (1 if closed else 0)):   # leg i-1 → i holds the tangent of both bends
        a, b = (i - 1) % n, i % n
        assert t[a] + t[b] <= math.dist(poly[a], poly[b]) + 1e-6, \
            f"bends at {poly[a][0]:.2f}, {poly[a][1]:.2f} and {poly[b][0]:.2f}, {poly[b][1]:.2f}: no room to bend"
    out = [] if closed else [poly[0]]
    for i in (range(n) if closed else range(1, n - 1)):
        A, B, C = poly[i - 1], poly[i], poly[(i + 1) % n]
        if turn[i] < 1e-6:
            out.append(B)
            continue
        u1 = ((B[0] - A[0]) / math.dist(A, B), (B[1] - A[1]) / math.dist(A, B))
        u2 = ((C[0] - B[0]) / math.dist(B, C), (C[1] - B[1]) / math.dist(B, C))
        cr = u1[0] * u2[1] - u1[1] * u2[0]
        r = radii[i]
        T1 = (B[0] - u1[0] * t[i], B[1] - u1[1] * t[i])
        nl = (-u1[1], u1[0]) if cr > 0 else (u1[1], -u1[0])   # towards the centre
        c = (T1[0] + nl[0] * r, T1[1] + nl[1] * r)
        a0 = math.atan2(T1[1] - c[1], T1[0] - c[0])
        out += _arc_pts(c, r, a0, a0 + (turn[i] if cr > 0 else -turn[i]), step)
    if not closed:
        out.append(poly[-1])
    clean = [out[0]]
    for q in out[1:]:
        if math.dist(q, clean[-1]) > 1e-6:
            clean.append(q)
    return clean, [math.degrees(a) for a in turn]


def _arc_pts(c, r, a0, a1, step=None):   # (not _arc: house_helpers has one)
    """Points on a circle centre c, radius r, from angle a0 to a1 (radians), sampled about every step metres."""
    n = max(2, int(abs(a1 - a0) * r / (step or CD["step"])) + 1)
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * k / (n - 1)), c[1] + r * math.sin(a0 + (a1 - a0) * k / (n - 1))) for k in range(n)]


def _corner_r(pi, pj, size):
    """The radius a run's 90° turn needs to clear a column filling the corner (pi, pj proud of the two walls) while the
    straights hug both walls at dc: distance from the arc centre to the column corner ≥ R + r_conduit + clear."""
    a, b = max(0.0, pi - CD["dc"]), max(0.0, pj - CD["dc"])
    if not a and not b:
        return CD["rmin"][size]
    need, rr = 0.0, EL["conduit"][size] / 2 + CD["clear"]
    while not (a <= need and b <= need and math.hypot(need - a, need - b) >= need + rr) and need < 2.0:
        need += 0.005   # the column corner between the arc and the corner, R + rr from the centre
    return max(CD["rmin"][size], need)


def _track_path(room, size="1/2"):
    """The plan line a conduit follows round a room on its walls, counter-clockwise, dc off the plaster: a corner is one
    90° bend, or two 45° bends past a column filling it (the run stays on the walls); a column standing proud mid-wall
    is passed with an offset bend (the user: 2 × 30° out, 2 × 30° back). → (points, [(x, y, degrees)] of the bends)."""
    rect, cut, _ = _voids()[room]
    x0, y0, x1, y1 = rect
    dc, r, rc = CD["dc"], CD["rmin"][size], EL["conduit"][size] / 2
    sides = [((x0, y0), (1, 0), x1 - x0, (0, 1)), ((x1, y0), (0, 1), y1 - y0, (-1, 0)),
             ((x1, y1), (-1, 0), x1 - x0, (0, -1)), ((x0, y1), (0, -1), y1 - y0, (1, 0))]
    proud = []   # per side: [(along a, along b, how far proud)] of the columns standing into the room
    for (sx, sy), (ux, uy), L, (nx, ny) in sides:
        cols = []
        for b in cut:
            ds = [(bx - sx) * nx + (by - sy) * ny for bx in (b[0], b[3]) for by in (b[1], b[4])]
            us = [(bx - sx) * ux + (by - sy) * uy for bx in (b[0], b[3]) for by in (b[1], b[4])]
            if min(ds) >= dc + rc + CD["clear"] or max(ds) <= 1e-6 or max(us) < -1e-6 or min(us) > L + 1e-6:
                continue   # clear of the run's line, or not into the room
            assert min(ds) <= 1e-6, f"{room}: a column stands {min(ds):.3f} off the wall, in the run's way"
            cols.append((max(0.0, min(us)), min(L, max(us)), max(ds)))
        proud.append(cols)
    poly, rad, deg = [], [], []
    def vert(i, u, o, rr, d):
        (sx, sy), (ux, uy), L, (nx, ny) = sides[i]
        poly.append((sx + ux * u + nx * (dc + o), sy + uy * u + ny * (dc + o)))
        rad.append(rr)
        deg.append(d)
    th = math.radians(CD["off_deg"])
    t30 = r * math.tan(th / 2)
    for i in range(4):
        L = sides[i][2]
        j = (i + 1) % 4
        mids = []   # columns mid-side, merged where two are too close to come back to the wall between them
        for a, b, d in sorted(c for c in proud[i] if c[0] > 1e-6 and c[1] < L - 1e-6):
            if d <= dc - rc - CD["clear"]:
                continue   # barely proud: the run passes it straight
            if mids and a - mids[-1][1] < 2 * (CD["clear"] + 2 * t30 + (max(d, mids[-1][2]) + CD["clear"]) / math.tan(th)):
                mids[-1] = (mids[-1][0], max(b, mids[-1][1]), max(d, mids[-1][2]))
            else:
                mids.append((a, b, d))
        for a, b, d in mids:
            o = d + CD["clear"]   # out past the column face (the run's dc + clear off it)
            run = o / math.tan(th)
            ua, ub = a - CD["clear"] - t30, b + CD["clear"] + t30
            vert(i, ua - run, 0.0, r, CD["off_deg"])
            vert(i, ua, o, r, CD["off_deg"])
            vert(i, ub, o, r, CD["off_deg"])
            vert(i, ub + run, 0.0, r, CD["off_deg"])
        # the corner at the end of side i: what fills it, how far proud of each wall
        pi = max([d for a, b, d in proud[i] if b >= L - 1e-6] + [0.0])
        pj = max([d for a, b, d in proud[j] if a <= 1e-6] + [0.0])
        if _corner_r(pi, pj, size) <= r + 1e-9:
            vert(i, L - dc, 0.0, r, 90.0)
        else:   # two 45° bends: a short diagonal past the column's corner, rc + clear off it
            m = (pi - dc) + (pj - dc) + (rc + CD["clear"]) * math.sqrt(2)   # along each run line, from where the two meet
            vert(i, L - dc - m, 0.0, r, 45.0)
            (sx, sy), (ux, uy), Lj, (nx, ny) = sides[j]
            poly.append((sx + ux * (dc + m) + nx * dc, sy + uy * (dc + m) + ny * dc))
            rad.append(r)
            deg.append(45.0)
    pts, turn = _round(poly, rad)
    for i, (got, want) in enumerate(zip(turn, deg)):   # each bend as designed, measured off the geometry
        assert abs(got - want) < 0.1, f"{room}: bend at {poly[i][0]:.2f}, {poly[i][1]:.2f} is {got:.1f}°, meant {want:.0f}°"
    return pts, [(*poly[i], turn[i]) for i in range(len(poly))]



class _Line:
    """A room's run line (counter-clockwise, closed) with arc length: where a point sits on it, and the stretch
    between two places either way round."""

    def __init__(self, room, size="1/2", poly=None):
        self.room = room
        if poly is None:
            self.pts, self.bends = _track_path(room, size)
        else:   # a given sharp loop, each corner a plain bend (the wall-plate faces: no columns)
            self.pts, turn = _round(poly, [CD["rmin"][size]] * len(poly))
            self.bends = [(*poly[i], turn[i]) for i in range(len(poly))]
        self.cum = [0.0]
        for i in range(len(self.pts)):
            self.cum.append(self.cum[-1] + math.dist(self.pts[i], self.pts[(i + 1) % len(self.pts)]))
        self.L = self.cum[-1]

    def at(self, s):   # the plan point at arc length s
        s = min(s % self.L, self.L - 1e-12)   # (-tiny) % L == L
        i = min(max(0, bisect.bisect_right(self.cum, s) - 1), len(self.pts) - 1)
        a, b = self.pts[i % len(self.pts)], self.pts[(i + 1) % len(self.pts)]
        f = (s - self.cum[i]) / max(self.cum[i + 1] - self.cum[i], 1e-12)
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)

    def s_of(self, P):   # arc length of the line point nearest P
        best = None
        for i in range(len(self.pts)):
            a, b = self.pts[i], self.pts[(i + 1) % len(self.pts)]
            ab = (b[0] - a[0], b[1] - a[1])
            L2 = ab[0] ** 2 + ab[1] ** 2
            t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((P[0] - a[0]) * ab[0] + (P[1] - a[1]) * ab[1]) / L2))
            d = math.dist(P, (a[0] + ab[0] * t, a[1] + ab[1] * t))
            if best is None or d < best[0]:
                best = (d, self.cum[i] + math.sqrt(L2) * t)
        return best[1] % self.L

    def span(self, s0, s1, sg):   # how far from s0 to s1 going sg (+1 counter-clockwise, -1 clockwise)
        return (s1 - s0) % self.L if sg > 0 else (s0 - s1) % self.L

    def stretch(self, s0, s1, sg, z):   # the 3D points from s0 to s1 going sg, at height z
        d = self.span(s0, s1, sg)
        assert d > 1e-6, f"{self.room}: an empty stretch at {s0:.3f}"
        out = [(*self.at(s0), z)]
        inner = sorted(((c - s0) % self.L if sg > 0 else (s0 - c) % self.L) for c in self.cum[:-1])
        out += [(*self.at(s0 + sg * u), z) for u in inner if 1e-9 < u < d - 1e-9]
        out.append((*self.at(s1), z))
        return [Vector(q) for q in out]

    def bend_deg(self, s0, s1, sg):   # the bending (°) a run takes along the stretch
        return sum(dg for x, y, dg in self.bends if self.span(s0, self.s_of((x, y)), sg) < self.span(s0, s1, sg))


def ccw(s0, s1, sg):   # a run from s0 to s1 going sg, as its counter-clockwise (start, end)
    return (s0, s1) if sg > 0 else (s1, s0)


def _plate_rect(room):
    """The faces of the steel wall plates (AS_*_2C) round a room: (x0, y0, x1, y1) of the clear space between them,
    and their z range — the second band the user allowed for passing runs (no columns up there)."""
    rect = _voids()[room][0]
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    x0, y0, x1, y1 = -9.0, -9.0, 9.0, 9.0
    zlo, zhi = 9.0, -9.0
    for o in bpy.data.objects:
        if not o.name.startswith("AS_") or o.type != "MESH":
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        bx0, by0, bz0 = (min(v[k] for v in bb) for k in range(3))
        bx1, by1, bz1 = (max(v[k] for v in bb) for k in range(3))
        if bx1 - bx0 > by1 - by0 and bx0 < cx < bx1:   # runs along x, spans the room
            if by1 <= cy:
                y0 = max(y0, by1)
            elif by0 >= cy:
                y1 = min(y1, by0)
        elif by1 - by0 > bx1 - bx0 and by0 < cy < by1:
            if bx1 <= cx:
                x0 = max(x0, bx1)
            elif bx0 >= cx:
                x1 = min(x1, bx0)
        zlo, zhi = min(zlo, bz0), max(zhi, bz1)
    return (x0, y0, x1, y1), (zlo, zhi)


def _plate_line(room, k=0):   # the run line on the plate faces in slot k (k · slot nearer the room): its own rmin corners
    (x0, y0, x1, y1), (zlo, zhi) = _plate_rect(room)
    d = CD["dc"] + k * CD["slot"]
    return _Line(room, "3/4", poly=[(x0 + d, y0 + d), (x1 - d, y0 + d), (x1 - d, y1 - d), (x0 + d, y1 - d)]), (zlo, zhi)


class _Levels:
    """Heights on a room's walls (the user: stacked on the wall face, the plaster band first, nearest the ceiling first).
    Holds the bands taken: (z low, z high, counter-clockwise stretch) — a conduit (z ± r), a box with the room its
    drop or flex needs below it. Two bands clash when they overlap in height (gap between) and along the line (gap_s)."""

    def __init__(self, room, line, z0=None, top=None):
        if z0 is None:
            o = bpy.data.objects[f"CL_{room}_WallAngle"]
            z0 = max((o.matrix_world @ v.co).z for v in o.data.vertices)
        self.z0, self.top = z0 + CD["over_angle"], top or CD["top"]
        self.line, self.used = line, []

    def _hit(self, a, b):
        L, g = self.line.L, CD["gap_s"]
        a0, la = a[0] % L, (a[1] - a[0]) % L
        b0, lb = b[0] % L, (b[1] - b[0]) % L
        return ((b0 - a0) % L) < la + g or ((a0 - b0) % L) < lb + g

    @staticmethod
    def _clashes(a, b):
        """run / run:k a conduit (k: its slot, k·22 mm out from the face), box a box and the room under it, front:k a
        climb in front of the band. Different slots stand apart; a climb only covers lids (and other climbs). climb /
        loop: a run that leaves the band there (onto the plate / into the wall) — a run, except at a hub."""
        ka, sa = (a.split(":") + ["0"])[:2]
        kb, sb = (b.split(":") + ["0"])[:2]
        ka, kb = ("run" if k_ in ("climb", "loop") else k_ for k_ in (ka, kb))
        if ka in ("box", "pbox") or kb in ("box", "pbox"):   # (pbox: a plate pull box, its conduit's own: see own)
            return True
        if ka == "front" and kb == "front":
            return sa == sb
        if ka == "run" and kb == "run":
            return sa == sb
        return False

    def free(self, lo, hi, st, kind="run", owner=None):
        """kind: run (a conduit on the wall), box (a box and the room under it), front (a climb onto a proud wall
        plate, in front of the band: it only covers lids)."""
        clash = lambda k2: self._clashes(kind, k2)
        own = lambda o2, k2: owner is not None and o2 == owner and kind != "box" and k2 != "box"   # a run's own stretches meet
        def hub_ok(lo2, hi2, k2):   # a hub (a shared pull box): a straight run passes through it, inside its height
            ka, kb = kind.split(":")[0], k2.split(":")[0]
            if "hub" not in (ka, kb):
                return None
            if kb == "hub":   # this band against a hub booked before
                other, r_lo, r_hi, h_lo, h_hi = kind, lo, hi, lo2, hi2
            else:             # a hub being booked against this band
                other, r_lo, r_hi, h_lo, h_hi = k2, lo2, hi2, lo, hi
            k_, slot_ = (other + ":0").split(":")[:2]
            return k_ == "run" and int(slot_) <= 1 and r_lo >= h_lo - 1e-9 and r_hi <= h_hi + 1e-9   # (a 4×4 holds slots 0–1)
        def hit(lo2, hi2, st2, k2, o2):
            if not (self._hit(st, st2) and lo < hi2 + CD["gap"] - 1e-9 and lo2 < hi + CD["gap"] - 1e-9):
                return False
            h = hub_ok(lo2, hi2, k2)
            return (not h) if h is not None else clash(k2) and not own(o2, k2)
        return lo >= self.z0 - 1e-9 and hi <= self.top - CD["gap"] + 1e-9 and not any(hit(*u) for u in self.used)

    def take(self, stretches, r, owner=None, kind="run"):
        """The lowest height (centre) for a conduit of radius r over the stretches [(s0, s1, sg)]."""
        return take_joint([(self, st, -r, r, kind) for st in stretches], owner)


def take_joint(bands, owner=None, prefer=None, only=False):
    """The lowest z at which every band [(levels, (s0, s1, sg), dz low, dz high)] is free (searched in 1 mm steps);
    takes them all. Asserts when the wall band is full."""
    # a band: (levels, stretch, lo, hi, kind[, zfix, mode]) — lo/hi off z (hi None: to the band top); mode "abs": off
    # zfix instead of z; mode "jog": from zfix to z (a run changing height)
    bands = [(b[0], ccw(*b[1]), b[2], b[3], b[4] if len(b) > 4 else ("box" if b[2] < -0.02 else "run"),
              b[5] if len(b) > 5 else None, b[6] if len(b) > 6 else None) for b in bands]
    def rng(lv, z, lo, hi, zf, md):
        top = lambda zz: lv.top - CD["gap"] if hi is None else zz + hi
        if md == "abs":
            return zf + lo, top(zf)
        if md == "jog":
            return min(z, zf) + lo, max(top(z), top(zf))
        return z + lo, top(z)
    fits = lambda z: all(lv.free(*rng(lv, z, lo, hi, zf, md), st, k, owner) for lv, st, lo, hi, k, zf, md in bands)
    if prefer is not None and fits(prefer):   # the height the run came in at: no change of height needed
        for lv, st, lo, hi, k, zf, md in bands:
            lv.used.append((*rng(lv, prefer, lo, hi, zf, md), st, k, owner))
        return prefer
    if only:   # that height or none
        raise AssertionError(f"the wall band is full: no room at {prefer:.3f} for " + ", ".join(
            f"{lv.line.room} {k} {tuple(round(v, 2) for v in st)}" for lv, st, lo, hi, k, zf, md in bands if not lv.free(*rng(lv, prefer, lo, hi, zf, md), st, k, owner)))
    z = max(lv.z0 - lo for lv, st, lo, hi, k, zf, md in bands if md is None)
    while z < max(lv.top for lv, *_ in bands):
        if all(lv.free(*rng(lv, z, lo, hi, zf, md), st, k, owner) for lv, st, lo, hi, k, zf, md in bands):
            for lv, st, lo, hi, k, zf, md in bands:
                lv.used.append((*rng(lv, z, lo, hi, zf, md), st, k, owner))
            return z
        z += 0.001
    def ranges(lv, st, lo, hi, k, zf, md):   # the heights where this band alone is free
        out_, z_ = [], 3.0
        while z_ < CD["top"]:
            if lv.free(*rng(lv, z_, lo, hi, zf, md), st, k, owner):
                if out_ and abs(out_[-1][1] - z_) < 0.0015:
                    out_[-1][1] = z_
                else:
                    out_.append([z_, z_])
            z_ += 0.001
        return [(round(a_, 3), round(b_, 3)) for a_, b_ in out_]
    raise AssertionError("the wall band is full: no height for " + "; ".join(
        f"{lv.line.room} {k}{'/' + md if md else ''} {tuple(round(v, 2) for v in st)} dz {lo:+.3f}..{hi if hi is None else round(hi, 3)} free {ranges(lv, st, lo, hi, k, zf, md)}"
        for lv, st, lo, hi, k, zf, md in bands))


def _bend_angle(lat, r, amax):
    """The angle of two equal bends (radius r) that shift a run sideways by lat: amax with a straight between them,
    or, when lat is too small for that, the largest angle whose two bends meet with no straight (bisected)."""
    f = lambda a: 2 * r * math.tan(a / 2) * math.sin(a)   # the least shift two bends of a make
    if lat >= f(amax):
        return amax
    lo, hi = 0.0, amax
    for _ in range(40):
        lo, hi = ((lo + hi) / 2, hi) if f((lo + hi) / 2) <= lat else (lo, (lo + hi) / 2)
    return lo


def _round3(pts, radii, step=None):
    """An open 3D polyline with each inner corner bent to its radius (an arc in the corner's plane): a field bend.
    radii[i] for vertex i (0 = leave sharp: a fitting). Asserts each leg holds the bends at its ends."""
    P = [Vector(p) for p in pts]
    n, t, turn = len(P), [0.0] * len(P), [0.0] * len(P)
    for i in range(1, n - 1):
        u1, u2 = (P[i] - P[i - 1]).normalized(), (P[i + 1] - P[i]).normalized()
        turn[i] = math.acos(max(-1.0, min(1.0, u1.dot(u2))))
        t[i] = radii[i] * math.tan(turn[i] / 2) if radii[i] else 0.0
    for i in range(1, n):
        assert t[i - 1] + t[i] <= (P[i] - P[i - 1]).length + 1e-6, f"no room to bend between {tuple(round(v, 3) for v in P[i - 1])} and {tuple(round(v, 3) for v in P[i])}"
    out = [P[0]]
    for i in range(1, n - 1):
        if not t[i] or turn[i] < 1e-6:
            out.append(P[i])
            continue
        u1, u2 = (P[i] - P[i - 1]).normalized(), (P[i + 1] - P[i]).normalized()
        T1 = P[i] - u1 * t[i]
        w = (u2 - u1 * u1.dot(u2)).normalized()   # in the corner's plane, square to u1, towards the turn
        c = T1 + w * radii[i]
        k = max(2, int(turn[i] * radii[i] / (step or CD["step"])) + 1)
        for j in range(k):
            a = turn[i] * j / (k - 1)
            out.append(c + (T1 - c) * math.cos(a) + u1 * radii[i] * math.sin(a))
    out.append(P[-1])
    clean = [out[0]]
    for q in out[1:]:
        if (q - clean[-1]).length > 1e-6:
            clean.append(q)
    return clean, [math.degrees(a) for a in turn]
