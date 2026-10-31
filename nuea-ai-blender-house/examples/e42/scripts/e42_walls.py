"""E42 ST06 ผนังและอะเส (spec 29 ต.ค.): 3-hole clay brick walls plastered both sides, concrete tie columns (เสาเอ็น),
prefab ladder lintels in the bed joints (ทับหลังสำเร็จ: over openings, under windows, mid-height), plaster on the
column faces and opening reveals, corner beads (เซี้ยม), and a steel wall plate (อะเส) on every beam line.
Needs e42_struct exec'd first.

Each wall line = an empty WL_<a>-<b> with _Brick, _Ties, _PlasterA/_PlasterB (the two faces), _Reveals, _TieBars,
_Ladders; each column CP_<grid>_Plaster; beads SM_Beads; each wall-plate run AS_<a>-<b>_2C. Exterior walls sit
flush with the columns' outer faces (plaster flush with the column plaster, the user); interior walls on the grid line.
Walls stop at column faces; where walls meet with no column the through wall gets a tie column and the other wall
stops at its brick face (at a corner the wall along x runs through).

    exec(open(<e42_struct>).read()); exec(open(<this file>).read()); build_walls(); print(report(C_WALL))
    print(selfcheck_walls())
"""
import itertools, math, os

exec(open(os.path.join(globals().get("SKILL_SCRIPTS") or os.path.expanduser("~/.claude/skills/nuea-ai-blender-house/scripts"), "steel_sections.py")).read())   # (SKILL_SCRIPTS: e42_load.py)

# brick: the user's spec 3-hole clay brick 6 × 10 × 20 cm laid 6 cm thick, 1 cm joints, 5 % breakage
WALL = dict(t=0.06, pl=0.015, tie_w=0.10, max_panel=2.50, min_panel=0.20, joint=0.01, brick_l=0.20, brick_h=0.10,
            waste=0.05, bar_d=0.006, bar_off=0.02, brick="อิฐมอญ 3 รู 6×10×20 ซม.", grade="St.180 ksc", bar="RB6 SR24")
PER_M2 = 1 / ((WALL["brick_l"] + WALL["joint"]) * (WALL["brick_h"] + WALL["joint"]))    # 43.3 bricks per m²
# lintels: prefab ladder (the user) in the bed joint over every opening and under every window, `lap` past each side,
# and one run at mid-height along the whole wall (walls over 3 m); sold in rolls
LADDER = dict(d=0.004, lap=0.20, roll=30.0, spec="เหล็กเอ็นทับหลังสำเร็จรูป SHP 4 มม. × 30 ม.")
# wall plate (spec 29 ต.ค.): two lipped C 100×50×20×2.3 toe to toe = a 100 × 100 box, 4.06 kg/m each (TIS table)
# modelled to the real profile (steel_sections.lipped_c, inner bend radius = t), section read off the ไทวัสดุ drawing
PLATE = dict(b=0.10, h=0.10, kg_m=2 * 4.06, pieces=2, stock=6.0, spec="อะเส 2C ประกบ 100×50×20×2.3 มม.",
             c=(0.100, 0.050, 0.020, 0.0023), c_kg_m=TIS[(100, 50, 20, 2.3)])
# corner bead (the user): KASSA PVC angle bead, 1 cm legs, 2 m pieces — modelled as its L on the plaster corner
BEAD = dict(leg=0.01, th=0.001, stock=2.0, spec="เซี้ยม KASSA มุมคม PVC 1.0 × 200 ซม.")
WALL_BASE = ZONES["House"][1] + SLAB["t"]          # on the slab over the beams (+0.42)
WALL_TOP = COL["top"]                              # up to the wall plate's underside (+3.45)
WALL_LINES = [("A1", "A2"), ("E1", "E3"), ("A1", "E1"), ("B3", "E3"), ("B2", "B3"), ("A2", "E2"), ("C1", "C2"),
              ("D1", "D2")]                        # e42_build build_walls (A2-B2 + B2-E2 are one line)
# exterior side → flush with the columns (the user). A2-E2 faces the porch on its A2-B2 stretch: the whole line goes
# flush to +x, so the living room side is flush with D2/E2 as well and the bedroom side has the columns proud.
OUTSIDE = {"A1-A2": -1, "E1-E3": 1, "A1-E1": -1, "B3-E3": 1, "B2-B3": -1, "A2-E2": 1}
OFFSET = {n: s * (COL["b"] / 2 - WALL["t"] / 2) for n, s in OUTSIDE.items()}
# (name, wall line, c0, c1 along the line, bottom, head) from e42_build WIN/DOORS; doors start at the slab top
# Door openings left after plaster + beads so door and frame go in (spec 29 ต.ค.), W × H from FL +0.45:
#   (spec 31 ต.ค., ST14) bedrooms + kitchen MASTERWOOD uPVC 80 × 200 in a KASSA WPC T1 80 × 200 frame (10 cm jamb;
#   ระยะช่องปูน not published — ECO DOOR's 2" × 4" frame of the same size asks 88 × 205 and KASSA ships it 88 × 205:
#   assumed); bath ECO DOOR uPVC W2 70 × 200 in an ECO DOOR WPC TVWG-100 frame: the maker's ระยะช่องปูน 78 × 205.
#   Brick opening = that + plaster each side and over the head. D4's west edge stays at 3.35 (the brick pier to D2_Bed2
#   stays min_panel wide: the heater run crosses there) and D3's east one at 6.55 (SW_Kitchen's room), both widened
#   the other way.
# Aluminium (spec 31 ต.ค., ST14): black units sold by their overall frame size (ขนาดรวมวงกบ, HomePro listings: WINDOW
# ASIA F10 / AZLE 120 × 110, 10 cm deep), set in a plaster clear UNIT_GAP bigger each side (sealant; assumed). The
# windows keep their old centres; D1 (4-panel sliding) stands on the floor like the doors, UNIT_GAP under its head.
UNIT = {"W1": (1.20, 1.10), "W2": (0.60, 1.10), "W3": (1.20, 0.90), "W4": (0.60, 0.50), "D1": (2.60, 2.05)}
UNIT_GAP = 0.005
UNIT_DEPTH = 0.10   # the listings' 10 cm: deeper than the finished wall, so the frame fills the reveal
DOOR_CLEAR = {"D2_Bed2": (0.88, 2.05), "D2_Bed1": (0.88, 2.05), "D4_Bath": (0.78, 2.05), "D3_Kitchen": (0.88, 2.05),
              "D1_Porch": (UNIT["D1"][0] + 2 * UNIT_GAP, UNIT["D1"][1] + UNIT_GAP)}
_dw = lambda n: DOOR_CLEAR[n][0] + 2 * WALL["pl"]
_dh = lambda n: 0.45 + DOOR_CLEAR[n][1] + WALL["pl"]


def _win(n, ln, c, zc):
    """A window's brick opening round its unit: unit + UNIT_GAP + plaster each side, centred on (c, zc)."""
    w, h = (v + 2 * (UNIT_GAP + WALL["pl"]) for v in UNIT[n[:2]])
    return (n, ln, c - w / 2, c + w / 2, zc - h / 2, zc + h / 2)


OPENINGS = [_win("W1_Bed2_Front", "A1-A2", 1.50, 1.90), _win("W2_Bed2_Side", "A1-E1", 0.55, 1.90),
            _win("W4_Bath", "A1-E1", 3.75, 2.20), _win("W2_Bed1_Side", "A1-E1", 5.10, 1.90),
            _win("W1_Bed1_Rear", "E1-E3", 1.50, 1.90), _win("W3_Kitchen", "E1-E3", 4.50, 2.00),
            _win("W1_Living", "B3-E3", 2.60, 1.90), ("D1_Porch", "B2-B3", 4.50 - _dw("D1_Porch") / 2, 4.50 + _dw("D1_Porch") / 2, WALL_BASE, _dh("D1_Porch")),
            ("D3_Kitchen", "B3-E3", 6.55 - _dw("D3_Kitchen"), 6.55, WALL_BASE, _dh("D3_Kitchen")), ("D2_Bed2", "A2-E2", 2.85 - _dw("D2_Bed2"), 2.85, WALL_BASE, _dh("D2_Bed2")),
            ("D4_Bath", "A2-E2", 3.35, 3.35 + _dw("D4_Bath"), WALL_BASE, _dh("D4_Bath")), ("D2_Bed1", "A2-E2", 4.65, 4.65 + _dw("D2_Bed1"), WALL_BASE, _dh("D2_Bed1"))]


def _wlines(pairs, offset=None):
    out = {}
    for a, b in pairs:
        pa, pb = _xy(a), _xy(b)
        assert pa[0] == pb[0] or pa[1] == pb[1], f"{a}-{b} not along a grid line"
        ax = 0 if pa[1] == pb[1] else 1
        if pa[ax] > pb[ax]:
            a, b, pa, pb = b, a, pb, pa
        n = f"{a}-{b}"
        out[n] = dict(ax=ax, gk=pa[1 - ax], k=pa[1 - ax] + (offset or {}).get(n, 0.0), u0=pa[ax], u1=pb[ax])
    return out


def _layout(pairs, half, pl=0.0, tie_w=0.0, columns=True, offset=None):
    """Per line: extent lo..hi, column gaps, junction ties, face cuts and corner plaster starts.
    Junctions are found on the grid; the geometry uses each line's own centreline k (exterior walls sit off the grid).
    A line ending on another stops at its face; a line passing a junction runs on (and takes a tie column + a cut in
    the face the other line meets); where both end (a corner) the line along x runs to the other's outer face."""
    L = _wlines(pairs, offset)
    colw = {g: COL["b"] for gs in STUB_GRIDS.values() for g in gs} if columns else {}
    for l in L.values():
        l.update(lo=l["u0"], hi=l["u1"], cols=[], ties=[], cuts={1: [], -1: []}, outer={})
        for g, w in colw.items():
            x = _xy(g)
            if abs(x[1 - l["ax"]] - l["gk"]) < 1e-9 and l["u0"] - 1e-9 <= x[l["ax"]] <= l["u1"] + 1e-9:
                u = x[l["ax"]]
                if abs(u - l["u0"]) < 1e-9:
                    l["lo"] = u + w / 2
                elif abs(u - l["u1"]) < 1e-9:
                    l["hi"] = u - w / 2
                else:
                    l["cols"].append((u - w / 2, u + w / 2))
    at_col = lambda p: any(abs(_xy(g)[0] - p[0]) < 1e-9 and abs(_xy(g)[1] - p[1]) < 1e-9 for g in colw)
    for (n1, l1), (n2, l2) in itertools.permutations(L.items(), 2):
        if l1["ax"] == l2["ax"] or not (l1["u0"] - 1e-9 <= l2["gk"] <= l1["u1"] + 1e-9 and
                                        l2["u0"] - 1e-9 <= l1["gk"] <= l2["u1"] + 1e-9):
            continue
        if at_col((l2["gk"], l1["gk"]) if l1["ax"] == 0 else (l1["gk"], l2["gk"])):
            continue
        ug = l2["gk"]                                                # the junction along l1, on the grid
        e1 = min(abs(ug - l1["u0"]), abs(ug - l1["u1"])) < 1e-9
        e2 = min(abs(l1["gk"] - l2["u0"]), abs(l1["gk"] - l2["u1"])) < 1e-9
        assert e1 or e2, f"{n1} and {n2} cross: no rule for a wall crossing"
        d1 = 1 if abs(ug - l1["u0"]) < 1e-9 else -1                  # into l1 from the junction
        d2 = 1 if abs(l1["gk"] - l2["u0"]) < 1e-9 else -1            # into l2 = the face of l1 that l2 meets
        u = l2["k"]                                                  # where l2 actually stands
        if (e2 and not e1) or (e1 and e2 and l1["ax"] == 0):         # l1 runs through
            if e1:                                                   # corner: run out to the other's outer face
                end = u - d1 * half
                l1["lo" if d1 > 0 else "hi"] = end
                if tie_w:
                    l1["ties"].append(tuple(sorted((end, end + d1 * tie_w))))
            elif tie_w:
                l1["ties"].append((u - tie_w / 2, u + tie_w / 2))
            l1["cuts"][d2].append((u - half - pl, u + half + pl))
        else:                                                        # stop at the other's face
            l1["lo" if d1 > 0 else "hi"] = u + d1 * half
            if e2:                                                   # corner: the outer face wraps the other's end
                l1["outer"][-d2] = (d1, u - d1 * (half + pl))
    return L


def _iv_minus(iv, holes):
    """1-D intervals iv minus holes."""
    out = list(iv)
    for h0, h1 in holes:
        out = [q for a, b in out for q in ((a, min(b, h0)), (max(a, h1), b)) if q[1] - q[0] > 1e-9]
    return out


def _merge(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + 1e-9:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(x) for x in out]


def _wall_plan(name, l):
    """Tie-column intervals, brick panels and the openings of one wall line (u along the line)."""
    t, w = WALL, WALL["tie_w"]
    ops = sorted((c0, c1, zb, zt, on) for on, ln, c0, c1, zb, zt in OPENINGS if ln == name)
    blocked = _merge(l["cols"])
    ties = list(l["ties"])
    for c0, c1, *_ in ops:
        assert l["lo"] - 1e-9 <= c0 < c1 <= l["hi"] + 1e-9, f"{name}: opening outside the wall"
        ties += _iv_minus([(c0 - w, c0), (c1, c1 + w)], blocked + [(-1e9, l["lo"]), (l["hi"], 1e9)])
    for _ in range(3):   # slivers of brick narrower than min_panel become concrete; long panels get ties
        ties = _merge(ties)
        panels = _iv_minus([(l["lo"], l["hi"])], blocked + ties + [(c0, c1) for c0, c1, *_ in ops])
        ties += [p for p in panels if p[1] - p[0] < t["min_panel"] - 1e-9]
    ties = _merge(ties)
    panels = _iv_minus([(l["lo"], l["hi"])], blocked + ties + [(c0, c1) for c0, c1, *_ in ops])
    for a, b in list(panels):
        if b - a > t["max_panel"] + 1e-9:
            n = math.ceil((b - a - t["max_panel"]) / (t["max_panel"] + w) - 1e-9)
            gap = (b - a - n * w) / (n + 1)
            ties += [(a + (i + 1) * gap + i * w, a + (i + 1) * (gap + w)) for i in range(n)]
    ties = _merge(ties)
    panels = _iv_minus([(l["lo"], l["hi"])], blocked + ties + [(c0, c1) for c0, c1, *_ in ops])
    return ties, panels, ops


def build_walls():
    """ST06: walls on WALL_LINES, column and reveal plaster, corner beads, wall plates."""
    t, H, p_ = WALL, WALL_TOP - WALL_BASE, WALL["pl"]
    for v in bpy.context.scene.view_layers:   # the old one-piece walls would count twice
        lc = _find_lc(v.layer_collection, "E42 Walls")
        if lc:
            lc.exclude = True
    c = _clear(C_WALL)
    brick_m = mat("M_Brick", (0.62, 0.30, 0.20), 0.9)
    conc = bpy.data.materials.get("rough_concrete_material_Str_Footings") or mat("M_Concrete", (0.50, 0.50, 0.48), 0.85)
    plaster_m = mat("M_Plaster", (0.85, 0.84, 0.80), 0.9)
    steel = mat("M_Rebar", (0.28, 0.17, 0.11), 0.55, 0.6)
    c_m = mat("M_Steel_C", (0.05, 0.05, 0.055), 0.35, 1.0)   # black cold-formed channel as sold (ไทวัสดุ photo)
    bead_m = mat("M_Bead", (0.95, 0.55, 0.10), 0.6)
    lay = _layout(WALL_LINES, t["t"] / 2, p_, t["tie_w"], offset=OFFSET)
    hv, dv, zmid = t["t"] / 2, t["t"] / 2 + p_, WALL_BASE + H / 2
    wall_solids, plan, open_beads, todo = [], [], [], []
    for name, l in lay.items():
        ax, k = l["ax"], l["k"]
        ties, panels, ops = _wall_plan(name, l)
        box = lambda u0, u1, v0, v1, z0, z1: _uv(ax, u0, k + v0, z0, u1, k + v1, z1)
        brick = [box(a, b, -hv, hv, WALL_BASE, WALL_TOP) for a, b in panels]
        for c0, c1, zb, zt, _ in ops:   # no concrete lintel: brick on the ladder over the opening, under a window
            brick.append(box(c0, c1, -hv, hv, zt, WALL_TOP))
            if zb > WALL_BASE + 1e-9:
                brick.append(box(c0, c1, -hv, hv, WALL_BASE, zb))
        tie_boxes = [box(a, b, -hv, hv, WALL_BASE, WALL_TOP) for a, b in ties]
        reveals = [q for c0, c1, zb, zt, _ in ops for q in    # jambs full height, head (and sill) between, wall-deep
                   [box(c0, c0 + p_, -dv, dv, zb, zt), box(c1 - p_, c1, -dv, dv, zb, zt),
                    box(c0 + p_, c1 - p_, -dv, dv, zt - p_, zt)] +
                   ([box(c0 + p_, c1 - p_, -dv, dv, zb, zb + p_)] if zb > WALL_BASE + 1e-9 else [])]
        plaster = {}
        for s_ in (1, -1):   # the two faces: over brick and concrete, not over columns, cut where a wall meets
            lo, hi = l["lo"], l["hi"]
            if s_ in l["outer"]:
                d, start = l["outer"][s_]
                lo, hi = (start, hi) if d > 0 else (lo, start)
            iv = _iv_minus([(lo, hi)], _merge(l["cols"]) + l["cuts"][s_])
            v0, v1 = (hv, dv) if s_ > 0 else (-dv, -hv)
            holes = [box(c0, c1, v0, v1, zb, zt) for c0, c1, zb, zt, _ in ops]
            plaster[s_] = [q for a, b in iv for q in _cut(box(a, b, v0, v1, WALL_BASE, WALL_TOP), holes)]
            vp = k + s_ * dv                                         # the face plaster's plane
            for c0, c1, zb, zt, _ in ops:   # beads where the face plaster meets the reveal plaster
                win = zb > WALL_BASE + 1e-9
                za, zz = (zb + p_ if win else zb), zt - p_
                open_beads += _bead(2, za, zz, {ax: (c0 + p_, -1), 1 - ax: (vp, -s_)})      # jambs
                open_beads += _bead(2, za, zz, {ax: (c1 - p_, 1), 1 - ax: (vp, -s_)})
                open_beads += _bead(ax, c0 + p_, c1 - p_, {2: (zt - p_, 1), 1 - ax: (vp, -s_)})   # head
                if win:
                    open_beads += _bead(ax, c0 + p_, c1 - p_, {2: (zb + p_, -1), 1 - ax: (vp, -s_)})
        o = t["bar_off"]
        tie_bars = [[_pt(ax, (a + b) / 2 + d_, k, WALL_BASE), _pt(ax, (a + b) / 2 + d_, k, WALL_TOP)]
                    for a, b in ties for d_ in (-o, o) if b - a >= 2 * o + t["bar_d"]]
        ladders = [[_pt(ax, a, k, z), _pt(ax, b, k, z)] for a, b, z in _ladder_runs(l, ops, zmid)]
        wall_solids += brick + tie_boxes + plaster[1] + plaster[-1] + reveals
        plan += [(b[0], b[1], b[3], b[4]) for b in brick + tie_boxes + plaster[1] + plaster[-1]]
        todo.append((name, (*_pt(ax, l["u0"], k, 0)[:2], WALL_BASE), brick, tie_boxes, plaster, reveals, tie_bars,
                     ladders))
    # columns: plaster round every column, less what the walls (brick, ties, their plaster) already take
    cols = []
    for g in sorted({g for gs in STUB_GRIDS.values() for g in gs}):
        x, y = _xy(g)
        w, z0, z1 = COL["b"] / 2, _slab_top_at(x, y), COL["top"] - COL["pt"]
        cols.append((g, (x, y, z0), [q for b in _col_ring(x, y, z0, z1) for q in _cut(b, wall_solids)]))
        plan.append((x - w - p_, y - w - p_, x + w + p_, y + w + p_))
    # corner beads: every outside vertical corner of the plastered plan, and round every opening on both faces.
    # Fixed before plastering (the user): each bead lies in the plaster, which is cut round it; `void` keeps the
    # plaster's area whole (plaster is bought by the face area, the bead takes none of it)
    corner_beads = [b for x, y, z0, z1, ix, iy in _outside_corners(plan) for b in _bead(2, z0, z1, {0: (x, ix), 1: (y, iy)})]
    beads = corner_beads + open_beads

    def plaster_data(name, bs, loc, **props):
        cut = [q for b in bs for q in _cut(b, [e for e in beads if _inter(b, e)])]
        void = sum(_vol(i) for b in bs for e in beads if (i := _inter(b, e)))
        return _boxes_data(name, [tuple(b[i] - loc[i % 3] for i in range(6)) for b in cut], plaster_m, element="plaster",
                           t=p_, void=void, **props)
    for name, loc, brick, tie_boxes, plaster, reveals, tie_bars, ladders in todo:
        rel = lambda bs: [tuple(b[i] - loc[i % 3] for i in range(6)) for b in bs]
        relp = lambda ws: [[tuple(q[i] - loc[i] for i in range(3)) for q in w_] for w_ in ws]
        D = {"Brick": _boxes_data(f"WL_{name}_Brick", rel(brick), brick_m, element="masonry", th=t["brick"], type="WL1",
                                  t=t["t"], per_m2=PER_M2, waste=t["waste"]),
             "Ties": _boxes_data(f"WL_{name}_Ties", rel(tie_boxes), conc, element="concrete", th="คอนกรีตเสาเอ็น",
                                 type="TC1", grade=t["grade"]),
             "PlasterA": plaster_data(f"WL_{name}_PlasterA", plaster[1], loc, th="ฉาบปูนผนัง 1.5 ซม.", type="PL1"),
             "PlasterB": plaster_data(f"WL_{name}_PlasterB", plaster[-1], loc, th="ฉาบปูนผนัง 1.5 ซม.", type="PL1")}
        if reveals:
            D["Reveals"] = plaster_data(f"WL_{name}_Reveals", reveals, loc, th="ฉาบปูนข้างช่องเปิด (ความลึกเท่าผนัง)",
                                        type="PL3")
        if tie_bars:
            D["TieBars"] = _rebar_data(f"WL_{name}_TieBars", relp(tie_bars), t["bar_d"], steel, element="rebar",
                                       th="เหล็กเสาเอ็น", type="TC1", bar=t["bar"], dia_mm=round(t["bar_d"] * 1000))
        D["Ladders"] = _rebar_data(f"WL_{name}_Ladders", relp(ladders), LADDER["d"], steel, element="ladder",
                                   th=LADDER["spec"], type="LD1", roll=LADDER["roll"])
        _link(c, f"WL_{name}", loc, D, line=name)
    for g, loc, pieces in cols:
        _link(c, f"CP_{g}", loc, {"Plaster": plaster_data(f"CP_{g}_Plaster", pieces, loc,
                                                         th="ฉาบปูนเสา (ผิวที่ไม่ติดผนัง)", type="PL2")}, grid=g)
    _link(c, "SM_Beads", (0.0, 0.0, 0.0), {
        "Corners": _boxes_data("SM_Beads_Corners", corner_beads, bead_m, element="bead", type="SM1",
                               th=f"{BEAD['spec']} มุมเสา/มุมผนัง", stock=BEAD["stock"]),
        "Openings": _boxes_data("SM_Beads_Openings", open_beads, bead_m, element="bead", type="SM2",
                                th=f"{BEAD['spec']} ขอบช่องเปิด (สองด้าน)", stock=BEAD["stock"])})
    # wall plates: one continuous 2C per grid line (collinear beam lines merged), on the column cap plates: two
    # lipped channels lips to lips, webs outside, centred on the line
    poly = lipped_c(*PLATE["c"])
    for name, l in _layout(_plate_pairs(), PLATE["b"] / 2, columns=False).items():
        ax, k = l["ax"], l["k"]
        loc = (*_pt(ax, l["u0"], k, 0)[:2], WALL_TOP)
        _drop(bpy.data.meshes, f"AS_{name}_2C")
        bm = bmesh.new()
        for side in (-1, 1):
            prism(bm, poly, l["lo"] - l["u0"], l["hi"] - l["u0"],
                  lambda u, s_, z, side=side: _pt(ax, u, side * (PLATE["b"] / 2 - s_), z))
        me = bpy.data.meshes.new(f"AS_{name}_2C")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(c_m)
        for k_, v in dict(element="steel", th=PLATE["spec"], type="AS1", kg_m=PLATE["kg_m"], stock=PLATE["stock"],
                          pieces=PLATE["pieces"], swept=True).items():
            me[k_] = v
        _link(c, f"AS_{name}", loc, {"2C": me}, line=name)
    return len(lay)


def _ladder_runs(l, ops, zmid):
    """(u0, u1, z) ladder runs of one wall line: over each opening and under each window, `lap` past both jambs,
    in the bed joint; one run at mid-height broken only by columns and the openings it would cross."""
    t, lap, out = WALL, LADDER["lap"], []
    stop = _merge(l["cols"]) + [(-1e9, l["lo"]), (l["hi"], 1e9)]
    for c0, c1, zb, zt, _ in ops:
        out += [(a, b, zt + t["joint"] / 2) for a, b in _iv_minus([(c0 - lap, c1 + lap)], stop)]
        if zb > WALL_BASE + 1e-9:
            out += [(a, b, zb - t["joint"] / 2) for a, b in _iv_minus([(c0 - lap, c1 + lap)], stop)]
    course = t["brick_h"] + t["joint"]   # no second ladder in the same course as a head/sill run
    near = [(a, b) for a, b, z in out if abs(z - zmid) < course]
    out += [(a, b, zmid) for a, b in _iv_minus([(l["lo"], l["hi"])], _merge(l["cols"]) + near +
                                            [(c0, c1) for c0, c1, zb, zt, _ in ops if zb < zmid < zt])]
    return out


def _col_ring(x, y, z0, z1):
    """The plaster skin round a column: faces across x wrap the corners."""
    w, p = COL["b"] / 2, WALL["pl"]
    return [(x + w, y - w - p, z0, x + w + p, y + w + p, z1), (x - w - p, y - w - p, z0, x - w, y + w + p, z1),
            (x - w, y + w, z0, x + w, y + w + p, z1), (x - w, y - w - p, z0, x + w, y - w, z1)]


def _bead(run, a0, a1, at):
    """Angle bead along axis `run` from a0 to a1, on the corner at[axis] = (coordinate, inside sign) for the other two
    axes: two legs `leg` wide, `th` thick, inside the plaster, outer faces flush with the plaster faces (nose on the
    corner, in the first leg): fixed to the corner first, plastered over up to its nose."""
    (j, (pj, sj)), (k, (pk, sk)) = sorted(at.items())
    lo, hi = [0.0] * 3, [0.0] * 3

    def box(rj, rk):
        for ax_, r in ((run, (a0, a1)), (j, rj), (k, rk)):
            lo[ax_], hi[ax_] = min(r), max(r)
        return (*lo, *hi)
    L, T = BEAD["leg"], BEAD["th"]
    return [box((pj, pj + sj * T), (pk, pk + sk * L)),       # under the face across j, from the nose
            box((pj + sj * T, pj + sj * L), (pk, pk + sk * T))]   # under the face across k


def _outside_corners(plan):
    """(x, y, z0, z1, ix, iy) of every convex corner of the union of plan rects: exactly one of the four quadrants
    round the point is inside (that one is ix, iy). Column corners run slab top → cap plate, walls the wall height."""
    inside = lambda px, py: any(r[0] < px < r[2] and r[1] < py < r[3] for r in plan)
    e, seen, out = 1e-4, set(), []
    for r in plan:
        for px, py in ((r[0], r[1]), (r[0], r[3]), (r[2], r[1]), (r[2], r[3])):
            key = (round(px, 5), round(py, 5))
            if key in seen:
                continue
            seen.add(key)
            if sum(inside(px + sx * e, py + sy * e) for sx in (-1, 1) for sy in (-1, 1)) != 1:
                continue
            col = [g for gs in STUB_GRIDS.values() for g in gs
                   if abs(px - _xy(g)[0]) <= COL["b"] / 2 + WALL["pl"] + 1e-6 and
                   abs(py - _xy(g)[1]) <= COL["b"] / 2 + WALL["pl"] + 1e-6]
            z0, z1 = (_slab_top_at(*_xy(col[0])), COL["top"] - COL["pt"]) if col else (WALL_BASE, WALL_TOP)
            ix, iy = next((sx, sy) for sx in (-1, 1) for sy in (-1, 1) if inside(px + sx * e, py + sy * e))
            out.append((px, py, z0, z1, ix, iy))
    return out


def _slab_top_at(x, y):
    tops = [top + SLAB["t"] for rects, top in _zones().values() for x0, y0, x1, y1 in rects
            if x0 - 1e-9 <= x <= x1 + 1e-9 and y0 - 1e-9 <= y <= y1 + 1e-9]
    assert tops, f"no slab at {x}, {y}"
    return max(tops)


def _link(c, root_name, loc, D, **props):
    root = bpy.data.objects.new(root_name, None)
    root.empty_display_type, root.empty_display_size = "PLAIN_AXES", 0.2
    root.location = loc
    for k_, v in props.items():
        root[k_] = v
    c.objects.link(root)
    for key, data in D.items():
        ob = bpy.data.objects.new(f"{root_name}_{key}", data)
        ob.parent = root
        c.objects.link(ob)


def _plate_pairs():
    """Beam lines merged per grid line into continuous runs (a plate runs through a column)."""
    runs = []
    for ax in (0, 1):
        groups = {}
        for a, b, _ in GB_LINES:
            pa, pb = _xy(a), _xy(b)
            if (ax == 0) == (pa[1] == pb[1]):
                groups.setdefault(pa[1 - ax], []).append(tuple(sorted(((pa[ax], a), (pb[ax], b)))))
        for k, segs in groups.items():
            cur = None
            for (u0, a), (u1, b) in sorted(segs):
                if cur and u0 <= cur[1][0] + 1e-9:
                    cur = (cur[0], max(cur[1], (u1, b)))
                else:
                    if cur:
                        runs.append((cur[0][1], cur[1][1]))
                    cur = ((u0, a), (u1, b))
            runs.append((cur[0][1], cur[1][1]))
    return runs


def selfcheck_walls():
    """Walls, plaster, ladders, beads and plates against the spec, read back from the model."""
    t, H, p_ = WALL, WALL_TOP - WALL_BASE, WALL["pl"]
    r = qto(C_WALL)

    def eq(a, b, what):
        assert abs(a - b) <= 1e-5 * max(abs(b), 1e-9), f"{what}: model {a} != expected {b}"
    sol, L = _solids([C_WALL]), _wlines(WALL_LINES, OFFSET)   # the user's door openings, measured in the built wall
    for n, (w_, h_) in DOOR_CLEAR.items():
        _, ln, c0, c1, _, _ = next(o for o in OPENINGS if o[0] == n)
        l = L[ln]
        ax, mid = l["ax"], (c0 + c1) / 2   # OPENINGS are absolute along the axis
        bs = [b for (o, _), b in sol.items() if bpy.data.objects[o].data.get("element") in ("masonry", "concrete")
              and b[1 - ax] < l["k"] < b[4 - ax] and b[ax] < c1 + 0.5 and b[ax + 3] > c0 - 0.5]   # (D1 is 2.6 m wide)
        side = [b for b in bs if b[2] < WALL_BASE + 1.0 < b[5]]
        w = min(b[ax] for b in side if b[ax] >= mid) - max(b[ax + 3] for b in side if b[ax + 3] <= mid) - 2 * p_
        h = min(b[2] for b in bs if b[ax] < mid < b[ax + 3] and b[2] > WALL_BASE + 0.5) - p_ - 0.45   # under the head plaster
        assert abs(w - w_) < 1e-4 and abs(h - h_) < 1e-4, f"{n}: opening {w:.3f} × {h:.3f}, the user: {w_} × {h_}"
    lay = _layout(WALL_LINES, t["t"] / 2, p_, t["tie_w"], offset=OFFSET)
    face, walls = 0.0, []
    for name, l in lay.items():
        ax = l["ax"]
        bs = {k_: _solids_named(f"WL_{name}_{k_}") for k_ in ("Brick", "Ties", "PlasterA", "PlasterB", "Reveals")}
        walls += [b for v in bs.values() for b in v]
        ops = [(c0, c1, zb, zt) for _, ln, c0, c1, zb, zt in OPENINGS if ln == name]
        # the wall plane closes: brick + tie columns = (extent − columns) × height − openings
        got = sum((b[3 + ax] - b[ax]) * (b[5] - b[2]) for k_ in ("Brick", "Ties") for b in bs[k_])
        exp = (l["hi"] - l["lo"] - sum(b - a for a, b in l["cols"])) * H - sum((c1 - c0) * (zt - zb) for c0, c1, zb, zt in ops)
        eq(got, exp, f"wall plane {name}")
        face += exp
        for b in bs["Brick"]:   # no full-height panel over max_panel, no brick against an opening's jamb
            full = abs(b[2] - WALL_BASE) < 1e-5 and abs(b[5] - WALL_TOP) < 1e-5
            assert not full or b[3 + ax] - b[ax] <= t["max_panel"] + 1e-6, f"{name}: brick panel {b[3 + ax] - b[ax]:.2f} m"
            for c0, c1, zb, zt in ops:
                if min(b[5], zt) - max(b[2], zb) > 1e-6:
                    assert abs(b[3 + ax] - c0) > 1e-6 and abs(b[ax] - c1) > 1e-6, f"{name}: brick against a jamb"
        if name in OUTSIDE:   # exterior plaster flush with the column plaster (the user)
            s_ = OUTSIDE[name]
            plane = l["gk"] + s_ * (COL["b"] / 2 + p_)
            far = max(b[4 - ax] for b in bs["PlasterA"] + bs["PlasterB"]) if s_ > 0 else \
                min(b[1 - ax] for b in bs["PlasterA"] + bs["PlasterB"])
            assert abs(far - plane) < 1e-5, f"{name}: outer plaster at {far:.3f}, column plaster at {plane:.3f}"
    eq(r[("masonry", "WL1")]["vol"] / t["t"] + r[("concrete", "TC1")]["vol"] / t["t"], face, "brick + tie columns")
    exp = 0.0   # wall plaster: both faces of every line, less columns, junction cuts and openings
    for name, l in lay.items():
        ops = [(c0, c1, zb, zt) for _, ln, c0, c1, zb, zt in OPENINGS if ln == name]
        for s_ in (1, -1):
            lo, hi = l["lo"], l["hi"]
            if s_ in l["outer"]:
                d, start = l["outer"][s_]
                lo, hi = (start, hi) if d > 0 else (lo, start)
            exp += sum(b - a for a, b in _iv_minus([(lo, hi)], _merge(l["cols"]) + l["cuts"][s_])) * H - \
                sum((c1 - c0) * (zt - zb) for c0, c1, zb, zt in ops)
    pl = lambda tn: (r[("plaster", tn)]["vol"] + r[("plaster", tn)]["void"]) / p_   # area: bead room put back
    beads = _solids_named("SM_Beads_Corners") + _solids_named("SM_Beads_Openings")
    # beads fixed before plastering: every bead inside the plaster, the plaster cut round exactly that much
    v_in, v_b = sum(r[("plaster", tn)]["void"] for tn in ("PL1", "PL2", "PL3")), sum(map(_vol, beads))
    assert abs(v_in - v_b) <= 1e-3 * v_b, f"beads in the plaster: {v_in} != {v_b}"   # 1 mm legs: float32 noise
    pls = [b for n, b in _solids([C_WALL]).items() if n[0].endswith(("Plaster", "PlasterA", "PlasterB", "Reveals"))]
    for b in beads:   # read back from the model: every leg still sits in the plaster (void is a build-time number)
        g = (*(v - 1e-4 for v in b[:3]), *(v + 1e-4 for v in b[3:]))
        assert any(_inter(g, q) for q in pls), f"bead leg out of the plaster at {tuple(round(v, 3) for v in b)}"
    eq(pl("PL1"), exp, "wall plaster area")
    # column plaster = the ring round every column less what the walls take (walls and ring pieces are disjoint)
    ring = [b for g in {g for gs in STUB_GRIDS.values() for g in gs} for b in
            _col_ring(*_xy(g), _slab_top_at(*_xy(g)), COL["top"] - COL["pt"])]
    eq(r[("plaster", "PL2")]["vol"], sum(map(_vol, ring)) - sum(_vol(i) for a in ring for b in walls + beads
                                                                 if (i := _inter(a, b))),
       "column plaster")
    eq(pl("PL3"), sum((t["t"] + 2 * p_) * (2 * (zt - zb) + (2 if zb > WALL_BASE + 1e-9 else 1) *
                                                                  (c1 - c0 - 2 * p_)) for _, _, c0, c1, zb, zt in OPENINGS),
       "reveal plaster area")
    # ladders: over/under the openings + the mid-height runs
    zmid = WALL_BASE + H / 2
    exp = sum(b - a for name, l in lay.items() for a, b, _ in
              _ladder_runs(l, [(c0, c1, zb, zt, on) for on, ln, c0, c1, zb, zt in OPENINGS if ln == name], zmid))
    eq(sum(r[("ladder", "LD1")]["bars"]), exp, "ladder lintels")
    # beads (2 legs per bead, legs in order): round each opening on both faces at the plaster corners; one per
    # outside corner of the plastered plan read back from the model (plaster + the beads set in it)
    edges = lambda tn: r[("bead", tn)]["lens"][::2]
    eq(sum(edges("SM2")), sum(2 * (2 * (zt - p_ - (zb + p_ if zb > WALL_BASE + 1e-9 else zb)) +
                                   (2 if zb > WALL_BASE + 1e-9 else 1) * (c1 - c0 - 2 * p_))
                              for _, _, c0, c1, zb, zt in OPENINGS), "opening beads")
    plan = [(b[0], b[1], b[3], b[4]) for b in walls + beads if b[5] - b[2] > 1e-6] + \
        [(x - COL["b"] / 2 - p_, y - COL["b"] / 2 - p_, x + COL["b"] / 2 + p_, y + COL["b"] / 2 + p_)
         for x, y in (_xy(g) for gs in STUB_GRIDS.values() for g in gs)]
    corners = _outside_corners(plan)
    assert len(edges("SM1")) == len(corners), f"{len(edges('SM1'))} corner beads for {len(corners)} outside corners"
    eq(sum(edges("SM1")), sum(z1 - z0 for _, _, z0, z1, _, _ in corners), "corner beads")
    # every column carries a wall plate; each 2C run = two channels of the drawing's profile: 100 × 100 outside,
    # section area × 7850 = the TIS table's kg/m (geometry vs table, independent)
    tubes = [b for n, b in _solids([C_WALL]).items() if n[0].endswith("_2C")]
    for o in (o for o in bpy.data.collections[C_WALL].objects if o.name.endswith("_2C")):
        bm = _world_bm(o)
        (x0, y0, z0), (x1, y1, z1) = ([f(v.co[i] for v in bm.verts) for i in range(3)] for f in (min, max))
        L, w = max(x1 - x0, y1 - y0), min(x1 - x0, y1 - y0)
        assert abs(w - PLATE["b"]) < 1e-5 and abs(z1 - z0 - PLATE["h"]) < 1e-5, f"{o.name}: {w:.4f} × {z1 - z0:.4f}"
        kg = bm.calc_volume() / L * RHO / PLATE["pieces"]
        ax_ = 0 if x1 - x0 > y1 - y0 else 1   # the end faces are the section itself, hollow (a filled cap hid in the volume)
        end = sum(f.calc_area() for f in bm.faces if abs(f.normal[ax_]) > 0.99 and f.calc_center_median()[ax_] < (x0, y0)[ax_] + 1e-6)
        assert abs(end - PLATE["pieces"] * PLATE["c_kg_m"] / RHO) <= 0.01 * end, f"{o.name}: end face {end * 1e6:.0f} mm²"
        assert abs(kg - PLATE["c_kg_m"]) <= 0.01 * PLATE["c_kg_m"], f"{o.name}: profile {kg:.3f} kg/m per C, TIS {PLATE['c_kg_m']}"
        bm.free()
    for g in {g for gs in STUB_GRIDS.values() for g in gs}:
        x, y = _xy(g)
        assert any(b[0] <= x <= b[3] and b[1] <= y <= b[4] and abs(b[2] - WALL_TOP) < 1e-5 for b in tubes), \
            f"no wall plate over column {g}"
    boxes = _solids(STAGES)   # nothing overlaps anything in any stage
    clash = [(a, b) for a, b in itertools.combinations(boxes, 2)
             if (i := _inter(boxes[a], boxes[b])) and _vol(i) > 1e-6]
    assert not clash, f"solids overlap: {clash[:3]}"
    return f"walls ok: {len(lay)} wall lines · {len(corners)} corner beads · {len(tubes)} wall-plate runs"


def _solids_named(obj_name):
    o = bpy.data.objects.get(obj_name)
    if not o:
        return []
    bm = _world_bm(o)
    bs = _obj_boxes(bm, o.name)
    bm.free()
    return bs
