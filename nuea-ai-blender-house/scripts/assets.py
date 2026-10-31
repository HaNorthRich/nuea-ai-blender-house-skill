"""Local 3D asset library (~/3d-assets) fed from Sketchfab, for furniture, plants and cars.

Load like helpers.py into a text block "house_assets" and exec it after helpers.py. Runs inside Blender, so the
Sketchfab token never leaves Blender: it is read from the Blender MCP add-on preferences, the scene property, the
env var BLENDERMCP_SKETCHFAB_API_KEY or ~/.config/blender-mcp/sketchfab_token (chmod 600). Never print it.

    hits = sf_search("modern fabric sofa")            # CC0 / CC-BY, downloadable only
    folder = sf_fetch(hits[0]["uid"], "furniture")    # cached: model + SOURCE.json + ATTRIBUTION.txt
    place_asset(folder, "Sofa", (4.6, 3.0, FL), rot_z=180, size=("x", 2.2))
"""
import bpy, glob, json, math, os, re, shutil, time, urllib.parse, urllib.request, zipfile
from mathutils import Vector

LIB = os.path.expanduser("~/3d-assets")
API = "https://api.sketchfab.com/v3"
OK_LICENCES = {"cc0", "by"}   # commercial renders: CC0 needs nothing, CC-BY needs the attribution line


def _token():
    for name, ad in bpy.context.preferences.addons.items():
        p = getattr(ad, "preferences", None)
        if p is not None and getattr(p, "sketchfab_api_key", ""):
            return p.sketchfab_api_key
    t = getattr(bpy.context.scene, "blendermcp_sketchfab_api_key", "") or os.environ.get("BLENDERMCP_SKETCHFAB_API_KEY", "")
    f = os.path.expanduser("~/.config/blender-mcp/sketchfab_token")
    if not t and os.path.exists(f):
        t = open(f).read().strip()
    assert t, "no Sketchfab token: add-on prefs, scene property, env var or ~/.config/blender-mcp/sketchfab_token"
    return t


def _get(url, auth=True):
    req = urllib.request.Request(url)
    if auth:   # unredirected: urllib would otherwise forward the token on a redirect, even to another host
        req.add_unredirected_header("Authorization", f"Token {_token()}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


_LABELS = {"cc0 public domain": "cc0", "cc attribution": "by"}   # exact labels; NC/ND/SA/Standard/Editorial refused


def _licence(m):
    """(slug, label, url). Search results carry only {uid, label}; model details may add slug/url."""
    lic = m.get("license") or {}
    label = lic.get("label", "")
    slug = (lic.get("slug") or _LABELS.get(label.strip().lower(), "")).lower()
    return slug, label, lic.get("url", "")


def sf_search(q, count=12, max_faces=300_000):
    """Downloadable models matching q, CC0/CC-BY only, lightest first. Returns [{uid, name, author, licence, faces, url}]."""
    url = f"{API}/search?" + urllib.parse.urlencode({"type": "models", "q": q, "downloadable": "true", "count": 24})
    out = []
    for m in _get(url).get("results", []):
        slug, label, _ = _licence(m)
        faces = m.get("faceCount") or 0
        if slug in OK_LICENCES and faces <= max_faces:
            out.append({"uid": m["uid"], "name": m.get("name", ""), "author": (m.get("user") or {}).get("displayName", ""),
                        "licence": label or slug, "faces": faces, "url": m.get("viewerUrl", "")})
    return sorted(out, key=lambda h: h["faces"])[:count]


def sf_fetch(uid, category):
    """Download glTF into LIB/<category>/sketchfab-<slug>-<uid>/ once; returns the folder. Refuses NC/ND/editorial."""
    assert re.fullmatch(r"[0-9a-f]{32}", uid), f"bad Sketchfab uid {uid!r}"
    assert re.fullmatch(r"[a-z0-9_-]+", category), f"bad category {category!r}"
    done = glob.glob(os.path.join(LIB, "*", f"sketchfab-*-{uid}", "SOURCE.json"))
    if done:   # library first: works offline and survives renames on the site
        return os.path.dirname(done[0])
    meta = _get(f"{API}/models/{uid}")
    slug, label, lic_url = _licence(meta)
    assert slug in OK_LICENCES, f"{uid}: licence '{label or slug}' is not CC0/CC-BY"
    name = "".join(ch if ch.isalnum() else "-" for ch in meta.get("name", uid).lower()).strip("-")[:40] or uid
    folder = os.path.join(LIB, category, f"sketchfab-{name}-{uid}")
    os.makedirs(folder, exist_ok=True)
    try:
        dl = _get(f"{API}/models/{uid}/download").get("gltf", {}).get("url", "")   # short-lived link, never cache it
        assert urllib.parse.urlparse(dl).scheme == "https", f"{uid}: no https glTF download"
        zpath = os.path.join(folder, "model.zip")
        with urllib.request.urlopen(dl, timeout=300) as r, open(zpath, "wb") as f:
            shutil.copyfileobj(r, f)
        base = os.path.realpath(os.path.join(folder, "model"))
        with zipfile.ZipFile(zpath) as z:
            for member in z.namelist():   # refuse paths that escape the folder
                target = os.path.realpath(os.path.join(base, member))
                assert os.path.commonpath([target, base]) == base, f"unsafe zip path {member}"
            z.extractall(base)
        os.remove(zpath)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)   # no half-filled library entries
        raise
    author = (meta.get("user") or {})
    src = {"source": "sketchfab", "uid": uid, "name": meta.get("name"), "url": meta.get("viewerUrl"),
           "author": author.get("displayName"), "author_url": author.get("profileUrl"), "licence": label or slug,
           "licence_url": lic_url, "downloaded": time.strftime("%Y-%m-%d")}
    att = "" if slug == "cc0" else (f'"{src["name"]}" by {src["author"]} ({src["author_url"]}) licensed under '
                                    f'{src["licence"]} ({lic_url}). Source: Sketchfab — {src["url"]}\n')
    open(os.path.join(folder, "ATTRIBUTION.txt"), "w").write(att or "CC0 — no attribution required\n")
    json.dump(src, open(os.path.join(folder, "SOURCE.json"), "w"), ensure_ascii=False, indent=1)   # written last = complete
    return folder


def _gltf_in(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith((".gltf", ".glb")):
                return os.path.join(root, f)
    raise FileNotFoundError(f"no .gltf/.glb under {folder}")


def _source_collection(folder):
    """Import a library model once into a hidden collection ASSET_<folder name>; later calls reuse it."""
    key = os.path.basename(folder)
    src = bpy.data.collections.get("ASSET_" + key)
    if src is None:
        before = set(bpy.data.objects)
        import contextlib, io, logging
        out, err = io.StringIO(), io.StringIO()
        prev = logging.root.manager.disable
        logging.disable(logging.INFO)   # the glTF importer logs one line per node (448 for a car): keep MCP output short
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                bpy.ops.import_scene.gltf(filepath=_gltf_in(folder))
        finally:
            logging.disable(prev)
        noisy = [ln for ln in (out.getvalue() + err.getvalue()).splitlines() if "WARNING" in ln or "ERROR" in ln]
        for ln in noisy[:10]:   # keep the warnings, drop the per-node chatter
            print("glTF:", ln[:200])
        new = [o for o in bpy.data.objects if o not in before]
        if not new:
            raise RuntimeError(f"glTF import made no objects: {folder}\n" + err.getvalue()[-1500:])
        src = bpy.data.collections.new("ASSET_" + key)
        bpy.context.scene.collection.children.link(src)
        for o in new:
            for uc in list(o.users_collection):
                uc.objects.unlink(o)
            src.objects.link(o)
        src["source_folder"] = folder
    lc = bpy.context.view_layer.layer_collection.children.get(src.name)
    if lc:
        lc.exclude = True
    return src


def place_collection(src, name, loc, rot_z=0.0, size=("max", 1.0), c=None):
    """Linked copies of every object in collection `src` under a new empty <name>, scaled so the `size` axis
    ('x' | 'y' | 'z' | 'max', measured before rotation) is the given metres, bottom-centre on loc, turned rot_z deg.

    Sketchfab models (glTF) face -y; Poly Haven models also come in at the origin — exclude their collection
    after the first placement. Re-running with the same name replaces the previous instance.
    """
    c = c or f"{PROJ} Interior"
    old = bpy.data.objects.get(name)
    if old:   # only ever replace a previous placement, never a modelled object or a source part
        assert old.get("asset_root") and old.name not in src.objects, f"{name} is not an asset root; pick another name"
        for ch in list(old.children_recursive):
            bpy.data.objects.remove(ch, do_unlink=True)
        bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(name, None)
    root["asset_root"] = True
    col(c).objects.link(root)
    mapping = {}
    for o in src.objects:   # linked copies share mesh data
        cp = o.copy()
        mapping[o] = cp
        col(c).objects.link(cp)
    for o, cp in mapping.items():
        cp.parent = mapping.get(o.parent, root)
        if o.parent is None or o.parent not in mapping:
            cp.matrix_parent_inverse.identity()
    bpy.context.view_layer.update()
    pts = [cp.matrix_world @ Vector(b) for cp in mapping.values() if cp.type == "MESH" for b in cp.bound_box]
    assert pts, f"{src.name} has no meshes"
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    dims = hi - lo
    axis, metres = size
    cur = max(dims) if axis == "max" else dims["xyz".index(axis)]
    s = metres / cur if cur > 1e-9 else 1.0
    root.scale = (s, s, s)
    centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)) * s
    root.rotation_euler.z = math.radians(rot_z)
    root.location = Vector(loc) - root.rotation_euler.to_matrix() @ centre
    return root


def place_asset(folder, name, loc, rot_z=0.0, size=("max", 1.0), c=None):
    """place_collection() for a library folder (imports it on first use). Returns the parent empty."""
    root = place_collection(_source_collection(folder), name, loc, rot_z, size, c)
    root["asset_folder"] = folder
    return root


def catalog():
    """Rewrite LIB/CATALOG.md from every SOURCE.json: what is in the library, its licence and the credit line."""
    rows = []
    for src in sorted(glob.glob(os.path.join(LIB, "*", "*", "SOURCE.json"))):
        d = json.load(open(src, encoding="utf-8"))
        folder = os.path.dirname(src)
        ap = os.path.join(folder, "ATTRIBUTION.txt")
        att = open(ap, encoding="utf-8").read().strip() if os.path.exists(ap) else ""
        cell = lambda v: str(v or "").replace("|", "/").replace("\n", " ")
        rows.append(f"| {os.path.basename(os.path.dirname(folder))} | {cell(d.get('name'))} | `{d.get('uid')}` | "
                    f"{cell(d.get('licence'))} | {cell(d.get('author'))} | {d.get('downloaded')} | {cell(att)} |")
    text = ("# 3D asset library\n\nGenerated by nuea-ai-blender-house `assets.catalog()`. CC-BY items need their credit line "
            "wherever a render that shows them is published.\n\n| category | model | uid | licence | author | downloaded | credit |\n"
            "|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
    open(os.path.join(LIB, "CATALOG.md"), "w", encoding="utf-8").write(text)
    return len(rows)
