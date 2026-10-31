"""SCG CPAC concrete trim pieces (ชุดครอบหลังคา เอสซีจี, catalog p.4) as real solids, one bmesh per piece.

Sizes W × L × H cm from SCG dealer pages (scg-towiwat / SCG HOME, 29 ต.ค.69); weights from onestockhome. Wall
thickness 13 mm is back-calculated from the ridge cap's 3.0 kg (25 × 33 × 10 arch, concrete ~2,100 kg/m³);
selftest() checks every piece's volume × RHO against its catalogue weight (±30 %, the pages disagree up to 25 %).

Local frame of every piece: x along the line it covers (0 = low/tail end, laid so the next piece's tail laps over
this one's head), y across, z up; the skirt bottoms are on z = 0, centred on y = 0.

    exec(open(<this file>).read())
    bm = bmesh.new(); PIECES["ridge"](bm); ...      # or build(bm, "hip_end")
    print(caps_selftest())
"""
import math
import bmesh

RHO_C = 2100.0   # kg/m³, concrete tile (fits the ridge cap's 3.0 kg at t = 13 mm)
T = 0.013
# key: (Thai name, W, L, H, kg, laid cover per piece or None for one per point)
CAPS = {
    "ridge":     ("ครอบสันโค้ง", 0.25, 0.33, 0.10, 3.0, 1 / 3.3),
    "gable_end": ("ครอบโค้งปิดจั่ว", 0.22, 0.33, 0.22, 4.8, None),
    "barge":     ("ครอบข้าง", 0.18, 0.36, 0.095, 3.1, 1 / 3.0),   # size not published: as the barge end, 3 /m
    "barge_end": ("ครอบข้างปิดชาย", 0.18, 0.345, 0.095, 2.9, None),
    "hip_end":   ("ครอบโค้งหางมน", 0.21, 0.36, 0.13, 4.0, None),
    "two_way":   ("ครอบโค้งสองทาง", 0.25, 0.33, 0.10, 3.5, None),
    "three_way": ("ครอบโค้งสามทาง", 0.37, 0.415, 0.14, 5.1, None),
    "four_way":  ("ครอบโค้งสี่ทาง", 0.36, 0.36, 0.14, 6.4, None),
}
HEAD = 0.027   # spigot at the head under the next piece's tail: 33 cm − 1/3.3 m cover (catalogue 3.3 /m)


def arch(w, h, t=T, n=14, base=0.0, fall=0.0):
    """Strip outline (prism() convention) of a half-elliptic arch w wide, h high, skirts t thick on z = base.
    fall = tan of the tiles' fall across the line: the skirt feet are bevelled to it (inner corner t · fall higher),
    so a cap lowered by w/2 · fall rests on the tiles along its whole foot."""
    a, b = w / 2, h
    out = [(a * math.cos(math.pi * i / n), base + b * math.sin(math.pi * i / n)) for i in range(n + 1)]
    inn = [((a - t) * math.cos(math.pi * i / n), base + (b - t) * math.sin(math.pi * i / n)) for i in range(n, -1, -1)]
    inn[0] = (inn[0][0], inn[0][1] + t * fall)
    inn[-1] = (inn[-1][0], inn[-1][1] + t * fall)
    return out + inn


def loft(bm, rings, place, cap0=True, cap1=True):
    """Join strip outlines rings = [(x, outline)] (same point count) into one solid; caps are quads between the
    outer and inner halves (prism() rule: a fan over the concave outline would fill the hollow)."""
    import bmesh
    n = len(rings[0][1])
    R = [[bm.verts.new(place(x, s, z)) for s, z in poly] for x, poly in rings]
    for r0, r1 in zip(R, R[1:]):
        for i in range(n):
            bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    for r, on, flip in ((R[0], cap0, True), (R[-1], cap1, False)):
        if on:
            for i in range(n // 2 - 1):
                q = (r[i], r[i + 1], r[n - 2 - i], r[n - 1 - i])
                bm.faces.new(q[::-1] if flip else q)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def _id(x, s, z):
    return (x, s, z)


def ridge(bm, place=_id, key="ridge", L=None, fall=0.0):
    """ครอบสันโค้ง: arch, plain tail at x = 0, a 7 mm spigot at the head that fits inside the next piece's tail."""
    _, W, L0, H, _, _ = CAPS[key]
    L = L0 if L is None else L
    h0 = L - HEAD
    big, small = arch(W, H, fall=fall), arch(W - 2 * T - 0.002, H - T - 0.001, T - 0.006, base=(T + 0.001) * fall, fall=fall)
    rings = [(0.0, big), (h0, big), (h0, small), (L, small)]
    loft(bm, rings, place)


def two_way(bm, place=_id, fall=0.0):
    """ครอบโค้งสองทาง: sockets (bells 8 mm proud) at both ends, the ridge caps from either gable slide in."""
    _, W, L, H, _, _ = CAPS["two_way"]
    big, mid = arch(W + 0.016, H + 0.008, T, base=-0.008 * fall, fall=fall), arch(W, H, fall=fall)
    loft(bm, [(0.0, big), (0.05, big), (0.05, mid), (L - 0.05, mid), (L - 0.05, big), (L, big)], place)


def hip_end(bm, place=_id, fall=0.0):
    """ครอบโค้งหางมน: hip arch whose tail rolls down into a rounded closed nose at x = 0 (the eave corner).
    fall = tan of the tiles' fall across the hip: the narrower nose rings sit that much higher, so every skirt
    rests on the tiles (placed with the full-width drop W/2 · fall)."""
    _, W, L, H, _, _ = CAPS["hip_end"]
    nose = 0.10
    rings = []
    for k in range(9):   # nose: quarter-ellipse in x, the arch shrinks to a small lip
        f = math.sin(math.pi / 2 * k / 8)
        w = W * (0.55 + 0.45 * f)
        rings.append((nose * (1 - math.cos(math.pi / 2 * k / 8)), arch(w, H * (0.35 + 0.65 * f), base=(W - w) / 2 * fall, fall=fall)))
    small = arch(W - 2 * T - 0.002, H - T - 0.001, T - 0.006, base=(T + 0.001) * fall, fall=fall)
    rings += [(L - HEAD, arch(W, H, fall=fall)), (L - HEAD, small), (L, small)]
    loft(bm, rings, place)
    # the nose face: a solid end plate closing the small arch
    _plate(bm, rings[0][1], 0.0, place, T)


def _plate(bm, poly, x, place, t):
    """Close an arch end with a plate t thick from x - t to x (outer outline, filled; a convex arch fills cleanly)."""
    n = len(poly) // 2
    out = poly[:n]
    for x0, x1 in ((x - t, x),):
        a = [bm.verts.new(place(x0, s, z)) for s, z in out]
        b = [bm.verts.new(place(x1, s, z)) for s, z in out]
        bm.faces.new(a[::-1])
        bm.faces.new(b)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))


def gable_end(bm, place=_id):
    """ครอบโค้งปิดจั่ว: ridge arch with a decorative end disc (22 high) closing the gable end at x = 0."""
    _, W, L, H, _, _ = CAPS["gable_end"]
    _, Wr, _, Hr, _, _ = CAPS["ridge"]
    ridge(bm, place, "ridge", L)
    # end disc: the ridge arch outline (+5 mm) carried down to the full 22 cm, closing the gable apex (convex)
    disc = [((Wr / 2 + 0.005) * math.cos(math.pi * i / 16), (Hr + 0.005) * math.sin(math.pi * i / 16)) for i in range(17)]
    disc += [(-(Wr / 2 + 0.005), Hr - H), ((Wr / 2 + 0.005), Hr - H)]
    a = [bm.verts.new(place(-T, s, z)) for s, z in disc]
    b = [bm.verts.new(place(0.0, s, z)) for s, z in disc]
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    m = len(disc)
    for i in range(m):
        bm.faces.new((a[i], a[(i + 1) % m], b[(i + 1) % m], b[i]))


def _barge_section(W, H, t=T):
    """ครอบข้าง section: a rounded roll on the last tile (y > 0) turning down into a skirt over the barge (y < 0)."""
    r = H * 0.55
    pts = [(W - 0.02, 0.0)]
    for i in range(9):
        a = math.pi * i / 8
        pts.append((W / 2 - 0.01 + (W / 2 - 0.01) * math.cos(a) * 0.9, H - r + r * math.sin(a)))
    pts += [(0.0, H - r), (0.0, -0.06)]
    return strip_path(pts, t)


def strip_path(path, t):
    """Mitred thin outline along a centreline (same as steel_sections.strip)."""
    def off(k):
        out = []
        for i, p in enumerate(path):
            ns = []
            for a, b in [(path[j], path[j + 1]) for j in (i - 1, i) if 0 <= j < len(path) - 1]:
                dx, dz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dz)
                ns.append((-dz / L, dx / L))
            nx, nz = sum(v[0] for v in ns), sum(v[1] for v in ns)
            m = math.hypot(nx, nz)
            nx, nz = nx / m, nz / m
            c = nx * ns[0][0] + nz * ns[0][1]
            out.append((p[0] + k * nx / c, p[1] + k * nz / c))
        return out
    return off(t / 2) + off(-t / 2)[::-1]


def barge(bm, place=_id, key="barge"):
    """ครอบข้าง: roll + skirt, spigot head as the ridge cap."""
    _, W, L, H, _, _ = CAPS[key]
    sec = _barge_section(W, H)
    small = _barge_section(W - 0.010, H - 0.006, T - 0.006)
    loft(bm, [(0.0, sec), (L - HEAD, sec), (L - HEAD, small), (L, small)], place)


def barge_end(bm, place=_id):
    """ครอบข้างปิดชาย: the barge cap with its tail closed by an end plate (the eave end of the verge)."""
    _, W, L, H, _, _ = CAPS["barge_end"]
    sec = _barge_section(W, H)
    small = _barge_section(W - 0.010, H - 0.006, T - 0.006)
    cy = sum(s for s, z in sec) / len(sec)
    cz = sum(z for s, z in sec) / len(sec)
    # the tail rolls shut over 4 cm (section drawn in toward its centre), so the eave end of the verge is closed
    shut = [(0.04 * f, [(cy + (s - cy) * (0.15 + 0.85 * f), cz + (z - cz) * (0.15 + 0.85 * f)) for s, z in sec])
            for f in (0.0, 0.5, 0.85, 1.0)]
    loft(bm, shut + [(L - HEAD, sec), (L - HEAD, small), (L, small)], place)


def junction(bm, arms, W, H, place=_id, dome=True, dome_z=None, floor=None, rays=192, rings=28, blend=0.02):
    """ครอบโค้งสามทาง / สี่ทาง as ONE continuous shell (spec 29 ต.ค.: separate arms round a ball looked broken; the
    real piece is a groin vault of its arms with a raised centre, catalogue photos).

    arms = [(dx, dy, slope, zoff, head[, fall])]: plan direction from the centre, fall per horizontal metre along
    the arm (0 for a ridge arm), the arm's skirt seat at the centre (zoff ≤ 0), head=True for a spigot end under the
    next ridge cap's tail (False: plain end over the hip cap below). The outer surface is the smooth maximum of the
    arms' arches and the centre dome (rim at dome_z, crown H above the lowest seat); the shell is T thick along the
    surface normal. floor(x, y) (local) = the tiles' height: each arm's skirts are seated on it (zoff/slope are then
    not used) and the underside never goes below it. Sampled on rays
    from the centre (the footprint is star-shaped), so the skirts follow the true outline."""
    from mathutils import Vector
    a0, rise = W * 0.68 / 2, H * 0.75   # arm arch: as the ridge cap it receives (25 × 10 on the three-way)
    L = W * 0.24 + 0.15                  # centre → arm end (footprint 37 × 41.5 for the three-way)
    R = W * 0.30
    seat_min = min(a[3] for a in arms)
    rim = 0.0 if dome_z is None else dome_z
    d_rise = H + seat_min - rim
    A = []
    for dx, dy, sl, zoff, head, *_ in arms:
        u = Vector((dx, dy)).normalized()
        A.append((u, Vector((-u.y, u.x)), sl, zoff, head))

    def size(t, head):   # arch half width and rise along the arm (the spigot is one wall thinner)
        return (a0 - T - 0.001, rise - T - 0.001) if head and t > L - HEAD else (a0, rise)

    def terms(x, y, clip):
        out = []
        for u, v, sl, zoff, head in A:
            t, s_ = u.x * x + u.y * y, v.x * x + v.y * y
            if -0.02 <= t <= L:
                a, h = size(t, head)
                if floor is None:
                    base = zoff - sl * max(t, 0.0)
                else:   # seated on the tiles: the lower of the two skirt feet at this station
                    tt = max(t, 0.0)
                    base = min(floor(*(u * tt + v * a)), floor(*(u * tt - v * a)))
                if abs(s_) < a:
                    out.append(base + h * math.sqrt(1 - (s_ / a) ** 2))
                elif not clip:   # beyond the skirt: falls away steeply, so it never lifts a neighbour (normals only)
                    out.append(base - 3 * (abs(s_) - a))
        r = math.hypot(x, y)
        if dome and r < R:
            out.append(rim + d_rise * math.sqrt(1 - (r / R) ** 2))
        elif dome and not clip:
            out.append(rim - 3 * (r - R))
        return out

    def f(x, y):
        vals = terms(x, y, False) or [seat_min]
        m = vals[0]
        for b in vals[1:]:   # smooth max: the arms blend into one surface instead of meeting in sharp creases
            m = (m + b + math.sqrt((m - b) ** 2 + blend ** 2)) / 2
        return m

    def edge(th):   # outline radius on a ray: bisection on "some arm or the dome covers the point"
        c, s_ = math.cos(th), math.sin(th)
        lo, hi = 0.0, 0.8
        for _ in range(40):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if terms(mid * c, mid * s_, True) else (lo, mid)
        return lo

    e = 1e-4
    def pts(x, y):
        z = f(x, y)
        n = Vector((-(f(x + e, y) - f(x - e, y)) / (2 * e), -(f(x, y + e) - f(x, y - e)) / (2 * e), 1.0)).normalized()
        top = Vector((x, y, z))
        bot = top - n * T
        if floor is not None:
            bot.z = max(bot.z, floor(bot.x, bot.y) + 0.0005)
        return top, bot

    rb = [edge(math.tau * i / rays) for i in range(rays)]
    grid = []
    for i in range(rays):
        th = math.tau * i / rays
        row = []
        for j in range(1, rings + 1):
            r = rb[i] * math.sin(math.pi / 2 * j / rings)   # denser toward the steep skirts
            row.append(pts(r * math.cos(th), r * math.sin(th)))
        grid.append(row)
    ctop, cbot = pts(0.0, 0.0)
    V = lambda p: bm.verts.new(place(p.x, p.y, p.z))
    vc = (V(ctop), V(cbot))
    G = [[(V(tp), V(bt)) for tp, bt in row] for row in grid]
    for i in range(rays):
        k = (i + 1) % rays
        bm.faces.new((vc[0], G[i][0][0], G[k][0][0]))
        bm.faces.new((vc[1], G[k][0][1], G[i][0][1]))
        for j in range(rings - 1):
            bm.faces.new((G[i][j][0], G[i][j + 1][0], G[k][j + 1][0], G[k][j][0]))
            bm.faces.new((G[i][j][1], G[k][j][1], G[k][j + 1][1], G[i][j + 1][1]))
        bm.faces.new((G[i][-1][0], G[i][-1][1], G[k][-1][1], G[k][-1][0]))   # the skirt foot
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def three_way(bm, place=_id, hip_fall=math.tan(math.radians(22.2))):
    """ครอบโค้งสามทาง (hip roof): the ridge arm along -x, two hip arms at ±135° in plan falling at the hip slope
    (30° roof: atan(tan30 / √2) = 22.2°)."""
    _, W, L, H, _, _ = CAPS["three_way"]
    s = math.sqrt(0.5)
    junction(bm, [(-1, 0, 0.0, 0.0, True), (s, s, hip_fall, 0.0, False), (s, -s, hip_fall, 0.0, False)], W, H, place)


def four_way(bm, place=_id, hip_fall=math.tan(math.radians(22.2))):
    """ครอบโค้งสี่ทาง: four hip arms of a pyramid roof under the dome."""
    _, W, L, H, _, _ = CAPS["four_way"]
    s = math.sqrt(0.5)
    junction(bm, [(a, b, hip_fall, 0.0, False) for a in (s, -s) for b in (s, -s)], W, H, place)


PIECES = dict(ridge=ridge, gable_end=gable_end, barge=barge, barge_end=barge_end, hip_end=hip_end, two_way=two_way,
              three_way=three_way, four_way=four_way)


def build(bm, key, place=_id):
    PIECES[key](bm, place)


def volume(bm):
    return abs(bm.calc_volume(signed=True))


def caps_selftest():
    """Each piece: a closed manifold solid whose volume × RHO_C is within 30 % of the catalogue weight."""
    import bmesh
    rows = []
    for key, (th, W, L, H, kg, cover) in CAPS.items():
        bm = bmesh.new()
        build(bm, key)
        bad = [e for e in bm.edges if not e.is_manifold]
        assert not bad, f"{key}: {len(bad)} open edges"
        got = volume(bm) * RHO_C
        bm.free()
        assert abs(got - kg) <= 0.30 * kg, f"{key} {th}: model {got:.2f} kg, catalogue {kg} kg"
        rows.append(f"{th} {got:.2f}/{kg}")
    return "cpac_caps ok: " + " · ".join(rows)
