# The E42 modules in build order, exec'd into the caller's namespace (they share it by design: later stages call
# earlier ones). Use from a test or the Blender MCP:
#     exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
# Set E42_UPTO = "<file>" first to stop after that module, E42_DIR / SKILL_SCRIPTS to load from other folders. A function, class or
# upper-case constant defined in two sources (house_helpers + the modules) is refused: a later def silently replaced an earlier one
# twice (walls/ceiling `_minus`, house_helpers/conduit `_arc`).
import ast as _ast
import os as _os
import bpy

E42_MODULES = ("e42_struct.py", "e42_walls.py", "e42_roof.py", "e42_roof_trim.py", "e42_fascia.py", "e42_ceiling.py",
               "e42_paint.py", "e42_tiles.py", "e42_elec.py", "e42_conduit_geom.py", "e42_conduit.py",
               "e42_conduit_route.py", "e42_conduit_main.py", "e42_conduit_check.py", "e42_units.py")
E42_DIR = globals().get("E42_DIR") or _os.path.join(_os.path.dirname(bpy.data.filepath), "scripts")
SKILL_SCRIPTS = globals().get("SKILL_SCRIPTS") or _os.path.normpath(_os.path.join(E42_DIR, "..", "..", "..", "scripts"))   # (examples/e42/scripts → the skill's scripts)
if "house_helpers" not in bpy.data.texts:   # a new file: the skill's helpers.py as the text block (self-contained .blend)
    bpy.data.texts.new("house_helpers").from_string(open(_os.path.join(SKILL_SCRIPTS, "helpers.py")).read())
_srcs = [("house_helpers", bpy.data.texts["house_helpers"].as_string())] + \
        [(_f, open(_os.path.join(E42_DIR, _f)).read()) for _f in E42_MODULES]
_seen = {}
for _f, _s in _srcs:   # functions, classes and top-level constants: one source each
    for _n in _ast.parse(_s).body:
        _names = [_n.name] if isinstance(_n, (_ast.FunctionDef, _ast.ClassDef)) else \
            [_t.id for _t in getattr(_n, "targets", []) if isinstance(_t, _ast.Name) and _t.id.isupper()]
        for _nm in _names:
            assert _seen.setdefault(_nm, _f) == _f, f"{_nm} is defined in {_seen[_nm]} and {_f}"
for _f, _s in _srcs[:E42_MODULES.index(globals().get("E42_UPTO", E42_MODULES[-1])) + 2]:
    exec(compile(_s, _os.path.join(E42_DIR, _f) if _f.endswith(".py") else _f, "exec"))   # (tracebacks name the file)
