# ST12 MAIN (spec 31 ต.ค.: overhead, the drop down the outside wall): the service from the meter on porch column A3
# to the CU, THW 16 (L + N) in 1" PVC, field bends ≥ 146 mm. Up the column's east face, through the soffit into the east
# eave void, north along the east wall's outer face over the soffit, down that face behind the CU into a TOP 4×4 there
# (a 1" bend needs 146 mm: no room for it at the wall), straight through the wall into the CU's back. No pull box in
# the house; nothing crosses the living room's band. Exec after e42_conduit_route.py (spec ../ST12_conduit_spec.md, 3b).
MAIN = dict(size="1", z_run=3.42, wires=[("16", 2)],   # (z_run: under the wall plate, near it past the open porch side)
            riser=(6.18, -0.03),   # up past the soffit's edge runner (x ≤ 6.151) between two cross runners, on stand-off clips
            meter=(0.15, 0.25, 0.40), meter_z=1.80,   # (across, along, height) of the meter board on the column; its centre
            th_meter="แผงยึดมิเตอร์ไฟฟ้า + ฐานมิเตอร์ บนเสา A3 (มิเตอร์ของการไฟฟ้า — ตำแหน่งสมมติ)")


def _main_soffit_holes(pts):
    """Where MAIN goes through the eave's soffit board (plan): its riser and its drop behind the CU — 2 holes."""
    xr, yr = MAIN["riser"]
    return [(xr, yr), (xr, pts["CU"]["p"].y)]


def _main_run(out, pts):
    """Lay MAIN into out (runs, boxes, wire, vlen, cross) and → the meter board (centre, half sizes)."""
    cu = pts["CU"]
    V = _voids()
    xo = V["Eave"][0][0]                     # the east wall's (and column A3's) outer face
    r = CD["rmin"][MAIN["size"]]
    pb = EL["box44"]["size"]
    yc, zc = cu["p"].y, cu["p"].z             # the CU's back: its centre on the inner face
    B = Vector((xo + pb[2] / 2, yc, zc))      # the 4×4 on the outer face behind it, lid out
    xr, yr = MAIN["riser"]                    # the riser and the run along the eave; the drop leans in to the box
    md, mw, mh = MAIN["meter"]
    M = Vector((xo + md / 2, GY["A"], MAIN["meter_z"]))   # (meter_z: its centre over the ground outside, GL 0)
    assert xo < xr < xo + md and abs(yr - M.y) < mw / 2, "MAIN: the riser is not over the meter board"
    zr = MAIN["z_run"]
    assert zr + EL["conduit"][MAIN["size"]] / 2 < CD["top"] and zr - r > V["Eave"][2], "MAIN: its run is not between the soffit and the wall plate"
    # the drop stays out past the edge runner through the soffit board, then a shallow 2-bend offset below it brings it in
    # onto the wall over the box's top knockout, plumb down into it
    zs = V["Eave"][2]
    a = _bend_angle(xr - B.x, r, math.radians(CD["off_deg"]))
    zA = zs - 0.03 - r * math.tan(a / 2)
    zB = zA - (xr - B.x) / math.tan(a)
    sharp = [Vector((xr, yr, M.z + mh / 2)), Vector((xr, yr, zr)), Vector((xr, yc, zr)), Vector((xr, yc, zA)), Vector((B.x, yc, zB)),
             Vector((B.x, yc, zc + pb[1] / 2))]
    up, _ = _round3(sharp, [0, r, r, r, r, 0])
    thru = [Vector((xo + 0.001, yc, zc)), Vector((cu["p"].x - 0.001, yc, zc))]   # (a hole straight through, into the CU's back)
    for to, P in (("MAIN_box", up), ("CU", thru)):
        out["runs"].setdefault(MAIN["size"], []).append(("MAIN", to, P))
        L = sum((q - p).length for p, q in zip(P, P[1:]))
        for w, k in MAIN["wires"]:
            out["wire"][w] = out["wire"].get(w, 0.0) + k * (L + 2 * EL["slack"])
        out["vlen"][MAIN["size"]] = out["vlen"].get(MAIN["size"], 0.0) + (L if to == "MAIN_box" else 0.0)   # (clipped all along: outdoors)
    out["boxes"].append((B, Vector((0, 1, 0)), pb))   # (lid on t × Z = +x: out)
    out["cross"] += 1
    return M, Vector((md / 2, mw / 2, mh / 2))
