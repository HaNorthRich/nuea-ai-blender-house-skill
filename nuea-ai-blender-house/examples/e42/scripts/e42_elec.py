"""E42 ST12 ไฟฟ้า + ดวงโคม (spec 30 ต.ค.), after the tiles:
  CHANG ซีรีส์ Y switches / double sockets, CHANG A14 consumer unit (63 A main), PHILIPS Meson 6" 12 W downlights,
  STIEBEL ELTRON DE 35 water heater, 1 × TCL T-VoxIN13S 12,283 BTU in Bed1; THW 1.5 lights, 2.5 sockets, 4 heater +
  AC, 16 main; yellow PVC conduit above the ceiling, chased into the walls down to each box.
Points come from a table placed against the rooms read from the model; downlights sit between the C-line runners.
Conduit: e42_conduit.py (spec ../ST12_conduit_spec.md) — on the wall faces over the ceiling, stacked by height, bent
not mitred, through brick at room corners, looped down chases into the wall devices, flex to the downlights;
its read-back checks in e42_conduit_check.py.

    exec(<e42_struct>) … exec(<e42_tiles>); exec(<this>); build_elec(); print(report(C_ELEC)); print(selfcheck_elec())
"""
import math
import bmesh
from mathutils import Vector

C_ELEC = "E42 ST12 Electrical"
# device heights above the room's finished floor (Thai practice; assumed): switches 1.20, sockets 0.30, counter
# sockets 1.10 (in the splash), heater box 1.60, AC point 2.30, CU centre 1.60
# sizes: DL262 cut-out 15 cm, 17 × 17 × 2.1 cm (HomePro); A-14 433 × 191 × 93 mm (Lazada); TCL indoor 82 × 30.5 × 19.5 cm
EL = dict(
    void=0.10,            # conduit runs this far over the ceiling boards
    box=(0.055, 0.105, 0.045), plate=(0.075, 0.120, 0.008),   # 2×4 flush box, plate (W × H × T)
    dl=dict(d=0.170, cut=0.150, h=0.021, w=12, below=0.002, flange=0.004,   # trim: its top `below` the board face (under
            th="โคมดาวน์ไลท์ PHILIPS Meson DL262 6\" LED 12W Daylight"),   # both paint coats), seen from the room; the body up the cut-out
    sw=dict(th="สวิตช์ทางเดียว CHANG ซีรีส์ Y CH-501N สีขาว", z=1.20),
    so=dict(th="เต้ารับคู่มีกราวด์ CHANG ซีรีส์ Y PCH-904 สีขาว", z=0.30),
    cu=dict(size=(0.433, 0.191, 0.093), z=1.60, th="ตู้คอนซูมเมอร์ CHANG A14 14 ช่อง พร้อมเมน 63A (มีไฟสัญญาณ)"),
    heater=dict(size=(0.21, 0.36, 0.08), z=1.60, w=3500, th="เครื่องทำน้ำอุ่น STIEBEL ELTRON DE 35 3,500 วัตต์ สีดำ"),
    ac_in=dict(size=(0.82, 0.305, 0.195), z=2.20, th="แอร์ติดผนัง Inverter TCL T-VoxIN13S 12,283 BTU (ชุดในบ้าน)"),
    ac_out=dict(size=(0.70, 0.50, 0.27), z=0.80, th="แอร์ TCL T-VoxIN13S (คอยล์ร้อน) บนขาแขวน"),
    conduit={"1/2": 0.016, "3/4": 0.020, "1": 0.025}, stock=4.0, clip=1.0,   # OD (m); ตราช้าง 4 m a piece (ไทวัสดุ); clips @ 1 m (assumed)
    slack=0.30,          # wire left at each device / box end
    # TOP กล่องพักสายเหลี่ยม สีเหลือง (ไทวัสดุ, spec 30 ต.ค.), on edge on the wall: (along, height, across) — sizes
    # estimated from the product photos (not printed): 2×4 at each downlight, 4×4 a shared pull box (≤ 360°) or a tee
    box24=dict(size=(0.115, 0.068, 0.050), ko=(1, 2), th="กล่องพักสายเหลี่ยม TOP 2×4 นิ้ว สีเหลือง (60159260)"),
    box44=dict(size=(0.115, 0.115, 0.055), ko=(2, 2), th="กล่องพักสายเหลี่ยม TOP 4×4 นิ้ว สีเหลือง (60282388)"),
    flex=dict(od=0.020, roll=50.0, max=1.80, th="ท่ออ่อนร้อยสายไฟ (ท่อลูกฟูก) 1/2\" ม้วน 50 ม. — จากกล่องพักถึงดวงโคม"),
    stock_wire=100.0,
)
CONDUIT_TH = {k: f"ท่อร้อยสายไฟ PVC สีเหลือง {k}\" ยาว 4 ม." for k in EL["conduit"]}
WIRE_TH = {"1.5": "สายไฟ THW 1×1.5 ตร.มม.", "G1.5": "สายดิน THW 1×1.5 ตร.มม. สีเขียว (วงจรแสงสว่าง — ยืนยันขนาดตาม วสท.)", "2.5": "สายไฟ THW 1×2.5 ตร.มม.", "4": "สายไฟ THW 1×4 ตร.มม.",
           "16": "สายไฟ THW 1×16 ตร.มม. (สายเมน)", "G2.5": "สายดิน THW 1×2.5 ตร.มม. สีเขียว",
           "G10": "สายต่อหลักดิน THW 1×10 ตร.มม. สีเขียว"}
# circuits: breaker A, conductors per run [(wire, n)], conduit, points in route order
CIRCUITS = [
    dict(id="L1", amp=10, wires=[("1.5", 2), ("G1.5", 1)], conduit="1/2", th="วงจรแสงสว่าง ห้องนอน + ห้องน้ำ",
         pts=["SW_Bath", "DL_Bath", "SW_Bed2", "DL_Bed2_1", "DL_Bed2_2", "SW_Bed1", "DL_Bed1_1", "DL_Bed1_2"]),
    dict(id="L2", amp=10, wires=[("1.5", 2), ("G1.5", 1)], conduit="1/2", th="วงจรแสงสว่าง นั่งเล่น ครัว เฉลียง หลังบ้าน",
         pts=["SW_Living", "DL_Living_1", "DL_Living_2", "DL_Porch_1", "DL_Porch_2", "SW_Porch", "SW_Kitchen", "DL_Kitchen_1",
              "DL_Kitchen_2", "DL_Back"]),
    dict(id="S1", amp=16, wires=[("2.5", 2), ("G2.5", 1)], conduit="1/2", th="วงจรเต้ารับ ห้องนอน",
         pts=["SO_Bed2_1", "SO_Bed2_2", "SO_Bed1_1", "SO_Bed1_2"]),
    dict(id="S2", amp=16, wires=[("2.5", 2), ("G2.5", 1)], conduit="1/2", th="วงจรเต้ารับ นั่งเล่น + ตู้เย็น",
         pts=["SO_Living_1", "SO_Living_2", "SO_Fridge"]),
    dict(id="S3", amp=16, wires=[("2.5", 2), ("G2.5", 1)], conduit="1/2", th="วงจรเต้ารับ เคาน์เตอร์ครัว",
         pts=["SO_Kitchen_1", "SO_Kitchen_2"]),
    dict(id="H1", amp=20, wires=[("4", 2), ("G2.5", 1)], conduit="1/2", th="วงจรเครื่องทำน้ำอุ่น", pts=["HT_Bath"]),
    dict(id="A1", amp=20, wires=[("4", 2), ("G2.5", 1)], conduit="1/2", th="วงจรแอร์ ห้องนอน 1", pts=["AC_Bed1"]),
]
# (id, kind, room, face or ceiling spot, along / (fx, fy), gangs) — faces: x0 x1 y0 y1 of the room's plaster rect
POINTS = [
    ("DL_Bed2_1", "dl", "Bed2", None, (0.5, 0.30), 0), ("DL_Bed2_2", "dl", "Bed2", None, (0.5, 0.72), 0),
    ("DL_Bed1_1", "dl", "Bed1", None, (0.5, 0.30), 0), ("DL_Bed1_2", "dl", "Bed1", None, (0.5, 0.72), 0),
    ("DL_Bath", "dl", "Bath", None, (0.45, 0.5), 0),
    ("DL_Living_1", "dl", "Living", None, (0.5, 0.18), 0), ("DL_Living_2", "dl", "Living", None, (0.5, 0.45), 0),
    ("DL_Kitchen_1", "dl", "Living", None, (0.5, 0.66), 0), ("DL_Kitchen_2", "dl", "Living", None, (0.5, 0.86), 0),
    ("DL_Porch_1", "dl", "Porch", None, (0.27, 0.5), 0), ("DL_Porch_2", "dl", "Porch", None, (0.73, 0.5), 0),
    ("DL_Back", "dl", "Soffit", None, (6.15, 0.17), 0),          # east eave at y 6.15, 17 cm out from the plaster
    ("SW_Bed2", "sw", "Bed2", "x1", 1.62, 1), ("SW_Bed1", "sw", "Bed1", "x1", 5.75, 1),   # (SW_Bed2 off SW_Porch's back, 31 ต.ค.)
    ("SW_Bath", "sw", "Living", "x0", 4.27, 1),   # (spec 30 ต.ค.: its chase in the door-jamb tie — no brick door → D2; 4.30 grazed D2's coat)
    ("SW_Living", "sw", "Living", "x1", 1.75, 1), ("SW_Porch", "sw", "Living", "x0", 1.7825, 1),   # (spec 31 ต.ค.: porch lights on a switch of their own, by the SW corner — between its loop's straight past the corner and the Bed2 door's jamb tie)
    ("SW_Kitchen", "sw", "Living", "x1", 6.75, 2),   # (assumed 30 ต.ค.: past the back door D3 (5.64–6.55 since ST14, east edge pinned) + its tie; 5.55 left the CU no room)
    ("SO_Bed2_1", "so", "Bed2", "x0", 1.80, 2), ("SO_Bed2_2", "so", "Bed2", "y1", 2.40, 2),
    ("SO_Bed1_1", "so", "Bed1", "x0", 6.30, 2), ("SO_Bed1_2", "so", "Bed1", "y0", 1.00, 2),
    ("SO_Living_1", "so", "Living", "x1", 3.70, 2), ("SO_Living_2", "so", "Living", "x0", 6.50, 2),
    ("SO_Fridge", "so", "Living", "y1", 5.45, 2),   # (assumed; 30 ต.ค. 7 cm off the NE corner column: room for its loop)
    ("SO_Kitchen_1", "so", "Living", "y1", 3.65, 2), ("SO_Kitchen_2", "so", "Living", "y1", 5.30, 2),   # (assumed 30 ต.ค.: 3.65 / 5.30 either side of window W3 + its tie; loops need ≥ 0.37 apart)
    ("HT_Bath", "heater", "Bath", "y0", 2.55, 0), ("AC_Bed1", "ac", "Bed1", "x0", 6.10, 0),
    ("CU", "cu", "Living", "x1", 5.10, 0),   # (assumed; 5.00 left no room to set out past D3 above the wall angle)
]
# which switch gang lights each downlight (the switched conductor runs between them)
CTL = {"DL_Bath": ("SW_Bath", 1), "DL_Bed2_1": ("SW_Bed2", 1), "DL_Bed2_2": ("SW_Bed2", 1), "DL_Bed1_1": ("SW_Bed1", 1),
       "DL_Bed1_2": ("SW_Bed1", 1), "DL_Living_1": ("SW_Living", 1), "DL_Living_2": ("SW_Living", 1),
       "DL_Porch_1": ("SW_Porch", 1), "DL_Porch_2": ("SW_Porch", 1), "DL_Kitchen_1": ("SW_Kitchen", 1),
       "DL_Kitchen_2": ("SW_Kitchen", 1), "DL_Back": ("SW_Kitchen", 2)}
HEIGHT = dict(sw=EL["sw"]["z"], so=EL["so"]["z"], heater=EL["heater"]["z"] + EL["heater"]["size"][1] / 2 + 0.05,
              ac=2.30, cu=EL["cu"]["z"])
COUNTER_SOCKET = 1.10   # above FL, in the splash (SO_Kitchen_*)
SHUNT = dict(AC_Bed1=0.45)   # the AC point beside its unit: along offset from the unit centre (m)


def _rooms_el():
    """{room: (plaster rect, finished floor, ceiling underside)} — the rooms of the paint stage + the porch."""
    out = dict(_rooms())
    pr = bpy.data.objects["CL_Porch_Boards"]
    vs = [pr.matrix_world @ v.co for v in pr.data.vertices]
    out["Porch"] = ((min(v.x for v in vs), min(v.y for v in vs), max(v.x for v in vs), max(v.y for v in vs)), FL_PORCH,
                    min(v.z for v in vs))
    return out


def _runner_gaps(tag, ax):
    """Centre lines of a ceiling's runners along one axis: ax 1 → cross runners (their y), ax 0 → mains (their x)."""
    out = set()
    for vs, _ in _islands(bpy.data.objects[f"CL_{tag}_Runners"]):
        dx = max(v.x for v in vs) - min(v.x for v in vs)
        dy = max(v.y for v in vs) - min(v.y for v in vs)
        if (dx > dy) == (ax == 1):
            out.add(round(sum(v[ax] for v in vs) / len(vs), 4))
    return sorted(out)


def _between(t, lines, half):
    """t moved into the middle of the gap between runner lines that holds it, clear of them by half."""
    for a, b in zip(lines, lines[1:]):
        if a <= t <= b:
            return (a + b) / 2 if b - a > 2 * half else t
    return t


def _points():
    """{id: dict(kind, room, p (world centre of the device face / fixture bottom), n (out of the wall), gangs, z_void)}."""
    rooms = _rooms_el()
    wb = _wall_build()
    out = {}
    half = EL["dl"]["d"] / 2 + CEIL["cline"][0] / 2 + 0.005
    for pid, kind, room, face, at, gangs in POINTS:
        if kind == "dl" and room == "Soffit":
            a, e, w, depth, L = _soffit_frame()[1]   # the east eave
            u, v = at[0] - a.y, depth - at[1]
            us = sorted({round((sum(q.x for q in vs) / len(vs) - a.x) * e.x + (sum(q.y for q in vs) / len(vs) - a.y) * e.y, 4)
                         for vs, _ in _islands(bpy.data.objects["CL_Soffit_Runners"])
                         if abs(max(q.y for q in vs) - min(q.y for q in vs)) < 0.05 and max(q.x for q in vs) > GX["3"]})
            u = _between(u, us, half)
            P = a + e * u + w * v
            z = _soffit_z()
            out[pid] = dict(kind=kind, room=room, p=Vector((P.x, P.y, z)), n=Vector((0, 0, -1)), gangs=0, zv=z + EL["void"])
            continue
        rc, fl, zc = rooms[room]
        if kind == "dl":
            x = rc[0] + at[0] * (rc[2] - rc[0])
            y = rc[1] + at[1] * (rc[3] - rc[1])
            x = _between(x, _runner_gaps(room, 0), half)
            y = _between(y, _runner_gaps(room, 1), half)
            out[pid] = dict(kind=kind, room=room, p=Vector((x, y, zc)), n=Vector((0, 0, -1)), gangs=0, zv=zc + EL["void"])
            continue
        n = {"x0": Vector((1, 0, 0)), "x1": Vector((-1, 0, 0)), "y0": Vector((0, 1, 0)), "y1": Vector((0, -1, 0))}[face]
        k = {"x0": rc[0], "x1": rc[2], "y0": rc[1], "y1": rc[3]}[face]
        h = COUNTER_SOCKET if pid.startswith("SO_Kitchen") else HEIGHT[kind]
        tiled = room == "Bath" or pid.startswith("SO_Kitchen")   # on the tile face
        k += n.x * (wb if tiled else 0) + n.y * (wb if tiled else 0)
        along = at + SHUNT.get(pid, 0.0)
        p = Vector((k, along, fl + h)) if face[0] == "x" else Vector((along, k, fl + h))
        out[pid] = dict(kind=kind, room=room, p=p, n=n, gangs=gangs, zv=zc + EL["void"])
    return out


def _curve(c, name, paths, r, m, **props):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_mode, cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = "3D", "ROUND", r, 2, True
    for pts in paths:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for P, q in zip(sp.points, pts):
            P.co = (*q, 1.0)
    for k, v in props.items():
        cu[k] = v
    cu.materials.append(m)
    o = bpy.data.objects.new(name, cu)
    c.objects.link(o)
    return o


def _cyl(bm, ctr, r, h, n=24):
    """Vertical cylinder, bottom centre ctr."""
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r, radius2=r, depth=h,
                          matrix=__import__("mathutils").Matrix.Translation(ctr + Vector((0, 0, h / 2))))


def _voids():
    """{room: (plaster rect, columns standing into it, ceiling z)} for every void a run passes: rooms, porch, east eave."""
    out = {r: (rc, cut, _rooms_el()[r][2]) for r, (rc, cut, fl) in _rooms_floor().items()}
    pr = _rooms_el()["Porch"][0]
    out["Porch"] = (pr, _merged(_intruders(pr, 1.0)), _rooms_el()["Porch"][2])
    a, e, w, depth, L = _soffit_frame()[1]
    xw = GX["3"] + WALL["t"] / 2 + OFFSET["B3-E3"] + WALL["pl"]   # the B3-E3 wall's outside plaster face
    out["Eave"] = ((xw, GY["A"], a.x, GY["E"]), [], _soffit_z())
    return out


def _fillet(path, rmax=0.04, keep=0.015):
    """A flexible conduit is bent, not mitred: each corner rounded (quadratic, 6 steps) as far as its legs allow, the
    ends left straight for keep (the connectors)."""
    out = [path[0]]
    for i in range(1, len(path) - 1):
        a, b, c = out[-1], path[i], path[i + 1]
        l1, l2 = (b - a).length, (c - b).length
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        u1, u2 = (b - a) / l1, (c - b) / l2
        if u1.dot(u2) > 0.999:
            out.append(b)
            continue
        t = min(rmax, l1 - (keep if i == 1 else 0.0), l2 / 2 if i + 1 < len(path) - 1 else l2 - keep)
        p1, p2 = b - u1 * t, b + u2 * t
        out += [p1 * (1 - s) ** 2 + b * 2 * (1 - s) * s + p2 * s ** 2 for s in (j / 6 for j in range(7))]
    out.append(path[-1])
    return out


def _ribs(bm, path, r, pitch=0.006, rib=0.0015, skip=0.015):
    """The corrugations of a flexible conduit: a thin ring every pitch along it (visual only, no take-off)."""
    L = _path_len(path)
    s, i, acc = skip, 0, 0.0
    while s < L - skip:
        while acc + (path[i + 1] - path[i]).length < s:
            acc += (path[i + 1] - path[i]).length
            i += 1
        t = (path[i + 1] - path[i]).normalized()
        c = path[i] + t * (s - acc)
        e1 = t.orthogonal().normalized()
        e2 = t.cross(e1)
        ring = []
        for k in range(8):
            a = 2 * math.pi * k / 8
            ring.append([bm.verts.new(c + (e1 * math.cos(a) + e2 * math.sin(a)) * (r + rib * m)) for m in (-0.6, 1.0)])
        for k in range(8):
            (a0, a1), (b0, b1) = ring[k], ring[(k + 1) % 8]
            bm.faces.new((a1, b1, b0, a0))
        s += pitch


def _path_len(path):
    return sum((q - p).length for p, q in zip(path, path[1:]))


def _lead(C, S, pts):
    """The live conductors of a leg whose downstream devices are S (a set of point ids): lighting = N if a light is
    downstream, L if a switch is, + one switched line per gang whose switch and lights lie on both sides of the leg;
    other circuits: all their live conductors."""
    live = [w for w in C["wires"] if not w[0].startswith("G")]
    if live[0][0] != "1.5":
        return live
    gangs = {}
    for x, g in CTL.items():
        if x in C["pts"] and g[0] in C["pts"]:
            gangs.setdefault(g, {g[0]}).add(x)
    n = (any(pts[x]["kind"] == "dl" for x in S) + any(pts[x]["kind"] == "sw" for x in S) +
         sum(1 for m in gangs.values() if m & S and not m <= S))
    return [(live[0][0], n)]


def _dl_lens_mat():
    """The downlight lens: lit (emission), set every build (mat() keeps an existing material as it was)."""
    m = mat("M_DL_Lens", (1.0, 0.99, 0.96), 0.3, emission=6.0)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Emission Color"].default_value = (1.0, 0.99, 0.96, 1)
    b.inputs["Emission Strength"].default_value = 6.0
    return m


def build_elec():
    """Devices, CU, heater, AC, downlights; conduit routes per circuit; take-off rows."""
    c = _clear(C_ELEC)
    white = mat("M_Device_White", (0.95, 0.95, 0.94), 0.4)
    grey = mat("M_CU_Grey", (0.82, 0.83, 0.84), 0.4)
    black = mat("M_Heater_Black", (0.05, 0.05, 0.05), 0.4)
    yellow = mat("M_Conduit_Yellow", (0.93, 0.78, 0.10), 0.5)
    pts = _points()
    X, Z = Vector((1, 0, 0)), Vector((0, 0, 1))
    groups = {}
    for pid, pt in pts.items():
        k, p, n = pt["kind"], pt["p"], pt["n"]
        bm = groups.setdefault(k, bmesh.new())
        if k == "dl":   # shortcut: the 150 mm cut-out is not cut in the board (box meshes the ceiling checks read back)
            dl = EL["dl"]
            _cyl(bm, p - Vector((0, 0, dl["below"] + dl["flange"])), dl["d"] / 2, dl["flange"])   # trim ring under the ceiling
            _cyl(bm, p - Vector((0, 0, dl["below"])), dl["cut"] / 2 - 0.002, dl["h"] + dl["below"])   # body up through the board
            _cyl(groups.setdefault("dl_lens", bmesh.new()), p - Vector((0, 0, dl["below"] + dl["flange"] + 0.0005)),
                 dl["cut"] / 2 - 0.015, 0.0005)   # the lit lens in the ring
            continue
        t = n.cross(Z) if abs(n.z) < 0.5 else X
        if k in ("sw", "so"):
            _cuboid(bm, p + n * EL["plate"][2] / 2, [t, Z, n], [EL["plate"][0] / 2, EL["plate"][1] / 2, EL["plate"][2] / 2])
            _cuboid(bm, p - n * EL["box"][2] / 2, [t, Z, n], [EL["box"][0] / 2, EL["box"][1] / 2, EL["box"][2] / 2 - 0.0005])
        elif k == "cu":
            s = EL["cu"]["size"]
            _cuboid(bm, p + n * s[2] / 2, [t, Z, n], [s[0] / 2, s[1] / 2, s[2] / 2])
        elif k == "heater":
            s = EL["heater"]["size"]
            ctr = Vector((p.x, p.y, pt["p"].z - HEIGHT["heater"] + EL["heater"]["z"]))
            _cuboid(bm, ctr + n * s[2] / 2, [t, Z, n], [s[0] / 2, s[1] / 2, s[2] / 2])
            _cuboid(bm, p - n * EL["box"][2] / 2, [t, Z, n], [EL["box"][0] / 2, EL["box"][1] / 2, EL["box"][2] / 2 - 0.0005])
        elif k == "ac":
            s = EL["ac_in"]["size"]
            fl = _rooms_el()[pt["room"]][1]
            off = Vector((0, SHUNT[pid], 0)) if abs(n.x) > 0.5 else Vector((SHUNT[pid], 0, 0))   # the unit beside its point
            ctr = Vector((p.x, p.y, fl + EL["ac_in"]["z"])) - off
            _cuboid(bm, ctr + n * s[2] / 2, [t, Z, n], [s[0] / 2, s[1] / 2, s[2] / 2])
            _cuboid(bm, p - n * EL["box"][2] / 2, [t, Z, n], [EL["box"][0] / 2, EL["box"][1] / 2, EL["box"][2] / 2 - 0.0005])
            out_face = ctr.x - (WALL["t"] + 2 * WALL["pl"]) if n.x > 0 else ctr.x   # outdoor unit on the outside face
            so_ = EL["ac_out"]["size"]
            _cuboid(groups.setdefault("ac_out", bmesh.new()), Vector((out_face - so_[2] / 2, ctr.y, EL["ac_out"]["z"] + so_[1] / 2)),
                    [Vector((0, 1, 0)), Z, X], [so_[0] / 2, so_[1] / 2, so_[2] / 2])
    props = dict(dl=dict(element="piece", type="EL1", th=EL["dl"]["th"]),
                 sw=dict(element="piece", type="EL2", th=EL["sw"]["th"]),
                 so=dict(element="piece", type="EL3", th=EL["so"]["th"]),
                 cu=dict(element="piece", type="EL4", th=EL["cu"]["th"]),
                 heater=dict(element="piece", type="EL5", th=EL["heater"]["th"]),
                 ac=dict(element="piece", type="EL6", th=EL["ac_in"]["th"]),
                 ac_out=dict(element="piece", type="EL7", th=EL["ac_out"]["th"]))
    counts = {k: sum(1 for p in pts.values() if p["kind"] == k) for k in props}
    counts["sw"] = sum(p["gangs"] for p in pts.values() if p["kind"] == "sw")   # one mechanism a gang
    counts["ac_out"] = counts["ac"]
    mats = dict(dl=white, sw=white, so=white, cu=grey, heater=black, ac=white, ac_out=grey,
                dl_lens=_dl_lens_mat())
    for k, bm in groups.items():
        if k == "dl_lens":   # (no take-off row: part of the fitting)
            _obj(c, "EL_dl_lens", bm, mats[k])
            continue
        _obj(c, f"EL_{k}", bm, mats[k], count=counts[k], **props[k])
    # routes: neat runs on the walls over the ceiling, boxes at every branch, flexible conduit to the downlights
    R = _routes_wall(pts)   # e42_conduit.py (ST12 rebuild, spec 30 ต.ค.): on the wall faces, bent, boxes on the wall
    runs, wire, bends, cross = R["runs"], R["wire"], R["bends"], R["cross"]
    yel = mat("M_Box_Yellow", (0.93, 0.76, 0.12), 0.45)
    for kind in ("box24", "box44"):
        jb = bmesh.new()
        n_ = 0
        for B, t, size in R["boxes"]:   # inline on the lanes: on edge, long side along the run, lid to the room
            if size == EL[kind]["size"]:
                _top_box(jb, B, t, EL[kind])
                n_ += 1
        _obj(c, f"EL_{kind}", jb, yel, element="piece", type=f"EL9{kind[-2:]}", count=n_, th=EL[kind]["th"])
    _curve(c, "EL_Flex", [path for _, _, path in R["flex"]], EL["flex"]["od"] / 2, mat("M_Flex", (0.95, 0.62, 0.12), 0.6),
           element="flex", type="EF", th=EL["flex"]["th"], lens=[sum((q - p).length for p, q in zip(path, path[1:]))
                                                                     for _, _, path in R["flex"]],
           bends=0, stock=EL["flex"]["roll"], clip=10.0, circ=[c_ for c_, _, _ in R["flex"]], to=[t_ for _, t_, _ in R["flex"]],
           amp=[0] * len(R["flex"]), wsz=[""] * len(R["flex"]))
    rb = bmesh.new()
    for _, _, path in R["flex"]:
        _ribs(rb, path, EL["flex"]["od"] / 2)
    _obj(c, "EL_Flex_Ribs", rb, mat("M_Flex", (0.95, 0.62, 0.12), 0.6))   # looks only: no take-off data
    gw = R["gw"]
    rod = bmesh.new()
    _cyl(rod, Vector((gw[-1].x, gw[-1].y, gw[-1].z - 2.40)), 0.008, 2.40)   # its top at the buried end of the ground run
    _obj(c, "EL_GroundRod", rod, mat("M_Copper", (0.72, 0.45, 0.20), 0.3, 1.0), element="piece", type="EL8",
         th="หลักดินทองแดง 5/8\" × 2.40 ม. + แคลมป์", count=1)
    byid = {C["id"]: C for C in CIRCUITS}   # (an unknown circuit id raises)
    for size, rs in runs.items():
        lens = [sum((q - p).length for p, q in zip(path, path[1:])) for _, _, path in rs]
        _curve(c, f"EL_Conduit_{size.replace('/', '-')}", [path for _, _, path in rs], EL["conduit"][size] / 2, yellow,
               element="conduit", type=f"EC{size}", th=CONDUIT_TH[size], lens=lens, bends=bends.get(size, 0),
               circ=[cid for cid, _, _ in rs], to=[pid for _, pid, _ in rs],
               amp=["" if cid in ("GND", "MAIN") else "+".join(str(byid[c]["amp"]) for c in cid.split("+")) for cid, _, _ in rs],   # "20+16": a shared conduit
               wsz=["" if cid in ("GND", "MAIN") else "+".join(byid[c]["wires"][0][0] for c in cid.split("+")) for cid, _, _ in rs],
               stock=EL["stock"], clip=EL["clip"], vlen=R["vlen"].get(size, 0.0))
    for w, L in wire.items():
        o = _obj(c, f"EL_Wire_{w}", bmesh.new(), yellow, element="wire", type=f"EW{w}", th=WIRE_TH[w], length=L,
                 roll=EL["stock_wire"])
        o.hide_viewport = o.hide_render = True
    br = {}
    for C in CIRCUITS:
        br[C["amp"]] = br.get(C["amp"], 0) + 1
    for a, n in br.items():
        o = _obj(c, f"EL_Breaker_{a}A", bmesh.new(), grey, element="piece", type=f"EB{a}", count=n,
                 th=f"เบรกเกอร์ลูกย่อย CHANG {a}A 1P (ปลั๊กออน)")
        o.hide_viewport = o.hide_render = True
    nb = sum(1 for p in pts.values() if p["kind"] in ("sw", "so", "heater", "ac"))
    for name, th, n in (("EL_Box2x4", "บล็อกฝัง 2×4 (สวิตช์ เต้ารับ จุดต่อเครื่องทำน้ำอุ่น จุดแอร์)", nb),
                        ("EL_FlexConn", "คอนเนคเตอร์ท่ออ่อน (2 ตัวต่อเส้น)", 2 * len(R["flex"])),
                        ("EL_WallHoles", "เจาะผนังเหนือฝ้าให้ท่อผ่าน", cross),
                        ("EL_SoffitHoles", "เจาะฝ้าชายคาให้ท่อเมนผ่าน (ท่อขึ้นจากมิเตอร์ + ท่อลงหลังตู้ไฟ)", len(_main_soffit_holes(pts))),
                        ("EL_Chase", "กรีดผนังฝังท่อ (ลงสวิตช์/เต้ารับ · ขึ้นจากตู้ไฟ · สายดิน) + ฉาบปิด — ความยาวรวมใน length", len(R["chase"])),
                        ("EL_Plate1", "หน้ากาก CHANG ซีรีส์ Y 1 ช่อง (สวิตช์ 1 ตัว)", sum(1 for p in pts.values() if p["kind"] == "sw" and p["gangs"] == 1)),
                        ("EL_Plate2", "หน้ากาก CHANG ซีรีส์ Y 2 ช่อง (สวิตช์ 2 ตัว)", sum(1 for p in pts.values() if p["kind"] == "sw" and p["gangs"] == 2)),
                        ("EL_PlateSO", "หน้ากากเต้ารับคู่ CHANG ซีรีส์ Y (ขนาดช่องตามรุ่น PCH-904 — ยืนยัน)", counts["so"]),
                        ("EL_PlateBlank", "หน้ากากปิดจุดต่อ (เครื่องทำน้ำอุ่น แอร์)", counts["heater"] + counts["ac"])):
        o = _obj(c, name, bmesh.new(), grey, element="piece", type=name, th=th, count=n)
        o.hide_viewport = o.hide_render = True
    bpy.data.objects["EL_Chase"].data["length"] = sum(top - bot for _, _, _, bot, top in R["chase"])
    bpy.data.objects["EL_Chase"].data["lens"] = sorted(top - bot for _, _, _, bot, top in R["chase"])   # (one a groove)
    mc, mhs = R["meter"]   # the meter board on column A3 (MAIN: e42_conduit_main.py)
    bm = bmesh.new()
    _cuboid(bm, mc, [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))], list(mhs))
    _obj(c, "EL_Meter", bm, grey, element="piece", type="EL0", th=MAIN["th_meter"], count=1)
    return dict(points=len(pts), wire={k: round(v, 1) for k, v in wire.items()}, crossings=cross)


def _top_box(bm, B, t, spec):
    """A TOP square junction box set on edge: a body whose lid edges (toward the room) are rounded, round knockouts
    on the ends (ko[0] each) and on the long sides (ko[1] each) as thin separate discs."""
    import mathutils
    L, H, D = spec["size"]
    Z = Vector((0, 0, 1))
    n = t.cross(Z)   # the lid faces +n
    before = set(bm.verts)
    _cuboid(bm, B, [t, Z, n], [L / 2, H / 2, D / 2])
    vs = set(bm.verts) - before
    front = [e for e in bm.edges if set(e.verts) <= vs and all((v.co - B).dot(n) > D / 2 - 1e-6 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=front, offset=0.006, segments=3, affect="EDGES", profile=0.5)
    r, th = min(0.0125, H / 4), 0.0012
    zc = -D / 2 + D * 0.40   # on the body, below the lid seam
    def disc(c, ax):
        m = mathutils.Matrix.Translation(c) @ ax.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=r, radius2=r, depth=th, matrix=m)
    for sg in (1, -1):
        for j in range(spec["ko"][0]):   # ends
            disc(B + t * sg * (L / 2 + th / 2) + Z * ((j - (spec["ko"][0] - 1) / 2) * H / 2) + n * zc, t * sg)
        for j in range(spec["ko"][1]):   # long sides (top / bottom when on edge)
            disc(B + Z * sg * (H / 2 + th / 2) + t * ((j - (spec["ko"][1] - 1) / 2) * L / 2) + n * zc, Z * sg)


def selfcheck_elec():
    """ST12 read back from the model: downlights flush under their ceiling, clear of its runners; wall devices off
    every opening; TOP boxes their product size; counts; breaker ↔ wire; the A14 holds the circuits; the heater in
    the shower zone — then the conduit (e42_conduit_check.py: bends, clearances, boxes, brick only, chases, wire)."""
    pts = _points()   # what should exist; positions are read from the model
    rooms = _rooms_el()
    ib, pb = EL["box24"]["size"], EL["box44"]["size"]
    isl = lambda name: [(vs, Vector((sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs))),
                         min(v.z for v in vs), max(v.z for v in vs)) for vs, _ in _islands(bpy.data.objects[name])]
    dls = isl("EL_dl")
    rings = [d for d in dls if d[3] - d[2] < 0.006]
    assert len(rings) == len(dls) // 2 == sum(1 for p in pts.values() if p["kind"] == "dl"), "downlights drawn ≠ table"
    assert EL["dl"]["below"] > 2 * (PAINT["film"] + PAINT["gap"]), "the trim inside the ceiling's paint"
    lens = isl("EL_dl_lens")
    assert len(lens) == len(rings), f"{len(lens)} lenses for {len(rings)} downlights"
    for vs, c, z0, z1 in rings:   # the trim seen from the room: under the ceiling face and its paint, its lens under it
        room = next((r for r, (rc, fl, zc) in rooms.items() if rc[0] < c.x < rc[2] and rc[1] < c.y < rc[3]), None)
        face = _soffit_z() if room is None else rooms[room][2]
        assert abs(z1 - (face - EL["dl"]["below"])) < 1e-4, f"downlight at {c.x:.2f}, {c.y:.2f}: trim top {(z1 - face) * 1000:.1f} mm off the {room or 'soffit'} ceiling"
        if room is not None:
            for ax in (0, 1):
                lines = _runner_gaps(room, ax)
                gap = min(abs(c[ax] - l) for l in lines) if lines else 1
                assert gap >= EL["dl"]["d"] / 2 + CEIL["cline"][0] / 2 - 1e-4, f"downlight at {c.x:.2f}, {c.y:.2f}: under a runner ({gap:.3f} m)"
        assert any((c - lc).length < 1e-4 and abs(lz1 - z0) < 1e-4 for _, lc, _, lz1 in lens), f"downlight at {c.x:.2f}, {c.y:.2f}: no lens"
    dev_boxes = 0
    for name in ("EL_sw", "EL_so", "EL_heater", "EL_ac", "EL_cu"):
        for vs, c, z0, z1 in isl(name):
            dev_boxes += abs(z1 - z0 - EL["box"][1]) < 1e-4
            P = Vector((c.x, c.y, (z0 + z1) / 2))
            for n_, ln, c0, c1, oz0, oz1 in OPENINGS:
                l = _wlines(WALL_LINES, OFFSET)[ln]
                ax = l["ax"]
                assert not (abs(P[1 - ax] - l["k"]) < 0.08 and c0 - 0.03 < P[ax] < c1 + 0.03 and oz0 - 0.05 < P.z < oz1 + 0.05), \
                    f"{name} at {P.x:.2f}, {P.y:.2f}: in opening {n_}"
    n_box = {}
    for name in ("EL_box24", "EL_box44"):
        sz = ib if name == "EL_box24" else pb
        for vs, c, z0, z1 in isl(name):
            ex = max(v.x for v in vs) - min(v.x for v in vs)
            ey = max(v.y for v in vs) - min(v.y for v in vs)
            if max(ex, ey, z1 - z0) < 0.03:   # a knockout disc
                continue
            assert abs(z1 - z0 - sz[1]) < 1e-4 and abs(max(ex, ey) - sz[0]) < 1e-3 and abs(min(ex, ey) - sz[2]) < 1e-3, f"{name}: not the TOP size"
            n_box[name] = n_box.get(name, 0) + 1
    for name, n in (("EL_Box2x4", dev_boxes), ("EL_box24", n_box.get("EL_box24", 0)), ("EL_box44", n_box.get("EL_box44", 0))):
        assert bpy.data.objects[name].data["count"] == n, f"{name}: count {bpy.data.objects[name].data['count']}, drawn {n}"
    for o in bpy.data.collections[C_ELEC].objects:
        if o.type == "CURVE":
            for cid, a, w in zip(o.data["circ"], o.data["amp"], o.data["wsz"]):
                for a_, w_ in zip(str(a).split("+"), w.split("+")) if a else ():   # each circuit of a shared conduit
                    assert {10: "1.5", 16: "2.5", 20: "4"}.get(int(a_)) == w_, f"{cid}: {a_} A breaker on THW {w_}"
    for C in CIRCUITS:   # every circuit carries its earth (grounded sockets / fittings)
        assert any(w.startswith("G") for w, _ in C["wires"]), f"{C['id']}: no earth wire"
    assert len(CIRCUITS) + 1 <= 14, "more circuits than the A14 holds"
    assert all(SHOWER[0] <= c.x <= SHOWER[1] for vs, c, z0, z1 in isl("EL_heater")), "heater outside the shower zone"
    return (f"electrical ok: {len(rings)} downlights · {bpy.data.objects['EL_sw'].data['count']} switches · "
            f"{bpy.data.objects['EL_so'].data['count']} sockets · {len(CIRCUITS)} circuits · " +
            " · ".join(f"{o.data['type']} {sum(o.data['lens']):.1f} m" for o in bpy.data.collections[C_ELEC].objects if o.type == "CURVE")
            + "\n" + selfcheck_conduit())
