"""E42 ST11 ปูกระเบื้อง (spec 29 ต.ค.), after coat 1 of the paint, in the order it is built:
  1. RC steps: front (porch → garden) and back (kitchen door → garden), 3 risers of 13.3 cm, treads 30 cm, the back
     one with a 60 cm landing at +0.40; on 5 cm sand, wire mesh 4 mm @ 0.20.
  2. Bath waterproofing จระเข้ เฟล็กซ์ ชิลด์ 2 coats: the whole floor, the walls 30 cm up, 1.80 m in the shower;
     fibreglass mesh 20 cm along every wall–floor and wall–wall corner it covers.
  3. Screed (ปรับระดับ) from the slab to under the adhesive: slab 7 cm + 3 cm = finished floor.
  4. Tiles on จระเข้ฟ้า adhesive, จระเข้เงิน grout: granite 60 × 60 in the rooms (one grid through the doors),
     30 × 30 R11 on the bath floor, 30 × 60 on the bath walls to the ceiling and 90 cm over the kitchen counter,
     dark R11 60 × 60 on the porch and the steps; aluminium nosing with rubber inserts on every step edge.
  5. WPC skirting CROBERN 10 × 200 × 0.8 white round the rooms (not the bath, not behind the counter).
Tiles are counted off the layout (every cell a tile touches is one tile, a cut piece too) + 3 % for breakage,
then whole boxes; the plain area × 1.10 rule is printed beside it for comparison.

    exec(<e42_struct>) … exec(<e42_paint>); exec(<this>); build_steps(); build_tiles(); print(selfcheck_tiles())
"""
import math
import bmesh
from mathutils import Vector

C_STEP, C_TILE = "E42 ST11 Steps", "E42 ST11 Tiles"
FL_HOUSE, FL_PORCH = 0.45, 0.40
# size (along u, along v, thickness), joint, adhesive bed, pieces a box. Joints: COTTO ≥ 2 mm for rectified granite,
# 3 mm outside. Thicknesses: COTTO pages (granite 9.5–10 mm, 30 × 30 R11 8 mm); wall tile 8 mm (assumed).
FT = dict(
    floor=dict(size=(0.60, 0.60, 0.0095), joint=0.002, bed=0.005, box=4,
               th="กระเบื้องแกรนิตโต้ 60 × 60 ซม. (พื้นห้องนอน นั่งเล่น ครัว)", rgb=(0.86, 0.84, 0.80)),
    bath=dict(size=(0.30, 0.30, 0.008), joint=0.002, bed=0.005, box=11,
              th="กระเบื้องแกรนิตโต้กันลื่น R11 30 × 30 ซม. (พื้นห้องน้ำ)", rgb=(0.55, 0.55, 0.53)),
    wall=dict(size=(0.60, 0.30, 0.008), joint=0.002, bed=0.004, box=8,
              th="กระเบื้องบุผนัง 30 × 60 ซม. วางนอน (ผนังห้องน้ำถึงฝ้า + กันเปื้อนครัว)", rgb=(0.93, 0.93, 0.92)),
    porch=dict(size=(0.60, 0.60, 0.0097), joint=0.003, bed=0.005, box=4,
               th="กระเบื้องแกรนิตโต้ภายนอกสีเข้ม กันลื่น R11 60 × 60 ซม. (เฉลียง + บันได)", rgb=(0.22, 0.22, 0.23)))
SPARE = 0.03     # breakage on top of the layout count (WDC: 3–5 % over rounding up the boxes)
ADH = dict(th="ปูนกาวซีเมนต์ จระเข้ฟ้า 20 กก.", big=2.5, small=5.5)   # m² a bag: 10×10 notch (tile ≥ 40 cm) / 6×6
GROUT = dict(th="ยาแนว จระเข้เงิน 1 กก.", rho=1.6, waste=0.10)       # kg/m² = (L+W)/(LW)·j·t·ρ (mm), 10 % assumed
WP = dict(th="กันซึมชนิดยืดหยุ่น จระเข้ เฟล็กซ์ ชิลด์ 20 กก. 2 เที่ยว", t=0.0015, kg=1.5, bag=20.0, up=0.30, shower=1.80,
          mesh="ไฟเบอร์เมช จระเข้ 8×8 กว้าง 20 ซม. ม้วน 10 ม. (มุมผนัง–พื้น, มุมผนัง)", roll=10.0)
SHOWER = (2.10, 3.10)   # bath x range of the shower zone (assumed: between the vanity and the door wall; ask the user)
SCREED = dict(th="ปรับระดับพื้นก่อนปูกระเบื้อง ปูนทราย 1:3")
SKIRT = dict(h=0.10, t=0.008, stock=2.0, th="บัวพื้น WPC CROBERN 10 × 200 × 0.8 ซม. สีขาว (ติดกาวตะปู)")
NOSE = dict(w=0.050, h=0.025, t=0.003, stock=6.0, th="จมูกบันไดอะลูมิเนียม ยางกันลื่น 3 แถว 50 × 25 มม. ยาว 6 ม.")
KITCHEN = dict(x1=5.20, top=0.85, splash=0.90)   # counter along the rear wall from the living room's side wall
_d1_clear = tuple(c + sg * WALL["pl"] for c, sg in zip(next(o for o in OPENINGS if o[0] == "D1_Porch")[2:4], (1, -1)))   # its plaster clear
STEPS = dict(rise=3, base=-0.10, sand=0.05,
             front=dict(edge=("y", GY["A"] - 0.10, -1), span=_d1_clear, treads=(0.0, 0.30, 0.30)),   # (as wide as D1, ST14)
             back=dict(edge=("x", GX["3"] + 0.10, 1), span=(5.60, 6.70), treads=(0.60, 0.30, 0.30)))
assert STEPS["back"]["span"][0] < next(o for o in OPENINGS if o[0] == "D3_Kitchen")[2] and \
    next(o for o in OPENINGS if o[0] == "D3_Kitchen")[3] < STEPS["back"]["span"][1], "the back steps narrower than D3"   # (a landing wider than the door)


def _put(c, name, boxes, m, **props):
    """Disjoint boxes (x0, y0, z0, x1, y1, z1) as one object carrying take-off props."""
    o = bpy.data.objects.new(name, _boxes_data(name, boxes, m, **props))
    c.objects.link(o)
    return o


def _cell_pieces(region, cut, o, a, b, jw):
    """2D layout: cells (i, j) of a × b tiles laid from origin o with joints jw → [pieces (u0, v0, u1, v1)], each
    cell clipped to the region rects less the cut boxes (columns)."""
    u0, v0 = min(r[0] for r in region), min(r[1] for r in region)
    u1, v1 = max(r[2] for r in region), max(r[3] for r in region)
    pa, pb = a + jw, b + jw
    cells = {}
    for i in range(math.floor((u0 - o[0]) / pa) - 1, math.ceil((u1 - o[0]) / pa) + 1):
        for j in range(math.floor((v0 - o[1]) / pb) - 1, math.ceil((v1 - o[1]) / pb) + 1):
            cr = (o[0] + i * pa, o[1] + j * pb, o[0] + i * pa + a, o[1] + j * pb + b)
            for r in region:
                q = (max(cr[0], r[0]), max(cr[1], r[1]), min(cr[2], r[2]), min(cr[3], r[3]))
                if q[2] - q[0] > 1e-5 and q[3] - q[1] > 1e-5:
                    cells.setdefault((i, j), []).extend(_minus(q, cut))
    return {k: v for k, v in cells.items() if v}


def _count(cells, a, b):
    """(whole, tiles for the cuts) of a layout: a cell covered to its full size is whole; a cut piece takes a tile,
    two pieces of ≤ 45 % each come out of one (the offcut used again)."""
    areas = [sum((p[2] - p[0]) * (p[3] - p[1]) for p in ps) for ps in cells.values()]
    whole = sum(1 for x in areas if abs(x - a * b) < 1e-6)
    small = sum(1 for x in areas if x <= 0.45 * a * b + 1e-9)
    return whole, len(areas) - whole - small + math.ceil(small / 2)


def _origin(lo, hi, a, jw):
    """Grid start along one axis so the room [lo, hi] has equal cuts at both ends, a joint or a tile on the centre,
    whichever leaves the bigger cut."""
    best = None
    for mid_joint in (True, False):
        c = (lo + hi) / 2
        o = c + jw / 2 if mid_joint else c - a / 2
        k = math.floor((o - lo) / (a + jw)) + 1
        o0 = o - k * (a + jw)
        edge = (o0 + a + jw) - lo   # the cut at lo
        edge = edge if edge > 1e-6 else edge + a + jw
        if best is None or edge > best[0]:
            best = (edge, o0)
    return best[1]


def _floor_faces(cells, z_top, t):
    return [(p[0], p[1], z_top - t, p[2], p[3], z_top) for ps in cells.values() for p in ps]


def _joints_plan(region, cut, o, a, b, jw):
    """The joint strips of a floor layout, inside the region less the cut."""
    out = []
    u0, v0 = min(r[0] for r in region), min(r[1] for r in region)
    u1, v1 = max(r[2] for r in region), max(r[3] for r in region)
    for ax, (lo, hi, oo, p) in enumerate(((u0, u1, o[0], a + jw), (v0, v1, o[1], b + jw))):
        k = math.floor((lo - oo) / p)
        while oo + k * p - jw < hi:
            g0 = oo + k * p - jw
            for r in region:
                s = (max(g0, r[0]), r[1], min(g0 + jw, r[2]), r[3]) if ax == 0 else \
                    (r[0], max(g0, r[1]), r[2], min(g0 + jw, r[3]))
                if s[2] - s[0] > 1e-6 and s[3] - s[1] > 1e-6:
                    out += _minus(s, cut)
            k += 1
    # crossings: keep each joint square once (the along-y strips give way)
    xs = [s for s in out if s[2] - s[0] <= jw + 1e-9]
    ys = [s for s in out if s[2] - s[0] > jw + 1e-9]
    return xs + [q for s in ys for q in _minus(s, [(x[0], x[1], 0, x[2], x[3], 0) for x in xs])]


def _grout_kg(area, a, b, jw, t):
    """Jorakay/Mapei rule: kg = A × (L+W)/(L·W) × joint × depth × ρ, sizes in mm."""
    L, W = a * 1000, b * 1000
    return area * (L + W) / (L * W) * jw * 1000 * t * 1000 * GROUT["rho"]


def _merged(boxes):
    """Touching plan boxes (a column, its plaster rim and the bead slivers) as one box each: a column cut is one
    rectangle, not a dozen 1 mm faces."""
    out = [list(b) for b in boxes]
    merged = True
    while merged:
        merged = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                if a[0] <= b[3] + 1e-4 and b[0] <= a[3] + 1e-4 and a[1] <= b[4] + 1e-4 and b[1] <= a[4] + 1e-4:
                    out[i] = [min(a[k], b[k]) for k in range(3)] + [max(a[k], b[k]) for k in range(3, 6)]
                    del out[j]
                    merged = True
                    break
            if merged:
                break
    return [tuple(b) for b in out]


def _rooms_floor():
    """{room: (plaster-face rect, columns cut, finished floor)} read from the walls."""
    out = {}
    for room, (seed, kind) in ROOMS.items():
        rc = _room_rect(seed, 2.6)
        cut = [(max(b[0], rc[0]), max(b[1], rc[1]), b[2], min(b[3], rc[2]), min(b[4], rc[3]), b[5]) for b in _merged(_intruders(rc, 1.0))]
        out[room] = (rc, cut, FL_BATH if kind == "mr" else FL_HOUSE)
    return out


def _doors():
    """Every door on the slab: (name, wall line dict, plastered opening along (a, b), head under the plaster)."""
    L, p_ = _wlines(WALL_LINES, OFFSET), WALL["pl"]
    return [(n, L[ln], c0 + p_, c1 - p_, z1 - p_)
            for n, ln, c0, c1, z0, z1 in OPENINGS if n.startswith("D") and abs(z0 - WALL_BASE) < 1e-9]


def _wall_build():
    return FT["wall"]["bed"] + FT["wall"]["size"][2]


def _thresholds(rooms):
    """Plan rects of the house floor through each door: wall face to wall face; into the bath it reaches over the
    wall tiles on the riser; onto the porch / back landing it stops at the slab edge (the riser tile goes in front)."""
    out, half = [], WALL["t"] / 2 + WALL["pl"]
    bx = rooms["Bath"][0]
    for n, l, a, b, _ in _doors():
        ax, k = l["ax"], l["k"]
        lo, hi = k - half, k + half
        if n.startswith("D4"):
            lo = bx[2] - _wall_build()
        elif n.startswith("D1"):
            lo = GY["B"] - 0.10       # house slab edge (B2-B3 beam face)
        elif n.startswith("D3"):
            hi = GX["3"] + 0.10
        out.append((n, (a, lo, b, hi) if ax == 0 else (lo, a, hi, b)))
    return out


def _wall_pieces(P, d, n, L, z0, z1, holes, size, jw, s0):
    """Wall tiles on a face from plan point P along unit d for L, z0 → z1, less the holes (u0, v0, u1, v1),
    s0 out from the plaster along n (the bed), laid from the face's start and the bottom: (cells, boxes)."""
    a, b, t = size
    cells = _cell_pieces([(0.0, z0, L, z1)], [(h[0], h[1], 0, h[2], h[3], 0) for h in holes], (0.0, z0), a, b, jw)
    boxes = []
    for ps in cells.values():
        for u_0, v_0, u_1, v_1 in ps:
            p0, p1 = P + d * u_0 + n * s0, P + d * u_1 + n * (s0 + t)
            boxes.append((min(p0.x, p1.x), min(p0.y, p1.y), v_0, max(p0.x, p1.x), max(p0.y, p1.y), v_1))
    return cells, boxes


def tiled_wall_boxes():
    """Where plaster is tiled over instead of painted (the paint stage skips these): the kitchen splash band, with
    the window reveals in it. The bath is tiled to the ceiling all round (paint skips the room)."""
    rc = _room_rect(ROOMS["Living"][0], 2.6)
    z0 = FL_HOUSE + KITCHEN["top"]
    return [(rc[0] - 1e-3, rc[3] - 1e-3, z0, KITCHEN["x1"], rc[3] + WALL["t"] / 2 + WALL["pl"], z0 + KITCHEN["splash"])]   # to the wall's centre


def build_steps():
    """RC steps on sand, against the beam faces; their take-off and the landing / tread levels for the tiles."""
    c = _clear(C_STEP)
    conc = bpy.data.materials.get("rough_concrete_material_Str_Footings") or mat("M_Concrete", (0.50, 0.50, 0.48), 0.85)
    sand = mat("M_Sand", (0.76, 0.68, 0.52), 0.95)
    steel = mat("M_Rebar", (0.28, 0.17, 0.11), 0.55, 0.6)
    eps = FT["porch"]["size"][2] + FT["porch"]["bed"]
    out = {}
    for nm in ("front", "back"):
        s = STEPS[nm]
        ax, E, sg = s["edge"]
        a0, a1 = s["span"]
        r = FL_PORCH / STEPS["rise"]
        noses = [sum(s["treads"][:i + 1]) + eps for i in range(len(s["treads"]))]
        tops = [FL_PORCH - i * r for i in range(len(s["treads"]))]
        P = lambda d0, d1, z0, z1: (tuple(sorted((E + sg * d0, E + sg * d1))) if ax == "x" else (a0, a1),
                                    (a0, a1) if ax == "x" else tuple(sorted((E + sg * d0, E + sg * d1))), (z0, z1))
        boxes = []
        for i, (Nn, h) in enumerate(zip(noses, tops)):
            if s["treads"][i] == 0.0:   # the porch itself is the top tread
                continue
            zb = STEPS["base"] if i == len(noses) - 1 else tops[i + 1] - eps
            (x0, x1), (y0, y1), (z0, z1) = P(0.0, Nn - eps, zb, h - eps)
            boxes.append((x0, y0, z0, x1, y1, z1))
        (x0, x1), (y0, y1), (z0, z1) = P(0.0, noses[-1] - eps, STEPS["base"] - STEPS["sand"], STEPS["base"])
        loc = (x0, y0, 0.0)
        rel = lambda b: tuple(b[i] - loc[i % 3] for i in range(6))
        D = {"Conc": _boxes_data(f"ST_{nm}_Conc", [rel(b) for b in boxes], conc, element="concrete", type="ST1",
                                 th="คอนกรีตบันได ค.ส.ล. (เทบนทรายอัดแน่น)", grade=SLAB["grade"]),
             "Sand": _boxes_data(f"ST_{nm}_Sand", [rel((x0, y0, z0, x1, y1, z1))], sand, element="sand", type="ST1",
                                 th=f"ทรายหยาบอัดแน่นรองบันได {STEPS['sand'] * 100:.0f} ซม."),
             "Exc": _boxes_data(f"ST_{nm}_Exc", [rel((x0, y0, z0, x1, y1, GL))], None, element="excavation", type="ST1",
                                th="ขุดดินบันได"),
             "Mesh": _rebar_data(f"ST_{nm}_Mesh", [[tuple(p[i] - loc[i] for i in range(3)) for p in w]
                                                   for w in _mesh_wires([(x0, y0, x1, y1)], STEPS["base"] + SLAB["mz"], SLAB)],
                                 SLAB["md"], steel, element="mesh", type="ST1", th="ไวร์เมชบันได", bar=SLAB["mesh"],
                                 dia_mm=round(SLAB["md"] * 1000), spacing=SLAB["ms"], area=(x1 - x0) * (y1 - y0))}
        root = bpy.data.objects.new(f"ST_{nm}", None)
        root.location = loc
        c.objects.link(root)
        for key, data in D.items():
            ob = bpy.data.objects.new(f"ST_{nm}_{key}", data)
            ob.parent = root
            c.objects.link(ob)
            if key == "Exc":
                ob.hide_viewport = ob.hide_render = True
        out[nm] = dict(noses=noses, tops=tops, rise=r)
    return out


def _step_geom():
    """Per flight: plan mapper, its noses (finished riser planes, from the edge), tread tops, rise."""
    eps = FT["porch"]["size"][2] + FT["porch"]["bed"]
    out = {}
    for nm in ("front", "back"):
        s = STEPS[nm]
        ax, E, sg = s["edge"]
        noses = [sum(s["treads"][:i + 1]) + eps for i in range(len(s["treads"]))]
        tops = [FL_PORCH - i * FL_PORCH / STEPS["rise"] for i in range(len(s["treads"]))]
        def box(d0, d1, z0, z1, ax=ax, E=E, sg=sg, s=s):
            p, q = sorted((E + sg * d0, E + sg * d1))
            a0, a1 = s["span"]
            return (p, a0, z0, q, a1, z1) if ax == "x" else (a0, p, z0, a1, q, z1)
        out[nm] = dict(box=box, noses=noses, tops=tops, treads=s["treads"], span=s["span"], ax=ax, sg=sg, E=E)
    return out


def build_tiles():
    """Waterproofing, screed, adhesive, tiles + grout, nosing, skirting; one take-off row each."""
    c = _clear(C_TILE)
    rooms = _rooms_floor()
    mats = {k: mat(f"M_Tile_{k}", v["rgb"], 0.25 if k != "porch" else 0.6) for k, v in FT.items()}
    grout_m = mat("M_Grout", (0.70, 0.70, 0.68), 0.8)
    adh_m = mat("M_TileAdhesive", (0.62, 0.62, 0.60), 0.9)
    scr_m = mat("M_Screed", (0.55, 0.54, 0.50), 0.95)
    wp_m = mat("M_Waterproof", (0.30, 0.45, 0.62), 0.7)
    wpc = mat("M_WPC_White", (0.95, 0.95, 0.94), 0.4)
    alu = mat("M_Alu", (0.80, 0.81, 0.83), 0.3, 0.9)
    rub = mat("M_Rubber", (0.04, 0.04, 0.04), 0.9)
    wb = _wall_build()
    res = {}
    # --- floors: house (rooms + thresholds, one grid), bath, porch
    house = [rooms[r][0] for r in ("Bed2", "Bed1", "Living")] + [r for _, r in _thresholds(rooms)]
    hcut = [b for r in ("Bed2", "Bed1", "Living") for b in rooms[r][1]]
    lv = rooms["Living"][0]
    bxr, bcut, _ = rooms["Bath"]
    bath = [(bxr[0] + wb, bxr[1] + wb, bxr[2] - wb, bxr[3] - wb)]
    bcut = [(b[0] - wb, b[1] - wb, b[2], b[3] + wb, b[4] + wb, b[5]) for b in bcut]
    g = _step_geom()
    fr = g["front"]
    x_out = lv[0]   # porch: from the A2-E2 wall's porch-side plaster face (the wall is flush to +x)
    nose_in = fr["E"] + fr["sg"] * (fr["noses"][0] - NOSE["w"])   # the porch tile stops at the nosing
    porch = [(x_out, GY["A"] - 0.10, GX["3"] + 0.10, GY["B"] - 0.10)]
    pcut = _merged(_intruders(porch[0], 1.0))   # the porch column
    porch = _minus(porch[0], [(fr["span"][0], GY["A"] - 0.10, 0, fr["span"][1], nose_in, 0)])   # nosing on the top edge
    d1 = next(r for n, r in _thresholds(rooms) if n.startswith("D1"))
    porch = [q for r in porch for q in _minus(r, [(d1[0], d1[1] - FT["porch"]["size"][2] - FT["porch"]["bed"], 0,
                                                   d1[2], d1[1], 0)])]   # riser tile in front of the door edge
    floors = dict(
        floor=(house, hcut, FL_HOUSE, (_origin(lv[0], lv[2], 0.60, FT["floor"]["joint"]), lv[1])),
        bath=(bath, bcut, FL_BATH, (bath[0][2] + FT["bath"]["joint"],
                                   _origin(bath[0][1], bath[0][3], 0.30, FT["bath"]["joint"]))),
        porch=(porch, pcut, FL_PORCH, (_origin(d1[0], d1[2], 0.60, FT["porch"]["joint"]), nose_in)))
    tally = {k: dict(area=0.0, whole=0, cut=0, strips=0) for k in FT}
    for k, (region, cut, fl, o) in floors.items():
        a, b, t = FT[k]["size"]
        jw, bed = FT[k]["joint"], FT[k]["bed"]
        cells = _cell_pieces(region, cut, o, a, b, jw)
        w_, c_ = _count(cells, a, b)
        boxes = _floor_faces(cells, fl, t)
        area = sum((p[3] - p[0]) * (p[4] - p[1]) for p in boxes)
        tally[k].update(area=tally[k]["area"] + area, whole=tally[k]["whole"] + w_, cut=tally[k]["cut"] + c_)
        _put(c, f"FT_{k}_Tiles", boxes, mats[k], fl=fl, origin=list(o), area=area)
        gb = [(s[0], s[1], fl - t, s[2], s[3], fl - 0.0005) for s in _joints_plan(region, cut, o, a, b, jw)]
        _put(c, f"FT_{k}_Grout", gb, grout_m)
        net = [q for r in region for q in _minus(r, cut)]
        _put(c, f"FT_{k}_Bed", [(q[0], q[1], fl - t - bed, q[2], q[3], fl - t) for q in net], adh_m)
        sc = []
        for q in net:   # screed: slab top → under the bed, over this floor's own slab (not over the bath's riser)
            for zr, ztop in _zones().values():
                top = ztop + SLAB["t"]
                for r in zr:
                    i = (max(q[0], r[0]), max(q[1], r[1]), min(q[2], r[2]), min(q[3], r[3]))
                    if i[2] - i[0] > 1e-6 and i[3] - i[1] > 1e-6 and 0 < fl - top < 0.04:
                        sc.append((i[0], i[1], top + (WP["t"] if k == "bath" else 0.0), i[2], i[3], fl - t - bed))
        res[f"screed_{k}"] = sc
    # --- bath waterproofing (floor + walls) and wall tiles; kitchen splash
    zc = FL_BATH + CEIL["h_bath"]
    bslab = ZONES["Bath"][1] + SLAB["t"]
    wp_boxes, wt_boxes, mesh_len = [], [], 0.0
    wp_boxes += [(q[0], q[1], bslab, q[2], q[3], bslab + WP["t"]) for q in _minus(bxr, rooms["Bath"][1])]
    doors = _doors()
    corners = set()
    wcells = 0
    faces = _outline(bxr, rooms["Bath"][1])
    def ends(p, q, d):
        """Tile run along a face at its corners: faces along x run through an inside corner and out over a convex
        one (by the wall build); faces along y stop short of an inside corner."""
        u0, u1 = 0.0, (Vector((*q, 0)) - Vector((*p, 0))).length
        for E, t, k in ((p, d, 0), (q, -d, 1)):
            for p2, q2, inn2 in faces:
                if (p2, q2) == (p, q) or not (math.dist(E, p2) < 1e-4 or math.dist(E, q2) < 1e-4):
                    continue
                c = Vector((*inn2, 0)).dot(t)
                if c > 0.5 and abs(d.y) > 0.5:
                    u0, u1 = (u0 + wb, u1) if k == 0 else (u0, u1 - wb)
                elif c < -0.5 and abs(d.x) > 0.5:
                    u0, u1 = (u0 - wb, u1) if k == 0 else (u0, u1 + wb)
        return u0, u1
    for p, q, inn in faces:
        P, Q, n = Vector((*p, 0)), Vector((*q, 0)), Vector((*inn, 0))
        d, L = (Q - P).normalized(), (Q - P).length
        corners |= {(round(p[0], 4), round(p[1], 4)), (round(q[0], 4), round(q[1], 4))}
        mesh_len += L
        holes = []
        for nm, l, a, b, head in doors:   # a door in this face: its plastered opening above the house floor's bed
            ax = l["ax"]
            if abs(p[1 - ax] - q[1 - ax]) < 1e-9 and abs(p[1 - ax] - l["k"]) < WALL["t"] / 2 + WALL["pl"] + 1e-3:
                ua, ub = sorted(((Vector((*([a, p[1]] if ax == 0 else [p[0], a]), 0)) - P).dot(d),
                                 (Vector((*([b, p[1]] if ax == 0 else [p[0], b]), 0)) - P).dot(d)))
                holes.append((ua, FL_HOUSE - FT["floor"]["size"][2] - FT["floor"]["bed"], ub, head))
        for wn, ln, c0, c1, z0, z1 in OPENINGS:   # windows: plastered opening
            l = _wlines(WALL_LINES, OFFSET)[ln]
            ax = l["ax"]
            if wn.startswith("W") and abs(p[1 - ax] - q[1 - ax]) < 1e-9 and abs(p[1 - ax] - l["k"]) < 0.06:
                a, b = c0 + WALL["pl"], c1 - WALL["pl"]
                ua, ub = sorted(((Vector((*([a, p[1]] if ax == 0 else [p[0], a]), 0)) - P).dot(d),
                                 (Vector((*([b, p[1]] if ax == 0 else [p[0], b]), 0)) - P).dot(d)))
                if ub > 0 and ua < L:
                    holes.append((ua, z0 + WALL["pl"], ub, z1 - WALL["pl"]))
        u0, u1 = ends(p, q, d)
        cells, boxes = _wall_pieces(P + d * u0, d, n, u1 - u0, FL_BATH - FT["bath"]["size"][2] - FT["bath"]["bed"], zc,
                                    [(h[0] - u0, h[1], h[2] - u0, h[3]) for h in holes],
                                    FT["wall"]["size"], FT["wall"]["joint"], FT["wall"]["bed"])
        w_, c_ = _count(cells, 0.60, 0.30)
        tally["wall"]["whole"] += w_
        tally["wall"]["cut"] += c_
        tally["wall"]["area"] += sum(max(b[3] - b[0], b[4] - b[1]) * (b[5] - b[2]) for b in boxes)
        wt_boxes += boxes
        # waterproofing up the wall: 30 cm, 1.80 m where the face is in the shower's x range
        if abs(d.x) > 0.5:   # a face along x: split at the shower's ends
            xs = sorted({min(max(x, min(P.x, Q.x)), max(P.x, Q.x)) for x in (P.x, Q.x, *SHOWER)})
            segs = [(min((xa - P.x) / d.x, (xb - P.x) / d.x), max((xa - P.x) / d.x, (xb - P.x) / d.x),
                     WP["shower"] if SHOWER[0] <= (xa + xb) / 2 <= SHOWER[1] else WP["up"]) for xa, xb in zip(xs, xs[1:])]
        else:
            segs = [(0.0, L, WP["shower"] if SHOWER[0] <= P.x <= SHOWER[1] else WP["up"])]
        for ua_, ub_, h in segs:
            for u0_, v0_, u1_, v1_ in _minus((ua_, bslab + WP["t"], ub_, FL_BATH + h), [(hh[0], hh[1], 0, hh[2], hh[3], 0) for hh in holes]):
                p0, p1 = P + d * u0_, P + d * u1_ + n * WP["t"]
                wp_boxes.append((min(p0.x, p1.x), min(p0.y, p1.y), v0_, max(p0.x, p1.x), max(p0.y, p1.y), v1_))
    in_shower = lambda x: SHOWER[0] - 1e-6 <= x <= SHOWER[1] + 1e-6
    mesh_len += sum(WP["shower"] if in_shower(x) else WP["up"] for x, y in corners)
    _put(c, "FT_Bath_Waterproof", wp_boxes, wp_m, element="membrane", type="WP1", th=WP["th"],
         area=sum((b[3] - b[0]) * (b[4] - b[1]) if b[5] - b[2] < 0.01 else max(b[3] - b[0], b[4] - b[1]) * (b[5] - b[2])
                  for b in wp_boxes), kg_m2=WP["kg"], bag=WP["bag"])
    _put(c, "FT_Bath_WPMesh", [], wp_m, element="joint", type="WP2", th=WP["mesh"], length=mesh_len, roll=WP["roll"])
    # kitchen splash on the living room's rear face, from its side wall to the counter end
    z0 = FL_HOUSE + KITCHEN["top"]
    P, d, n = Vector((lv[0], lv[3], 0)), Vector((1, 0, 0)), Vector((0, -1, 0))
    holes = []
    for wn, ln, c0, c1, wz0, wz1 in OPENINGS:
        l = _wlines(WALL_LINES, OFFSET)[ln]
        if wn.startswith("W") and l["ax"] == 0 and abs(l["k"] - lv[3]) < 0.06:
            holes.append((c0 + WALL["pl"] - lv[0], wz0 + WALL["pl"], c1 - WALL["pl"] - lv[0], wz1 - WALL["pl"]))
    cells, boxes = _wall_pieces(P, d, n, KITCHEN["x1"] - lv[0], z0, z0 + KITCHEN["splash"], holes,
                                FT["wall"]["size"], FT["wall"]["joint"], FT["wall"]["bed"])
    w_, c_ = _count(cells, 0.60, 0.30)
    tally["wall"]["whole"] += w_
    tally["wall"]["cut"] += c_
    tally["wall"]["area"] += sum((b[3] - b[0]) * (b[5] - b[2]) for b in boxes)
    wt_boxes += boxes
    # window reveals inside the tiled height: jambs, sill (and head) to the wall's centre line, strips cut from tiles
    rev, rev_len = [], []
    for wn, ln, c0, c1, wz0, wz1 in OPENINGS:
        l = _wlines(WALL_LINES, OFFSET)[ln]
        ax = l["ax"]
        a, b = c0 + WALL["pl"], c1 - WALL["pl"]
        za, zb = wz0 + WALL["pl"], wz1 - WALL["pl"]
        for face, lo_z, hi_z in ((bxr, FL_BATH, zc), (lv, z0, z0 + KITCHEN["splash"])):
            fk = (face[1], face[3]) if ax == 0 else (face[0], face[2])
            side = next((f for f in fk if abs(f - l["k"]) < 0.06), None)
            inside = (face[0] - 1e-3 <= a and b <= face[2] + 1e-3) if ax == 0 else (face[1] - 1e-3 <= a and b <= face[3] + 1e-3)
            if face is lv and not (ax == 0 and side == lv[3] and b <= KITCHEN["x1"] + 1e-3):   # the splash: rear wall only
                continue
            if not wn.startswith("W") or side is None or not inside or zb <= lo_z or za >= hi_z:
                continue
            if wn[:2] in UNIT and UNIT_DEPTH >= WALL["t"] + 2 * WALL["pl"]:   # (ST14) the frame fills it: tiles stop at it
                continue
            s0, s1 = sorted((side, l["k"]))
            t_ = FT["wall"]["size"][2]
            z_lo, z_hi = max(za, lo_z), min(zb, hi_z)
            for u in (a, b):   # jambs
                du = t_ if u == a else -t_
                u0_, u1_ = sorted((u, u + du))
                rev.append((u0_, s0, z_lo, u1_, s1, z_hi) if ax == 0 else (s0, u0_, z_lo, s1, u1_, z_hi))
                rev_len.append(z_hi - z_lo)
            if za >= lo_z:   # sill
                rev.append((a + t_, s0, za, b - t_, s1, za + t_) if ax == 0 else (s0, a + t_, za, s1, b - t_, za + t_))
                rev_len.append(b - a)
            if zb <= hi_z:   # head
                rev.append((a + t_, s0, zb - t_, b - t_, s1, zb) if ax == 0 else (s0, a + t_, zb - t_, s1, b - t_, zb))
                rev_len.append(b - a)
    depth = WALL["t"] / 2 + WALL["pl"]
    per_tile = math.floor(0.30 / (depth + FT["wall"]["joint"]))
    tally["wall"]["strips"] = math.ceil(sum(math.ceil(x / 0.60) for x in rev_len) / per_tile)
    tally["wall"]["area"] += sum(rev_len) * depth
    _put(c, "FT_wall_Tiles", wt_boxes + rev, mats["wall"])
    # --- steps: treads, risers (incl. the 5 cm door risers onto the porch and the back landing), nosing
    st_boxes, nose_b, rub_b, strips, nose_len = [], [], [], [], []
    a_, b_, t = FT["porch"]["size"]
    eps = t + FT["porch"]["bed"]
    bm_n = bmesh.new()
    for nm in ("front", "back"):
        G = g[nm]
        for i, (Nn, h) in enumerate(zip(G["noses"], G["tops"])):
            nxt = G["tops"][i + 1] if i + 1 < len(G["tops"]) else GL
            back = 0.0 if i == 0 else G["noses"][i - 1] - eps
            if G["treads"][i] > 0:
                st_boxes.append(G["box"](back, Nn - NOSE["w"], h - t, h))
                strips.append((Nn - NOSE["w"] - back, G["span"][1] - G["span"][0]))
            st_boxes.append(G["box"](Nn - t, Nn, nxt, h - NOSE["h"]))   # riser tile under the nosing
            strips.append((h - NOSE["h"] - nxt, G["span"][1] - G["span"][0]))
            nose_len.append(G["span"][1] - G["span"][0])
            ax, sg, E = G["ax"], G["sg"], G["E"]
            sec = strip([(-NOSE["w"], -NOSE["t"] / 2), (-NOSE["t"] / 2, -NOSE["t"] / 2), (-NOSE["t"] / 2, -NOSE["h"])], NOSE["t"])
            def place(u, s, z, Nn=Nn, h=h, ax=ax, sg=sg, E=E):
                dd = E + sg * (Nn + s)
                return (dd, u, h + z) if ax == "x" else (u, dd, h + z)
            prism(bm_n, sec, G["span"][0], G["span"][1], place)
            for k in range(3):   # rubber inserts flush in the top
                s0 = -NOSE["w"] + 0.008 + k * 0.014
                p_, q_ = sorted((E + sg * (Nn + s0), E + sg * (Nn + s0 + 0.006)))
                rub_b.append((p_, G["span"][0], h - 0.0015, q_, G["span"][1], h + 0.0002) if ax == "x" else
                             (G["span"][0], p_, h - 0.0015, G["span"][1], q_, h + 0.0002))
    for n_, r in _thresholds(rooms):   # 5 cm risers at the porch door and the kitchen door
        if n_.startswith("D1"):
            st_boxes.append((r[0], r[1] - t, FL_PORCH, r[2], r[1], FL_HOUSE - FT["floor"]["size"][2]))
            strips.append((FL_HOUSE - FL_PORCH, r[2] - r[0]))
        if n_.startswith("D3"):
            st_boxes.append((r[2], r[1], FL_PORCH, r[2] + t, r[3], FL_HOUSE - FT["floor"]["size"][2]))
            strips.append((FL_HOUSE - FL_PORCH, r[3] - r[1]))
    _put(c, "FT_porch_Steps", st_boxes, mats["porch"])
    tally["porch"]["area"] += sum(h * L for h, L in strips)
    tally["porch"]["strips"] = sum(math.ceil(math.ceil(L / a_) / max(1, math.floor(a_ / (h + FT["porch"]["joint"]))))
                                   for h, L in strips)
    me = bpy.data.meshes.new("FT_Nosing")
    bm_n.to_mesh(me)
    bm_n.free()
    me.materials.append(alu)
    on = bpy.data.objects.new("FT_Nosing", me)
    for kk, v in dict(element="trim", type="FN1", th=NOSE["th"], lens=nose_len, stock=NOSE["stock"], butt=True).items():
        me[kk] = v
    c.objects.link(on)
    _put(c, "FT_Nosing_Rubber", rub_b, rub)
    # --- screed, adhesive (whole floors + walls), grout, tile rows
    sc = [b for k in ("floor", "bath", "porch") for b in res[f"screed_{k}"]]
    _put(c, "FT_Screed", sc, scr_m, element="screed", type="SC1", th=SCREED["th"],
         area=sum((b[3] - b[0]) * (b[4] - b[1]) for b in sc))
    for k, v in FT.items():
        a, b, t = v["size"]
        x = tally[k]
        need = math.ceil((x["whole"] + x["cut"] + x["strips"]) * (1 + SPARE) - 1e-9)
        o = _put(c, f"FT_{k}_Qty", [], mats[k], element="floor_tile", type=f"FT_{k}", th=v["th"], area=x["area"],
                 whole=x["whole"], cut=x["cut"], strips=x["strips"], need=need, box=v["box"], sheet=a * b)
        o.hide_viewport = o.hide_render = True
        bags = x["area"] / (ADH["big"] if max(a, b) >= 0.40 else ADH["small"])
        o.data["adh_bags"] = bags
        o.data["grout_kg"] = _grout_kg(x["area"], a, b, v["joint"], t) * (1 + GROUT["waste"])
    # --- skirting round the rooms, less doors and the counter
    sk, lens = [], []
    for room in ("Bed2", "Bed1", "Living"):
        rc, cut, fl = rooms[room]
        for p, q, inn in _outline(rc, cut):
            ax = 0 if abs(p[1] - q[1]) < 1e-9 else 1
            lo, hi = sorted((p[ax], q[ax]))
            blocks = []
            for nm, l, a, b, _ in doors:
                if l["ax"] == ax and abs(p[1 - ax] - l["k"]) < WALL["t"] / 2 + WALL["pl"] + 1e-3:
                    blocks.append((a, b))
            if room == "Living" and ax == 0 and abs(p[1] - rc[3]) < 1e-6:
                blocks.append((rc[0] - 1, KITCHEN["x1"]))
            for u0_, u1_ in _runs(lo, hi, blocks, ax):
                lens.append(u1_ - u0_)
                P = Vector((*([u0_, p[1]] if ax == 0 else [p[0], u0_]), 0))
                I = Vector((*inn, 0))
                d = Vector((1, 0, 0)) if ax == 0 else Vector((0, 1, 0))
                sk.append((P, d, I, u1_ - u0_, fl))
    bm = bmesh.new()
    # section (s off the plaster, z up): back up the wall, front down with a rounded-off top (prism strip pairs)
    sec = [(0.0, 0.0), (0.0, 0.080), (0.0, SKIRT["h"]), (0.6 * SKIRT["t"], SKIRT["h"]), (SKIRT["t"], 0.080), (SKIRT["t"], 0.0)]
    for P, d, I, L, fl in sk:
        prism(bm, sec, 0.0, L, lambda u, s, z, P=P, d=d, I=I, fl=fl: tuple(P + d * u + I * s + Vector((0, 0, fl + z))))
    me = bpy.data.meshes.new("FT_Skirting")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(wpc)
    for kk, v in dict(element="trim", type="FS1", th=SKIRT["th"], lens=lens, stock=SKIRT["stock"], butt=True).items():
        me[kk] = v
    so = bpy.data.objects.new("FT_Skirting", me)
    c.objects.link(so)
    hid = bpy.data.objects.get("Kit_Splash")   # the old model's splash board: the tiles replace it
    if hid:
        hid.hide_viewport = hid.hide_render = True
    return {k: (round(v["area"], 2), v["whole"], v["cut"], v["strips"]) for k, v in tally.items()}


def _boxes_of(name):
    bm = _world_bm(bpy.data.objects[name])
    out = _obj_boxes(bm, name)
    bm.free()
    return out


def selfcheck_tiles():
    """ST11 against the user's spec, read back from the model: floor levels (bath 10 cm down, porch 5 cm), every floor
    filled by tiles + joints exactly (no gap, no overlap, joints the spec width), tiles no bigger than their size; bath
    walls bare nowhere from the floor to the ceiling, the splash 90 cm over the counter, nothing tiled elsewhere;
    waterproofing 30 cm / 1.80 m and behind the tiles; screed on the slab; steps equal risers with a nosing on each;
    skirting = room outlines − doors − counter; counts = layout + 3 %."""
    rooms = _rooms_floor()
    wb = _wall_build()
    lv, bxr = rooms["Living"][0], rooms["Bath"][0]
    assert abs(FL_HOUSE - (ZONES["House"][1] + SLAB["t"] + 0.03)) < 1e-6 and abs(FL_PORCH - (ZONES["Porch"][1] + SLAB["t"] + 0.03)) < 1e-6, \
        "finished floors ≠ slab + 3 cm"
    assert abs(FL_HOUSE - FL_BATH - 0.10) < 1e-6 and abs(FL_HOUSE - FL_PORCH - 0.05) < 1e-6, "floor levels (the user: bath −10 cm)"
    out = []
    for k, fl in (("floor", FL_HOUSE), ("bath", FL_BATH), ("porch", FL_PORCH)):
        a, b, t = FT[k]["size"]
        jw = FT[k]["joint"]
        tiles, grout = _boxes_of(f"FT_{k}_Tiles"), _boxes_of(f"FT_{k}_Grout")
        for x in tiles:
            assert abs(x[5] - fl) < 1e-5 and abs(x[5] - x[2] - t) < 1e-5, f"{k}: a tile off the floor level at {x[0]:.2f}, {x[1]:.2f}"
            assert x[3] - x[0] <= a + 1e-5 and x[4] - x[1] <= b + 1e-5, f"{k}: a piece bigger than a tile"
        for p_, q_ in ((p_, q_) for p_ in tiles for q_ in tiles if p_ < q_):   # no two tiles overlap
            assert min(p_[3], q_[3]) - max(p_[0], q_[0]) < 1e-6 or min(p_[4], q_[4]) - max(p_[1], q_[1]) < 1e-6, f"{k}: tiles overlap"
        # joints between neighbours are 0 (one tile split round a column) or the spec width
        xs = sorted(tiles)
        for p_ in xs:
            nb = [q_ for q_ in xs if 1e-6 < q_[0] - p_[3] < 0.01 and min(p_[4], q_[4]) - max(p_[1], q_[1]) > 0.01]
            assert all(abs(q_[0] - p_[3] - jw) < 1e-5 for q_ in nb), f"{k}: joint {min(q_[0] - p_[3] for q_ in nb) * 1000:.1f} mm, spec {jw * 1000:.0f}"
        got = sum((x[3] - x[0]) * (x[4] - x[1]) for x in tiles + grout)
        out.append((k, got))
    # the floors' net areas, measured independently: room rects − columns + door strips (house), bath inset, porch
    th = _thresholds(rooms)
    net_h = sum(_area([(q[0], q[1]), (q[2], q[1]), (q[2], q[3]), (q[0], q[3])]) for r in ("Bed2", "Bed1", "Living")
                for q in _minus(rooms[r][0], rooms[r][1])) + sum((r[2] - r[0]) * (r[3] - r[1]) for _, r in th)
    assert abs(out[0][1] - net_h) < 1e-4, f"house floor: tiles + joints {out[0][1]:.4f} m², rooms + doors {net_h:.4f}"
    net_b = (bxr[2] - bxr[0] - 2 * wb) * (bxr[3] - bxr[1] - 2 * wb) - sum(
        (min(c[3] + wb, bxr[2] - wb) - max(c[0] - wb, bxr[0] + wb)) * (min(c[4] + wb, bxr[3] - wb) - max(c[1] - wb, bxr[1] + wb))
        for c in rooms["Bath"][1])
    assert abs(out[1][1] - net_b) < 1e-4, f"bath floor: tiles + joints {out[1][1]:.4f} m², room {net_b:.4f}"
    # porch, by hand: slab rect − the column − the nosing strip along the steps − the door riser
    eps = FT["porch"]["size"][2] + FT["porch"]["bed"]
    pr = (lv[0], GY["A"] - 0.10, GX["3"] + 0.10, GY["B"] - 0.10)
    col = sum((min(c[3], pr[2]) - max(c[0], pr[0])) * (min(c[4], pr[3]) - max(c[1], pr[1])) for c in _merged(_intruders(pr, 1.0)))
    sp = STEPS["front"]["span"]
    d1 = next(r for n_, r in th if n_.startswith("D1"))
    net_p = (pr[2] - pr[0]) * (pr[3] - pr[1]) - col - (sp[1] - sp[0]) * (NOSE["w"] - eps) - (d1[2] - d1[0]) * eps
    assert abs(out[2][1] - net_p) < 1e-4, f"porch: tiles + joints {out[2][1]:.4f} m², slab − column − nosing − riser {net_p:.4f}"
    # the thresholds end where the next finish starts: over the bath's riser tiles, at the porch / landing slab edges
    ft = _boxes_of("FT_floor_Tiles")
    for n_, l, a, b, _ in _doors():
        ax = l["ax"]
        mine = [x for x in ft if (a + 1e-3 < (x[0] + x[3]) / 2 < b - 1e-3 if ax == 0 else a + 1e-3 < (x[1] + x[4]) / 2 < b - 1e-3)
                and abs(((x[1] + x[4]) / 2 if ax == 0 else (x[0] + x[3]) / 2) - l["k"]) < 0.06]
        if n_.startswith("D4"):
            face = min(x[0] for x in _boxes_of("FT_wall_Tiles") if bxr[2] - wb - 1e-3 < x[0] < bxr[2] and a < x[1] < b)
            assert abs(min(x[0] for x in mine) - face) < 1e-5, "bath door: the house tile does not reach over the riser tiles"
        if n_.startswith("D1"):
            assert abs(min(x[1] for x in mine) - (GY["B"] - 0.10)) < 1e-5, "porch door: house tile not to the slab edge"
        if n_.startswith("D3"):
            assert abs(max(x[3] for x in mine) - (GX["3"] + 0.10)) < 1e-5, "kitchen door: house tile not to the slab edge"
    # walls: sample the bath faces and the splash every 5 cm — every point under a tile or in a joint
    wt = _boxes_of("FT_wall_Tiles")
    for i_, p_ in enumerate(wt):   # and no two wall tiles overlap (inside corners)
        for q_ in wt[i_ + 1:]:
            assert any(min(p_[k + 3], q_[k + 3]) - max(p_[k], q_[k]) < 1e-6 for k in range(3)), \
                f"wall tiles overlap at {p_[0]:.3f}, {p_[1]:.3f}, {p_[2]:.2f}"
    zc = min(v.z for v in _verts(bpy.data.objects["CL_Bath_Boards"]))
    assert abs(max(x[5] for x in wt if bxr[0] - 0.1 < x[0] < bxr[2] + 0.1 and bxr[1] - 0.1 < x[1] < bxr[3] + 0.1) - zc) < 1e-4, \
        "bath wall tiles do not reach the ceiling (the user)"
    jw = FT["wall"]["joint"]
    near = lambda p, x: x[0] - jw - 1e-4 <= p.x <= x[3] + jw + 1e-4 and x[1] - jw - 1e-4 <= p.y <= x[4] + jw + 1e-4 and \
        x[2] - jw - 1e-4 <= p.z <= x[5] + jw + 1e-4
    openings = [(c0 + WALL["pl"], c1 - WALL["pl"], z0 + WALL["pl"], z1 - WALL["pl"], _wlines(WALL_LINES, OFFSET)[ln])
                for n_, ln, c0, c1, z0, z1 in OPENINGS]
    def in_opening(p, face_k, ax):
        for a, b, z0, z1, l in openings:
            if l["ax"] == ax and abs(face_k - l["k"]) < 0.06 and a < (p.x if ax == 0 else p.y) < b and z0 < p.z < z1:
                return True
        return False
    bare = 0
    for p, q, inn in _outline(bxr, rooms["Bath"][1]):
        ax = 0 if abs(p[1] - q[1]) < 1e-9 else 1
        lo, hi = sorted((p[ax], q[ax]))
        for i in range(1, int((hi - lo) / 0.05)):
            for j in range(1, int((zc - FL_BATH) / 0.05)):
                u, z = lo + i * 0.05, FL_BATH + j * 0.05
                P = Vector((u, p[1] + inn[1] * (wb - 0.001), z)) if ax == 0 else Vector((p[0] + inn[0] * (wb - 0.001), u, z))
                if z > FL_HOUSE - 0.02 and in_opening(P, p[1 - ax], ax):
                    continue
                bare += not any(near(P, x) for x in wt)
    assert bare == 0, f"bath walls: {bare} sample points bare"
    z0 = FL_HOUSE + KITCHEN["top"]
    for i in range(1, int((KITCHEN["x1"] - lv[0]) / 0.05)):
        for j in range(1, int(KITCHEN["splash"] / 0.05)):
            P = Vector((lv[0] + i * 0.05, lv[3] - wb + 0.001, z0 + j * 0.05))
            if not in_opening(P, lv[3], 0):
                assert any(near(P, x) for x in wt), f"kitchen splash bare at {P.x:.2f}, {P.z:.2f}"
    for x in wt:   # nothing tiled outside the bath and the splash band (+ their window reveals)
        c = Vector(((x[0] + x[3]) / 2, (x[1] + x[4]) / 2, (x[2] + x[5]) / 2))
        in_bath = bxr[0] - 0.05 <= c.x <= bxr[2] + 0.05 and bxr[1] - 0.05 <= c.y <= bxr[3] + 0.05
        in_spl = lv[0] - 1e-3 <= c.x <= KITCHEN["x1"] + 1e-3 and lv[3] - 0.02 <= c.y <= lv[3] + 0.05 and z0 - 1e-4 <= c.z <= z0 + KITCHEN["splash"] + 1e-4
        assert in_bath or in_spl, f"a wall tile off the bath and the splash at {c.x:.2f}, {c.y:.2f}, {c.z:.2f}"
    # waterproofing: the whole bath floor, up the walls 30 cm (1.80 in the shower), behind the tiles
    wp = _boxes_of("FT_Bath_Waterproof")
    fl_wp = sum((x[3] - x[0]) * (x[4] - x[1]) for x in wp if x[5] - x[2] < 0.01)
    bslab = ZONES["Bath"][1] + SLAB["t"]
    want = sum((q[2] - q[0]) * (q[3] - q[1]) for q in _minus(bxr, rooms["Bath"][1]))
    assert abs(fl_wp - want) < 1e-4 and all(abs(x[2] - bslab) < 1e-5 for x in wp if x[5] - x[2] < 0.01), "bath floor waterproofing"
    for x in wp:
        if x[5] - x[2] >= 0.01:
            cx = (x[0] + x[3]) / 2
            h = WP["shower"] if SHOWER[0] <= cx <= SHOWER[1] else WP["up"]
            assert x[5] <= FL_BATH + h + 1e-5, f"waterproofing over {h} m at x {cx:.2f}"
            assert min(x[3] - x[0], x[4] - x[1]) <= WP["t"] + 1e-6, "waterproofing not a thin coat"
    wall_wp = [x for x in wp if x[5] - x[2] >= 0.01]
    inb = lambda P: any(x[0] - 1e-6 <= P.x <= x[3] + 1e-6 and x[1] - 1e-6 <= P.y <= x[4] + 1e-6 and x[2] <= P.z <= x[5] for x in wall_wp)
    for p, q, inn in _outline(bxr, rooms["Bath"][1]):   # every face, every 5 cm: coated to exactly its height
        ax = 0 if abs(p[1] - q[1]) < 1e-9 else 1
        lo, hi = sorted((p[ax], q[ax]))
        for i in range(1, int((hi - lo) / 0.05)):
            u = lo + i * 0.05
            P = Vector((u, p[1] + inn[1] * WP["t"] / 2, 0)) if ax == 0 else Vector((p[0] + inn[0] * WP["t"] / 2, u, 0))
            h = FL_BATH + (WP["shower"] if SHOWER[0] <= P.x <= SHOWER[1] else WP["up"])
            P.z = h - 0.01
            if in_opening(P, p[1 - ax], ax):
                continue
            assert inb(P), f"waterproofing short of {h - FL_BATH:.2f} at {P.x:.2f}, {P.y:.2f}"
            P.z = h + 0.01
            assert not inb(P), f"waterproofing over {h - FL_BATH:.2f} at {P.x:.2f}, {P.y:.2f}"
    # finishes never inside the structure (slab, curb, beams, joints, columns): the old bath ledge would show here
    conc = [b for (n_, _), b in _solids([C_SLAB, C_GB, C_COL, C_STEP]).items() if bpy.data.objects[n_].data.get("element") == "concrete"]
    for nm in ("FT_floor_Tiles", "FT_bath_Tiles", "FT_porch_Tiles", "FT_floor_Bed", "FT_bath_Bed", "FT_porch_Bed", "FT_Screed",
               "FT_wall_Tiles", "FT_porch_Steps"):
        for x in _boxes_of(nm):
            hit = next((b for b in conc if (i := _inter(x, b)) and _vol(i) > 1e-9), None)
            assert hit is None, f"{nm} inside the concrete at {x[0]:.2f}, {x[1]:.2f}, {x[2]:.3f}"
    # screed on its slab, up to under the bed
    for x in _boxes_of("FT_Screed"):
        assert any(abs(x[2] - (zt + SLAB["t"]) - (WP["t"] if abs(zt + SLAB["t"] - bslab) < 1e-6 else 0)) < 1e-5 for _, zt in _zones().values()), \
            f"screed off the slab at {x[0]:.2f}, {x[1]:.2f}"
    # steps: equal risers ≤ 15 cm, treads ≥ 25 cm, the nosing on every step edge
    g = _step_geom()
    for nm, G in g.items():
        r = [h - (G["tops"][i + 1] if i + 1 < len(G["tops"]) else GL) for i, h in enumerate(G["tops"])]
        assert max(r) - min(r) < 1e-6 and max(r) <= 0.15 + 1e-6, f"{nm} steps: risers {r}"
        assert all(t_ >= 0.25 for t_ in G["treads"][1:]), f"{nm} steps: treads"
    nl = bpy.data.objects["FT_Nosing"].data["lens"]
    assert len(nl) == sum(len(G["tops"]) for G in g.values()), "a step edge without nosing"
    noses = _islands(bpy.data.objects["FT_Nosing"])   # each nosing on its nose, top flush with its tread, read back
    for nm, G in g.items():
        for Nn, h in zip(G["noses"], G["tops"]):
            at = G["E"] + G["sg"] * Nn
            k = 0 if G["ax"] == "x" else 1
            assert any(abs(max(v.z for v in vs) - h) < 1e-4 and abs((max if G["sg"] > 0 else min)(v[k] for v in vs) - at) < 1e-4
                       for vs, _ in noses), f"{nm}: no nosing on the nose at {at:.3f}, +{h:.3f}"
    for nm, G in g.items():   # the concrete under each tread: its top one tile + bed below the finished tread
        cb = _boxes_of(f"ST_{nm}_Conc")
        eps = FT["porch"]["size"][2] + FT["porch"]["bed"]
        for i, h in enumerate(G["tops"]):
            if G["treads"][i] > 0:
                assert any(abs(x[5] - (h - eps)) < 1e-5 for x in cb), f"{nm}: tread {i} concrete not {eps * 1000:.1f} mm under its finish"
    # skirting = room outlines less the doors and the counter
    want = 0.0
    for room in ("Bed2", "Bed1", "Living"):
        rc, cut, _ = rooms[room]
        want += sum(math.dist(p, q) for p, q, _ in _outline(rc, cut))
        for n_, l, a, b, _ in _doors():
            for side in ((rc[0], rc[2]) if l["ax"] == 1 else (rc[1], rc[3])):
                if abs(side - l["k"]) < WALL["t"] / 2 + WALL["pl"] + 1e-3 and \
                        ((rc[1] <= a and b <= rc[3]) if l["ax"] == 1 else (rc[0] <= a and b <= rc[2])):
                    want -= b - a
    want -= KITCHEN["x1"] - lv[0]
    got = sum(bpy.data.objects["FT_Skirting"].data["lens"])
    assert abs(got - want) < 0.05, f"skirting {got:.2f} m, outlines − doors − counter {want:.2f}"
    for k in FT:
        q = bpy.data.objects[f"FT_{k}_Qty"].data
        assert q["need"] == math.ceil((q["whole"] + q["cut"] + q["strips"]) * (1 + SPARE) - 1e-9), f"{k}: tile count"
    return ("tiles ok: " + " · ".join(f"{k} {a:.2f} m² (tiles + joints)" for k, a in out) +
            f" · bath walls to the ceiling {zc:.2f}, splash {KITCHEN['splash']:.2f} · skirting {got:.2f} m")
