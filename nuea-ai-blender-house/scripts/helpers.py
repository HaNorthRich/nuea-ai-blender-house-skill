"""House-modeling helpers for the Blender MCP (execute_blender_code).

Load once per .blend (keeps the file self-contained):
    import bpy
    t = bpy.data.texts.get("house_helpers") or bpy.data.texts.new("house_helpers")
    t.from_string(open("<skill dir>/scripts/helpers.py").read())
Then start every later call with:
    PROJ = "P-2389"   # optional: collection prefix, set before exec
    exec(bpy.data.texts["house_helpers"].as_string())

Units are metres. x = left->right, y = front(-)->rear(+), z = up.
Every mesh is built in world coordinates, so object origins stay at world 0
(box-projected textures rely on that).
"""
import bpy, bmesh, math, os, time
from mathutils import Vector

# Project constants; a value set in the caller before exec wins.
PROJ = globals().get("PROJ", "House")   # collection prefix
FL = globals().get("FL", 0.45)          # finished floor level
WT = globals().get("WT", 3.45)          # wall top
TE = globals().get("TE", 0.15)          # exterior wall thickness
TI = globals().get("TI", 0.10)          # interior wall thickness


def col(name=None):
    name = name or PROJ
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def mat(name, rgb, rough=0.5, metal=0.0, transmission=0.0, emission=0.0):
    """Get-or-create a Principled material. Colour goes on the node, diffuse_color is viewport only."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if emission:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emission
    m.diffuse_color = (*rgb, 1)
    return m


# Corner order (i, j, k) per face, wound counter-clockwise seen from outside -> normals point out.
_BOX_FACES = (((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
              ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
              ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)))


def _bm_box(bm, x0, y0, z0, x1, y1, z1):
    xs, ys, zs = sorted((x0, x1)), sorted((y0, y1)), sorted((z0, z1))
    v = {(i, j, k): bm.verts.new((xs[i], ys[j], zs[k])) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    for f in _BOX_FACES:
        bm.faces.new([v[p] for p in f])


def replace_obj(name):
    """Delete an existing mesh/curve object so a rebuild keeps the exact name, not .001.

    Returns its materials so the rebuild can keep Poly Haven materials applied after it.
    """
    o = bpy.data.objects.get(name)
    if not o:
        return []
    assert o.type in ("MESH", "CURVE"), f"{name} is a {o.type}; pick another name"
    data, store = o.data, (bpy.data.meshes if o.type == "MESH" else bpy.data.curves)
    mats = list(data.materials)
    bpy.data.objects.remove(o, do_unlink=True)
    if data.users == 0:
        store.remove(data)
    return mats


def _bm_to_obj(name, bm, m=None, c=None):
    """Turn a bmesh into object `name`, replacing an old one of that name. Frees bm."""
    old_mats = replace_obj(name)
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    col(c).objects.link(o)
    # a rebuild keeps the materials applied since the first build (e.g. Poly Haven); m only seeds new objects
    for mm in [x for x in old_mats if x] or ([m] if m else []):
        o.data.materials.append(mm)
    return o


def mesh_obj(name, boxes, m=None, c=None):
    """One object made of several boxes (x0, y0, z0, x1, y1, z1). Re-running rebuilds it in place."""
    bm = bmesh.new()
    for b in boxes:
        _bm_box(bm, *b)
    return _bm_to_obj(name, bm, m, c)


def box(name, x0, y0, z0, x1, y1, z1, m=None, c=None):
    return mesh_obj(name, [(x0, y0, z0, x1, y1, z1)], m, c)


def prisms(name, polys, axis, w0, w1, m=None, c=None):
    """Solids from 2D outlines [(u, z), ...] extruded through a wall, all in one object.

    axis='x' -> wall runs along x: u = x and the extrusion spans y = w0..w1; axis='y' -> u = y, spans x.
    """
    P = (lambda u, w, z: (u, w, z)) if axis == 'x' else (lambda u, w, z: (w, u, z))
    bm = bmesh.new()
    for poly in polys:
        a = [bm.verts.new(P(u, w0, z)) for u, z in poly]
        b = [bm.verts.new(P(u, w1, z)) for u, z in poly]
        bm.faces.new(a)
        bm.faces.new(b[::-1])
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # each piece is closed, so this is reliable
    return _bm_to_obj(name, bm, m, c)


def _arc(cu, cz, r, a0, a1, n):
    return [(cu + r * math.cos(a0 + (a1 - a0) * k / n), cz + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def spandrels(c0, c1, zt, R, n=12):
    """2D wall pieces that round the top corners of opening c0..c1 (top zt) with radius R.

    R = (c1 - c0) / 2 turns the opening into a round arch; a smaller R gives a porch opening with rounded corners.
    """
    left = [(c0, zt - R), (c0, zt), (c0 + R, zt)] + _arc(c0 + R, zt - R, R, math.pi / 2, math.pi, n)[1:-1]
    right = [(c1 - R, zt), (c1, zt), (c1, zt - R)] + _arc(c1 - R, zt - R, R, 0, math.pi / 2, n)[1:-1]
    return [left, right]


def _rect(u0, u1, z0, z1):
    return [(u0, z0), (u1, z0), (u1, z1), (u0, z1)]


def arch_window(name, axis, plane, c0, c1, zb, zt, t, mv=1, mh=3, fw=0.05, depth=0.07, out=-1,
                frame=None, glass=None, wallm=None, trim=None, tw=0.12, n=16, c=None):
    """Round-top window in a rectangular wall opening (c0, c1, zb, zt) cut by wall_x/wall_y; zt = apex.

    Builds <name>_spandrel (wall-coloured fill above the spring line), _frame (outer frame, mv mullions running
    up into the arch, mh transoms), _glass and, with trim=, an outside architrave + _sill.
    t = wall thickness; out = which side of the wall is outdoors (-1/+1 along the wall normal).
    """
    c = c or f"{PROJ} Openings"
    assert n % 2 == 0, "n must be even so the spandrel quarters share the frame's arc vertices"
    r = (c1 - c0) / 2
    cx, zs = c0 + r, zt - r
    prisms(name + "_spandrel", spandrels(c0, c1, zt, r, n // 2), axis, plane - t / 2, plane + t / 2, wallm, c)
    ri = r - fw
    bars = [_rect(c0, c1, zb, zb + fw), _rect(c0, c0 + fw, zb, zs), _rect(c1 - fw, c1, zb, zs),
            _rect(c0, c1, zs - fw / 2, zs + fw / 2)]
    for i in range(1, mv + 1):
        cc = c0 + (c1 - c0) * i / (mv + 1)
        bars.append(_rect(cc - fw / 2, cc + fw / 2, zb, zs + math.sqrt(max(ri ** 2 - (cc - cx) ** 2, 0))))
    for i in range(1, mh + 1):
        zz = zb + (zs - zb) * i / (mh + 1)
        bars.append(_rect(c0, c1, zz - fw / 2, zz + fw / 2))
    outer, inner = _arc(cx, zs, r, 0, math.pi, n), _arc(cx, zs, ri, 0, math.pi, n)
    bars += [[outer[k], outer[k + 1], inner[k + 1], inner[k]] for k in range(n)]
    prisms(name + "_frame", bars, axis, plane - depth / 2, plane + depth / 2, frame, c)
    pane = [(c0, zb), (c1, zb)] + _arc(cx, zs, r, 0, math.pi, n)
    prisms(name + "_glass", [pane], axis, plane - 0.005, plane + 0.005, glass, c)
    if trim:
        f = plane + out * t / 2   # outside face of the wall
        ring = _arc(cx, zs, r + tw, 0, math.pi, n)
        polys = [[outer[k], outer[k + 1], ring[k + 1], ring[k]] for k in range(n)]
        polys += [_rect(c0 - tw, c0, zb, zs), _rect(c1, c1 + tw, zb, zs)]
        prisms(name + "_trim", polys, axis, f, f + out * 0.04, trim, c)
        if axis == 'x':
            box(name + "_sill", c0 - tw - 0.05, f, zb - 0.08, c1 + tw + 0.05, f + out * 0.09, zb, trim, c)
        else:
            box(name + "_sill", f, c0 - tw - 0.05, zb - 0.08, f + out * 0.09, c1 + tw + 0.05, zb, trim, c)
    else:   # a rebuild without trim removes the old architrave too
        replace_obj(name + "_trim")
        replace_obj(name + "_sill")


def _pieces(a0, a1, z0, z1, openings):
    """Split a wall span a0..a1 x z0..z1 around openings [(c0, c1, zb, zt)] (absolute coords)."""
    out, s = [], a0
    for c0, c1, zb, zt in sorted(openings):
        if c0 > s:
            out.append((s, c0, z0, z1))
        if zb > z0:
            out.append((c0, c1, z0, zb))
        if zt < z1:
            out.append((c0, c1, zt, z1))
        s = c1
    if s < a1:
        out.append((s, a1, z0, z1))
    return out


def wall_x(name, y, x0, x1, t, openings=(), z0=None, z1=None, m=None):
    """Wall running along x, centred on y."""
    z0 = FL if z0 is None else z0
    z1 = WT if z1 is None else z1
    return mesh_obj(name, [(a, y - t/2, za, b, y + t/2, zb) for a, b, za, zb in _pieces(x0, x1, z0, z1, openings)],
                    m, f"{PROJ} Walls")


def wall_y(name, x, y0, y1, t, openings=(), z0=None, z1=None, m=None):
    """Wall running along y, centred on x."""
    z0 = FL if z0 is None else z0
    z1 = WT if z1 is None else z1
    return mesh_obj(name, [(x - t/2, a, za, x + t/2, b, zb) for a, b, za, zb in _pieces(y0, y1, z0, z1, openings)],
                    m, f"{PROJ} Walls")


def trim_rect(name, axis, plane, c0, c1, zb, zt, t, out=-1, tw=0.12, proj=0.04, sill=True, m=None, c=None):
    """Outside architrave (บัวกรอบ) around a rectangular opening (c0, c1, zb, zt) + a projecting sill for windows.

    Same proportions as arch_window(trim=): 12 cm band, 4 cm proud, sill 9 cm proud. Doors: sill=False.
    """
    c = c or f"{PROJ} Openings"
    f = plane + out * t / 2
    bands = [_rect(c0 - tw, c1 + tw, zt, zt + tw), _rect(c0 - tw, c0, zb, zt), _rect(c1, c1 + tw, zb, zt)]
    o = prisms(name + "_trim", bands, axis, f, f + out * proj, m, c)
    if sill:
        if axis == 'x':
            box(name + "_sill", c0 - tw - 0.05, f, zb - 0.08, c1 + tw + 0.05, f + out * 0.09, zb, m, c)
        else:
            box(name + "_sill", f, c0 - tw - 0.05, zb - 0.08, f + out * 0.09, c1 + tw + 0.05, zb, m, c)
    else:
        replace_obj(name + "_sill")
    return o


def cornice(name, segs, profile, m=None, c=None, cuts=()):
    """Moulding bands / gutters along outside faces.

    segs: (axis, face, a0, a1, out[, ext0, ext1]) — face = outside face coordinate, a0..a1 = span along it,
    out = -1/+1 outward direction. profile: [(z0, z1, projection), ...]. Each end extends by the projection
    (ext0/ext1=False to stop flush) so convex corners close and concave ones bury inside the wall.
    At every corner extend exactly ONE of the two segments: when both extend, their bands overlap with coplanar
    faces and render as black streaks (CM3 carport fascia corner).
    cuts: [(axis, face, u0, u1, z_top)] — on that face, bands starting below z_top stop at u0..u1, so a string
    course dies into a window architrave instead of running through it (CM3 arches). Keep every band that is
    not cut above the architrave tops.
    """
    boxes = []
    for s in segs:
        axis, f, a0, a1, out = s[:5]
        e0, e1 = s[5:7] if len(s) > 5 else (True, True)
        for z0, z1, p in profile:
            spans = [(a0 - (p if e0 else 0), a1 + (p if e1 else 0))]
            for ax, cf, c0, c1, ztop in cuts:
                assert c0 < c1, f"cornice cut {c0}..{c1} is empty"
                if ax == axis and abs(cf - f) < 0.05 and z0 < ztop:
                    spans = [piece for u0, u1 in spans for piece in ((u0, min(u1, c0)), (max(u0, c1), u1))
                             if piece[1] - piece[0] > 1e-4]
            for u0, u1 in spans:
                boxes.append((u0, f, z0, u1, f + out * p, z1) if axis == 'x' else (f, u0, z0, f + out * p, u1, z1))
    return mesh_obj(name, boxes, m, c)


def window(name, axis, plane, c0, c1, zb, zt, mv=1, mh=0, fw=0.05, depth=0.07, frame=None, glass=None, c=None):
    """Aluminium frame + glass in an opening. axis='x' -> wall runs along x at y=plane. mv/mh = mullions."""
    c = c or f"{PROJ} Openings"
    boxes = []

    def B(a0, a1, z0, z1):
        if axis == 'x':
            boxes.append((a0, plane - depth/2, z0, a1, plane + depth/2, z1))
        else:
            boxes.append((plane - depth/2, a0, z0, plane + depth/2, a1, z1))
    B(c0, c1, zb, zb + fw); B(c0, c1, zt - fw, zt)
    B(c0, c0 + fw, zb, zt); B(c1 - fw, c1, zb, zt)
    for i in range(1, mv + 1):
        cc = c0 + (c1 - c0) * i / (mv + 1)
        B(cc - fw/2, cc + fw/2, zb, zt)
    for i in range(1, mh + 1):
        zz = zb + (zt - zb) * i / (mh + 1)
        B(c0, c1, zz - fw/2, zz + fw/2)
    f = mesh_obj(name + "_frame", boxes, frame, c)
    if axis == 'x':
        g = box(name + "_glass", c0, plane - 0.005, zb, c1, plane + 0.005, zt, glass, c)
    else:
        g = box(name + "_glass", plane - 0.005, c0, zb, plane + 0.005, c1, zt, glass, c)
    return f, g


def door(name, axis, plane, c0, c1, zb, zt, m=None, c=None):
    c = c or f"{PROJ} Openings"
    if axis == 'x':
        return box(name, c0, plane - 0.02, zb, c1, plane + 0.02, zt, m, c)
    return box(name, plane - 0.02, c0, zb, plane + 0.02, c1, zt, m, c)


# ---------------------------------------------------------------- materials

def fix_textures(prefix, size=2.0, disp_scale=0.02, normal_strength=None):
    """Make image-texture materials work on UV-less boxes and stop displacement artefacts.

    Poly Haven import_asset(apply_to=...) makes one copy per object named <id>_material_<obj>,
    so pass the asset id as prefix to fix every copy. size = metres one texture tile covers.
    normal_strength: plaster needs ~0.15 or walls show vertical streaks (P-2389, CM3).
    """
    done = []
    for m in bpy.data.materials:
        if not (m.name == prefix or m.name.startswith(prefix + "_material")) or not m.node_tree:
            continue
        nt = m.node_tree
        imgs = [n for n in nt.nodes if n.type == "TEX_IMAGE"]
        if not imgs:
            continue
        tc = next((n for n in nt.nodes if n.type == "TEX_COORD"), None) or nt.nodes.new("ShaderNodeTexCoord")
        mp = next((n for n in nt.nodes if n.type == "MAPPING"), None) or nt.nodes.new("ShaderNodeMapping")
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        mp.inputs["Scale"].default_value = (1 / size,) * 3
        for n in imgs:
            n.projection = "BOX"
            n.projection_blend = 0.25
            nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        for owner in (m, getattr(m, "cycles", None)):   # property moved from cycles to material in 4.x
            if owner is not None and hasattr(owner, "displacement_method"):
                owner.displacement_method = "BUMP"
        for n in nt.nodes:
            if n.type == "DISPLACEMENT":
                n.inputs["Scale"].default_value = disp_scale
            if n.type == "NORMAL_MAP" and normal_strength is not None:
                n.inputs["Strength"].default_value = normal_strength
        done.append(m.name)
    return done


def _fresh_nodes(name):
    """Get-or-create `name` and rebuild its node tree in place (assignments survive; old Principled values stay
    until the caller sets them). Don't pass the name of a textured material you want to keep."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"):
            nt.nodes.remove(n)
    return m, nt, next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")


def tile_mat(name, rgb, size=0.6, grout=0.005, grout_rgb=(0.35, 0.35, 0.34), rough=0.45, var=0.04):
    """Procedural square floor tiles (granito, pavers, porch tiles) in world metres on UV-less boxes.

    Cleaner than Poly Haven stone floors, whose veining reads orange (P-2389). Horizontal faces only.
    """
    m, nt, b = _fresh_nodes(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset, br.squash = 0.0, 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = size
    br.inputs["Row Height"].default_value = size
    br.inputs["Mortar Size"].default_value = grout
    br.inputs["Color1"].default_value = (*rgb, 1)
    br.inputs["Color2"].default_value = (*(max(0.0, ch - var) for ch in rgb), 1)
    br.inputs["Mortar"].default_value = (*grout_rgb, 1)
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    bump.invert = True   # grout lines sit lower than the tiles
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*rgb, 1)
    return m


def lawn_mat(name="M_Lawn", light=(0.20, 0.36, 0.07), dark=(0.10, 0.22, 0.04)):
    """Manicured lawn: large-scale colour patches + fine blade bump. Poly Haven grass is leafy/dry."""
    m, nt, b = _fresh_nodes(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    big = nt.nodes.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value, big.inputs["Detail"].default_value = 0.35, 4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value, fine.inputs["Detail"].default_value = 260, 2
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    for a, z in ((tc.outputs["Object"], big.inputs["Vector"]), (big.outputs["Fac"], ramp.inputs["Fac"]),
                 (ramp.outputs["Color"], b.inputs["Base Color"]), (tc.outputs["Object"], fine.inputs["Vector"]),
                 (fine.outputs["Fac"], bump.inputs["Height"]), (bump.outputs["Normal"], b.inputs["Normal"])):
        nt.links.new(a, z)
    b.inputs["Roughness"].default_value = 0.9
    m.diffuse_color = (*light, 1)
    return m


# ---------------------------------------------------------------- landscape

def leaf_mat(name, light, dark, scale=55.0):
    """Clipped-foliage look (hedges, cypress): voronoi leaf clumps for colour and bump."""
    m, nt, b = _fresh_nodes(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = scale
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    for a, z in ((tc.outputs["Object"], vor.inputs["Vector"]), (vor.outputs["Distance"], ramp.inputs["Fac"]),
                 (ramp.outputs["Color"], b.inputs["Base Color"]), (vor.outputs["Distance"], bump.inputs["Height"]),
                 (bump.outputs["Normal"], b.inputs["Normal"])):
        nt.links.new(a, z)
    b.inputs["Roughness"].default_value = 0.7
    m.diffuse_color = (*light, 1)
    return m


def hedge(name, pts, w=0.45, h=0.8, r=0.08, m=None, c=None):
    """Clipped hedge swept along a ground path [(x, y), ...]: rounded-rectangle section w x h, corner radius r.

    A full-round bevel (bevel_depth = w/2) read as rolled turf in CM3; this boxy section reads as boxwood.
    """
    c = c or f"{PROJ} Landscape"
    replace_obj(name + "_profile")
    pr = bpy.data.curves.new(name + "_profile", "CURVE")
    pr.dimensions = "2D"
    q = []
    for cx, cz, a0 in ((w / 2 - r, h - r, 0), (-w / 2 + r, h - r, 90), (-w / 2 + r, r, 180), (w / 2 - r, r, 270)):
        q += _arc(cx, cz, r, math.radians(a0), math.radians(a0 + 90), 4)
    sp = pr.splines.new("POLY")
    sp.points.add(len(q) - 1)
    for p, (x, z) in zip(sp.points, q):
        p.co = (x, z, 0, 1)
    sp.use_cyclic_u = True
    po = bpy.data.objects.new(name + "_profile", pr)
    col(c).objects.link(po)
    po.hide_render = po.hide_viewport = True
    old_mats = replace_obj(name)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.twist_mode = "3D", "Z_UP"
    cu.bevel_mode, cu.bevel_object, cu.use_fill_caps = "OBJECT", po, True
    s = cu.splines.new("POLY")
    s.points.add(len(pts) - 1)
    for p, (x, y) in zip(s.points, pts):
        p.co = (x, y, 0, 1)
    o = bpy.data.objects.new(name, cu)
    col(c).objects.link(o)
    for mm in [x for x in old_mats if x] or ([m] if m else []):
        cu.materials.append(mm)
    return o


def scatter(name, rects, count, r, z0, z1, m=None, seed=1, c=None):
    """Small blobs at random points over ground rectangles (x0, y0, x1, y1): flowers, ground cover.

    One mesh, deterministic. Hair particles put instances at the root (sunk into the soil), so they were dropped.
    """
    import random
    rnd = random.Random(seed)
    area = [(x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in rects]
    bm = bmesh.new()
    for _ in range(count):
        x0, y0, x1, y1 = rnd.choices(rects, weights=area)[0]
        g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r * rnd.uniform(0.6, 1.3))
        bmesh.ops.translate(bm, verts=g["verts"], vec=(rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(z0, z1)))
    return _bm_to_obj(name, bm, m, c or f"{PROJ} Landscape")


# ---------------------------------------------------------------- light, cameras, render

def setup_light(sun_rot_deg=(52, 0, 28), energy=4.5, hdri_strength=0.6, c=None):
    """Predictable daylight: a Sun lamp with a known direction; the HDRI only fills."""
    w = bpy.context.scene.world
    if w and hasattr(w, "sun_threshold"):
        w.sun_threshold = 1000.0   # don't let EEVEE extract the HDRI sun as a second shadow
    if w and w.node_tree:
        bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg:
            bg.inputs["Strength"].default_value = hdri_strength
    ld = bpy.data.lights.get("Sun_Key") or bpy.data.lights.new("Sun_Key", "SUN")
    ld.energy, ld.angle = energy, math.radians(2)
    sun = bpy.data.objects.get("Sun_Key") or bpy.data.objects.new("Sun_Key", ld)
    if not sun.users_collection:
        col(c or f"{PROJ} Site").objects.link(sun)
    sun.rotation_euler = tuple(math.radians(a) for a in sun_rot_deg)
    return sun


def setup_render(samples=128, look="AgX - Medium High Contrast", exposure=0.0):
    s = bpy.context.scene
    try:
        s.render.engine = "BLENDER_EEVEE"
    except TypeError:   # older builds call it BLENDER_EEVEE_NEXT
        s.render.engine = "BLENDER_EEVEE_NEXT"
    e = s.eevee
    e.use_raytracing = True
    try:
        e.ray_tracing_method = "SCREEN"
    except TypeError as x:
        print("ray_tracing_method:", x)
    e.use_fast_gi = True
    e.gi_diffuse_bounces = 3
    e.taa_render_samples = samples
    try:
        s.view_settings.look = look
    except TypeError as x:
        print("look:", x)
    s.view_settings.exposure = exposure


def cam(name, loc, tgt, lens=24, shift_y=0.0, ortho_scale=None, c=None):
    """Get-or-create a camera at loc looking at tgt. ortho_scale -> orthographic (top plans)."""
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens, cd.shift_y = lens, shift_y
    cd.clip_end = 500
    if ortho_scale:
        cd.type, cd.ortho_scale = "ORTHO", ortho_scale
    co = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if not co.users_collection:
        col(c or f"{PROJ} Site").objects.link(co)
    co.location = loc
    co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return co


def shoot(camera, fname, w=1920, h=1080, hide=(), subdir="renders"):
    """Render one still next to the .blend; hides `hide` objects for this shot only. Returns (path, seconds).

    One 1920x1080 EEVEE frame takes ~30-55 s; an MCP call over 120 s goes to the background,
    so shoot at most 2 per call.
    """
    s, O = bpy.context.scene, bpy.data.objects
    assert bpy.data.filepath, "save the .blend first; renders go next to it"
    missing = [n for n in hide if n not in O]
    assert not missing, f"hide list names not in scene: {missing}"
    d = os.path.join(os.path.dirname(bpy.data.filepath), subdir)
    os.makedirs(d, exist_ok=True)
    prev = (s.camera, s.render.resolution_x, s.render.resolution_y, s.render.filepath)
    hidden = [n for n in hide if not O[n].hide_render]
    for n in hidden:
        O[n].hide_render = True
    try:
        s.camera = O[camera]
        s.render.resolution_x, s.render.resolution_y = w, h
        s.render.filepath = os.path.join(d, fname)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        return s.render.filepath, round(time.time() - t, 1)
    finally:
        for n in hidden:
            O[n].hide_render = False
        s.camera, s.render.resolution_x, s.render.resolution_y, s.render.filepath = prev


# ---------------------------------------------------------------- checks

def inward_meshes(max_faces=2000):
    """Names of closed (manifold) meshes that are inside-out (negative net signed volume). Open meshes are skipped.

    Works for concave solids (arch frames, spandrels), where a centroid test misfires. The volume is summed over
    the whole object, so one flipped piece among larger correct ones can go unnoticed.
    """
    bad = []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.polygons or len(o.data.polygons) > max_faces:
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        if all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) < 0:
            bad.append(o.name)
        bm.free()
    return bad


def selftest():
    assert _pieces(0, 4, 0, 3, [(1, 2, 1, 2)]) == [(0, 1, 0, 3), (1, 2, 0, 1), (1, 2, 2, 3), (2, 4, 0, 3)]
    assert _pieces(0, 4, 0, 3, [(0, 1, 0, 3)]) == [(1, 4, 0, 3)]   # full-height door at the wall end
    me = bpy.data.meshes.new("_selftest_box")
    bm = bmesh.new()
    _bm_box(bm, 0, 0, 0, 1, 2, 3)
    bm.normal_update()
    out = all((f.calc_center_median() - Vector((0.5, 1, 1.5))).dot(f.normal) > 0 for f in bm.faces)
    bm.free()
    bpy.data.meshes.remove(me)
    assert out, "box normals point inward"
    a = box("_selftest_obj", 0, 0, 0, 1, 1, 1, c="_selftest")
    b = box("_selftest_obj", 0, 0, 0, 2, 2, 2, c="_selftest")
    assert b.name == "_selftest_obj" and "_selftest_obj.001" not in bpy.data.objects, "rebuild made a duplicate"
    keep = mat("_selftest_mat", (1, 0, 0))
    b.data.materials.append(keep)
    b = box("_selftest_obj", 0, 0, 0, 3, 3, 3, mat("_selftest_other", (0, 1, 0)), c="_selftest")
    assert list(b.data.materials) == [keep], "rebuild dropped the applied material"
    for n in ("_selftest_mat", "_selftest_other"):
        bpy.data.materials.remove(bpy.data.materials[n])
    replace_obj("_selftest_obj")
    trim_m = mat("_selftest_trim", (1, 1, 1))
    arch_window("_selftest_arch", 'x', 0, 1, 2, 0.5, 2.5, 0.15, trim=trim_m, c="_selftest")
    bad = inward_meshes(max_faces=10 ** 6)
    for part in ("spandrel", "frame", "glass", "trim", "sill"):
        o = bpy.data.objects[f"_selftest_arch_{part}"]
        assert len(o.data.polygons) > 0, part
        assert o.name not in bad, f"{part} inside-out"
    arch_window("_selftest_arch", 'x', 0, 1, 2, 0.5, 2.5, 0.15, c="_selftest")   # rebuild without trim
    assert "_selftest_arch_trim" not in bpy.data.objects, "old trim left behind"
    for part in ("spandrel", "frame", "glass"):
        replace_obj(f"_selftest_arch_{part}")
    bpy.data.materials.remove(trim_m)
    bpy.data.collections.remove(bpy.data.collections["_selftest"])
    return "helpers selftest ok"
