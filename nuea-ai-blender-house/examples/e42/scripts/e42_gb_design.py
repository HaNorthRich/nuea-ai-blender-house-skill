"""E42 ground beams: load on every span (beam_wsd, the engineer's WSD method) → which SS-02 S-22 type per line.
Headless:  Blender -b E42_house.blend --factory-startup --python-exit-code 1 -P scripts/e42_gb_design.py
"""
import itertools, os, bpy

HERE = os.path.dirname(bpy.data.filepath)
exec(bpy.data.texts["house_helpers"].as_string())
exec(open(os.path.join(HERE, "scripts", "e42_struct.py")).read())
exec(open(os.path.join(globals().get("SKILL_SCRIPTS") or os.path.expanduser("~/.claude/skills/nuea-ai-blender-house/scripts"), "beam_wsd.py")).read())

SLAB_ON_BEAMS = False                           # spec 28 ต.ค.: cast slab on ground (fill to beam top) — no slab load
SLAB_T = 0.10                                   # used only for a slab carried by the beams (suspended or precast)
SLAB_DL, SLAB_LL = SLAB_T * CRIT["rc"] + CRIT["finish"], CRIT["ll_floor"]      # 360 + 200 kg/m²
PANELS = [("ห้องนอน 2", "A1", "C2"), ("ห้องน้ำ", "C1", "D2"), ("ห้องนอน 1", "D1", "E2"),
          ("ห้องนั่งเล่น-ครัว", "B2", "E3"), ("ระเบียง", "A2", "B3")]          # slab panels between beams
WALLS = [("A1", "A2"), ("E1", "E3"), ("A1", "E1"), ("B3", "E3"), ("B2", "B3"), ("A2", "B2"), ("B2", "E2"),
         ("C1", "C2"), ("D1", "D2")]           # e42_build build_walls: every wall stands on a ground beam
RB_BOT = 3.45                                   # wall top = column top under the wall plate (spec 28 ต.ค.)
B, DIA = round(GBEAM["b"] * 100), round(GBEAM["d"] * 1000)   # 20 cm wide, DB12; depth per type (BEAM_TYPES)
# Types from e42_struct BEAM_TYPES / LINE_TYPE: tension bars = 2 continuous + n_sp specials (GB1 = S-22 GB1 with its
# special bar on the tension side, spec 28 ต.ค.; GB4 0.20 × 0.50 for the 4.50 m beams carrying secondary beams).
# S-22 GB2/GB3 mix their labels like GB1 and are not confirmed. (The engineer's calc PDF has its own GB1–GB3.)


def _along(seg, e0, e1):
    """(u0, u1) of span seg measured from e0 along the line e0–e1, or None when seg is not on it."""
    ax = 0 if abs(e0[1] - e1[1]) < 1e-9 else 1
    assert abs(e0[1 - ax] - e1[1 - ax]) < 1e-9 or abs(e0[ax] - e1[ax]) < 1e-9, f"{e0}-{e1} not along a grid line"
    (p, q), lo, hi = seg, min(e0[ax], e1[ax]), max(e0[ax], e1[ax])
    if abs(p[1 - ax] - e0[1 - ax]) > 1e-9 or abs(q[1 - ax] - e0[1 - ax]) > 1e-9:
        return None
    a, b = sorted((p[ax], q[ax]))
    if b <= lo + 1e-9 or a >= hi - 1e-9:
        return None
    assert lo - 1e-9 <= a and b <= hi + 1e-9, f"span {seg} only partly on {e0}-{e1}: load would be lost"
    return a - lo, b - lo


def loads():
    """{span id: [dead, live, why]} kg/m; every wall and every panel edge must land on spans for its full length."""
    spans = {}
    for name, ax, o, top, G, on in _gb_lines():
        pts = [((o[0] + u, o[1]) if ax == 0 else (o[0], o[1] + u)) for u, _ in on]
        for i, seg in enumerate(zip(pts, pts[1:])):
            sw = GBEAM["b"] * _bt(name)[1]["h"] * CRIT["rc"]
            spans[(name, i)] = (seg, [sw, 0.0, [f"คาน {sw:.0f}"]], top)
    for a, b in WALLS:
        e0, e1 = _xy(a), _xy(b)
        got = 0.0
        for seg, ld, top in spans.values():
            if (r := _along(seg, e0, e1)):
                w = CRIT["wall"] * (RB_BOT - top)
                ld[0] += w
                ld[2].append(f"ผนัง {w:.0f}")
                got += r[1] - r[0]
        assert abs(got - abs(e1[0] - e0[0]) - abs(e1[1] - e0[1])) < 1e-9, f"wall {a}-{b} not fully on beams"
    for pn, c0, c1 in (PANELS if SLAB_ON_BEAMS else ()):
        (x0, y0), (x1, y1) = _xy(c0), _xy(c1)
        sx, sy = x1 - x0, y1 - y0
        assert sx > 0 and sy > 0, f"panel {pn}: corners {c0} {c1}"
        for e0, e1, ln in (((x0, y0), (x1, y0), sx), ((x0, y1), (x1, y1), sx),
                           ((x0, y0), (x0, y1), sy), ((x1, y0), (x1, y1), sy)):
            got = 0.0
            for seg, ld, _ in spans.values():
                if (r := _along(seg, e0, e1)):
                    short = ln == min(sx, sy)
                    f = edge_load(sx, sy, 1.0, r[0], r[1], short)
                    ld[0], ld[1] = ld[0] + f * SLAB_DL, ld[1] + f * SLAB_LL
                    ld[2].append(f"{pn} {f * (SLAB_DL + SLAB_LL):.0f}")
                    got += r[1] - r[0]
            assert abs(got - ln) < 1e-9, f"panel {pn}: edge {e0}-{e1} not fully on beams"
    return spans


def design():
    dd = lambda tn: depth(BEAM_TYPES[tn]["h"] * 100, cover=GBEAM["cover"] * 100, stirrup=GBEAM["dt"] * 100,
                          bar=GBEAM["d"] * 100)
    sp = loads()
    out = [f"{tn} {B}×{bt['h'] * 100:.0f}: d = {dd(tn):.1f} ซม. · เหล็กรับแรงดึง {2 + bt['n_sp']}-DB12 รับได้ "
           f"{capacity(2 + bt['n_sp'], DIA, B, dd(tn)):.0f} · เสริมเดี่ยวสูงสุด {R * B * dd(tn) ** 2 / 100:.0f} กก.-ม."
           for tn, bt in BEAM_TYPES.items()]
    stubs = {g for gs in STUB_GRIDS.values() for g in gs}
    lines = {l[0]: l for l in _gb_lines()}
    # one continuous beam = collinear lines joined at an end with no column under it (bars run through the joint);
    # its supports are the columns on it and its own ends; a beam ending on another one loads it with its reaction
    chain = {n: n for n in lines}
    root = lambda n: n if chain[n] == n else root(chain[n])
    for a, b in itertools.combinations(lines, 2):
        la, lb = lines[a], lines[b]
        if la[1] == lb[1] and la[2][1 - la[1]] == lb[2][1 - lb[1]] and \
                ({la[5][0][1], la[5][-1][1]} & {lb[5][0][1], lb[5][-1][1]}) - stubs:
            chain[root(a)] = root(b)
    beams = {}
    for n in lines:
        beams.setdefault(root(n), []).append(n)
    info = {}
    for r_, names in beams.items():
        ax = lines[names[0]][1]
        nodes = sorted({(lines[n][2][ax] + u, g) for n in names for u, g in lines[n][5]})
        segs = [(sp[(n, i)][0][0][ax], sp[(n, i)][0][1][ax], sp[(n, i)][1]) for n in names
                for i in range(len(lines[n][5]) - 1)]
        sup = [(u, g) for u, g in nodes if g in stubs or (u, g) in (nodes[0], nodes[-1])]
        info[r_] = dict(names=names, ax=ax, nodes=nodes, segs=segs, sup=sup)
    rest = {}   # node → [beams resting there with an end that has no column]
    for r_, b in info.items():
        for u, g in (b["nodes"][0], b["nodes"][-1]):
            if g not in stubs:
                rest.setdefault(g, []).append(r_)
    react, used, pick, done = {}, set(), {}, set()
    while len(done) < len(info):
        ready = [r_ for r_, b in info.items() if r_ not in done and all(
            s in done for u, g in b["nodes"][1:-1] if g not in stubs for s in rest.get(g, []) if s != r_)]
        assert ready, "beams resting on each other in a loop"
        for r_ in ready:
            b = info[r_]
            us = [u for u, _ in b["sup"]]
            spans = [v - u for u, v in zip(us, us[1:])]
            lds = [[] for _ in spans]
            for u0, u1, ld in b["segs"]:
                i = max(j for j, u in enumerate(us[:-1]) if u <= min(u0, u1) + 1e-9)
                lds[i].append((min(u0, u1) - us[i], max(u0, u1) - us[i], ld[0], ld[1]))
            pts = []
            for u, g in b["nodes"]:
                if (u, g) not in b["sup"] and g in react:   # a secondary beam's reaction, where no column takes it
                    i = max(j for j, x in enumerate(us[:-1]) if x <= u + 1e-9)
                    lds[i].append((u - us[i], u - us[i], *react[g]))
                    used.add(g)
                    pts.append(f"{g} {react[g][0] + react[g][1]:.0f} กก.")
            env, rd, rl = beam_loads(spans, lds)
            for j, (u, g) in enumerate(b["sup"]):   # ends resting on another beam pass their reaction on
                if g not in stubs:
                    react[g] = (react.get(g, (0, 0))[0] + rd[j], react.get(g, (0, 0))[1] + rl[j])
            mpos = max(e[0] for e in env)
            mneg = max(0.0, max(-min(e[1], e[2]) for e in env))
            vmax = max(e[3] for e in env)
            tns = {_bt(n)[0] for n in b["names"]}
            assert len(tns) == 1, f"one continuous beam, two types: {b['names']}"
            tn = tns.pop()
            d, nb = dd(tn), 2 + BEAM_TYPES[tn]["n_sp"]   # tension bars: 2 continuous + the specials
            t = tn if bars_ok(nb, DIA, mpos, B, d) and bars_ok(nb, DIA, mneg, B, d) else None
            ok_v = shear_ok(vmax, B, d)
            for n in b["names"]:
                pick[n] = t if ok_v else None
            out.append(f"{' + '.join(b['names'])}: ช่วงรองรับ {' · '.join(f'{L:.2f}' for L in spans)} ม. · รองรับที่ "
                       f"{', '.join(g for _, g in b['sup'])}" + (f" · แรงจุดจากคานฝาก {', '.join(pts)}" if pts else ""))
            out.append(f"    M+ {mpos:.0f} · M− {mneg:.0f} กก.-ม. · V {vmax:.0f} กก. {'ok' if ok_v else 'เฉือนไม่ผ่าน'}"
                       f" → {tn} {'ผ่าน' if pick[b['names'][0]] else 'ไม่ผ่าน: ต้องใช้คานใหญ่ขึ้น'}")
            done.add(r_)
    # a beam end with no column must rest inside another beam: a reaction nobody takes would be lost load
    assert set(react) <= used, f"reactions with no beam to take them: {sorted(set(react) - used)}"
    return "\n".join(out), pick


print(selftest())
txt, PICK = design()
print(txt)
print(PICK)
