# E42 ST12 conduit, part 3 of 3: _route_once — one routing pass of every circuit (spec ../ST12_conduit_spec.md).
# After e42_conduit.py (its tables) and e42_conduit_geom.py.
import bisect
import math
from mathutils import Vector


def _route_once(pts):
    """ST12 conduit on the wall faces (spec ../ST12_conduit_spec.md). Every CU circuit leaves the CU top up its chase,
    bends level in the chase (lower levels further from the CU middle, so no rise crosses another's bend), sets out
    onto the wall and runs at its own height: counter-clockwise round the living room for everything that leaves it
    (teeing off into Bed1 / bath / Bed2 on the way), clockwise for living-room points the other side of the CU (a
    second conduit from the CU). Boxes sit on the wall on the run's height, lid to the room, with room below for their
    drop (chased into the wall) or flex. → dict(runs, flex, boxes, wire, chase, pieces, hubs, …) for build_elec()."""
    rooms = ("Living", "Bed1", "Bed2", "Bath")
    V = _voids()
    lines = {r: _Line(r, "3/4") for r in rooms}   # (corners at the 3/4" radius: every size may follow them)
    lev = {r: _Levels(r, lines[r]) for r in rooms}
    CD["_last_levels"] = lev   # (inspection after a failed run)
    xs = {k: _xing(lines, *k) for k in XS}   # keyed (from, to, way)
    out = dict(runs={}, flex=[], boxes=[], wire={}, bends={}, cross=0, vlen={}, chase=[], skipped=[], deg={}, fill={}, pieces=[])
    ib, pb = EL["box24"]["size"], EL["box44"]["size"]
    r0, rc = CD["rmin"]["3/4"], EL["conduit"]["1/2"] / 2   # (rc: a 1/2"'s; a 3/4" route books its own, RC_OF)
    Lv = lines["Living"]
    cu = pts["CU"]
    s_cu = Lv.s_of((cu["p"].x, cu["p"].y))
    room_of = lambda pid: {"Soffit": "Eave"}.get(pts[pid]["room"], pts[pid]["room"])
    zc_room = {r: V[r][2] for r in rooms}
    n_in = lambda line, s: (lambda a, b: Vector((-(b[1] - a[1]), b[0] - a[0], 0)).normalized())(line.at(s - 0.005), line.at(s + 0.005))

    fixed = {r: [lines[r].s_of((pts[p]["p"].x, pts[p]["p"].y)) for p in pts
                 if pts[p]["kind"] not in ("dl", "cu") and room_of(p) == r] for r in rooms}
    TR = 0.75   # along the wall, kept for one plaster ↔ wall-plate transition
    LEAD = CD["rmin"]["3/4"] * math.tan(math.radians(CD["off_deg"]) / 2) + 0.01   # a climb's straight lead-in before its first bend
    # spec 30 ต.ค.: a wall device's box is looped (no box over the ceiling): the run turns a_l into the wall, then bends
    # 90° down (heading into the wall as it turns) into a chase straight down to the device box top; a second conduit
    # comes back up beside it and out the same way, mirrored
    LK = 0.0125   # the two conduits into a 2×4 box top, this far either side of its centre
    lat_l = CD["dc"] + 0.02   # face run → chase
    def geo(size):   # (bend radius, conduit radius, loop turn a_l, its leg AB, loop reach) for a conduit size
        r_ = CD["rmin"]["3/4"]   # (every conduit bends at the 3/4" radius: ≥ the 1/2" one, and a 3/4" may take any route)
        lo_, hi_ = 0.01, math.radians(45.0)   # the steepest turn whose leg still holds both bends: lat/sin a ≥ r·(tan(a/2) + 1)
        for _ in range(40):
            lo_, hi_ = ((lo_ + hi_) / 2, hi_) if lat_l / math.sin((lo_ + hi_) / 2) >= r_ * (math.tan((lo_ + hi_) / 4) + 1) else (lo_, (lo_ + hi_) / 2)
        ab = lat_l / math.sin(lo_)   # the leg from the turn on the face to the top of the chase
        return r_, EL["conduit"][size] / 2, lo_, ab, LK + ab * math.cos(lo_) + r_ * math.tan(lo_ / 2) + 0.01   # (loop: device s → straight again)
    GEO = {sz: geo(sz) for sz in ("1/2", "3/4")}
    _, _, a_l, AB, LOOP = GEO["1/2"]
    DIP = 0.015   # the down bend dips this far before it is behind the face
    # spec 31 ต.ค.: every wall device has a junction box (TOP 4×4) on the run over the ceiling, behind it along the run:
    # the run in at one end, on out of the far end; the drop out of the far end's other knockout (2·KO off the run),
    # diving into the wall as a loop's down leg did, straight down its chase onto the device. The wires loop through.
    JB = LOOP + 0.02 + pb[0]   # how far behind the device its junction box starts (dive, a 2 cm lead out of the box, the box)
    reach = lambda room: LOOP if room in CD["jb_off"] else JB   # a wall device's reach along its wall: its loop, or its junction box and drop
    ext = lambda pid: (pb[0] / 2 + 0.02 if pid.startswith("HUB") else ib[0] / 2) if pid not in pts or pts[pid]["kind"] == "dl" else reach(room_of(pid))   # how far along the wall a box / drop / hub reaches
    HOME = 0.55   # a CU home run is on the wall face by s_in + this at most (its chase bend 0.012 + dz ≤ 0.16, set-out r0 + 0.23, leg 0.10): no climb before
    SLOT = CD["slot"]
    PL = {}
    for r_ in rooms:   # each room's wall-plate band: its line and its heights (the user: the passing runs ride there)
        ln_, (z0_, z1_) = _plate_line(r_)
        PL[r_] = (ln_, _Levels(r_, ln_, z0=z0_, top=z1_))
    PLK = {r_: [_plate_line(r_, k)[0] for k in range(4)] for r_ in rooms}   # (an offset corner would bend tighter than rmin)
    HUBS = []   # shared pull boxes (spec 30 ต.ค.): (room, band | plate, s, its line, z centre) — booked first, runs pass through
    for room_, kind_, s_, *h_own in CD.get("hubs", []):
        h_own = h_own[0] if h_own else None
        if kind_ == "plate":   # a 2×4 pull box for the one conduit up on the plate there: its stretch of the band is its own
            pln_, plv_ = PL[room_]
            plv_.used.append((plv_.z0, plv_.top, ccw(s_ - ib[0] / 2 - 0.05, s_ + ib[0] / 2 + 0.05, 1), "pbox", h_own))
            HUBS.append((room_, kind_, s_, PLK[room_][0], None))
            continue
        ln_, lv_ = lines[room_], lev[room_]
        zc_ = min(lv_.top - CD["gap"] - pb[1] / 2 - 0.01, 3.37)
        lv_.used.append((zc_ - pb[1] / 2, zc_ + pb[1] / 2, ccw(s_ - pb[0] / 2 - 0.02, s_ + pb[0] / 2 + 0.02, 1), "hub", "HUB"))
        HUBS.append((room_, kind_, s_, ln_, zc_))
    th30 = math.radians(CD["off_deg"])
    t30 = r0 * math.tan(th30 / 2)

    def both_straight(room, s, length, sg):   # the plaster line and the plate line both straight over s → s + sg·length
        line, pln = lines[room], PL[room][0]    # (a climb in front of a box lid: the bands' front / box check, by height)
        for k in range(int(length / 0.05) + 1):
            q = s + sg * 0.05 * k
            if not _straight_at(line, q, 0.03) or not _straight_at(pln, pln.s_of(line.at(q)), 0.03):
                return False
        return True

    def plate_lat(room, s):   # how far the wall plate's run line stands proud (+) of the plaster's at s
        line, pln = lines[room], PL[room][0]
        nin = n_in(line, s)
        P, Q = line.at(s), pln.at(pln.s_of(line.at(s)))
        return (Q[0] - P[0]) * nin.x + (Q[1] - P[1]) * nin.y

    def plate_gaps(room, ev, s_c, sg, back, shift=0.0, shift_dn=None):   # stretches over 2 m without a box: [(before event j, s up, s down)]
        Lv = lines[room]
        out_, prev = [], s_c
        for j, (span, s, kind, ident) in enumerate(ev):
            nxt = s - sg * ((ext(ident) + 0.05) if kind in ("dev", "hub") else (pb[0] + 0.15 + back))
            behind = Lv.span(prev, nxt, sg) > Lv.span(prev, s, sg)   # the reaches overlap: nxt lies behind prev
            if not behind and Lv.span(prev, nxt, sg) > 2.0:
                su = prev + sg * (0.10 + shift)
                while not both_straight(room, su - sg * LEAD, TR + LEAD, sg) and Lv.span(su, nxt, sg) > 2 * TR:
                    su += sg * 0.02
                sd = nxt - sg * (0.10 + (shift if shift_dn is None else shift_dn))
                while not both_straight(room, sd - sg * TR, TR + LEAD, sg) and Lv.span(su, sd, sg) > 2 * TR:
                    sd -= sg * 0.02
                if Lv.span(su, sd, sg) > 2 * TR + 0.30:
                    out_.append((j, su, sd))
            prev = s + sg * ((ext(ident) + 0.02) if kind in ("dev", "hub") else 0.10)
        return out_


    def dl_s(room, pid, after=None):   # a downlight's box: the wall nearest the fitting, 0.3 m clear of every switch / socket
        line = lines[room]                # box (after = (s, sg, d): at least d on from s)
        s0 = line.s_of((pts[pid]["p"].x, pts[pid]["p"].y))
        d_ = pts[pid]["p"]
        for k in range(0, 300):
            for s in ((s0 + k * 0.01, s0 - k * 0.01) if k else (s0,)):
                if all(min((s - f) % line.L, (f - s) % line.L) > (0.30 if room in CD["jb_off"] else JB + ib[0] / 2 + 0.02) for f in fixed[room]) and _straight_at(line, s, ib[0] / 2 + 0.01) \
                        and (room != "Living" or min((s - s_cu) % line.L, (s_cu - s) % line.L) > HOME + 0.25 + ib[0] / 2) \
                        and min(abs(line.at(s - 0.06)[k] - line.at(s + 0.06)[k]) for k in (0, 1)) < 1e-6 \
                        and (pid not in CD["dl_face"] or abs(line.at(s)[CD["dl_face"][pid] % 2] - (V[room][0][CD["dl_face"][pid]]
                                                             + (CD["dc"] if CD["dl_face"][pid] < 2 else -CD["dc"]))) < 0.01) \
                        and (after is None or line.span(after[0], s, after[1]) >= after[2]) \
                        and math.dist(line.at(s), (d_.x, d_.y)) + 0.25 <= EL["flex"]["max"]:   # the flex still reaches
                    return s
        raise AssertionError(f"{room}: no place for {pid}'s box")

    def box_s(line, s0, half, slide):   # nearest place to s0 where a box lies flat on a straight
        for k in range(0, int(slide / 0.005) + 1):
            for s in ((s0 + k * 0.005, s0 - k * 0.005) if k else (s0,)):
                if _straight_at(line, s, half + 0.01):
                    return s
        raise AssertionError(f"{line.room}: no straight for a box near s {s0:.2f}")

    # ---- plan: each circuit's branches; a branch is a chain of room visits (Living → Bed1 → bath → Bed2) ----
    def ordered(line, s_from, sg, items):   # [(span, s, kind, id)] along sg from s_from
        return sorted((line.span(s_from, s, sg), s, k, i) for s, k, i in items)

    JMAX = 0.40   # along the wall, kept for a run to change height on coming into a room (2 × 30°)

    def link_sharp(fed, pid, t_):   # fed's box → pid's box in the wall, out of its bottom (top) and in at the top (bottom):
        hb = EL["box"][1] / 2         # (sharp points, whether its bends fit between the two boxes)
        pa, pb_ = pts[fed]["p"] - pts[fed]["n"] * 0.02, pts[pid]["p"] - pts[pid]["n"] * 0.02
        v = 1 if pb_.z > pa.z else -1
        a0 = pa + Vector((0, 0, v * hb)) + (t_ * LK if v > 0 else Vector())   # (out of its top: ahead of the conduit coming down into it)
        b0 = pb_ - Vector((0, 0, v * hb)) - t_ * LK   # (into the knockout behind: the way on leaves ahead)
        dxy = (b0.xy - a0.xy).length
        P1 = a0 + Vector((0, 0, v * 0.06))
        sh = [a0, P1]
        if dxy > 1e-4:
            sh.append(Vector((b0.x, b0.y, P1.z + v * dxy / math.tan(_bend_angle(dxy, r0, math.radians(30.0))))))
        return sh + [b0], (b0.z - sh[-1].z) * v > r0 * math.tan(math.radians(15.0)) + 0.005

    def links(line, s, s_nx, pid, nid, sg):   # pid's box linked in the wall to nid's, the next box on its wall
        t_ = (Vector((*line.at(s + 0.01), 0)) - Vector((*line.at(s - 0.01), 0))).normalized() * sg
        g_ = line.span(s, s_nx, sg)
        return g_ < 2 * LOOP + 0.03 and _straight_at(line, s + sg * g_ / 2, g_ / 2 + 0.02) \
            and link_sharp(pid, nid, t_)[1]   # (boxes level with each other, or a corner between: two loops instead)

    def visit(C, room, s_in, sg, rest, devs, back, shift, tdir, z_in=None, jshift=0.0, slot=0, from_plate=False, dlx=0.0, jb=True):
        """One room visit at a height of its own: its events in order (boxes; the way on to the next room, through a
        branching box when the run must go on round for boxes past it) and the bands it takes. A run coming in from
        another room arrives at z_in and changes height (a 2 × 30° offset on the wall face) just inside. → (node, bands)."""
        line, lv = lines[room], lev[room]
        r0, rc, a_l, AB, LOOP = GEO[C["conduit"]]   # (the bands and loop reach of this conduit's size)
        dz = 0.0
        jog = None
        if z_in is not None and not from_plate:
            sj0 = s_in + sg * (0.66 + jshift)   # past the stretch the room before booked for it (to 0.35 past the join)
            while not _straight_at(line, sj0 + sg * JMAX / 2, JMAX / 2 + 0.01):
                sj0 += sg * 0.02
            jog = sj0
        aft = (s_in, sg, TR + 0.75 + dlx) if from_plate else None   # room to come down off the plate first (past a corner column)
        items = [(dl_s(room, p, aft) if pts[p]["kind"] == "dl" else line.s_of((pts[p]["p"].x, pts[p]["p"].y)),
                  "dev", p) for p in devs.get(room, [])]
        ex = None
        if rest:
            Y = rest[0]
            sl, sgl, poly, sj, sgy = xs[(room, Y, sg)] if (room, Y, sg) in xs else xs[(room, Y, 1)]
            assert sgl == sg, f"{C['id']}: the way into {Y} runs against the way round {room}"
            items.append((sl, "exit", Y))
            ex = (Y, sl, poly, sj, sgy)
        ev = ordered(line, s_in, sg, items)
        # the shared pull boxes on the band before its last event: events where the run is on the band there (added once
        # its stretches up on the plate are known: a run up there passes over them; one up from the CU passes none)
        hubs_here = [] if not ev or (room == "Living" and C.get("route") in CD["home_plate"]) else \
            [(line.span(s_in, hs, sg), hs, "hub", f"HUB@{room}{hs:.2f}") for room_, kd_, hs in (h_[:3] for h_ in CD.get("hubs", []))
             if room_ == room and kd_ == "band" and (2 * TR if from_plate else 0.30) < line.span(s_in, hs, sg) < ev[-1][0] - ext("HUB") - 0.05]
        strict = False
        if jog is not None and not all(line.span(s_in, e[1], sg) > line.span(s_in, jog + sg * JMAX, sg) + 0.07 for e in ev):
            jog, strict = None, True   # a box just inside the way in: no room to change height, keep the one it came at
        k_ex = next((i for i, e in enumerate(ev) if e[2] == "exit"), None)
        tee, tee_dev = None, None
        if k_ex is not None and k_ex < len(ev) - 1:   # boxes past the way out: branch before it
            before = [e for e in ev[:k_ex] if e[2] == "dev" and pts[e[3]]["kind"] == "dl"]   # (a looped wall box sits low)
            if before:   # the last device box before the way out does it (the user: a device box may branch): a 4×4
                tee_dev = before[-1][3]
            else:        # none: a tee of its own
                tee = box_s(line, ev[k_ex][1] - sg * (pb[0] / 2 + 0.05 + back), pb[0] / 2, 0.3)
        over = None
        if ex and (room, ex[0]) in XO and tee is None and tee_dev is None:   # up onto the plate before the corner, over it
            prev = max([e[1] + sg * (ext(e[3]) + 0.02) for e in ev if e[2] in ("dev", "hub")] + [s_in + sg * (HOME if z_in is None else 0.0)],
                       key=lambda q: line.span(s_in, q, sg))
            su = prev + sg * (0.10 + shift[0])
            while not both_straight(room, su - sg * LEAD, TR + LEAD, sg):
                su += sg * 0.02
                assert line.span(su, ex[1], sg) > TR + 0.3, f"{C['id']}: no straight to climb onto the plate before {ex[0]}"
            over = su
        down = None
        if from_plate:   # it comes in on this room's plate band: down to the plaster before the first box
            first = min((e for e in ev if e[2] in ("dev", "hub")), key=lambda e: e[0])
            sd = first[1] - sg * (ext(first[3]) + 0.08 + shift[1])
            while not both_straight(room, sd - sg * TR, TR + LEAD, sg):
                sd -= sg * 0.02
                assert 0.02 < line.span(s_in, sd - sg * TR, sg) < line.L / 2, \
                    f"{C['id']}: no straight to come down off the plate in {room} (in {s_in:.2f}, first box {first[1]:.2f} {first[3]}, at {sd:.2f})"
            assert 0.02 < line.span(s_in, sd - sg * TR, sg) < first[0], \
                f"{C['id']}: no straight to come down off the plate in {room} between its way in and {first[3]}"
            down = sd
        plates = [] if (room == "Living" and (not rest or C.get("route") not in CD["home_plate"])) or over is not None else \
            plate_gaps(room, ev, down if from_plate else (s_in + sg * (HOME if z_in is None else 0.0) if jog is None else jog + sg * JMAX),
                       sg, back, shift[0], shift[1])
        up_ = [(line.span(s_in, su, sg), line.span(s_in, sd, sg)) for _, su, sd in plates] + \
            ([(line.span(s_in, over, sg), 99.0)] if over is not None else []) + ([(-1.0, line.span(s_in, down, sg))] if down is not None else []) + \
            ([(line.span(s_in, jog, sg), line.span(s_in, jog + sg * (JMAX + 0.07), sg))] if jog is not None else [])
        m_ = ext("HUB") + LEAD   # (a hub's half-length and a climb's lead-in: the run level through it)
        keep = [h_ for h_ in hubs_here if not any(a_ - m_ < h_[0] < b_ + m_ for a_, b_ in up_)]
        if keep:
            old = ev
            ev = sorted(ev + keep)
            plates = [(ev.index(old[j]) if j < len(old) else len(ev), su, sd) for j, su, sd in plates]   # ("before event j")
        # (a conduit that stays in the living room keeps to the plaster band: its stretches are short)
        bands = []
        branched = tee is not None or tee_dev is not None
        end = ev[-1][1] if branched or k_ex is None else next(e[1] for e in ev if e[2] == "exit")   # (by kind: hubs merged since k_ex)
        if over is not None:
            end = over
        start = s_in + (sg * 0.65 if strict else 0.0) if jog is None else jog + sg * JMAX
        if down is not None:
            start = down
        cuts = [start] + [q for _, su, sd in plates for q in (su, sd)] + [end]
        if jog is not None:   # in at z_in, then the change of height
            if line.span(s_in + sg * 0.65, jog, sg) > 0.01 and line.span(s_in + sg * 0.65, jog, sg) < line.L / 2:   # (the first
                bands.append((lv, (s_in + sg * 0.65, jog, sg), -rc, rc, "run", z_in, "abs"))                     # 0.65 m: booked before)
            bands.append((lv, (jog, jog + sg * JMAX, sg), -rc, rc, "run", z_in, "jog"))
        for a_, b_ in zip(cuts[0::2], cuts[1::2]):   # the run on the plaster band
            bands.append((lv, (a_, b_, sg), dz - rc, dz + rc, "run"))
        for _, su, sd in plates + ([(None, over, None)] if over is not None else []) + ([(None, None, down)] if down is not None else []):
            for a_, b_ in ([(su, su + sg * TR)] if su is not None else []) + ([(sd - sg * TR, sd)] if sd is not None else []):
                bands.append((lv, (a_, b_, sg), dz - rc, None, f"front:{slot}" if plate_lat(room, (a_ + b_) / 2) > 0 else "climb"))
        if jb:   # junction boxes clear of each other and of the run's start (a device fed in the wall has none)
            wd = [e for e in ev if e[2] == "dev" and pts[e[3]]["kind"] != "dl"]
            fed_ = False
            for a_, b_ in zip(wd, wd[1:]):   # (as walk_visit lays them: a fed device links on to none)
                fed_ = not fed_ and ev[ev.index(a_) + 1] is b_ and links(line, a_[1], b_[1], a_[3], b_[3], sg)
                assert fed_ or line.span(a_[1], b_[1], sg) >= JB + 0.01, f"{C['id']} in {room}: {a_[3]} and {b_[3]} too close for two junction boxes"
            if wd:   # the run is on the wall at its height from: down off the plate, past its change of height, else the way in
                st_ = down if down is not None else (jog + sg * JMAX if jog is not None else s_in)
                assert line.span(st_, wd[0][1], sg) >= JB + 0.02, \
                    f"{C['id']} in {room}: {wd[0][3]}'s junction box would start before the run is on the wall"
        for span, s, kind, ident in ev:
            if kind == "dev" and pts[ident]["kind"] != "dl" and not jb:   # a looped wall device (no room for junction boxes here)
                bands.append((lv, (s - LOOP, s + LOOP, 1), dz - rc - DIP, dz + rc, "loop"))
            elif kind == "dev" and pts[ident]["kind"] != "dl":   # a wall device: its junction box (centre tdir·KO off the run) and its drop's dive
                sb_ = s - sg * (JB - pb[0] / 2)
                bands.append((lv, (sb_ - pb[0] / 2 - 0.01, sb_ + pb[0] / 2 + 0.01, 1), dz + tdir * KO - pb[1] / 2, dz + tdir * KO + pb[1] / 2, "box"))
                d0_, d1_ = sorted((s - sg * (LOOP + 0.02), s + sg * (LK + 0.01)))
                bands.append((lv, (d0_, d1_, 1), dz + 2 * tdir * KO - rc - DIP, dz + 2 * tdir * KO + rc, "drop"))
            if kind == "dev" and pts[ident]["kind"] == "dl":
                below = CD["below_dl"]
                if ident == tee_dev:   # a 4×4: its centre KO off the run, the drop / flex from its bottom
                    c_ = dz + tdir * KO
                    bands.append((lv, (s - pb[0] / 2 - 0.01, s + pb[0] / 2 + 0.01, 1), c_ - pb[1] / 2 - below, c_ + pb[1] / 2, "box"))
                else:
                    bands.append((lv, (s - ib[0] / 2 - 0.01, s + ib[0] / 2 + 0.01, 1), dz - ib[1] / 2 - below, dz + ib[1] / 2, "box"))
        child = None
        if ex:
            dzc = dz + (tdir * 2 * KO if branched else 0.0)
            if tee is not None:
                bands.append((lv, (tee - pb[0] / 2 - 0.01, tee + pb[0] / 2 + 0.01, 1), dz + tdir * KO - pb[1] / 2, dz + tdir * KO + pb[1] / 2, "box"))
            if branched:
                s_br = tee if tee is not None else next(e[1] for e in ev if e[3] == tee_dev)
                bands.append((lv, (s_br, ex[1] + sg * 0.35, sg), dzc - rc, dzc + rc, "run"))
            Y, sj, sgy = ex[0], ex[3], ex[4]   # and it must arrive in the next room at a height free there (over its ceiling)
            if over is None:
                bands.append((lev[Y], (sj - sgy * 0.3, sj + sgy * 0.35, sgy), dzc - rc, dzc + rc, "run"))
        return dict(room=room, s_in=s_in, sg=sg, ev=ev, tee=tee, tee_dev=tee_dev, tdir=tdir, ex=ex, child=None,
                    plates=plates, jog=jog, z_in=z_in, rest=rest, branched=branched, strict=strict, slot=slot, over=over,
                    down=down, from_plate=from_plate, jb=jb), bands

    def climb_band(room, a_, b_, sgr, slot, rc_=None):   # a climb's window up into the plate band: from its bottom to the run (jog mode)
        pln_, plv_ = PL[room]
        return (plv_, (pln_.s_of(lines[room].at(a_)), pln_.s_of(lines[room].at(b_)), sgr), 0.0, rc_ or rc, f"climb:{slot}", plv_.z0, "jog")

    def plate_take(room, sgr, su, sd, slot, owner):   # a passing stretch on the plate and its two climbs: its height there
        pln_, plv_ = PL[room]
        rc_ = RC_OF.get(owner, rc)
        return take_joint([(plv_, (pln_.s_of(lines[room].at(su + sgr * TR)), pln_.s_of(lines[room].at(sd - sgr * TR)), sgr), -rc_, rc_, f"run:{slot}"),
                           climb_band(room, su, su + sgr * TR, sgr, slot, rc_), climb_band(room, sd - sgr * TR, sd, sgr, slot, rc_)], owner)

    def over_book(C, room, sg, rest, devs, node):   # on the plate to the corner, over it, on into Y's plate band (raises: none)
        pln, plv = PL[room]
        rc_ = GEO[C["conduit"]][1]
        Y, sl, poly, sj, sgy = node["ex"]
        owner = C.get("route", C["id"])
        _, (pA, pE, pXe, pYs) = over_path(room, Y, 3.5, 3.56, 3.5, node["slot"], rc_)
        s_up = pln.s_of(lines[room].at(node["over"] + sg * TR))
        s_xe = pln.s_of((pXe.x, pXe.y))
        node["zp_over"] = take_joint([(plv, (s_up, s_xe, sg), -rc_, rc_, f"run:{node['slot']}"),   # (the climb over: booked to the top)
                                      climb_band(room, node["over"], node["over"] + sg * TR, sg, node["slot"], rc_)], owner)
        take_joint([(plv, (s_xe - sg * 0.35, s_xe, sg), -rc_, None, f"run:{node['slot']}")], owner, node["zp_over"], True)
        OV.setdefault((room, Y), [])
        node["zo"] = 3.55 + CD["gap"] + rc_ + len(OV[(room, Y)]) * (2 * EL["conduit"]["3/4"] / 2 + CD["gap"])
        OV[(room, Y)].append(owner)
        ly, (plnY, plvY) = lines[Y], PL[Y]
        errs2 = []
        for back2, sh2, dlx in [(0.15 * k, 0.4 * m, 0.75 * q) for q in range(3) for m in range(6) for k in range(2)]:
            try:
                cn, cb = visit(C, Y, ly.s_of((pYs.x, pYs.y)), sgy, rest[1:], devs, back2, (0.0, sh2), 1, None, 0.0, node["slot"], True, dlx,
                               jb=Y not in CD["jb_off"])
                cn["z"] = take_joint(cb, owner)
                break
            except AssertionError as e:
                errs2.append(e)
        else:
            raise AssertionError(f"{C['id']} in {Y} (over the plate): " + " || ".join(dict.fromkeys(str(e)[:220] for e in errs2)))
        s_ys = plnY.s_of((pYs.x, pYs.y))
        s_dn = plnY.s_of(ly.at(cn["down"] - sgy * TR))
        cn["zp_in"] = take_joint([(plvY, (s_ys, s_dn, sgy), -rc_, rc_, f"run:{node['slot']}"),
                                  climb_band(Y, cn["down"] - sgy * TR, cn["down"], sgy, node["slot"], rc_)], owner)
        take_joint([(plvY, (s_ys - sgy * 0.05, s_ys + sgy * 0.35, sgy), -rc_, None, f"run:{node['slot']}")], owner, cn["zp_in"], True)
        cn["pl"] = {j: (su, sd, plate_take(Y, sgy, su, sd, node["slot"], owner)) for j, su, sd in cn["plates"]}   # its stretches between boxes up on the plate
        node["child"] = cn

    def place(C, room, s_in, sg, rest, devs, z_in=None):
        """Plan a room visit, take its height (sliding its tees / climbs, trying the branch up or down when nothing
        fits), give its passing stretches their wall-plate heights, then the next room."""
        errs = []
        for tdir, jb in [(t_, j_) for j_ in ((False,) if room in CD["jb_off"] else (True,)) for t_ in (1, -1)]:   # junction boxes, or loops where none fit
            for back, shift, js, sl_ in [(0.15 * k, (0.8 * mu, 0.8 * md), 0.4 * q, slot) for slot in range(4) for q in range(4 if z_in is not None else 1)
                                         for mu in range(3) for md in range(3) for k in range(2)]:
                snap = {id(l_): (l_, len(l_.used)) for l_ in list(lev.values()) + [pv for _, pv in PL.values()]}
                try:
                    node, bands = visit(C, room, s_in, sg, rest, devs, back, shift, tdir, z_in, js, sl_, jb=jb)
                    cnode = None
                    if node["ex"] and node["over"] is None:   # the next room keeps the height it comes in at (a box at its way in): book it now too
                        Y, sl_, poly_, sj_, sgy_ = node["ex"]
                        dzc = node["tdir"] * 2 * KO if node["branched"] else 0.0
                        cn, cb = visit(C, Y, sj_ - sgy_ * 0.3, sgy_, rest[1:], devs, back, (0.0, 0.0), tdir, 0.0, 0.0, jb=Y not in CD["jb_off"])
                        if cn["strict"] and not cn["ex"]:
                            cnode = cn
                            bands += [(b_[0], b_[1], b_[2] + dzc, None if b_[3] is None else b_[3] + dzc, b_[4]) for b_ in cb]
                    node["z"] = take_joint(bands, C.get("route", C["id"]), z_in, node["strict"])
                    node["pl"] = {j: (su, sd, plate_take(room, sg, su, sd, node["slot"], C.get("route", C["id"]))) for j, su, sd in node["plates"]}
                    if node["ex"] and node["over"] is not None:
                        OVn = {k_: list(v_) for k_, v_ in OV.items()}
                        try:
                            over_book(C, room, sg, rest, devs, node)
                        except AssertionError:
                            OV.clear()
                            OV.update(OVn)
                            raise
                    break
                except AssertionError as e:
                    for l_, n_ in snap.values():   # undo what this attempt booked
                        del l_.used[n_:]
                    errs.append(e)
            else:
                continue
            break
        else:
            best = min(errs, key=lambda e: str(e).count("free []"))   # the nearest miss
            CD["_errs"] = errs   # (inspection)
            raise AssertionError(f"{C['id']} in {room}: {best}")
        pln, plv = PL[room]
        if node["ex"] and node["over"] is not None:
            pass   # (booked with the attempt: over_book)
        elif node["ex"]:
            Y, sl, poly, sj, sgy = node["ex"]
            zc = node["z"] + (node["tdir"] * 2 * KO if node["branched"] else 0.0)
            if cnode is not None:   # booked with this room: same height, its plate stretches now
                cnode["z"], cnode["z_in"] = zc, zc
                cnode["pl"] = {j: (su, sd, plate_take(Y, sgy, su, sd, cnode["slot"], C.get("route", C["id"]))) for j, su, sd in cnode["plates"]}
                node["child"] = cnode
            else:
                node["child"] = place(C, Y, sj - sgy * 0.3, sgy, rest[1:], devs, zc)
        return node

    OV = {}   # crossing over a plate → heights taken over it (they stack)

    def over_path(X, Y, zp, zo, zpY, slot, rc_=None):   # X's plate line at zp → up to zo over the crossed plate → Y's plate line at zpY
        a, d, ax, ux_end, uy_start, fn, ff = _over({X: PL[X][0], Y: PL[Y][0]}, X, Y)
        rcx = _voids()[X][0]
        inward = 1 if (rcx[1 - ax] + rcx[3 - ax]) / 2 > a else -1
        a_s = a + inward * slot * SLOT
        def P(u, z_):
            q = [0.0, 0.0, z_]
            q[ax], q[1 - ax] = u, a_s
            return Vector(q)
        u2 = fn - d[ax] * ((rc_ or rc) + 0.01)
        u1 = u2 - d[ax] * (zo - zp) / math.tan(th30)
        uA = u1 - d[ax] * (t30 + 0.01)
        u3 = ff + d[ax] * ((rc_ or rc) + 0.01)
        u4 = u3 + d[ax] * (zo - zpY) / math.tan(th30)
        uE = u4 + d[ax] * (t30 + 0.01)
        assert uA * d[ax] <= ux_end * d[ax] + 1e-6 and uE * d[ax] >= uy_start * d[ax] - 1e-6, f"{X} → {Y}: no straight for the climb over the plate"
        pts_, _ = _round3([P(uA, zp), P(u1, zp), P(u2, zo), P(u3, zo), P(u4, zpY), P(uE, zpY)], [0, r0, r0, r0, r0, 0])
        return pts_, (P(uA, 0), P(uE, 0), P(ux_end, 0), P(uy_start, 0))

    def subtree(node):   # every device a visit and the visits after it feed
        return {i for _, _, k, i in node["ev"] if k == "dev"} | (subtree(node["child"]) if node["child"] else set())

    plans = []
    byid = {C["id"]: C for C in CIRCUITS}
    routed = {p for _, _, _, legs in ROUTES for _, ps in legs for p in ps}
    for C in CIRCUITS:   # every point of a routed circuit must be on a route (or the circuit waits: porch / eave)
        missing = [p for p in C["pts"] if p not in routed and p not in CD["pending"]]
        if missing:   # a circuit on no route at all waits (L2, MAIN: the porch / eave set); a routed one must be whole
            assert not any(C["id"] in cid.split("+") for _, cid, _, _ in ROUTES), f"{C['id']}: {missing} on no route"
            out["skipped"].append(C["id"])
    for name, cid, sg, legs in ROUTES:
        devs = {room: ps for room, ps in legs}
        ms = [byid[c] for c in cid.split("+")]
        assert {p for _, ps in legs for p in ps} <= {p for M in ms for p in M["pts"]}, f"{name}: a point on no circuit of {cid}"
        plans.append((dict(ms[0], id=cid, route=name, members=ms, pts=[p for M in ms for p in M["pts"]],
                           conduit=CD["route_size"].get(name, ms[0]["conduit"])), sg,
                      [room for room, _ in legs[1:]], devs))

    RC_OF = {C["route"]: GEO[C["conduit"]][1] for C, _, _, _ in plans}   # each route's conduit radius (plate booking)
    # the order the conduits take their heights in (by circuit id; found by trial, 30 ต.ค.: the first ones get the free
    # band, later ones fit round them)
    order = CD.get("order", ["S2+S3+L2", "L1+H1", "A1+S1+L1", "S2+L2", "L1+S1+L2"])
    if order:
        plans.sort(key=lambda pl_: order.index(pl_[0]["id"]) if pl_[0]["id"] in order else 99)
    built = []
    for C, sg, rs, devs in plans:
        node = place(C, "Living", s_cu + sg * 0.10, sg, rs, devs)   # its run is on the wall from about s_cu + 0.10
        built.append((C, sg, node, node["z"], None))

    # ---- the home runs: lower levels rise further from the CU middle (bends never cross) ----
    for sg in (1, -1):
        grp = sorted([b for b in built if b[1] == sg], key=lambda b: -b[3])   # highest first
        if grp:
            for C, _, node, z, pl in grp:
                out.setdefault("_home", {})[id(node)] = (s_cu + sg * (0.012 + (grp[0][3] - z)), z)

    fill_of = lambda ws, size: sum(k * math.pi / 4 * CD["fill"]["od"][w.lstrip("G")] ** 2 for w, k in ws) / (math.pi / 4 * CD["fill"]["id"][size] ** 2)

    def piece(cid, to, path, S, C, ws=None, size=None):   # one conduit piece: its wire (ws: its conductors when not S's own)
        size = size or C["conduit"]
        clean = [path[0]]
        for q in path[1:]:
            if (q - clean[-1]).length > 1e-6:
                clean.append(q)
        out["runs"].setdefault(size, []).append((cid, to, clean))
        L = _path_len(clean)
        out["pieces"].append([C.get("route", cid), cid, to, clean, size, None])
        ws = ws if ws is not None else _conductors(C["members"], S, pts, f"{cid} → {to}")
        fill = fill_of(ws, size)
        assert fill <= 0.40 + 1e-9, f"{cid} → {to}: conductors fill {fill:.0%} of the {size}\" conduit (> 40 %)"
        out["fill"][(cid, to)] = fill
        out["pieces"][-1][5] = ws
        for w, k in ws:
            out["wire"][w] = out["wire"].get(w, 0.0) + k * (L + 2 * EL["slack"])
        zmin = min(zc_room.values()) + 0.01
        out["vlen"][size] = out["vlen"].get(size, 0.0) + sum((q - p).length for p, q in zip(clean, clean[1:]) if min(p.z, q.z) > zmin)

    def in_top(P, F, nin):   # a chase's top: where its conduit goes in behind the wall face (in its bend, below the run)
        dep = [(F - p).dot(nin) - CD["dc"] for p in P]   # ≥ 0: at or behind the face
        zs = [p.z for p, d in zip(P, dep) if d >= -1e-9]
        zs += [p.z + (q.z - p.z) * (-dp / (dq - dp)) for p, q, dp, dq in zip(P, P[1:], dep, dep[1:]) if (dp < 0) != (dq < 0)]   # (the crossing)
        return max(zs)

    def loop(line, s, z, sg, pid, path, S, C, more, fed=None):   # into the wall, down into pid's box (or in from the box
        pt = pts[pid]                                               # fed, in the wall); back up and out if more follows
        r0, rc, a_l, AB, LOOP = GEO[C["conduit"]]
        t_ = (Vector((*line.at(s + 0.01), 0)) - Vector((*line.at(s - 0.01), 0))).normalized() * sg
        assert (fed or _straight_at(line, s - sg * LOOP / 2, LOOP / 2)) and (not more or _straight_at(line, s + sg * LOOP / 2, LOOP / 2)), \
            f"{C['id']}: the wall is not straight round {pid}'s loop"
        nin = n_in(line, s)
        F = Vector((*line.at(s), z))   # on the face run
        W = F - nin * lat_l            # in the chase
        dev = pt["p"] - pt["n"] * 0.02 + Vector((0, 0, EL["box"][1] / 2))
        def leg(k):   # k = -1 down (in from behind), +1 up (out ahead): sharp points from the face to the box top
            sv = k * LK
            sa = sv + k * AB * math.cos(a_l)
            return [F + t_ * (sa + k * (r0 * math.tan(a_l / 2) + 0.01)), F + t_ * sa, W + t_ * sv, Vector((*(W + t_ * sv).xy, dev.z))]
        if fed:   # from the box before, close by on this wall: out of its bottom (top), 2 bends in the wall, into this box
            sh, ok = link_sharp(fed, pid, t_)
            assert ok, f"{C['id']}: {fed} → {pid} too close in height to link in the wall"
            lpts, _ = _round3(sh, [0] + [r0] * (len(sh) - 2) + [0])
            piece(C["id"], pid, lpts, S, C)
            out["chase"].append((C["id"], pid + "_link", tuple(sh[-1].xy), 0.0, _path_len(lpts)))   # (its length: diagonal)
            if not more:
                return None
            up = list(reversed(leg(1)))
            upts, _ = _round3(up, [0, r0, r0, 0])
            out["chase"].append((C["id"], pid + "_up", tuple(up[0].xy), dev.z, in_top(upts, F, nin)))   # (no way down here: a chase of its own)
            return upts
        dn = leg(-1)
        e0 = line.s_of((dn[0].x, dn[0].y))
        s_from = line.s_of((path[-1].x, path[-1].y))
        assert line.span(s_from, e0, sg) < line.L - 0.5, f"{C['id']}: {pid}'s loop is behind the run"
        if line.span(s_from, e0, sg) > 1e-6:
            path += line.stretch(s_from, e0, sg, z)[1:]
        dpts, _ = _round3(dn, [0, r0, r0, 0])
        piece(C["id"], pid, path + dpts[1:], S, C)
        out["chase"].append((C["id"], pid, tuple(dn[-1].xy), dev.z, in_top(dpts, F, nin)))
        if not more:
            return None
        up = list(reversed(leg(1)))
        upts, _ = _round3(up, [0, r0, r0, 0])
        return upts

    def device(line, room, s, z, sg, pid, path, S, C, td=0, to=None):   # on along the line into pid's box; its drop / flex; out the
        pt = pts[pid]                                               # far end (td ≠ 0: a 4×4 that branches, td·2·KO off)
        bs = pb if td else ib
        e_in = s - sg * bs[0] / 2
        s_from = line.s_of((path[-1].x, path[-1].y))
        assert line.span(s_from, e_in, sg) < line.L - 0.5, f"{C['id']}: {pid}'s box is behind the run"
        if line.span(s_from, e_in, sg) > 1e-6:
            path += line.stretch(s_from, e_in, sg, z)[1:]
        piece(C["id"], to or pid, path, S, C)
        B = Vector((*line.at(s), z + td * KO))
        t = Vector((*line.at(s + 0.01), 0)) - Vector((*line.at(s - 0.01), 0))
        t.normalize()
        out["boxes"].append((B, -t, bs))   # (_top_box puts the lid on t × Z: clockwise along the wall = to the room)
        bot = B - Vector((0, 0, bs[1] / 2))
        nin = n_in(line, s)
        if pt["kind"] == "dl":   # flex: down out of the box bottom, out into the void, over to the fitting
            d = pt["p"]
            if room_of(pid) == room:
                zu = zc_room[room] + 0.05
                fx = _fillet([bot, bot - Vector((0, 0, 0.025)), bot - Vector((0, 0, 0.025)) + nin * 0.10,
                              Vector((d.x, d.y, zu)), Vector((d.x, d.y, d.z + EL["dl"]["h"]))])
            else:   # a light the other side of this wall (the eave): the flex straight through it (a hole in the brick)
                P1 = bot - Vector((0, 0, 0.025))
                P2 = P1 - nin * (CD["dc"] + WALL["t"] + 2 * WALL["pl"] + 0.06)
                Vo = V[room_of(pid)]
                assert room_of(pid) in ("Porch", "Eave") and Vo[0][0] - 0.03 < P2.x < Vo[0][2] + 0.03 and Vo[0][1] - 0.03 < P2.y < Vo[0][3] + 0.03 \
                    and P2.z > Vo[2] + EL["flex"]["od"] / 2 + 0.02, f"{pid}: its flex through the wall does not come out over its soffit"
                fx = _fillet([bot, P1, P2, Vector((d.x, d.y, Vo[2] + 0.05)), Vector((d.x, d.y, d.z + EL["dl"]["h"]))])
                out["cross"] += 1
            out["flex"].append((C["id"], pid, fx))
            M = next(M for M in C["members"] if pid in M["pts"])   # the light's own circuit
            for w, k in [(M["wires"][0][0], 2)] + [w for w in M["wires"] if w[0].startswith("G")]:
                out["wire"][w] = out["wire"].get(w, 0.0) + k * (_path_len(fx) + 2 * EL["slack"])
        elif to is None:
            raise AssertionError(f"{pid}: a wall device's box goes through jbox()")
        far = Vector((*line.at(s + sg * bs[0] / 2), z))
        return ([far], [far + Vector((0, 0, 2 * td * KO))]) if td else [far]

    def jbox(line, room, s, z, sg, pid, path, S, C, td, linked=None):   # pid's junction box behind it on the run, the drop
        r0, rc, a_l, AB, LOOP = GEO[C["conduit"]]                            # from its far end down onto pid; → the run's way on
        assert _straight_at(line, s - sg * JB / 2, JB / 2 + 0.01), f"{C['id']} in {room}: the wall is not straight behind {pid} for its junction box"
        sb = s - sg * (JB - pb[0] / 2)
        run_on, drop0 = device(line, room, sb, z, sg, pid, path, S, C, td, to="J@" + pid)
        pt = pts[pid]
        t_ = (Vector((*line.at(s + 0.01), 0)) - Vector((*line.at(s - 0.01), 0))).normalized() * sg
        nin = n_in(line, s)
        zd = z + 2 * td * KO
        F = Vector((*line.at(s), zd))   # the drop on the face, at its knockout's height
        W = F - nin * lat_l             # in the chase
        dev = pt["p"] - pt["n"] * 0.02 + Vector((0, 0, EL["box"][1] / 2))
        sa = -LK - AB * math.cos(a_l)   # as a loop's down leg: in from behind onto the box top's near knockout
        sh = [drop0[0], F + t_ * sa, W - t_ * LK, Vector((*(W - t_ * LK).xy, dev.z))]
        assert (sh[1] - sh[0]).dot(t_) > r0 * math.tan(a_l / 2) + 0.005, f"{C['id']} in {room}: no straight out of {pid}'s junction box before the drop turns in"
        dpts, _ = _round3(sh, [0, r0, r0, 0])
        mine = {pid} | ({linked} if linked else set())
        Mp = [M for M in C["members"] if set(M["pts"]) & mine]   # only the device's own circuits go down: the others pass the box
        own = set().union(*[set(M["pts"]) for M in Mp])
        S_dn = set(S) & own
        S_up = S_dn - mine   # (spec 31 ต.ค.: no joints) down with what that circuit feeds on, back up with it
        ws = _conductors(Mp, S_dn, pts, f"{C['id']} → {pid}") + (_conductors(Mp, S_up, pts, f"{C['id']} → {pid} (back up)") if S_up else [])
        size = next((sz for sz in (C["conduit"], "3/4") if fill_of(ws, sz) <= 0.40 + 1e-9), None)   # (a loop-through drop may need 3/4")
        assert size, f"{C['id']} in {room}: {pid}'s drop fills even a 3/4\" conduit past 40 %"   # (that room keeps its loops)
        piece(C["id"], pid, dpts, S, C, ws, size)
        out["chase"].append((C["id"], pid, tuple(sh[-1].xy), dev.z, in_top(dpts, F, nin)))
        return run_on

    def _drop_in(top, ch, z_end):   # from the (flush) CU bottom straight down, 2 bends back into the chase at ch, down to z_end
        lat_v = Vector((ch.x - top.x, ch.y - top.y, 0))
        lat = lat_v.length
        a = _bend_angle(lat, r0, math.radians(CD["drop_deg"]))
        assert r0 * math.tan(a / 2) <= CD["drop_lead"] + 1e-9, f"drop_lead too short for a {math.degrees(a):.0f}° bend"
        P1 = top - Vector((0, 0, CD["drop_lead"]))
        P2 = P1 + lat_v - Vector((0, 0, lat / math.tan(a)))
        pts_, _ = _round3([top, P1, P2, Vector((ch.x, ch.y, z_end))], [0, r0, r0, 0])
        return pts_

    def climb(room, s0, z, zp, sg, slot=0):   # plaster line at s0, height z → the wall plate's line (slot·22 mm out) at zp
        Lv, pln = lines[room], PL[room][0]
        tdir = (Vector((*Lv.at(s0 + sg * 0.01), 0)) - Vector((*Lv.at(s0 - sg * 0.01), 0))).normalized()
        nin = n_in(Lv, s0)   # into the room (left of counter-clockwise)
        P0 = Vector((*Lv.at(s0), z))
        Pp = Vector((*pln.at(pln.s_of(Lv.at(s0))), 0))
        lat = (Pp - Vector((P0.x, P0.y, 0))).dot(nin) + slot * SLOT   # + the plate stands proud of the plaster, − set back
        up = Vector((0, 0, zp - z))
        step = lambda v, d: v + tdir * (d / math.tan(th30))
        ph = _bend_angle(abs(lat), r0, th30)   # a plate only a few mm proud: two shallower bends
        side = (lambda v: v + tdir * (abs(lat) / math.tan(ph)) + nin * lat) if abs(lat) > 1e-4 else (lambda v: v + tdir * (t30 + 0.01))   # flush: a straight leg
        if lat > 0:   # out first (in front of the band), then up
            V1 = side(P0)
            V2 = V1 + tdir * (2 * t30 + 0.01)
            V3 = step(V2, zp - z) + up
        else:         # up first (on the plaster, over the wall top), then back onto the plate
            V1 = step(P0, zp - z) + up
            V2 = V1 + tdir * (2 * t30 + 0.01)
            V3 = side(V2)
        E = V3 + tdir * (t30 + 0.01)
        sharp = [P0 - tdir * (t30 + 0.01), P0, V1, V2, V3, E]
        pts_, turn = _round3(sharp, [0, r0, r0, r0, r0, 0])
        assert (E - P0).dot(tdir) <= TR + 1e-6, f"a climb onto the wall plate longer than {TR} m at s {s0:.2f}"
        return pts_

    def plate_run(room, p0, p1, sg, zp, k):   # along a room's plate line from near p0 to near p1 at zp, in slot k
        pln = PLK[room][k]
        return pln.stretch(pln.s_of((p0.x, p0.y)), pln.s_of((p1.x, p1.y)), sg, zp)

    def walk_visit(node, path, z, C, pl):   # lay a room visit and the visits after it
        room, sg = node["room"], node["sg"]
        line = lines[room]
        zz = node["z"]
        ev = node["ev"]
        if node["from_plate"]:   # in on this room's plate band: along it, down to the plaster before the first box
            dn_ = list(reversed(climb(room, node["down"], zz, node["zp_in"], -sg, node["slot"])))
            path += plate_run(room, path[-1], dn_[0], sg, node["zp_in"], node["slot"])[1:]
            path += dn_[1:]
        if node["jog"] is not None and abs(zz - node["z_in"]) > 1e-4:   # in at the height it came, then change it
            s_now = line.s_of((path[-1].x, path[-1].y))
            j0 = node["jog"]
            if line.span(s_now, j0 - sg * 0.05, sg) > 1e-6:
                path += line.stretch(s_now, j0 - sg * 0.05, sg, node["z_in"])[1:]
            d_ = abs(zz - node["z_in"]) / math.tan(th30)
            P0, P1 = Vector((*line.at(j0), node["z_in"])), Vector((*line.at(j0 + sg * d_), zz))
            Pa = Vector((*line.at(j0 - sg * 0.05), node["z_in"]))
            Pb = Vector((*line.at(j0 + sg * (d_ + t30 + 0.02)), zz))
            jp, _ = _round3([Pa, P0, P1, Pb], [0, r0, r0, 0])
            path += jp[1:]
        fed = None   # a wall box fed in the wall from the one before it
        for j, (span, s, kind, ident) in enumerate(ev):
            if j in node["pl"]:   # up onto the wall plate, along it, down again before this event
                su, sd, zp = node["pl"][j]
                a_ = su - sg * (t30 + 0.01)
                s_now = line.s_of((path[-1].x, path[-1].y))
                assert line.span(s_now, a_, sg) < line.L / 2, f"{C['id']}: the run is already past its climb at {a_:.2f} in {room}"
                if line.span(s_now, a_, sg) > 1e-6:
                    path += line.stretch(s_now, a_, sg, zz)[1:]
                k_ = node["slot"]
                up_ = climb(room, su, zz, zp, sg, k_)
                dn_ = list(reversed(climb(room, sd, zz, zp, -sg, k_)))
                path += up_[1:]
                path += plate_run(room, up_[-1], dn_[0], sg, zp, k_)[1:]   # in its slot all along
                path += dn_[1:]
            down = {i2 for _, _, k2, i2 in ev[j:] if k2 == "dev"} | (subtree(node["child"]) if node["child"] and any(k2 == "exit" for _, _, k2, _ in ev[j:]) else set())
            if kind == "hub":   # the run passes through (split there afterwards)
                continue
            if kind == "dev" and pts[ident]["kind"] != "dl":   # the next box close by on this wall: linked to it in the wall
                nx = ev[j + 1] if j + 1 < len(ev) else None
                lk = nx is not None and nx[2] == "dev" and pts[nx[3]]["kind"] != "dl" and links(line, s, nx[1], ident, nx[3], sg)
                if not node["jb"]:   # looped through its box (this visit had no height for junction boxes)
                    path = loop(line, s, zz, sg, ident, path, down, C, j < len(ev) - 1 and not lk, fed)
                    fed = ident if lk else None
                    continue
                if fed:   # fed in the wall from the device box before (its junction box's drop): the link only
                    loop(line, s, zz, sg, ident, path, {ident}, C, False, fed)
                    fed = None
                    continue
                path = jbox(line, room, s, zz, sg, ident, path, down, C, node["tdir"], nx[3] if lk else None)
                fed = ident if lk else None
                continue
            if kind == "dev":
                if ident == node["tee_dev"]:
                    path, branch = device(line, room, s, zz, sg, ident, path, down, C, node["tdir"])
                else:
                    path = device(line, room, s, zz, sg, ident, path, down, C)
                continue
            Y, sl, poly, sj, sgy = node["ex"]
            if node["over"] is not None:   # up onto the plate, along it to the corner, over the crossed plate into Y
                su, k_, zp = node["over"], node["slot"], node["zp_over"]
                a_ = su - sg * (t30 + 0.01)
                s_now = line.s_of((path[-1].x, path[-1].y))
                assert line.span(s_now, a_, sg) < line.L / 2, f"{C['id']}: the run is already past its climb at {a_:.2f} in {room}"
                if line.span(s_now, a_, sg) > 1e-6:
                    path += line.stretch(s_now, a_, sg, zz)[1:]
                up_ = climb(room, su, zz, zp, sg, k_)
                path += up_[1:]
                opts, _ = over_path(room, Y, zp, node["zo"], node["child"]["zp_in"], k_, GEO[C["conduit"]][1])
                path += plate_run(room, path[-1], opts[0], sg, zp, k_)[1:]
                path += opts[1:]
                walk_visit(node["child"], path, z, C, pl)
                return
            if node["tee_dev"] is not None:   # the child leaves the branching device box's other far knockout
                cpath, zc_ = branch, zz + node["tdir"] * 2 * KO
            elif node["tee"] is not None:   # into the tee's lower end; the child out of its upper far knockout
                sT = node["tee"]
                s_now = line.s_of((path[-1].x, path[-1].y))
                path += line.stretch(s_now, sT - sg * pb[0] / 2, sg, zz)[1:]
                piece(C["id"], f"T@{room}", path, down, C)
                td = node["tdir"]
                T = Vector((*line.at(sT), zz + td * KO))
                t = (Vector((*line.at(sT + 0.01), 0)) - Vector((*line.at(sT - 0.01), 0))).normalized()
                out["boxes"].append((T, -t, pb))
                cpath = [Vector((*line.at(sT + sg * pb[0] / 2), zz + td * 2 * KO))]
                path = [Vector((*line.at(sT + sg * pb[0] / 2), zz))]
                zc_ = zz + td * 2 * KO
            else:
                cpath, zc_ = path, zz
            s_now = line.s_of((cpath[-1].x, cpath[-1].y))
            if line.span(s_now, sl, sg) > 1e-6:
                cpath += line.stretch(s_now, sl, sg, zc_)[1:]
            xpath, _ = _round(poly, [r0] * len(poly), closed=False)
            cpath += [Vector((x, y, zc_)) for x, y in xpath[1:]]
            out["cross"] += 1
            walk_visit(node["child"], cpath, z, C, pl)
            if node["tee"] is None and node["tee_dev"] is None:
                return

    for C, sg, node, z, pl in built:
        s_k, _ = out["_home"][id(node)]
        rh = GEO[C["conduit"]][0]   # this conduit's bend radius
        nin = n_in(Lv, s_k)
        face = lambda s: Vector((*Lv.at(s), 0))
        rec = lambda s: face(s) - nin * (CD["dc"] + 0.02)   # in the chase
        top = Vector((rec(s_k).x, rec(s_k).y, cu["p"].z + EL["cu"]["size"][1] / 2))
        h0 = rec(s_k + sg * (rh + 0.03))
        set_end = s_k + sg * (rh + 0.23)   # out of the chase onto the run line where it is straight
        while not _straight_at(Lv, set_end, 0.12):
            set_end += sg * 0.01
        if Lv.bend_deg(s_k, set_end + sg * 0.12, sg) < 0.5:
            sharp = [top, Vector((rec(s_k).x, rec(s_k).y, z)), Vector((h0.x, h0.y, z)),
                     Vector((*Lv.at(set_end), z)), Vector((*Lv.at(set_end + sg * 0.10), z))]
            home, _ = _round3(sharp, [0, rh, rh, rh, 0])
        else:   # a column too close to set out before it (D3): level in the chase (out of the wall above the ceiling's
            while _straight_at(Lv, set_end - sg * 0.01, 0.01):   # wall angle), then straight out onto the line past its face
                set_end -= sg * 0.005   # back to where that straight begins: the bend onto it ends there
            u = (Vector((*Lv.at(set_end + 0.01), 0)) - Vector((*Lv.at(set_end - 0.01), 0))).normalized() * sg
            uc = (Vector((*Lv.at(s_k + sg * 0.01), 0)) - Vector((*Lv.at(s_k), 0))).normalized()   # along the chase
            A_ = Vector((rec(s_k).x, rec(s_k).y, 0))
            assert u.dot(uc) > 0.9999, f"{C['id']}: the chase and the line past the column are not parallel"
            th_ = math.radians(30.0)
            for _ in range(50):   # the bend's angle sets its tangent, which moves its ends: to a fixed point
                last, t_ = th_, rh * math.tan(th_ / 2)
                H_ = A_ + uc * (rh + t_ + 0.005)
                V_ = Vector((*Lv.at(set_end), 0)) - u * t_
                assert (V_ - H_).length >= 2 * t_ + 0.005, f"{C['id']}: no room to set out past the column"
                th_ = (V_ - H_).angle(u)
                if abs(th_ - last) < 1e-9:
                    break
            else:
                raise AssertionError(f"{C['id']}: the set-out past the column does not converge")
            assert math.degrees(th_) <= 45.0, f"{C['id']}: set-out past the column at {math.degrees(th_):.0f}° (> 45°): the CU too near it"
            sharp = [top, Vector((A_.x, A_.y, z)), Vector((H_.x, H_.y, z)), Vector((V_.x, V_.y, z)),
                     Vector((*Lv.at(set_end + sg * 0.10), z))]
            home, _ = _round3(sharp, [0, rh, rh, rh, 0])
        assert all(Lv.span(set_end, e[1], sg) > 0.10 + (ext(e[3]) + ib[0] / 2 if e[2] in ("dev", "hub") else ib[0]) for e in node["ev"]), \
            f"{C['id']}: a box before its run is on the wall"
        cw = rec(s_k)   # its level run behind the wall's plaster face (bending level in the chase) is grooved too
        uc_ = (Vector((*Lv.at(s_k + 0.01), 0)) - Vector((*Lv.at(s_k - 0.01), 0))).normalized()   # the chase's wall runs this way
        wls = [l for l in _wlines(WALL_LINES, OFFSET).values() if abs(uc_[l["ax"]]) > 0.99
               and abs(cw[1 - l["ax"]] - l["k"]) < WALL["t"] / 2 + WALL["pl"] and l["u0"] - 0.2 < cw[l["ax"]] < l["u1"] + 0.2]
        assert len(wls) == 1, f"{C['id']}: the CU's chase is in {len(wls)} wall lines"
        wl = wls[0]
        sd = 1 if nin[1 - wl["ax"]] > 0 else -1
        fk = wl["k"] + sd * (WALL["t"] / 2 + WALL["pl"])
        lvl = 0.0
        for p, q in zip(home, home[1:]):   # level pieces behind the face (a piece crossing it: its part behind)
            dp, dq = (p[1 - wl["ax"]] - fk) * sd, (q[1 - wl["ax"]] - fk) * sd
            if abs(q.z - p.z) < CD["level_dz"] and min(dp, dq) < 0:
                lvl += (q - p).xy.length * (1.0 if max(dp, dq) <= 0 else min(dp, dq) / (min(dp, dq) - max(dp, dq)))
        # (chase entries are (id, piece, xy, bot, top) and only top − bot is read: the groove's length. This one's
        # top carries the level run on top of the rise, so it is a length, not a height)
        out["chase"].append((C["id"], "CU", tuple(top.xy), top.z, z + lvl))   # up its own groove over the CU (+ the level run)
        walk_visit(node, home, z, C, pl)

    # ---- the hubs: every piece passing straight through one ends there and goes on from its far side ----
    used_hubs, plate_box = set(), {}
    for h, (room_, kind_, s_, ln_, zc_) in enumerate(HUBS):
        Hc = Vector((*ln_.at(s_), zc_ or 0.0))
        t_ = (Vector((*ln_.at(s_ + 0.01), 0)) - Vector((*ln_.at(s_ - 0.01), 0))).normalized()
        w_ = (pb if kind_ == "band" else ib)[0] / 2
        new = []
        for pc in out["pieces"]:
            route, cid, to, P, size, ws = pc
            for i in range(1, len(P)):
                a, b = P[i - 1], P[i]
                ua, ub = (a - Hc).dot(t_), (b - Hc).dot(t_)
                lat = max(abs((a - Hc - t_ * ua).xy.length), abs((b - Hc - t_ * ub).xy.length))
                if kind_ == "band":   # a shared 4×4: every run within its height
                    in_ = abs(a.z - zc_) < pb[1] / 2 - EL["conduit"][size] / 2 and lat < CD["slot"] + 0.005
                else:                 # a 2×4 on the plate: the one run passing there, at its own height
                    in_ = a.z > 3.45 and lat < 4 * CD["slot"] + 0.005 and h not in plate_box and route == (CD["hubs"][h][3:] or [None])[0]
                if abs(a.z - b.z) < 1e-6 and in_ and min(ua, ub) < -w_ and max(ua, ub) > w_:
                    d_ = 1 if ub > ua else -1
                    E1 = a + (b - a) * ((-d_ * w_ - ua) / (ub - ua))
                    E2 = a + (b - a) * ((d_ * w_ - ua) / (ub - ua))
                    if kind_ == "plate":
                        plate_box[h] = (E1 + E2) / 2
                    new.append([route, cid, f"HUB{h}", P[:i] + [E1], size, ws])
                    pc[3] = [E2] + P[i:]
                    for w, k in ws:   # each new piece end its slack (the wire = every piece's length + slack at both ends)
                        out["wire"][w] += k * (2 * EL["slack"] - (E2 - E1).length)
                    out["vlen"][size] -= (E2 - E1).length   # (no clips inside the box)
                    used_hubs.add(h)
                    break
            new.append(pc)
        out["pieces"] = new
    for h in sorted(used_hubs):
        room_, kind_, s_, ln_, zc_ = HUBS[h]
        t_ = (Vector((*ln_.at(s_ + 0.01), 0)) - Vector((*ln_.at(s_ - 0.01), 0))).normalized()
        out["boxes"].append((Vector((*ln_.at(s_), zc_)), -t_, pb) if kind_ == "band" else (plate_box[h], -t_, ib))
    out["runs"] = {}
    for route, cid, to, P, size, ws in out["pieces"]:
        out["runs"].setdefault(size, []).append((cid, to, P))
    out["hubs"] = [CD["hubs"][h] for h in sorted(used_hubs)]

    # ground (spec 30 ต.ค.: not down the outside face): CU bottom, straight down a chase in the wall, bent into the
    # floor slab under the wall (the bend clears the wall face below the slab top FL − 0.03), down through the fill
    # inside the ground beam, under the beam and out to the rod 0.5 m outside the wall, 0.30 deep (laid before the pour)
    cn = cu["n"]
    g0 = cu["p"] - cn * 0.02 + Vector((0, 0, -EL["cu"]["size"][1] / 2))
    ch = cu["p"] - cn * (CD["dc"] + 0.02)   # in the chase, as the drops
    z_sl, z_bur = FL - 0.065, GL - 0.30
    x_in = ch.x + cn.x * 0.30   # inside the ground beam under the wall
    g1 = _drop_in(g0, Vector((ch.x, ch.y, 0)), g0.z - 0.25)   # (the CU is flush: already behind the face)
    sharp = [g1[-1], Vector((ch.x, ch.y, z_sl)), Vector((x_in, ch.y, z_sl)), Vector((x_in, ch.y, z_bur)),
             Vector((ch.x - cn.x * 0.59, ch.y, z_bur))]
    g2, _ = _round3(sharp, [0, r0, r0, r0, 0])
    gw = g1 + g2[1:]
    out["runs"].setdefault("1/2", []).append(("GND", "ROD", gw))
    out["chase"].append(("GND", "ROD", (ch.x, ch.y), FL - 0.03, g0.z))
    out["wire"]["G10"] = _path_len(gw) + 2 * EL["slack"]
    out["gw"] = gw
    out["lines"], out["levels"], out["plk"] = lines, lev, PLK
    out["fixed"] = {r_: [(f, reach(r_) + pb[0] / 2 + 0.10) for f in fixed[r_]] + ([(s_cu, HOME + 0.25 + pb[0] / 2)] if r_ == "Living" else [])
                    for r_ in rooms}   # (hubs keep off the loops, and off the CU's home runs)
    return out
