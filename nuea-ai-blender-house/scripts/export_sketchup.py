"""Export the model for SketchUp as GLB (SketchUp Pro/Studio: File > Import > .glb, then save as .skp).

    /Applications/Blender.app/Contents/MacOS/Blender -b "<file>.blend" --python-exit-code 1 -P export_sketchup.py -- \
        --out "<dir>/<name>.glb" [--with-assets] [--with-tiles]

Blender cannot write .skp (closed format, SketchUp SDK only) and Blender 5 dropped COLLADA, so GLB is the route;
SketchUp imports it with materials and image textures. Runs on the saved file and never saves it back.

Default = building + site, light enough for SketchUp: library assets (Sketchfab / Poly Haven furniture, trees, car —
up to ~600k faces each), roof tile geometry (~190k faces; the *_Hip underlay keeps the roof planes) and helper
objects are left out (battens go with the tiles). --with-assets / --with-tiles put them back. Procedural base colours (tiles, lawn, granito)
cannot travel in glTF, so they are flattened to the material's viewport colour for the export.
"""
import argparse
import fnmatch
import os
import sys

import bpy

HELPERS = ("Plan_WallCaps", "*_profile")
POLYHAVEN = ("island_tree_*", "potted_plant_*", "modern_coffee_table_*", "side_table_*")


def is_asset(o):
    while o:
        if o.get("asset_root") or any(fnmatch.fnmatchcase(o.name, p) for p in POLYHAVEN):
            return True
        o = o.parent
    return False


def feeds_image(node, seen=None):
    """True if an image texture reaches this node through any chain (Mix, Hue/Sat, Reroute, groups)."""
    seen = set() if seen is None else seen
    if node in seen:
        return False
    seen.add(node)
    if node.type == "TEX_IMAGE":
        return True
    if node.type == "GROUP" and node.node_tree and any(x.type == "TEX_IMAGE" for x in node.node_tree.nodes):
        return True
    return any(feeds_image(l.from_node, seen) for s in node.inputs for l in s.links)


def flatten_procedural():
    """Base Color driven only by procedural nodes -> unlink it and use the material's viewport colour."""
    done = []
    for m in bpy.data.materials:
        if not m.users or not m.node_tree:
            continue
        for n in m.node_tree.nodes:
            if n.type != "BSDF_PRINCIPLED":
                continue
            sock = n.inputs["Base Color"]
            if sock.is_linked and not feeds_image(sock.links[0].from_node):
                m.node_tree.links.remove(sock.links[0])
                sock.default_value = tuple(m.diffuse_color)
                done.append(m.name)
    return done


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--with-assets", action="store_true")
    ap.add_argument("--with-tiles", action="store_true")
    a = ap.parse_args(argv)
    assert a.out.lower().endswith(".glb"), "--out must be a .glb file"
    # battens sit on the roof plane under the tiles: without tiles they z-fight with the underlay (CM3)
    skip = list(HELPERS) + ([] if a.with_tiles else ["*_CPAC_Tiles", "*_Battens"])
    off = set()   # render-off collections, children inherit

    def walk(c, hidden):
        hidden = hidden or c.hide_render
        if hidden:
            off.add(c)
        for ch in c.children:
            walk(ch, hidden)
    walk(bpy.context.scene.collection, False)
    keep, faces, why = [], 0, {}
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.view_layer.objects:
        reason = ("type" if o.type not in ("MESH", "CURVE") else
                  "render-hidden" if o.hide_render or all(c in off for c in o.users_collection) else
                  "pattern" if any(fnmatch.fnmatchcase(o.name, p) for p in skip) else
                  "asset" if not a.with_assets and is_asset(o) else None)
        if reason:
            why[reason] = why.get(reason, 0) + 1
            continue
        keep.append(o)
        me = o.evaluated_get(dg).to_mesh()
        faces += len(me.polygons)
        o.evaluated_get(dg).to_mesh_clear()
    assert keep, "nothing to export"
    flat = flatten_procedural()
    bpy.ops.object.select_all(action="DESELECT")
    for o in keep:   # viewport-hidden or locked objects cannot be selected and would drop out silently
        o.hide_set(False)
        o.hide_viewport = o.hide_select = False
        o.select_set(True)
    missing = [o.name for o in keep if not o.select_get()]
    assert not missing, f"cannot select (collection hidden in the viewport?): {missing[:5]}"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if os.path.exists(a.out):
        os.remove(a.out)   # a failed run must not leave the previous GLB looking like a result
    bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", use_selection=True, export_apply=True,
                              export_cameras=False, export_lights=False, export_yup=True)
    print(f"EXPORTED {a.out}: {len(keep)} objects, {faces} faces, "
          f"{os.path.getsize(a.out) / 1e6:.1f} MB; flattened {len(flat)} procedural materials; skipped {why}")


main()
