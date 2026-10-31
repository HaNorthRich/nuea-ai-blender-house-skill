"""Line drawings from the model as DXF that AutoCAD opens directly: 4 elevations, a top view, 2 sections.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<file>.blend" -P drawings.py -- --out "<dir>" \
        [--name CM3] [--section-y 3.0] [--section-x 4.6] [--skip "Ground,Road,..."]

Hidden lines are removed by ray casting, and a line is kept only where the surface really changes across it
(depth step, fold or outline) — seams between wall pieces and triangulation edges drop out. Section cut lines go
on their own layer (A-SECT). Units: millimetres. DXF R12 (AC1009): every AutoCAD opens it; SAVEAS DWG there, or
convert with ODA File Converter. An SVG preview is written next to every DXF for checking.

Included: render-visible mesh/curve objects of the view layer (excluded collections drop out, e.g. Poly Haven
source assets parked at the origin) outside collections named *Landscape*, *Interior* and ASSET_*, minus --skip
patterns (fnmatch: "Car" is exact, "Road*" a prefix) matched on the object or any parent. Roof tiles are skipped by default: the *_Hip underlay and the caps
give the roof outline; drawing every tile makes an unreadable elevation.
"""
import argparse
import fnmatch
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SKIP = ("Ground", "Road*", "Plan_WallCaps", "Car", "*_CPAC_Tiles", "*_Battens")   # "Car" must not catch "Carport"
LAYERS = {"A-ELEV": 7, "A-SECT": 1, "A-GLAZ": 4, "A-ROOF": 30, "A-SITE": 8, "A-GRND": 8, "A-TEXT": 2}
ELEV_SKIP = ("Fence*",)   # elevations and sections show the building; the fence stays in the top view
STEP, EPS, DEPTH_TOL, CREASE_COS = 0.04, 0.01, 0.008, math.cos(math.radians(8))
MIN_LINE = 0.06   # m; shorter *partial* pieces are noise at 1:100 (whole short edges, e.g. arc segments, stay)
ROUND_COS = math.cos(math.radians(40))   # bevelled tubes (ridge caps): facet folds are not lines, only the outline
OCC_TOL = 0.001   # occlusion: a wing roof 2 mm under the main roof must count as hidden (CM3)


def layer_of(name):
    n = name.lower()
    if "glass" in n:
        return "A-GLAZ"
    if n.startswith(("roof", "gutter")) or "valley" in n:
        return "A-ROOF"
    if n.startswith(("fence", "paving", "driveway", "patio", "slab")):
        return "A-SITE"
    return "A-ELEV"


def pick_objects(skip):
    def skipped(o):
        while o:
            if any(fnmatch.fnmatchcase(o.name, s) for s in skip):
                return True
            o = o.parent
        return False
    parent = {ch: c for c in bpy.data.collections for ch in c.children}

    def chain(c):   # the collection and every parent above it
        while c:
            yield c
            c = parent.get(c)
    out, hidden = [], []
    for o in bpy.context.view_layer.objects:
        if o.type not in ("MESH", "CURVE") or skipped(o):
            continue
        cols = [p for c in o.users_collection for p in chain(c)]
        if any("Landscape" in c.name or "Interior" in c.name or c.name.startswith("ASSET_") for c in cols):
            continue
        if o.hide_render or any(c.hide_render for c in cols):
            hidden.append(o.name)   # hidden for a cutaway render? it would vanish from the drawings silently
            continue
        out.append(o)
    if hidden:
        print(f"skipped {len(hidden)} render-hidden objects: {', '.join(hidden[:12])}{' ...' if len(hidden) > 12 else ''}")
    return out


def world_meshes(objs):
    """[(name, verts world, edges, polys)] from evaluated objects (modifiers and curve bevels applied)."""
    dg = bpy.context.evaluated_depsgraph_get()
    res = []
    for o in objs:
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        mw = e.matrix_world
        res.append((o.name, [mw @ v.co for v in me.vertices], [tuple(ed.vertices) for ed in me.edges],
                    [tuple(p.vertices) for p in me.polygons]))
        e.to_mesh_clear()
    return res


class Scene:
    def __init__(self, meshes):
        verts, polys = [], []
        for _, vs, _, ps in meshes:
            k = len(verts)
            verts += vs
            polys += [tuple(i + k for i in p) for p in ps]
        self.tree = BVHTree.FromPolygons(verts, polys)

    def hit(self, o, d, maxd):
        """First hit along d, skipping faces seen edge-on (they make visibility flicker)."""
        start = 0.0
        for _ in range(4):
            loc, n, _, dist = self.tree.ray_cast(o + d * start, d, maxd - start)
            if loc is None:
                return None
            if abs(n.dot(d)) > 0.02:
                return start + dist, n
            start += dist + 1e-4
        return None


class View:
    def __init__(self, key, title, d, right, up, cut=None):
        self.key, self.title = key, title
        self.d, self.u, self.v = Vector(d).normalized(), Vector(right), Vector(up)
        self.cut = Vector(cut) if cut else None   # a point on the section plane (plane normal = d)

    def origin(self, p):
        """Ray start for point p: on the section plane, or far in front of the model."""
        if self.cut is None:
            return p - self.d * 200.0, 200.0
        s = (p - self.cut).dot(self.d) - 1e-3   # start 1 mm past the plane: a wall face on the plane must not hide all
        return p - self.d * s, s

    def xy(self, p):
        return p.dot(self.u), p.dot(self.v)


def visible_lines(view, scene, meshes):
    lines = []
    for name, vs, edges, _ in meshes:
        lay = layer_of(name)
        crease = ROUND_COS if name.endswith("_Caps") else CREASE_COS
        for i, j in edges:
            a, b = vs[i], vs[j]
            if view.cut is not None:   # keep the part beyond the section plane
                sa, sb = (a - view.cut).dot(view.d), (b - view.cut).dot(view.d)
                if sa < 1e-3 and sb < 1e-3:
                    continue
                if sa < 1e-3 or sb < 1e-3:
                    t = (1e-3 - sa) / (sb - sa)
                    a, b = (a.lerp(b, t), b) if sa < 1e-3 else (a, a.lerp(b, t))
            L = (b - a).length
            if L < 0.003:
                continue
            edir = (b - a) / L
            perp = view.d.cross(edir)
            if perp.length < 1e-6:   # edge along the view direction projects to a point
                continue
            perp.normalize()
            n = max(1, math.ceil(L / STEP))
            vis, real = [], []
            for k in range(n + 1):
                p = a.lerp(b, k / n)
                o, dp = view.origin(p)
                if scene.hit(o, view.d, dp - OCC_TOL):
                    vis.append(False)    # something in front
                    real.append(False)
                    continue
                vis.append(True)
                ha = scene.hit(o + perp * EPS, view.d, dp + 50)
                hb = scene.hit(o - perp * EPS, view.d, dp + 50)
                if (ha is None) != (hb is None) or (ha is None and hb is None):
                    real.append(True)    # outline
                else:
                    step = abs(ha[0] + hb[0] - 2 * dp) > DEPTH_TOL       # depth step across the line
                    fold = abs(ha[1].dot(hb[1])) < crease                # surface turns across the line
                    real.append(step or fold)
            for k in range(1, n):   # a probe landing on a crossing edge behind drops 1-2 samples: close those gaps
                if vis[k] and not real[k] and real[k - 1]:
                    j = k
                    while j < n and vis[j] and not real[j] and j - k < 2:
                        j += 1
                    if real[j]:
                        for m in range(k, j):
                            real[m] = True
            start = None
            for k, v in enumerate(real + [False]):
                if v and start is None:
                    start = k
                elif not v and start is not None:
                    whole = start == 0 and k - 1 == n
                    if k - 1 > start and (whole or (k - 1 - start) / n * L >= MIN_LINE):
                        lines.append((lay, view.xy(a.lerp(b, start / n)), view.xy(a.lerp(b, (k - 1) / n))))
                    start = None
    return lines


def cut_lines(view, meshes):
    out = []
    for name, vs, edges, polys in meshes:
        bm = bmesh.new()
        bv = [bm.verts.new(v) for v in vs]
        for p in polys:
            try:
                bm.faces.new([bv[i] for i in p])
            except ValueError:   # duplicate face in the source mesh
                pass
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=view.cut, plane_no=view.d)
        lay = "A-GLAZ" if layer_of(name) == "A-GLAZ" else "A-SECT"
        for e in res["geom_cut"]:
            if isinstance(e, bmesh.types.BMEdge):
                out.append((lay, view.xy(e.verts[0].co), view.xy(e.verts[1].co)))
        bm.free()
    return out


def _normal(vs, p):
    return (vs[p[1]] - vs[p[0]]).cross(vs[p[2]] - vs[p[0]]).normalized()


def trim_roofs(meshes):
    """Remove the parts of smaller *_Hip roofs that lie under the largest one (drawings only, the model is untouched).

    An L/T wing roof is modelled whole; the part under the main roof is not built, so it must not show as cut or
    hidden lines (CM3 section B). The wing is split along the main roof's face planes and footprint edges, then every
    piece whose centre has the main roof's top surface above it is deleted.
    """
    roofs = [i for i, m in enumerate(meshes) if m[0].endswith("_Hip")]
    if len(roofs) < 2:
        return meshes
    area = lambda vs: (max(v.x for v in vs) - min(v.x for v in vs)) * (max(v.y for v in vs) - min(v.y for v in vs))
    dom = max(roofs, key=lambda i: area(meshes[i][1]))
    _, dvs, _, dps = meshes[dom]
    tops = [p for p in dps if len(p) >= 3 and _normal(dvs, p).z > 0.3]
    tree = BVHTree.FromPolygons(dvs, tops)
    planes = []
    for p in tops:
        planes.append((dvs[p[0]], _normal(dvs, p)))
        for k in range(len(p)):
            a, b = dvs[p[k]], dvs[p[(k + 1) % len(p)]]
            no = (b - a).cross(Vector((0, 0, 1)))
            if no.length > 1e-6:
                planes.append((a, no.normalized()))
    out = list(meshes)
    for i in roofs:
        if i == dom:
            continue
        name, vs, _, polys = meshes[i]
        bm = bmesh.new()
        bv = [bm.verts.new(v) for v in vs]
        for p in polys:
            try:
                bm.faces.new([bv[j] for j in p])
            except ValueError:
                pass
        for co, no in planes:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6, plane_co=co, plane_no=no)
        up = Vector((0, 0, 1))
        dead = [f for f in bm.faces if tree.ray_cast(f.calc_center_median() + up * 1e-4, up, 20.0)[0] is not None]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
        bm.verts.index_update()
        out[i] = (name, [v.co.copy() for v in bm.verts], [tuple(v.index for v in e.verts) for e in bm.edges],
                  [tuple(v.index for v in f.verts) for f in bm.faces])
        bm.free()
    return out


def dedupe(lines):
    seen, out = set(), []
    for lay, p, q in lines:
        a, b = (round(p[0], 3), round(p[1], 3)), (round(q[0], 3), round(q[1], 3))
        key = (min(a, b), max(a, b))
        if a != b and key not in seen:
            seen.add(key)
            out.append((lay, p, q))
    return out


def bounds(lines):
    xs = [c[0] for _, p, q in lines for c in (p, q)]
    ys = [c[1] for _, p, q in lines for c in (p, q)]
    return min(xs), min(ys), max(xs), max(ys)


def annotate(view, lines, ground):
    x0, y0, x1, y1 = bounds(lines)
    if ground:   # ±0.00 ground line under elevations and sections
        lines.append(("A-GRND", (x0 - 1.0, 0.0), (x1 + 1.0, 0.0)))
    return [("A-TEXT", (x0, min(y0, 0.0) - 0.9), f"{view.title}   SCALE 1:100   UNITS mm", 0.25)]


def write_dxf(path, lines, texts, off=(0.0, 0.0)):
    """Minimal DXF R12: LTYPE + LAYER tables, LINE and TEXT entities; model units = mm."""
    mm = lambda v, o: f"{(v + o) * 1000:.1f}"
    out = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "0", "ENDSEC",
           "0", "SECTION", "2", "TABLES",
           "0", "TABLE", "2", "LTYPE", "70", "1",
           "0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line", "72", "65", "73", "0", "40", "0.0",
           "0", "ENDTAB", "0", "TABLE", "2", "LAYER", "70", str(len(LAYERS))]
    for name, color in LAYERS.items():
        out += ["0", "LAYER", "2", name, "70", "0", "62", str(color), "6", "CONTINUOUS"]
    out += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for lay, p, q in lines:
        out += ["0", "LINE", "8", lay, "10", mm(p[0], off[0]), "20", mm(p[1], off[1]), "30", "0.0",
                "11", mm(q[0], off[0]), "21", mm(q[1], off[1]), "31", "0.0"]
    for lay, p, s, h in texts:
        out += ["0", "TEXT", "8", lay, "10", mm(p[0], off[0]), "20", mm(p[1], off[1]), "30", "0.0",
                "40", f"{h * 1000:.1f}", "1", s]
    out += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(out) + "\n")


def write_svg(path, lines, texts):
    colors = {"A-ELEV": "#222", "A-SECT": "#c0392b", "A-GLAZ": "#1f8fb5", "A-ROOF": "#a35a00", "A-SITE": "#888",
              "A-GRND": "#888", "A-TEXT": "#222"}
    widths = {"A-SECT": 2.2}
    x0, y0, x1, y1 = bounds(lines + [(None, t[1], t[1]) for t in texts])
    s, pad = 80, 30
    W, H = (x1 - x0) * s + 2 * pad, (y1 - y0) * s + 2 * pad
    X = lambda x: (x - x0) * s + pad
    Y = lambda y: (y1 - y) * s + pad
    el = [f'<line x1="{X(p[0]):.1f}" y1="{Y(p[1]):.1f}" x2="{X(q[0]):.1f}" y2="{Y(q[1]):.1f}" '
          f'stroke="{colors.get(l, "#222")}" stroke-width="{widths.get(l, 0.8)}"/>' for l, p, q in lines]
    el += [f'<text x="{X(p[0]):.1f}" y="{Y(p[1]):.1f}" font-size="{h * s:.0f}" font-family="Helvetica">{t}</text>'
           for _, p, t, h in texts]
    with open(path, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}">'
                f'<rect width="100%" height="100%" fill="#fff"/>{"".join(el)}</svg>')


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="HOUSE")
    ap.add_argument("--section-y", type=float, default=3.0, help="section A-A: plane y = this, looking to the rear")
    ap.add_argument("--section-x", type=float, default=4.6, help="section B-B: plane x = this, looking to +x")
    ap.add_argument("--skip", default="", help="extra fnmatch patterns, added to the defaults")
    ap.add_argument("--no-default-skip", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    objs = pick_objects([s for s in a.skip.split(",") if s] + ([] if a.no_default_skip else list(SKIP)))
    assert objs, "no objects to draw (all filtered out?)"
    plan_meshes = trim_roofs(world_meshes(objs))
    elev_meshes = [m for m in plan_meshes if not any(fnmatch.fnmatchcase(m[0], s) for s in ELEV_SKIP)]
    sets = {True: (plan_meshes, Scene(plan_meshes)), False: (elev_meshes, Scene(elev_meshes))}
    print(f"{len(objs)} objects, {sum(len(m[2]) for m in plan_meshes)} edges")
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    views = [View("01_FRONT", "FRONT ELEVATION", Y, X, Z), View("02_REAR", "REAR ELEVATION", (0, -1, 0), (-1, 0, 0), Z),
             View("03_LEFT", "LEFT ELEVATION", X, (0, -1, 0), Z), View("04_RIGHT", "RIGHT ELEVATION", (-1, 0, 0), Y, Z),
             View("05_TOP", "TOP VIEW (ROOF PLAN)", (0, 0, -1), X, Y),
             View("06_SECTION_A", f"SECTION A-A (Y = {a.section_y:.2f} m, LOOKING TO REAR)", Y, X, Z, (0, a.section_y, 0)),
             View("07_SECTION_B", f"SECTION B-B (X = {a.section_x:.2f} m, LOOKING TO +X)", X, (0, -1, 0), Z, (a.section_x, 0, 0))]
    sheet, ox = [], 0.0
    for v in views:
        meshes, scene = sets[v.key == "05_TOP"]
        lines = visible_lines(v, scene, meshes) + (cut_lines(v, meshes) if v.cut is not None else [])
        lines = dedupe(lines)
        if not lines:
            sys.exit(f"{v.key}: no lines - is the section plane outside the model?")
        texts = annotate(v, lines, ground=v.key != "05_TOP")
        base = os.path.join(a.out, f"{a.name}_{v.key}")
        write_dxf(base + ".dxf", lines, texts)
        write_svg(base + ".svg", lines, texts)
        x0, _, x1, _ = bounds(lines)
        sheet.append((lines, texts, ox - x0))
        ox += (x1 - x0) + 4.0
        print(f"{v.key}: {len(lines)} lines -> {base}.dxf")
    all_lines = [(l, (p[0] + dx, p[1]), (q[0] + dx, q[1])) for ls, _, dx in sheet for l, p, q in ls]
    all_texts = [(l, (p[0] + dx, p[1]), t, h) for _, ts, dx in sheet for l, p, t, h in ts]
    write_dxf(os.path.join(a.out, f"{a.name}_00_ALL_VIEWS.dxf"), all_lines, all_texts)
    print("DONE")


if __name__ == "__main__":
    main()
