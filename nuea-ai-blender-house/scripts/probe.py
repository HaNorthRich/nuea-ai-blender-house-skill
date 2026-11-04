"""Measure the model, don't reason it (references/working-economy.md, rule 2). Compact tables, meant to be written to a file
and grepped, not pasted whole into the conversation.

    exec(open(S + "probe.py").read())
    objects_in((2.3, -0.2, 2.8), (3.0, 1.6, 3.8), skip=("PR_", "PC_", "PD_"))   # what is in a box of space
    parts("WL_B_Conc")                                                            # its loose parts: ties, lintels, beams
    near((2.62, 5.3, 3.12), reach=0.25)                                           # nearest surface of each object to a point
"""
import bmesh
import bpy
from mathutils import Vector


def _world_verts(o):
    """The evaluated mesh's vertices in world space (modifiers such as Solidify applied)."""
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    try:
        return [o.matrix_world @ v.co for v in me.vertices]
    finally:
        e.to_mesh_clear()


def _bb(o):
    """World bounding box of the evaluated mesh, or None when a modifier leaves it empty."""
    vs = _world_verts(o)
    if not vs:
        return None
    return Vector([min(v[i] for v in vs) for i in range(3)]), Vector([max(v[i] for v in vs) for i in range(3)])


def _meshes(skip=()):
    """Mesh objects in the current scene (not the whole file), skipping name prefixes."""
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and len(o.data.vertices) and not o.name.startswith(tuple(skip))]


def objects_in(lo, hi, skip=(), limit=80):
    """Every mesh whose bounding box meets the box lo..hi: name, collection, extents. Sorted by name."""
    lo, hi, rows = Vector(lo), Vector(hi), []
    for o in _meshes(skip):
        box = _bb(o)
        if box is None:
            continue
        a, b = box
        if all(a[i] <= hi[i] and b[i] >= lo[i] for i in range(3)):
            col = o.users_collection[0].name if o.users_collection else ""
            rows.append(f"{o.name:26s} {col[:24]:24s} x {a.x:.3f}–{b.x:.3f}  y {a.y:.3f}–{b.y:.3f}  z {a.z:.3f}–{b.z:.3f}")
    rows.sort()
    print("\n".join(rows[:limit]) + (f"\n… {len(rows) - limit} more" if len(rows) > limit else ""))
    return len(rows)


def parts(name, limit=40):
    """The loose parts of one mesh as boxes (one wall object holds its ties and lintels as separate parts). Modifiers applied."""
    o = bpy.data.objects[name]
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(e.to_mesh())
    e.to_mesh_clear()
    bm.verts.ensure_lookup_table()
    seen, rows, M = set(), [], o.matrix_world
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, pts = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop()
            pts.append(M @ a.co)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index)
                    stack.append(b)
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        rows.append(f"x {lo[0]:.3f}–{hi[0]:.3f}  y {lo[1]:.3f}–{hi[1]:.3f}  z {lo[2]:.3f}–{hi[2]:.3f}")
    bm.free()
    rows.sort()
    print(f"{name}: {len(rows)} parts\n" + "\n".join(rows[:limit]))
    return len(rows)


def near(p, reach=0.3, skip=(), limit=20):
    """Nearest surface point of each mesh within reach of p (world metres, modifiers and object scale applied): distance and object, closest first."""
    from mathutils.bvhtree import BVHTree
    p, rows = Vector(p), []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in _meshes(skip):
        box = _bb(o)
        if box is None or any(p[i] < box[0][i] - reach or p[i] > box[1][i] + reach for i in range(3)):
            continue
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        try:   # a tree in world space, so reach and distance are world metres whatever the object's scale
            t = BVHTree.FromPolygons([o.matrix_world @ v.co for v in me.vertices], [tuple(f.vertices) for f in me.polygons])
        finally:
            e.to_mesh_clear()
        hit = t.find_nearest(p, reach)
        if hit[0] is not None and hit[3] <= reach:
            rows.append((hit[3], o.name, hit[0]))
    rows.sort(key=lambda r: r[0])
    print("\n".join(f"{d * 1000:7.1f} mm  {n:26s} at ({w.x:.3f}, {w.y:.3f}, {w.z:.3f})" for d, n, w in rows[:limit]))
    return rows[:limit]


def _selftest():
    """A scaled cube 0.2 m from a point: near() reads 0.2 in world metres, objects_in finds it, parts counts one."""
    import bmesh as _bm
    me = bpy.data.meshes.new("_probe_test")
    bm = _bm.new()
    _bm.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("_probe_test", me)
    bpy.context.scene.collection.objects.link(o)
    o.scale = (0.5, 0.5, 0.5)
    o.location = (10.0, 0.0, 0.0)   # faces at x 9.75 … 10.25
    bpy.context.view_layer.update()
    try:
        rows = near((9.55, 0.0, 0.0), reach=0.3)
        hit = [r for r in rows if r[1] == "_probe_test"]
        assert hit and abs(hit[0][0] - 0.20) < 1e-4, rows
        assert objects_in((9.7, -0.1, -0.1), (9.8, 0.1, 0.1)) >= 1
        assert parts("_probe_test") == 1
    finally:
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)
    return "probe ok"


if __name__ == "__main__":   # blender -b --factory-startup --python-exit-code 1 -P probe.py
    print(_selftest())
