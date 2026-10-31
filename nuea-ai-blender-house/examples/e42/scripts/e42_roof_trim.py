"""E42 ST07 roof trims (spec 29 ต.ค.): the CPAC caps as real pieces on the SCG Dry Tech dry system, to the CPAC
installation manual (Dec 2024, p.20-23), and the metal-sheet TEST's accessories to the METALUXE SSR760 guide.

CPAC order on a hip roof (manual p.20-23): brackets ≤ 1 m apart on the hips and ridge → cap rail on them →
underlay strip 0.15 m each side → ครอบโค้งหางมน at the foot of each hip, ครอบสันโค้ง up the hip (each tail over
the head below) → ครอบโค้งสามทาง where the hips meet the ridge → ครอบสันโค้ง from both ends of the ridge to the
middle → ครอบโค้งสองทาง over the middle. One 2.5" screw per cap, 3 on the three-way.

    exec(<e42_struct>); exec(<e42_walls>); exec(<e42_roof>); exec(<this file>)
    build_roof(); build_cpac_trims(); print(selfcheck_trims())
"""
import math, os
import bmesh
from mathutils import Vector, Matrix

exec(open(os.path.join(globals().get("SKILL_SCRIPTS") or os.path.expanduser("~/.claude/skills/nuea-ai-blender-house/scripts"), "cpac_caps.py")).read())

# the tiles' top above the rafter tops, along the normal: batten + wave + course step + gap + tile (cpac_tiles())
CREST = BATTEN["h"] + TILE["wave"] + 0.025 + 0.004 + TILE["t"]
# Dry Tech parts: bracket = bent flat bar (manual p.22, size not printed: 30 × 2 mm assumed); cap rail = a hat
# section (picture p.20; drawn as the PROFAST batten), 3 m a kit; underlay strip 0.15 m, 2 cm inside the cap edge
DRY = dict(step=1.0, bar_w=0.030, bar_t=0.002, foot=0.05, strip_t=0.0015, on_tile=0.08, inside=0.02, kit=3.0, end=0.10)
TSPEC = dict(bracket="ขาเหล็กยึดเหล็กรับครอบ (ชุด Dry Tech)", rail="เหล็กรับครอบ Dry Tech 3 ม./ท่อน",
            strip="แผ่นรองใต้ครอบ Dry Tech กว้าง 0.15 ม. (ข้างละแถบ)")


def _rm(o):
    """Remove an object and its mesh (a rebuild with fewer pieces leaves no orphan data)."""
    me = o.data
    bpy.data.objects.remove(o)
    if me is not None and me.users == 0:
        (bpy.data.meshes if isinstance(me, bpy.types.Mesh) else bpy.data.curves).remove(me)


def _planes(sides, off=None):
    """The four covering-top planes (n, c): n·p = c, `off` above the rafter tops (default: the CPAC tile crests)."""
    return [(s["n"], s["n"].dot(s["Q0"]) + (CREST if off is None else off)) for s in sides]


def _meet(*pl):
    """The point on three planes, or a point on the line of two."""
    if len(pl) == 3:
        return Matrix([n for n, _ in pl]).inverted() @ Vector([c for _, c in pl])
    (n1, c1), (n2, c2) = pl
    d = n1.cross(n2)
    return (n2.cross(d) * c1 + d.cross(n1) * c2) / d.length_squared


def _frame(d, pl):
    """Section frame of a line along d: (side, up, tan of the tile fall across it, read from both planes)."""
    up = (Vector((0, 0, 1)) - d * d.z).normalized()
    side = d.cross(up)
    t = [abs(n.dot(side)) / n.dot(up) for n, _ in pl]
    assert abs(t[0] - t[1]) < 1e-6, "line not midway between its planes"
    return side, up, t[0]


def _cap_lines(off=None):
    """Hips (foot at the covering's corner → three-way centre) and the ridge (centre → centre), on the covering
    tops. The covering runs past the fascia: tiles FASCIA["tile_over"], sheets FASCIA["sheet_over"]."""
    E, sides, D, ze = _geom()
    over = _tile_edge() if off is None else FASCIA["sheet_over"]
    cx, cy = sum(x for x, _ in E) / 4, sum(y for _, y in E) / 4
    E = [(x + math.copysign(over, x - cx), y + math.copysign(over, y - cy)) for x, y in E]
    P = _planes(sides, off)
    tri = [k for k, s in enumerate(sides) if s["L"] - 2 * D < 1e-6]
    long_ = [k for k in range(4) if k not in tri]
    J = {k: _meet(P[k], P[long_[0]], P[long_[1]]) for k in tri}   # a three-way over each ridge end
    hips = []
    for i, (ex, ey) in enumerate(E):
        a, b = (i - 1) % 4, i
        d = P[a][0].cross(P[b][0]).normalized()
        d = d if d.z > 0 else -d
        p = _meet(P[a], P[b])
        foot = p + d * ((Vector((ex, ey)) - p.xy).dot(d.xy) / d.xy.length_squared)
        top = J[a if a in tri else b]
        hips.append(dict(name=f"Hip{i + 1}", F=foot, J=top, d=(top - foot).normalized(), pl=(P[a], P[b])))
    j0, j1 = (J[k] for k in tri)
    ridge = dict(name="Ridge", F=j0, J=j1, d=(j1 - j0).normalized(), pl=(P[long_[0]], P[long_[1]]))
    return hips, ridge, J


def _place(O, d, side, up, x0, drop):
    return lambda x, s, z: tuple(O + d * (x0 + x) + side * s + up * (z - drop))


def _piece(c, m, name, key, O, d, pl, x0, L=None):
    """One cap on a line: tail at x0 from O, skirts on the tile crests of both planes."""
    side, up, tf = _frame(d, pl)
    th, W, L0, H, kg, _ = CAPS[key]
    bm = bmesh.new()
    if key == "ridge":
        ridge(bm, _place(O, d, side, up, x0, W / 2 * tf), "ridge", L or L0, fall=tf)
    elif key == "hip_end":
        hip_end(bm, _place(O, d, side, up, x0, W / 2 * tf), fall=tf)
    else:
        PIECES[key](bm, _place(O, d, side, up, x0, W / 2 * tf), fall=tf)
    o = _obj(c, name, bm, m, element="cap_piece", type=f"RC_{key}", th=th, count=1, cut=bool(L and L < L0 - 1e-6),
             screws=1)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _run(c, m, line, x_from, x_to, tag):
    """ครอบสันโค้ง along a line from x_from (first tail) to x_to (last head), each tail over the head before it;
    the last one cut to fit."""
    _, W, L0, _, _, cover = CAPS["ridge"]
    n = 1 if x_to - x_from <= L0 else math.ceil((x_to - x_from - L0) / cover - 1e-9) + 1
    out = []
    for i in range(n):
        x0 = x_from + i * cover
        L = min(L0, x_to - x0)
        assert L > HEAD + 0.03, f"{tag}: last cap only {L:.3f} m"
        out.append(_piece(c, m, f"RC_{tag}_{i + 1:02d}", "ridge", line["F"], line["d"], line["pl"], x0, L))
    return out


def _arm_end(key):
    """Distance from a junction centre to the end of its arms (cpac_caps.junction: start W·0.24 + 0.15)."""
    return CAPS[key][1] * 0.24 + 0.15


def build_cpac_trims():
    """Dry Tech brackets, rails and underlay strips + every cap piece on the hips and ridge (into C_CPAC)."""
    c = bpy.data.collections[C_CPAC]
    for o in [o for o in c.objects if o.name.startswith(("RC_", "RD_"))]:
        _rm(o)
    m = bpy.data.materials["M_Roof_CPAC"]
    galv = mat("M_Steel_Galv", (0.62, 0.64, 0.66), 0.35, 0.9)
    under = mat("M_DryTech_Strip", (0.02, 0.02, 0.02), 0.8)
    hips, ridge_l, J = _cap_lines()
    mem = {mm[1]: mm for mm in _members()[0]}
    r_end, hw = _arm_end("three_way"), CAPS["three_way"][1] * 0.68 / 2
    # --- Dry Tech support on every line: rail under the cap crown, brackets down to the 2C member, strips
    for line in hips + [ridge_l]:
        side, up, tf = _frame(line["d"], line["pl"])
        Lw = (line["J"] - line["F"]).length
        _, W, _, H, _, _ = CAPS["ridge"]
        z_rail = H - T - W / 2 * tf   # rail top under the cap's inner crown
        x0, x1 = (DRY["end"], Lw - r_end) if line is not ridge_l else (r_end - 0.05, Lw - r_end + 0.05)
        p0 = line["F"] + line["d"] * x0 + up * (z_rail - BATTEN["h"])
        p1 = line["F"] + line["d"] * x1 + up * (z_rail - BATTEN["h"])
        bm = bmesh.new()
        _sweep(bm, "hat", p0, p1, side, up)
        _obj(c, f"RD_Rail_{line['name']}", bm, galv, element="rail", type="RD2", th=TSPEC["rail"], stock=DRY["kit"],
             swept=True, butt=True)
        # brackets: ≤ 1 m apart, the end ones DRY["end"] in; each from the member top up to the rail
        kind = "RF_Ridge" if line is ridge_l else f"RF_{line['name']}"
        _, _, _, q0, q1, mside, mup, mw, mh = mem[kind]
        n = max(1, math.ceil((x1 - x0 - 2 * DRY["end"]) / DRY["step"] - 1e-9))
        bm = bmesh.new()
        for i in range(n + 1):
            pc = line["F"] + line["d"] * (x0 + DRY["end"] + i * (x1 - x0 - 2 * DRY["end"]) / n)
            top_line = (q0 + mup * mh, (q1 - q0).normalized())
            pm = top_line[0] + top_line[1] * (pc - top_line[0]).dot(top_line[1])   # on the member top
            head = pc + up * (z_rail - BATTEN["h"])
            hgt = (head - pm).dot(mup)
            _cuboid(bm, pm + mup * (hgt / 2), [line["d"], side, mup], [DRY["bar_w"] / 2, DRY["bar_t"] / 2, hgt / 2])
            _cuboid(bm, pm + mup * (DRY["bar_t"] / 2), [line["d"], side, mup], [DRY["bar_w"] / 2, DRY["foot"] / 2, DRY["bar_t"] / 2])
        _obj(c, f"RD_Brackets_{line['name']}", bm, galv, element="piece", type="RD1", th=TSPEC["bracket"], count=n + 1)
        # underlay strip each side: from the rail flank down onto the tiles, 2 cm inside the cap edge
        s_e = W / 2 - DRY["inside"]
        for sg in (1, -1):
            path = [(BATTEN["w"] / 2, z_rail - 0.006), (s_e - DRY["on_tile"], -(s_e - DRY["on_tile"]) * tf + 0.001),
                    (s_e, -s_e * tf + 0.001)]
            bm = bmesh.new()
            prism(bm, strip([(sg * a, z) for a, z in path], DRY["strip_t"]), 0.0, Lw,
                  lambda u, s, z, line=line: tuple(line["F"] + line["d"] * u + side * s + up * z))
            _obj(c, f"RD_Strip_{line['name']}_{'LR'[sg < 0]}", bm, under, element="strip", type="RD3",
                 th=TSPEC["strip"], stock=DRY["kit"], joint=0.05, swept=True)
    # --- caps: hips foot-up, then the three-ways, then the ridge from both ends into the two-way
    n_caps = 0
    for line in hips:
        Lw = (line["J"] - line["F"]).length
        _piece(c, m, f"RC_{line['name']}_00_end", "hip_end", line["F"], line["d"], line["pl"], 0.0)
        top = Lw - r_end + HEAD   # the last head runs HEAD under the three-way's plain hip arm
        n_caps += len(_run(c, m, line, CAPS["hip_end"][2] - HEAD, top, line["name"]))
    for k, Jc in J.items():
        rd = (ridge_l["J"] - ridge_l["F"]).normalized() * (1 if (Jc - ridge_l["F"]).length < 1e-6 else -1)
        side, up, tf = _frame(rd, ridge_l["pl"])
        arms = [(rd.x, rd.y, 0.0, -hw * tf, True, tf)]
        for line in hips:
            if (line["J"] - Jc).length < 1e-6:
                dn = -line["d"]
                hs, hu, htf = _frame(line["d"], line["pl"])
                arms.append((dn.x / dn.xy.length, dn.y / dn.xy.length, -dn.z / dn.xy.length, -hw * htf, False, htf))
        assert len(arms) == 3, f"three-way {k}: {len(arms)} arms"
        bm = bmesh.new()
        three = CAPS["three_way"]
        crest = lambda x, y, Jc=Jc, P_=_planes(_geom()[1]): min((cc - n.x * (Jc.x + x) - n.y * (Jc.y + y)) / n.z for n, cc in P_) - Jc.z
        junction(bm, arms, three[1], three[3], lambda x, y, z, Jc=Jc: tuple(Jc + Vector((x, y, z))),
                 dome_z=0.0, floor=crest)   # rim on the ridge crest: around the junction the tiles only fall away
        o = _obj(c, f"RC_ThreeWay_{k}", bm, m, element="cap_piece", type="RC_three_way", th=three[0], count=1,
                 screws=3)
        for p in o.data.polygons:
            p.use_smooth = True
    Lr = (ridge_l["J"] - ridge_l["F"]).length
    mid, two = Lr / 2, CAPS["two_way"]
    head_to = mid - two[2] / 2 + 0.04   # last heads 4 cm into the two-way's bells (bells 5 cm)
    start = r_end - HEAD                # the first tail over the three-way's ridge spigot
    n_caps += len(_run(c, m, ridge_l, start, head_to, "Ridge_A"))
    ridge_b = dict(ridge_l, F=ridge_l["J"], J=ridge_l["F"], d=-ridge_l["d"])   # laid from the other end
    n_caps += len(_run(c, m, ridge_b, start, head_to, "Ridge_B"))
    _piece(c, m, "RC_Ridge_TwoWay", "two_way", ridge_l["F"], ridge_l["d"], ridge_l["pl"], mid - two[2] / 2)
    return n_caps


def _verts(o):
    return [o.matrix_world @ v.co for v in o.data.vertices]


def selfcheck_trims():
    """CPAC trims against the manual, read back from the model: caps continuous up every hip and along the ridge
    with each tail lapping the head before it, every skirt seated on the tiles, the rail under the cap crowns,
    brackets ≤ 1 m apart on the members, the underlay strips hidden 2 cm inside the cap edge."""
    c = bpy.data.collections[C_CPAC]
    E, sides, D, ze = _geom()
    P = _planes(sides)
    roof = lambda p: p.z - min((cc - n.x * p.x - n.y * p.y) / n.z for n, cc in P)   # height above the tile crests
    hips, ridge_l, J = _cap_lines()
    caps = [o for o in c.objects if o.name.startswith("RC_")]
    assert caps, "no caps"
    tl = next(o for o in c.objects if o.name.endswith("CPAC_Tiles"))   # the crest constant against the tile mesh
    ev = tl.evaluated_get(bpy.context.evaluated_depsgraph_get())   # with its Solidify (the tile thickness)
    tv = [tl.matrix_world @ v.co for v in ev.to_mesh().vertices]
    ev.to_mesh_clear()
    for k, s in enumerate(sides):
        top = max((v - s["Q0"]).dot(s["n"]) for v in tv   # tile vertices nearest this plane
                  if min(range(4), key=lambda q: abs((v - sides[q]["Q0"]).dot(sides[q]["n"]))) == k)
        assert abs(top - CREST) < 0.002, f"tile crests {top * 1000:.1f} mm above plane {k + 1}, CREST {CREST * 1000:.1f}"
    for o in caps:   # every piece sits on the tiles: lowest point touching, nothing sunk into them
        h = min(roof(v) for v in _verts(o))
        assert -0.002 < h < 0.002, f"{o.name}: lowest point {h * 1000:.1f} mm off the tiles"
    ridge_b = dict(ridge_l, F=ridge_l["J"], d=-ridge_l["d"])
    r_end = _arm_end("three_way")
    for line, tag in [(h_, h_["name"] + "_") for h_ in hips] + [(ridge_l, "Ridge_A_"), (ridge_b, "Ridge_B_")]:
        run = sorted(((min((v - line["F"]).dot(line["d"]) for v in _verts(o)),
                       max((v - line["F"]).dot(line["d"]) for v in _verts(o)), o.name)
                      for o in caps if o.name.startswith("RC_" + tag)))
        assert run, f"no caps on {tag}"
        if tag.startswith("Hip"):
            assert run[0][2].endswith("_end") and run[0][0] < 0.01, f"{tag}: no ครอบโค้งหางมน at the foot ({run[0]})"
            Lw = (line["J"] - line["F"]).length
            assert Lw - r_end < run[-1][1] <= Lw - r_end + HEAD + 0.002, f"{tag}: last head not under the three-way"
        else:
            assert run[0][0] < r_end - HEAD + 0.002, f"{tag}: first tail not over the three-way spigot"
        for (a0, a1, an), (b0, b1, bn) in zip(run, run[1:]):
            lap = a1 - b0
            assert HEAD - 0.002 < lap < HEAD + 0.03, f"{bn} laps {an} by {lap * 100:.1f} cm (head {HEAD * 100:.1f})"
    for k, Jc in J.items():   # one three-way over each hip/ridge meeting, the two-way over the ridge's middle
        o = bpy.data.objects.get(f"RC_ThreeWay_{k}")
        assert o, f"three-way {k} missing"
        crown = max(_verts(o), key=lambda v: v.z)
        assert (crown - Jc).xy.length < 0.01, f"three-way {k}: crown {(crown - Jc).xy.length * 100:.1f} cm off the junction"
    mid = (ridge_l["F"] + ridge_l["J"]) / 2
    tw = bpy.data.objects["RC_Ridge_TwoWay"]
    assert (sum(_verts(tw), Vector()) / len(tw.data.vertices) - mid).xy.length < 0.01, "two-way not mid-ridge"
    _, W, _, H, _, _ = CAPS["ridge"]
    mem = {mm[1]: mm for mm in _members()[0]}
    for line in hips + [ridge_l]:
        side, up, tf = _frame(line["d"], line["pl"])
        crown = H - T - W / 2 * tf   # the cap's inner crown above the line
        top = max((v - line["F"]).dot(up) for v in _verts(bpy.data.objects[f"RD_Rail_{line['name']}"]))
        assert -0.0005 < crown - top < 0.002, f"rail {line['name']}: {(crown - top) * 1000:.1f} mm under the cap crown"
        br = bpy.data.objects[f"RD_Brackets_{line['name']}"]
        vs = _verts(br)
        xs = sorted({round(sum((v - line["F"]).dot(line["d"]) for v in vs[i:i + 16]) / 16, 3) for i in range(0, len(vs), 16)})
        assert len(xs) == br.data["count"] and all(b - a <= DRY["step"] + 1e-3 for a, b in zip(xs, xs[1:])), \
            f"brackets {line['name']} more than {DRY['step']} m apart: {xs}"
        kind = "RF_Ridge" if line is ridge_l else f"RF_{line['name']}"
        _, _, _, q0, q1, _, mup, _, mh = mem[kind]
        lo = min((v - q0).dot(mup) for v in vs)
        assert abs(lo - mh) < 1e-4, f"brackets {line['name']}: feet {lo - mh:.4f} m off the member top"
        for sg in "LR":
            sv = _verts(bpy.data.objects[f"RD_Strip_{line['name']}_{sg}"])
            reach = max(abs((v - line["F"]).dot(side)) for v in sv)
            assert abs(reach - (W / 2 - DRY["inside"])) < DRY["strip_t"] + 1e-3, \
                f"strip {line['name']} {sg}: edge {reach:.3f} m out, cap edge {W / 2:.3f}"
            assert min(roof(v) for v in sv) > -1e-4, f"strip {line['name']} {sg} under the tiles"
    n = {k: sum(o.data.get("count", 1) for o in caps if o.data["type"] == k) for k in {o.data["type"] for o in caps}}
    m_lines = sum((h_["J"] - h_["F"]).length for h_ in hips) + (ridge_l["J"] - ridge_l["F"]).length
    return (f"trims ok: {n} · hips + ridge {m_lines:.2f} m · take-off rule {m_lines * 3.3 * 1.03:.0f} pieces · "
            f"{sum(o.data['count'] for o in c.objects if o.name.startswith('RD_Brackets'))} brackets")


# --- metal-sheet TEST accessories (METALUXE SSR760 guide p.6-9; cap girth and stock length not printed: assumed)
RIB = MS["tube"][0] + MS["foam"] + MS["c_h"] + 0.0015   # rib tops above the rafter tops (purlin + foam + rib)
FLASH = dict(wing=0.20, hem=0.015, t=0.00035, stock=2.40, lap=0.20, nose=0.10,
             spec_h="ครอบตะเข้เมทัลชีท (flashing) 0.35 มม. ปีกข้างละ 20 ซม. ยาว 2.40 ม.",
             spec_r="ครอบสันเมทัลชีท (flashing) 0.35 มม. ปีกข้างละ 20 ซม. ยาว 2.40 ม.")
SCREW = dict(rib="สกรูยึดหลังคาปลายสว่าน 50 มม. (บนลอน: แปชายคา · แปรอยทาบ · กลางแผ่น 3 ลอน)",
             pan="สกรูยึดหลังคาปลายสว่าน 16 มม. (ท้องลอน: แปสัน · สะพานหนู)",
             cap="สกรูยึดครอบปลายสว่าน 22 มม. (ห่างขอบครอบ 5 มม. บนลอน)")


def _flash_section(tf):
    w, h = FLASH["wing"], FLASH["hem"]
    return strip([(-w, -w * tf - h), (-w, -w * tf), (0.0, 0.0), (w, -w * tf), (w, -w * tf - h)], FLASH["t"])


def _screw(bm, p, n):
    """Hex washer-head drill screw seated on p, axis n: Ø16 bonded washer 2 mm + 8 mm hex head 5 mm."""
    a = n.orthogonal().normalized()
    b = n.cross(a)
    for r, z0, z1, k in ((0.008, 0.0, 0.002, 8), (0.0046, 0.002, 0.007, 6)):
        ring = lambda z: [bm.verts.new(p + n * z + (a * math.cos(math.tau * i / k) + b * math.sin(math.tau * i / k)) * r)
                          for i in range(k)]
        lo, hi = ring(z0), ring(z1)
        bm.faces.new(lo[::-1])
        bm.faces.new(hi)
        for i in range(k):
            bm.faces.new((lo[i], lo[(i + 1) % k], hi[(i + 1) % k], hi[i]))


def _inside(p, s, D, margin=0.01):
    return all((Vector((p.x, p.y, 0)) - Vector((pc.x, pc.y, 0))).dot(pn) >= margin for pc, pn in _sheet_cuts(s, D))


def build_metal_trims():
    """Hip and ridge flashings + every screw the guide asks for, into C_MS (after build_metal_test)."""
    c = bpy.data.collections[C_MS]
    for o in [o for o in c.objects if o.name.startswith(("MS_Flash", "MS_Screws"))]:
        _rm(o)
    sheet_m = bpy.data.materials["M_MetalSheet"]
    hd = mat("M_Screw", (0.75, 0.76, 0.78), 0.3, 0.9)
    E, sides, D, ze = _geom()
    hips, ridge_l, J = _cap_lines(RIB)
    # flashings: hip caps from 10 cm past the eave corner (nose folded shut) up to the ridge, pieces lapped 20 cm;
    # the ridge cap over both hip caps (guide p.9: hip, the other hip to its centre, then the ridge cap)
    for li, line in enumerate(hips + [ridge_l]):
        side, up, tf = _frame(line["d"], line["pl"])
        sec = _flash_section(tf)
        Lw = (line["J"] - line["F"]).length
        x0 = -FLASH["nose"] if line is not ridge_l else 0.0
        lift = 0.0015 if line is ridge_l else 0.0005 * (li % 2)
        bm = bmesh.new()
        i, x = 0, x0
        while x < Lw - 1e-6:
            x1 = min(x + FLASH["stock"], Lw)
            z = lift + 0.0008 * (i % 2)   # each lap rides on the piece below
            prism(bm, sec, x, x1, lambda u, s_, z_, z=z: tuple(line["F"] + line["d"] * u + side * s_ + up * (z_ + z)))
            i += 1
            x = x1 - FLASH["lap"] if x1 < Lw - 1e-6 else Lw
        if line is not ridge_l:   # the folded nose: a plate closing the V at the low end
            w = FLASH["wing"]
            tri = [(-w, -w * tf), (0.0, 0.0), (w, -w * tf)]
            vs = [bm.verts.new(line["F"] + line["d"] * (x0 + dx) + side * a + up * (z_ + lift)) for dx in (0.0, FLASH["t"]) for a, z_ in tri]
            for f in ((0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)):
                bm.faces.new([vs[q] for q in f])
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        _obj(c, f"MS_Flash_{line['name']}", bm, sheet_m, element="flashing", type="MF2" if line is ridge_l else "MF1",
             th=FLASH["spec_r"] if line is ridge_l else FLASH["spec_h"], count=i)
    # screws (guide p.7-8): eave purlin + end-lap purlins every rib, middle purlins centre + edge ribs, ridge purlin
    # and hip battens every pan; caps 5 mm in from the edge on every rib they cross
    cover, pitch = MS["cover"], MS["cover"] / 4
    crests = [MS["c_base"] / 2 + k * pitch for k in range(5)]
    B, zr, zp = MS["tube"][0], MS["tube"][0] + MS["foam"] + MS["c_h"], MS["tube"][0] + MS["foam"]
    S = {k: (bmesh.new(), [0]) for k in ("rib", "pan", "cap")}
    seen = set()
    def put(kind, p, n):   # a sheet's last crest is the next sheet's first (side lap): one screw there, not two
        key = (kind, round(p.x, 3), round(p.y, 3), round(p.z, 3))
        if key in seen:
            return
        seen.add(key)
        _screw(S[kind][0], p, n)
        S[kind][1][0] += 1
    for k, s in enumerate(sides):
        vt = D / COS
        rows = sorted((o for o in c.objects if o.name.startswith(f"MS_Purlin_{k + 1}_")), key=lambda o: float(o.name.split("_")[-1]))
        laps = {(o.name.split("_")[3], o.name.split("_")[4]) for o in c.objects if o.name.startswith(f"MS_Sheet_{k + 1}_")}
        n_rows = 1 + max(int(r) for _, r in laps)
        lap_v = []   # end laps sit on a purlin: those purlins get a screw on every rib
        for o in rows:
            v = float(o.name.split("_")[-1])
            vs = [(q - s["Q0"]).dot(s["e"]) for q in _verts(o)]
            u0, u1 = min(vs), max(vs)
            top, eave = o is rows[-1], o is rows[0]
            lapped = any(abs(v - q) < 0.06 for q in _lap_purlins(s, D, rows)) if n_rows > 1 else False
            j = 0
            while j * cover < s["L"] - 1e-6:
                ks = range(5) if (eave or lapped) else (0, 2, 4)
                pos = [j * cover + crests[q] for q in ks] if not top else [j * cover + crests[q] + pitch / 2 for q in range(4)]
                for u in pos:
                    if u0 + 0.01 < u < u1 - 0.01:
                        p = s["Q0"] + s["e"] * u + s["up"] * v + s["n"] * (zp if top else zr)
                        if _inside(p, s, D):
                            put("pan" if top else "rib", p, s["n"])
                j += 1
        for o in [o for o in c.objects if o.name.startswith(f"MS_HipBatten_{k + 1}_")]:
            vs = _verts(o)
            a = min(vs, key=lambda q: (q - s["Q0"]).dot(s["up"]))
            b = max(vs, key=lambda q: (q - s["Q0"]).dot(s["up"]))
            ua, ub = (a - s["Q0"]).dot(s["e"]), (b - s["Q0"]).dot(s["e"])
            j = 0
            while j * cover < s["L"] - 1e-6:
                for q in range(4):
                    u = j * cover + crests[q] + pitch / 2
                    if min(ua, ub) < u < max(ua, ub):
                        f = (u - ua) / (ub - ua)
                        v = ((a + (b - a) * f) - s["Q0"]).dot(s["up"])
                        p = s["Q0"] + s["e"] * u + s["up"] * v + s["n"] * zp
                        if _inside(p, s, D, 0.0):
                            put("pan", p, s["n"])
                j += 1
    for line in hips + [ridge_l]:   # cap screws where each wing edge crosses a rib
        side, up, tf = _frame(line["d"], line["pl"])
        Lw = (line["J"] - line["F"]).length
        for sg in (1, -1):
            e0 = line["F"] + side * sg * (FLASH["wing"] - 0.005)
            n_ = next(n for n, _ in line["pl"] if n.dot(side * sg) > 0)   # the line's plane on this side
            s = next(sd for sd in sides if (sd["n"] - n_).length < 1e-9)
            j = 0
            while j * cover < s["L"] - 1e-6:
                for q in range(5):
                    u = j * cover + crests[q]
                    # rib line u = const on plane s meets the edge line e0 + d·t (plan 2D)
                    dt = line["d"].xy
                    o_ = (s["Q0"] + s["e"] * u).xy
                    w = s["w"].xy
                    det = w.x * (-dt.y) - w.y * (-dt.x)
                    if abs(det) < 1e-9:
                        continue
                    rhs = e0.xy - o_
                    t = (w.x * rhs.y - w.y * rhs.x) / det
                    a_ = (rhs.x * (-dt.y) - rhs.y * (-dt.x)) / det   # along the rib (plan)
                    if (-FLASH["nose"] if line is not ridge_l else 0.0) < t < Lw and 0.0 <= a_ <= D:
                        p = e0 + line["d"] * t - up * ((FLASH["wing"] - 0.005) * tf) + up * FLASH["t"]   # on the wing
                        put("cap", p, s["n"])
                j += 1
    for kind, (bm, n) in S.items():
        _obj(c, f"MS_Screws_{kind}", bm, hd, element="piece", type={"rib": "MS2", "pan": "MS3", "cap": "MS4"}[kind],
             th=SCREW[kind], count=n[0])
    return {k: n[0] for k, (_, n) in S.items()}


def _lap_purlins(s, D, rows):
    """v of the purlins the sheet end laps sit on (build_metal_test centres each lap on one)."""
    vt, out, v = D / COS, [], _sheet_v0()
    pv = sorted(float(o.name.split("_")[-1]) for o in rows)
    while v + MS["length"] < vt:
        q = max(x for x in pv if x + MS["end_lap"] / 2 <= v + MS["length"])
        out.append(q)
        nv = q + MS["end_lap"] / 2 - MS["end_lap"]
        assert nv > v + 0.5, "sheet rows do not advance: purlins too far apart for the sheet length"
        v = nv
    return out


def selfcheck_metal():
    """Metal TEST against the SSR760 guide, read back from the model: สะพานหนู 10 cm off each hip, sheets cut
    2.5 cm short of the hips, top purlins 15 cm apart across the ridge, end laps on a purlin, hip caps 10 cm past
    the eave corner, screws placed."""
    c = bpy.data.collections[C_MS]
    E, sides, D, ze = _geom()
    R0, R1, ax = _ridge(E, sides, D, ze)
    hl = []   # hip plan lines (corner, unit direction)
    for ex, ey in E:
        R = min((R0, R1), key=lambda q: (q.xy - Vector((ex, ey))).length)
        hl.append((Vector((ex, ey)), (R.xy - Vector((ex, ey))).normalized(), (R.xy - Vector((ex, ey))).length))
    # plan distance to the nearest hip segment (corner → ridge end; a whole line would cross the far planes)
    dist = lambda p: min((p.xy - (a + u * max(0.0, min(L, (p.xy - a).dot(u))))).length for a, u, L in hl)
    bats = [o for o in c.objects if o.name.startswith("MS_HipBatten")]
    assert len(bats) == 8, f"{len(bats)} hip battens"
    for o in bats:
        vs = _verts(o)
        m = Vector(o.data["p0"]) + Vector(o.data["axis"]) * (o.data["len"] / 2)   # bottom centre, mid-length
        assert abs(dist(m) - MS["hip_batten"]) < 0.003, f"{o.name}: {dist(m):.3f} m off the hip"
    sheets = [o for o in c.objects if o.name.startswith("MS_Sheet")]
    near = min(dist(v) for o in sheets for v in _verts(o))
    assert MS["hip_gap"] - 0.002 < near < MS["hip_gap"] + 0.015, f"sheets come {near:.3f} m from a hip"
    rl = (R0.xy, ax.xy.normalized())
    for k in (1, 3) if abs(ax.y) > 0.5 else (0, 2):
        top = max((o for o in c.objects if o.name.startswith(f"MS_Purlin_{k + 1}_")), key=lambda o: float(o.name.split("_")[-1]))
        m = Vector(top.data["p0"])   # bottom centre
        g = abs((m.xy - rl[0]).cross(rl[1]))
        assert abs(g - MS["ridge_gap"] / 2) < 0.005, f"{top.name}: {g:.3f} m off the ridge (pair 15 cm apart)"
    for o in sheets:   # an upper sheet's lap (its lowest 10 cm) sits on a purlin
        k, j, r = o.name.split("_")[2:5]
        if r == "0":
            continue
        s = sides[int(k) - 1]
        v0 = min((v - s["Q0"]).dot(s["up"]) for v in _verts(o))
        pv = [float(p.name.split("_")[-1]) for p in c.objects if p.name.startswith(f"MS_Purlin_{k}_")]
        assert any(v0 - 0.002 < q < v0 + MS["end_lap"] + 0.002 for q in pv), f"{o.name}: end lap not on a purlin"
    for i, (a, u, _) in enumerate(hl):
        vs = _verts(bpy.data.objects[f"MS_Flash_Hip{i + 1}"])
        a = a - u * (FASCIA["sheet_over"] * math.sqrt(2))   # the sheets' corner, 15 cm past the fascia each way
        past = max(-(v.xy - a).dot(u) for v in vs)   # beyond the sheet corner, measured along the hip in plan
        exp = FLASH["nose"] * Vector((u.x, u.y, 0)).length * _cap_lines(RIB)[0][i]["d"].xy.length
        assert abs(past - exp) < 0.01, f"hip cap {i + 1}: {past:.3f} m past the corner, guide 10 cm ({exp:.3f} in plan)"
    for o in c.objects:   # purlins and สะพานหนู that run into steel are cut flush to it and welded
        if o.type == "MESH" and o.data.get("coped"):
            assert o.data.get("cut_by"), f"{o.name}: cut but sits on nothing"
            w = bpy.data.objects.get("WD_" + o.name[3:])
            assert w and w.data["length"] > 0.02, f"{o.name}: no weld"
    purl = [o for o in c.objects if o.name.startswith("MS_Purlin")]
    assert sum(1 for o in purl if o.data.get("coped")) >= len(purl) // 2, "purlins not cut to the สะพานหนู"
    from mathutils.kdtree import KDTree
    for o in [o for o in c.objects if o.name.startswith("MS_Screws")]:   # 28 vertices a screw; none doubled up
        vs = _verts(o)
        pts = [sum(vs[i:i + 8], Vector()) / 8 for i in range(0, len(vs), 28)]
        assert len(pts) == o.data["count"], f"{o.name}: {len(pts)} screws drawn, count {o.data['count']}"
        kd = KDTree(len(pts))
        for i, q in enumerate(pts):
            kd.insert(q, i)
        kd.balance()
        assert all(len(kd.find_range(q, 0.005)) == 1 for q in pts), f"{o.name}: two screws within 5 mm"
    n = {o.data["type"]: o.data["count"] for o in c.objects if o.name.startswith("MS_Screws")}
    assert len(n) == 3 and all(v > 0 for v in n.values()), f"screws: {n}"
    return f"metal ok: 8 สะพานหนู · sheets {near * 100:.1f} cm off the hips · laps on purlins · screws {n}"
