"""E42 structure rebuilt in construction order for quantity take-off (training with the user, 28 ต.ค. 69).

One stage per call, the user checks each before the next:
  ST00 grid · ST01 ฐานแผ่ F1 (pit, compacted sand, lean concrete, rebar mat, footing concrete)
  ST02 ตอม่อ P1 (stub concrete footing top → ground-beam bottom, starter bars, ties)
  ST03 คานคอดิน GB1 (clear spans between joints, lean concrete, bars, stirrups) + joints J1 + backfill
  ST04 พื้นหล่อบนดิน GS1 (compacted fill to the beam top, wire mesh, slab) per zone: House, Porch, Bath (−10 cm)
  ST05 เสา C1 (joint top → under the wall plate, ties from the stub top; bars from ST02); cast before the slab

Each footing = an empty F1_<grid> at the footing's bottom centre, parenting one object per work item:
_Exc (pit: wire, take-off only, never rendered/exported), _Sand, _Lean, _Conc, _Rebar (curve, one spline per bar).
Each stub = an empty P1_<grid> at the footing top with _Conc, _Bars, _Ties.
Each beam line = an empty GB1_<a>-<b> at its start grid point, beam top, with _Conc, _Lean, _Bars, _Stirrups;
each joint = an empty J1_<grid> at the stub top with _Conc.
Identical elements share their mesh/curve data, so a type is defined once and placed many times.
The old merged structure of e42_build.build_structure stays in an excluded "E42 Structure OLD" until every
stage is rebuilt.

    exec(bpy.data.texts["house_helpers"].as_string())    # mat()
    exec(open(<this file>).read()); build_grid(); build_footings(); build_stubs(); build_ground_beams()
    build_columns(); build_ground_slab(); for c in STAGES: print(report(c))
    print(selfcheck())
"""
import bpy, bmesh, itertools, math

GL = 0.00                                          # ระดับดินเดิม = top of Ground
GX = {"1": 0.0, "2": 3.0, "3": 6.0}               # grid lines (column centres), numbers along x
GY = {"A": 0.0, "B": 1.5, "C": 3.0, "D": 4.5, "E": 7.5}   # letters along y, front -> rear
# spec 28 ต.ค.: columns at most MAX_COL_SPAN apart centre to centre along a beam line (more is wasteful) — B2, B3,
# C1, C2 dropped; the beams that ended there (B2–B3, C1–C2) now rest on other beams.
FOOTINGS = {"F1": ["A1", "A2", "A3", "D1", "D2", "D3", "E1", "E2", "E3"]}
MAX_COL_SPAN = 4.50
# B×B×T footing on lean + sand (`pad` wider each side) at the bottom of a pit dug to level `exc`, `work` wider
# than the footing. Rebar mat: bar d @ s both ways, side/bottom/top cover, ends bent up `hook` (centreline, sharp bends).
TYPES = {"F1": dict(B=1.00, T=0.25, exc=-1.50, sand=0.05, lean=0.05, pad=0.05, work=0.30,   # exc: spec 28 ต.ค.
                    d=0.012, s=0.15, side=0.05, bottom=0.075, top=0.03, hook=0.12,
                    grade="St.240 ksc", bar="DB12 SD40")}
TYPES = {k: {**t, "bot": t["exc"] + t["sand"] + t["lean"]} for k, t in TYPES.items()}   # footing bottom
# Ground beams 0.20×0.40 by top level (e42_build GB_HOUSE/GB_PORCH); the stage that builds them is ST03.
# Floor (spec 28 ต.ค.): cast slab on ground — soil filled to the beam top, wire mesh 4 mm, slab 7 cm + tiles 3 cm,
# finished floor kept at +0.45 (porch +0.40), so beam tops = floor − 0.10.
GB_D = 0.40
# Round the bath the beams sit 10 cm lower across their whole section (spec 29 ต.ค.: no ledge in the bath): C1-C2,
# D1-D2, and the whole of A1-E1 / A2-E2 (the bath is mid-span of their 4.50 m A–D span; split at D, A2–D2 lost its
# continuity over D2 and failed GB4, so the lines stay whole); a concrete curb cast with the slab fills over them up to
# the slab bottom outside the bath. They step 10 cm at the columns A1, E1, E2 and at the beam end B2.
GB_LINES = [(a, b, 0.35) for a, b in (("A1", "A2"), ("E1", "E3"), ("B3", "E3"), ("B2", "B3"))] + \
           [(a, b, 0.25) for a, b in (("A1", "E1"), ("A2", "E2"), ("C1", "C2"), ("D1", "D2"))] + \
           [(a, b, 0.30) for a, b in (("A2", "A3"), ("A3", "B3"))]   # porch edge: floor 0.40, 5 cm lower
STUB_GRIDS = {"P1": FOOTINGS["F1"]}
# b×b stub cast footing top → lowest beam bottom over it (the beam pour takes the joint). The column bars are one
# piece (spec 28 ต.ค.): L-foot on the mat, up through stub, joint and column to the underside of the column-top
# plate, bent 90° `bend` there (pinwheel, welded under the plate; the user: 6 cm, so a bar stays ≤ 5 m = two from a
# 10 m stock bar) — set in this stage, no lap. They stand where the col×col column needs them (col_cover), the ties wrap them tight,
# so the stub cover must reach soil_cover (stub and column both 0.20: cover 4 cm for both).
STUBS = {"P1": dict(b=0.20, col=0.20, col_cover=0.04, soil_cover=0.04, d=0.012, foot=0.20, bend=0.06,
                    dt=0.006, s=0.15, first=0.05, hook=0.075, grade="St.240 ksc", bar="DB12 SD40", tie="RB6 SR24")}
# Every GB_LINES beam is SS-02 S-22 GB1 (e42_gb_design.py, slab on ground: walls + self-weight only): b × GB_D
# between the joints, 2 top + 2 bottom bars d running the whole line with 90° hooks into the end joints (no laps:
# a line must fit one stock bar), plus the special bars on the tension side (spec 28 ต.ค.; S-22 draws them on the
# compression side): 1 bottom bar 0.8 L centred in each span, 1 top bar from each column centre L/4 into every
# span beside it (hooked into the joint at a line end). L = column-centre span. Stirrups dt @ s in each clear span
# with 135° hooks, lean concrete `pad` wider each side, trench dug from the lean's bottom to GL where it is below GL.
# Joints J1 (stub b × b, lowest beam bottom → highest beam top) are cast with the beams.
GBEAM = dict(type="GB1", b=0.20, lean=0.05, pad=0.05, cover=0.03, d=0.012, hook=0.15, dt=0.006, s=0.15, first=0.05,
             shook=0.075, mid=0.8, sup=0.25, grade="St.240 ksc", bar="DB12 SD40", tie="RB6 SR24")
# Depth and special bars (n_sp per place) per type; GB4 0.20 × 0.50 is not in S-22: spec 28 ต.ค. (option 1) for the
# two 4.50 m beams that carry secondary beams once B2/B3/C1/C2 lost their columns (e42_gb_design.py).
BEAM_TYPES = {"GB1": dict(h=0.40, n_sp=1), "GB4": dict(h=0.50, n_sp=2)}
LINE_TYPE = {"A1-E1": "GB4", "A2-E2": "GB4"}       # every other line GB1
# Slab on ground (spec 28 ต.ค.): compacted soil filled from GL to the beam top inside the beams, wire mesh, slab t
# cast over fill and beams out to the beams' outer faces; the tiles' 3 cm come with the finishes. Zones: plan rects
# (x0, y0, x1, y1) and their beam top. Mesh @ ms both ways, mcover from the slab edge, wires at mz above the bottom.
SLAB = dict(type="GS1", t=0.07, md=0.004, ms=0.20, mcover=0.05, mz=0.035, grade="St.240 ksc",
            mesh="Wire mesh 4 มม. @0.20")
# A zone listed later is cut out of the ones before it (the bath, set 10 cm down between its beams: spec 28 ต.ค.).
ZONES = {"House": ([(-0.10, -0.10, 3.10, 7.60), (3.10, 1.40, 6.10, 7.60)], 0.35),
         "Porch": ([(3.10, -0.10, 6.10, 1.40)], 0.30),
         "Bath": ([(-0.025, 3.045, 3.025, 4.455)], 0.25)}   # to the bath's plaster faces (e42_walls), over the lowered beams
# Column C1 b × b on every stub (spec 28 ต.ค.: 0.20 × 0.20), from the highest beam top over it (joint top) up to
# `top` = floor +0.45 + 3.00 = underside of the steel wall plate (อะเส; no roof beam), capped by a steel plate
# plate × plate × pt (the user: 16 × 16 cm, 6 mm) whose top is `top`. Its bars come from the stub stage. Ties dt @ s run
# from the stub top through the ground-beam joint up the column, first/last 5 cm from the ends.
COL = dict(type="C1", b=0.20, cover=0.04, dt=0.006, s=0.15, first=0.05, shook=0.075, top=3.45, plate=0.16, pt=0.006,
           grade="St.240 ksc", tie="RB6 SR24", plate_spec="เพลทหัวเสา 160×160×6 มม.")
KG_M = {4: 0.099, 6: 0.222, 9: 0.499, 12: 0.888, 16: 1.578}
STOCK = 10.0                                       # rebar sold in 10 m bars
C_GRID, C_FOOT, C_STUB, C_OLD = "E42 ST00 Grid", "E42 ST01 Footings", "E42 ST02 Stubs", "E42 Structure OLD"
C_GB, C_SLAB, C_COL = "E42 ST03 Ground Beams", "E42 ST04 Ground Slab", "E42 ST05 Columns"
C_WALL = "E42 ST06 Walls"                          # built by e42_walls.py
STAGES = [C_FOOT, C_STUB, C_GB, C_COL, C_SLAB, C_WALL]   # cast in this order: columns go up before the slab


def _coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def _clear(name):
    c = _coll(name)
    for o in list(c.objects):
        bpy.data.objects.remove(o)
    return c


def _drop(store, name):
    d = store.get(name)
    if d:
        store.remove(d)


def _find_lc(lc, name):
    if lc.collection.name == name:
        return lc
    for ch in lc.children:
        f = _find_lc(ch, name)
        if f:
            return f


def retire_old():
    """Old merged Str_* objects -> excluded collection, so nothing is counted twice."""
    new, old = bpy.data.collections.get("E42 Structure"), bpy.data.collections.get(C_OLD)
    if new and old:   # e42_build ran again: merge, a rename would give an unexcluded "... OLD.001"
        for o in list(new.objects):
            if o.name not in old.objects:
                old.objects.link(o)
            new.objects.unlink(o)
        bpy.data.collections.remove(new)
    elif new:
        new.name = C_OLD
    if bpy.data.collections.get(C_OLD):
        for vl in bpy.context.scene.view_layers:
            lc = _find_lc(vl.layer_collection, C_OLD)
            if lc:
                lc.exclude = True


def _box_data(name, x0, y0, z0, x1, y1, z1, m=None, **props):
    return _boxes_data(name, [(x0, y0, z0, x1, y1, z1)], m, **props)


def _boxes_data(name, boxes, m=None, **props):
    """One mesh of disjoint boxes, 8 vertices each in creation order (_obj_boxes reads them back that way)."""
    _drop(bpy.data.meshes, name)
    bm = bmesh.new()
    for x0, y0, z0, x1, y1, z1 in boxes:
        assert min(x1 - x0, y1 - y0, z1 - z0) > 1e-6, f"{name}: a box under 1 µm thick ({x0:.4f}, {y0:.4f}, {z0:.4f})"   # it would double a face
        for v in bmesh.ops.create_cube(bm, size=1.0)["verts"]:   # outward normals
            v.co = (x0 if v.co.x < 0 else x1, y0 if v.co.y < 0 else y1, z0 if v.co.z < 0 else z1)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if m:
        me.materials.append(m)
    me.update(calc_edges=True)
    for k, v in props.items():
        me[k] = v
    return me


def _mat_bars(t):
    """Two layers of hooked bars: [(points...), ...] relative to the footing bottom centre."""
    d, e = t["d"], t["B"] / 2 - t["side"] - t["d"] / 2
    n = math.ceil(2 * e / t["s"] - 1e-9) + 1        # spacing never above s
    assert t["bottom"] + 2 * d + t["hook"] <= t["T"] - t["top"] + 1e-9, "hooks leave less than the top cover"
    bars = []
    for layer, (ee, z) in enumerate(((e, t["bottom"] + d / 2), (e - d, t["bottom"] + 1.5 * d))):
        for i in range(n):
            p = -ee + i * 2 * ee / (n - 1)
            pts = [(-ee, p, z + t["hook"]), (-ee, p, z), (ee, p, z), (ee, p, z + t["hook"])]
            bars.append([(y, x, z) for x, y, z in pts] if layer else pts)   # layer 2 runs along y
    return bars


def _bt(name):
    """(type name, spec) of beam line `name` (a-b as in GB_LINES)."""
    tn = LINE_TYPE.get(name, GBEAM["type"])
    return tn, BEAM_TYPES[tn]


def _tops_at(g):
    """(top, bottom) of every ground beam passing over grid point g (ends included)."""
    x, y = GX[g[1:]], GY[g[0]]
    for a, b, _ in GB_LINES:
        assert a[0] == b[0] or a[1:] == b[1:], f"beam {a}-{b} not along a grid line"
    assert set(LINE_TYPE) <= {f"{a}-{b}" for a, b, _ in GB_LINES}, "LINE_TYPE names a line that is not in GB_LINES"
    return [(top, top - _bt(f"{a}-{b}")[1]["h"]) for a, b, top in GB_LINES
            if (GX[a[1:]] == GX[b[1:]] == x and min(GY[a[0]], GY[b[0]]) <= y <= max(GY[a[0]], GY[b[0]])) or
            (GY[a[0]] == GY[b[0]] == y and min(GX[a[1:]], GX[b[1:]]) <= x <= max(GX[a[1:]], GX[b[1:]]))]


def _nodes():
    """Every beam joint: stubs and beam ends (a beam may rest on another beam) → (bottom, top, width)."""
    stubs = {g: STUBS[sn]["b"] for sn, gs in STUB_GRIDS.items() for g in gs}
    out = {}
    for g in set(stubs) | {e for a, b, _ in GB_LINES for e in (a, b)}:
        tb = _tops_at(g)
        out[g] = (min(b for _, b in tb), max(t for t, _ in tb), stubs.get(g, GBEAM["b"]))
    return out


def _stub_levels():
    """grid -> (stub bottom = footing top, stub top = lowest beam bottom, highest beam top, starter foot z)."""
    lv = {}
    for sn, gs in STUB_GRIDS.items():
        for g in gs:
            tb = _tops_at(g)
            ft = [k for k, v in FOOTINGS.items() if g in v]
            assert tb and len(ft) == 1, f"stub {g}: no ground beam over it or no footing under it"
            f = TYPES[ft[0]]
            lv[g] = (f["bot"] + f["T"], min(b for _, b in tb), max(t for t, _ in tb), f["bot"] + f["bottom"] + 2 * f["d"])
    return lv


def _stub_bars(t, h, zf, top):
    """Starter bars and ties relative to the stub bottom centre; zf = foot z, top = bar top."""
    m = t["col"] / 2 - t["col_cover"] - t["dt"] - t["d"] / 2      # bar centre, from the column's cover
    a = m + t["d"] / 2 + t["dt"] / 2                                # tie centreline, tight on the bars
    assert t["b"] / 2 - a - t["dt"] / 2 >= t["soil_cover"] - 1e-9, "stub cover below soil_cover"
    assert h > 2 * t["first"], "stub too short for ties"
    assert t["bend"] <= 2 * m - t["d"] + 1e-9, "top bends would hit the next corner bar"
    zf += t["d"] / 2                                                # foot rests on the mat's top layer
    bend = lambda sx, sy: (sx * (m - t["bend"]), sy * m, top) if sx == sy else (sx * m, sy * (m - t["bend"]), top)
    mains = [[(sx * (m + t["foot"]), sy * m, zf), (sx * m, sy * m, zf), (sx * m, sy * m, top), bend(sx, sy)]
             for sx in (-1, 1) for sy in (-1, 1)]               # top bends turn round like a pinwheel, not an X
    nt = math.ceil((h - 2 * t["first"]) / t["s"] - 1e-9) + 1       # spacing never above s
    k = a - t["hook"] / math.sqrt(2)                                # 135° hooks into the core
    ties = [[(k, k, z), (a, a, z), (-a, a, z), (-a, -a, z), (a, -a, z), (a, a, z), (k, k, z)]
            for z in (t["first"] + i * (h - 2 * t["first"]) / (nt - 1) for i in range(nt))]
    return mains, ties, nt, a


def _rebar_data(name, bars, d, m, **props):
    _drop(bpy.data.curves, name)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = d / 2
    cu.bevel_resolution = 1
    cu.use_fill_caps = True
    for pts in bars:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for P, c in zip(sp.points, pts):
            P.co = (*c, 1.0)
    cu.materials.append(m)
    for k, v in props.items():
        cu[k] = v
    return cu


def build_grid(ext=0.8, size=0.5):
    """ST00: grid lines at ground level + labels (helpers, never rendered)."""
    c = _clear(C_GRID)
    ink = mat("M_GridLabel", (0.95, 0.80, 0.15), 0.5)   # grey default text vanished on the grey viewport grid
    xs, ys = sorted(GX.values()), sorted(GY.values())
    V, E = [], []
    for x in xs:
        V += [(x, ys[0] - ext, GL), (x, ys[-1] + ext, GL)]
        E.append((len(V) - 2, len(V) - 1))
    for y in ys:
        V += [(xs[0] - ext, y, GL), (xs[-1] + ext, y, GL)]
        E.append((len(V) - 2, len(V) - 1))
    _drop(bpy.data.meshes, "Grid_Lines")
    me = bpy.data.meshes.new("Grid_Lines")
    me.from_pydata(V, E, [])
    objs = [bpy.data.objects.new("Grid_Lines", me)]
    labels = [(k, (x, ys[0] - ext - size, GL)) for k, x in GX.items()] + \
             [(k, (xs[0] - ext - size, y, GL)) for k, y in GY.items()]
    for k, loc in labels:
        _drop(bpy.data.curves, f"Grid_{k}")
        tx = bpy.data.curves.new(f"Grid_{k}", "FONT")
        tx.body, tx.size, tx.align_x, tx.align_y = k, size, "CENTER", "CENTER"
        tx.materials.append(ink)
        o = bpy.data.objects.new(f"Grid_{k}", tx)
        o.location = loc
        objs.append(o)
    for o in objs:
        o.hide_render = True
        c.objects.link(o)
    return len(objs)


def build_footings():
    """ST01: every footing type in TYPES at its grid points in FOOTINGS."""
    pts = [g for v in FOOTINGS.values() for g in v]
    assert len(pts) == len(set(pts)) and set(FOOTINGS) == set(TYPES), "grid point used twice or type without size"
    retire_old()
    c = _clear(C_FOOT)
    conc = bpy.data.materials.get("rough_concrete_material_Str_Footings") or mat("M_Concrete", (0.50, 0.50, 0.48), 0.85)
    lean = mat("M_LeanConcrete", (0.30, 0.30, 0.28), 0.95)
    sand = mat("M_Sand", (0.76, 0.68, 0.52), 0.95)
    steel = mat("M_Rebar", (0.28, 0.17, 0.11), 0.55, 0.6)
    n = 0
    for tn, t in TYPES.items():
        h, q, w = t["B"] / 2, t["B"] / 2 + t["pad"], t["B"] / 2 + t["work"]
        zs, zl = -(t["sand"] + t["lean"]), -t["lean"]
        D = {
            "Exc": _box_data(f"{tn}_Exc", -w, -w, zs, w, w, GL - t["bot"], None,
                             element="excavation", th="ขุดดินฐานราก", type=tn),
            "Sand": _box_data(f"{tn}_Sand", -q, -q, zs, q, q, zl, sand,
                              element="sand", th=f"ทรายหยาบอัดแน่น {t['sand'] * 100:.0f} ซม.", type=tn),
            "Lean": _box_data(f"{tn}_Lean", -q, -q, zl, q, q, 0, lean,
                              element="lean_concrete", th=f"คอนกรีตหยาบ {t['lean'] * 100:.0f} ซม.", type=tn),
            "Conc": _box_data(f"{tn}_Conc", -h, -h, 0, h, h, t["T"], conc,
                              element="concrete", th="คอนกรีตฐานราก", type=tn, grade=t["grade"]),
            "Rebar": _rebar_data(f"{tn}_Rebar", _mat_bars(t), t["d"], steel, element="rebar", th="เหล็กเสริมฐานราก", type=tn,
                                 bar=t["bar"], dia_mm=round(t["d"] * 1000), spacing=t["s"]),
        }
        for g in FOOTINGS[tn]:
            root = bpy.data.objects.new(f"{tn}_{g}", None)
            root.empty_display_type, root.empty_display_size = "PLAIN_AXES", 0.3
            root.location = (GX[g[1:]], GY[g[0]], t["bot"])
            root["grid"], root["type"] = g, tn
            c.objects.link(root)
            for k, data in D.items():
                o = bpy.data.objects.new(f"{tn}_{g}_{k}", data)
                o.parent = root
                c.objects.link(o)
                if k == "Exc":
                    o.display_type, o.hide_render = "WIRE", True
            n += 1
    return n


def build_stubs():
    """ST02: stubs of STUBS at STUB_GRIDS; stubs of equal height and bar top share one set of data."""
    pts = [g for v in STUB_GRIDS.values() for g in v]
    assert len(pts) == len(set(pts)) and set(STUB_GRIDS) == set(STUBS) and not set(STUBS) & set(TYPES), \
        "grid point used twice, stub type without size, or stub type named like a footing type"
    lv = _stub_levels()
    c = _clear(C_STUB)
    conc = bpy.data.materials.get("rough_concrete_material_Str_Footings") or mat("M_Concrete", (0.50, 0.50, 0.48), 0.85)
    steel = mat("M_Rebar", (0.28, 0.17, 0.11), 0.55, 0.6)
    n = 0
    for sn, t in STUBS.items():
        shared = {}
        for g in STUB_GRIDS[sn]:
            zb, zt, beam_top, zf = lv[g]
            h, top = zt - zb, COL["top"] - COL["pt"] - t["d"] / 2 - zb   # bar centre just under the plate
            key = f"{sn}_H{round(h * 100)}_T{round(top * 100)}"
            if key not in shared:
                mains, ties, _, _ = _stub_bars(t, h, zf - zb, top)
                w = t["b"] / 2
                shared[key] = ((round(h, 6), round(top, 6), round(zf - zb, 6)), {
                    "Conc": _box_data(f"{key}_Conc", -w, -w, 0, w, w, h, conc,
                                      element="concrete", th="คอนกรีตตอม่อ", type=sn, grade=t["grade"]),
                    "Bars": _rebar_data(f"{key}_Bars", mains, t["d"], steel, element="rebar",
                                        th="เหล็กยืนเสา (เส้นเดียวจากฐานถึงปลายเสา)", type=sn, bar=t["bar"], dia_mm=round(t["d"] * 1000)),
                    "Ties": _rebar_data(f"{key}_Ties", ties, t["dt"], steel, element="ties", th="เหล็กปลอกตอม่อ",
                                        type=sn, bar=t["tie"], dia_mm=round(t["dt"] * 1000), spacing=t["s"]),
                })
            levels, D = shared[key]
            assert levels == (round(h, 6), round(top, 6), round(zf - zb, 6)), f"{key}: same name, other levels"
            root = bpy.data.objects.new(f"{sn}_{g}", None)
            root.empty_display_type, root.empty_display_size = "PLAIN_AXES", 0.2
            root.location = (GX[g[1:]], GY[g[0]], zb)
            root["grid"], root["type"] = g, sn
            c.objects.link(root)
            for k, data in D.items():
                o = bpy.data.objects.new(f"{sn}_{g}_{k}", data)
                o.parent = root
                c.objects.link(o)
            n += 1
    return n


def _xy(g):
    return GX[g[1:]], GY[g[0]]


def _gb_lines():
    """Beam lines (name, axis 0=x/1=y, start xy, top, length, [(u, grid) joints along it]). A line ends on a stub or
    on another beam; along a grid line the columns stand at most MAX_COL_SPAN apart."""
    stubs = [g for gs in STUB_GRIDS.values() for g in gs]
    nodes = set(stubs) | {e for a, b, _ in GB_LINES for e in (a, b)}
    on_line = lambda g, a, b: (_xy(g)[0] == _xy(a)[0] == _xy(b)[0] and
                               min(_xy(a)[1], _xy(b)[1]) <= _xy(g)[1] <= max(_xy(a)[1], _xy(b)[1])) or \
                              (_xy(g)[1] == _xy(a)[1] == _xy(b)[1] and
                               min(_xy(a)[0], _xy(b)[0]) <= _xy(g)[0] <= max(_xy(a)[0], _xy(b)[0]))
    for a, b, _ in GB_LINES:
        for e in (a, b):
            assert e in stubs or any(on_line(e, c, d) for c, d, _ in GB_LINES if (c, d) != (a, b)), \
                f"beam {a}-{b}: end {e} on neither a column nor another beam"
    for ax in (0, 1):   # column spacing per grid line, across collinear beams
        for k in {(_xy(a)[1 - ax]) for a, b, _ in GB_LINES if _xy(a)[1 - ax] == _xy(b)[1 - ax]}:
            iv = sorted(tuple(sorted((_xy(a)[ax], _xy(b)[ax]))) for a, b, _ in GB_LINES
                        if _xy(a)[1 - ax] == _xy(b)[1 - ax] == k)
            runs = []
            for lo, hi in iv:
                if runs and lo <= runs[-1][1] + 1e-9:
                    runs[-1][1] = max(runs[-1][1], hi)
                else:
                    runs.append([lo, hi])
            for lo, hi in runs:
                us = sorted(_xy(g)[ax] for g in stubs if _xy(g)[1 - ax] == k and lo - 1e-9 <= _xy(g)[ax] <= hi + 1e-9)
                assert all(v - u <= MAX_COL_SPAN + 1e-9 for u, v in zip(us, us[1:])), \
                    f"columns more than {MAX_COL_SPAN} m apart on grid line {'yx'[ax]} = {k}"
    out = []
    for a, b, top in GB_LINES:
        pa, pb = _xy(a), _xy(b)
        assert pa[0] == pb[0] or pa[1] == pb[1], f"beam {a}-{b} not along a grid line"
        ax = 0 if pa[1] == pb[1] else 1
        if pa[ax] > pb[ax]:
            a, b, pa, pb = b, a, pb, pa
        G = pb[ax] - pa[ax]
        on = sorted((_xy(g)[ax] - pa[ax], g) for g in nodes
                    if _xy(g)[1 - ax] == pa[1 - ax] and 0 <= _xy(g)[ax] - pa[ax] <= G)
        out.append((f"{a}-{b}", ax, pa, top, G, on))
    return out


def _spans(on, jb):
    """Clear spans (u0, u1) between the joint faces along a line."""
    return [(u0 + jb[g0] / 2, u1 - jb[g1] / 2) for (u0, g0), (u1, g1) in zip(on, on[1:])]


def _pt(ax, u, v, z):
    """Point from coordinates along (u) and across (v) a beam line."""
    return (u, v, z) if ax == 0 else (v, u, z)


def _uv(ax, u0, v0, z0, u1, v1, z1):
    return (*_pt(ax, u0, v0, z0), *_pt(ax, u1, v1, z1))


def _gb_strips(lines, jb):
    """[(line, world box)]: lean strip under every clear span, `pad` wider than the beam each side."""
    t, w = GBEAM, GBEAM["b"] / 2 + GBEAM["pad"]
    return [(name, _uv(ax, o[ax] + s0, o[1 - ax] - w, top - h - t["lean"], o[ax] + s1, o[1 - ax] + w, top - h))
            for name, ax, o, top, G, on in lines for h in (_bt(name)[1]["h"],) for s0, s1 in _spans(on, jb)]


def _box_minus(a, c):
    """a minus c as disjoint boxes; no float-noise sliver (< 1 µm, it stores as a 0-thick box that doubles a face)."""
    i = _inter(a, c)
    if not i or min(i[k + 3] - i[k] for k in range(3)) < 1e-6:   # (a touch by float noise: the slivers came from here)
        return [a]
    out, lo, hi = [], list(a[:3]), list(a[3:])
    for k in range(3):
        if lo[k] < i[k] - 1e-6:
            b = lo + hi
            b[k + 3] = i[k]
            out.append(tuple(b))
            lo[k] = i[k]
        if i[k + 3] < hi[k] - 1e-6:
            b = lo + hi
            b[k] = i[k + 3]
            out.append(tuple(b))
            hi[k] = i[k + 3]
    return out


def build_ground_beams():
    """ST03: GB1 as clear spans between joints with lean, bars and stirrups per line; joints J1 over the stubs."""
    t = GBEAM
    nodes, lines = _nodes(), _gb_lines()
    jb = {g: w for g, (_, _, w) in nodes.items()}
    stubs = {g for gs in STUB_GRIDS.values() for g in gs}
    assert all(t["b"] <= jb[g] for *_, on in lines for _, g in on), "beam wider than its joint"
    eb = t["cover"] + t["dt"] + t["d"] / 2                          # bar centre from a concrete face
    aw, zt = t["b"] / 2 - t["cover"] - t["dt"] / 2, -t["cover"] - t["dt"] / 2
    k = t["shook"] / math.sqrt(2)                                   # 135° stirrup hooks into the core
    c = _clear(C_GB)
    conc = bpy.data.materials.get("rough_concrete_material_Str_Footings") or mat("M_Concrete", (0.50, 0.50, 0.48), 0.85)
    lean_m = mat("M_LeanConcrete", (0.30, 0.30, 0.28), 0.95)
    steel = mat("M_Rebar", (0.28, 0.17, 0.11), 0.55, 0.6)
    # strips of two perpendicular lines overlap pad × pad at a joint: lines along x keep theirs whole, lines
    # along y give way (each strip minus every piece already placed)
    axis, lean, placed = {l[0]: l[1] for l in lines}, {}, []
    for name, box in sorted(_gb_strips(lines, jb), key=lambda nb: axis[nb[0]]):
        pieces = [box]
        for p in placed:
            pieces = [q for r in pieces for q in _box_minus(r, p)]
        placed += pieces
        lean.setdefault(name, []).extend(pieces)
    dug = []
    for name, ax, o, top, G, on in lines:
        tn, bt = _bt(name)
        h, nsp = bt["h"], bt["n_sp"]
        assert 2 * t["hook"] <= h - 2 * eb + 1e-9, "top and bottom bar hooks overlap"
        zb = -h + t["cover"] + t["dt"] / 2
        vs = [(eb - t["b"] / 2) * (1 - 2 * (j + 1) / (nsp + 1)) for j in range(nsp)]   # specials between the corners
        loc = (o[0], o[1], top)
        spans = _spans(on, jb)
        ea, ez = jb[on[0][1]] / 2 - eb, G + jb[on[-1][1]] / 2 - eb    # bar ends inside the end joints
        assert ea + ez + 2 * t["hook"] <= STOCK, f"{name}: bars longer than {STOCK} m need a lap"
        bars = [[_pt(ax, -ea, v, z + dz), _pt(ax, -ea, v, z), _pt(ax, ez, v, z), _pt(ax, ez, v, z + dz)]
                for v in (eb - t["b"] / 2, t["b"] / 2 - eb)
                for z, dz in ((-eb, -t["hook"]), (eb - h, t["hook"]))]     # top bars hook down, bottom bars up
        cc = [u for u, _ in on]                                            # column centres along the line
        bars += [[_pt(ax, (u0 + u1 - t["mid"] * (u1 - u0)) / 2, v, eb - h), _pt(ax, (u0 + u1 + t["mid"] * (u1 - u0)) / 2, v, eb - h)]
                 for u0, u1 in zip(cc, cc[1:]) for v in vs]                # special bottom bars, mid-span
        for i, u in enumerate(cc):                                         # special top bars over every joint
            for v in vs:
                p0 = [_pt(ax, u - t["sup"] * (u - cc[i - 1]), v, -eb)] if i else \
                    [_pt(ax, -ea, v, -eb - t["hook"]), _pt(ax, -ea, v, -eb)]   # line end: hooked into the joint
                p1 = [_pt(ax, u + t["sup"] * (cc[i + 1] - u), v, -eb)] if i < len(cc) - 1 else \
                    [_pt(ax, ez, v, -eb), _pt(ax, ez, v, -eb - t["hook"])]
                bars.append(p0 + p1)
        stirrups = []
        for s0, s1 in spans:
            L = s1 - s0
            assert L > 2 * t["first"], f"{name}: span too short for stirrups"
            n = math.ceil((L - 2 * t["first"]) / t["s"] - 1e-9) + 1       # spacing never above s
            for i in range(n):
                u = s0 + t["first"] + i * (L - 2 * t["first"]) / (n - 1)
                stirrups.append([_pt(ax, u, v, z) for v, z in
                                 ((aw - k, zt - k), (aw, zt), (-aw, zt), (-aw, zb), (aw, zb), (aw, zt), (aw - k, zt - k))])
        D = {
            "Conc": _boxes_data(f"{tn}_{name}_Conc", [_uv(ax, s0, -t["b"] / 2, -h, s1, t["b"] / 2, 0) for s0, s1 in spans],
                                conc, element="concrete", th=f"คอนกรีตคานคอดิน {t['b']:.2f}×{h:.2f}", type=tn,
                                grade=t["grade"]),
            "Lean": _boxes_data(f"{tn}_{name}_Lean", [tuple(b[i] - loc[i % 3] for i in range(6)) for b in lean[name]],
                                lean_m, element="lean_concrete", th=f"คอนกรีตหยาบรองท้องคาน {t['lean'] * 100:.0f} ซม.",
                                type=tn),
            "Bars": _rebar_data(f"{tn}_{name}_Bars", bars, t["d"], steel, element="rebar", th="เหล็กเสริมคานคอดิน",
                                type=tn, bar=t["bar"], dia_mm=round(t["d"] * 1000)),
            "Stirrups": _rebar_data(f"{tn}_{name}_Stirrups", stirrups, t["dt"], steel, element="stirrups",
                                    th="เหล็กปลอกคานคอดิน", type=tn, bar=t["tie"], dia_mm=round(t["dt"] * 1000),
                                    spacing=t["s"]),
        }
        # dig from GL to the lean's bottom; strips at other levels (porch) overlap in plan: each gives way to the dug
        trench = [q for b in lean[name] if b[2] < GL - 1e-9 for q in _cut((*b[:5], GL), dug)]
        dug += trench
        if trench:
            D["Exc"] = _boxes_data(f"{tn}_{name}_Exc", [tuple(b[i] - loc[i % 3] for i in range(6)) for b in trench],
                                   None, element="excavation", th="ขุดร่องคานคอดิน", type=tn)
        root = bpy.data.objects.new(f"{tn}_{name}", None)
        root.empty_display_type, root.empty_display_size = "PLAIN_AXES", 0.2
        root.location = loc
        root["line"], root["type"] = name, tn
        c.objects.link(root)
        for key, data in D.items():
            ob = bpy.data.objects.new(f"{tn}_{name}_{key}", data)
            ob.parent = root
            c.objects.link(ob)
            if key == "Exc":
                ob.display_type, ob.hide_render = "WIRE", True
    shared = {}   # joints of equal size and height share one mesh
    for g, (zb0, zt0, b) in sorted(nodes.items()):
        hj = zt0 - zb0
        key = f"J1_B{round(b * 100)}_H{round(hj * 100)}"
        if key not in shared:
            shared[key] = (round(hj, 6), _box_data(f"{key}_Conc", -b / 2, -b / 2, 0, b / 2, b / 2, hj, conc,
                                                   element="concrete", th="คอนกรีตหัวเสาช่วงคานคอดิน (เทพร้อมคาน)",
                                                   type="J1", grade=t["grade"]))
        assert shared[key][0] == round(hj, 6), f"{key}: same name, other height"
        root = bpy.data.objects.new(f"J1_{g}", None)
        root.empty_display_type, root.empty_display_size = "PLAIN_AXES", 0.2
        root.location = (*_xy(g), zb0)
        root["grid"], root["type"] = g, "J1"
        c.objects.link(root)
        parts = {"Conc": shared[key][1]}
        if g not in stubs:   # a joint on beams only: lean (and its trench) under it too, like under the spans
            x, y = _xy(g)
            sq = (x - b / 2, y - b / 2, zb0 - t["lean"], x + b / 2, y + b / 2, zb0)
            rel = lambda q: tuple(q[i] - (x, y, zb0)[i % 3] for i in range(6))
            parts["Lean"] = _box_data(f"J1_{g}_Lean", *rel(sq), lean_m, element="lean_concrete",
                                      th=f"คอนกรีตหยาบรองท้องคาน {t['lean'] * 100:.0f} ซม.", type=t["type"])
            trench = _cut((*sq[:5], GL), dug) if sq[2] < GL - 1e-9 else []
            dug += trench
            if trench:
                parts["Exc"] = _boxes_data(f"J1_{g}_Exc", [rel(q) for q in trench], None, element="excavation",
                                           th="ขุดร่องคานคอดิน", type=t["type"])
        for kk, data in parts.items():
            ob = bpy.data.objects.new(f"J1_{g}_{kk}", data)
            ob.parent = root
            c.objects.link(ob)
            if kk == "Exc":
                ob.display_type, ob.hide_render = "WIRE", True
    return len(lines), len(nodes)


def _zones():
    """ZONES with every zone's rects minus the zones listed after it."""
    box, names, out = (lambda r: (r[0], r[1], 0.0, r[2], r[3], 1.0)), list(ZONES), {}
    for i, zn in enumerate(names):
        rects, top = ZONES[zn]
        later = [box(r) for z in names[i + 1:] for r in ZONES[z][0]]
        out[zn] = ([(b[0], b[1], b[3], b[4]) for r in rects for b in _cut(box(r), later)], top)
    return out


def _zone_inset(rects, c):
    """Plan rects (x0, y0, x1, y1) of a zone shrunk by c along its true outline: zone minus the outside grown by c."""
    box = lambda r: (r[0], r[1], 0.0, r[2], r[3], 1.0)
    frame = (min(r[0] for r in rects) - 2 * c, min(r[1] for r in rects) - 2 * c, 0.0,
             max(r[2] for r in rects) + 2 * c, max(r[3] for r in rects) + 2 * c, 1.0)
    grown = [(b[0] - c, b[1] - c, 0.0, b[3] + c, b[4] + c, 1.0) for b in _cut(frame, [box(r) for r in rects])]
    return [(b[0], b[1], b[3], b[4]) for r in rects for b in _cut(box(r), grown)]


def _mesh_wires(rects, z, t):
    """Wire mesh over a zone of plan rects, mcover inside its outline: per direction, lines @ ≤ ms across the
    shrunk zone, each cut to the stretches inside it (touching pieces merged)."""
    inner, out = _zone_inset(rects, t["mcover"]), []
    for ax in (0, 1):                                   # ax 0: wires along x, placed at y positions
        lo, hi = min(r[1 - ax] for r in inner), max(r[3 - ax] for r in inner)
        n = math.ceil((hi - lo) / t["ms"] - 1e-9) + 1
        for i in range(n):
            p = lo + i * (hi - lo) / (n - 1)
            merged = []
            for a, b in sorted((r[ax], r[2 + ax]) for r in inner if r[1 - ax] - 1e-9 <= p <= r[3 - ax] + 1e-9):
                if merged and a <= merged[-1][1] + 1e-9:
                    merged[-1][1] = max(merged[-1][1], b)
                else:
                    merged.append([a, b])
            zz = z + ax * t["md"]                       # wires along y lie on the ones along x
            out += [[(a, p, zz), (b, p, zz)] if ax == 0 else [(p, a, zz), (p, b, zz)] for a, b in merged]
    return out


def build_ground_slab():
    """ST04: per zone the compacted fill (GL → beam top, around beams and joints), the wire mesh and the slab."""
    t, tn = SLAB, SLAB["type"]
    # rounded: float32 beam tops (0.34999999) would leave micron slivers of fill on top of the cut
    # + the columns: a column on a lowered joint (round the bath) starts below the fill top
    cutters = [tuple(round(x, 5) for x in b) for b in _solids([C_STUB, C_GB]).values()] + _col_prisms()
    beams = [tuple(round(x, 5) for x in b) for (n, _), b in _solids([C_GB]).items()
             if bpy.data.objects[n].data.get("element") == "concrete"]   # beams + joints, not their lean
    c = _clear(C_SLAB)
    conc = bpy.data.materials.get("rough_concrete_material_Str_Footings") or mat("M_Concrete", (0.50, 0.50, 0.48), 0.85)
    fill_m = mat("M_Fill", (0.45, 0.33, 0.22), 0.95)
    steel = mat("M_Rebar", (0.28, 0.17, 0.11), 0.55, 0.6)
    for zn, (rects, top) in _zones().items():
        loc = (rects[0][0], rects[0][1], top)
        rel = lambda b: tuple(b[i] - loc[i % 3] for i in range(6))
        curb = []   # over beams set lower than this zone's fill (round the bath): concrete up to the slab, cast with it
        for b in beams:
            for x0, y0, x1, y1 in rects:
                if b[5] < top - 1e-4 and min(b[3], x1) - max(b[0], x0) > 1e-4 and min(b[4], y1) - max(b[1], y0) > 1e-4:
                    curb += _cut((max(b[0], x0), max(b[1], y0), b[5], min(b[3], x1), min(b[4], y1), top), cutters + curb)
        fill = [q for x0, y0, x1, y1 in rects for q in _cut((x0, y0, GL, x1, y1, top), cutters + curb)]
        slab = [q for x0, y0, x1, y1 in rects for q in _cut((x0, y0, top, x1, y1, top + t["t"]), _col_prisms() + beams)]   # the bath's: round the corner joints
        area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in rects)
        wires = [[tuple(p[i] - loc[i] for i in range(3)) for p in w] for w in _mesh_wires(rects, top + t["mz"], t)]
        D = {
            "Fill": _boxes_data(f"{tn}_{zn}_Fill", [rel(b) for b in fill], fill_m, element="fill",
                                th="ดินถมบดอัดใต้พื้น", type=tn),
            "Conc": _boxes_data(f"{tn}_{zn}_Conc", [rel(b) for b in slab], conc, element="concrete", th=f"พื้นหล่อบนดิน {t['t'] * 100:.0f} ซม.", type=tn,
                                grade=t["grade"]),
            **({"Curb": _boxes_data(f"{tn}_{zn}_Curb", [rel(b) for b in curb], conc, element="concrete", type=f"{tn}C",
                                    th="คันคอนกรีตเหนือคานลดระดับรอบห้องน้ำ (เทพร้อมพื้น)", grade=t["grade"],
                                    on_fill=True)} if curb else {}),
            "Mesh": _rebar_data(f"{tn}_{zn}_Mesh", wires, t["md"], steel, element="mesh", th="ไวร์เมชพื้น",
                                type=tn, bar=t["mesh"], dia_mm=round(t["md"] * 1000), spacing=t["ms"], area=area),
        }
        root = bpy.data.objects.new(f"{tn}_{zn}", None)
        root.empty_display_type, root.empty_display_size = "PLAIN_AXES", 0.3
        root.location = loc
        root["zone"], root["type"] = zn, tn
        c.objects.link(root)
        for key, data in D.items():
            ob = bpy.data.objects.new(f"{tn}_{zn}_{key}", data)
            ob.parent = root
            c.objects.link(ob)
    return len(ZONES)


def _col_prisms():
    """Plan footprint of every column, joint top → ring-beam bottom (the slab on ground is cast around them)."""
    lv, w = _stub_levels(), COL["b"] / 2
    return [(x - w, y - w, lv[g][2], x + w, y + w, COL["top"]) for g in lv for x, y in (_xy(g),)]


def build_columns():
    """ST05: column C1 concrete and ties on every stub (its bars come from the stub stage); equal columns share data."""
    t, tn = COL, COL["type"]
    lv = _stub_levels()
    assert all(t["b"] == s["col"] and t["cover"] == s["col_cover"] for s in STUBS.values()), "COL ≠ the stubs' column"
    a = t["b"] / 2 - t["cover"] - t["dt"] / 2                     # tie centreline, tight on the stub's bars
    kt = a - t["shook"] / math.sqrt(2)
    c = _clear(C_COL)
    conc = bpy.data.materials.get("rough_concrete_material_Str_Footings") or mat("M_Concrete", (0.50, 0.50, 0.48), 0.85)
    steel = mat("M_Rebar", (0.28, 0.17, 0.11), 0.55, 0.6)
    plate_m = mat("M_SteelPlate", (0.35, 0.36, 0.38), 0.4, 0.9)
    shared = {}
    for g in lv:
        z0 = lv[g][2]                                              # joint top = highest beam top
        h, z1 = t["top"] - t["pt"] - z0, lv[g][1] - z0             # concrete up to the plate; stub top (≤ 0)
        key = f"{tn}_H{round(h * 100)}_J{round(-z1 * 100)}"
        if key not in shared:
            L = h - z1 - 2 * t["first"]                            # ties from the stub top through the joint
            assert L > 0, "column too short for ties"
            n = math.ceil(L / t["s"] - 1e-9) + 1                   # spacing never above s
            ties = [[(kt, kt, z), (a, a, z), (-a, a, z), (-a, -a, z), (a, -a, z), (a, a, z), (kt, kt, z)]
                    for z in (z1 + t["first"] + i * L / (n - 1) for i in range(n))]
            w = t["b"] / 2
            shared[key] = ((round(h, 6), round(z1, 6)), {
                "Conc": _box_data(f"{key}_Conc", -w, -w, 0, w, w, h, conc, element="concrete", th="คอนกรีตเสา",
                                  type=tn, grade=t["grade"]),
                "Ties": _rebar_data(f"{key}_Ties", ties, t["dt"], steel, element="ties",
                                    th="เหล็กปลอกเสา (รวมช่วงหัวเสาคานคอดิน)", type=tn, bar=t["tie"],
                                    dia_mm=round(t["dt"] * 1000), spacing=t["s"]),
                "Plate": _box_data(f"{key}_Plate", -t["plate"] / 2, -t["plate"] / 2, h, t["plate"] / 2, t["plate"] / 2,
                                   h + t["pt"], plate_m, element="plate", th=t["plate_spec"], type=tn),
            })
        assert shared[key][0] == (round(h, 6), round(z1, 6)), f"{key}: same name, other levels"
        root = bpy.data.objects.new(f"{tn}_{g}", None)
        root.empty_display_type, root.empty_display_size = "PLAIN_AXES", 0.2
        root.location = (*_xy(g), z0)
        root["grid"], root["type"] = g, tn
        c.objects.link(root)
        for kk, data in shared[key][1].items():
            ob = bpy.data.objects.new(f"{tn}_{g}_{kk}", data)
            ob.parent = root
            c.objects.link(ob)
    return len(lv)


def _world_bm(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(ev.to_mesh())
    ev.to_mesh_clear()
    bm.transform(o.matrix_world)
    return bm


def _cuts(L, stock, lap=0.0):
    """Pieces to make a run L from stock lengths, each joint lapping `lap` (0 = butt-welded)."""
    out = []
    while L > stock + 1e-9:
        out.append(stock)
        L -= stock - lap
    return out + [L]


def _bar_lengths(o):
    return [sum((sp.points[i + 1].co.xyz - sp.points[i].co.xyz).length for i in range(len(sp.points) - 1))
            for sp in o.data.splines]


def _vol(b):
    return (b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2])


def _inter(a, b):
    lo, hi = [max(a[i], b[i]) for i in range(3)], [min(a[i + 3], b[i + 3]) for i in range(3)]
    return (*lo, *hi) if all(l < h for l, h in zip(lo, hi)) else None


def _union_volume(boxes):
    """Exact volume of a union of axis-aligned boxes: sum the grid cells that lie inside any box."""
    ax = [sorted({b[i] for b in boxes} | {b[i + 3] for b in boxes}) for i in range(3)]
    v = 0.0
    for x0, x1 in zip(ax[0], ax[0][1:]):
        for y0, y1 in zip(ax[1], ax[1][1:]):
            for z0, z1 in zip(ax[2], ax[2][1:]):
                c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
                if any(all(b[i] < c[i] < b[i + 3] for i in range(3)) for b in boxes):
                    v += (x1 - x0) * (y1 - y0) * (z1 - z0)
    return v


def _obj_boxes(bm, name):
    """World boxes of a _boxes_data mesh (8 vertices per box, in creation order)."""
    vs = [v.co.copy() for v in bm.verts]
    assert vs and len(vs) % 8 == 0, f"not boxes: {name}"
    bs = [tuple(f(p[i] for p in vs[j:j + 8]) for f in (min, max) for i in range(3)) for j in range(0, len(vs), 8)]
    tot = sum(map(_vol, bs))
    assert abs(tot - bm.calc_volume()) <= 1e-5 * tot, f"not boxes: {name}"
    return bs


def _touch(a, b):
    """Area where two boxes meet on a vertical plane."""
    for k in (0, 1):
        if abs(a[k + 3] - b[k]) < 1e-5 or abs(b[k + 3] - a[k]) < 1e-5:
            o = [min(a[j + 3], b[j + 3]) - max(a[j], b[j]) for j in range(3) if j != k]
            if all(x > 1e-9 for x in o):
                return o[0] * o[1]
    return 0.0


def _stock_bars(lengths, stock=STOCK):
    """Stock bars needed to cut every length, offcuts reused (first-fit decreasing)."""
    free = []
    for L in sorted(lengths, reverse=True):
        assert L <= stock + 1e-9, f"piece {L:.3f} m longer than stock"
        i = next((i for i, f in enumerate(free) if f >= L - 1e-9), None)
        if i is None:
            free.append(stock - L)
        else:
            free[i] -= L
    return len(free)


def _solids(colls):
    """{(object, i): world box} of every solid except pits in the given stages; asserts closed meshes."""
    out = {}
    for cn in colls:
        c = bpy.data.collections.get(cn)
        for o in (c.objects if c else ()):
            if o.type == "MESH":
                bm = _world_bm(o)
                assert all(len(e.link_faces) == 2 for e in bm.edges), f"open mesh: {o.name}"
                if o.data.get("kg_m"):   # a section to its profile: nothing else may enter its outline box
                    out[(o.name, 0)] = tuple(f(v.co[i] for v in bm.verts) for f in (min, max) for i in range(3))
                elif o.data["element"] != "excavation":
                    out.update(((o.name, i), b) for i, b in enumerate(_obj_boxes(bm, o.name)))
                bm.free()
    return out


def _exc_boxes(coll):
    return [b for (el, _), x in qto(coll).items() if el == "excavation" for b in x["boxes"]] \
        if bpy.data.collections.get(coll) else []


def _earth():
    """(pits, dug, backfill, taken): the pits' union, everything dug (pits + beam trenches), the soil that goes
    back up to GL, and the room the solids take below GL."""
    pits = _exc_boxes(C_FOOT)
    dug_boxes = pits + _exc_boxes(C_GB)
    dug = _union_volume(dug_boxes)
    taken = sum(_union_volume(ii) for s in _solids((C_FOOT, C_STUB, C_GB)).values()
                if (ii := [i for p in dug_boxes if (i := _inter(s, p))]))
    return _union_volume(pits), dug, dug - taken, taken


def qto(coll=C_FOOT):
    """Measure every object whose data carries `element` + `type`: volume, formwork, bar lengths.
    Rows per (element, type), so sizes, grades and bar diameters of different types never mix.
    Formwork = vertical faces of the concrete minus faces poured against other concrete of the same stage or against
    brick, plus the soffit of pieces marked `soffit` (lintels over openings). Steel sections (`kg_m`): piece lengths."""
    rows, conc, brick = {}, [], []
    for o in _coll(coll).objects:
        el = o.data.get("element") if o.data else None
        if not el:
            continue
        mw = o.matrix_world
        assert mw.determinant() > 0 and all(abs(s - 1) < 1e-9 for s in mw.to_scale()), f"scaled/mirrored: {o.name}"
        r = rows.setdefault((el, o.data["type"]), dict(th=o.data["th"], n=0, vol=0.0, side=0.0, bars=[], boxes=[],
                                                        dia=o.data.get("dia_mm"), bar=o.data.get("bar"), area=0.0,
                                                        lens=[], t=o.data.get("t"), per_m2=o.data.get("per_m2"),
                                                        waste=o.data.get("waste", 0.0), roll=o.data.get("roll"),
                                                        pieces=o.data.get("pieces", 1),
                                                        kg_m=o.data.get("kg_m"), stock=o.data.get("stock"),
                                                        joint=o.data.get("joint", 0.0), per_m=o.data.get("per_m"),
                                                        butt=o.data.get("butt", False), count=0, screws=0, cut=0,
                                                        sheet=o.data.get("sheet"), per_bucket=o.data.get("per_bucket")))
        assert r["dia"] == o.data.get("dia_mm") and r["bar"] == o.data.get("bar"), f"two bar specs in one row: {o.name}"
        r["n"] += 1
        r["count"] += o.data.get("count", 1)   # one object can hold several identical parts (brackets, screws)
        r["screws"] += o.data.get("screws", 0)
        r["cut"] += bool(o.data.get("cut"))
        r["area"] += o.data.get("area", 0.0)
        r["wlen"] = r.get("wlen", 0.0) + o.data.get("length", 0.0)   # weld beads (curves)
        r["links"] = r.get("links", 0) + o.data.get("links", 0)   # ceiling hangers that need a sideways link
        r["link_len"] = r.get("link_len", 0.0) + o.data.get("link_len", 0.0)
        r["void"] = r.get("void", 0.0) + o.data.get("void", 0.0)   # room an embedded bead takes in the plaster
        if el in ("floor_tile", "membrane", "conduit", "flex"):   # one object per row: its props (layout counts, rates)
            r["props"] = {k: (list(v) if hasattr(v, "to_list") else v) for k, v in o.data.items()}
        if o.type == "MESH" and (el in ("tile", "sheet", "joint", "paint", "floor_tile", "membrane", "wire")
                                 or (el == "piece" and not o.data.polygons)):   # count-only rows (no geometry)
            bm = _world_bm(o)
            r["area"] += sum(f.calc_area() for f in bm.faces) if el == "tile" else 0.0
            bm.free()
        elif o.type == "MESH":
            bm = _world_bm(o)
            v = bm.calc_volume(signed=True)
            assert v > 0, f"inside-out: {o.name}"
            r["vol"] += v
            if not o.data.get("on_fill"):   # cast in a trench of compacted fill: no form
                r["side"] += sum(f.calc_area() for f in bm.faces if abs(f.normal.z) < 1e-6)
            if el == "excavation":   # digs that overlap are dug once: keep boxes for the union (rounded: float32)
                r["boxes"] += [tuple(round(x, 5) for x in b) for b in _obj_boxes(bm, o.name)]
            elif el == "concrete":   # a curb (on_fill) still spares the faces poured against it their form
                conc += [(r, b) for b in _obj_boxes(bm, o.name)]
                r["on_fill"] = bool(o.data.get("on_fill"))
            elif el == "masonry":
                brick += _obj_boxes(bm, o.name)
            if o.data.get("soffit"):
                r["side"] += sum(f.calc_area() for f in bm.faces if f.normal.z < -0.99)
            if o.data.get("lens"):   # one object holding several runs (ceiling runners): each run's length
                r["lens"] += list(o.data["lens"])
            elif o.data.get("swept") and "len" in o.data:   # written at build (a coped member: rings out of order)
                r["lens"].append(o.data["len"])
            elif o.data.get("swept"):   # a member swept to its profile (steel_sections): ring of n verts at each end
                vs = [v.co for v in bm.verts]
                n = len(vs) // (2 * r["pieces"])
                r["lens"].append((vs[n] - vs[0]).length)
            elif o.data.get("stock"):   # beads bought by the length: one box per leg
                r["lens"] += [max(b[3] - b[0], b[4] - b[1], b[5] - b[2]) for b in _obj_boxes(bm, o.name)]
            bm.free()
        elif o.data.get("element") in ("conduit", "flex"):   # a conduit curve: its runs' lengths
            r["lens"] += list(o.data["lens"])
        else:
            r["bars"] += _bar_lengths(o)
    for (ra, a), (rb, b) in itertools.combinations(conc, 2):
        area = _touch(a, b)
        ra["side"] -= area
        rb["side"] -= area
    for ra, a in conc:   # cast against the brick it fills in
        ra["side"] -= sum(_touch(a, b) for b in brick)
    if coll in STAGES:   # faces cast against concrete of an earlier stage need no form either
        older = [b for (n, _), b in _solids(STAGES[:STAGES.index(coll)]).items() if n.endswith("_Conc")]
        for ra, a in conc:
            ra["side"] -= sum(_touch(a, b) for b in older)
    for x in rows.values():
        if x.get("on_fill"):
            x["side"] = 0.0
    return rows


def report(coll=C_FOOT):
    r, out = qto(coll), []
    for (el, tn), x in r.items():
        if el == "excavation":
            unit = "หลุม" if tn in TYPES else "แนว"
            out.append(f"{tn} {x['th']}: {x['n']} {unit} รวมราย{unit} {x['vol']:.3f} ลบ.ม.")
        elif el == "plate":
            out.append(f"{tn} {x['th']}: {x['n']} แผ่น = {x['vol'] * 7850:.1f} กก.")
        elif el == "masonry":   # area from the volume and the wall's thickness
            a = x["vol"] / x["t"]
            out.append(f"{tn} {x['th']}: {a:.2f} ตร.ม. (หักช่องเปิด เสา เสาเอ็นแล้ว) × {x['per_m2']:.1f} ก้อน/ตร.ม. "
                       f"+ เผื่อแตก {x['waste'] * 100:.0f}% → {math.ceil(a * x['per_m2'] * (1 + x['waste']) - 1e-9)} ก้อน")
        elif el == "ladder":   # prefab ladder lintel, sold in rolls
            m = sum(x["bars"])
            out.append(f"{tn} {x['th']}: {len(x['bars'])} แนว = {m:.2f} ม. → {math.ceil(m / x['roll'] - 1e-9)} ม้วน")
        elif el == "bead":   # two legs per bead: one length each; longer than a stock piece → cut and butt
            ed, st = x["lens"][::2], x["stock"]
            cut = [q for L in ed for q in [st] * math.floor(L / st - 1e-9) + [L - st * math.floor(L / st - 1e-9)]]
            out.append(f"{tn} {x['th']}: {len(ed)} เส้น = {sum(ed):.2f} ม. → {_stock_bars(cut, st)} ท่อน (ท่อนละ {st:.0f} ม.)")
        elif el == "plaster":
            out.append(f"{tn} {x['th']}: {(x['vol'] + x['void']) / x['t']:.2f} ตร.ม.")
        elif el == "tile":   # a common take-off rule: ceil(A × 10.5 × 1.05) to tens
            n_ = math.ceil(x["area"] * x["per_m2"] * (1 + x["waste"]) / 10 - 1e-9) * 10
            out.append(f"{tn} {x['th']}: พื้นที่ลาดเอียง {x['area']:.2f} ตร.ม. × {x['per_m2']} แผ่น/ตร.ม. + เผื่อ "
                       f"{x['waste'] * 100:.0f}% → {n_} แผ่น")
        elif el == "sheet":
            out.append(f"{tn} {x['th']}: {x['n']} แผ่น (ตามที่วางในโมเดล)")
        elif el == "cap_piece":   # counted off the model, a cut piece is bought whole
            cut = f" (ตัด {x['cut']})" if x["cut"] else ""
            out.append(f"{tn} {x['th']}: {x['count']} แผ่น{cut} · ตะปูเกลียวยึด {x['screws']} ตัว")
        elif el == "ceiling":   # boards: area off the layout; sheets = area / sheet + waste, and the cut pieces drawn
            n_ = math.ceil(x["area"] / x["sheet"] * (1 + x["waste"]) - 1e-9)
            out.append(f"{tn} {x['th']}: {x['area']:.2f} ตร.ม. ({x['count']} ชิ้นตามแบบวาง) + เผื่อ {x['waste'] * 100:.0f}% → {n_} แผ่น")
        elif el == "paint":   # by area; buckets where a rate is set (the user: ceilings 87.5 m² a bucket)
            b_ = f" ÷ {x['per_bucket']:.1f} ตร.ม./ถัง → {math.ceil(x['area'] / x['per_bucket'] - 1e-9)} ถัง" if x.get("per_bucket") else ""
            out.append(f"{tn} {x['th']}: {x['area']:.2f} ตร.ม.{b_}")
        elif el == "joint":
            roll = f" → {math.ceil(x['wlen'] / x['roll'] - 1e-9)} ม้วน" if x.get("roll") else ""
            out.append(f"{tn} {x['th']}: ยาวรวม {x['wlen']:.2f} ม.{roll}")
        elif el == "conduit":   # pieces of stock, a coupling where a run needs more than one, bends, clips
            L = sum(x["lens"])
            n = sum(math.ceil(l / x["stock"] - 1e-9) for l in x["lens"])
            p = x["props"]
            out.append(f"{tn} {x['th']}: {len(x['lens'])} แนว = {L:.2f} ม. → {math.ceil(L / x['stock'] - 1e-9)} ท่อน · "
                       f"ข้อต่อตรง {max(0, n - len(x['lens']))} · ข้องอ {p['bends']} · ข้อต่อเข้ากล่อง {2 * len(x['lens'])} · "
                       f"กิ๊บจับท่อ {math.ceil(p.get('vlen', L) / p['clip'] - 1e-9)} ตัว (เฉพาะช่วงเหนือฝ้า)")
        elif el == "flex":   # by the roll; its connectors are a row of their own
            L = sum(x["lens"])
            out.append(f"{tn} {x['th']}: {len(x['lens'])} เส้น = {L:.2f} ม. → {math.ceil(L / x['stock'] - 1e-9)} ม้วน")
        elif el == "wire":
            buy = (f"{math.ceil(x['wlen'] / x['roll'] - 1e-9)} ม้วน ({x['roll']:.0f} ม.)" if x["wlen"] >= x["roll"] / 2
                   else f"ซื้อตัด {math.ceil(x['wlen'])} ม.")   # under half a roll: by the metre (ไทวัสดุ sells THW cut)
            out.append(f"{tn} {x['th']}: {x['wlen']:.1f} ม. → {buy}")
        elif el == "floor_tile":   # counted off the layout + spare, whole boxes; adhesive and grout off its area
            p = x["props"]
            st = f" + เศษตัดแถบ (ลูกตั้ง/ขอบ) {p['strips']} แผ่น" if p["strips"] else ""
            out.append(f"{tn} {x['th']}: {x['area']:.2f} ตร.ม. · วางจริงเต็ม {p['whole']} + ตัด {p['cut']} แผ่น{st} + แตก/สำรอง "
                       f"3% → {p['need']} แผ่น = {math.ceil(p['need'] / p['box'] - 1e-9)} กล่อง ({p['box']} แผ่น/กล่อง) "
                       f"[เทียบ พื้นที่ × 1.10 = {math.ceil(x['area'] / p['sheet'] * 1.10 - 1e-9)} แผ่น] · ปูนกาว {p['adh_bags']:.2f} "
                       f"→ {math.ceil(p['adh_bags'] - 1e-9)} ถุง · ยาแนว {p['grout_kg']:.2f} กก. → {math.ceil(p['grout_kg'] - 1e-9)} ถุง")
        elif el == "membrane":
            p = x["props"]
            kg = x["area"] * p["kg_m2"]
            out.append(f"{tn} {x['th']}: {x['area']:.2f} ตร.ม. × {p['kg_m2']} กก./ตร.ม. = {kg:.1f} กก. → "
                       f"{math.ceil(kg / p['bag'] - 1e-9)} ถุง ({p['bag']:.0f} กก.)")
        elif el == "screed":
            out.append(f"{tn} {x['th']}: {x['area']:.2f} ตร.ม. · หนาเฉลี่ย {x['vol'] / x['area'] * 100:.1f} ซม. = {x['vol']:.3f} ลบ.ม.")
        elif el == "weld":
            out.append(f"{tn} {x['th']}: {x['n']} ชิ้นงาน · ยาวรวม {x['wlen']:.2f} ม.")
        elif el == "piece":
            out.append(f"{tn} {x['th']}: {x['count']} ชิ้น" + (f" · ยาวรวม {x['wlen']:.2f} ม." if x["wlen"] else "") +
                       (f" · ต้องมีเหล็กต่อแขวนด้านข้าง {x['links']} จุด รวม {x['link_len']:.2f} ม." if x["links"] else ""))
        elif el == "flashing":   # one object per line; count = stock pieces laid along it
            out.append(f"{tn} {x['th']}: {x['n']} แนว = {x['count']} ท่อน")
        elif x["lens"]:   # a run longer than stock is cut to stock lengths + the rest: welded, or lapped `joint`
            m, st, j = sum(x["lens"]), x["stock"], x["joint"] or 0.0
            cut = [p for L in x["lens"] for p in _cuts(L, st, j)]
            n = x["pieces"]   # 2C: each run is two channels
            kg = f" = {m * x['kg_m']:.1f} กก." if x["kg_m"] else ""
            how = f"รอยต่อทาบ {j * 100:.0f} ซม." if j else ("รอยต่อชน" if x["butt"] else "รอยต่อเชื่อม")
            out.append(f"{tn} {x['th']}: {len(x['lens'])} ชิ้น = {m:.2f} ม.{kg} "
                       f"→ ใช้เส้นยาว {st:.0f} ม. {_stock_bars(cut * n, st)} เส้น · {how} {(len(cut) - len(x['lens'])) * n} จุด")
        elif el == "mesh":   # sold by area; the length/weight shows what is in it
            m = sum(x["bars"])
            out.append(f"{tn} {x['th']} {x['bar']}: พื้นที่ {x['area']:.2f} ตร.ม. (ยังไม่รวมทาบ) · ลวด {m:.1f} ม. = "
                       f"{m * KG_M[x['dia']]:.1f} กก.")
        elif x["bars"]:
            m = sum(x["bars"])
            groups = {}
            for L in x["bars"]:
                groups[round(L, 3)] = groups.get(round(L, 3), 0) + 1
            cut = " · ".join(f"{k} ท่อน × {L:.3f} ม." for L, k in sorted(groups.items()))
            out.append(f"{tn} {x['th']} {x['bar']}: {cut} = {m:.2f} ม. = {m * KG_M[x['dia']]:.1f} กก. "
                       f"→ ใช้เหล็กเส้น 10 ม. {_stock_bars(x['bars'])} เส้น (ใช้เศษตัดต่อ)")
        else:
            line = f"{tn} {x['th']}: {x['n']} ชิ้น = {x['vol']:.3f} ลบ.ม."
            if el == "concrete":
                line += f" · ไม้แบบ {x['side']:.2f} ตร.ม."
            out.append(line)
    poured = sum(x["vol"] for (el, _), x in r.items() if el == "concrete")
    if poured:
        out.append(f"คอนกรีตเทครั้งนี้ {poured:.3f} ลบ.ม. → สั่ง {math.ceil(poured * 2 - 1e-9) / 2:.1f} ลบ.ม.")
    pits = [b for (el, _), x in r.items() if el == "excavation" for b in x["boxes"]]
    if pits and coll == C_FOOT:
        merged = sum(1 for a, b in itertools.combinations(pits, 2) if _inter(a, b))
        out.append(f"ขุดดินสุทธิ {_union_volume(pits):.3f} ลบ.ม. (หลุมที่ซ้อนกัน {merged} คู่ นับครั้งเดียว = ขุดเป็นร่อง)")
    if coll == C_GB:
        pit, dug, back, taken = _earth()
        out.append(f"ขุดร่องคานเพิ่มนอกหลุมฐาน {dug - pit:.3f} ลบ.ม. → ขุดรวม {dug:.3f} ลบ.ม.")
        out.append(f"ดินถมกลับหลุมและร่องถึงระดับดินเดิม {back:.3f} ลบ.ม. = ขุดรวม {dug:.3f} − ฐาน/ตอม่อ/คาน/หัวเสา/"
                   f"คอนกรีตหยาบ/ทรายที่อยู่ใต้ดิน {taken:.3f} (ดินเหลือ {taken:.3f} ลบ.ม.)")
    if coll == C_SLAB and ("fill", SLAB["type"]) in r:
        fill, left = r[("fill", SLAB["type"])]["vol"], _earth()[3]
        out.append(f"ดินถมใต้พื้น {fill:.3f} − ดินเหลือจากงานขุด {left:.3f} = ต้องหาดินเพิ่ม {fill - left:.3f} ลบ.ม. "
                   f"(ปริมาตรบดอัดแล้ว ยังไม่คูณค่ายุบตัว)")
    return "\n".join(out)


def selfcheck():
    r, pits = qto(), []

    def eq(a, b, what):
        assert abs(a - b) <= 1e-5 * abs(b), f"{what}: model {a} != expected {b}"   # float32 vertex coords
    for tn, t in TYPES.items():
        n, B, d = len(FOOTINGS[tn]), t["B"], t["d"]
        g = lambda el: r[(el, tn)]
        eq(g("concrete")["vol"], n * B * B * t["T"], f"{tn} concrete")
        eq(g("concrete")["side"], n * 4 * B * t["T"], f"{tn} formwork")
        eq(g("lean_concrete")["vol"], n * (B + 2 * t["pad"]) ** 2 * t["lean"], f"{tn} lean")
        eq(g("sand")["vol"], n * (B + 2 * t["pad"]) ** 2 * t["sand"], f"{tn} sand")
        eq(g("excavation")["vol"], n * (B + 2 * t["work"]) ** 2 * (GL - t["exc"]), f"{tn} pits")
        assert all(abs(b[2] - t["exc"]) < 1e-5 for b in g("excavation")["boxes"]), f"{tn} pit bottom not at exc"
        e = B / 2 - t["side"] - d / 2
        nb = math.ceil(2 * e / t["s"] - 1e-9) + 1
        eq(sum(g("rebar")["bars"]), n * nb * (2 * e + 2 * (e - d) + 4 * t["hook"]), f"{tn} rebar length")
        pits += g("excavation")["boxes"]
    # net pit volume two ways: cell union vs sum minus pairwise overlaps (valid while no soil is in 3 pits)
    assert not any(_inter(_inter(a, b) or a, c) for a, b, c in itertools.combinations(pits, 3) if _inter(a, b)), \
        "three pits overlap: pairwise check no longer valid"
    pair = sum(_vol(i) for a, b in itertools.combinations(pits, 2) if (i := _inter(a, b)))
    eq(_union_volume(pits), sum(_vol(b) for b in pits) - pair, "net excavation")
    msg, colls = [f"{len(pits)} footings"], [C_FOOT]
    stubs = bpy.data.collections.get(C_STUB)
    if stubs and stubs.objects:
        r, lv = qto(C_STUB), _stub_levels()
        for sn, t in STUBS.items():
            gs, g = STUB_GRIDS[sn], lambda el: r[(el, sn)]
            H = sum(lv[k][1] - lv[k][0] for k in gs)
            eq(g("concrete")["vol"], t["b"] ** 2 * H, f"{sn} concrete")
            eq(g("concrete")["side"], 4 * t["b"] * H, f"{sn} formwork")
            eq(sum(g("rebar")["bars"]), sum(4 * (COL["top"] - COL["pt"] - lv[k][3] - t["d"] + t["foot"] + t["bend"])
                                            for k in gs),
               f"{sn} starters")
            # ties read back from the model and checked against the spec, not against _stub_bars' own numbers
            a, expect = t["col"] / 2 - t["col_cover"] - t["dt"] / 2, 0.0
            for o in _coll(C_STUB).objects:
                if o.data and o.data.get("element") == "ties" and o.data["type"] == sn:
                    k = o.parent["grid"]
                    zs = sorted(sp.points[0].co.z for sp in o.data.splines)
                    assert abs(zs[0] - t["first"]) < 1e-5 and abs(zs[-1] - (lv[k][1] - lv[k][0] - t["first"])) < 1e-5 \
                        and t["s"] + 1e-6 >= max(z1 - z0 for z0, z1 in zip(zs, zs[1:])) \
                        and min(z1 - z0 for z0, z1 in zip(zs, zs[1:])) > 1e-6, f"tie spacing: {o.name}"   # min: no doubled tie
                    assert abs(max(abs(p.co.x) for sp in o.data.splines for p in sp.points) - a) < 1e-6, f"tie size: {o.name}"
                    expect += len(zs) * (8 * a + 2 * t["hook"])
            eq(sum(g("ties")["bars"]), expect, f"{sn} ties")
        msg.append(f"{len(lv)} stubs")
        colls.append(C_STUB)
    gb = bpy.data.collections.get(C_GB)
    if len(colls) > 1 and gb and gb.objects:
        r, t = qto(C_GB), GBEAM
        lines, nodes = _gb_lines(), _nodes()
        jb = {g: w for g, (_, _, w) in nodes.items()}
        tot = lambda el, k: sum(x[k] for (e, _), x in r.items() if e == el)                     # over beam types
        hl = {name: _bt(name)[1]["h"] for name, *_ in lines}
        # hand formulas: net length = gross − joint widths; joints b² × (highest top − lowest bottom)
        net = {name: G - sum(jb[g] for _, g in on) + (jb[on[0][1]] + jb[on[-1][1]]) / 2 for name, _, _, _, G, on in lines}
        hj = {g: zt0 - zb0 for g, (zb0, zt0, _) in nodes.items()}
        endf = {}   # beam end faces against each joint: 1 per line end, 2 where a line runs through
        for name, *_, on in lines:
            for i, (_, g) in enumerate(on):
                endf[g] = endf.get(g, 0) + (1 if i in (0, len(on) - 1) else 2) * t["b"] * hl[name]
        for tn in {_bt(n)[0] for n in hl}:
            ns = [n for n in hl if _bt(n)[0] == tn]
            eq(r[("concrete", tn)]["vol"], sum(t["b"] * hl[n] * net[n] for n in ns), f"{tn} concrete")
            eq(r[("concrete", tn)]["side"], sum(2 * hl[n] * net[n] for n in ns), f"{tn} formwork")
        eq(r[("concrete", "J1")]["vol"], sum(jb[g] ** 2 * hj[g] for g in jb), "joint concrete")
        eq(r[("concrete", "J1")]["side"], sum(4 * jb[g] * hj[g] - endf[g] for g in jb), "joint formwork")
        # lean: the pieces the builder cut must add up to the union of the full strips (cell count), plus a joint-size
        # square under every joint that has no stub
        stubs = {g for gs in STUB_GRIDS.values() for g in gs}
        squares = [(x - w / 2, y - w / 2, zb0 - t["lean"], x + w / 2, y + w / 2, zb0)
                   for g, (zb0, _, w) in nodes.items() if g not in stubs for x, y in (_xy(g),)]
        eq(tot("lean_concrete", "vol"), _union_volume([b for _, b in _gb_strips(lines, jb)] + squares), "GB lean")
        eb = t["cover"] + t["dt"] + t["d"] / 2
        anchor = lambda on: (jb[on[0][1]] + jb[on[-1][1]]) / 2 - 2 * eb + 2 * t["hook"]   # into both end joints
        # 4 main bars end to end; n_sp specials each: bottom mid·L per span, top sup·L each side of every joint
        eq(sum(sum(x["bars"]) for (e, _), x in r.items() if e == "rebar"),
           sum((4 + _bt(name)[1]["n_sp"]) * anchor(on) + G * (4 + _bt(name)[1]["n_sp"] * (t["mid"] + 2 * t["sup"]))
               for name, _, _, _, G, on in lines), "GB bars")
        # trench: the builder's cut pieces must fill the union (cell count) of every lean piece dug up to GL
        lean_b = [b for (n, _), b in _solids([C_GB]).items() if n.endswith("_Lean") and b[2] < GL]
        if lean_b:
            eq(tot("excavation", "vol"), _union_volume([(*b[:5], GL) for b in lean_b]), "GB trench")
        # stirrups read back from the model and checked against the spec in every clear span
        aw, expect = t["b"] / 2 - t["cover"] - t["dt"] / 2, 0.0
        for name, ax, _, _, _, on in lines:
            hz = hl[name] - 2 * t["cover"] - t["dt"]
            cu = bpy.data.objects[f"{_bt(name)[0]}_{name}_Stirrups"].data
            us = sorted(sp.points[0].co[ax] for sp in cu.splines)
            seen = 0
            for s0, s1 in _spans(on, jb):
                zs = [u for u in us if s0 < u < s1]
                seen += len(zs)
                assert len(zs) > 1 and abs(zs[0] - s0 - t["first"]) < 1e-5 and abs(s1 - zs[-1] - t["first"]) < 1e-5 \
                    and all(1e-6 < q - p <= t["s"] + 1e-6 for p, q in zip(zs, zs[1:])), f"stirrup spacing: {name}"
            pts = [p.co for sp in cu.splines for p in sp.points]
            assert seen == len(us), f"stirrup outside a clear span: {name}"
            assert abs(max(abs(p[1 - ax]) for p in pts) - aw) < 1e-6 and \
                abs(max(p[2] for p in pts) - min(p[2] for p in pts) - hz) < 1e-6, f"stirrup size: {name}"
            expect += len(us) * (2 * (2 * aw + hz) + 2 * t["shook"])
        eq(sum(sum(x["bars"]) for (e, _), x in r.items() if e == "stirrups"), expect, "GB stirrups")
        msg.append(f"{len(lines)} beam lines · {len(jb)} joints")
        colls.append(C_GB)
    cl = bpy.data.collections.get(C_COL)
    if C_GB in colls and cl and cl.objects:
        r, t, tn = qto(C_COL), COL, COL["type"]
        hs = {g: t["top"] - t["pt"] - lv[g][2] for g in lv}       # concrete stops under the plate
        pv = len(lv) * t["plate"] ** 2 * t["pt"]   # 6 mm at z ≈ 3 m: float32 leaves ~3e-5 of the thickness
        assert r[("plate", tn)]["n"] == len(lv) and abs(r[("plate", tn)]["vol"] - pv) <= 1e-3 * pv, f"{tn} plates"
        eq(r[("concrete", tn)]["vol"], t["b"] ** 2 * sum(hs.values()), f"{tn} concrete")
        eq(r[("concrete", tn)]["side"], 4 * t["b"] * sum(hs.values()), f"{tn} formwork")
        a, expect = t["b"] / 2 - t["cover"] - t["dt"] / 2, 0.0       # ties read back, checked against the spec
        for g in lv:
            cu = bpy.data.objects[f"{tn}_{g}_Ties"].data
            zs = sorted(sp.points[0].co.z for sp in cu.splines)
            z1 = lv[g][1] - lv[g][2]                                  # stub top, from the joint top
            assert abs(zs[0] - z1 - t["first"]) < 1e-5 and abs(zs[-1] - hs[g] + t["first"]) < 1e-5 and \
                all(1e-6 < q - p <= t["s"] + 1e-6 for p, q in zip(zs, zs[1:])), f"column tie spacing: {g}"
            assert abs(max(abs(p.co.x) for sp in cu.splines for p in sp.points) - a) < 1e-6, f"column tie size: {g}"
            expect += len(zs) * (8 * a + 2 * t["shook"])
            # the one-piece bars (stub stage) end `ext` above this column's top
            st = max((bpy.data.objects[f"{sn}_{g}_Bars"].matrix_world @ p.co.xyz).z
                     for sn, gs in STUB_GRIDS.items() if g in gs for sp in bpy.data.objects[f"{sn}_{g}_Bars"].data.splines
                     for p in sp.points)
            d = next(STUBS[sn]["d"] for sn, gs in STUB_GRIDS.items() if g in gs)
            assert abs(st - (t["top"] - t["pt"] - d / 2)) < 1e-5, f"column {g}: bars end at {st:.3f}, not under the plate"
        eq(sum(r[("ties", tn)]["bars"]), expect, f"{tn} ties")
        msg.append(f"{len(lv)} columns")
        colls.append(C_COL)
    sl = bpy.data.collections.get(C_SLAB)
    if C_GB in colls and sl and sl.objects:
        r, t, tn = qto(C_SLAB), SLAB, SLAB["type"]
        under = list(_solids([C_STUB, C_GB]).values())
        Z = _zones()
        area = {zn: sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in rects) for zn, (rects, _) in Z.items()}
        # zones cut out of each other still cover the plan once (cell count of the uncut rects)
        eq(sum(area.values()), _union_volume([(r[0], r[1], 0.0, r[2], r[3], 1.0) for rs, _ in ZONES.values() for r in rs]),
           "slab zones cover the plan once")
        holes = sum(_vol(i) for c in _col_prisms() + under for rs, top in Z.values() for x0, y0, x1, y1 in rs   # columns,
                    if (i := _inter(c, (x0, y0, top, x1, y1, top + t["t"]))))                                     # bath corner joints
        eq(r[("concrete", tn)]["vol"], t["t"] * sum(area.values()) - holes, f"{tn} slab")
        eq(r[("mesh", tn)]["area"], sum(area.values()), f"{tn} mesh area")
        # fill: zone × (top − GL) minus what the beams and joints already fill there (solids are disjoint)
        curb = r.get(("concrete", f"{tn}C"), {}).get("vol", 0.0)   # the curb fills over the lowered beams
        eq(r[("fill", tn)]["vol"] + curb, sum(area[zn] * (top - GL) - sum(_vol(i) for x0, y0, x1, y1 in rects for s in under + _col_prisms()
                                                                  if (i := _inter(s, (x0, y0, GL, x1, y1, top))))
                                       for zn, (rects, top) in Z.items()), f"{tn} fill")
        # mesh read back: a square of half-size mcover around every wire end lies inside its zone; gaps ≤ ms
        for zn, (rects, top) in Z.items():
            o, cv = bpy.data.objects[f"{tn}_{zn}_Mesh"], t["mcover"] - 1e-6
            zone = [(x0, y0, 0.0, x1, y1, 1.0) for x0, y0, x1, y1 in rects]
            for sp in o.data.splines:
                for p in (o.matrix_world @ q.co.xyz for q in sp.points):
                    assert not _cut((p.x - cv, p.y - cv, 0.0, p.x + cv, p.y + cv, 1.0), zone), f"mesh cover: {zn} {p}"
            for ax in (0, 1):   # ax 0: wires along x, their y positions
                ps = sorted({round((o.matrix_world @ sp.points[0].co.xyz)[1 - ax], 6) for sp in o.data.splines
                             if abs(sp.points[0].co[ax] - sp.points[-1].co[ax]) > 1e-9})
                assert all(0 < b - a <= t["ms"] + 1e-6 for a, b in zip(ps, ps[1:])), f"mesh spacing: {zn}"
        curbs = [b for (n, _), b in _solids([C_SLAB]).items() if bpy.data.objects[n].data.get("element") == "concrete"]
        conc_gb = [b for (n, _), b in _solids([C_GB]).items() if bpy.data.objects[n].data.get("element") == "concrete"]
        for zn, (rects, top) in Z.items():   # over every beam set below a zone's fill top: concrete, not soil (curb)
            for b in conc_gb:
                for x0, y0, x1, y1 in rects:
                    ix = (max(b[0], x0), max(b[1], y0), min(b[3], x1), min(b[4], y1))
                    if b[5] < top - 1e-4 and ix[2] - ix[0] > 1e-3 and ix[3] - ix[1] > 1e-3:
                        P = ((ix[0] + ix[2]) / 2, (ix[1] + ix[3]) / 2, (b[5] + top) / 2)
                        assert any(c[0] - 1e-6 <= P[0] <= c[3] + 1e-6 and c[1] - 1e-6 <= P[1] <= c[4] + 1e-6 and c[2] <= P[2] <= c[5]
                                   for c in curbs + conc_gb + _col_prisms()), f"{zn}: soil over a lowered beam at {P[0]:.2f}, {P[1]:.2f}"
        for (n, _), b in _solids([C_SLAB]).items():   # slab on the beam tops, fill from GL up to them
            top = ZONES[n.split("_")[1]][1]
            if n.endswith("_Curb"):   # up to the slab, standing on a beam set lower than this zone
                assert abs(b[5] - top) < 1e-5 and any(abs(u[5] - b[2]) < 1e-5 and u[0] - 1e-5 <= b[0] and b[3] <= u[3] + 1e-5
                                                      and u[1] - 1e-5 <= b[1] and b[4] <= u[4] + 1e-5 for u in under), f"{n} not on a beam"
                continue
            lo, hi = (top, top + t["t"]) if n.endswith("_Conc") else (GL, top)
            assert abs(b[2] - lo) < 1e-5 and abs(b[5] - hi) < 1e-5, f"{n} off its level"
        msg.append(f"{len(ZONES)} slab zones")
        colls.append(C_SLAB)
    # closed meshes; every solid made of boxes; no two boxes share volume, so each m³ is counted once
    boxes = _solids(colls)
    clash = [(a, b) for a, b in itertools.combinations(boxes, 2)
             if (i := _inter(boxes[a], boxes[b])) and _vol(i) > 1e-6]   # touching faces differ by float32 noise
    assert not clash, f"solids overlap: {clash[:3]}"
    if len(colls) > 1:   # each stub stands on its footing and stops under its beam
        for sn, gs in STUB_GRIDS.items():
            for k in gs:
                s = boxes[(f"{sn}_{k}_Conc", 0)]
                f = next(boxes[(f"{ft}_{k}_Conc", 0)] for ft, v in FOOTINGS.items() if k in v)
                assert abs(s[2] - f[5]) < 1e-5 and abs(s[5] - lv[k][1]) < 1e-5, f"stub {k} off its footing/beam"
                assert abs((s[0] + s[3]) / 2 - GX[k[1:]]) < 1e-5 and abs((s[1] + s[4]) / 2 - GY[k[0]]) < 1e-5, \
                    f"stub {k} off its grid point"
                if C_GB in colls:   # the joint sits on the stub, same footprint
                    j = boxes[(f"J1_{k}_Conc", 0)]
                    assert all(abs(j[i] - s[i]) < 1e-5 for i in (0, 1, 3, 4)) and abs(j[2] - s[5]) < 1e-5, \
                        f"joint {k} not on its stub"
                    if C_COL in colls:   # the column stands on the joint, centred, up to the ring-beam bottom
                        cb = boxes[(f"{COL['type']}_{k}_Conc", 0)]
                        pl = boxes[(f"{COL['type']}_{k}_Plate", 0)]   # plate on the concrete, top at COL top
                        assert abs(pl[2] - cb[5]) < 1e-5 and abs(pl[5] - COL["top"]) < 1e-5 and \
                            abs((pl[0] + pl[3]) / 2 - GX[k[1:]]) < 1e-5 and abs((pl[1] + pl[4]) / 2 - GY[k[0]]) < 1e-5, \
                            f"plate {k} off its column"
                        assert abs(cb[2] - j[5]) < 1e-5 and abs(cb[5] - COL["top"] + COL["pt"]) < 1e-5 and \
                            abs((cb[0] + cb[3]) / 2 - GX[k[1:]]) < 1e-5 and abs((cb[1] + cb[4]) / 2 - GY[k[0]]) < 1e-5, \
                            f"column {k} off its joint"
    if C_GB in colls:   # earthwork a second way: box subtraction instead of cell counting
        pit, dug, back, taken = _earth()
        trench = _exc_boxes(C_GB)
        assert not any(_inter(a, b) for a, b in itertools.combinations(trench, 2)), "trench pieces overlap"
        eq(dug, pit + sum(_vol(q) for tb in trench for q in _cut(tb, pits)), "dug")
        eq(taken, sum(_vol(s) - sum(_vol(q) for q in _cut(s, pits + trench)) for s in boxes.values()), "soil taken")
    return "selfcheck ok: " + " · ".join(msg)


def _cut(box, cutters):
    """Pieces of box outside every cutter box."""
    pieces = [box]
    for c in cutters:
        pieces = [q for p in pieces for q in _box_minus(p, c)]
    return pieces
