"""Working-stress (WSD) check of RC beams, the method of the engineer's calculation the user gave
(a licensed engineer's calculation sheet): loads → slab share to the beams → continuous-beam
moments → bars. Use it to choose among the beam types a drawing gives (SS-02 S-22: GB1/GB2/GB3) line by line in a
model and to flag lines that need more. It is a check for modelling and BOQ; a licensed engineer signs the design.

Units: kg, m for loads and lengths; cm, cm², ksc for sections.

    exec(open(<this file>).read()); print(selftest())
"""
import itertools, math

# Design criteria of the calc (page 1): loads kg/m³ · kg/m², stresses ksc
CRIT = dict(rc=2400, finish=120, wall=180, ll_floor=200, ll_roof=50, fc_cyl=173, fc=65, fs=1700, fy=4000,
            n=10.26, fv=1200)   # fv: RB stirrups SR24, 0.5 fy
K = CRIT["n"] * CRIT["fc"] / (CRIT["n"] * CRIT["fc"] + CRIT["fs"])   # 0.282
J = 1 - K / 3                                                       # 0.906
R = 0.5 * CRIT["fc"] * K * J                                        # 8.297 ksc
VC = 0.29 * math.sqrt(CRIT["fc_cyl"])                               # 3.81 ksc, concrete shear without stirrups
AREA = {6: 0.283, 9: 0.636, 12: 1.131, 16: 2.011, 20: 3.142}       # cm² per bar


def slab_to_beams(S, L, w):
    """Equivalent uniform load (kg/m) a slab panel S ≤ L (m) of w (kg/m²) puts on its short and long edge beams.
    Two-way when S/L ≥ 0.5 (calc p.6: short wS/3, long wS/3·(3 − m²)/2), else one-way onto the long edges."""
    S, L = min(S, L), max(S, L)
    m = S / L
    return (w * S / 3, w * S / 3 * (3 - m * m) / 2) if m >= 0.5 else (0.0, w * S / 2)


def edge_load(S, L, w, u0, u1, short):
    """Equivalent uniform load (kg/m) on the part u0..u1 (m from the edge's start) of a panel edge, short edge of
    length S or long edge of length L: the 45° tributary load q(u) (one-way: wS/2 on the long edges only), turned
    into the uniform load with the same mid-span moment on u0..u1 as a simple span. A full edge gives
    slab_to_beams(); a span between two stubs in the middle of a long edge gets its real share (up to wS/2)."""
    S, L = min(S, L), max(S, L)
    ln = S if short else L
    if S / L >= 0.5:
        q = lambda u: w * min(u, ln - u, S / 2)
    else:
        q = lambda u: 0.0 if short else w * S / 2
    Ls, n = u1 - u0, 400
    assert Ls > 0 and -1e-9 <= u0 and u1 <= ln + 1e-9, "span not on the edge"
    dx = Ls / n
    M = sum(q(u0 + (i + 0.5) * dx) * min(i + 0.5, n - i - 0.5) * dx / 2 * dx for i in range(n))
    return 8 * M / (Ls * Ls)


def depth(h, cover=2.5, stirrup=0.6, bar=1.2):
    """Effective depth d (cm). The calc itself uses d = h − cover (no stirrup, no half bar): less safe."""
    return h - cover - stirrup - bar / 2


def continuous(spans, dl, ll, end_hog=1 / 16):
    """Spans L (m) on pinned supports with uniform dead dl and live ll (kg/m) per span. Envelope over every
    live-load pattern: per span (max sagging M, hogging M at left/right support (≤ 0), max |V|) in kg·m, kg.
    The two outer ends get at least −w·L²·end_hog: a beam cast with its column is not a pin (ACI 6.5.2,
    exterior support built integral with a column: wL²/16; 0 = true pin)."""
    n = len(spans)
    env = [[0.0, 0.0, 0.0, 0.0] for _ in range(n)]
    for on in itertools.product((0, 1), repeat=n):
        w = [d + l * o for d, l, o in zip(dl, ll, on)]
        # slope-deflection, EI = 1, unknown rotations at the n + 1 supports, clockwise end moments
        A = [[0.0] * (n + 1) for _ in range(n + 1)]
        b = [0.0] * (n + 1)
        for i, (L, q) in enumerate(zip(spans, w)):
            k = 2 / L
            A[i][i] += 2 * k; A[i][i + 1] += k; b[i] += q * L * L / 12          # M_ab = k(2θa + θb) − qL²/12
            A[i + 1][i] += k; A[i + 1][i + 1] += 2 * k; b[i + 1] -= q * L * L / 12  # M_ba = k(θa + 2θb) + qL²/12
        th = _solve(A, b)
        for i, (L, q) in enumerate(zip(spans, w)):
            k = 2 / L
            m0 = k * (2 * th[i] + th[i + 1]) - q * L * L / 12      # sagging moment at the left end
            m1 = -(k * (th[i] + 2 * th[i + 1]) + q * L * L / 12)   # sagging moment at the right end
            v0 = q * L / 2 + (m1 - m0) / L
            x = min(max(v0 / q, 0.0), L)
            e = env[i]
            e[0] = max(e[0], m0 + v0 * x - q * x * x / 2)
            e[1], e[2] = min(e[1], m0), min(e[2], m1)
            e[3] = max(e[3], abs(v0), abs(v0 - q * L))
    env[0][1] = min(env[0][1], -(dl[0] + ll[0]) * spans[0] ** 2 * end_hog)
    env[-1][2] = min(env[-1][2], -(dl[-1] + ll[-1]) * spans[-1] ** 2 * end_hog)
    return [tuple(e) for e in env]


def beam_loads(spans, loads, end_hog=1 / 16, n=200):
    """continuous() for any loads, e.g. a secondary beam resting on this one. loads[i] = [(a0, a1, wd, wl), ...] on
    span i (m from its left support): uniform dead/live kg/m over a0..a1, or a point load in kg when a0 == a1.
    Returns (envelope as continuous(), support reactions dead, support reactions live), reactions with every span
    loaded. Uniform pieces are split into n point loads (midpoint rule)."""
    pts = []
    for L, ld in zip(spans, loads):
        p = []
        for a0, a1, wd, wl in ld:
            assert -1e-9 <= a0 <= a1 <= L + 1e-9, "load outside its span"
            if a1 - a0 < 1e-9:
                p.append((a0, wd, wl))
            else:
                dx = (a1 - a0) / n
                p += [(a0 + (i + 0.5) * dx, wd * dx, wl * dx) for i in range(n)]
        pts.append(sorted(p))

    def solve(P):   # P[i] = [(a, load kg)] → per span (m0, m1, v0)
        m = len(spans)
        A, b = [[0.0] * (m + 1) for _ in range(m + 1)], [0.0] * (m + 1)
        fem = []
        for i, L in enumerate(spans):
            k = 2 / L
            fa = -sum(w * a * (L - a) ** 2 for a, w in P[i]) / L ** 2      # clockwise fixed-end moments
            fb = sum(w * a * a * (L - a) for a, w in P[i]) / L ** 2
            fem.append((fa, fb))
            A[i][i] += 2 * k; A[i][i + 1] += k; b[i] -= fa
            A[i + 1][i] += k; A[i + 1][i + 1] += 2 * k; b[i + 1] -= fb
        th = _solve(A, b)
        out = []
        for i, L in enumerate(spans):
            k, (fa, fb) = 2 / L, fem[i]
            m0, m1 = k * (2 * th[i] + th[i + 1]) + fa, -(k * (th[i] + 2 * th[i + 1]) + fb)
            out.append((m0, m1, sum(w * (L - a) / L for a, w in P[i]) + (m1 - m0) / L))
        return out

    env = [[0.0, 0.0, 0.0, 0.0] for _ in spans]
    for on in itertools.product((0, 1), repeat=len(spans)):
        P = [[(a, d + l * o) for a, d, l in p] for p, o in zip(pts, on)]
        for i, (L, (m0, m1, v0)) in enumerate(zip(spans, solve(P))):
            tot, e = sum(w for _, w in P[i]), env[i]
            for x in sorted({L * j / 400 for j in range(401)} | {a for a, _ in P[i]}):   # peaks sit under point loads
                e[0] = max(e[0], m0 + v0 * x - sum(w * (x - a) for a, w in P[i] if a < x))
            e[1], e[2] = min(e[1], m0), min(e[2], m1)
            e[3] = max(e[3], abs(v0), abs(v0 - tot))
    for i, k in ((0, 1), (len(spans) - 1, 2)):   # outer ends cast with a column / beam: at least W·L·end_hog
        env[i][k] = min(env[i][k], -sum(d + l for _, d, l in pts[i]) * spans[i] * end_hog)

    def reactions(P):
        r = [0.0] * (len(spans) + 1)
        for i, (m0, m1, v0) in enumerate(solve(P)):
            r[i] += v0
            r[i + 1] += sum(w for _, w in P[i]) - v0
        return r
    return [tuple(e) for e in env], reactions([[(a, d) for a, d, _ in p] for p in pts]), \
        reactions([[(a, l) for a, _, l in p] for p in pts])


def _solve(A, b):
    n = len(b)
    M = [row[:] + [v] for row, v in zip(A, b)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * x for a, x in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def capacity(nbars, dia, b, d):
    """Allowable moment (kg·m) of a singly reinforced section: steel As·fs·j·d, capped by concrete R·b·d²."""
    return min(nbars * AREA[dia] * CRIT["fs"] * J * d, R * b * d * d) / 100


def bars_ok(n, dia, M, b, d):
    """n bars carry M (kg·m) and meet the minimum steel: As ≥ 14/fy·b·d, or ≥ 4/3 of the steel M needs."""
    As, req = n * AREA[dia], M * 100 / (CRIT["fs"] * J * d)
    return M <= R * b * d * d / 100 and As >= req and As >= min(14 / CRIT["fy"] * b * d, 4 / 3 * req)


def shear_ok(V, b, d, legs=2, dia=6, s=15):
    """Concrete + stirrups (kg) ≥ V and spacing ≤ d/2."""
    return V <= VC * b * d + legs * AREA[dia] * CRIT["fv"] * d / s and s <= d / 2


def selftest():
    """Reproduce the engineer's numbers (calc pp. 4–6, his d = h − 2.5)."""
    def near(a, b, tol=0.01):
        assert abs(a - b) <= tol * abs(b), (a, b)
    near(K, 0.282, 0.002); near(J, 0.906, 0.001); near(R, 8.297, 0.001); near(VC, 3.81, 0.002)
    for b, h, M, d_req, ast in ((15, 30, 800, 25.35, 1.89), (20, 40, 2000, 34.72, 3.46)):
        near(math.sqrt(M * 100 / (R * b)), d_req)
        near(M * 100 / (CRIT["fs"] * J * (h - 2.5)), ast)
    d = 37.5                                    # GB3 of the calc: 3,400 kg·m on 20×40 → doubly reinforced
    mc = R * 20 * d * d
    fs2 = 2 * CRIT["fs"] * (K - 2.5 / d) / (1 - K)
    near(mc / 100, 2333.44)
    near(mc / (CRIT["fs"] * J * d) + (340000 - mc) / (CRIT["fs"] * (d - 2.5)), 5.83)
    near((340000 - mc) / (fs2 * (d - 2.5)), 2.99)
    near(slab_to_beams(1.8, 2.0, 560)[0], 336.0); near(slab_to_beams(1.8, 2.0, 560)[1], 367.92)
    near(edge_load(1.8, 2.0, 560, 0, 1.8, True), 336.0, 0.001)      # full edges = the engineer's coefficients
    near(edge_load(1.8, 2.0, 560, 0, 2.0, False), 367.92, 0.001)
    near(edge_load(3.0, 6.0, 1.0, 1.5, 3.0, False), 1.5, 0.001)     # mid part of a long edge: flat wS/2
    (m_pos, m_l, m_r, v), = continuous([4.0], [1000.0], [0.0], end_hog=0)
    near(m_pos, 2000.0); near(v, 2000.0); assert abs(m_l) < 1e-6 and abs(m_r) < 1e-6
    near(-continuous([4.0], [1000.0], [0.0])[0][1], 1000.0)         # integral end: wL²/16
    (p1, _, r1, _), (p2, l2, _, _) = continuous([4.0, 4.0], [1000.0, 1000.0], [0.0, 0.0])
    near(-r1, 2000.0); near(-l2, 2000.0); near(p1, 1125.0)    # two equal spans: wL²/8 over the middle support
    # live load on one span only: M_B = −(w1 + w2)L²/16, R_A = w1·L/2 + M_B/L, M+ = R_A²/(2·w1) = 1880.2
    (p1, _, r1, _), _ = continuous([4.0, 4.0], [1000.0, 1000.0], [500.0, 500.0])
    near(p1, (1500 * 2 - 2500 / 4) ** 2 / 3000); near(-r1, 3000.0)
    # beam_loads: same uniform case, a point load (P a b / L), reactions summing to the load
    env, rd, rl = beam_loads([4.0, 4.0], [[(0, 4, 1000.0, 500.0)], [(0, 4, 1000.0, 500.0)]])
    near(env[0][0], (1500 * 2 - 2500 / 4) ** 2 / 3000); near(-env[0][2], 3000.0)
    near(rd[1], 1.25 * 1000 * 4); near(sum(rd) + sum(rl), 1500 * 8)
    env, rd, _ = beam_loads([4.0], [[(1.0, 1.0, 1000.0, 0.0)]], end_hog=0)
    near(env[0][0], 1000 * 1 * 3 / 4); near(rd[0], 750.0); near(env[0][3], 750.0)
    assert not bars_ok(2, 12, 967, 20, 36.3) and bars_ok(3, 12, 967, 20, 36.3)   # 2.26 < 4/3 × 1.73 cm²
    assert bars_ok(2, 12, 0, 20, 36.3) and not bars_ok(3, 12, 2300, 20, 36.3)    # over R·b·d²: doubly
    return "beam_wsd selftest ok"
