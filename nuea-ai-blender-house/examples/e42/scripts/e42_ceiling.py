"""E42 ST08 ฝ้า (spec 29 ต.ค.), after the fascia and the roof covering:
  inside: gypsum 9 mm 1.20 × 2.40 at FL + 2.80 (bath: moisture-resistant gypsum 9 mm at the bath floor + 2.60) on a
  C-line grid — wall angle round the room, main runners ≤ 0.80 m, cross runners ≤ 0.40 m under them (SCG ceiling
  manual p.7-8; gypsum-specific spacings are not in it), hung from the roof steel every ≤ 1.00 m (assumed);
  eave soffit all round (porch eave and corner too, spec 29 ต.ค.): SCG Smartboard vented 4 mm 0.60 × 1.20, open
  5 mm joints, its face 1" above the fascia bottom (manual p.7), runners at the wall, at the 0.60 joint and at the
  fascia, cross runners @ 0.40; porch ceiling (inside the eave line): flat Smartboard, butt joints filled smooth.
Screws 1.2 cm in from the edges, 5 cm from the corners, then @ 0.20 m on every runner (manual p.7-8).

    exec(<e42_struct>); exec(<e42_walls>); exec(<e42_roof>); exec(<e42_roof_trim>); exec(<e42_fascia>); exec(<this>)
    build_ceilings(); print(report(C_CEIL)); print(selfcheck_ceilings())
"""
import math
import bmesh
from mathutils import Vector

C_CEIL = "E42 ST08 Ceiling"
FL, FL_BATH = 0.45, ZONES["Bath"][1] + SLAB["t"] + 0.03   # finished floors (bath 10 cm down)
# hangers ≤ 1.00 m apart along a main and ≤ 0.75 m from its ends (assumed: the manual gives none; the cross runners
# rest on the wall angle at the walls)
CEIL = dict(h=2.80, h_bath=2.60, board=(1.20, 2.40, 0.009), main=0.80, cross=0.40, hang=1.00, hang_end=0.75,
            soffit=(0.60, 1.20, 0.004), gap=0.005, above_fascia=0.025, screw=0.20, screw_edge=0.012, screw_end=0.05,
            # CS C-Line (spec 29 ต.ค.: 0.625 kg / 4 m; the TIS one is 1.125 kg): lipped C 36 × 11, 3 mm lips, 0.31 mm
            # (0.156 kg/m); wall angle 20 × 20 × 0.4; hanger rod Ø 4 mm
            cline=(0.036, 0.011, 0.00031), lip=0.003, angle=(0.020, 0.0004), rod=0.002, stock=4.0, lap=0.10,
            waste=0.05, hatch=0.60,
            wall_clear=0.12)   # no hanger this near a main's end at a wall: the conduits run there (ST12, on the wall face)
CEIL_KG_M = 0.625 / 4.0
SPEC = dict(gyp="แผ่นยิปซัมบอร์ด 9 มม. ขอบลาด 1.20 × 2.40 ม.", mr="แผ่นยิปซัมบอร์ดกันชื้น 9 มม. 1.20 × 2.40 ม.",
            vent="ฝ้าสมาร์ทบอร์ด SCG รุ่นเซาะร่องระบายอากาศครึ่งแผ่น 60 × 120 × 0.4 ซม. สีซีเมนต์",
            flat="ฝ้าสมาร์ทบอร์ด SCG รุ่นเรียบ 60 × 120 × 0.4 ซม.", cline="โครงคร่าว CS C-Line นน. 0.625 กก. ยาว 4 ม.",
            clip="ตัวล็อคโครง C-line clip (ทุกจุดตัดคร่าว)", spring="สปริงปรับระดับ (spring joiner)",
            top="ฉากเหล็ก + ชุดหัวโครง ยึดลวดกับเหล็กหลังคา", hatch="ช่องเซอร์วิสฝ้า 60 × 60 ซม. กรอบอะลูมิเนียม",
            angle="ฉากริมเหล็กชุบสังกะสี 20 × 20 มม. ยาว 4 ม.", rod="ลวด/ก้านแขวนฝ้า Ø 4 มม.",
            screw="สกรูยึดฝ้าปลายสว่าน 18 มม. (@ 0.20 ม.)", tape="รอยต่อฉาบเรียบ: เทปกระดาษ + ปูนฉาบรอยต่อยิปซัม",
            seal="รอยต่อร่อง 5 มม.: ยาแนวโพลียูรีเทน",
            tape_fc="รอยต่อฉาบเรียบ (สมาร์ทบอร์ดภายนอก): เทปตาข่ายไฟเบอร์กลาส + วัสดุฉาบรอยต่อไฟเบอร์ซีเมนต์ (สมมติ)")
HATCH_ROOM = "Living"
# seeds off the column lines: at (4.5, 4.5) the living room's +x scan stopped on column D3, 14 cm short of the wall
ROOMS = dict(Bed2=((1.5, 1.5), "gyp"), Bath=((1.5, 3.75), "mr"), Bed1=((1.5, 6.0), "gyp"), Living=((4.5, 4.0), "gyp"))
HATCH_AT = (4.50, 4.50)   # the user: the hatch stays where it is


def _room_rect(seed, z):
    """The room's plaster faces round a plan seed at height z, read from the wall/column solids: (x0, y0, x1, y1)."""
    boxes = list(_solids([C_WALL, C_COL]).values())
    sx, sy = seed
    hit = lambda b, ax: b[2] < z < b[5] and (b[1] < sy < b[4] if ax == 0 else b[0] < sx < b[3])
    x0 = max(b[3] for b in boxes if hit(b, 0) and b[3] <= sx)
    x1 = min(b[0] for b in boxes if hit(b, 0) and b[0] >= sx)
    y0 = max(b[4] for b in boxes if hit(b, 1) and b[4] <= sy)
    y1 = min(b[1] for b in boxes if hit(b, 1) and b[1] >= sy)
    return x0, y0, x1, y1


def _intruders(rect, z):
    """Solids standing inside a rect at height z (columns proud of the walls): their plan boxes."""
    x0, y0, x1, y1 = rect
    return [b for b in _solids([C_WALL, C_COL]).values()
            if b[2] < z < b[5] and b[0] < x1 - 1e-4 and b[3] > x0 + 1e-4 and b[1] < y1 - 1e-4 and b[4] > y0 + 1e-4]


def _clip(poly, a, b):
    """Convex clip of a plan polygon by the half-plane left of the directed line a → b."""
    out = []
    side = lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        sp, sq = side(p), side(q)
        if sp >= -1e-9:
            out.append(p)
        if (sp >= -1e-9) != (sq >= -1e-9):
            t = sp / (sp - sq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def _slab(bm, poly, z0, z1):
    """Extrude a convex plan polygon from z0 to z1 into bm."""
    lo = [bm.verts.new((x, y, z0)) for x, y in poly]
    hi = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))


def _area(poly):
    return abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))) / 2


def _runs(a, b, blocks, ax):
    """Pieces of the runner interval [a, b] along axis ax left after the plan blocks [(lo, hi)] it passes."""
    out, cur = [], a
    for lo, hi in sorted(blocks):
        if hi <= cur or lo >= b:
            continue
        if lo - cur > 0.05:
            out.append((cur, lo))
        cur = max(cur, hi)
    if b - cur > 0.05:
        out.append((cur, b))
    return out


def _cline(bm, p0, p1, z, flip=False):
    """A C-Line runner p0 → p1 (plan, along x or y): 36 mm face on z, legs up with 3 mm lips (down when flip)."""
    w, h, t = CEIL["cline"]
    d = (Vector((*p1, 0)) - Vector((*p0, 0))).normalized()
    side = Vector((-d.y, d.x, 0))
    s = -1 if flip else 1
    lp = CEIL["lip"]
    path = [(-w / 2 + lp, s * h), (-w / 2, s * h), (-w / 2, 0.0), (w / 2, 0.0), (w / 2, s * h), (w / 2 - lp, s * h)]
    prism(bm, strip(path, t), 0.0, (Vector((*p1, 0)) - Vector((*p0, 0))).length,
          lambda u, a, zz: tuple(Vector((*p0, z)) + d * u + side * a + Vector((0, 0, zz))))


def _hang_point(p, z):
    """The roof steel straight above plan point p from height z: the hit z, or None (between members). Ceiling
    and paint pieces on the way are passed through (a later stage must not hide the roof from the hangers)."""
    dg = bpy.context.evaluated_depsgraph_get()
    skip = {o for cn in ("E42 ST08 Ceiling", "E42 ST09 Primer", "E42 ST10 Paint Coat 1", "E42 ST13 Paint Coat 2") if cn in bpy.data.collections
            for o in bpy.data.collections[cn].objects}   # (.objects: all_objects is a stale cache after a rebuild)
    q = Vector((*p, z + 0.001))
    for _ in range(40):
        ok, loc, nrm, idx, ob, mtx = bpy.context.scene.ray_cast(dg, q, Vector((0, 0, 1)))
        if not ok:
            return None
        if ob in skip or (ob.original in skip if hasattr(ob, "original") else False):
            q = loc + Vector((0, 0, 1e-4))
            continue
        if ob.name.startswith(("RF_Rafter", "RF_Hip", "RF_Ridge", "RF_Post")) or ob.name.endswith("_2C"):
            return loc.z
        return None
    raise AssertionError(f"hanger ray at {p} passed 40 ceiling/paint faces without an answer")


def _minus(r, boxes):
    """Rectangle r (x0, y0, x1, y1) less the plan boxes (x0, y0, _, x1, y1, _): the rectangles left (a board cut
    round a column, exactly, without a boolean)."""
    out = [r]
    for b in boxes:
        nxt = []
        for x0, y0, x1, y1 in out:
            if b[0] >= x1 or b[3] <= x0 or b[1] >= y1 or b[4] <= y0:
                nxt.append((x0, y0, x1, y1))
                continue
            cx0, cx1, cy0, cy1 = max(x0, b[0]), min(x1, b[3]), max(y0, b[1]), min(y1, b[4])
            nxt += [q for q in ((x0, y0, cx0, y1), (cx1, y0, x1, y1), (cx0, y0, cx1, cy0), (cx0, cy1, cx1, y1))
                    if q[2] - q[0] > 1e-5 and q[3] - q[1] > 1e-5]
        out = nxt
    return out


def _search(P, side, zb, reach=0.5):
    """Roof steel over plan point P, found within `reach` sideways (2 cm steps): (offset, top z) or (None, None)."""
    for k in sorted(range(-round(reach / 0.02), round(reach / 0.02) + 1), key=abs):
        q = P + side * (k * 0.02)
        z = _hang_point((q.x, q.y), zb)
        if z:
            return k * 0.02, z
    return None, None


def _hangers_along(bm, p0, p1, zb, tag, parts=None):
    """Hangers for one main runner p0 → p1 (plan): one under every roof member crossing it (scanned every 2 cm),
    more along a member that runs with it, then sideways ones (a short link from the main, counted) wherever a gap
    exceeds CEIL["hang"] or an end is further than CEIL["hang_end"]. Returns (positions along, rod length, links)."""
    P0 = Vector((*p0, 0.0))
    d = Vector((*p1, 0.0)) - P0
    L = d.length
    d.normalize()
    side = Vector((-d.y, d.x, 0.0))
    segs, cur = [], []
    for k in range(int(L / 0.02) + 1):
        t = k * 0.02
        z = _hang_point(tuple((P0 + d * t).xy), zb)
        if z:
            cur.append((t, z))
        elif cur:
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    w_ = CEIL["wall_clear"]
    segs = [s_ for s_ in ([q for q in sg if w_ <= q[0] <= L - w_] for sg in segs) if s_]
    pts = []   # (t along, sideways offset, top z)
    for sg in segs:
        a, b = sg[0][0], sg[-1][0]
        n = 0 if b - a <= 0.10 else math.ceil((b - a) / CEIL["hang"] - 1e-9)
        for i in range(n + 1):
            tt = (a + b) / 2 if n == 0 else a + (b - a) * i / n
            t, z = min(sg, key=lambda s: abs(s[0] - tt))
            pts.append((t, 0.0, z))
    def fill(t):
        off, z = _search(P0 + d * t, side, zb)
        assert z, f"{tag}: no roof steel within 0.5 m of a hanger at {tuple(round(c, 2) for c in (P0 + d * t).xy)}"
        pts.append((t, off, z))
    for _ in range(50):   # until the ends and every gap are within reach
        ts = sorted(p[0] for p in pts)
        if not ts or ts[0] > CEIL["hang_end"] + 0.05:
            fill(min(CEIL["hang_end"], L / 2))
            continue
        if L - ts[-1] > CEIL["hang_end"] + 0.05:
            fill(max(L - CEIL["hang_end"], L / 2))
            continue
        gap = next(((a, b) for a, b in zip(ts, ts[1:]) if b - a > CEIL["hang"] + 0.05), None)   # 2 cm scan slack
        if not gap:
            break
        fill((gap[0] + gap[1]) / 2)
    else:
        raise AssertionError(f"{tag}: hangers do not converge")
    hl, links = 0.0, []
    for t, off, z in pts:
        q = P0 + d * t + side * off
        X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
        _cuboid(bm, Vector((q.x, q.y, (zb + z) / 2)), [X, Y, Z], [CEIL["rod"], CEIL["rod"], (z - zb) / 2])
        if parts:   # spring joiner at the main, steel angle + rod joiner on the roof member
            _cuboid(parts[0], Vector((q.x, q.y, zb + 0.015)), [X, Y, Z], [0.008, 0.012, 0.015])
            _cuboid(parts[1], Vector((q.x, q.y, z - 0.015)), [X, Y, Z], [0.015, 0.015, 0.015])
        hl += z - zb
        if off:
            links.append(abs(off))
    return sorted(p[0] for p in pts), hl, links


def _edge_joint(p, q, rect, cut):
    """Length of a board edge p → q that is a joint: zero on the outline, less what runs through a column."""
    x0, y0, x1, y1 = rect
    if (abs(p[0] - q[0]) < 1e-6 and min(abs(p[0] - x0), abs(p[0] - x1)) < 1e-6) or \
            (abs(p[1] - q[1]) < 1e-6 and min(abs(p[1] - y0), abs(p[1] - y1)) < 1e-6):
        return 0.0
    L = math.dist(p, q)
    for b in cut:   # the part inside a column box is no joint
        if abs(p[0] - q[0]) < 1e-6 and b[0] < p[0] < b[3]:
            L -= max(0.0, min(max(p[1], q[1]), b[4]) - max(min(p[1], q[1]), b[1]))
        elif abs(p[1] - q[1]) < 1e-6 and b[1] < p[1] < b[4]:
            L -= max(0.0, min(max(p[0], q[0]), b[3]) - max(min(p[0], q[0]), b[0]))
    return max(L, 0.0)


def _outline(rect, cut, sides=(0, 1, 2, 3)):
    """The wall-angle runs round a rect less the columns: [(p, q, into-the-room)] — rect sides (0 = y0, 1 = x1,
    2 = y1, 3 = x0) less where a column stands on them, plus each column's faces inside the rect."""
    x0, y0, x1, y1 = rect
    S = [((x0, y0), (x1, y0), (0, 1), 0), ((x1, y0), (x1, y1), (-1, 0), 1), ((x0, y1), (x1, y1), (0, -1), 0),
         ((x0, y0), (x0, y1), (1, 0), 1)]
    out = []
    for k in sides:
        p, q, inn, ax = S[k]
        blocks = [(b[ax], b[ax + 3]) for b in cut if (abs(b[1 - ax] - p[1 - ax]) < 1e-3 or abs(b[4 - ax] - p[1 - ax]) < 1e-3
                                                     or b[1 - ax] < p[1 - ax] < b[4 - ax])]
        for a, c in _runs(p[ax], q[ax], blocks, ax):
            pa, pc = list(p), list(p)
            pa[ax], pc[ax] = a, c
            out.append((tuple(pa), tuple(pc), inn))
    for b in cut:   # faces of a column standing into the room, the angle running round it
        for p, q, inn, ok in (((b[0], b[1]), (b[0], b[4]), (-1, 0), b[0] > x0 + 1e-4), ((b[3], b[1]), (b[3], b[4]), (1, 0), b[3] < x1 - 1e-4),
                              ((b[0], b[1]), (b[3], b[1]), (0, -1), b[1] > y0 + 1e-4), ((b[0], b[4]), (b[3], b[4]), (0, 1), b[4] < y1 - 1e-4)):
            if ok:
                p = (min(max(p[0], x0), x1), min(max(p[1], y0), y1))
                q = (min(max(q[0], x0), x1), min(max(q[1], y0), y1))
                if math.dist(p, q) > 0.01:
                    out.append((p, q, inn))
    return out


def _by_wall(x, rect, sides):
    """A main (along y) within 0.30 m of a wall-angle side parallel to it."""
    return (3 in sides and x - rect[0] <= 0.30) or (1 in sides and rect[2] - x <= 0.30)


def _grid(c, tag, rect, cut, zc, board, gap, bmat, btype, bspec, mats, sides=(0, 1, 2, 3), hatch=None):
    """One ceiling: boards bw (x) × bl (y) laid from the rect's x0/y0 corner with `gap` joints, cut round the
    columns; cross runners along x on the boards — one under every row joint, the rest evenly ≤ CEIL["cross"];
    mains along y over them evenly ≤ CEIL["main"]; wall angle on `sides`; hangers; screws (5 cm from the ends,
    @ 0.20, both board edges at a joint); joint length. Returns a summary."""
    galv, head = mats
    cut = list(cut) + ([hatch] if hatch else [])   # a service hatch is an opening like a column: trimmed round
    bw, bl, bt = board
    x0, y0, x1, y1 = rect
    w, hh, t = CEIL["cline"]
    bm, n_b, area, joints, rows = bmesh.new(), 0, 0.0, 0.0, []
    y = y0
    while y < y1 - 1e-6:
        ye = min(y + bl, y1)
        rows.append((y, ye))
        x = x0
        while x < x1 - 1e-6:
            xe = min(x + bw, x1)
            for p, q in (((x, y), (xe, y)), ((xe, y), (xe, ye)), ((x, ye), (xe, ye)), ((x, y), (x, ye))):
                joints += _edge_joint(p, q, rect, cut) / 2   # each joint is two boards' edges
            for r in _minus((x, y, xe, ye), cut):   # round the columns
                rq = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
                _slab(bm, rq, zc, zc + bt)
                area += _area(rq)
            n_b += 1
            x = xe + gap
        y = ye + gap
    o = _obj(c, f"CL_{tag}_Boards", bm, bmat, element="ceiling", type=btype, th=bspec, count=n_b, sheet=bw * bl,
             waste=CEIL["waste"], area=area, z=zc)
    # cross runners: at the room edges, under each row joint, evenly between
    stops = [y0 + w / 2] + [(a[1] + b[0]) / 2 for a, b in zip(rows, rows[1:])] + [y1 - w / 2]
    ycs = []
    for a, b in zip(stops, stops[1:]):
        n = max(1, math.ceil((b - a) / CEIL["cross"] - 1e-9))
        ycs += [a + (b - a) * i / n for i in range(n)]
    ycs.append(stops[-1])
    joint_y = set(stops[1:-1])
    nxm = max(1, math.ceil((x1 - x0 - 0.30) / CEIL["main"] - 1e-9))
    xms = [x0 + 0.15 + k * (x1 - x0 - 0.30) / nxm for k in range(nxm + 1)]
    zr = zc + bt
    blk_x = lambda yy: [(b[0], b[3]) for b in cut if b[1] - w < yy < b[4] + w]
    blk_y = lambda xx: [(b[1], b[4]) for b in cut if b[0] - w < xx < b[3] + w]
    bm, lens, mains = bmesh.new(), [], []
    for yy in ycs:
        for a, b in _runs(x0, x1, blk_x(yy), 0):
            _cline(bm, (a, yy), (b, yy), zr)
            lens.append(b - a)
    for xx in xms:
        for a, b in _runs(y0, y1, blk_y(xx), 1):
            _cline(bm, (xx, a), (xx, b), zr + hh)
            lens.append(b - a)
            mains.append(((xx, a), (xx, b)))
    _obj(c, f"CL_{tag}_Runners", bm, galv, element="steel", type="CF1", th=SPEC["cline"], kg_m=CEIL_KG_M,
         stock=CEIL["stock"], joint=CEIL["lap"], swept=True, lens=lens)
    bm, alens = bmesh.new(), []   # wall angle: horizontal leg under the runners' ends, vertical leg up the plaster
    aw, at = CEIL["angle"]
    for p, q, inn in _outline(rect, cut, sides):
        P, Q, I = Vector((*p, 0)), Vector((*q, 0)), Vector((*inn, 0))
        d = (Q - P).normalized()
        prism(bm, strip([(aw, 0.0), (0.0, 0.0), (0.0, aw)], at), 0.0, (Q - P).length,
              lambda u, a, zz, P=P, d=d, I=I: tuple(P + Vector((0, 0, zr)) + d * u + I * a + Vector((0, 0, zz))))
        alens.append((Q - P).length)
    _obj(c, f"CL_{tag}_WallAngle", bm, galv, element="steel", type="CF2", th=SPEC["angle"], kg_m=0.12,
         stock=CEIL["stock"], joint=CEIL["lap"], swept=True, lens=alens)
    bm, n_h, hl, links = bmesh.new(), 0, 0.0, []
    sp, tp = bmesh.new(), bmesh.new()
    for p, q in mains:
        if _by_wall(p[0], rect, sides):   # carried at the wall angle through the cross runners: no hangers (assumed)
            continue
        ts, l_, lk = _hangers_along(bm, p, q, zr + 2 * hh, tag, (sp, tp))
        n_h += len(ts)
        hl += l_
        links += lk
    _obj(c, f"CL_{tag}_Hangers", bm, galv, element="piece", type="CF3", th=SPEC["rod"], count=n_h, length=hl,
         links=len(links), link_len=sum(links))
    _obj(c, f"CL_{tag}_Springs", sp, galv, element="piece", type="CF6", th=SPEC["spring"], count=n_h)
    _obj(c, f"CL_{tag}_RodTops", tp, galv, element="piece", type="CF7", th=SPEC["top"], count=n_h)
    bm, n_c = bmesh.new(), 0   # a C-line clip at every crossing of a main over a cross runner
    covers = lambda segs, v: any(a < v < b for a, b in segs)
    for xx in xms:
        main_segs = _runs(y0, y1, blk_y(xx), 1)
        for yy in ycs:
            if covers(main_segs, yy) and covers(_runs(x0, x1, blk_x(yy), 0), xx):
                _cuboid(bm, Vector((xx, yy, zr + hh + 0.001)), [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))],
                        [w / 2 + 0.002, 0.010, 0.001])
                n_c += 1
    _obj(c, f"CL_{tag}_Clips", bm, galv, element="piece", type="CF5", th=SPEC["clip"], count=n_c)
    if hatch:   # the hatch: an aluminium frame flush under the ceiling and a 9 mm board lid in it
        hx0, hy0, _, hx1, hy1, _ = hatch
        bm = bmesh.new()
        X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
        cx, cy, fw = (hx0 + hx1) / 2, (hy0 + hy1) / 2, 0.02
        for ctr, half in (((cx, hy0 + fw / 2), (CEIL["hatch"] / 2, fw / 2)), ((cx, hy1 - fw / 2), (CEIL["hatch"] / 2, fw / 2)),
                          ((hx0 + fw / 2, cy), (fw / 2, CEIL["hatch"] / 2 - fw)), ((hx1 - fw / 2, cy), (fw / 2, CEIL["hatch"] / 2 - fw))):
            _cuboid(bm, Vector((*ctr, zc + bt / 2)), [X, Y, Z], [half[0], half[1], bt / 2 + 0.001])
        _cuboid(bm, Vector((cx, cy, zc + bt / 2)), [X, Y, Z], [CEIL["hatch"] / 2 - fw - 0.001, CEIL["hatch"] / 2 - fw - 0.001, bt / 2])
        _obj(c, f"CL_{tag}_Hatch", bm, bmat, element="piece", type="CH1", th=SPEC["hatch"], count=1,
             rect=[hx0, hy0, hx1, hy1])
    bm, n_s = bmesh.new(), 0   # screws along every cross runner, per board
    for yy in ycs:
        rows_y = [yy - gap / 2 - CEIL["screw_edge"], yy + gap / 2 + CEIL["screw_edge"]] if yy in joint_y else [yy]
        for ry in rows_y:
            xb = x0
            while xb < x1 - 1e-6:
                xe = min(xb + bw, x1)
                k = xb + CEIL["screw_end"]
                while k <= xe - CEIL["screw_end"] + 1e-6:
                    if not any(b[0] - 0.01 < k < b[3] + 0.01 and b[1] - 0.01 < ry < b[4] + 0.01 for b in cut):
                        _disc(bm, Vector((k, ry, zc)), Vector((0, 0, -1)))
                        n_s += 1
                    k += CEIL["screw"]
                xb = xe + gap
    _obj(c, f"CL_{tag}_Screws", bm, head, element="piece", type="CF4", th=SPEC["screw"], count=n_s)
    _joint_obj(c, f"CL_{tag}_Joints", joints, "CJ2" if gap else "CJ3" if btype == "CB4" else "CJ1",
               SPEC["seal"] if gap else SPEC["tape_fc"] if btype == "CB4" else SPEC["tape"])
    return dict(area=round(area, 2), boards=n_b, runs=len(lens), hangers=n_h, links=len(links), screws=n_s,
                joints=round(joints, 2))


def build_ceilings():
    """Every room ceiling and the eave soffit + porch ceiling (frame, hangers, screws, joints, boards)."""
    c = _clear(C_CEIL)
    gyp = mat("M_Gypsum", (0.92, 0.92, 0.90), 0.8)
    smart = mat("M_Smartboard_Vent", (0.90, 0.90, 0.88), 0.7)
    galv = mat("M_Steel_Galv", (0.62, 0.64, 0.66), 0.35, 0.9)
    head = mat("M_Screw", (0.75, 0.76, 0.78), 0.3, 0.9)
    out = {}
    for room, (seed, kind) in ROOMS.items():
        zc = (FL_BATH + CEIL["h_bath"]) if kind == "mr" else (FL + CEIL["h"])
        rect = _room_rect(seed, zc + 0.05)
        h_ = None
        if room == HATCH_ROOM:   # the user: one 60 × 60 service hatch, at the middle of the living room
            (cx, cy), a = HATCH_AT, CEIL["hatch"] / 2
            h_ = (cx - a, cy - a, 0.0, cx + a, cy + a, 0.0)
        out[room] = _grid(c, room, rect, _intruders(rect, zc + 0.05), zc, CEIL["board"], 0.0, gyp,
                          "CB2" if kind == "mr" else "CB1", SPEC[kind], (galv, head), hatch=h_)
    zs = _soffit_z()
    f = COL["b"] / 2 + WALL["pl"]
    pr = (GX["2"] + f, GY["A"] - f, GX["3"] + f, GY["B"] - f)   # porch: A2-E2 face, B2-B3 face, the wall lines
    cols = _intruders(pr, zs + 0.05)
    SW, SL, ST = CEIL["soffit"]
    out["Porch"] = _grid(c, "Porch", pr, cols, zs, (SW, SL, ST), 0.0, smart, "CB4", SPEC["flat"], (galv, head),   # smooth like inside (the user)
                         sides=(2, 3))
    out["Soffit"] = _build_soffit(c, smart, galv, head, zs)
    return out


def _joint_obj(c, name, L, typ, th):
    """A take-off row for board joints (tape + compound, or sealant): an empty mesh carrying the length."""
    bm = bmesh.new()
    o = _obj(c, name, bm, mat("M_Gypsum", (0.92, 0.92, 0.90), 0.8), element="joint", type=typ, th=th, length=L)
    o.hide_viewport = o.hide_render = True
    return o


def _soffit_z():
    """Soffit underside: 1" over the fascia bottom (manual p.7); the 8" fascia hangs from the rafter tops."""
    s0 = _geom()[1][0]
    return _zr(s0, -BACK) - FASCIA["b8"][0] + CEIL["above_fascia"]


def _soffit_frame():
    """Per eave: (a, e, w, depth, L) — the fascia-back line start a, along e, inward w, wall-face depth, length."""
    xs, ys = sorted(GX.values()), sorted(GY.values())
    back = FACE + ROOF["eave"] - BACK + FASCIA["angle"][1]   # the 8" board's back from the grid
    f = COL["b"] / 2 + WALL["pl"]
    O = [(xs[0] - back, ys[0] - back), (xs[-1] + back, ys[0] - back), (xs[-1] + back, ys[-1] + back), (xs[0] - back, ys[-1] + back)]
    out = []
    for k in range(4):
        a, b = Vector(O[k]), Vector(O[(k + 1) % 4])
        e = (b - a).normalized()
        out.append((a, e, Vector((-e.y, e.x)), back - f, (b - a).length))
    return out


def _build_soffit(c, smart, galv, head, zs):
    """Eave soffit round the house: per eave a trapezoid from the fascia back (v = 0) to the plaster face line
    (v = depth), 45° at the corners (at v it spans u ∈ [v, L − v]); a full 0.60 board at the wall, a strip at the
    fascia; runners along at the fascia, the 0.60 joint and the wall; short cross pieces cut in between them on the
    same level, under every board end joint and evenly ≤ 0.40 between; hangers along the joint runner; screws 1.2 cm
    off each board edge @ 0.20."""
    SW, SL, ST = CEIL["soffit"]
    g = CEIL["gap"]
    w_, hh, t = CEIL["cline"]
    zr = zs + ST
    bm, pieces, area, joints, slot_area = bmesh.new(), 0, 0.0, 0.0, 0.0
    fr, rb, sb, hb = bmesh.new(), [], bmesh.new(), bmesh.new()
    sp, tp = bmesh.new(), bmesh.new()
    n_s, n_h, hl, links = 0, 0, 0.0, []
    pt = lambda a, e, w, u, v: tuple(a + e * u + w * v)
    for a, e, w, depth, L in _soffit_frame():
        trap = [pt(a, e, w, 0, 0), pt(a, e, w, L, 0), pt(a, e, w, L - depth, depth), pt(a, e, w, depth, depth)]
        vj = depth - SW - g / 2   # the long joint between the wall board and the strip
        for v0, v1 in ((vj + g / 2, depth), (0.0, vj - g / 2)):
            u = 0.0
            while u < L - 1e-6:
                q = [pt(a, e, w, uu, vv) for uu, vv in ((u, v0), (min(u + SL, L), v0), (min(u + SL, L), v1), (u, v1))]
                for p0, p1 in zip(trap, trap[1:] + trap[:1]):
                    q = _clip(q, p0, p1)
                if len(q) >= 3 and _area(q) > 1e-4:
                    # the wall board is the vented model: 3 grooves 3" apart in its fascia-side half (slots 25 cm,
                    # 5 cm bridges, 6 mm wide; slot sizes are not printed); the strip at the fascia is plain
                    slots = []
                    if v0 > vj:
                        for kk in (1, 2, 3):
                            vk, su = v0 + 0.0762 * kk, u + 0.05
                            while su + 0.10 < min(u + SL, L) - 0.05:
                                slots.append((su, vk - 0.003, 0, min(su + 0.25, min(u + SL, L) - 0.05), vk + 0.003, 0))
                                su += 0.30
                    kept = 0.0
                    for r in _minus((u, v0, min(u + SL, L), v1), slots):
                        rq = [pt(a, e, w, uu, vv) for uu, vv in ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3]))]
                        for p0, p1 in zip(trap, trap[1:] + trap[:1]):
                            rq = _clip(rq, p0, p1)
                        if len(rq) >= 3 and _area(rq) > 1e-6:
                            _slab(bm, rq, zs, zs + ST)
                            kept += _area(rq)
                    area += _area(q)
                    slot_area += _area(q) - kept
                    pieces += 1
                    for p0, p1 in zip(q, q[1:] + q[:1]):   # joints: every edge not on the fascia or the wall line
                        v_ = [(Vector(p) - a).dot(w) for p in (p0, p1)]
                        if not (all(abs(x) < 1e-5 for x in v_) or all(abs(x - depth) < 1e-5 for x in v_)):
                            joints += math.dist(p0, p1) / 2
                u += SL + g
        # runners along the eave: at the fascia, the joint, the wall — each stops at the corner diagonals
        for vv in (w_ / 2, vj, depth - w_ / 2):
            _cline(fr, pt(a, e, w, vv, vv), pt(a, e, w, L - vv, vv), zr)
            rb.append(L - 2 * vv)
            if abs(vv - vj) < 1e-9:   # hangers along the joint runner, two screw rows on it
                ts, l_, lk = _hangers_along(hb, pt(a, e, w, vv, vv), pt(a, e, w, L - vv, vv), zr + hh, "Soffit", (sp, tp))   # one level
                n_h += len(ts)
                hl += l_
                links += lk
            rows = [vv - g / 2 - CEIL["screw_edge"], vv + g / 2 + CEIL["screw_edge"]] if abs(vv - vj) < 1e-9 else [vv]
            for rv in rows:
                k = rv + CEIL["screw_end"]
                while k <= L - rv - CEIL["screw_end"]:
                    _disc(sb, Vector((*pt(a, e, w, k, rv), zs)), Vector((0, 0, -1)))
                    n_s += 1
                    k += CEIL["screw"]
        # cross runners: under every board end joint, then evenly ≤ 0.40 between; each spans to the diagonals
        ends = [k * (SL + g) - g / 2 for k in range(1, math.ceil(L / (SL + g)))]
        stops = [0.0] + ends + [L]
        us = []
        for p_, q_ in zip(stops, stops[1:]):
            n = max(1, math.ceil((q_ - p_) / CEIL["cross"] - 1e-9))
            us += [p_ + (q_ - p_) * i / n for i in range(1, n)]
        for u in us + ends:   # short pieces cut in between the runners along, on the boards' backs (one level)
            for lo_, hi_ in ((w_, vj - w_ / 2), (vj + w_ / 2, depth - w_)):
                hi_ = min(hi_, u, L - u)   # the corner diagonals
                if hi_ - lo_ > 0.05:
                    _cline(fr, pt(a, e, w, u, lo_), pt(a, e, w, u, hi_), zr)
                    rb.append(hi_ - lo_)
                    if u in ends:   # both board ends screwed on it
                        for du in (-g / 2 - CEIL["screw_edge"], g / 2 + CEIL["screw_edge"]):
                            k = lo_ + CEIL["screw_end"]
                            while k <= hi_ - CEIL["screw_end"] + 1e-6:
                                _disc(sb, Vector((*pt(a, e, w, u + du, k), zs)), Vector((0, 0, -1)))
                                n_s += 1
                                k += CEIL["screw"]
    _obj(c, "CL_Soffit_Boards", bm, smart, element="ceiling", type="CB3", th=SPEC["vent"], sheet=SW * SL,
         waste=CEIL["waste"], count=pieces, area=area, z=zs, slots=slot_area)
    _obj(c, "CL_Soffit_Runners", fr, galv, element="steel", type="CF1", th=SPEC["cline"], kg_m=CEIL_KG_M,
         stock=CEIL["stock"], joint=CEIL["lap"], swept=True, lens=rb)
    _obj(c, "CL_Soffit_Hangers", hb, galv, element="piece", type="CF3", th=SPEC["rod"], count=n_h, length=hl,
         links=len(links), link_len=sum(links))
    _obj(c, "CL_Soffit_Screws", sb, head, element="piece", type="CF4", th=SPEC["screw"], count=n_s)
    _obj(c, "CL_Soffit_Springs", sp, galv, element="piece", type="CF6", th=SPEC["spring"], count=n_h)
    _obj(c, "CL_Soffit_RodTops", tp, galv, element="piece", type="CF7", th=SPEC["top"], count=n_h)
    joints += (GX["3"] - GX["2"]) + (GY["B"] - GY["A"])   # where the porch ceiling meets the soffit (2 open sides)
    _joint_obj(c, "CL_Soffit_Joints", joints, "CJ2", SPEC["seal"])
    return dict(area=round(area, 2), boards=pieces, runs=len(rb), hangers=n_h, links=len(links), screws=n_s,
                joints=round(joints, 2))


def _islands(o):
    """World vertex lists of each separate piece of a mesh object."""
    bm = _world_bm(o)
    left, out = set(bm.faces), []
    while left:
        f0 = left.pop()
        grp, stack = {f0}, [f0]
        while stack:
            for e in stack.pop().edges:
                for g in e.link_faces:
                    if g in left:
                        left.discard(g)
                        grp.add(g)
                        stack.append(g)
        out.append(([v.co.copy() for v in {v for f in grp for v in f.verts}],
                    sum(f.calc_area() for f in grp if f.normal.z < -0.99)))
    bm.free()
    return out




def _floor_z(p):
    """Finished floor under plan point p, read from the model: the slab top straight below + the 3 cm tiles."""
    dg = bpy.context.evaluated_depsgraph_get()
    q = Vector((*p, 2.0))
    for _ in range(20):   # through later finishes (tiles, screed: ST11) down to the slab
        ok, loc, _, _, ob, _ = bpy.context.scene.ray_cast(dg, q, Vector((0, 0, -1)))
        ct = globals().get("C_TILE")   # ST11 loaded later, or not at all
        if not (ok and ct in bpy.data.collections and ob.name in bpy.data.collections[ct].objects):
            break
        q = loc - Vector((0, 0, 1e-5))
    assert ok and ob.name in bpy.data.collections[C_SLAB].objects, f"no slab under {p} ({ob.name if ok else None})"
    return loc.z + 0.03


def _check_grid(tag, rect, zc, board, steel, gap, sides=(0, 1, 2, 3)):
    """Boards, runners and hangers of one _grid ceiling against its outline, the manual and the roof steel."""
    bw, bl, bt = board
    x0, y0, x1, y1 = rect
    pcs = _islands(bpy.data.objects[f"CL_{tag}_Boards"])
    assert abs(min(v.z for vs, _ in pcs for v in vs) - zc) < 1e-3, f"{tag}: boards not at {zc:.3f}"
    for vs, _ in pcs:
        a, b = sorted((max(v.x for v in vs) - min(v.x for v in vs), max(v.y for v in vs) - min(v.y for v in vs)))
        assert a <= min(bw, bl) + 1e-4 and b <= max(bw, bl) + 1e-4, f"{tag}: a piece {a:.2f} × {b:.2f} bigger than a sheet"
        assert all(x0 - 1e-4 <= v.x <= x1 + 1e-4 and y0 - 1e-4 <= v.y <= y1 + 1e-4 for v in vs), f"{tag}: a board past its outline"
    zr = zc + bt
    ycs, mains = set(), []
    for vs, _ in _islands(bpy.data.objects[f"CL_{tag}_Runners"]):
        dx = max(v.x for v in vs) - min(v.x for v in vs)
        dy = max(v.y for v in vs) - min(v.y for v in vs)
        if dx > dy:
            assert abs(min(v.z for v in vs) - zr) < 1e-3, f"{tag}: a cross runner off the boards"
            ycs.add(round(sum(v.y for v in vs) / len(vs), 3))
        else:
            assert abs(min(v.z for v in vs) - zr - CEIL["cline"][1]) < 1e-3, f"{tag}: a main off the cross runners"
            mains.append((sum(v.x for v in vs) / len(vs), min(v.y for v in vs), max(v.y for v in vs)))
    crossings = 0   # a C-line clip at every main over a cross runner (plan boxes of the runs overlapping)
    runs_ = [(min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs))
             for vs, _ in _islands(bpy.data.objects[f"CL_{tag}_Runners"])]
    cr = [r for r in runs_ if r[1] - r[0] > r[3] - r[2]]
    mn = [r for r in runs_ if r[1] - r[0] <= r[3] - r[2]]
    for a in mn:
        for b in cr:
            if a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]:
                crossings += 1
    clips = bpy.data.objects[f"CL_{tag}_Clips"]
    assert clips.data["count"] == crossings == len(_islands(clips)), f"{tag}: {clips.data['count']} clips for {crossings} crossings"
    ycs = sorted(ycs)
    xms = sorted({round(m[0], 3) for m in mains})
    assert max(b - a for a, b in zip(ycs, ycs[1:])) <= CEIL["cross"] + 0.002, f"{tag}: cross runners over {CEIL['cross']} apart"
    assert max(b - a for a, b in zip(xms, xms[1:])) <= CEIL["main"] + 0.002, f"{tag}: mains over {CEIL['main']} apart"
    hv = _islands(bpy.data.objects[f"CL_{tag}_Hangers"])
    hs = []
    for vs, _ in hv:
        top, foot = max(v.z for v in vs), min(v.z for v in vs)
        p = (sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs))
        loc = steel.ray_cast(Vector((*p, top - 0.003)), Vector((0, 0, 1)))[0]   # the roof steel only
        assert loc is not None and abs(loc.z - top) < 1e-3, f"{tag}: hanger at {p[0]:.2f}, {p[1]:.2f} not on steel"
        assert abs(foot - (zr + 2 * CEIL["cline"][1])) < 1e-4, f"{tag}: hanger foot off the mains"
        hs.append(p)
    for x, a, b in mains:   # along each main: ends ≤ hang_end, gaps ≤ hang (sideways links ≤ 0.5 m)
        if _by_wall(x, rect, sides):
            continue
        ys = sorted(p[1] for p in hs if abs(p[0] - x) <= 0.5 + 1e-3 and a - 1e-3 <= p[1] <= b + 1e-3)
        assert ys and ys[0] - a <= CEIL["hang_end"] + 0.05 and b - ys[-1] <= CEIL["hang_end"] + 0.05, f"{tag}: main at x {x:.2f} hangers too far from its ends"
        assert all(q - p <= CEIL["hang"] + 0.05 for p, q in zip(ys, ys[1:])), f"{tag}: main at x {x:.2f} hangers over {CEIL['hang']} m apart"
    return sum(a for _, a in pcs)


def selfcheck_ceilings():
    """Ceilings against the user's spec and the SCG manual, read from the model: each ceiling's height from the floor
    under it, boards within their outline and no bigger than a sheet, board area = plaster-face rectangle − columns,
    runner spacings, hangers on roof steel at ≤ 1.00 m, the soffit 1" over the fascia bottom spanning plaster face →
    fascia back on every eave with its runners inside the eave."""
    from mathutils.bvhtree import BVHTree
    sb = bmesh.new()   # the members a hanger may hang from: rafters, hips, ridge, posts, wall plates
    for o in list(bpy.data.collections[C_ROOF].objects) + list(bpy.data.collections[C_WALL].objects):
        if o.type == "MESH" and (o.name.startswith(("RF_Rafter", "RF_Hip", "RF_Ridge", "RF_Post")) or o.name.endswith("_2C")):
            m = o.data.copy()
            m.transform(o.matrix_world)
            sb.from_mesh(m)
            bpy.data.meshes.remove(m)
    steel = BVHTree.FromBMesh(sb)
    sb.free()
    out = []
    for room, (seed, kind) in ROOMS.items():
        h = CEIL["h_bath"] if kind == "mr" else CEIL["h"]   # the user: 2.80 / bath 2.60 from its own floor
        zc = _floor_z(seed) + h
        o = bpy.data.objects[f"CL_{room}_Boards"]
        assert o.data["type"] == ("CB2" if kind == "mr" else "CB1"), f"{room}: wrong board ({o.data['th']})"
        rect = _room_rect(seed, zc + 0.05)   # the plaster faces, read again from the walls
        got = _check_grid(room, rect, zc, CEIL["board"], steel, 0.0)
        x0, y0, x1, y1 = rect
        net = (x1 - x0) * (y1 - y0) - sum((min(b[3], x1) - max(b[0], x0)) * (min(b[4], y1) - max(b[1], y0))
                                          for b in _intruders(rect, zc + 0.05))
        if room == HATCH_ROOM:   # the service hatch: present, 60 × 60, and no board over it
            ho = bpy.data.objects.get(f"CL_{room}_Hatch")
            assert ho, f"{room}: no service hatch"
            hv = _verts(ho)   # measured from the hatch mesh, not the rect it was built from
            hx0, hy0, hx1, hy1 = min(v.x for v in hv), min(v.y for v in hv), max(v.x for v in hv), max(v.y for v in hv)
            assert abs(hx1 - hx0 - CEIL["hatch"]) < 1e-3 and abs(hy1 - hy0 - CEIL["hatch"]) < 1e-3, "hatch not 60 × 60"
            for vs, _ in _islands(bpy.data.objects[f"CL_{room}_Boards"]):   # no board overlapping the opening
                ov = max(0.0, min(max(v.x for v in vs), hx1) - max(min(v.x for v in vs), hx0)) * \
                    max(0.0, min(max(v.y for v in vs), hy1) - max(min(v.y for v in vs), hy0))
                assert ov < 1e-6, "a board over the hatch"
            net -= (hx1 - hx0) * (hy1 - hy0)
        assert abs(got - net) < 0.005 and abs(o.data["area"] - got) < 0.005, f"{room}: boards {got:.3f} m², room net {net:.3f}"
        out.append(f"{room} {got:.2f} m²")
    # soffit + porch: 1" over the fascia bottom, measured on every eave's 8" board
    zs = min(v.z for vs, _ in _islands(bpy.data.objects["CL_Soffit_Boards"]) for v in vs)
    E, sides, D, ze = _geom()
    f = COL["b"] / 2 + WALL["pl"]
    SW, SL, ST = CEIL["soffit"]
    so = _islands(bpy.data.objects["CL_Soffit_Boards"])
    # The user: vents all round, the porch eave and the outer corners too — slotted boards fall apart into many islands
    # (≥ 3 per slot); count them in the first and last 1.2 m of each eave, so one flat eave at a corner shows
    for a, e, w, depth, L in _soffit_frame():
        uv = [((Vector((sum(v.x for v in vs), sum(v.y for v in vs))) / len(vs) - a).dot(e),
               (Vector((sum(v.x for v in vs), sum(v.y for v in vs))) / len(vs) - a).dot(w)) for vs, _ in so]
        uv = [(u, v) for u, v in uv if 0 <= v <= depth and v <= u <= L - v]
        for lo, hi in ((0, 1.2), (L - 1.2, L)):
            n_ = sum(1 for u, v in uv if lo <= u <= hi)
            assert n_ >= 6, f"soffit eave from {tuple(round(x, 2) for x in a)}: {n_} pieces at u {lo:.1f}–{hi:.1f}, vents missing"
    for vs, _ in so:
        a, b = sorted((max(v.x for v in vs) - min(v.x for v in vs), max(v.y for v in vs) - min(v.y for v in vs)))
        assert a <= SW + 1e-4 and b <= SL + 1e-4, f"soffit piece {a:.2f} × {b:.2f} bigger than a board"
    sv = [v for vs, _ in so for v in vs]
    xs, ys = sorted(GX.values()), sorted(GY.values())
    for k, s in enumerate(sides):
        out_ = -s["w"]
        b8 = _verts(bpy.data.objects[f"FA_B8_{k + 1}"])
        mid = [v for v in sv if abs((v - s["Q0"]).dot(s["e"]) - s["L"] / 2) < 1.0 and (v - s["Q0"]).dot(s["w"]) < 1.5]
        zk = min(v.z for v in mid)   # this eave's soffit
        assert abs(zk - min(v.z for v in b8) - CEIL["above_fascia"]) < 1e-3, f"soffit {(zk - min(v.z for v in b8)) * 100:.1f} cm over fascia {k + 1}"
        reach = max(v.dot(out_) for v in mid)
        assert abs(reach - min(v.dot(out_) for v in b8)) < 2e-3, f"soffit {k + 1}: {(min(v.dot(out_) for v in b8) - reach) * 1000:.1f} mm off the fascia back"
        wall = max(Vector((x, y, 0)).dot(out_) for x in xs for y in ys) + f
        inner = min(v.dot(out_) for v in mid)
        assert abs(inner - wall) < 2e-3, f"soffit {k + 1}: stops {(inner - wall) * 1000:.1f} mm off the plaster face"
    pr = (GX["2"] + f, GY["A"] - f, GX["3"] + f, GY["B"] - f)
    got = _check_grid("Porch", pr, zs, (SW, SL, ST), steel, 0.0, sides=(2, 3))
    assert bpy.data.objects["CL_Porch_Joints"].data["type"] == "CJ3", "porch: open joints, not filled smooth (the user)"
    assert bpy.data.objects["CL_Porch_Boards"].data["type"] == "CB4", "porch: not the flat Smartboard (the user)"
    assert bpy.data.objects["CL_Soffit_Boards"].data["type"] == "CB3", "soffit: not the vented Smartboard (the user)"
    for o in bpy.data.collections[C_CEIL].objects:   # a spring joiner and a top angle on every hanger
        if o.name.endswith("_Hangers"):
            t_ = o.name[:-len("_Hangers")]
            n_ = o.data["count"]
            assert len(_islands(o)) == n_, f"{o.name}: {len(_islands(o))} rods drawn, count {n_}"
            for part in ("_Springs", "_RodTops"):
                assert bpy.data.objects[t_ + part].data["count"] == n_ and len(_islands(bpy.data.objects[t_ + part])) == n_, f"{t_ + part} ≠ hangers"
    def inside(v, fr):
        a, e, w, depth, L = fr
        u, vv = (Vector((v.x, v.y)) - a).dot(e), (Vector((v.x, v.y)) - a).dot(w)
        return -0.02 <= vv <= depth + 0.02 and vv - 0.02 <= u <= L - vv + 0.02
    for vs, _ in _islands(bpy.data.objects["CL_Soffit_Runners"]):   # every soffit runner wholly in one eave
        assert any(all(inside(v, fr) for v in vs) for fr in _soffit_frame()), \
            f"a soffit runner leaves its eave near {vs[0].x:.2f}, {vs[0].y:.2f}"
    for vs, _ in _islands(bpy.data.objects["CL_Soffit_Runners"]):   # and on the boards' backs (one level)
        assert abs(min(v.z for v in vs) - zs - CEIL["soffit"][2]) < 1e-3, "a soffit runner off the boards"
    drawn = sum(a for _, a in so)
    slots = bpy.data.objects["CL_Soffit_Boards"].data["slots"]
    gross = bpy.data.objects["CL_Soffit_Boards"].data["area"]
    assert abs(gross - drawn - slots) < 1e-3, "soffit: gross ≠ drawn + vent slots"
    return ("ceilings ok: " + " · ".join(out) + f" · soffit {drawn + slots:.2f} m² gross ({slots:.2f} vent slots) + porch "
            f"{got:.2f} m², 1\" over the fascia bottom")
