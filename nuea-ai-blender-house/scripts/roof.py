"""Hip roof (ปั้นหยา) + eave soffit + CPAC-style wave tiles + hip/ridge caps.

Needs helpers.py exec'd first (col, mat, box, PROJ). Load like helpers.py into a text block
"house_roof", then:
    exec(bpy.data.texts["house_helpers"].as_string()); exec(bpy.data.texts["house_roof"].as_string())
    hip_roof(-0.675, -0.675, 10.475, 9.475, ze=3.55, pitch=25)   # footprint incl. overhang
    cpac_tiles(); roof_caps()

Re-running any of these rebuilds the same objects in place.
shortcut: rectangular footprints only. L/T-shaped house: one hip_roof per wing (name="Roof_Wing2" ->
Roof_Wing2_Hip/_Eave/_CPAC_Tiles/_Caps) whose slope runs into the main roof — the intersection is the valley —
then roof_caps(base, others=[the other *_Hip]) for each roof so caps stop where another roof covers them.
"""
import bpy, bmesh, math
from mathutils import Vector


def _part(base, part):
    """Roof_Hip -> Roof_CPAC_Tiles; Roof_Wing2_Hip -> Roof_Wing2_CPAC_Tiles."""
    return (base[:-4] if base.endswith("_Hip") else base) + "_" + part


def hip_roof(x0, y0, x1, y1, ze, pitch=25, soffit_z=None, name="Roof", c=None):
    """<name>_Eave (soffit + fascia slab) and <name>_Hip (4 faces, metre UVs, thin underlay).

    x0..y1 = outer eave line (wall face + overhang). ze = eave height. The ridge runs along
    the longer side. The Eave's underside is the exterior soffit (ฝ้าชายคา): keep it visible
    and only hide it for top-plan / cutaway shots.
    """
    soffit_z = ze - 0.15 if soffit_z is None else soffit_z
    eave = box(name + "_Eave", x0, y0, soffit_z, x1, y1, ze, mat("M_Soffit_White", (0.85, 0.85, 0.83), 0.6), c)
    replace_obj(name + "_Hip")
    half = min(x1 - x0, y1 - y0) / 2
    zr = ze + half * math.tan(math.radians(pitch))
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    me = bpy.data.meshes.new(name + "_Hip")
    bm = bmesh.new()
    c0, c1, c2, c3 = [bm.verts.new(p) for p in ((x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze))]
    if abs((x1 - x0) - (y1 - y0)) < 1e-4:   # square -> pyramid, one apex (two coincident ridge ends broke roof_caps)
        r0 = bm.verts.new((xm, ym, zr))
        faces = ((c0, c1, r0), (c1, c2, r0), (c2, c3, r0), (c3, c0, r0))
    elif x1 - x0 >= y1 - y0:
        r0, r1 = bm.verts.new((x0 + half, ym, zr)), bm.verts.new((x1 - half, ym, zr))
        faces = ((c0, c1, r1, r0), (c1, c2, r1), (c2, c3, r0, r1), (c3, c0, r0))
    else:
        r0, r1 = bm.verts.new((xm, y0 + half, zr)), bm.verts.new((xm, y1 - half, zr))
        faces = ((c0, c1, r0), (c1, c2, r1, r0), (c2, c3, r1), (c3, c0, r0, r1))
    for f in faces:
        bm.faces.new(f)
    bm.normal_update()
    uvl = bm.loops.layers.uv.new("UVMap")   # u along the eave, v up the slope, in metres
    for f in bm.faces:
        e = (f.verts[1].co - f.verts[0].co).normalized()
        up = f.normal.cross(e).normalized()
        if up.z < 0:
            up = -up
        for l in f.loops:
            l[uvl].uv = (l.vert.co.dot(e), l.vert.co.dot(up))
    bm.to_mesh(me)
    bm.free()
    roof = bpy.data.objects.new(name + "_Hip", me)
    col(c).objects.link(roof)
    roof.data.materials.append(mat("M_Roof_Underlay", (0.022, 0.025, 0.032), 0.9))   # as dark as the tiles: shows through valley gaps (CM3)
    sol = roof.modifiers.new("Thickness", "SOLIDIFY")
    sol.thickness, sol.offset = 0.06, -1   # top surface = roof plane, tiles sit on it
    assert all(p.normal.z > 0 for p in me.polygons), "roof faces point down"
    return eave, roof


def soffit_ring(name, eaves, outline, z, t=0.012, m=None, c=None):
    """Flat soffit (ฝ้าชายคา) = eave rectangles minus the building outline, as boxes z..z+t.

    For long overhangs whose eave sits below the wall top (H2B: 1.10 m at 30 deg -> soffit +2.84, walls +3.60),
    where hip_roof's full _Eave box would cut through the walls and show as a low ceiling inside — delete those
    boxes and use this. eaves = [(x0, y0, x1, y1)] inside the fascia; outline = building outer faces [(x, y)].
    Grid cells on every breakpoint, so any orthogonal outline (bumps, wings) works.
    """
    eaves = [(min(a, c), min(b, d), max(a, c), max(b, d)) for a, b, c, d in eaves]
    def inside(x, y):
        k = False
        for i in range(len(outline)):
            (x1, y1), (x2, y2) = outline[i], outline[(i + 1) % len(outline)]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                k = not k
        return k
    xs = sorted({v for e in eaves for v in (e[0], e[2])} | {p[0] for p in outline})
    ys = sorted({v for e in eaves for v in (e[1], e[3])} | {p[1] for p in outline})
    bm = bmesh.new()
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            if any(e[0] < cx < e[2] and e[1] < cy < e[3] for e in eaves) and not inside(cx, cy):
                _bm_box(bm, xa, ya, z, xb, yb, z + t)
    assert bm.faces, f"{name}: no soffit cells — eaves {eaves} do not reach outside the outline"
    return _bm_to_obj(name, bm, m or mat("M_Soffit_White", (0.85, 0.85, 0.83), 0.6), c)


def _cpac_material(lap=0.32, tile_w=0.30):
    """Get-or-create M_Roof_CPAC: per-tile colour variation and side/lap joints from the tiles' TileUV map.

    lap/tile_w only apply when the material is created; delete M_Roof_CPAC to rebuild it for other tiles.
    """
    m = bpy.data.materials.get("M_Roof_CPAC")
    if m:
        return m
    m = bpy.data.materials.new("M_Roof_CPAC")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "TileUV"
    br = nt.nodes.new("ShaderNodeTexBrick")   # one brick = one tile: random shade per tile + dark joints
    br.offset, br.squash = 0.0, 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = tile_w
    br.inputs["Row Height"].default_value = lap
    br.inputs["Mortar Size"].default_value = 0.004
    # near-black blue-charcoal (CM3): lighter colours (P-2389 used 0.065-0.115) render pale grey at eye level
    br.inputs["Color1"].default_value = (0.026, 0.029, 0.039, 1)   # a wider spread reads as a checkerboard (CM3)
    br.inputs["Color2"].default_value = (0.033, 0.037, 0.049, 1)
    br.inputs["Mortar"].default_value = (0.008, 0.009, 0.012, 1)
    nt.links.new(uvn.outputs["UV"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    jb = nt.nodes.new("ShaderNodeBump")
    jb.inputs["Strength"].default_value = 0.4
    jb.invert = True
    nt.links.new(br.outputs["Fac"], jb.inputs["Height"])
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 120
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(jb.outputs["Normal"], bump.inputs["Normal"])   # chain: joints, then fine grain
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.0   # grazing sky reflections bleach a dark roof otherwise
    m.diffuse_color = (0.03, 0.035, 0.045, 1)
    return m


def _coverer(others, coplanar_counts, dist=10.0):
    """covered(p): another roof's surface lies above world point p (p on or just above this roof's plane).

    coplanar_counts=True starts the upward ray 3 cm below p, so a roof face lying in the same plane counts as
    covering (use it for the roof that should give way); False starts 3 cm above p (strictly above only).
    """
    from mathutils.bvhtree import BVHTree
    missing = [n for n in others if n not in bpy.data.objects]
    assert not missing, f"unknown roofs in others: {missing}"
    trees = []
    for nm in others:
        o = bpy.data.objects[nm]
        trees.append(BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices], [p.vertices for p in o.data.polygons]))
    off, up = Vector((0, 0, -0.03 if coplanar_counts else 0.03)), Vector((0, 0, 1))
    return lambda p: any(t.ray_cast(p + off, up, dist)[0] is not None for t in trees)


def _runs(a, b, covered, step=0.1):
    """Visible sub-segments of a->b (sampled every `step` m) that are not covered."""
    n = max(2, int((b - a).length / step))
    vis = [not covered(a.lerp(b, k / n)) for k in range(n + 1)]
    out, start = [], None
    for k, v in enumerate(vis + [False]):
        if v and start is None:
            start = k
        elif not v and start is not None:
            if k - 1 > start:
                out.append((a.lerp(b, start / n), a.lerp(b, (k - 1) / n)))
            start = None
    return out


def cpac_tiles(base="Roof_Hip", pitch_u=0.30, lap=0.32, wave=0.035, step=0.025, others=(), give_way=False,
               tile_w=0.30, c=None):
    """Real tile geometry on every face of `base` (~150k faces for a 10x11 m roof).

    pitch_u = wave pitch, lap = exposed tile length (= batten spacing), wave = wave height (0 = flat tiles),
    step = lap step. Typical values: CPAC CT lap 0.32-0.34, Neustile (flat) 0.27-0.29 (research CM3).
    others = other roofs of an L/T house: tile faces under them are removed. give_way=True also removes tiles
    where the other roof lies in the same plane (one roof must give way there, or both tile sets z-fight).
    Writes a "TileUV" map in metres (u along the eave, v up the slope) for per-tile joints in the material.
    """
    ob = bpy.data.objects[base]
    src = ob.data

    def h(u, v):
        return wave * (0.5 - 0.5 * math.cos(2 * math.pi * u / pitch_u)) + step * (1.0 - (v / lap) % 1.0) + 0.004

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("TileUV")
    uvof, base_pt = {}, {}   # base_pt: point on the roof plane under each tile face (coverage test)
    for poly in src.polygons:
        first_face = len(bm.faces)
        V = [src.vertices[i].co.copy() for i in poly.vertices]
        n = poly.normal.copy()
        e = (V[1] - V[0]).normalized()
        if e.x < -1e-6 or (abs(e.x) <= 1e-6 and e.y < 0):
            e = -e
        up = n.cross(e).normalized()
        if up.z < 0:
            up = -up
        # u from a world origin, v from this face's eave: coplanar faces of two roofs (L/T merged planes) share
        # waves and courses; a per-face origin left a zig-zag seam along the old hip (H2B terrace wing)
        v0 = min(p.dot(up) for p in V)
        o = n * V[0].dot(n) + up * v0
        uv = [((p - o).dot(e), (p - o).dot(up)) for p in V]
        vmax = max(q[1] for q in uv)
        vs = sorted({min(k * lap + t, vmax) for k in range(int(vmax / lap) + 2)
                     for t in (0, 0.006, 0.08, 0.16, 0.24, lap - 0.006)})

        def urange(v):
            xs = []
            for i in range(len(uv)):
                (u1, v1), (u2, v2) = uv[i], uv[(i + 1) % len(uv)]
                if (v1 - v) * (v2 - v) <= 0 and abs(v2 - v1) > 1e-9:
                    xs.append(u1 + (u2 - u1) * (v - v1) / (v2 - v1))
                elif abs(v1 - v) < 1e-9:
                    xs.append(u1)
            return (min(xs), max(xs)) if xs else None

        rows = []
        for v in vs:
            r = urange(v)
            if not r or r[1] - r[0] < 0.01:
                continue
            ua, ub = r
            us = [ua] + [k * 0.03 for k in range(math.ceil(ua / 0.03), math.floor(ub / 0.03) + 1)
                         if ua + 0.005 < k * 0.03 < ub - 0.005] + [ub]
            row = []
            for u in us:
                vert = bm.verts.new(o + e * u + up * v + n * h(u, v))
                uvof[vert] = (u, v)
                row.append((u, vert))
            rows.append(row)
        # rows differ in length on hip triangles/trapezoids: zip them with a triangle strip
        for A, B in zip(rows, rows[1:]):
            i = j = 0
            while i < len(A) - 1 or j < len(B) - 1:
                if j == len(B) - 1 or (i < len(A) - 1 and A[i + 1][0] <= B[j + 1][0]):
                    f = bm.faces.new((A[i][1], A[i + 1][1], B[j][1])); i += 1
                else:
                    f = bm.faces.new((A[i][1], B[j + 1][1], B[j][1])); j += 1
                for l in f.loops:
                    l[uvl].uv = uvof[l.vert]
                uc = sum(uvof[v][0] for v in f.verts) / 3
                vc = sum(uvof[v][1] for v in f.verts) / 3
                base_pt[f] = o + e * uc + up * vc
        # orient this roof face's tiles against its own normal (recalc on an open, near-flat sheet is unreliable)
        bm.faces.ensure_lookup_table()
        for k in range(first_face, len(bm.faces)):
            f = bm.faces[k]
            f.normal_update()
            if f.normal.dot(n) < 0:
                f.normal_flip()
    if others:   # drop tiles another roof covers; test on this roof's plane, not the tile centre (waves reach 7 cm)
        covered = _coverer(others, give_way)
        mw = ob.matrix_world
        dead = [f for f in bm.faces if covered(mw @ base_pt[f])]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
    for f in bm.faces:
        f.smooth = True
    name = _part(base, "CPAC_Tiles")
    replace_obj(name)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    tiles = bpy.data.objects.new(name, me)
    if not tiles.users_collection:
        col(c).objects.link(tiles)
    sol = tiles.modifiers.get("Thick") or tiles.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness, sol.offset = 0.012, -1
    me.materials.clear()
    m = _cpac_material(lap, tile_w)
    br = next((n for n in m.node_tree.nodes if n.type == "TEX_BRICK"), None)
    if br:   # shared material: keep the joints on this tile size
        br.inputs["Brick Width"].default_value, br.inputs["Row Height"].default_value = tile_w, lap
    me.materials.append(m)
    up_share = sum(1 for p in me.polygons if p.normal.z > 0) / max(1, len(me.polygons))
    # lap risers (~15% of faces) legitimately face down-slope; a flipped mesh would be ~0.15
    assert up_share > 0.7, f"tiles facing up only {up_share:.2f}"
    return tiles


def roof_caps(base="Roof_Hip", radius=0.11, lift=0.05, hip_pullback=0.25, others=(), cover_dist=10.0, c=None):
    """Half-round hip and ridge caps as one bevelled curve on the roof edges.

    others = names of the other *_Hip roofs of an L/T house: cap stretches that run under another
    roof are cut out (every visible run is kept), otherwise the caps of both roofs poke through and
    cross (CM3 kitchen wing). A roof more than cover_dist metres above a cap does not count as covering it.
    """
    missing = [n for n in others if n not in bpy.data.objects]
    assert not missing and base not in others, f"others must name other existing roofs: {missing or base}"
    covered = _coverer(others, True, cover_dist)   # coplanar counts: a hip lying in a merged plane is not a hip
    ob = bpy.data.objects[base]
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    ze = min(v.z for v in vs)
    corners = [v for v in vs if abs(v.z - ze) < 1e-3]
    ridge = [v for v in vs if v.z > ze + 0.1]
    name = _part(base, "Caps")
    replace_obj(name)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", radius, 4
    lv = Vector((0, 0, lift))

    def line(a, b):
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (*(a + lv), 1)
        sp.points[1].co = (*(b + lv), 1)

    def seg(a, b):
        L = (b - a).length
        if L < 1e-6:
            return
        if not others:
            return line(a, b)
        step, d, ext = L / 60, (b - a).normalized(), radius + L / 60
        for p, q in _runs(a, b, covered, step):   # one spline per visible run
            if (q - p).length > 2 * step:
                # ends that stop at another roof run on under it, so meeting caps close (CM3 left an 18 cm gap);
                # clamped to the edge so a cap never sticks out past a hip/ridge end
                tp, tq = (p - a).dot(d), (q - a).dot(d)
                p = p if tp < 1e-6 else a + d * max(0.0, tp - ext)
                q = q if L - tq < 1e-6 else a + d * min(L, tq + ext)
                line(p, q)
    for k in corners:
        r = min(ridge, key=lambda q: (q.xy - k.xy).length)
        seg(k + (r - k).normalized() * hip_pullback, r)   # stop the cap at the tile edge, not past the eave
    if len(ridge) == 2:
        seg(ridge[0], ridge[1])
    caps = bpy.data.objects.new(name, cu)
    col(c).objects.link(caps)
    cu.materials.clear()
    cu.materials.append(_cpac_material())
    return caps


def _faces(name):
    """World-space faces of a *_Hip roof: (verts, normal, eave dir e, up-slope dir up). First edge = eave."""
    o = bpy.data.objects[name]
    out = []
    for p in o.data.polygons:
        V = [o.matrix_world @ o.data.vertices[i].co for i in p.vertices]
        n = (o.matrix_world.to_3x3() @ p.normal).normalized()
        e = (V[1] - V[0]).normalized()
        up = n.cross(e).normalized()
        if up.z < 0:
            up = -up
        out.append((V, n, e, up))
    return out


def _clip_line(p0, d, V, n):
    """t-range of p0 + t*d inside the convex polygon V (normal n), or None."""
    lo, hi = -1e9, 1e9
    for i in range(len(V)):
        a, b = V[i], V[(i + 1) % len(V)]
        m = n.cross(b - a)   # points into the polygon for counter-clockwise V
        s0, s1 = (p0 - a).dot(m), d.dot(m)
        if abs(s1) < 1e-9 * m.length:
            if s0 <= 1e-4 * m.length:   # along (or outside) an edge: a hip of one roof, not a valley
                return None
        elif s1 > 0:
            lo = max(lo, -s0 / s1)
        else:
            hi = min(hi, -s0 / s1)
    return (lo, hi) if hi - lo > 1e-6 else None


def valley_lines(a="Roof_Hip", b="Roof_Wing2_Hip", min_len=0.05):
    """Where two hip roofs' faces cross (valleys of an L/T roof): list of (p0, p1, up, (sa, na), (sb, nb)).

    up = mean face normal; sa/sb = in-plane unit vectors from the valley across roof a / roof b's visible side.

    Parallel and coplanar face pairs are skipped (a merged plane has no valley).
    """
    from mathutils.bvhtree import BVHTree
    def surf(name):
        o = bpy.data.objects[name]
        t = BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices], [p.vertices for p in o.data.polygons])
        def z(x, y):
            hit = t.ray_cast(Vector((x, y, 100.0)), Vector((0, 0, -1)), 200.0)[0]
            return hit.z if hit else -1e9
        return z
    za, zb = surf(a), surf(b)
    out = []
    for Va, na, _, _ in _faces(a):
        for Vb, nb, _, _ in _faces(b):
            d = na.cross(nb)
            if d.length < 1e-4:
                continue
            d.normalize()
            # a point on both planes: solve with the third equation d.x = 0
            import mathutils
            M = mathutils.Matrix((na, nb, d))
            p0 = M.inverted() @ Vector((na.dot(Va[0]), nb.dot(Vb[0]), 0.0))
            ra, rb = _clip_line(p0, d, Va, na), _clip_line(p0, d, Vb, nb)
            if not ra or not rb:
                continue
            t0, t1 = max(ra[0], rb[0]), min(ra[1], rb[1])
            if t1 - t0 <= min_len:
                continue
            # a real valley: roof a is clearly on top on one side, roof b on the other (rules out a hip of one
            # roof that merely lies in, or 2 mm under, the other roof's plane)
            mid = p0 + d * (t0 + t1) / 2
            side = d.cross(Vector((0, 0, 1)))
            if side.length < 1e-6:
                continue
            side = side.normalized() * 0.3
            dif = [za(q.x, q.y) - zb(q.x, q.y) for q in (mid + side, mid - side)]
            if min(dif) < -0.02 and max(dif) > 0.02:
                sa = d.cross(na).normalized()   # in plane a, across the valley
                if (sa.dot(side) > 0) != (dif[0] > 0):
                    sa = -sa                      # point toward the side where roof a is on top
                sb = d.cross(nb).normalized()
                if (sb.dot(side) > 0) != (dif[0] < 0):
                    sb = -sb
                out.append((p0 + d * t0, p0 + d * t1, (na + nb).normalized(), (sa, na), (sb, nb)))
    return out


def roof_valleys(a="Roof_Hip", b="Roof_Wing2_Hip", width=0.24, lift=0.03, name="Roof_Valleys", c=None):
    """Metal valley gutter (รางน้ำตะเข้) along every valley of two intersecting hip roofs: a V of two strips,
    width/2 on each roof plane, `lift` above it (flat tiles 0.03, wave tiles 0.07) so it covers the cut tile edges.

    Valleys get metal, never ridge caps (a cap would dam the water). SCG CT spec: gutter bed 12 cm, wings 12 cm
    each side, valley rafter <= 6 m, catchment <= 36 m2.
    """
    segs = valley_lines(a, b)
    bm = bmesh.new()
    for p0, p1, up, *sides in segs:
        for s, n in sides:   # a flat strip across a V sank under the tiles and showed a white zigzag (CM3)
            w, l = s * width / 2, n * lift
            v = [bm.verts.new(p) for p in (p0 + l, p1 + l, p1 + w + l, p0 + w + l)]
            bm.faces.new(v)
    o = _bm_to_obj(name, bm, mat("M_Valley_Metal", (0.035, 0.038, 0.045), 0.7, 0.3), c)   # shiny metal read as a white zigzag (CM3)
    o.modifiers.new("Thick", "SOLIDIFY").thickness = 0.004
    return o, segs


def _beam(bm, p0, p1, w, h, up):
    """Box under the line p0-p1: top face on the line, w wide, h deep along -up."""
    d = (p1 - p0).normalized()
    u = (up - d * up.dot(d)).normalized()
    s = d.cross(u) * (w / 2)
    q = [p + sd * s + hd * u for p in (p0, p1) for sd in (-1, 1) for hd in (0, -h)]
    v = [bm.verts.new(x) for x in q]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)):
        bm.faces.new([v[i] for i in f])


def roof_frame(base="Roof_Hip", others=(), give_way=False, valleys_with=(), rafter_step=1.0, first=0.34, lap=0.32,
               post_step=1.5, wall_top=None, c=None):
    """Steel hip-roof frame under the tiles, Thai practice for CPAC concrete tiles (research CM3, SCG CT guide):

    จันทัน (rafters) C100x50 @ rafter_step 1.00 m · ระแนง/แป (battens) 40x25 at `first` from the eave, then every
    `lap` (CT 0.34/0.32-0.34, Neustile 0.295/0.27-0.29) plus a ridge pair · ตะเฆ่สัน (hips), อกไก่ (ridge),
    ตะเฆ่ราง (valleys with `valleys_with` roofs) C125x50 doubled = 100x125 · ดั้ง (king posts) C125x50 every
    post_step along the ridge down to wall_top. Members under another roof are cut (same rule as cpac_tiles).
    Returns <name>_Frame (structural steel) and <name>_Battens (galvanised). The *_Hip underlay hides them in
    normal renders; hide the tiles + underlay + eave slab for a structure shot.
    """
    wall_top = WT if wall_top is None else wall_top
    covered = _coverer(others, give_way) if others else (lambda p: False)
    F = _faces(base)
    fr, bt = bmesh.new(), bmesh.new()
    T_B, T_R = 0.025, 0.10   # batten depth, rafter depth (battens sit on rafters, tiles on battens)

    def place(bm, a, b, w, h, up, drop):
        for p, q in _runs(a, b, covered):
            _beam(bm, p - up * drop, q - up * drop, w, h, up)

    for V, n, e, up in F:
        o = V[0]
        uv = [((p - o).dot(e), (p - o).dot(up)) for p in V]

        def span(axis, val):   # range of the other coordinate where the polygon crosses axis=val
            xs = []
            for i in range(len(uv)):
                p1, p2 = uv[i], uv[(i + 1) % len(uv)]
                a1, a2 = p1[axis], p2[axis]
                if (a1 - val) * (a2 - val) <= 0 and abs(a2 - a1) > 1e-9:
                    xs.append(p1[1 - axis] + (p2[1 - axis] - p1[1 - axis]) * (val - a1) / (a2 - a1))
            return (min(xs), max(xs)) if len(xs) >= 2 else None

        P = lambda u, v: o + e * u + up * v
        L = uv[1][0]
        vtop = max(q[1] for q in uv)
        k = 0
        while k * rafter_step <= L + 1e-6:   # rafters from the eave up to the hip/ridge
            u = min(max(k * rafter_step, 0.03), L - 0.03)
            r = span(0, u)
            if r and r[1] - r[0] > 0.1:
                place(fr, P(u, r[0]), P(u, r[1] - 0.02), 0.05, T_R, n, T_B)
            k += 1
        vs = [first + i * lap for i in range(int((vtop - first) / lap) + 1)] + [vtop - 0.06, vtop - 0.14]
        for v in vs:   # battens parallel to the eave
            r = span(1, v) if 0 < v < vtop else None
            if r and r[1] - r[0] > 0.1:
                place(bt, P(r[0] + 0.02, v), P(r[1] - 0.02, v), 0.04, T_B, n, 0.0)
    # hips + ridge: every non-eave edge, shared by two faces (dedupe by rounded endpoints)
    seen = set()
    for V, n, e, up in F:
        for i in range(1, len(V)):
            a, b = V[i], V[(i + 1) % len(V)]
            key = tuple(sorted((tuple(round(x, 3) for x in a), tuple(round(x, 3) for x in b))))
            if key in seen or abs(a.z - b.z) < 1e-6 and a.z < min(v.z for v in V) + 1e-6:
                continue
            seen.add(key)
            place(fr, a, b, 0.10, 0.125, Vector((0, 0, 1)), T_B)
    for other in valleys_with:
        for p0, p1, upn, *_ in valley_lines(base, other):
            place(fr, p0, p1, 0.10, 0.125, upn, T_B)
    # king posts under the ridge (or the apex of a pyramid)
    zs = [v.z for V, *_ in F for v in V]
    top = [v for V, *_ in F for v in V if v.z > max(zs) - 1e-4]
    r0, r1 = min(top, key=lambda v: (v.x, v.y)), max(top, key=lambda v: (v.x, v.y))
    nposts = 1 if (r1 - r0).length < 1e-6 else max(1, int((r1 - r0).length / post_step)) + 1   # pyramid: one post
    for i in range(nposts):
        p = r0.lerp(r1, i / max(1, nposts - 1)) - Vector((0, 0, T_B + 0.125))
        if covered(p + Vector((0, 0, T_B + 0.125))):
            continue
        _beam(fr, p, Vector((p.x, p.y, wall_top)), 0.125, 0.05, Vector((1, 0, 0)))
    steel = mat("M_Steel_Primer", (0.20, 0.20, 0.21), 0.5, 0.6)
    galv = mat("M_Steel_Galv", (0.62, 0.64, 0.66), 0.35, 0.9)
    f = _bm_to_obj(_part(base, "Frame"), fr, steel, c)
    b = _bm_to_obj(_part(base, "Battens"), bt, galv, c)
    return f, b


def carport_metal(name, x_low, x_high, y0, y1, z_high, posts, slope_deg=7.0, purlin_step=0.8, rib=0.25,
                  purlin=(0.045, 0.075), rafter_d=0.10, beam_d=0.10, flush=False, rafter_step=None, c=None):
    """Mono-pitch metal-sheet carport (โรงจอดรถหลังคาเมทัลชีท), sloping along x, as a free-standing frame.

    Sheet top runs from z_high at x_high down to x_low (slope >= 5 deg, 6 deg+ for a single 760 sheet, 3 deg only with
    click-lock sheet — research CM3). posts = [(x, y), ...] box posts 100x100. Under the sheet: purlins (w, h) along y
    every purlin_step (<= 1.0 m); rafters (rafter_d deep) along x at each post row, plus intermediates so they are
    <= rafter_step apart; edge beams (beam_d deep) along y on each post line — under the rafters, or with flush=True
    welded flush with the rafter tops (shallower roof build-up). Gutter + downpipes on the low side (ป.พ.พ. 1341).
    Research CM3: 1 car = 2.8-3.0 x 5.5 m, clear >= 2.5 m.
    Returns {part: object, "steel_low": lowest steel z (float)} — filter with isinstance(v, bpy.types.Object) before
    treating the values as objects; check the printed clear height.
    """
    c = c or f"{PROJ} Site"
    t = math.tan(math.radians(slope_deg))
    zs = lambda x: z_high - abs(x_high - x) * t   # sheet top
    lo, hi = min(x_low, x_high), max(x_low, x_high)
    pw, ph = purlin
    dz = Vector((0, 0, 1))
    # sheet: trapezoidal ribs running down the slope
    bm = bmesh.new()
    prof = []
    k = 0
    while y0 + (k + 0.9) * rib <= y1:   # whole ribs only; a partial last pan runs flat to y1
        b0 = y0 + k * rib
        prof += [(b0, 0.0), (b0 + 0.6 * rib, 0.0), (b0 + 0.7 * rib, 0.03), (b0 + 0.9 * rib, 0.03)]
        k += 1
    prof.append((y1, 0.0))
    rows = [[bm.verts.new((x, y, zs(x) + h)) for y, h in prof] for x in (lo, hi)]
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    out = {"sheet": _bm_to_obj(name + "_Sheet", bm, mat("M_MetalSheet", (0.05, 0.055, 0.065), 0.35, 0.6), c)}
    out["sheet"].modifiers.new("Thick", "SOLIDIFY").thickness = 0.0015
    for p in out["sheet"].data.polygons:
        p.use_smooth = False
    # frame
    fr = bmesh.new()
    n = max(1, round((hi - lo - 0.2) / purlin_step))
    for x in [lo + 0.1 + i * (hi - lo - 0.2) / n for i in range(n + 1)]:   # purlins along y, top under the sheet
        _beam(fr, Vector((x, y0 + 0.05, zs(x))), Vector((x, y1 - 0.05, zs(x))), pw, ph, dz)
    rows_y = sorted({round(y, 3) for _, y in posts})
    cols_x = sorted({round(x, 3) for x, _ in posts})
    rafters = list(rows_y)
    if rafter_step:
        for a, b in zip(rows_y, rows_y[1:]):
            k = math.ceil((b - a) / rafter_step - 1e-6)
            rafters += [a + (b - a) * i / k for i in range(1, k)]
    for y in rafters:   # rafters along x under the purlins
        _beam(fr, Vector((lo, y, zs(lo) - ph)), Vector((hi, y, zs(hi) - ph)), 0.05, rafter_d, dz)
    beam_top = lambda x: zs(x) - ph - (0.0 if flush else rafter_d)
    for x in cols_x:   # edge beams on each post line
        _beam(fr, Vector((x, y0 + 0.2, beam_top(x))), Vector((x, y1 - 0.2, beam_top(x))), 0.10, beam_d, dz)
    clear = min(beam_top(x) - beam_d for x in cols_x)
    out["steel_low"] = min(clear, zs(lo) - ph - rafter_d)
    pts = [(x - 0.05, y - 0.05, 0, x + 0.05, y + 0.05, beam_top(x) - beam_d) for x, y in posts]
    pts += [(x - 0.15, y - 0.15, 0, x + 0.15, y + 0.15, 0.03) for x, y in posts]   # base plates on footings
    out["frame"] = _bm_to_obj(name + "_Frame", fr, mat("M_Steel_White", (0.88, 0.88, 0.86), 0.4, 0.3), c)
    out["posts"] = mesh_obj(name + "_Posts", pts, mat("M_Steel_White", (0.88, 0.88, 0.86), 0.4, 0.3), c)
    # fascia boards on the open ends
    fb = bmesh.new()
    for y in (y0, y1):
        _beam(fb, Vector((lo, y, zs(lo) + 0.06)), Vector((hi, y, zs(hi) + 0.06)), 0.02, 0.24, dz)
    out["fascia"] = _bm_to_obj(name + "_Fascia", fb, mat("M_Steel_White", (0.88, 0.88, 0.86), 0.4, 0.3), c)
    # gutter + downpipes on the low side
    g = -1 if x_low < x_high else 1
    xg = x_low + g * 0.08
    gut = mat("M_Gutter", (0.05, 0.05, 0.055), 0.4, 0.3)
    out["gutter"] = box(name + "_Gutter", xg - 0.08, y0, zs(x_low) - 0.14, xg + 0.08, y1, zs(x_low) - 0.02, gut, c)
    ends = [min(posts, key=lambda p: (abs(p[0] - x_low), p[1])), min(posts, key=lambda p: (abs(p[0] - x_low), -p[1]))]
    out["downpipes"] = mesh_obj(name + "_Downpipes", [(xg - 0.04, y - 0.04, 0, xg + 0.04, y + 0.04, zs(x_low) - 0.12)
                                                      for _, y in ends], gut, c)
    print(f"{name}: clear height under beams {clear:.2f} m, low edge {zs(x_low):.2f}, high edge {zs(x_high):.2f}")
    return out


def carport_classic(name, x_low, x_high, y0, y1, z_high, posts, slope_deg=3.0, fillet_r=0.4, lights=3, rib=0.35, c=None):
    """Modern-classic carport to match a classic house: the metal-sheet roof and steel of carport_metal() hidden
    behind a white fascia with cornice bands, a flat soffit ceiling with downlights, square columns with base and
    capital, and rounded-corner fillets between the street-side columns (same language as a classic porch).

    The fascia must hide the roof's rise plus the steel under it, so keep both small: click-lock sheet at 3 deg
    (research CM3, BlueScope: 3 deg needs click-lock) and edge beams flush with the rafters. CM3: 6 deg + stacked
    steel gave a 0.76 m fascia that the user found far too heavy; 3 deg + flush gives ~0.43 m.
    Put the columns so the fascia overhangs them equally at both ends (printed); the user checks symmetry.
    Build (typical Thai practice, not an engineered design): steel box posts clad to 200x200 with fibre-cement and
    PU/foam base + capital mouldings; fascia = fibre-cement board on a steel stud frame; flat fibre-cement soffit.

    shortcut: house on the x_high side, street on y0, back on y1; other orientations need the boxes mirrored.
    Concealed box gutter on the low side behind the fascia (ป.พ.พ. 1341). Prints the clear height under the ceiling.
    Returns {part: object, "levels": {ceiling, fascia_bottom, fascia_top, sheet_high, sheet_low}} (levels is a dict).
    """
    c = c or f"{PROJ} Site"
    assert x_low < x_high, "carport_classic expects the house on the x_high side"
    out = carport_metal(name, x_low, x_high, y0, y1, z_high, posts, slope_deg, rib=rib, purlin=(0.05, 0.05),
                        rafter_d=0.10, beam_d=0.10, flush=True, rafter_step=1.3, c=c)
    replace_obj(name + "_Posts")
    replace_obj(name + "_Fascia")
    out.pop("posts", None)   # replaced by the columns below
    t = math.tan(math.radians(slope_deg))
    zs = lambda x: z_high - abs(x_high - x) * t
    zc = math.floor((out.pop("steel_low") - 0.02) * 100) / 100   # ceiling board just under the lowest steel
    zt, zf = z_high + 0.04, zc - 0.04                             # fascia top (covers the sheet edge) / bottom lip
    xf = x_low - 0.18                                             # fascia outside face, low side (gutter behind it)
    trim = bpy.data.materials.get("M_Trim_White") or mat("M_Trim_White", (0.95, 0.94, 0.91), 0.6)
    soffit = bpy.data.materials.get("M_Soffit_White") or mat("M_Soffit_White", (0.85, 0.85, 0.83), 0.6)
    out["fascia"] = mesh_obj(name + "_Fascia", [(xf, y0 - 0.08, zf, x_high, y0, zt),              # street side
                                                (xf, y0, zf, xf + 0.08, y1, zt)], trim, c)          # low side, no corner overlap
    # same end detail on both ends of the street elevation (symmetry); the side band butts into the front return
    out["cornice"] = cornice(name + "_Cornice", [('x', y0 - 0.08, xf, x_high, -1, True, True),
                                                 ('y', xf, y0 - 0.08, y1, -1, False, False)],
                             [(zt - 0.08, zt, 0.05), (zt - 0.13, zt - 0.08, 0.03), (zf, zf + 0.04, 0.02)], trim, c)
    out["ceiling"] = box(name + "_Ceiling", xf + 0.08, y0, zc, x_high, y1, zc + 0.02, soffit, c)
    cols = []
    for x, y in posts:   # 200 shaft, 300 base, capital: steel post inside, rendered as a plastered column
        cols += [(x - 0.10, y - 0.10, 0, x + 0.10, y + 0.10, zc), (x - 0.15, y - 0.15, 0, x + 0.15, y + 0.15, 0.22),
                 (x - 0.135, y - 0.135, 0.22, x + 0.135, y + 0.135, 0.26),
                 (x - 0.13, y - 0.13, zc - 0.10, x + 0.13, y + 0.13, zc - 0.04),
                 (x - 0.15, y - 0.15, zc - 0.04, x + 0.15, y + 0.15, zc)]
    out["columns"] = mesh_obj(name + "_Columns", cols, trim, c)
    ymin, ymax = min(y for _, y in posts), max(y for _, y in posts)
    front = sorted(x for x, y in posts if abs(y - ymin) < 1e-6)
    over_low, over_house = (front[0] - 0.10) - xf, x_high - (front[-1] + 0.10)
    print(f"{name}: fascia overhang past the street columns — low side {over_low:.2f} m, house side {over_house:.2f} m"
          + ("" if abs(over_low - over_house) < 0.02 else "  ← NOT symmetric: move the columns"))
    polys = []
    for a, b in zip(front, front[1:]):
        polys += spandrels(a + 0.10, b - 0.10, zf, fillet_r)
    if polys:
        out["fillets"] = prisms(name + "_Fillets", polys, 'x', y0 - 0.06, y0 + 0.14, trim, c)
    else:
        replace_obj(name + "_Fillets")
    # downpipes tucked behind the low-side end columns, painted like the columns (replace first: a rebuild keeps
    # the old object's material, so carport_metal's dark gutter colour would win)
    replace_obj(name + "_Downpipes")
    xp = xf + 0.06
    out["downpipes"] = mesh_obj(name + "_Downpipes", [(xp - 0.04, y - 0.04, 0, xp + 0.04, y + 0.04, zs(x_low) - 0.12)
                                                      for y in (ymin + 0.28, ymax - 0.28)], trim, c)
    glow = bpy.data.materials.get("M_Lamp_Glow") or mat("M_Lamp_Glow", (1.0, 0.72, 0.42), 0.4, emission=12.0)
    xm = (xf + 0.08 + x_high) / 2
    ys = [y0 + (y1 - y0) * (i + 0.5) / lights for i in range(lights)]
    out["downlights"] = mesh_obj(name + "_Downlights", [(xm - 0.06, y - 0.06, zc - 0.005, xm + 0.06, y + 0.06, zc)
                                                        for y in ys], glow, c)
    for i, y in enumerate(ys):
        ld = bpy.data.lights.get(f"{name}_Spot_{i}") or bpy.data.lights.new(f"{name}_Spot_{i}", "SPOT")
        ld.energy, ld.color, ld.spot_size, ld.spot_blend = 60, (1.0, 0.78, 0.55), math.radians(110), 0.6
        lo = bpy.data.objects.get(f"{name}_Spot_{i}") or bpy.data.objects.new(f"{name}_Spot_{i}", ld)
        if not lo.users_collection:
            col(c).objects.link(lo)
        lo.location = (xm, y, zc - 0.03)
    i = lights
    while bpy.data.objects.get(f"{name}_Spot_{i}"):   # spots left over from a run with more lights
        bpy.data.objects.remove(bpy.data.objects[f"{name}_Spot_{i}"], do_unlink=True)
        i += 1
    print(f"{name}: fascia {zt - zf:.2f} m tall ({zf:.2f}-{zt:.2f}), clear height under the ceiling {zc:.2f} m "
          f"(fillets lower it to {zf - fillet_r:.2f} at the columns)")
    out["levels"] = {"ceiling": zc, "fascia_bottom": zf, "fascia_top": zt, "sheet_high": z_high, "sheet_low": zs(x_low)}
    return out
