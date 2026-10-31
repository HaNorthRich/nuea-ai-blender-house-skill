# ST14 doors · windows · aluminium (spec 31 ต.ค.; spec ../ST14_doors_windows_spec.md): the units in the openings the
# walls left (e42_walls OPENINGS / DOOR_CLEAR / UNIT), as their real pieces — door frames, leaves, hinges, handles;
# aluminium frames, sashes, glass, screens, louvre blades. Leaves and sashes closed. Exec after e42_elec (its device
# points drive the swing checks). The massing model's openings (e42_build) are hidden, not deleted.
C_UNITS, C_OLD_OPEN = "E42 ST14 Doors Windows", "E42 Openings"
# doors: 2" × 4" WPC frame — jamb face 32 mm (ECO DOOR: outer 870 − inner clear 806 = 2 × 32), 10 cm deep, centred on
# the wall; the leaf hangs in it 3 mm off the jambs and the head, 10 mm over the floor, on the swing side
DOOR = dict(jw=0.032, depth=0.10, t_leaf=0.035, inset=0.005, under=0.010, hinge=(0.003, 0.030, 0.10), hinges=3,
            per_pack=2, backset=0.06, handle_z=1.00,
            hinge_th="บานพับ HAFELE 4 × 3 นิ้ว (แพ็ก 2 ตัว · นับเป็นแพ็ก)")
DOORSET = {"D2": dict(leaf=(0.80, 2.00), leaf_t=("DR1", "ประตู uPVC MASTERWOOD 80 × 200 ซม. (เจาะลูกบิด)"),
                      frame_t=("DF1", "วงกบ WPC KASSA T1 80 × 200 ซม."), handle_t=("DH1", "มือจับก้านโยก YALE YLL-YK-ZN006")),
           "D4": dict(leaf=(0.70, 2.00), leaf_t=("DR2", "ประตู uPVC ECO DOOR W2 70 × 200 ซม. (เจาะลูกบิด)"),
                      frame_t=("DF2", "วงกบ WPC ECO DOOR TVWG-100 70 × 200 ซม."), handle_t=("DH2", "ลูกบิดห้องน้ำ HAFELE 489.93.271"))}
DOORSET["D3"] = DOORSET["D2"]   # the kitchen door: the bedrooms' (spec 31 ต.ค.)
# hinge end along the line, swing across it (into the room), and the switch the latch goes beside (the user confirmed 31 ต.ค.:
# latch by the switch, the leaf opens back against the nearest cross wall)
SWING = {"D2_Bed2": ("c1", -1, "SW_Bed2"), "D2_Bed1": ("c0", -1, "SW_Bed1"), "D4_Bath": ("c0", -1, "SW_Bath"),
         "D3_Kitchen": ("c0", -1, "SW_Kitchen")}
# aluminium: frame face fw, 10 cm deep (the listings); sashes sw × sd on tracks `track` apart; 5 mm glass; screens on
# the room side; louvre blades lapping blade_lap
ALU = dict(fw=0.030, depth=UNIT_DEPTH, sw=0.035, sd=0.025, track=0.035, lap=0.040, glass=0.005, scr_w=0.020, scr_d=0.010,
           blade_h=0.075, blade_lap=0.010)
ALUSET = {"W1": dict(kind="slide", panes=2, fixed=(), screens=(1,), type="AL1",
                     th="หน้าต่างบานเลื่อนอะลูมิเนียม 120 × 110 ซม. + มุ้ง สีดำ กระจกใส 5 มม."),
          "W2": dict(kind="awning", panes=1, screens=(0,), type="AL2",
                     th="หน้าต่างบานกระทุ้งอะลูมิเนียม 60 × 110 ซม. + มุ้ง สีดำ กระจกใส 5 มม."),
          "W3": dict(kind="slide", panes=2, fixed=(), screens=(1,), type="AL3",
                     th="หน้าต่างบานเลื่อนอะลูมิเนียม 120 × 90 ซม. + มุ้ง สีดำ กระจกใส 5 มม."),
          "W4": dict(kind="louvre", screens=(), type="AL4", th="หน้าต่างบานเกล็ดอะลูมิเนียม 60 × 50 ซม. สีดำ กระจกฝ้า"),
          "D1": dict(kind="slide", panes=4, fixed=(0, 3), screens=(1, 2), type="AL5",
                     th="ประตูบานเลื่อนอะลูมิเนียม 4 บาน 260 × 205 ซม. (2 เลื่อน 2 ตาย) + มุ้ง สีดำ กระจกใส 5 มม.")}


def _u_open(n):
    """An opening's line and its plaster clear in line coordinates: (l, u0, u1, z0, z1); doors from the floor."""
    _, ln, c0, c1, zb, zt = next(o for o in OPENINGS if o[0] == n)
    l, p_ = _wlines(WALL_LINES, OFFSET)[ln], WALL["pl"]
    return l, c0 + p_, c1 - p_, (FL_HOUSE if zb <= WALL_BASE + 1e-9 else zb + p_), zt - p_


def _u_box(l, u0, u1, v0, v1, z0, z1):
    """World box of (along, across from the wall centre, height) ranges on line l."""
    (a0, a1), (b0, b1) = sorted((u0, u1)), sorted((l["k"] + v0, l["k"] + v1))
    return (a0, b0, z0, a1, b1, z1) if l["ax"] == 0 else (b0, a0, z0, b1, a1, z1)


def _u_room_side(ln, swing=None):
    """+1 / −1 across the line toward the room side (exterior lines: away from OUTSIDE)."""
    return swing if swing is not None else -OUTSIDE.get(ln, 1)


def _u_door(c, n, mats):
    l, u0, u1, z0, z1 = _u_open(n)
    d, ds = DOOR, DOORSET[n[:2]]
    hinge_end, s, _ = SWING[n]
    g = UNIT_GAP
    f0, f1, ft = u0 + g, u1 - g, z1 - g
    hd = d["depth"] / 2
    jambs = [(f0, f0 + d["jw"]), (f1 - d["jw"], f1)]
    frame = [_u_box(l, a, b, -hd, hd, z0, ft) for a, b in jambs] + [_u_box(l, f0 + d["jw"], f1 - d["jw"], -hd, hd, ft - d["jw"], ft)]
    lw, lh = ds["leaf"]
    i0, i1 = f0 + d["jw"], f1 - d["jw"]
    assert i1 - i0 - lw >= 2 * d["hinge"][0] - 1e-9 and ft - d["jw"] - z0 - d["under"] - lh >= 0.002, f"{n}: the leaf does not fit its frame"   # (hinges fill the side gap)
    l0, l1 = (i0 + i1 - lw) / 2, (i0 + i1 + lw) / 2
    v_out = s * (hd - d["inset"])
    v_in = v_out - s * d["t_leaf"]
    lz0 = z0 + d["under"]
    leaf = [_u_box(l, l0, l1, v_in, v_out, lz0, lz0 + lh)]
    he, le = (l0, l1) if hinge_end == "c0" else (l1, l0)   # hinge edge, latch edge
    hu = (he + (i0 if hinge_end == "c0" else i1)) / 2
    ht, hwv, hh = d["hinge"]
    vm = (v_in + v_out) / 2
    zs = [lz0 + 0.25, lz0 + lh / 2, lz0 + lh - 0.25]
    hinges = [_u_box(l, hu - ht / 2, hu + ht / 2, vm - hwv / 2, vm + hwv / 2, z - hh / 2, z + hh / 2) for z in zs]
    hu_ = le - d["backset"] if le > he else le + d["backset"]
    zh = z0 + d["handle_z"]
    handle = []
    for side in (v_out, v_in):   # rose + lever (or knob) on both faces
        out_ = side + (s if side == v_out else -s) * 0.010
        handle.append(_u_box(l, hu_ - 0.025, hu_ + 0.025, *sorted((side, out_)), zh - 0.025, zh + 0.025))
        tip = out_ + (s if side == v_out else -s) * 0.050
        if ds["handle_t"][0] == "DH1":   # lever toward the hinge, 12 cm
            a, b = sorted((hu_, hu_ + (0.12 if he > le else -0.12)))
            handle.append(_u_box(l, a, b, *sorted((out_, tip)), zh - 0.009, zh + 0.009))
        else:
            handle.append(_u_box(l, hu_ - 0.0275, hu_ + 0.0275, *sorted((out_, tip)), zh - 0.0275, zh + 0.0275))
    lt, ft_, ht_ = ds["leaf_t"], ds["frame_t"], ds["handle_t"]
    _put(c, f"{n}_Frame", frame, mats["wpc"], element="piece", type=ft_[0], th=ft_[1], opening=n)
    _put(c, f"{n}_Leaf", leaf, mats["upvc"], element="piece", type=lt[0], th=lt[1], opening=n, hinge=hinge_end, swing=s)
    _put(c, f"{n}_Handle", handle, mats["steel"], element="piece", type=ht_[0], th=ht_[1], opening=n)
    return hinges


def _u_rect_frame(l, a0, a1, z0, z1, w, v0, v1):
    """Four members w wide round [a0, a1] × [z0, z1], v0..v1 deep (head and sill run through)."""
    return [_u_box(l, a0, a1, v0, v1, z0, z0 + w), _u_box(l, a0, a1, v0, v1, z1 - w, z1),
            _u_box(l, a0, a0 + w, v0, v1, z0 + w, z1 - w), _u_box(l, a1 - w, a1, v0, v1, z0 + w, z1 - w)]


def _u_alu(c, n, mats):
    l, u0, u1, z0, z1 = _u_open(n)
    A, S = ALU, ALUSET[n[:2]]
    w_, h_ = UNIT[n[:2]]   # the product, centred in the clear (D1 on the floor)
    f0, f1 = (u0 + u1 - w_) / 2, (u0 + u1 + w_) / 2
    fz0 = z0 if z0 == FL_HOUSE else (z0 + z1 - h_) / 2
    fz1 = fz0 + h_
    hd = A["depth"] / 2
    room = _u_room_side(next(o for o in OPENINGS if o[0] == n)[1])
    frame = _u_rect_frame(l, f0, f1, fz0, fz1, A["fw"], -hd, hd)
    i0, i1, iz0, iz1 = f0 + A["fw"], f1 - A["fw"], fz0 + A["fw"], fz1 - A["fw"]
    sash, glass, screen = [], [], []

    def pane(a0, a1, vc):   # a sash round its glass, centred vc across
        sash.extend(_u_rect_frame(l, a0, a1, iz0, iz1, A["sw"], vc - A["sd"] / 2, vc + A["sd"] / 2))
        glass.append(_u_box(l, a0 + A["sw"], a1 - A["sw"], vc - A["glass"] / 2, vc + A["glass"] / 2, iz0 + A["sw"], iz1 - A["sw"]))
    spans = []
    if S["kind"] == "slide":
        k = S["panes"]
        tracks = [(1 if i in S["fixed"] else 0) if S["fixed"] else i % 2 for i in range(k)]   # 0 room side; fixed outside
        laps = [A["lap"] if tracks[i] != tracks[i + 1] else 0.0 for i in range(k - 1)]   # sliders on one track butt
        pw = (i1 - i0 + sum(laps)) / k
        a0 = i0
        for i in range(k):
            pane(a0, a0 + pw, room * (0.5 - tracks[i]) * A["track"])
            spans.append((a0, a0 + pw))
            a0 += pw - (laps[i] if i < k - 1 else 0.0)
        assert abs(spans[-1][1] - i1) < 1e-9, f"{n}: panes do not close the frame"
    elif S["kind"] == "awning":
        pane(i0, i1, -room * A["track"] / 2)
        spans.append((i0, i1))
    else:   # louvres: carriers on the jambs, blades lapping down the opening
        cw = 0.012
        sash += [_u_box(l, i0, i0 + cw, -0.015, 0.015, iz0, iz1), _u_box(l, i1 - cw, i1, -0.015, 0.015, iz0, iz1)]
        nb = math.ceil((iz1 - iz0 - A["blade_lap"]) / (A["blade_h"] - A["blade_lap"]) - 1e-9)
        assert nb >= 2, f"{n}: too short for louvres"
        step = (iz1 - iz0 - A["blade_h"]) / (nb - 1)
        for i in range(nb):
            vc = (i % 2 - 0.5) * 2 * A["glass"]   # alternate faces so the laps clear
            glass.append(_u_box(l, i0 + cw, i1 - cw, vc - A["glass"] / 2, vc + A["glass"] / 2, iz0 + i * step, iz0 + i * step + A["blade_h"]))
    vs = room * (A["track"] + A["scr_d"] / 2 + 0.002)   # screens one track in from the sashes, on the room side
    for i in S["screens"]:
        a0, a1 = spans[i]
        screen += _u_rect_frame(l, a0, a1, iz0, iz1, A["scr_w"], vs - A["scr_d"] / 2, vs + A["scr_d"] / 2)
        screen.append(_u_box(l, a0 + A["scr_w"], a1 - A["scr_w"], vs - 0.0005, vs + 0.0005, iz0 + A["scr_w"], iz1 - A["scr_w"]))
    _put(c, f"{n}_Frame", frame, mats["alu"], element="piece", type=S["type"], th=S["th"], opening=n)
    _put(c, f"{n}_Sashes", sash, mats["alu"], opening=n)
    _put(c, f"{n}_Glass", glass, mats["frosted" if S["kind"] == "louvre" else "glass"], opening=n, panes=len(glass))
    if screen:
        _put(c, f"{n}_Screens", screen, mats["screen"], opening=n)
    return []


# glass: 5 mm float, clear (W1–W3, D1) or frosted (W4) — a thin refracting slab; EEVEE refracts it only with ray
# tracing on (set here), Cycles as is; see-through in the solid viewport too
GLASS = dict(clear=((0.94, 0.97, 0.98), 0.0), frosted=((0.93, 0.95, 0.96), 0.30), ior=1.52, solid_alpha=0.25,
             screen_alpha=0.35)   # (insect mesh: you see through it)


def _u_glass(name, spec):
    """The glass material, set every build (mat() keeps an existing material as it was)."""
    rgb, rough = spec
    m = mat(name, rgb, rough, transmission=1.0)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for k, v in (("Base Color", (*rgb, 1)), ("Roughness", rough), ("Transmission Weight", 1.0), ("IOR", GLASS["ior"])):
        b.inputs[k].default_value = v
    m.use_raytrace_refraction = True
    m.thickness_mode = "SLAB"
    m.diffuse_color = (*rgb, GLASS["solid_alpha"])
    return m


def _u_screen(name):
    """Insect mesh: dark and see-through (alpha), set every build. The screens' frames share it (shortcut: one material)."""
    m = mat(name, (0.10, 0.10, 0.10), 0.8)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Alpha"].default_value = GLASS["screen_alpha"]
    m.diffuse_color = (0.10, 0.10, 0.10, GLASS["screen_alpha"])
    return m


def build_units():
    """Every opening's unit; the massing model's openings hidden; → {type: count}."""
    c = _clear(C_UNITS)
    mats = dict(wpc=mat("M_WPC_Frame", (0.28, 0.18, 0.12), 0.6),   # (colour assumed)
                upvc=mat("M_uPVC_Door", (0.90, 0.89, 0.86), 0.5),   # (colour assumed)
                steel=mat("M_Door_Steel", (0.70, 0.70, 0.72), 0.3, metal=1.0),
                alu=mat("M_Alu_Black", (0.03, 0.03, 0.03), 0.35, metal=0.8),
                glass=_u_glass("M_Glass_Clear", GLASS["clear"]), frosted=_u_glass("M_Glass_Frosted", GLASS["frosted"]),
                screen=_u_screen("M_Screen"))
    hinges = []
    for n, *_ in OPENINGS:
        hinges += (_u_door if n[:2] in DOORSET else _u_alu)(c, n, mats)
    _put(c, "DR_Hinges", hinges, mats["steel"], element="piece", type="DH3", th=DOOR["hinge_th"], hinges=len(hinges),
         count=math.ceil(len(hinges) / DOOR["per_pack"]))   # bought for the house in packs (not per door)
    lc = _u_layer(C_OLD_OPEN)
    if lc:
        lc.exclude = True
    bpy.context.scene.eevee.use_raytracing = True   # (the glass refracts in EEVEE)
    from collections import Counter
    out = Counter()
    for o in c.objects:
        if o.data.get("element"):
            out[o.data["type"]] += o.data.get("count", 1)
    return dict(out)


def _u_layer(name, lc=None):
    lc = lc or bpy.context.view_layer.layer_collection
    if lc.name == name:
        return lc
    return next((r for ch in lc.children if (r := _u_layer(name, ch))), None)


def _u_measured(n, sol):
    """An opening's plaster clear measured in the built wall (line coords): u0, u1, z0 (doors: the floor), z1."""
    _, ln, c0, c1, zb, zt = next(o for o in OPENINGS if o[0] == n)
    l = _wlines(WALL_LINES, OFFSET)[ln]
    ax, mid, zm = l["ax"], (c0 + c1) / 2, (zb + zt) / 2
    bs = [b for b in sol if b[1 - ax] < l["k"] < b[4 - ax] and b[ax] < c1 + 0.5 and b[ax + 3] > c0 - 0.5]
    side = [b for b in bs if b[2] < zm < b[5]]
    u0 = max(b[ax + 3] for b in side if b[ax + 3] <= mid)
    u1 = min(b[ax] for b in side if b[ax] >= mid)
    over = [b for b in bs if b[ax] < mid < b[ax + 3]]
    z1 = min(b[2] for b in over if b[2] > zm)
    z0 = FL_HOUSE if zb <= WALL_BASE + 1e-9 else max(b[5] for b in over if b[5] < zm)
    return l, u0, u1, z0, z1


def _u_extent(o, l):
    bm = _world_bm(o)
    vs = [v.co for v in bm.verts]
    bm.free()
    ax = l["ax"]
    return (min(v[ax] for v in vs), max(v[ax] for v in vs), min(v.z for v in vs), max(v.z for v in vs),
            min(v[1 - ax] for v in vs) - l["k"], max(v[1 - ax] for v in vs) - l["k"])


def selfcheck_units():
    """ST14 from the model: one unit per opening, each frame snug in the plaster clear measured in the wall (UNIT_GAP
    all round, on the floor for doors), nothing of it in a wall, tile, paint or electrical piece, door leaves hung in
    their frames with the latch by the room's switch and a clear swing, glass per unit, the take-off counts; the
    massing openings hidden."""
    from mathutils.bvhtree import BVHTree
    from collections import Counter
    cu = bpy.data.collections[C_UNITS]
    objs = {o.name: o for o in cu.objects}
    ops = [o[0] for o in OPENINGS]
    fl = [o for o in objs.values() if o.name.endswith("_Frame")]
    frames = {o.data["opening"]: o for o in fl}
    assert sorted(frames) == sorted(ops) and len(fl) == len(ops), f"units: frames for {sorted(frames)}, openings {sorted(ops)}"
    sol = [b for (on, _), b in _solids([C_WALL]).items() if bpy.data.objects[on].data.get("element") in ("masonry", "concrete", "plaster")]
    g = UNIT_GAP
    for n in ops:
        l, u0, u1, z0, z1 = _u_measured(n, sol)
        a0, a1, e0, e1, v0, v1 = _u_extent(frames[n], l)
        assert abs(a0 - (u0 + g)) < 1e-4 and abs(a1 - (u1 - g)) < 1e-4, f"{n}: frame {a0:.4f}–{a1:.4f} in a clear {u0:.4f}–{u1:.4f}"
        zg = 0.0 if n[0] == "D" else g   # doors (D1 too) stand on the floor
        assert abs(e0 - (z0 + zg)) < 1e-4 and abs(e1 - (z1 - g)) < 1e-4, f"{n}: frame {e0:.4f}–{e1:.4f} high, clear {z0:.4f}–{z1:.4f}"
        if n[:2] in ALUSET:
            w_, h_ = UNIT[n[:2]]
            assert abs(a1 - a0 - w_) < 1e-4 and abs(e1 - e0 - h_) < 1e-4, f"{n}: frame {a1 - a0:.3f} × {e1 - e0:.3f}, unit {w_} × {h_}"
        assert abs(v0 + v1) < 1e-4, f"{n}: frame not centred in the wall"
        for o in objs.values():   # every piece of the unit inside the clear (along and up)
            if o.data.get("opening") == n:
                b = _u_extent(o, l)
                assert u0 - 1e-6 < b[0] and b[1] < u1 + 1e-6 and z0 - 1e-6 < b[2] and b[3] < z1 + 1e-6, f"{o.name}: outside its opening"
    # nothing of a unit in another stage's piece: the units' boxes 0.1 mm in (standing on a floor is contact) against
    # every mesh and curve (conduit, flex: evaluated with their bevel) — triangles crossing (BVH) or a piece wholly
    # inside a unit (its vertices)
    others = [cn for cn in (C_WALL, C_TILE, C_STEP, C_PAINT, C_FINISH, C_COAT2, C_ELEC, C_CEIL) if cn in bpy.data.collections]
    ub, bm_u = [], bmesh.new()
    for o in cu.objects:
        bm = _world_bm(o)
        for b in _obj_boxes(bm, o.name):
            q = tuple(b[i] + 1e-4 for i in range(3)) + tuple(b[i] - 1e-4 for i in range(3, 6))
            ub.append(q)
            for v in bmesh.ops.create_cube(bm_u, size=1.0)["verts"]:
                v.co = tuple(q[i] if v.co[i] < 0 else q[i + 3] for i in range(3))
        bm.free()
    t_units = BVHTree.FromBMesh(bm_u)
    lo = [min(b[i] for b in ub) for i in range(3)]
    hi = [max(b[i + 3] for b in ub) for i in range(3)]
    for cn in others:
        for o in bpy.data.collections[cn].objects:   # (not all_objects: a stale cache after a rebuild)
            if o.type not in ("MESH", "CURVE"):
                continue
            bm = _world_bm(o)
            hits = t_units.overlap(BVHTree.FromBMesh(bm))
            assert not hits, f"a unit runs into {o.name} ({cn}, {len(hits)} faces)"
            for v in bm.verts:
                p = v.co
                if all(lo[i] < p[i] < hi[i] for i in range(3)):
                    assert not any(all(b[i] < p[i] < b[i + 3] for i in range(3)) for b in ub), f"{o.name} inside a unit at {p.x:.3f}, {p.y:.3f}, {p.z:.3f}"
            bm.free()
    # doors: on the tiled floor — the highest floor tile under each jamb's foot is the frame's bottom (measured off
    # the tile boxes: a ray down meets the frame's own bottom on the tile face), leaf in its frame, latch by the
    # switch, the swing (the leaf's swing face and its handle) clear of walls, wall tiles and devices
    ftb = [b for t_ in ("FT_floor_Tiles", "FT_bath_Tiles", "FT_porch_Tiles") if t_ in bpy.data.objects
           for b in _obj_boxes(_world_bm(bpy.data.objects[t_]), t_)]
    for n in ops:
        if n[0] == "D":
            l = _wlines(WALL_LINES, OFFSET)[next(o for o in OPENINGS if o[0] == n)[1]]
            a0, a1, e0, e1, v0, v1 = _u_extent(frames[n], l)
            jw = DOOR["jw"] if n[:2] in DOORSET else ALU["fw"]
            for fa, fb in ((a0, a0 + jw), (a1 - jw, a1)):
                foot = _u_box(l, fa, fb, v0, v1, 0, 0)
                under = [b[5] for b in ftb if b[0] < foot[3] and foot[0] < b[3] and b[1] < foot[4] and foot[1] < b[4]]
                assert under and abs(max(under) - e0) < 1e-4, f"{n}: a jamb foot at {e0:.4f}, the tiles under it at {max(under) if under else None}"
    pts = _points()
    walls2d = [b for b in sol if b[2] < FL_HOUSE + 1.0 < b[5]]
    walls2d += [b for b in _obj_boxes(_world_bm(bpy.data.objects["FT_wall_Tiles"]), "FT_wall_Tiles") if b[2] < FL_HOUSE + 1.0 < b[5]]
    for n, (he, s, sw) in SWING.items():
        assert f"{n}_Leaf" in objs and f"{n}_Handle" in objs, f"{n}: no leaf / handle"
        lf = objs[f"{n}_Leaf"]
        assert lf.data["hinge"] == he and lf.data["swing"] == s, f"{n}: hung {lf.data['hinge']} / {lf.data['swing']}"
        l, u0, u1, z0, z1 = _u_measured(n, sol)
        a0, a1, e0, e1, v0, v1 = _u_extent(lf, l)
        assert v0 * s > 0 and v1 * s > 0, f"{n}: the leaf is not on its swing side"
        p = pts[sw]["p"]
        su = p[l["ax"]]
        hinge_u, latch_u = (a0, a1) if he == "c0" else (a1, a0)
        assert abs(su - latch_u) < abs(su - hinge_u), f"{n}: {sw} is on the hinge side"
        w = a1 - a0
        vm, dl, tf = (v0 + v1) / 2, (1 if latch_u > hinge_u else -1), (v1 - v0) / 2
        hb_n = [b for b in _obj_boxes(_world_bm(objs["DR_Hinges"]), "DR_Hinges")   # this door's hinges (pooled for the take-off)
                if u0 < (b[l["ax"]] + b[l["ax"] + 3]) / 2 < u1 and abs((b[1 - l["ax"]] + b[4 - l["ax"]]) / 2 - l["k"]) < 0.06]
        assert len(hb_n) == DOOR["hinges"], f"{n}: {len(hb_n)} hinges"
        assert all(abs((b[l["ax"]] + b[l["ax"] + 3]) / 2 - (hinge_u - dl * DOOR["hinge"][0] / 2)) < 1e-4 for b in hb_n), f"{n}: a hinge off the hinge edge"
        for pid, q in pts.items():   # a device inside the quarter disc the leaf sweeps (exact, 5 cm margin)
            if q["kind"] in ("sw", "so", "heater", "cu") and q["p"].z < e1:
                du, dv = (q["p"][l["ax"]] - hinge_u) * dl, (q["p"][1 - l["ax"]] - l["k"] - vm) * s
                assert not (du > -0.05 and dv > -0.05 and math.hypot(max(du, 0), max(dv, 0)) < w + 0.05), f"{n}: {pid} in the swing"
        for deg in range(0, 91, 5):   # as it opens, in plan: its swing face, and the handle 6 cm off it near the latch
            t = math.radians(deg)
            d_ = (dl * math.cos(t), s * math.sin(t))   # along the leaf (u, v), and the swing face's normal
            nf = (-dl * math.sin(t), s * math.cos(t))
            probes = [(w * f_, tf) for f_ in (0.1 * i for i in range(1, 11))] + [(w - DOOR["backset"], tf + 0.06)]
            for along, off in probes:
                du = d_[0] * along + nf[0] * off
                dv = vm + d_[1] * along + nf[1] * off
                q = _u_box(l, hinge_u + du, hinge_u + du, dv, dv, 0, 0)[:2]
                assert not any(b[0] + 1e-4 < q[0] < b[3] - 1e-4 and b[1] + 1e-4 < q[1] < b[4] - 1e-4 for b in walls2d), \
                    f"{n}: the leaf hits a wall opening {deg}° at {q[0]:.2f}, {q[1]:.2f}"
    # glass: panes as the spec, frosted only in the bath
    for n in ops:
        if n[:2] in ALUSET:
            assert f"{n}_Glass" in objs and f"{n}_Sashes" in objs, f"{n}: no glass / sashes"
            gl = objs[f"{n}_Glass"]
            S = ALUSET[n[:2]]
            k = len(_islands(gl))
            assert k == gl.data["panes"] and (S["kind"] == "louvre" or k == S["panes"]), f"{n}: {k} panes"
            gm = gl.material_slots[0].material
            assert gm.name == ("M_Glass_Frosted" if S["kind"] == "louvre" else "M_Glass_Clear"), f"{n}: glass"
            b_ = next(x for x in gm.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
            rough = GLASS["frosted" if S["kind"] == "louvre" else "clear"][1]
            assert b_.inputs["Transmission Weight"].default_value == 1.0 and abs(b_.inputs["IOR"].default_value - GLASS["ior"]) < 1e-6 \
                and abs(b_.inputs["Roughness"].default_value - rough) < 1e-6 and gm.use_raytrace_refraction and gm.thickness_mode == "SLAB" \
                and gm.diffuse_color[3] < 1, f"{n}: {gm.name} is not glass"
            assert (f"{n}_Screens" in objs) == bool(S["screens"]), f"{n}: screens"
            if S["kind"] == "louvre":
                continue
            # across the wall: panes from their sashes (4 boxes each), glass in its sash, sliders and screens on the
            # room side, fixed panes outside, overlapping panes on tracks that clear each other
            l = _wlines(WALL_LINES, OFFSET)[next(o for o in OPENINGS if o[0] == n)[1]]
            ax, room = l["ax"], _u_room_side(next(o for o in OPENINGS if o[0] == n)[1])
            sb = _obj_boxes(_world_bm(objs[f"{n}_Sashes"]), f"{n}_Sashes")
            panes = [(min(b[ax] for b in sb[i:i + 4]), max(b[ax + 3] for b in sb[i:i + 4]),
                      sum(b[1 - ax] + b[4 - ax] for b in sb[i:i + 4]) / 8 - l["k"]) for i in range(0, len(sb), 4)]
            gb = _obj_boxes(_world_bm(gl), gl.name)
            assert len(panes) == len(gb) and all(abs((g_[1 - ax] + g_[4 - ax]) / 2 - l["k"] - p_[2]) < 1e-6 for g_, p_ in zip(gb, panes)), f"{n}: glass off its sash"
            for i, p_ in enumerate(panes):
                if S["kind"] == "awning":
                    assert p_[2] * room <= 1e-9, f"{n}: the awning sash on the room side"
                elif S["fixed"]:
                    assert (p_[2] * room < 0) == (i in S["fixed"]), f"{n}: pane {i} on the wrong track"
                for q_ in panes[i + 1:]:
                    ov = min(p_[1], q_[1]) - max(p_[0], q_[0])
                    assert ov < 1e-6 or abs(p_[2] - q_[2]) >= ALU["sd"] - 1e-6, f"{n}: two panes in one another"
            for a_, b_ in zip(panes, panes[1:]):   # meeting panes: a lap across tracks, a butt on one
                ov = min(a_[1], b_[1]) - max(a_[0], b_[0])
                assert abs(ov - (ALU["lap"] if abs(a_[2] - b_[2]) > 1e-6 else 0.0)) < 1e-6, f"{n}: panes meet {ov * 1000:.0f} mm"
            if S["screens"]:
                sm = objs[f"{n}_Screens"].material_slots[0].material
                assert next(x for x in sm.node_tree.nodes if x.type == "BSDF_PRINCIPLED").inputs["Alpha"].default_value < 1, f"{n}: the screen is opaque"
                scr = _obj_boxes(_world_bm(objs[f"{n}_Screens"]), f"{n}_Screens")
                assert all(((b[1 - ax] + b[4 - ax]) / 2 - l["k"]) * room > 0 for b in scr), f"{n}: a screen on the outside"
                spans = {(round(min(b[ax] for b in scr[i:i + 5]), 6), round(max(b[ax + 3] for b in scr[i:i + 5]), 6)) for i in range(0, len(scr), 5)}
                want_s = {(round(panes[i][0], 6), round(panes[i][1], 6)) for i in S["screens"]}
                assert spans == want_s, f"{n}: screens over {sorted(spans)}, sliders {sorted(want_s)}"
    # take-off: counts against the openings, products against the spec
    want = Counter()
    for n in ops:
        if n[:2] in DOORSET:
            ds = DOORSET[n[:2]]
            want[ds["leaf_t"]] += 1
            want[ds["frame_t"]] += 1
            want[ds["handle_t"]] += 1
        else:
            want[(ALUSET[n[:2]]["type"], ALUSET[n[:2]]["th"])] += 1
    nd = sum(1 for n in ops if n[:2] in DOORSET)
    hb = _obj_boxes(_world_bm(objs["DR_Hinges"]), "DR_Hinges")
    assert len(hb) == DOOR["hinges"] * nd == objs["DR_Hinges"].data["hinges"], f"{len(hb)} hinges for {nd} doors"
    want[("DH3", DOOR["hinge_th"])] = math.ceil(DOOR["hinges"] * nd / DOOR["per_pack"])   # packs for the house
    got = {(tn, x["th"]): x["count"] for (el, tn), x in qto(C_UNITS).items() if el == "piece"}
    assert got == dict(want), f"take-off {got} ≠ {dict(want)}"
    lc = _u_layer(C_OLD_OPEN)
    assert lc is None or lc.exclude, "the massing openings still show"
    assert bpy.context.scene.eevee.use_raytracing, "EEVEE ray tracing off: the glass will not refract"
    return "units ok: " + " · ".join(f"{tn} {k}" for (tn, _), k in sorted(got.items()))
