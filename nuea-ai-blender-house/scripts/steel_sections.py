"""Cold-formed steel sections modelled to the real profile (spec 29 ต.ค.): wall plates, rafters, purlins.

Read the size off the shop's dimension drawing (ไทวัสดุ product page → open the enlarged picture: h × b × lip × t),
take kg/m from the TIS 1228 table on the same page or in `TIS`, build the profile here and check it against the
table: the profile area × 7850 must give the table's kg/m (inner bend radius = t makes the lipped C match).

    exec(open(<this file>).read())
    poly = lipped_c(0.100, 0.050, 0.020, 0.0023)        # (s, z): web on s = 0, opening to +s, z 0 … h
    prism(bm, poly, 0.0, 6.0, lambda u, s, z: (u, s, z))   # closed solid along u into a bmesh
    o, i = box_tube(0.050, 0.050, 0.002); tube(bm, o, i, 0.0, 6.0, place)   # square tube (แป๊บเหลี่ยม)
    hat = strip([(-0.0305, 0), ...], 0.0005); prism(bm, hat, ...)            # thin formed batten from its centreline
    print(selftest())
"""
import math

RHO = 7850.0
# lipped channels (h, b, lip, t mm): standard TIS 1228 / JIS G 3350 table kg/m — confirm each size on the shop page
# before use (100×50×20×2.3 was on the E42 order)
TIS = {(75, 45, 15, 2.3): 3.25, (100, 50, 20, 2.3): 4.06, (125, 50, 20, 2.3): 4.51, (150, 50, 20, 2.3): 4.96,
       (100, 50, 20, 3.2): 5.50, (150, 65, 20, 3.2): 7.51}


def _arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def lipped_c(h, b, c, t, ri=None, n=8):
    """Closed outline of a lipped channel h × b × c × t: outer contour from the bottom lip tip round to the top lip
    tip, then the inner contour back. Bends have inner radius ri (default t), n segments each."""
    ri = t if ri is None else ri
    ro = ri + t
    assert c > ro and b > 2 * ro and h > 2 * ro, f"lip/flange too short for the bends: {h} {b} {c} {t}"
    out = [(b, c)] + _arc(b - ro, ro, ro, 0, -90, n) + _arc(ro, ro, ro, -90, -180, n) + \
        _arc(ro, h - ro, ro, 180, 90, n) + _arc(b - ro, h - ro, ro, 90, 0, n) + [(b, h - c)]
    inn = [(b - t, h - c)] + _arc(b - ro, h - ro, ri, 0, 90, n) + _arc(ro, h - ro, ri, 90, 180, n) + \
        _arc(ro, ro, ri, 180, 270, n) + _arc(b - ro, ro, ri, 270, 360, n) + [(b - t, c)]
    return out + inn


def area(poly):
    """Shoelace area of a closed outline (positive)."""
    return abs(sum(x0 * z1 - x1 * z0 for (x0, z0), (x1, z1) in zip(poly, poly[1:] + poly[:1]))) / 2


def kg_m(poly):
    return area(poly) * RHO


def prism(bm, poly, u0, u1, place):
    """Add the outline swept from u0 to u1 to bmesh bm as one closed solid; place(u, s, z) → world (x, y, z).
    poly is a strip (lipped_c: outer contour then inner back, poly[i] facing poly[-1-i]): each cap is the quads
    between the two contours. (Triangulating the concave n-gon filled the channel's hollow, E42: caps 18 times
    the section.) Normals point out whatever the handedness of place."""
    import bmesh
    n = len(poly)
    assert n % 2 == 0, "not a strip outline"
    rings = [[bm.verts.new(place(u, s, z)) for s, z in poly] for u in (u0, u1)]
    for r, flip in ((rings[0], True), (rings[1], False)):
        for i in range(n // 2 - 1):
            q = (r[i], r[i + 1], r[n - 2 - i], r[n - 1 - i])
            bm.faces.new(q[::-1] if flip else q)
    for i in range(n):
        bm.faces.new((rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def box_tube(B, H, t, ro=None, n=6):
    """(outer, inner) loops of a square/rectangular tube B × H × t (TIS 107), centred on s = 0, z 0 … H, outer
    corner radius ro (default 2t; TIS allows up to 3t), same point count so the caps pair up."""
    ro = 2 * t if ro is None else ro
    ri = max(ro - t, 1e-6)
    loop = lambda r, o: (_arc(B / 2 - ro, ro, r, -90, 0, n) + _arc(B / 2 - ro, H - ro, r, 0, 90, n) +
                         _arc(-B / 2 + ro, H - ro, r, 90, 180, n) + _arc(-B / 2 + ro, ro, r, 180, 270, n))
    return loop(ro, 0), loop(ri, t)


def tube_area(outer, inner):
    return area(outer) - area(inner)


def tube(bm, outer, inner, u0, u1, place):
    """Sweep a tube (outer, inner loops) from u0 to u1 into bm: one closed solid, caps = quads between the loops."""
    import bmesh
    n = len(outer)
    assert len(inner) == n, "loops must pair up"
    R = [[[bm.verts.new(place(u, s, z)) for s, z in lp] for lp in (outer, inner)] for u in (u0, u1)]
    for i in range(n):
        j = (i + 1) % n
        for k in (0, 1):   # outer and inner walls
            bm.faces.new((R[0][k][i], R[0][k][j], R[1][k][j], R[1][k][i]))
        for r in (0, 1):   # caps
            bm.faces.new((R[r][0][i], R[r][0][j], R[r][1][j], R[r][1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def strip(path, t):
    """Thin cold-formed strip t thick along a centreline polyline [(s, z)] (mitred corners): an outline in the
    prism() convention (one side out, the other back)."""
    def off(k):
        out = []
        for i, p in enumerate(path):
            ns = []
            for a, b in [(path[j], path[j + 1]) for j in (i - 1, i) if 0 <= j < len(path) - 1]:
                dx, dz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dz)
                ns.append((-dz / L, dx / L))
            nx, nz = (sum(v[0] for v in ns), sum(v[1] for v in ns))
            m = math.hypot(nx, nz)
            nx, nz = nx / m, nz / m
            cosh = nx * ns[0][0] + nz * ns[0][1]   # mitre: stretch by 1/cos(half angle)
            out.append((p[0] + k * nx / cosh, p[1] + k * nz / cosh))
        return out
    return off(t / 2) + off(-t / 2)[::-1]


def frame(p0, d, side, up):
    """place(u, s, z) for a member whose section bottom-centre line starts at p0 and runs along unit d; s along
    `side`, z along `up` (all mathutils Vectors, orthonormal)."""
    return lambda u, s, z: tuple(p0 + d * u + side * s + up * z)


def obb(verts, d):
    """Tightest box round a straight member's vertices with one axis along d: (centre, axes, half sizes).
    The other two axes come from the section's own edge directions (rotating calipers over the hull)."""
    from mathutils import Vector
    d = d.normalized()
    a0 = d.orthogonal().normalized()
    b0 = d.cross(a0)
    P = [(v.dot(a0), v.dot(b0)) for v in verts]
    best = None
    for i in range(len(P) - 1):
        ex, ey = P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]
        L = math.hypot(ex, ey)
        if L < 1e-7:
            continue
        ex, ey = ex / L, ey / L
        xs = [x * ex + y * ey for x, y in P]
        ys = [-x * ey + y * ex for x, y in P]
        A = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if best is None or A < best[0] - 1e-12:
            best = (A, ex, ey, xs, ys)
    _, ex, ey, xs, ys = best
    ax = [d, (a0 * ex + b0 * ey).normalized(), (-a0 * ey + b0 * ex).normalized()]
    us = [v.dot(d) for v in verts]
    lo, hi = [min(us), min(xs), min(ys)], [max(us), max(xs), max(ys)]
    c = sum(((lo[k] + hi[k]) / 2 * ax[k] for k in range(3)), Vector())
    return c, ax, [(hi[k] - lo[k]) / 2 for k in range(3)]


def obb_overlap(A, B):
    """Penetration depth of two oriented boxes (separating-axis test, 15 axes); <= 0 means apart or touching."""
    (ca, aa, ha), (cb, ab, hb) = A, B
    t = cb - ca
    depth = float("inf")
    axes = aa + ab + [x.cross(y) for x in aa for y in ab]
    for L in axes:
        if L.length < 1e-6:
            continue
        L = L.normalized()
        ra = sum(ha[k] * abs(aa[k].dot(L)) for k in range(3))
        rb = sum(hb[k] * abs(ab[k].dot(L)) for k in range(3))
        depth = min(depth, ra + rb - abs(t.dot(L)))
        if depth <= 0:
            return depth
    return depth


def selftest():
    for (h, b, c, t), w in TIS.items():
        got = kg_m(lipped_c(h / 1000, b / 1000, c / 1000, t / 1000, n=32))
        assert abs(got - w) <= 0.01 * w, f"C{h}×{b}×{c}×{t}: profile {got:.3f} kg/m, TIS {w}"
    o, i = box_tube(0.050, 0.050, 0.002, ro=0.006, n=32)   # TIS 107 50×50×2.0 with r = 3t: table 2.88 kg/m
    assert abs(tube_area(o, i) * RHO - 2.88) <= 0.01 * 2.88, f"box 50×50×2.0: {tube_area(o, i) * RHO:.3f} kg/m"
    s = strip([(0, 0), (0.01, 0), (0.01, 0.01)], 0.001)   # L 10 × 10 mm × 1 mm centreline = 20 mm → 20 mm²
    assert abs(area(s) - 0.02 * 0.001) < 1e-12, f"strip area {area(s)}"
    return f"steel_sections ok: {len(TIS)} TIS lipped channels within 1 % · box tube · strip"
