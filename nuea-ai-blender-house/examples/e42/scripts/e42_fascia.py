"""E42 ST07 ไม้เชิงชาย (spec 29 ต.ค.): SCG synthetic-wood installation manual §4.1 (p.12), SCG fascia catalogue,
CPAC manual p.7. Plumb fascia ("จันทันดิ่ง") on every eave:
  เหล็กฉาก 5×5×0.23 cm welded to each rafter end (rafters ≤ 1.00 m apart) → ไม้เชิงชาย 8" on the angles, 45 mm
  drill-point screws ×2 per rafter → over it a ไม้ปิดกันนกลอนคู่ 6" (CPAC: its top follows the tile rolls 2.5 cm
  above the batten tops) or a ไม้เชิงชาย 6" (metal sheet), 45 mm ×1 per rafter + 38 mm stitching @ 0.30 m.
Boards mitred 45° at the hip corners; the 70 cm eave is to the fascia's outer face (FASCIA, BACK in e42_roof).

    exec(<e42_struct>); exec(<e42_walls>); exec(<e42_roof>); exec(<e42_roof_trim>); exec(<this file>)
    build_roof(); build_fascia_frame(); build_cpac_trims(); build_fascia("cpac"); print(selfcheck_fascia("cpac"))
    build_metal_test(); build_metal_trims(); build_fascia("metal"); print(selfcheck_fascia("metal"))
"""
import math
from bisect import bisect_left
import bmesh
from mathutils import Vector

FB = dict(b8=("FB1", "ไม้เชิงชาย เอสซีจี ลายไม้ 8 นิ้ว (20 × 400 × 1.6 ซม.)", 4.0),
          b6=("FB2", "ไม้เชิงชาย เอสซีจี ลายไม้ 6 นิ้ว (15 × 400 × 1.6 ซม.)", 4.0),
          bird=("FB3", "ไม้ปิดกันนกลอนคู่ เอสซีจี (15 × 300 × 0.8 ซม.)", 3.0))
FSCREW = dict(s45="สกรูปลายสว่านมีปีก 45 มม. (ไม้เชิงชาย → เหล็กฉาก)", s38="สกรูปลายแหลม 38 มม. @ 0.30 ม. (ชั้นนอก → 8 นิ้ว)")


def _zr(s, o):
    """Rafter-top plane height at outward offset o from the eave line of side s (o < 0 is inward)."""
    return s["Q0"].z - o * TAN


def _board(bm, s, o1, o2, zlo, zhi, n=1):
    """A board on eave side s between outward offsets o1 < o2, mitred 45° at both corners; zlo(U)/zhi(U) give its
    bottom/top at world coordinate U along the eave (n segments along, for a shaped top)."""
    out = -s["w"]
    rings = []
    for i in range(n + 1):
        f = i / n
        ring = []
        for o, top in ((o1, False), (o1, True), (o2, True), (o2, False)):
            u = -o + f * (s["L"] + 2 * o)   # the board's face at offset o runs o past each corner (45° mitre)
            p = s["Q0"] + s["e"] * u + out * o
            U = s["Q0"].dot(s["e"]) + u
            ring.append(bm.verts.new((p.x, p.y, zhi(U) if top else zlo(U))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(4):
            bm.faces.new((r0[i], r0[(i + 1) % 4], r1[(i + 1) % 4], r1[i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def _disc(bm, p, n, r=0.004, t=0.001):
    """A screw head sunk flush in a board face (puttied over: SCG manual p.13)."""
    a = n.orthogonal().normalized()
    b = n.cross(a)
    lo = [bm.verts.new(p - n * t + (a * math.cos(math.tau * i / 8) + b * math.sin(math.tau * i / 8)) * r) for i in range(8)]
    hi = [bm.verts.new(p + (a * math.cos(math.tau * i / 8) + b * math.sin(math.tau * i / 8)) * r) for i in range(8)]
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    for i in range(8):
        bm.faces.new((lo[i], lo[(i + 1) % 8], hi[(i + 1) % 8], hi[i]))


def _tile_under(s, o, fallback):
    """top(U): the laid tiles' underside over the bird stop's outer face (offset o on side s), less 0.5 mm — the bird
    stop is cut to the tile rolls and the first course rests on it; past the tiles `fallback`."""
    tl = next(x for x in bpy.data.collections[C_CPAC].objects if x.name.endswith("CPAC_Tiles"))
    out, face = -s["w"], s["Q0"].dot(-s["w"]) + o
    pts = {}
    for v in tl.data.vertices:
        p = tl.matrix_world @ v.co
        if abs(p.dot(out) - face) < 0.04:
            U = round(p.dot(s["e"]), 3)
            z = p.z + (p.dot(out) - face) * TAN   # carried along the slope to the face
            pts[U] = min(pts.get(U, z), z)
    keys = sorted(pts)
    def top(U):
        near = [pts[k] for k in keys[max(0, bisect_left(keys, U) - 2):bisect_left(keys, U) + 2] if abs(k - U) < 0.02]
        return min(near) - 0.0005 if near else fallback
    return top


def _rafter_ends(k):
    """u along eave k of every rafter of that plane (from its stored start)."""
    s = _geom()[1][k]
    return sorted((Vector(o.data["p0"]) - s["Q0"]).dot(s["e"]) for o in bpy.data.collections[C_ROOF].objects
                  if o.name.startswith(f"RF_Rafter_{k + 1}_"))


def build_fascia_frame():
    """เหล็กฉาก 5×5×0.23 cm at every rafter end, welded to the rafter side (into C_ROOF, shared by both coverings)."""
    c = bpy.data.collections[C_ROOF]
    for o in [o for o in c.objects if o.name in ("RF_FasciaAngles", "WD_FasciaAngles")]:
        _rm(o)
    steel = mat("M_Steel_C", (0.05, 0.05, 0.055), 0.35, 1.0)
    leg, t, L = FASCIA["angle"]
    E, sides, D, ze = _geom()
    bm, welds, n = bmesh.new(), [], 0
    for k, s in enumerate(sides):
        out, zt = -s["w"], _zr(s, -BACK)
        for u in _rafter_ends(k):
            b = RAFTER["c"][1]
            base = s["Q0"] + s["e"] * u
            # leg against the fascia back, leg along the rafter's side (lip side), L tall from the rafter top down
            # face leg in front of the plumb cut (the 2.3 mm BACK keeps for it), side leg back along the rafter
            _cuboid(bm, Vector((*(base + out * (-BACK + t / 2)).xy, zt - L / 2)), [s["e"], out, Vector((0, 0, 1))], [leg / 2, t / 2, L / 2])
            q = base + s["e"] * (b / 2 + t / 2) + out * (-BACK + t - leg / 2)
            _cuboid(bm, Vector((*q.xy, zt - L / 2)), [s["e"], out, Vector((0, 0, 1))], [t / 2, leg / 2, L / 2])
            zb = zt - RAFTER["c"][0] / COS + 0.01   # rafter bottom at its end (plumb face h / cos)
            for oo in (-BACK + t - leg, -BACK - 0.002):   # along the side leg where it lies on the rafter
                p = base + s["e"] * (b / 2) + out * oo
                welds.append((Vector((p.x, p.y, zb)), Vector((p.x, p.y, zt - 0.005))))
            n += 1
    _obj(c, "RF_FasciaAngles", bm, steel, element="piece", type="FA1",
         th=f"เหล็กฉาก {leg * 1000:.0f}×{leg * 1000:.0f}×{t * 1000:.1f} มม. ยาว {L * 100:.0f} ซม. รับไม้เชิงชาย", count=n)
    _weld_obj(c, "WD_FasciaAngles", welds)
    return n


def build_fascia(which):
    """Fascia boards + screws for one covering: "cpac" (8" + bird stop, into C_CPAC) or "metal" (8" + 6", C_MS)."""
    cn, tag = (C_CPAC, "FA") if which == "cpac" else (C_MS, "MSF")
    c = bpy.data.collections[cn]
    for o in [o for o in c.objects if o.name.startswith(tag + "_")]:
        _rm(o)
    wood = mat("M_Fascia_SCG", (0.62, 0.42, 0.25), 0.55)
    head = mat("M_Screw", (0.75, 0.76, 0.78), 0.3, 0.9)
    E, sides, D, ze = _geom()
    t_a, t8, t6 = FASCIA["angle"][1], FASCIA["b8"][1], FASCIA["b6"][1]
    h8, h6 = FASCIA["b8"][0], FASCIA["b6"][0]
    S45, S38, n45, n38 = bmesh.new(), bmesh.new(), 0, 0
    for k, s in enumerate(sides):
        out = -s["w"]
        o8 = (-BACK + t_a, -BACK + t_a + t8)
        top8 = _zr(s, -BACK)   # flush with the rafter tops at their ends
        bm = bmesh.new()
        _board(bm, s, *o8, lambda U: top8 - h8, lambda U: top8)
        L8 = s["L"] + 2 * o8[1]
        _obj(c, f"{tag}_B8_{k + 1}", bm, wood, element="board", type=FB["b8"][0], th=FB["b8"][1], stock=FB["b8"][2],
             swept=True, butt=True, len=L8, axis=tuple(s["e"]), p0=tuple(s["Q0"] + s["e"] * -o8[1] + out * o8[1]))
        if which == "cpac":   # bird stop: top follows the tile rolls, 2.5 cm over the batten tops (CPAC p.7)
            ob = (-t6, -t6 + FASCIA["bird"][1])
            bed = _zr(s, ob[0]) + BATTEN["h"] / COS
            top = _tile_under(s, ob[1], bed + FASCIA["bird_rise"])   # cut to the tiles actually laid
            low = bed + FASCIA["bird_rise"] - FASCIA["bird"][0]
            bm = bmesh.new()
            _board(bm, s, *ob, lambda U: low, top, n=max(1, round(s["L"] / 0.01)))
            key, o2 = "bird", ob
        else:   # 6" board up to the purlin tops, the sheets pass over it
            ob = (-t6, 0.0)
            top6 = _zr(s, ob[1]) + MS["tube"][1] / COS - 0.003   # under the purlin-top plane at its outer face
            bm = bmesh.new()
            _board(bm, s, *ob, lambda U: top6 - h6, lambda U: top6)
            key, o2, low = "b6", ob, top6 - h6
        Lo = s["L"] + 2 * o2[1]
        _obj(c, f"{tag}_{key.upper()}_{k + 1}", bm, wood, element="board", type=FB[key][0], th=FB[key][1],
             stock=FB[key][2], swept=True, butt=True, len=Lo, axis=tuple(s["e"]),
             p0=tuple(s["Q0"] + s["e"] * -o2[1] + out * o2[1]))
        # screws (SCG p.12): 8" ×2 per rafter (3 cm and 10 cm down), outer layer ×1 per rafter + 38 mm @ 0.30
        for u in _rafter_ends(k):
            for dz in (0.03, 0.10):
                _disc(S45, Vector((*(s["Q0"] + s["e"] * u + out * o8[1]).xy, top8 - dz)), out)
                n45 += 1
            _disc(S45, Vector((*(s["Q0"] + s["e"] * u + out * o2[1]).xy, low + 0.05)), out)
            n45 += 1
        u = 0.15
        while u < s["L"] - 0.1:
            _disc(S38, Vector((*(s["Q0"] + s["e"] * u + out * o2[1]).xy, low + 0.02)), out)
            n38 += 1
            u += 0.30
    _obj(c, f"{tag}_Screws45", S45, head, element="piece", type="FS1", th=FSCREW["s45"], count=n45)
    _obj(c, f"{tag}_Screws38", S38, head, element="piece", type="FS2", th=FSCREW["s38"], count=n38)
    return n45, n38


def selfcheck_fascia(which):
    """The fascia against the manuals, read from the model: 8" top flush with the rafter tops, the outer layer
    (bird stop 2.5 cm over the batten tops / 6" under the purlin tops), the covering's overhang past the fascia,
    a welded angle at every rafter end, mitred corners closing."""
    cn, tag = (C_CPAC, "FA") if which == "cpac" else (C_MS, "MSF")
    c = bpy.data.collections[cn]
    E, sides, D, ze = _geom()
    assert "RF_FasciaAngles" in bpy.data.objects and "WD_FasciaAngles" in bpy.data.objects, "no fascia angles"
    angles = _verts(bpy.data.objects["RF_FasciaAngles"])
    n_raf = sum(1 for o in bpy.data.collections[C_ROOF].objects if o.name.startswith("RF_Rafter_"))
    assert len(angles) == 16 * n_raf, f"{len(angles) // 16} angles drawn for {n_raf} rafters"
    assert len(bpy.data.objects["WD_FasciaAngles"].data.splines) >= 2 * n_raf, "not every angle welded"
    outer = "BIRD" if which == "cpac" else "B6"
    for k, s in enumerate(sides):
        out = -s["w"]
        o0 = (s["Q0"]).dot(out)
        raf = [o for o in bpy.data.collections[C_ROOF].objects if o.name.startswith(f"RF_Rafter_{k + 1}_")]
        rv = [v for o in raf for v in _verts(o)]
        r_end = max(v.dot(out) for v in rv)
        r_top = max(v.z for v in rv if v.dot(out) > r_end - 1e-4)
        b8 = _verts(bpy.data.objects[f"{tag}_B8_{k + 1}"])
        assert abs(max(v.z for v in b8) - r_top) < 1e-3, f"8\" fascia {k + 1}: top off the rafter tops"
        ang = [v for v in angles if abs(v.dot(out) - r_end) < 0.06 and -0.05 < (v - s["Q0"]).dot(s["e"]) < s["L"] + 0.05
               and abs((v - s["Q0"]).dot(s["w"]) - BACK) < 0.06]
        assert ang and abs(min(v.dot(out) for v in ang) - (r_end - FASCIA["angle"][0] + FASCIA["angle"][1])) < 1e-4, \
            f"angles {k + 1}: side legs not back along the rafters"
        assert abs(min(v.dot(out) for v in b8) - max(v.dot(out) for v in ang)) < 1e-4, f"8\" fascia {k + 1}: not on the angles"
        assert abs(max(v.dot(out) for v in ang) - r_end - FASCIA["angle"][1]) < 1e-4, f"angles {k + 1}: face leg not on the rafter ends"
        ov = _verts(bpy.data.objects[f"{tag}_{outer}_{k + 1}"])
        face = max(v.dot(out) for v in ov)
        if which == "cpac":
            # batten tops measured from the battens of this plane, carried to the bird stop's back face
            bt = max((v - s["Q0"]).dot(s["n"]) for o in bpy.data.collections[C_CPAC].objects
                     if o.name.startswith(f"RF_Batten_{k + 1}_") for v in _verts(o))
            ob0 = min(v.dot(out) for v in ov) - o0
            bed = s["Q0"].z + bt / COS - ob0 * TAN
            tops = [v.z for v in ov if v.z > bed]
            # CPAC p.7: 2.5 cm over the batten tops; the model's first course sits ~2.2 there (cpac_tiles' fixed lift)
            assert abs(min(tops) - (bed + FASCIA["bird_rise"])) < 0.004, f"bird stop {k + 1}: top {(min(tops) - bed) * 100:.1f} cm over the battens"
            tl = next(o for o in bpy.data.collections[C_CPAC].objects if o.name.endswith("CPAC_Tiles"))
            up_ = lambda p: (p - s["Q0"]).dot(s["up"])
            tv = [tl.matrix_world @ v.co for v in tl.data.vertices]   # the tiles' underside (no Solidify)
            tv = [p for p in tv if 0.3 < (p - s["Q0"]).dot(s["e"]) < s["L"] - 0.3 and up_(p) < 0.2]
            edge = min(up_(p) for p in tv)
            row = [p for p in tv if up_(p) < edge + 1e-4]   # the eave edge of the first course
            trough = min(p.dot(out) for p in row)
            assert abs(trough - face - FASCIA["tile_over"]) < 0.006, f"tiles overhang fascia {k + 1} by {(trough - face) * 100:.1f} cm under a trough"
            # over the bird stop the tile underside stays just above its shaped top, all along (phase and height)
            gaps = []
            for p in tv:
                u = (p - s["Q0"]).dot(s["e"])
                if abs(p.dot(out) - face) < 0.04:
                    bird = [v.z for v in ov if abs((v - s["Q0"]).dot(s["e"]) - u) < 0.006 and v.z > bed]
                    if bird:
                        gaps.append(p.z + (p.dot(out) - face) * TAN - max(bird))   # underside carried to the bird face
            assert gaps and min(gaps) > -1e-4 and max(gaps) < 0.015, \
                f"bird stop {k + 1} vs tile underside: gap {min(gaps) * 1000:.1f} to {max(gaps) * 1000:.1f} mm"
        else:
            sh = [v for o in c.objects if o.name.startswith(f"MS_Sheet_{k + 1}_") for v in _verts(o)
                  if abs((v - s["Q0"]).dot(s["e"]) - s["L"] / 2) < 1.0]
            reach = max(v.dot(out) for v in sh)
            exp = FASCIA["sheet_over"] + (MS["c_h"] + 0.002) * SIN   # pans 15 cm out; the ribs stand a little further
            assert abs(reach - face - exp) < 0.004, f"sheets overhang fascia {k + 1} by {(reach - face) * 100:.1f} cm ({exp * 100:.1f})"
            fm = [v for o in c.objects if o.name.startswith(f"MS_Foam_{k + 1}_") for v in _verts(o)]
            lo_n = min((v - s["Q0"]).dot(s["n"]) for v in fm)   # the foam underside plane, carried to the board face
            under = s["Q0"].z + lo_n / COS - (face - s["Q0"].dot(out)) * TAN
            assert max(v.z for v in ov) < under, f"6\" fascia {k + 1} pokes {(max(v.z for v in ov) - under) * 1000:.1f} mm above the sheets' underside"
        # mitre: this side's outer face meets the next side's at the corner (plan)
        nx = sides[(k + 1) % 4]
        a = max(ov, key=lambda v: (v - s["Q0"]).dot(s["e"])).xy
        nv = _verts(bpy.data.objects[f"{tag}_{outer}_{(k + 1) % 4 + 1}"])
        b = min(nv, key=lambda v: (v - nx["Q0"]).dot(nx["e"])).xy
        assert (a - b).length < 0.002, f"fascia corner {k + 1}/{(k + 1) % 4 + 1} open by {(a - b).length * 1000:.1f} mm"
    return f"fascia {which} ok: 4 eaves · 8\" + {outer.lower()} · {n_raf} angles welded · corners mitred"
